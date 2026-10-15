import { useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowLeft, ArrowRight, Building2, ClipboardList, FileCheck2, Plus, Wallet } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { DataState, Empty, Feedback, FormField, Metric, Notice,
  PageTitle, Panel, StatePill, Submit, money, useAction, useLoad } from '../components/Shared';
import type { Evidence, Evaluation, Lender, LenderPolicy, LoanApplication, LoanProduct,
  SimulatedLoan } from '../lib/types';

export function AdminDashboard() {
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const apps=useLoad<LoanApplication[]>('/api/v1/applications');
  const loans=useLoad<SimulatedLoan[]>('/api/v1/loans');
  const reviews=useLoad<{id:number}[]>('/api/v1/review/tasks');
  return <>
    <PageTitle eyebrow="PLATFORM ADMINISTRATION" title="Marketplace overview"
      description="Monitor fictional lender configuration, application decisions and human verification."
      action={<Link className="btn btn-primary" to="/admin/lenders"><Plus size={16}/> Manage lenders</Link>}/>
    <div className="metric-row">
      <Metric label="Fictional lenders" value={lenders.data?.length??'—'} note="Configured in the system"/>
      <Metric label="Loan applications" value={apps.data?.length??'—'} note="Synthetic requests"/>
      <Metric label="Open review tasks" value={reviews.data?.length??'—'} note="Awaiting source verification"/>
      <Metric label="Mock loans" value={loans.data?.length??'—'} note="Simulated only"/>
    </div>
    <div className="panel-grid">
      <Link className="quick-card" to="/admin/lenders"><Building2 size={25}/><h3>Manage lenders</h3><p>Add fictional lenders, products, and versioned policies.</p><ArrowRight size={18}/></Link>
      <Link className="quick-card" to="/admin/applications"><ClipboardList size={25}/><h3>Applications</h3><p>Run rules across lenders and generate provisional offers.</p><ArrowRight size={18}/></Link>
      <Link className="quick-card" to="/review"><FileCheck2 size={25}/><h3>Human review</h3><p>Prioritize uncertain evidence and verify corrections.</p><ArrowRight size={18}/></Link>
      <Link className="quick-card" to="/admin/loans"><Wallet size={25}/><h3>Loan servicing</h3><p>Record mock disbursement and repayment activity.</p><ArrowRight size={18}/></Link>
    </div>
    <Notice>Role permissions are checked by FastAPI. This portal does not access real bank systems or process money.</Notice>
  </>;
}

