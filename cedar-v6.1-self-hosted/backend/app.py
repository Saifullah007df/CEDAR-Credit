"""CEDAR v6 self-hosted development system. No third-party API required at runtime.
Not a core banking ledger, regulatory certification, or live Samunnati connector.
"""
import os, json, uuid, hashlib, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import jwt
from argon2 import PasswordHasher
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (create_engine, Column, String, Integer, DateTime, ForeignKey,
                        Numeric, Boolean, Text, UniqueConstraint, select, update, func, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
from sqlalchemy.exc import IntegrityError

D = Decimal
ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get('DATABASE_URL','sqlite:///'+str(ROOT/'cedar_demo.db'))
DEMO_MODE = os.environ.get('CEDAR_DEMO_MODE','false').lower() == 'true'
JWT_SECRET = os.environ.get('CEDAR_JWT_SECRET', 'local-demo-secret-not-for-production' if DEMO_MODE else '')
if not JWT_SECRET or (not DEMO_MODE and len(JWT_SECRET) < 32):
    raise RuntimeError('Set strong CEDAR_JWT_SECRET outside demo mode')
UPLOAD_DIR = Path(os.environ.get('CEDAR_UPLOAD_DIR',str(ROOT/'uploads')))
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
if not DEMO_MODE and DATABASE_URL.startswith('sqlite'):
    raise RuntimeError('Production configuration requires PostgreSQL DATABASE_URL')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine,'connect')
    def pragmas(dbapi_connection, _):
        cur=dbapi_connection.cursor(); cur.execute('PRAGMA foreign_keys=ON');cur.close()
SessionLocal=sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
ph=PasswordHasher()

def utcnow(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())
def money(v):
    try: x=D(str(v))
    except Exception: raise HTTPException(422,'Invalid decimal amount')
    if not x.is_finite() or x<=0 or x.as_tuple().exponent < -2:
        raise HTTPException(422,'Amount must be positive INR with at most two decimals')
    return x.quantize(D('0.01'))
def ds(x):return str(D(x).quantize(D('0.01')))

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    username:Mapped[str]=mapped_column(String,unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String)
    role:Mapped[str]=mapped_column(String)
    totp_secret:Mapped[Optional[str]]=mapped_column(String,nullable=True)
    totp_last_step:Mapped[int]=mapped_column(Integer,default=-1)
    failed_logins:Mapped[int]=mapped_column(Integer,default=0)
    locked_until:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)
    token_version:Mapped[int]=mapped_column(Integer,default=0)
class LoanAccess(Base):
    __tablename__='loan_access'
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'),primary_key=True)
class Loan(Base):
    __tablename__='loans'
    id:Mapped[str]=mapped_column(String,primary_key=True)
    borrower:Mapped[str]=mapped_column(String)
    principal:Mapped[Decimal]=mapped_column(Numeric(20,2))
    permitted_categories:Mapped[str]=mapped_column(Text)
    version:Mapped[int]=mapped_column(Integer,default=1)
    current_snapshot_id:Mapped[Optional[str]]=mapped_column(String,nullable=True)
class Batch(Base):
    __tablename__='batches'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    source:Mapped[str]=mapped_column(String)
    batch_ref:Mapped[str]=mapped_column(String)
    expected_count:Mapped[int]=mapped_column(Integer)
    received_count:Mapped[int]=mapped_column(Integer)
    status:Mapped[str]=mapped_column(String)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__=(UniqueConstraint('source','batch_ref'),)
class Payment(Base):
    __tablename__='payments'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    source:Mapped[str]=mapped_column(String)
    external_id:Mapped[str]=mapped_column(String)
    batch_id:Mapped[str]=mapped_column(ForeignKey('batches.id'))
    payee:Mapped[str]=mapped_column(String)
    amount:Mapped[Decimal]=mapped_column(Numeric(20,2))
    allocated:Mapped[Decimal]=mapped_column(Numeric(20,2),default=D('0'))
    reversed:Mapped[bool]=mapped_column(Boolean,default=False)
    version:Mapped[int]=mapped_column(Integer,default=1)
    __table_args__=(UniqueConstraint('source','external_id'),)
class Invoice(Base):
    __tablename__='invoices'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    number:Mapped[str]=mapped_column(String)
    supplier:Mapped[str]=mapped_column(String)
    category:Mapped[str]=mapped_column(String)
    amount:Mapped[Decimal]=mapped_column(Numeric(20,2))
    allocated:Mapped[Decimal]=mapped_column(Numeric(20,2),default=D('0'))
    document_verified:Mapped[bool]=mapped_column(Boolean,default=False)
    delivery_verified:Mapped[bool]=mapped_column(Boolean,default=False)
    version:Mapped[int]=mapped_column(Integer,default=1)
