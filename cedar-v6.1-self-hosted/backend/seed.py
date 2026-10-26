"""Creates ONLY clearly synthetic demo users and scenario; never use for production."""
from decimal import Decimal as D
from sqlalchemy import select
from .app import (SessionLocal,User,Loan,Batch,Payment,Invoice,Allocation,Audit,Case,ph,calculate,Snapshot,uid,json,ds,utcnow,LoanAccess)

def seed():
    with SessionLocal() as s:
        if s.scalar(select(User).limit(1)):
            print('Database already has users; seed skipped')
            return
        for name,role in [('admin','admin'),('operator','operator'),('reviewer','reviewer'),('approver','approver'),('auditor','auditor'),('lender','lender'),('borrower','borrower')]:
            s.add(User(username=name,role=role,password_hash=ph.hash('DemoOnly!123')))
        loan=Loan(id='LN-DEMO-001',borrower='Green Valley FPO (synthetic)',principal=D('500000'),permitted_categories=json.dumps(['SEEDS','FERTILIZER','IRRIGATION_EQUIPMENT']),version=1)
        s.add(loan)
        s.flush()
        for role_name in ('lender','borrower'):
            actor=s.scalar(select(User).where(User.username==role_name))
            s.add(LoanAccess(user_id=actor.id,loan_id=loan.id))
        batch=Batch(source='SYNTHETIC-LMS',batch_ref='DEMO-BATCH-001',expected_count=4,received_count=4,status='COMPLETE')
        s.add(batch);s.flush()
        items=[('PAY-001','Seed supplier','150000'),('PAY-002','Fertilizer supplier','120000'),('PAY-003','Irrigation supplier','100000'),('PAY-004','Unknown recipient','80000')]
        pays={}
        for external,payee,amount in items:
            p=Payment(loan_id=loan.id,source=batch.source,external_id=external,batch_id=batch.id,payee=payee,amount=D(amount),allocated=D('0'))
            s.add(p);s.flush();pays[external]=p
        invs={}
        for number,supplier,category,amount,delivery in [('INV-001','Seed supplier','SEEDS','150000',True),('INV-002','Fertilizer supplier','FERTILIZER','120000',False),('INV-003','Irrigation supplier','IRRIGATION_EQUIPMENT','100000',True)]:
            inv=Invoice(loan_id=loan.id,number=number,supplier=supplier,category=category,amount=D(amount),allocated=D('0'),document_verified=True,delivery_verified=delivery)
            s.add(inv);s.flush();invs[number]=inv
        for pk,ik,amount in [('PAY-001','INV-001','150000'),('PAY-002','INV-002','120000'),('PAY-003','INV-003','100000')]:
            p=pays[pk];i=invs[ik];value=D(amount)
            p.allocated+=value;i.allocated+=value
            s.add(Allocation(loan_id=loan.id,payment_id=p.id,invoice_id=i.id,amount=value,active=True,created_by='demo-seed'))
        loan.version=2
        s.add(Case(loan_id=loan.id,fingerprint='DEMO-MISSING-DELIVERY',title='Delivery evidence missing for fertilizer',severity='S2',status='OPEN',version=1))
        s.add(Case(loan_id=loan.id,fingerprint='DEMO-UNALLOCATED',title='₹80,000 transfer has no supporting invoice',severity='S1',status='OPEN',version=1))
        s.add(Audit(actor='demo-seed',action='SYNTHETIC_DATA_CREATED',entity=loan.id,details=json.dumps({'notice':'All borrowers and records are fabricated for testing'})))
        s.commit()
        print('Demo seeded. Users: admin / operator / reviewer / approver / auditor / lender / borrower; password: DemoOnly!123')
if __name__=='__main__':seed()