export function AdminLenders() {
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const products=useLoad<LoanProduct[]>('/api/v1/products');
  const {execute,busy,error,success}=useAction();
  const [newName,setNewName]=useState('');
  const [targetLender,setTargetLender]=useState('');
  const [productName,setProductName]=useState('FPO Crop Loan');
  const [min,setMin]=useState('100000');
  const [max,setMax]=useState('1000000');
  const [apr,setApr]=useState('11');
  const [field,setField]=useState('turnover');
  const [operator,setOperator]=useState('gte');
  const [threshold,setThreshold]=useState('1500000');
  const [userEmail,setUserEmail]=useState('');
  const [userPassword,setUserPassword]=useState('');

  function selectedId(){return Number(targetLender||lenders.data?.[0]?.id||0);}
  async function createLender(e:FormEvent) {
    e.preventDefault();
    const r=await execute('POST','/api/v1/admin/lenders',{name:newName},'Fictional lender created.');
    if(r){setNewName('');lenders.refresh();}
  }
  async function createProduct(e:FormEvent){
    e.preventDefault();
    const r=await execute('POST','/api/v1/admin/lenders/'+selectedId()+'/products',
      {name:productName,min_amount:Number(min),max_amount:Number(max),apr:Number(apr)},'Loan product created.');
    if(r)products.refresh();
  }
  async function publishPolicy(e:FormEvent){
    e.preventDefault();
    let target:unknown;
    try{target=JSON.parse(threshold);}catch{target=threshold;}
    const r=await execute('POST','/api/v1/admin/lenders/'+selectedId()+'/policies',
      {rules:[{field_key:field,operator,target,required:true}]},'New versioned lender policy published.');
    if(r)lenders.refresh();
  }
  async function createLenderUser(e:FormEvent){
    e.preventDefault();
    const r=await execute('POST','/api/v1/admin/lenders/'+selectedId()+'/users',
      {email:userEmail,password:userPassword},'Lender administrator account created.');
    if(r){setUserEmail('');setUserPassword('');}
  }
  const lenderSelector=<FormField label="Fictional lender"><select value={targetLender}
    onChange={e=>setTargetLender(e.target.value)} required>
    {lenders.data?.length ? lenders.data.map(l=><option key={l.id} value={l.id}>{l.name}</option>)
      : <option value="">No lenders configured</option>}
  </select></FormField>;
  return <>
    <PageTitle eyebrow="PLATFORM ADMIN / LENDERS" title="Manage fictional lenders"
      description="Create lending institutions, define product ranges, and publish immutable policy versions."/>
    <div className="portal-columns">
      <Panel title="Registered fictional lenders">
        <DataState state={lenders}>{rows=>rows.length===0
          ? <Empty title="No lenders configured" description="Create a fictional lender below."/>
          : <div className="item-list">{rows.map(l=><div key={l.id} className="list-entry">
            <span className="entry-icon"><Building2 size={18}/></span>
            <span className="entry-main"><strong>{l.name}</strong><small>Lender #{l.id}</small></span>
            <StatePill value="active"/>
          </div>)}</div>}</DataState>
      </Panel>
      <Panel title="Existing loan products">
        <DataState state={products}>{rows=>rows.length===0
          ? <Empty title="No products" description="Add a product below."/>
          : <div className="item-list">{rows.map(p=><div className="list-entry" key={p.id}>
            <span className="entry-main"><strong>{p.name}</strong>
              <small>Lender #{p.lender_id} · APR {p.apr}% · {money(p.min_amount)}–{money(p.max_amount)}</small></span>
          </div>)}</div>}</DataState>
      </Panel>
    </div>
    <div className="portal-columns">
      <Panel title="Add fictional lender">
        <form className="form-stack" onSubmit={createLender}>
          <FormField label="Institution name"><input required value={newName}
            onChange={e=>setNewName(e.target.value)} placeholder="e.g. Demo Agricultural Bank"/></FormField>
          <Submit busy={busy}>Create lender</Submit>
        </form>
      </Panel>
      <Panel title="Add a loan product">
        <form className="form-stack" onSubmit={createProduct}>
          {lenderSelector}
          <FormField label="Product name"><input value={productName} required onChange={e=>setProductName(e.target.value)}/></FormField>
          <div className="form-two">
            <FormField label="Minimum INR"><input type="number" required min="1" value={min} onChange={e=>setMin(e.target.value)}/></FormField>
            <FormField label="Maximum INR"><input type="number" required min="1" value={max} onChange={e=>setMax(e.target.value)}/></FormField>
          </div>
          <FormField label="Simulated annual APR (%)"><input required min="0" max="100" type="number"
            value={apr} onChange={e=>setApr(e.target.value)}/></FormField>
          <Submit busy={busy}>Add product</Submit>
        </form>
      </Panel>
      <Panel title="Publish a policy version" sub="This replaces the active policy; historical versions remain accessible.">
        <form className="form-stack" onSubmit={publishPolicy}>
          {lenderSelector}
          <FormField label="Evidence field"><input required pattern="[a-z][a-z0-9_]*" value={field}
            onChange={e=>setField(e.target.value)}/></FormField>
          <div className="form-two">
            <FormField label="Operator"><select value={operator} onChange={e=>setOperator(e.target.value)}>
              {['gte','gt','lte','lt','eq','neq','in'].map(x=><option key={x}>{x}</option>)}
            </select></FormField>
            <FormField label="Target (JSON value)"><input required value={threshold}
              onChange={e=>setThreshold(e.target.value)}/></FormField>
          </div>
          <Submit busy={busy}>Publish policy</Submit>
        </form>
      </Panel>
      <Panel title="Provision lender administrator" sub="Only platform administrators can create lender-staff accounts.">
        <form className="form-stack" onSubmit={createLenderUser}>
          {lenderSelector}
          <FormField label="Email address"><input type="email" required value={userEmail}
            onChange={e=>setUserEmail(e.target.value)}/></FormField>
          <FormField label="Temporary password (12+ chars)"><input type="password" minLength={12}
            required value={userPassword} onChange={e=>setUserPassword(e.target.value)}/></FormField>
          <Submit busy={busy}>Create account</Submit>
        </form>
      </Panel>
    </div>
    <Feedback error={error} success={success}/>
  </>;
}