class Allocation(Base):
    __tablename__='allocations'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    payment_id:Mapped[str]=mapped_column(ForeignKey('payments.id'))
    invoice_id:Mapped[str]=mapped_column(ForeignKey('invoices.id'))
    amount:Mapped[Decimal]=mapped_column(Numeric(20,2))
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_by:Mapped[str]=mapped_column(String)
    reversed_by:Mapped[Optional[str]]=mapped_column(String,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Idempotency(Base):
    __tablename__='idempotency'
    key:Mapped[str]=mapped_column(String,primary_key=True)
    request_hash:Mapped[str]=mapped_column(String)
    response_json:Mapped[str]=mapped_column(Text)
class Case(Base):
    __tablename__='cases'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    fingerprint:Mapped[str]=mapped_column(String,unique=True)
    title:Mapped[str]=mapped_column(String)
    severity:Mapped[str]=mapped_column(String)
    status:Mapped[str]=mapped_column(String,default='OPEN')
    proposed_by:Mapped[Optional[str]]=mapped_column(String,nullable=True)
    proposed_note:Mapped[Optional[str]]=mapped_column(Text,nullable=True)
    closed_by:Mapped[Optional[str]]=mapped_column(String,nullable=True)
    version:Mapped[int]=mapped_column(Integer,default=1)
class Doc(Base):
    __tablename__='documents'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    filename:Mapped[str]=mapped_column(String)
    sha256:Mapped[str]=mapped_column(String)
    content_type:Mapped[str]=mapped_column(String)
    extracted_text:Mapped[str]=mapped_column(Text,default='')
    stored_name:Mapped[str]=mapped_column(String)
    verified:Mapped[bool]=mapped_column(Boolean,default=False)
    version:Mapped[int]=mapped_column(Integer,default=1)
class Snapshot(Base):
    __tablename__='snapshots'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    loan_version:Mapped[int]=mapped_column(Integer)
    result_json:Mapped[str]=mapped_column(Text)
    published_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Outbox(Base):
    __tablename__='outbox_events'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    event_type:Mapped[str]=mapped_column(String)
    aggregate_id:Mapped[str]=mapped_column(String)
    payload:Mapped[str]=mapped_column(Text)
    published:Mapped[bool]=mapped_column(Boolean,default=False)
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    processed_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True), nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class Audit(Base):
    __tablename__='audit_events'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    actor:Mapped[str]=mapped_column(String)
    action:Mapped[str]=mapped_column(String)
    entity:Mapped[str]=mapped_column(String)
    details:Mapped[str]=mapped_column(Text)


class Journal(Base):
    __tablename__='journals'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    source:Mapped[str]=mapped_column(String)
    external_id:Mapped[str]=mapped_column(String)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    posting_date:Mapped[str]=mapped_column(String)
    currency:Mapped[str]=mapped_column(String,default='INR')
    journal_type:Mapped[str]=mapped_column(String,default='OTHER')
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__=(UniqueConstraint('source','external_id'),)
class JournalLine(Base):
    __tablename__='journal_lines'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    journal_id:Mapped[str]=mapped_column(ForeignKey('journals.id'))
    account:Mapped[str]=mapped_column(String)
    debit:Mapped[Decimal]=mapped_column(Numeric(20,2),default=D('0'))
    credit:Mapped[Decimal]=mapped_column(Numeric(20,2),default=D('0'))
class PolicyVersion(Base):
    __tablename__='policy_versions'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    loan_id:Mapped[str]=mapped_column(ForeignKey('loans.id'))
    version:Mapped[int]=mapped_column(Integer)
    categories_json:Mapped[str]=mapped_column(Text)
    approved_by:Mapped[str]=mapped_column(String)
    effective_date:Mapped[str]=mapped_column(String)
    __table_args__=(UniqueConstraint('loan_id','version'),)
class DocumentCorrection(Base):
    __tablename__='document_corrections'
    id:Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    doc_id:Mapped[str]=mapped_column(ForeignKey('documents.id'))
    version:Mapped[int]=mapped_column(Integer)
    corrected_text:Mapped[str]=mapped_column(Text)
    reason:Mapped[str]=mapped_column(Text)
    actor:Mapped[str]=mapped_column(String)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    __table_args__=(UniqueConstraint('doc_id','version'),)

if os.getenv('CEDAR_AUTO_CREATE_SCHEMA', 'true' if DEMO_MODE else 'false').lower()=='true':
    Base.metadata.create_all(engine)  # development tests only; use alembic upgrade head in deployment
app=FastAPI(title='CEDAR v6 Self-hosted API', version='0.2.0', description='Local operation; financial evidence is not proof of physical end use')
app.add_middleware(CORSMiddleware,allow_origins=os.environ.get('CEDAR_CORS_ORIGINS','http://localhost:5173,http://localhost:8000').split(','),allow_methods=['*'],allow_headers=['*'])

def db():
    with SessionLocal() as s: yield s

