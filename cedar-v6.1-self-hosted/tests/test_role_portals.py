"""Role isolation: UI separation must be backed by API authorization.
Test with DEVELOPMENT config only. Borrower and lender never inherit demo staff bypass.
"""
import os
os.environ.setdefault('CEDAR_DEMO_MODE','true')
os.environ.setdefault('CEDAR_AUTO_CREATE_SCHEMA','true')
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/cedar_role_isolation_tests.db')
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app import app, Base, engine, SessionLocal, User, ph, LoanAccess

def setup_module(module):
    Base.metadata.create_all(engine)

def test_separate_login_portals_and_backend_boundaries():
    mark='role'+uuid.uuid4().hex[:8]
    pwd='VeryStrongUnique#123456'
    with SessionLocal() as s:
        admin=User(username=mark+'_admin',role='admin',password_hash=ph.hash(pwd))
        lender=User(username=mark+'_lender',role='lender',password_hash=ph.hash(pwd))
        borrower=User(username=mark+'_borrower',role='borrower',password_hash=ph.hash(pwd))
        other=User(username=mark+'_other',role='borrower',password_hash=ph.hash(pwd))
        s.add_all([admin,lender,borrower,other]);s.commit()
    with TestClient(app) as c:
        def session(who):
            r=c.post('/v1/auth/login',json={'username':mark+'_'+who,'password':pwd})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        a=session('admin');b=session('borrower');l=session('lender');o=session('other')
        loan_a=mark+'-LOAN-1';loan_b=mark+'-LOAN-2'
        for id in [loan_a,loan_b]:
            r=c.post('/v1/loans',headers=a,json={'id':id,'borrower':'Synthetic test FPO','principal':'20000.00','permitted_categories':['SEEDS']})
            assert r.status_code==201,r.text
        for user,loan in [('borrower',loan_a),('lender',loan_a),('other',loan_b)]:
            r=c.post('/v1/staff/loan-access',headers=a,json={'username':mark+'_'+user,'loan_id':loan})
            assert r.status_code==201,r.text
        assert c.get('/v1/auth/me',headers=b).json()['portal']['url']=='/borrower.html'
        assert c.get('/v1/auth/me',headers=l).json()['portal']['url']=='/lender.html'
        assert c.get('/v1/auth/me',headers=a).json()['portal']['url']=='/'
        borrower_loans=c.get('/v1/borrower/loans',headers=b)
        assert borrower_loans.status_code==200
        assert {x['id'] for x in borrower_loans.json()}=={loan_a}
        assert {x['id'] for x in c.get('/v1/lender/portfolio',headers=l).json()}=={loan_a}
        # Borrower cannot see the lender's records, even through direct URL calls.
        for endpoint in ['/v1/payments','/v1/invoices','/v1/loans','/v1/dashboard','/v1/cases',
                         '/v1/audit','/v1/journals','/v1/source-batches','/v1/lender/dashboard',
                         '/v1/documents','/v1/allocations',f'/v1/loans/{loan_a}/ledger-reconciliation',
                         f'/v1/loans/{loan_a}/utilization']:
            assert c.get(endpoint,headers=b).status_code==403,endpoint
        for endpoint in [f'/v1/borrower/loans/{loan_b}/documents',
                         f'/v1/borrower/loans/{loan_b}/invoices']:
            assert c.get(endpoint,headers=b).status_code==403
        # Lender can't enter borrower submission workflows or internal staff cases.
        for endpoint in ['/v1/borrower/dashboard','/v1/borrower/loans','/v1/cases','/v1/audit','/v1/admin/users']:
            assert c.get(endpoint,headers=l).status_code==403,endpoint
        for endpoint,payload in [('/v1/journals',{'source':'bank','external_id':'x','loan_id':loan_a,'posting_date':'2026-10-26','lines':[]}),
                                 ('/v1/loans',{'id':mark+'-BAD','borrower':'Bad','principal':'100','permitted_categories':['SEEDS']}),
                                 ('/v1/loans/'+loan_a+'/evaluate',{})]:
            assert c.post(endpoint,headers=l,json=payload).status_code==403,endpoint
        assert c.post('/v1/borrower/loans/'+loan_a+'/invoices',headers=l,json={
            'number':'INV-1','supplier':'ABC','category':'SEEDS','amount':'3000'}).status_code==403
        submit=c.post('/v1/borrower/loans/'+loan_a+'/invoices',headers=b,json={
            'number':'INV-PENDING-101','supplier':'Synthetic supplier','category':'SEEDS','amount':'3000'})
        assert submit.status_code==201,submit.text
        assert submit.json()['status']=='PENDING_VERIFICATION'
        lender_view=c.get('/v1/invoices?loan_id='+loan_a,headers=l)
        assert lender_view.status_code==200
        assert any(x['number']=='INV-PENDING-101' and x['document_verified']==False for x in lender_view.json())
        assert c.get('/v1/invoices?loan_id='+loan_b,headers=l).json()==[]
        assert c.get('/v1/borrower/loans/'+loan_a+'/invoices',headers=o).status_code==403
        # Logout invalidates the token server-side (not just sessionStorage).
        assert c.post('/v1/auth/logout',headers=b).status_code==200
        assert c.get('/v1/borrower/loans',headers=b).status_code==401


