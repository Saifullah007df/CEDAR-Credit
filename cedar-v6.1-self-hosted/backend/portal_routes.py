"""Role-separated, locally hosted borrower/lender portals.
No third-party APIs. Permissions are enforced server-side on every route.
Borrowers are provisioned by administrators and linked to their own loan IDs.
"""
import json
from decimal import Decimal
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app import (
    User, Loan, LoanAccess, Invoice, Doc, Case, Payment, Allocation,
    db, require, user_from_header, ensure_loan_scope, need_loan, money, ds, uid,
    audit, outbox, touch, ph, DEMO_MODE, upload_document, calculate,
)

router = APIRouter(prefix='/v1')

PORTALS = {
    'borrower': {'name':'Borrower / FPO Portal','url':'/borrower.html','modules':['My loans','Submit invoice','Upload documents','Evidence status']},
    'lender': {'name':'Lender Workspace','url':'/lender.html','modules':['Assigned portfolio','Loan performance','Evidence overview','Reconciliation summary']},
    'operator': {'name':'Finance Operations','url':'/','modules':['Overview','Ledger','Utilization']},
    'reviewer': {'name':'Evidence Review','url':'/','modules':['Overview','Evidence','Utilization','Review']},
    'approver': {'name':'Approval Workspace','url':'/','modules':['Overview','Review','Audit']},
    'auditor': {'name':'Audit Workspace','url':'/','modules':['Overview','Ledger','Utilization','Audit']},
    'admin': {'name':'Platform Administration','url':'/','modules':['Overview','Ledger','Evidence','Utilization','Review','Audit','Access']},
}

@router.get('/auth/me')
def whoami(u:User=Depends(user_from_header),s:Session=Depends(db)):
    visible = s.scalars(select(LoanAccess.loan_id).where(LoanAccess.user_id == u.id)).all()
    return {'username':u.username,'role':u.role,'portal':PORTALS.get(u.role,PORTALS['auditor']),
        'assigned_loan_ids':visible,'mfa_enabled':bool(u.totp_secret)}

@router.post('/auth/logout')
def logout(u:User=Depends(user_from_header),s:Session=Depends(db)):
    u.token_version=(u.token_version or 0)+1
    audit(s,u.username,'SESSIONS_REVOKED',u.id,{'reason':'logout'})
    s.commit()
    return {'status':'signed_out'}

# Borrower-specific APIs expose no staff scoring, payee lists, case notes or internal audit.
@router.get('/borrower/dashboard')
def borrower_dashboard(u:User=Depends(require('borrower')),s:Session=Depends(db)):
    loan_ids=s.scalars(select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)).all()
    docs=s.scalar(select(func.count()).select_from(Doc).where(Doc.loan_id.in_(loan_ids))) or 0
    invoices=s.scalar(select(func.count()).select_from(Invoice).where(Invoice.loan_id.in_(loan_ids))) or 0
    verified=s.scalar(select(func.count()).select_from(Doc).where(Doc.loan_id.in_(loan_ids),Doc.verified==True)) or 0
    return {'loan_count':len(loan_ids),'uploaded_documents':docs,'submitted_invoices':invoices,
            'reviewed_documents':verified,'disclaimer':'Evidence submitted is not automatic lender approval.'}

@router.get('/borrower/loans')
def borrower_loans(u:User=Depends(require('borrower')),s:Session=Depends(db)):
    ids=select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)
    loans=s.scalars(select(Loan).where(Loan.id.in_(ids)).order_by(Loan.id)).all()
    return [{'id':l.id,'borrower':l.borrower,'principal':ds(l.principal),
             'permitted_categories':json.loads(l.permitted_categories),
             'status':'EVIDENCE_COLLECTION',
             'notice':'This is a document tracking status, not a lender approval or live balance.'} for l in loans]

@router.get('/borrower/loans/{loan_id}/documents')
def borrower_documents(loan_id:str,u:User=Depends(require('borrower')),s:Session=Depends(db)):
    ensure_loan_scope(s,u,loan_id)
    return [{'id':d.id,'filename':d.filename,'verified':d.verified,'status':'REVIEWED' if d.verified else 'SUBMITTED',
             'version':d.version} for d in s.scalars(select(Doc).where(Doc.loan_id==loan_id).order_by(Doc.filename))]

@router.post('/borrower/loans/{loan_id}/documents',status_code=201)
async def borrower_upload(loan_id:str,file:UploadFile=File(...),u:User=Depends(require('borrower')),s:Session=Depends(db)):
    ensure_loan_scope(s,u,loan_id)
    result=await upload_document(loan_id=loan_id,file=file,s=s,u=u)
    # Do not disclose machine-extracted identifiers/text back to the borrower in this endpoint.
    return {'id':result['id'],'status':'SUBMITTED','message':'Document received for authorized verification.'}

class BorrowerInvoice(BaseModel):
    number:str=Field(min_length=1,max_length=80)
    supplier:str=Field(min_length=2,max_length=180)
    category:str=Field(min_length=2,max_length=80)
    amount:str