def audit(s,actor,action,entity,details):
    s.add(Audit(actor=actor,action=action,entity=entity,details=json.dumps(details,default=str)))
def touch(s, loan): loan.version+=1;loan.current_snapshot_id=None
def outbox(s, typ, entity, payload):
    s.add(Outbox(event_type=typ,aggregate_id=entity,payload=json.dumps(payload,default=str)))

def _totp(secret:str,step:int)->str:
    import base64,hmac,struct
    key=base64.b32decode(secret,casefold=True)
    mac=hmac.new(key,struct.pack('>Q',step),hashlib.sha1).digest()
    idx=mac[-1]&15
    return str((int.from_bytes(mac[idx:idx+4],'big')&0x7FFFFFFF)%1000000).zfill(6)

def user_from_header(authorization: str=Header(default=''),s:Session=Depends(db)):
    if not authorization.startswith('Bearer '): raise HTTPException(401,'Bearer token required')
    try: data=jwt.decode(authorization[7:],JWT_SECRET,algorithms=['HS256'])
    except jwt.PyJWTError: raise HTTPException(401,'Invalid or expired token')
    u=s.get(User,data.get('sub'))
    if not u:raise HTTPException(401,'Unknown user')
    if data.get('v')!=getattr(u,'token_version',0):raise HTTPException(401,'Session revoked')
    return u

def require(*roles):
    def dep(u:User=Depends(user_from_header)):
        if u.role not in roles:raise HTTPException(403,'Insufficient role')
        if not DEMO_MODE and u.role in ('admin','approver') and not u.totp_secret:
            raise HTTPException(403,'Privileged account requires offline MFA enrollment')
        return u
    return dep

def active_categories(s,loan):
    pv=s.scalar(select(PolicyVersion).where(PolicyVersion.loan_id==loan.id).order_by(PolicyVersion.version.desc()))
    return json.loads(pv.categories_json) if pv else json.loads(loan.permitted_categories)

def ensure_loan_scope(s,u,loan_id):
    if u.role=='admin' or (DEMO_MODE and u.role not in ('borrower','lender')):return
    allowed=s.get(LoanAccess,{'user_id':u.id,'loan_id':loan_id})
    if not allowed:raise HTTPException(403,'No access to this loan')

def need_loan(s,id):
    o=s.get(Loan,id)
    if not o:raise HTTPException(404,'Loan not found')
    return o

def getcase(s,id):
    c=s.get(Case,id)
    if not c:raise HTTPException(404,'Case not found')
    return c

def case_upsert(s, loan_id, fingerprint, title, severity):
    c=s.scalar(select(Case).where(Case.fingerprint==fingerprint))
    if c:return c
    c=Case(loan_id=loan_id,fingerprint=fingerprint,title=title,severity=severity)
    s.add(c);s.flush();return c

class Login(BaseModel): username:str; password:str; otp:Optional[str]=None
class NewLoan(BaseModel): id:str; borrower:str; principal:Decimal; permitted_categories:list[str]
class PaymentIn(BaseModel): loan_id:str; external_id:str; payee:str; amount:Decimal
class BatchIn(BaseModel): source:str; batch_ref:str; expected_count:int=Field(ge=0); payments:list[PaymentIn]
class InvoiceIn(BaseModel): loan_id:str; number:str; supplier:str; category:str; amount:Decimal; document_verified:bool=False; delivery_verified:bool=False
class AllocationIn(BaseModel): payment_id:str; invoice_id:str; amount:Decimal
class CaseAction(BaseModel): action:str; expected_version:int; note:str=Field(min_length=3)

