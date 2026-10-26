"""PostgreSQL transaction-backed outbox consumer.
No cloud queue or external API is required for local runtime.
Runs after `alembic upgrade head`, with CEDAR_AUTO_CREATE_SCHEMA=false.
"""
import os,time,json,logging
from datetime import datetime,timezone
from sqlalchemy import select,func
from backend.app import (
    SessionLocal, DATABASE_URL, Outbox, Loan, Payment, Batch, Snapshot,
    calculate, audit, uid
)
log=logging.getLogger('cedar.worker')
logging.basicConfig(level=os.getenv('CEDAR_LOG_LEVEL','INFO'))

def handle_one():
    with SessionLocal() as s:
        query=select(Outbox).where(Outbox.published==False).order_by(Outbox.created_at,Outbox.id)
        if not DATABASE_URL.startswith('sqlite'):
            query=query.with_for_update(skip_locked=True)
        ev=s.scalar(query.limit(1))
        if ev is None:return False
        try:
            payload=json.loads(ev.payload)
            targets=[]
            if payload.get('loan_id'):targets=[payload['loan_id']]
            elif ev.event_type=='FinancialBatchImported':
                targets=list(s.scalars(select(Payment.loan_id).where(Payment.batch_id==ev.aggregate_id).distinct()))
            for loan_id in targets:
                query=select(Loan).where(Loan.id==loan_id)
                if not DATABASE_URL.startswith('sqlite'):query=query.with_for_update()
                loan=s.scalar(query)
                if loan is None:continue
                if loan.current_snapshot_id:
                    prior=s.get(Snapshot,loan.current_snapshot_id)
                    if prior and prior.loan_version==loan.version:continue
                result=calculate(s,loan)
                snap=Snapshot(loan_id=loan.id,loan_version=loan.version,result_json=json.dumps(result))
                s.add(snap);s.flush()
                loan.current_snapshot_id=snap.id
                audit(s,'system-worker','SNAPSHOT_REFRESHED',snap.id,{'loan_id':loan.id,'version':loan.version})
            ev.published=True
            ev.processed_at=datetime.now(timezone.utc)
            ev.attempts=(ev.attempts or 0)+1
            s.commit()
            return True
        except Exception:
            s.rollback()
            log.exception('Outbox event failed: %s',ev.id)
            with SessionLocal() as retry:
                failing=retry.get(Outbox,ev.id)
                if failing:
                    failing.attempts=(failing.attempts or 0)+1
                    retry.commit()
            return False

def run():
    log.info('CEDAR local outbox worker running')
    while True:
        worked=handle_one()
        if not worked:time.sleep(float(os.getenv('CEDAR_WORKER_POLL_SECONDS','2')))
if __name__=='__main__':run()