export function AdminApplications() {
  const state=useLoad<LoanApplication[]>('/api/v1/applications');
  return <>
    <PageTitle eyebrow="PLATFORM ADMIN / APPLICATIONS" title="Application management"
      description="Review synthetic loan requests and their preliminary lending-rule decisions."/>
    <Panel><DataState state={state}>{items=>items.length===0
      ? <Empty title="No applications yet" description="A borrower must submit an application first."/>
      : <div className="data-table-wrap"><table className="data-table"><thead><tr>
        <th>ID</th><th>Borrower profile</th><th>Loan purpose</th><th>Amount</th><th>Status</th><th></th>
      </tr></thead><tbody>{items.map(a=><tr key={a.id}>
        <td>#{a.id}</td><td>{a.borrower_id===undefined?'Restricted':'#'+a.borrower_id}</td>
        <td>{a.loan_purpose}</td><td>{money(a.requested_amount)}</td>
        <td><StatePill value={a.status}/></td>
        <td><Link className="action-link" to={'/admin/applications/'+a.id}>Inspect <ArrowRight size={15}/></Link></td>
      </tr>)}</tbody></table></div>}</DataState>
    </Panel>
  </>;
}

export function AdminApplicationDetail() {
  const {id}=useParams();
  const appId=Number(id);
  const application=useLoad<LoanApplication>('/api/v1/applications/'+appId);
  const evidences=useLoad<Evidence[]>('/api/v1/applications/'+appId+'/evidence');
  const evaluations=useLoad<Evaluation[]>('/api/v1/applications/'+appId+'/evaluations');
  const products=useLoad<LoanProduct[]>('/api/v1/products');
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const {execute,busy,error,success}=useAction();
  const [evaluationId,setEvaluationId]=useState('');
  const [productId,setProductId]=useState('');
  const [lastResult,setLastResult]=useState<unknown>(null);

  async function evaluate(){
    const result=await execute('POST','/api/v1/applications/'+appId+'/evaluate',{},
      'Preliminary lender rules evaluated.');
    if(result){setLastResult(result);evaluations.refresh();}
  }
  async function schedule(){
    const result=await execute('POST','/api/v1/applications/'+appId+'/schedule-review',{},
      'Unverified evidence considered for the review queue.');
    if(result)setLastResult(result);
  }
  async function offer(e:FormEvent){
    e.preventDefault();
    const result=await execute('POST','/api/v1/applications/'+appId+'/offers',
      {evaluation_id:Number(evaluationId),product_id:Number(productId)},
      'Simulated, nonbinding offer created.');
    if(result)setLastResult(result);
  }
  const current=evaluations.data?.filter(x=>x.current)||[];
  const eligible=current.filter(x=>x.decision==='PASS'&&x.stable===true);
  const selected=eligible.find(x=>x.id===Number(evaluationId))||eligible[0];
  const matching=products.data?.filter(p=>p.lender_id===selected?.lender_id) || [];
  return <>
    <Link to="/admin/applications" className="back-link"><ArrowLeft size={16}/> All applications</Link>
    <DataState state={application}>{a=><PageTitle eyebrow="PLATFORM ADMIN / APPLICATION"
      title={'Application #'+a.id} description={a.loan_purpose+' · '+money(a.requested_amount)}
      action={<StatePill value={a.status}/>}/>}</DataState>
    <div className="portal-columns">
      <Panel title="Evidence status">
        <DataState state={evidences}>{items=>items.length===0
          ? <Empty title="No evidence" description="The borrower has not provided any facts."/>
          : <div className="item-list">{items.map(x=><div className="list-entry" key={x.id}>
            <span className="entry-main"><strong>{x.key}</strong>
              <small>Value: {String(x.value)} · v{x.version} · {x.candidates.length} alternatives</small></span>
            <StatePill value={x.verified?'verified':'unverified'}/></div>)}</div>}</DataState>
      </Panel>
      <Panel title="Decision actions" sub="Results are provisional rules outputs; never lender approvals.">
        <div className="action-stack">
          <button className="btn btn-primary" disabled={busy} onClick={()=>void evaluate()}>Evaluate all active lender policies</button>
          <button className="btn btn-secondary" disabled={busy} onClick={()=>void schedule()}>Schedule evidence review</button>
          <Link to="/review" className="action-link">Open reviewer queue <ArrowRight size={15}/></Link>
        </div>
      </Panel>
    </div>
    <Panel title="Lender decisions" sub="Current evaluations, evidence versions and executed rules">
      <DataState state={evaluations}>{items=>items.length===0
        ? <Empty title="No lender checks yet" description="Select Evaluate all active lender policies above."/>
        : <div className="item-list">{items.map(ev=><div className="decision-row" key={ev.id}>
          <div><strong>{lenders.data?.find(l=>l.id===ev.lender_id)?.name||'Lender #'+ev.lender_id}
            {' · Evaluation #'+ev.id}</strong>
            <small>{ev.current?'Current':'Historical'} · Policy #{ev.policy_id} · Evidence {JSON.stringify(ev.evidence_versions)}</small>
            <div className="decision-rules">{ev.rules.map(r=><span key={r.rule_id}>{r.explanation}</span>)}</div>
          </div><div className="decision-tags"><StatePill value={ev.decision}/>
            <StatePill value={ev.stable===null?'Unknown':ev.stable?'Stable':'Unstable'}/></div>
        </div>)}</div>}</DataState>
    </Panel>
    <Panel title="Create a nonbinding simulated offer" sub="Only current, stable PASS evaluations with verified evidence qualify.">
      {eligible.length===0 ? <Empty title="No qualifying preliminary evaluation"
        description="All mandatory evidence must be verified before issuing a provisional demo offer."/>
        : <form className="form-stack max-form" onSubmit={offer}>
          <FormField label="Eligible evaluation"><select required value={evaluationId||String(selected?.id||'')}
            onChange={e=>{setEvaluationId(e.target.value);setProductId('');}}>
            {eligible.map(ev=><option key={ev.id} value={ev.id}>
              {lenders.data?.find(l=>l.id===ev.lender_id)?.name||'Lender '+ev.lender_id} — Evaluation #{ev.id}
            </option>)}
          </select></FormField>
          <FormField label="Matching loan product"><select required value={productId}
            onChange={e=>setProductId(e.target.value)}>
            <option value="">Choose a product</option>
            {matching.map(p=><option key={p.id} value={p.id}>{p.name} · APR {p.apr}%</option>)}
          </select></FormField>
          <Notice>Offer creation may still be rejected if mandatory evidence is not independently verified or the amount falls outside the product range.</Notice>
          <Submit busy={busy}>Create provisional mock offer</Submit>
        </form>}
    </Panel>
    <Feedback error={error} success={success}/>
    {lastResult!==null&&<Panel title="Latest operation result"><pre className="result-json">{JSON.stringify(lastResult,null,2)}</pre></Panel>}
  </>;
}