@app.post('/v1/auth/login')
def login(body:Login,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.username==body.username))
    if u and u.locked_until and u.locked_until.replace(tzinfo=timezone.utc) > utcnow():
        raise HTTPException(429,'Account temporarily locked')
    try: verified=bool(u and ph.verify(u.password_hash,body.password))
    except Exception:verified=False
    if not verified:
        if u:
            u.failed_logins=(u.failed_logins or 0)+1
            if u.failed_logins>=5:
                u.locked_until=utcnow()+timedelta(minutes=15)
                u.failed_logins=0
            s.commit()
        raise HTTPException(401,'Invalid credentials')
    if u.totp_secret:
        step=int(utcnow().timestamp()//30)
        valid_step=next((x for x in [step-1,step,step+1]
            if x>u.totp_last_step and body.otp and _totp(u.totp_secret,x)==body.otp),None)
        if valid_step is None:raise HTTPException(401,'Valid one-time authentication code required')
        u.totp_last_step=valid_step
    u.failed_logins=0;u.locked_until=None;s.commit()
    token=jwt.encode({'sub':u.id,'v':u.token_version or 0,'exp':utcnow()+timedelta(hours=4)},JWT_SECRET,algorithm='HS256')
    return {'token':token,'role':u.role,'username':u.username,'mfa_enabled':bool(u.totp_secret)}

@app.get('/v1/health')
def health():
    try:
        with engine.connect() as c: c.execute(select(func.count()).select_from(Loan))
    except Exception: raise HTTPException(503,'Database unavailable')
    return {'status':'ok','mode':'DEVELOPMENT' if DEMO_MODE else 'SELF_HOSTED','database':'available'}

@app.get('/v1/loans')
def loans(s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor','lender'))):
    return [{'id':l.id,'borrower':l.borrower,'principal':ds(l.principal),'categories':json.loads(l.permitted_categories),'version':l.version} for l in s.scalars(select(Loan).order_by(Loan.id)).all() if u.role=='admin' or (DEMO_MODE and u.role not in ('borrower','lender')) or s.get(LoanAccess,{'user_id':u.id,'loan_id':l.id})]

@app.post('/v1/loans', status_code=201)
def addloan(body:NewLoan,s:Session=Depends(db),u:User=Depends(require('admin'))):
    amount=money(body.principal)
    if not body.permitted_categories:raise HTTPException(422,'At least one purpose category required')
    if s.get(Loan,body.id):raise HTTPException(409,'Loan exists')
    s.add(Loan(id=body.id,borrower=body.borrower,principal=amount,permitted_categories=json.dumps(body.permitted_categories)))
    audit(s,u.username,'LOAN_CREATED',body.id,{'principal':ds(amount)})
    s.commit();return {'id':body.id}

@app.post('/v1/source-batches',status_code=201)
def ingest(body:BatchIn,s:Session=Depends(db),u:User=Depends(require('admin','operator'))):
    if s.scalar(select(Batch).where(Batch.source==body.source,Batch.batch_ref==body.batch_ref)):
        raise HTTPException(409,'Source batch already imported')
    # reject collision with previously imported source identity, even in an incomplete batch
    ids=[p.external_id for p in body.payments]
    if len(ids)!=len(set(ids)):raise HTTPException(409,'Duplicate external IDs within batch')
    for p in body.payments:
        need_loan(s,p.loan_id);ensure_loan_scope(s,u,p.loan_id);money(p.amount)
        if s.scalar(select(Payment).where(Payment.source==body.source,Payment.external_id==p.external_id)):
            raise HTTPException(409,'Source event collision; inspect revision before importing')
    complete=len(body.payments)==body.expected_count
    b=Batch(source=body.source,batch_ref=body.batch_ref,expected_count=body.expected_count,received_count=len(body.payments),status='COMPLETE' if complete else 'INCOMPLETE')
    s.add(b);s.flush()
    for p in body.payments:
        s.add(Payment(loan_id=p.loan_id,source=body.source,external_id=p.external_id,batch_id=b.id,payee=p.payee,amount=money(p.amount),allocated=D('0')))
        touch(s,need_loan(s,p.loan_id))
    if not complete:
        for id in set(p.loan_id for p in body.payments):case_upsert(s,id,'SOURCE:'+b.id,'Incomplete financial import batch','S1')
    audit(s,u.username,'BATCH_IMPORTED',b.id,{'expected':body.expected_count,'received':len(body.payments),'complete':complete})
    outbox(s,'FinancialBatchImported',b.id,{'status':b.status,'source':b.source})
    s.commit()
    return {'id':b.id,'status':b.status,'received_count':b.received_count,'expected_count':b.expected_count}

@app.get('/v1/source-batches')
def batches(s:Session=Depends(db),u:User=Depends(require('admin','operator','auditor'))):
    return [{'id':b.id,'source':b.source,'batch_ref':b.batch_ref,'status':b.status,'received':b.received_count,'expected':b.expected_count} for b in s.scalars(select(Batch).order_by(Batch.created_at.desc())).all()]

@app.get('/v1/payments')
def payments(loan_id:Optional[str]=None,s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor','lender'))):
    stmt=select(Payment).order_by(Payment.external_id)
    if loan_id:stmt=stmt.where(Payment.loan_id==loan_id)
    if (not DEMO_MODE or u.role in ('borrower','lender')) and u.role!='admin':stmt=stmt.where(Payment.loan_id.in_(select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)))
    return [{'id':p.id,'loan_id':p.loan_id,'external_id':p.external_id,'source':p.source,'payee':p.payee,'amount':ds(p.amount),'allocated':ds(p.allocated),'available':ds(p.amount-p.allocated),'reversed':p.reversed} for p in s.scalars(stmt)]

@app.post('/v1/invoices',status_code=201)
def create_invoice(body:InvoiceIn,s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer'))):
    loan=need_loan(s,body.loan_id);ensure_loan_scope(s,u,body.loan_id); amt=money(body.amount)
    inv=Invoice(loan_id=loan.id,number=body.number,supplier=body.supplier,category=body.category.upper(),amount=amt,allocated=D('0'),document_verified=False,delivery_verified=False)
    s.add(inv);s.flush();touch(s,loan)
    audit(s,u.username,'INVOICE_CREATED',inv.id,{'loan':loan.id,'number':inv.number})
    outbox(s,'InvoiceCreated',inv.id,{'loan_id':loan.id})
    s.commit();return {'id':inv.id}

class InvoiceEvidenceUpdate(BaseModel):
    document_verified:bool
    delivery_verified:bool
    expected_version:int
    reason:str=Field(min_length=3)

@app.post('/v1/invoices/{invoice_id}/verify')
def verify_invoice(invoice_id:str,body:InvoiceEvidenceUpdate,s:Session=Depends(db),u:User=Depends(require('admin','reviewer'))):
    inv=s.get(Invoice,invoice_id)
    if not inv:raise HTTPException(404,'Invoice not found')
    ensure_loan_scope(s,u,inv.loan_id)
    if inv.version != body.expected_version:raise HTTPException(409,'Invoice version conflict')
    inv.document_verified=body.document_verified
    inv.delivery_verified=body.delivery_verified
    inv.version+=1
    touch(s,need_loan(s,inv.loan_id))
    audit(s,u.username,'INVOICE_EVIDENCE_REVIEWED',inv.id,{'reason':body.reason,'document_verified':body.document_verified,'delivery_verified':body.delivery_verified})
    outbox(s,'InvoiceEvidenceReviewed',inv.id,{'loan_id':inv.loan_id})
    s.commit();return {'id':inv.id,'version':inv.version,'document_verified':inv.document_verified,'delivery_verified':inv.delivery_verified}

@app.get('/v1/invoices')
def invoices(loan_id:Optional[str]=None,s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor','lender'))):
    stmt=select(Invoice).order_by(Invoice.number)
    if loan_id:stmt=stmt.where(Invoice.loan_id==loan_id)
    if (not DEMO_MODE or u.role in ('borrower','lender')) and u.role!='admin':stmt=stmt.where(Invoice.loan_id.in_(select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)))
    return [{'id':v.id,'loan_id':v.loan_id,'number':v.number,'supplier':v.supplier,'category':v.category,'amount':ds(v.amount),'allocated':ds(v.allocated),'available':ds(v.amount-v.allocated),'document_verified':v.document_verified,'delivery_verified':v.delivery_verified,'version':v.version} for v in s.scalars(stmt)]

@app.post('/v1/allocations',status_code=201)
def allocate(body:AllocationIn, idempotency_key:str=Header(alias='Idempotency-Key'),s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer'))):
    amt=money(body.amount)
    # Database-level conditional updates prevent two concurrent writes exceeding either capacity.
    # In PostgreSQL, row locking in sorted order should additionally be used to reduce deadlocks.
    key=u.id+':'+idempotency_key
    reqhash=hashlib.sha256(f'{body.payment_id}|{body.invoice_id}|{ds(amt)}'.encode()).hexdigest()
    idem=s.get(Idempotency,key)
    if idem:
        if idem.request_hash!=reqhash:raise HTTPException(409,'Idempotency key reused with different request')
        return json.loads(idem.response_json)
    p=s.get(Payment,body.payment_id);i=s.get(Invoice,body.invoice_id)
    if not p or not i:raise HTTPException(404,'Payment or invoice not found')
    if p.loan_id!=i.loan_id:raise HTTPException(409,'Cross-loan allocation forbidden')
    ensure_loan_scope(s,u,p.loan_id)
    if p.reversed:raise HTTPException(409,'Reversed payment cannot be allocated')
    if not i.document_verified:raise HTTPException(409,'Invoice must be human verified')
    loan=need_loan(s,p.loan_id)
    if i.category not in active_categories(s,loan):
        raise HTTPException(409,'Category not permitted by current demo loan policy')
    try:
        q=s.execute(update(Payment).where(Payment.id==p.id,Payment.reversed==False,Payment.allocated+amt<=Payment.amount).values(allocated=Payment.allocated+amt,version=Payment.version+1))
        if q.rowcount!=1:raise HTTPException(409,'Payment capacity exceeded')
        q=s.execute(update(Invoice).where(Invoice.id==i.id,Invoice.allocated+amt<=Invoice.amount).values(allocated=Invoice.allocated+amt,version=Invoice.version+1))
        if q.rowcount!=1:raise HTTPException(409,'Invoice capacity exceeded')
        a=Allocation(loan_id=p.loan_id,payment_id=p.id,invoice_id=i.id,amount=amt,created_by=u.username)
        s.add(a);s.flush();touch(s,loan)
        result={'id':a.id,'loan_id':loan.id,'amount':ds(amt),'status':'COMMITTED'}
        s.add(Idempotency(key=key,request_hash=reqhash,response_json=json.dumps(result)))
        audit(s,u.username,'ALLOCATION_COMMITTED',a.id,{'payment':p.id,'invoice':i.id,'amount':ds(amt)})
        outbox(s,'AllocationCommitted',a.id,{'loan_id':loan.id,'amount':ds(amt)})
        s.commit();return result
    except IntegrityError:
        s.rollback();raise HTTPException(409,'Concurrent allocation or idempotency conflict; retry safely')
    except Exception:
        s.rollback();raise

@app.post('/v1/allocations/{allocation_id}/reverse')
def reverse(allocation_id:str,s:Session=Depends(db),u:User=Depends(require('admin','approver'))):
    a=s.get(Allocation,allocation_id)
    if not a:raise HTTPException(404,'Allocation not found')
    ensure_loan_scope(s,u,a.loan_id)
    if not a.active:raise HTTPException(409,'Already reversed')
    p=s.get(Payment,a.payment_id);i=s.get(Invoice,a.invoice_id)
    # Explicitly reject reversal if source capacities no longer reconcile.
    s.execute(update(Payment).where(Payment.id==p.id,Payment.allocated>=a.amount).values(allocated=Payment.allocated-a.amount,version=Payment.version+1))
    s.execute(update(Invoice).where(Invoice.id==i.id,Invoice.allocated>=a.amount).values(allocated=Invoice.allocated-a.amount,version=Invoice.version+1))
    a.active=False;a.reversed_by=u.username;touch(s,need_loan(s,a.loan_id))
    audit(s,u.username,'ALLOCATION_REVERSED',a.id,{'amount':ds(a.amount)})
    outbox(s,'AllocationReversed',a.id,{'loan_id':a.loan_id})
    s.commit();return {'id':a.id,'status':'REVERSED'}

@app.get('/v1/allocations')
def allocations(loan_id:Optional[str]=None,s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor','lender'))):
    stmt=select(Allocation)
    if loan_id:stmt=stmt.where(Allocation.loan_id==loan_id)
    if (not DEMO_MODE or u.role in ('borrower','lender')) and u.role!='admin':stmt=stmt.where(Allocation.loan_id.in_(select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)))
    return [{'id':a.id,'loan_id':a.loan_id,'payment_id':a.payment_id,'invoice_id':a.invoice_id,'amount':ds(a.amount),'active':a.active} for a in s.scalars(stmt)]

def calculate(s,loan):
    ps=s.scalars(select(Payment).where(Payment.loan_id==loan.id,Payment.reversed==False)).all()
    invs=s.scalars(select(Invoice).where(Invoice.loan_id==loan.id)).all()
    allocs=s.scalars(select(Allocation).where(Allocation.loan_id==loan.id,Allocation.active==True)).all()
    byinvoice={i.id:i for i in invs}
    supported=D('0');incomplete=D('0');policy_exception=D('0')
    for a in allocs:
        inv=byinvoice[a.invoice_id]
        if inv.category not in active_categories(s,loan):policy_exception+=a.amount
        elif inv.document_verified and inv.delivery_verified:supported+=a.amount
        else:incomplete+=a.amount
    allocated=sum((a.amount for a in allocs),D('0'))
    total=sum((p.amount for p in ps),D('0'))
    source_incomplete=s.scalar(select(func.count()).select_from(Batch).join(Payment,Payment.batch_id==Batch.id).where(Payment.loan_id==loan.id,Batch.status!='COMPLETE'))>0
    unallocated=total-allocated
    findings=[]
    if source_incomplete:findings.append('Financial source batch is incomplete; result provisional')
    if incomplete>0:findings.append('Delivery or document verification incomplete')
    if unallocated>0:findings.append('Some observed payments have no verified expenditure allocation')
    if policy_exception>0:findings.append('Allocated evidence falls outside permitted categories')
    return {'loan_id':loan.id,'version':loan.version,'principal':ds(loan.principal),'observed_payments':ds(total),'supported':ds(supported),'incomplete':ds(incomplete),'policy_exception':ds(policy_exception),'unallocated':ds(unallocated),'source_complete':not source_incomplete,'status':'PROVISIONAL' if source_incomplete else 'ASSESSED_IMPORTED_RECORDS','findings':findings,'disclaimer':'Evidence assessment, not conclusive proof of physical end use or a lending decision.'}

@app.post('/v1/loans/{loan_id}/evaluate')
def evaluate(loan_id:str,s:Session=Depends(db),u:User=Depends(require('admin','reviewer','approver','operator'))):
    loan=need_loan(s,loan_id);ensure_loan_scope(s,u,loan_id)
    # Serialized by loan row in PostgreSQL; no external API required.
    if not DATABASE_URL.startswith('sqlite'):
        loan=s.scalar(select(Loan).where(Loan.id==loan_id).with_for_update())
    result=calculate(s,loan)
    sn=Snapshot(loan_id=loan.id,loan_version=loan.version,result_json=json.dumps(result))
    s.add(sn);s.flush()
    loan.current_snapshot_id=sn.id
    if D(result['incomplete'])>0: case_upsert(s,loan.id,'INCOMPLETE:'+str(loan.version),'Evidence pending verification','S2')
    if D(result['unallocated'])>0: case_upsert(s,loan.id,'UNALLOCATED:'+str(loan.version),'Unallocated observed expenditure','S2')
    if not result['source_complete']:case_upsert(s,loan.id,'SOURCE_LOAN:'+str(loan.version),'Incomplete financial source','S1')
    audit(s,u.username,'EVALUATION_PUBLISHED',sn.id,{'loan':loan.id,'version':loan.version,'status':result['status']})
    outbox(s,'EvaluationPublished',sn.id,{'loan_id':loan.id,'version':loan.version})
    s.commit()
    return {'snapshot_id':sn.id,**result}

@app.get('/v1/loans/{loan_id}/utilization')
def utilization(loan_id:str,s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor','lender'))):
    loan=need_loan(s,loan_id);ensure_loan_scope(s,u,loan_id)
    if loan.current_snapshot_id:
        snap=s.get(Snapshot,loan.current_snapshot_id)
        if snap and snap.loan_version==loan.version:
            return {'snapshot_id':snap.id,**json.loads(snap.result_json)}
    return {'snapshot_id':None,**calculate(s,loan),'status':'UNPUBLISHED_CURRENT_INPUTS'}

@app.get('/v1/cases')
def cases(s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor'))):
    return [{'id':c.id,'loan_id':c.loan_id,'title':c.title,'severity':c.severity,'status':c.status,'version':c.version,'proposed_by':c.proposed_by,'proposed_note':c.proposed_note} for c in s.scalars(select(Case).order_by(Case.severity,Case.title)).all() if u.role=='admin' or (DEMO_MODE and u.role not in ('borrower','lender')) or s.get(LoanAccess,{'user_id':u.id,'loan_id':c.loan_id})]

@app.post('/v1/cases/{case_id}/actions')
def case_action(case_id:str,body:CaseAction,s:Session=Depends(db),u:User=Depends(require('admin','reviewer','approver'))):
    c=getcase(s,case_id);ensure_loan_scope(s,u,c.loan_id)
    if c.version!=body.expected_version:raise HTTPException(409,'Case version is stale')
    if body.action=='propose':
        if u.role not in ('reviewer','admin') or c.status not in ('OPEN','UNDER_REVIEW'):raise HTTPException(409,'Invalid propose transition')
        c.proposed_by=u.username;c.proposed_note=body.note;c.status='APPROVAL_PENDING'
    elif body.action=='approve':
        if u.role not in ('approver','admin'):raise HTTPException(403,'Approver role required')
        if c.status!='APPROVAL_PENDING':raise HTTPException(409,'Case is not awaiting approval')
        if c.proposed_by==u.username:raise HTTPException(403,'Maker-checker violation')
        c.status='CLOSED';c.closed_by=u.username
    elif body.action=='reopen':
        if u.role not in ('approver','admin') or c.status!='CLOSED':raise HTTPException(409,'Invalid reopen transition')
        c.status='OPEN';c.closed_by=None
    else:raise HTTPException(422,'Allowed actions: propose, approve, reopen')
    c.version+=1
    audit(s,u.username,'CASE_'+body.action.upper(),c.id,{'note':body.note,'version':c.version})
    outbox(s,'Case'+body.action.title(),c.id,{'version':c.version})
    s.commit();return {'id':c.id,'status':c.status,'version':c.version}

@app.post('/v1/documents',status_code=201)
async def upload_document(loan_id:str,file:UploadFile=File(...),s:Session=Depends(db),u:User=Depends(require('admin','reviewer','operator'))):
    loan=need_loan(s,loan_id);ensure_loan_scope(s,u,loan_id)
    data=await file.read(5_000_001)
    if len(data)>5_000_000:raise HTTPException(413,'Max 5MB in this first implementation')
    typ='pdf' if data.startswith(b'%PDF') else ('png' if data.startswith(b'\x89PNG\r\n\x1a\n') else ('jpg' if data.startswith(b'\xff\xd8\xff') else 'unknown'))
    if typ=='unknown':raise HTTPException(415,'Only PDF/PNG/JPEG supported')
    filename=Path(file.filename or 'document').name
    path=UPLOAD_DIR/(uid()+'.'+typ)
    # Files must remain non-executable, and scanning is fail-closed when enabled.
    path.write_bytes(data)
    path.chmod(0o600)
    scan_required=os.getenv('CEDAR_REQUIRE_MALWARE_SCAN','true' if not DEMO_MODE else 'false').lower()=='true'
    if scan_required:
        import subprocess,shutil
        scanner=shutil.which('clamscan')
        if not scanner:
            path.unlink(missing_ok=True)
            raise HTTPException(503,'Local malware scanner is not available; upload rejected')
        try:
            r=subprocess.run([scanner,'--no-summary',str(path)],capture_output=True,timeout=45)
        except Exception:
            path.unlink(missing_ok=True)
            raise HTTPException(503,'Local malware scanning failed; upload rejected')
        if r.returncode!=0:
            path.unlink(missing_ok=True)
            raise HTTPException(422 if r.returncode==1 else 503,'File failed malware scan')
    text=''
    try:
        if typ=='pdf':
            from pypdf import PdfReader
            from io import BytesIO
            reader=PdfReader(BytesIO(data),strict=False)
            if len(reader.pages)>10:raise HTTPException(413,'PDF page limit 10')
            text='\n'.join(page.extract_text() or '' for page in reader.pages)[:10000]
        else:
            import pytesseract
            from PIL import Image, UnidentifiedImageError
            from io import BytesIO
            # OCR text is unverified, never automatically trusted.
            image=Image.open(BytesIO(data))
            image.verify()
            image=Image.open(BytesIO(data))
            if image.width*image.height>20_000_000: raise HTTPException(413,'Image pixel limit exceeded')
            text=pytesseract.image_to_string(image,lang='eng+tam',config='--psm 6',timeout=20)[:10000]
    except HTTPException:
        path.unlink(missing_ok=True);raise
    except Exception:
        if typ in ('png','jpg'):
            path.unlink(missing_ok=True)
            raise HTTPException(422,'Unreadable image file')
        text='[Extraction failed: requires human verification]'
    doc=Doc(loan_id=loan.id,filename=filename,sha256=hashlib.sha256(data).hexdigest(),content_type=typ,stored_name=path.name,extracted_text=text,verified=False)
    s.add(doc);s.flush();touch(s,loan)
    audit(s,u.username,'DOCUMENT_UPLOADED',doc.id,{'sha256':doc.sha256,'type':typ})
    outbox(s,'DocumentUploaded',doc.id,{'loan_id':loan.id})
    s.commit();return {'id':doc.id,'sha256':doc.sha256,'extract_preview':text[:1500],'verified':False}

@app.get('/v1/documents')
def documents(loan_id:Optional[str]=None,s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor','lender'))):
    stmt=select(Doc)
    if loan_id:stmt=stmt.where(Doc.loan_id==loan_id)
    if (not DEMO_MODE or u.role in ('borrower','lender')) and u.role!='admin':stmt=stmt.where(Doc.loan_id.in_(select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)))
    return [{'id':d.id,'loan_id':d.loan_id,'filename':d.filename,'sha256':d.sha256,'extracted_text':d.extracted_text[:1500],'verified':d.verified} for d in s.scalars(stmt).all()]

@app.get('/v1/audit')
def audits(limit:int=50,s:Session=Depends(db),u:User=Depends(require('admin','approver','auditor'))):
    if limit<1 or limit>200:raise HTTPException(422,'limit 1..200')
    return [{'id':a.id,'at':str(a.at),'actor':a.actor,'action':a.action,'entity':a.entity,'details':json.loads(a.details)} for a in s.scalars(select(Audit).order_by(Audit.id.desc()).limit(limit)).all()]

@app.get('/v1/dashboard')
def dashboard(s:Session=Depends(db),u:User=Depends(require('admin','operator','reviewer','approver','auditor','lender'))):
    if (not DEMO_MODE or u.role in ('borrower','lender')) and u.role!='admin':
        visible=s.scalars(select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)).all()
        return {'loans':len(visible),'payments':s.scalar(select(func.count()).select_from(Payment).where(Payment.loan_id.in_(visible))),'invoices':s.scalar(select(func.count()).select_from(Invoice).where(Invoice.loan_id.in_(visible))),'open_cases':s.scalar(select(func.count()).select_from(Case).where(Case.loan_id.in_(visible),Case.status!='CLOSED')),'allocations':s.scalar(select(func.count()).select_from(Allocation).where(Allocation.loan_id.in_(visible),Allocation.active==True))}
    return {'loans':s.scalar(select(func.count()).select_from(Loan)),'payments':s.scalar(select(func.count()).select_from(Payment)),'invoices':s.scalar(select(func.count()).select_from(Invoice)),'open_cases':s.scalar(select(func.count()).select_from(Case).where(Case.status!='CLOSED')),'allocations':s.scalar(select(func.count()).select_from(Allocation).where(Allocation.active==True))}

# One-command local demo: backend serves its own static operational UI.
# Reverse-proxy this through the approved HTTPS gateway for a real deployment.
from fastapi.staticfiles import StaticFiles
from backend.v6_routes import router as v6_router
from backend.portal_routes import router as portal_router
app.include_router(v6_router)
app.include_router(portal_router)
app.mount('/', StaticFiles(directory=str(ROOT/'web'), html=True),name='web')