def test_admin_can_provision_borrower_but_not_public_signup():
    mark='create'+uuid.uuid4().hex[:8]
    pwd='VeryStrongUnique#123456'
    with SessionLocal() as s:
        admin=User(username=mark+'_admin',role='admin',password_hash=ph.hash(pwd))
        s.add(admin);s.commit()
    with TestClient(app) as c:
        r=c.post('/v1/auth/login',json={'username':mark+'_admin','password':pwd})
        ah={'Authorization':'Bearer '+r.json()['token']}
        loan=mark+'-LOAN'
        assert c.post('/v1/loans',headers=ah,json={'id':loan,'borrower':'Demo','principal':'1000','permitted_categories':['SEEDS']}).status_code==201
        body={'username':mark+'_new','password':pwd,'loan_id':loan}
        assert c.post('/v1/admin/borrowers',json=body).status_code==401
        r=c.post('/v1/admin/borrowers',headers=ah,json=body)
        assert r.status_code==201,r.text
        assert r.json()['role']=='borrower'
        r=c.post('/v1/auth/login',json={'username':body['username'],'password':pwd})
        assert r.status_code==200
        bh={'Authorization':'Bearer '+r.json()['token']}
        assert c.get('/v1/admin/users',headers=bh).status_code==403

def test_role_assignment_revocation_and_document_submission():
    from io import BytesIO
    from PIL import Image
    mark='doc'+uuid.uuid4().hex[:8]
    pwd='VeryStrongUnique#123456'
    with SessionLocal() as s:
        for name,role in [('admin','admin'),('borrower','borrower'),('lender','lender')]:
            s.add(User(username=mark+'_'+name,role=role,password_hash=ph.hash(pwd)))
        s.commit()
    with TestClient(app) as c:
        def login(role):
            r=c.post('/v1/auth/login',json={'username':mark+'_'+role,'password':pwd})
            assert r.status_code==200
            return {'Authorization':'Bearer '+r.json()['token']}
        a,b,l=(login(x) for x in ('admin','borrower','lender'))
        loan=mark+'-LOAN'
        assert c.post('/v1/loans',headers=a,json={'id':loan,'borrower':'Test FPO','principal':'1000','permitted_categories':['SEEDS']}).status_code==201
        for role in ('borrower','lender'):
            assert c.post('/v1/staff/loan-access',headers=a,json={'username':mark+'_'+role,'loan_id':loan}).status_code==201
        img=Image.new('RGB',(100,35),color='white')
        buffer=BytesIO();img.save(buffer,format='PNG')
        posted=c.post('/v1/borrower/loans/'+loan+'/documents',headers=b,files={'file':('proof.png',buffer.getvalue(),'image/png')})
        assert posted.status_code==201,posted.text
        assert posted.json()['status']=='SUBMITTED'
        assert 'extract_preview' not in posted.json()
        d=c.get('/v1/borrower/loans/'+loan+'/documents',headers=b).json()
        assert any(x['filename']=='proof.png' for x in d)
        assert all('extracted_text' not in x for x in d)
        assert c.post('/v1/borrower/loans/'+loan+'/documents',headers=l,files={'file':('other.png',buffer.getvalue(),'image/png')}).status_code==403
        revoked=c.post('/v1/admin/revoke-loan-access',headers=a,json={'username':mark+'_borrower','loan_id':loan})
        assert revoked.status_code==200,revoked.text
        assert c.get('/v1/borrower/loans',headers=b).json()==[]
        assert c.get('/v1/borrower/loans/'+loan+'/documents',headers=b).status_code==403
        assert c.get('/v1/lender/portfolio',headers=l).status_code==200
