import os
from pathlib import Path
# use isolated fixture database, no demo data touched
os.environ['DATABASE_URL']='sqlite:////tmp/cedar_v5_test.db'
os.environ['CEDAR_DEMO_MODE']='true'
try:Path('/tmp/cedar_v5_test.db').unlink()
except FileNotFoundError:pass
from fastapi.testclient import TestClient
from backend.app import app, Base,engine,SessionLocal,User,Loan,ph,Payment,Invoice,Allocation,Audit,Outbox,Doc
from sqlalchemy import select,func
from decimal import Decimal as D
import json
import pytest

@pytest.fixture(scope='module')
def client():
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        for r in ['admin','operator','reviewer','approver','auditor']:
            s.add(User(username=r,role=r,password_hash=ph.hash('pass1234')))
        s.commit()
    with TestClient(app) as c:yield c

@pytest.fixture(scope='module')
def headers(client):
    return {r:{'Authorization':'Bearer '+client.post('/v1/auth/login',json={'username':r,'password':'pass1234'}).json()['token']} for r in ['admin','operator','reviewer','approver','auditor']}

def test_loan_and_auth(client,headers):
    assert client.get('/v1/loans').status_code==401
    assert client.post('/v1/loans',json={'id':'LOAN-X','borrower':'Synthetic FPO','principal':'500000','permitted_categories':['SEEDS']},headers=headers['reviewer']).status_code==403
    r=client.post('/v1/loans',json={'id':'LOAN-X','borrower':'Synthetic FPO','principal':'500000','permitted_categories':['SEEDS']},headers=headers['admin'])
    assert r.status_code==201,r.text

def test_source_batch_and_duplicate(client,headers):
    j={'source':'TEST-LMS','batch_ref':'B1','expected_count':1,'payments':[{'loan_id':'LOAN-X','external_id':'P1','payee':'Supplier A','amount':'250.00'}]}
    r=client.post('/v1/source-batches',json=j,headers=headers['operator'])
    assert r.status_code==201,r.text
    assert r.json()['status']=='COMPLETE'
    assert client.post('/v1/source-batches',json=j,headers=headers['operator']).status_code==409
    j['batch_ref']='B2'
    assert client.post('/v1/source-batches',json=j,headers=headers['operator']).status_code==409

def test_evidence_verify_and_allocation(client,headers):
    inv=client.post('/v1/invoices',headers=headers['operator'],json={'loan_id':'LOAN-X','number':'I1','supplier':'Supplier A','category':'SEEDS','amount':'200.00','document_verified':True,'delivery_verified':True})
    assert inv.status_code==201,inv.text
    iid=inv.json()['id']
    invoice=next(x for x in client.get('/v1/invoices',headers=headers['reviewer']).json() if x['id']==iid)
    assert invoice['document_verified'] is False # prevent trusting operator-submitted flags
    payment=client.get('/v1/payments',headers=headers['reviewer']).json()[0]
    key={'Idempotency-Key':'test-key'} | headers['reviewer']
    body={'payment_id':payment['id'],'invoice_id':iid,'amount':'150.00'}
    assert client.post('/v1/allocations',json=body,headers=key).status_code==409
    verified=client.post(f'/v1/invoices/{iid}/verify',headers=headers['reviewer'],json={'document_verified':True,'delivery_verified':True,'expected_version':invoice['version'],'reason':'Checked original paper'})
    assert verified.status_code==200,verified.text
    r=client.post('/v1/allocations',json=body,headers=key)
    assert r.status_code==201,r.text
    assert client.post('/v1/allocations',json=body,headers=key).json()['id']==r.json()['id']
    assert client.post('/v1/allocations',json={**body,'amount':'10.00'},headers=key).status_code==409
    overflow=client.post('/v1/allocations',json={**body,'amount':'100.00'},headers={**headers['reviewer'],'Idempotency-Key':'other'})
    assert overflow.status_code==409
    p=client.get('/v1/payments',headers=headers['reviewer']).json()[0]
    assert p['allocated']=='150.00'

def test_evaluation_and_reversal(client,headers):
    e=client.post('/v1/loans/LOAN-X/evaluate',headers=headers['reviewer'])
    assert e.status_code==200,e.text
    assert e.json()['supported']=='150.00'
    snap=e.json()['snapshot_id']
    assert client.get('/v1/loans/LOAN-X/utilization',headers=headers['reviewer']).json()['snapshot_id']==snap
    al=client.get('/v1/allocations',headers=headers['reviewer']).json()[0]
    assert client.post('/v1/allocations/'+al['id']+'/reverse',headers=headers['reviewer']).status_code==403
    assert client.post('/v1/allocations/'+al['id']+'/reverse',headers=headers['approver']).status_code==200
    changed=client.get('/v1/loans/LOAN-X/utilization',headers=headers['reviewer']).json()
    assert changed['snapshot_id'] is None and changed['supported']=='0.00'
    assert client.post('/v1/allocations/'+al['id']+'/reverse',headers=headers['approver']).status_code==409

def test_maker_checker_and_audit(client,headers):
    client.post('/v1/loans/LOAN-X/evaluate',headers=headers['reviewer'])
    cases=client.get('/v1/cases',headers=headers['reviewer']).json()
    assert cases
    c=cases[0]
    r=client.post(f"/v1/cases/{c['id']}/actions",headers=headers['reviewer'],json={'action':'propose','expected_version':c['version'],'note':'Investigated supporting records'})
    assert r.status_code==200,r.text
    assert client.post(f"/v1/cases/{c['id']}/actions",headers=headers['reviewer'],json={'action':'approve','expected_version':c['version']+1,'note':'approve'}).status_code==403
    bad=client.post(f"/v1/cases/{c['id']}/actions",headers=headers['approver'],json={'action':'approve','expected_version':c['version'],'note':'approve'})
    assert bad.status_code==409
    good=client.post(f"/v1/cases/{c['id']}/actions",headers=headers['approver'],json={'action':'approve','expected_version':c['version']+1,'note':'Source checked'})
    assert good.status_code==200 and good.json()['status']=='CLOSED'
    assert client.get('/v1/audit',headers=headers['reviewer']).status_code==403
    assert any(x['action']=='ALLOCATION_COMMITTED' for x in client.get('/v1/audit',headers=headers['auditor']).json())
    with SessionLocal() as s:assert s.scalar(select(func.count()).select_from(Outbox))>0

def test_incomplete_source_and_upload(client,headers):
    j={'source':'TEST-LMS','batch_ref':'B3','expected_count':2,'payments':[{'loan_id':'LOAN-X','external_id':'P2','payee':'Supplier B','amount':'500.00'}]}
    assert client.post('/v1/source-batches',json=j,headers=headers['operator']).json()['status']=='INCOMPLETE'
    ev=client.post('/v1/loans/LOAN-X/evaluate',headers=headers['reviewer']).json()
    assert ev['source_complete'] is False and ev['status']=='PROVISIONAL'
    r=client.post('/v1/documents?loan_id=LOAN-X',headers=headers['reviewer'],files={'file':('bad.txt',b'not a pdf','text/plain')})
    assert r.status_code==415
    r=client.post('/v1/documents?loan_id=LOAN-X',headers=headers['reviewer'],files={'file':('invoice.png',b'\x89PNG\r\n\x1a\nnot-a-valid-image','image/png')})
    assert r.status_code==422