@router.get('/borrower/loans/{loan_id}/invoices')
def borrower_invoices(loan_id:str,u:User=Depends(require('borrower')),s:Session=Depends(db)):
    ensure_loan_scope(s,u,loan_id)
    return [{'id':i.id,'number':i.number,'supplier':i.supplier,'category':i.category,
             'amount':ds(i.amount),'status':'REVIEWED' if i.document_verified else 'PENDING_VERIFICATION'}
            for i in s.scalars(select(Invoice).where(Invoice.loan_id==loan_id).order_by(Invoice.number))]

@router.post('/borrower/loans/{loan_id}/invoices',status_code=201)
def borrower_submit_invoice(loan_id:str,body:BorrowerInvoice,u:User=Depends(require('borrower')),s:Session=Depends(db)):
    ensure_loan_scope(s,u,loan_id)
    loan=need_loan(s,loan_id)
    inv=Invoice(loan_id=loan_id,number=body.number.strip(),supplier=body.supplier.strip(),
        category=body.category.strip().upper(),amount=money(body.amount),allocated=0,
        document_verified=False,delivery_verified=False)
    s.add(inv);s.flush();touch(s,loan)
    audit(s,u.username,'BORROWER_INVOICE_SUBMITTED',inv.id,{'loan_id':loan_id})
    outbox(s,'BorrowerInvoiceSubmitted',inv.id,{'loan_id':loan_id})
    s.commit()
    return {'id':inv.id,'status':'PENDING_VERIFICATION','message':'Invoice recorded but not verified.'}

# Lender staff can see only the loans explicitly granted to their account.
# This is a read-only portal; independent reviewer/finance permissions are separate roles.
@router.get('/lender/dashboard')
def lender_dashboard(u:User=Depends(require('lender')),s:Session=Depends(db)):
    ids=select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)
    loans=s.scalars(select(Loan).where(Loan.id.in_(ids)).order_by(Loan.id)).all()
    case_total=s.scalar(select(func.count()).select_from(Case).where(Case.loan_id.in_(ids),Case.status!='CLOSED')) or 0
    return {'assigned_loans':len(loans),'open_exceptions':case_total,
        'total_contractual_principal':ds(sum((l.principal for l in loans),start=Decimal('0'))),
        'notice':'Based on imported records; not a live authoritative outstanding balance.'}

@router.get('/lender/portfolio')
def lender_portfolio(u:User=Depends(require('lender')),s:Session=Depends(db)):
    ids=select(LoanAccess.loan_id).where(LoanAccess.user_id==u.id)
    loans=s.scalars(select(Loan).where(Loan.id.in_(ids)).order_by(Loan.id)).all()
    response=[]
    for loan in loans:
        result=calculate(s,loan)
        response.append({'id':loan.id,'borrower':loan.borrower,'principal':ds(loan.principal),
            'observed_payments':result['observed_payments'],'supported':result['supported'],
            'incomplete':result['incomplete'],'unallocated':result['unallocated'],
            'assessment_status':result['status'],'version':loan.version})
    return response

class BorrowerProvision(BaseModel):
    username:str=Field(min_length=3,max_length=80,pattern=r'^[a-zA-Z0-9._-]+$')
    password:str=Field(min_length=16,max_length=256)
    loan_id:str

@router.post('/admin/borrowers',status_code=201)
def provision_borrower(body:BorrowerProvision,u:User=Depends(require('admin')),s:Session=Depends(db)):
    from sqlalchemy import select
    if s.scalar(select(User).where(User.username==body.username)):
        raise HTTPException(409,'Username already in use')
    if len(set(body.password))<8:
        raise HTTPException(422,'Password lacks sufficient character variety')
    need_loan(s,body.loan_id)
    user=User(username=body.username,role='borrower',password_hash=ph.hash(body.password))
    s.add(user);s.flush()
    s.add(LoanAccess(user_id=user.id,loan_id=body.loan_id))
    audit(s,u.username,'BORROWER_PROVISIONED',user.id,{'loan_id':body.loan_id})
    s.commit()
    return {'id':user.id,'username':user.username,'role':'borrower','assigned_loan_id':body.loan_id}

@router.get('/admin/users')
def list_users(u:User=Depends(require('admin')),s:Session=Depends(db)):
    users=s.scalars(select(User).order_by(User.username)).all()
    return [{'id':v.id,'username':v.username,'role':v.role,
             'assigned_loans':s.scalars(select(LoanAccess.loan_id).where(LoanAccess.user_id==v.id)).all(),
             'mfa_enabled':bool(v.totp_secret)} for v in users]

class RevokeLoanGrant(BaseModel):
    username:str
    loan_id:str

@router.post('/admin/revoke-loan-access')
def revoke_loan_grant(body:RevokeLoanGrant,u:User=Depends(require('admin')),s:Session=Depends(db)):
    target=s.scalar(select(User).where(User.username==body.username))
    if not target:raise HTTPException(404,'User not found')
    grant=s.get(LoanAccess,{'user_id':target.id,'loan_id':body.loan_id})
    if not grant:raise HTTPException(404,'Grant not found')
    s.delete(grant)
    audit(s,u.username,'LOAN_ACCESS_REVOKED',body.loan_id,{'username':body.username})
    s.commit()
    return {'username':body.username,'loan_id':body.loan_id,'assigned':False}