export function AdminLoans() {
  const loans=useLoad<SimulatedLoan[]>('/api/v1/loans');
  const {execute,busy,error,success}=useAction();
  const [paymentByLoan,setPaymentByLoan]=useState<Record<number,string>>({});
  async function disburse(id:number){
    const result=await execute('POST','/api/v1/loans/'+id+'/mock-disburse',{},
      'Mock disbursement recorded. No money transferred.');
    if(result)loans.refresh();
  }
  async function repay(id:number){
    const amount=Number(paymentByLoan[id]);
    if(!Number.isFinite(amount)||amount<=0)return;
    const result=await execute('POST','/api/v1/loans/'+id+'/mock-repayments',
      {amount},'Simulated repayment recorded.');
    if(result)loans.refresh();
  }
  return <>
    <PageTitle eyebrow="PLATFORM ADMIN / SERVICING" title="Mock loan servicing"
      description="Disbursement, repayment and outstanding balances are recorded as simulations only."/>
    <Panel>
      <DataState state={loans}>{rows=>rows.length===0
        ? <Empty title="No accepted mock loans" description="A borrower must accept a provisional demo offer before servicing begins."/>
        : <div className="item-list">{rows.map(l=><div className="servicing-row" key={l.id}>
          <div className="servicing-info"><strong>Loan #{l.id} · {money(l.amount)}</strong>
            <small>Application #{l.application_id} · Lender #{l.lender_id} · {l.apr}% APR</small>
            <StatePill value={l.status}/></div>
          <div className="servicing-actions">{l.status==='accepted'&&<button className="btn btn-primary btn-sm"
            disabled={busy} onClick={()=>void disburse(l.id)}>Record mock disbursement</button>}
            {l.status==='mock_disbursed'&&<>
              <input aria-label={'Repayment amount for loan '+l.id} type="number" min="1" placeholder="Demo repayment INR"
                value={paymentByLoan[l.id]||''} onChange={e=>setPaymentByLoan(x=>({...x,[l.id]:e.target.value}))}/>
              <button className="btn btn-primary btn-sm" disabled={busy||!paymentByLoan[l.id]}
                onClick={()=>void repay(l.id)}>Record payment</button>
            </>}</div>
        </div>)}</div>}</DataState>
    </Panel>
    <Feedback error={error} success={success}/>
    <Notice>These records are educational demonstrations, not banking transfers, obligations or regulated servicing activity.</Notice>
  </>;
}
