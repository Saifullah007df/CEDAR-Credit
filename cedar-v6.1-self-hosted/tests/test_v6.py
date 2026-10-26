"""Additional v6 regression tests against a real transaction-capable SQLite engine.
PostgreSQL row-level concurrency and Docker must be tested separately before live use.
"""
import os
os.environ.setdefault('CEDAR_DEMO_MODE','true')
os.environ.setdefault('CEDAR_AUTO_CREATE_SCHEMA','true')
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/cedar_v6_extra_test.db')
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app import Base,engine,SessionLocal,User,ph,PolicyVersion,Journal,JournalLine,Outbox,Doc
from backend.worker import handle_one
from PIL import Image
from io import BytesIO
import pytest

@pytest.fixture(scope='module')
def ctx():
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        for role in ['admin','operator','reviewer','approver','auditor']:
            username='v6_'+role
            if not s.scalar(select(User).where(User.username==username)):
                s.add(User(username=username,role=role,password_hash=ph.hash('test-password-1234567!')))
        s.commit()
    with TestClient(__import__('backend.app',fromlist=['app']).app) as c:
        tokens={}
        for role in ['admin','operator','reviewer','approver','auditor']:
            r=c.post('/v1/auth/login',json={'username':'v6_'+role,'password':'test-password-1234567!'})
            assert r.status_code==200, r.text
            tokens[role]={'Authorization':'Bearer '+r.json()['token']}
        yield c,tokens

def test_journal_and_reconciliation(ctx):
    c,h=ctx
    r=c.post('/v1/loans',json={'id':'LOAN-V6','borrower':'Offline Synthetic FPO','principal':'100000',
        'permitted_categories':['SEEDS']},headers=h['admin'])
    assert r.status_code in (201,409),r.text
    incorrect={'source':'OFFLINE-GL','external_id':'J-V6-1','loan_id':'LOAN-V6','posting_date':'2026-10-26',
        'journal_type':'DISBURSEMENT','lines':[{'account':'LOAN_RECEIVABLE','debit':'100000','credit':'0'},
        {'account':'BANK_CASH','debit':'0','credit':'99000'}]}
    assert c.post('/v1/journals',json=incorrect,headers=h['operator']).status_code==422
    correct={**incorrect,'lines':[incorrect['lines'][0],{'account':'BANK_CASH','debit':'0','credit':'100000'}]}
    r=c.post('/v1/journals',json=correct,headers=h['operator'])
    assert r.status_code==201,r.text
    assert r.json()['status']=='BALANCED'
    assert c.post('/v1/journals',json=correct,headers=h['operator']).status_code==409
    report=c.get('/v1/loans/LOAN-V6/ledger-reconciliation',headers=h['auditor']).json()
    assert report['journal_count']==1 and report['debit_total']=='100000.00'
    assert report['status']=='RECONCILED_WITH_IMPORTED_JOURNALS'

def test_offline_csv_and_xlsx_ingestion(ctx):
    c,h=ctx
    csv_data=b'loan_id,external_id,payee,amount\nLOAN-V6,TX-V6-1,Seed Supplier,20000.00\n'
    r=c.post('/v1/imports/financial-file?source=OFFLINE-BANK&batch_ref=CSV-V6&expected_count=1',
        headers=h['operator'],files={'file':('bank.csv',csv_data,'text/csv')})
    assert r.status_code==201,r.text
    assert r.json()['status']=='COMPLETE'
    assert c.post('/v1/imports/financial-file?source=OFFLINE-BANK&batch_ref=CSV-V6&expected_count=1',
        headers=h['operator'],files={'file':('bank.csv',csv_data,'text/csv')}).status_code==409
    from openpyxl import Workbook
    book=Workbook();sheet=book.active
    sheet.append(['loan_id','external_id','payee','amount'])
    sheet.append(['LOAN-V6','TX-V6-2','Seed Supplier','5000.00'])
    output=BytesIO();book.save(output)
    r=c.post('/v1/imports/financial-file?source=OFFLINE-BANK&batch_ref=XLS-V6&expected_count=1',
        headers=h['operator'],files={'file':('bank.xlsx',output.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert r.status_code==201,r.text

def test_policy_and_document_correction(ctx):
    c,h=ctx
    p=c.post('/v1/loans/LOAN-V6/policies',headers=h['approver'],json={
        'categories':['SEEDS','IRRIGATION'], 'effective_date':'2026-10-26', 'reason':'Approved internal policy'} )
    assert p.status_code==201,p.text
    assert p.json()['version']>=1
    assert c.get('/v1/loans/LOAN-V6/policies',headers=h['reviewer']).json()[-1]['categories']==['IRRIGATION','SEEDS']
    img=Image.new('RGB',(130,50),color='white')
    buf=BytesIO();img.save(buf,format='PNG')
    r=c.post('/v1/documents?loan_id=LOAN-V6',headers=h['reviewer'],files={'file':('scan.png',buf.getvalue(),'image/png')})
    assert r.status_code==201,r.text
    docid=r.json()['id']
    r=c.post(f'/v1/documents/{docid}/corrections',headers=h['reviewer'],json={
        'expected_version':1,'corrected_text':'Invoice amount INR 20000','reason':'Checked original source file'})
    assert r.status_code==200,r.text
    assert r.json()['original_ocr_unchanged']
    assert c.post(f'/v1/documents/{docid}/corrections',headers=h['reviewer'],json={
        'expected_version':1,'corrected_text':'Wrong stale correction','reason':'Stale request'}).status_code==409
    history=c.get(f'/v1/documents/{docid}/history',headers=h['auditor']).json()
    assert history['current_version']==2 and len(history['corrections'])==1

def test_worker_refreshes_and_staff_controls(ctx):
    c,h=ctx
    for _ in range(40):
        if not handle_one():break
    r=c.get('/v1/loans/LOAN-V6/utilization',headers=h['reviewer'])
    assert r.status_code==200 and r.json()['snapshot_id'] is not None, r.text
    status=c.get('/v1/operations/status',headers=h['operator'])
    assert status.status_code==200
    assert status.json()['outbound_financial_apis'] is False
    assert c.post('/v1/staff',headers=h['reviewer'],json={
        'username':'new_operator_v6','password':'VeryStrongNewPassword#123','role':'operator'}).status_code==403
    add=c.post('/v1/staff',headers=h['admin'],json={
        'username':'new_operator_v6','password':'VeryStrongNewPassword#123','role':'operator'})
    assert add.status_code in (201,409),add.text
