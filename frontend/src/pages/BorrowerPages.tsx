import { useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, FileUp, Plus, Sprout } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useSession } from '../lib/session';
import { DataState, Empty, ErrorBanner, Feedback, FormField, Metric, Notice,
  PageTitle, Panel, StatePill, Submit, formatDate, money, useAction, useLoad } from '../components/Shared';
import type { Counterfactual, Document, Evidence, Evaluation, Installment,
  LoanApplication, LoanOffer, SimulatedLoan, UtilizationClaim } from '../lib/types';

export function BorrowerDashboard() {
  const applications = useLoad<LoanApplication[]>('/api/v1/applications');
  const loans = useLoad<SimulatedLoan[]>('/api/v1/loans');
  return <>
    <PageTitle eyebrow="BORROWER WORKSPACE" title="Your agricultural credit, clearly organized"
      description="Track applications, evidence and mock loan activity in one secure place."
      action={<Link className="btn btn-primary" to="/borrower/apply"><Plus size={17}/> New application</Link>}/>
    <div className="metric-row">
      <Metric label="My applications" value={applications.data?.length ?? '—'} note="Submitted to the sandbox"/>
      <Metric label="Active demo loans" value={loans.data?.length ?? '—'} note="Simulated contracts only"/>
      <Metric label="Requested credit" value={applications.data
        ? money(applications.data.reduce((n, a) => n + Number(a.requested_amount), 0)) : '—'}/>
    </div>
    <Panel title="Recent applications" sub="Live records from your borrower account"
      action={<Link className="action-link" to="/borrower/applications">See all <ArrowRight size={16}/></Link>}>
      <DataState state={applications}>{apps => apps.length === 0
        ? <Empty title="Start your first application" description="Create a fictional loan application and review lender evidence rules." href="/borrower/apply" action="Apply now"/>
        : <div className="item-list">{apps.slice(0,5).map(a =>
          <Link key={a.id} className="list-entry" to={'/borrower/applications/' + a.id}>
            <span className="entry-icon"><Sprout size={20}/></span>
            <span className="entry-main"><strong>Application #{a.id}</strong><small>{a.loan_purpose}</small></span>
            <strong>{money(a.requested_amount)}</strong><StatePill value={a.status}/><ArrowRight size={17}/>
          </Link>)}</div>}</DataState>
    </Panel>
    <Notice>All lender matching is preliminary. This research system does not approve loans or transfer funds.</Notice>
  </>;
}

export function BorrowerApplications() {
  const state = useLoad<LoanApplication[]>('/api/v1/applications');
  return <>
    <PageTitle eyebrow="BORROWER / APPLICATIONS" title="My applications"
      description="Choose an application to see its documents, evidence, lender decisions and offers."
      action={<Link className="btn btn-primary" to="/borrower/apply"><Plus size={17}/> Apply for loan</Link>}/>
    <Panel>
      <DataState state={state}>{items => items.length === 0
        ? <Empty title="No loan applications" description="Your applications will appear here." href="/borrower/apply" action="Create application"/>
        : <div className="data-table-wrap"><table className="data-table"><thead><tr>
            <th>Application</th><th>Purpose</th><th>Amount</th><th>Status</th><th></th>
          </tr></thead><tbody>{items.map(a => <tr key={a.id}>
            <td><strong>#{a.id}</strong></td><td>{a.loan_purpose}</td>
            <td>{money(a.requested_amount)}</td><td><StatePill value={a.status}/></td>
            <td><Link className="action-link" to={'/borrower/applications/' + a.id}>Open <ArrowRight size={15}/></Link></td>
          </tr>)}</tbody></table></div>}</DataState>
    </Panel>
  </>;
}

export function ApplyLoan() {
  const { identity } = useSession();
  const { execute, busy, error } = useAction();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [amount, setAmount] = useState('500000');
  const [purpose, setPurpose] = useState('Seeds and fertilizer');
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (step < 3) { setStep(s => s + 1); return; }
    const result = await execute<{ id: number }>('POST', '/api/v1/applications',
      { requested_amount: Number(amount), loan_purpose: purpose });
    if (result) navigate('/borrower/applications/' + result.id);
  }
  return <>
    <PageTitle eyebrow="BORROWER / NEW APPLICATION" title="Apply for agricultural credit"
      description="Three simple steps. After submission you can attach documents and evidence."/>
    <div className="steps">{['Loan details','Borrower profile','Confirm'].map((name, index) =>
      <div className={'step ' + (step >= index+1 ? 'done' : '')} key={name}>
        <span>{step > index+1 ? <CheckCircle2 size={17}/> : index+1}</span>{name}
      </div>)}</div>
    <Panel>
      <form className="form-stack max-form" onSubmit={submit}>
        {step === 1 && <>
          <h2>Tell us about the loan</h2>
          <FormField label="Requested amount (INR)">
            <input required type="number" min="1" max="100000000" step="1" value={amount}
              onChange={e => setAmount(e.target.value)}/>
          </FormField>
          <FormField label="Purpose">
            <select value={purpose} onChange={e => setPurpose(e.target.value)}>
              {['Seeds and fertilizer', 'Farm equipment', 'Irrigation', 'Working capital',
                'Crop storage', 'Agricultural business'].map(x => <option key={x}>{x}</option>)}
            </select>
          </FormField>
        </>}
        {step === 2 && <>
          <h2>Borrower account</h2>
          <p>Your fictional application will be associated with the signed-in borrower account.</p>
          <div className="review-summary"><span>Email</span><strong>{identity?.email}</strong></div>
          <Notice>Identity verification and real-world KYC are not connected to this research prototype.</Notice>
        </>}
        {step === 3 && <>
          <h2>Review and submit</h2>
          <div className="review-summary"><span>Requested amount</span><strong>{money(amount)}</strong></div>
          <div className="review-summary"><span>Loan purpose</span><strong>{purpose}</strong></div>
          <div className="review-summary"><span>Applicant</span><strong>{identity?.email}</strong></div>
          <Notice>Submission creates a synthetic loan request, not a legal credit application to a financial institution.</Notice>
        </>}
        {error && <ErrorBanner error={error}/>}
        <div className="form-actions">{step > 1 && <button className="btn btn-secondary" type="button"
          onClick={() => setStep(s => s-1)}><ArrowLeft size={16}/> Back</button>}
          <Submit busy={busy}>{step === 3 ? 'Submit demo application' : 'Continue'} <ArrowRight size={16}/></Submit></div>
      </form>
    </Panel>
  </>;
}

function EvidencePanel({ appId }: { appId: number }) {
  const state = useLoad<Evidence[]>('/api/v1/applications/' + appId + '/evidence');
  const { execute, busy, error, success } = useAction();
  const [key, setKey] = useState('turnover');
  const [value, setValue] = useState('1300000');
  const [alternatives, setAlternatives] = useState('1800000');
  const [source, setSource] = useState('');
  const docs = useLoad<Document[]>('/api/v1/applications/' + appId + '/documents');
  async function create(e: FormEvent) {
    e.preventDefault();
    let numericValue: unknown;
    let candidates: unknown[];
    try {
      numericValue = JSON.parse(value);
      candidates = alternatives.trim() ? alternatives.split(',').map(s => JSON.parse(s.trim())) : [];
    } catch { return; }
    const result = await execute('POST','/api/v1/applications/' + appId + '/evidence',
      {key, value:numericValue, candidates, document_id: source ? Number(source) : null},
      'Unverified evidence recorded. A reviewer must confirm any correction.');
    if (result) state.refresh();
  }
  return <>
    <Panel title="Recorded evidence" sub="Versioned observations with alternatives and verification state">
      <DataState state={state}>{facts => facts.length === 0
        ? <Empty title="No evidence entered" description="You can add a candidate turnover and its possible alternative below."/>
        : <div className="data-table-wrap"><table className="data-table"><thead><tr>
          <th>Field</th><th>Current value</th><th>Alternative values</th><th>Version</th><th>Verification</th>
        </tr></thead><tbody>{facts.map(f => <tr key={f.id}>
          <td><strong>{f.key}</strong></td><td>{String(f.value ?? 'Unknown')}</td>
          <td>{f.candidates.length ? f.candidates.map(String).join(', ') : '—'}</td>
          <td>v{f.version}</td><td><StatePill value={f.verified ? 'verified' : 'unverified'}/></td>
        </tr>)}</tbody></table></div>}</DataState>
    </Panel>
    <Panel title="Add candidate evidence" sub="Use numbers or JSON strings. Values are never automatically certified.">
      <form className="form-stack max-form" onSubmit={create}>
        <FormField label="Evidence field"><input required pattern="[a-z][a-z0-9_]*" value={key}
          onChange={e => setKey(e.target.value)}/></FormField>
        <FormField label="Observed value (JSON scalar)"><input required value={value}
          onChange={e => setValue(e.target.value)}/></FormField>
        <FormField label="Alternative values (comma-separated JSON scalars)">
          <input value={alternatives} onChange={e=>setAlternatives(e.target.value)}/></FormField>
        <FormField label="Source document (optional)">
          <select value={source} onChange={e=>setSource(e.target.value)}><option value="">Manual observation</option>
            {docs.data?.map(d=><option key={d.id} value={d.id}>{d.label} — {d.filename}</option>)}</select>
        </FormField>
        <Feedback error={error} success={success}/>
        <Submit busy={busy}>Record unverified evidence</Submit>
      </form>
    </Panel>
  </>;
}

function DocumentsPanel({ appId }: { appId: number }) {
  const state = useLoad<Document[]>('/api/v1/applications/' + appId + '/documents');
  const { execute, busy, error, success } = useAction();
  const [label, setLabel] = useState('Annual turnover statement');
  const [file, setFile] = useState<File | null>(null);
  const [extraction, setExtraction] = useState<unknown>(null);
  async function upload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    const data = new FormData();
    data.append('file', file);
    const result = await execute('POST', '/api/v1/applications/' + appId +
      '/documents?label=' + encodeURIComponent(label), data, 'Document uploaded securely.');
    if (result) { setFile(null); state.refresh(); }
  }
  async function extract(docId:number) {
    const result = await execute('POST','/api/v1/applications/' + appId +
      '/documents/' + docId + '/extract?language=eng', {}, 'Local text extraction complete.');
    if (result) setExtraction(result);
  }
  return <>
    <Panel title="Documents" sub="PDF, PNG or JPEG; maximum 5 MB per document.">
      <DataState state={state}>{docs=>docs.length===0
        ? <Empty title="No documents uploaded" description="Upload a synthetic PDF or image below."/>
        : <div className="item-list">{docs.map(d=><div className="list-entry" key={d.id}>
          <span className="entry-icon"><FileUp size={19}/></span>
          <span className="entry-main"><strong>{d.label}</strong><small>{d.filename} · SHA-256 recorded</small></span>
          <button className="btn btn-secondary btn-sm" onClick={()=>void extract(d.id)} disabled={busy}>Extract text</button>
          <a className="action-link" href={'/api/v1/applications/' + appId + '/documents/' + d.id + '/download'}>Download</a>
        </div>)}</div>}</DataState>
    </Panel>
    <Panel title="Upload a source document">
      <form className="form-stack max-form" onSubmit={upload}>
        <FormField label="Document label"><input required maxLength={100} value={label}
          onChange={e=>setLabel(e.target.value)}/></FormField>
        <FormField label="PDF or image file"><input required type="file" accept=".pdf,.png,.jpg,.jpeg"
          onChange={e=>setFile(e.target.files?.[0]??null)}/></FormField>
        <Feedback error={error} success={success}/><Submit busy={busy}>Upload document</Submit>
      </form>
      {extraction!==null && <div className="extraction-box"><h3>Unverified extraction suggestions</h3>
        <pre>{JSON.stringify(extraction,null,2)}</pre>
        <p>Inspect the source and manually record any useful candidate evidence in the Evidence tab.</p></div>}
    </Panel>
  </>;
}

function DecisionsPanel({appId}:{appId:number}) {
  const state=useLoad<Evaluation[]>('/api/v1/applications/'+appId+'/evaluations');
  const cf=useLoad<Counterfactual[]>('/api/v1/applications/'+appId+'/counterfactual');
  const lenders=useLoad<{id:number;name:string}[]>('/api/v1/lenders');
  function name(id:number){return lenders.data?.find(x=>x.id===id)?.name || 'Lender #'+id;}
  return <>
    <Notice>These are provisional rule-engine decisions and do not represent real lender approval.</Notice>
    <Panel title="Latest lender decisions" sub="Only current evaluations are shown first">
      <DataState state={state}>{evaluations => evaluations.length===0
        ? <Empty title="Not yet evaluated" description="A platform administrator can run preliminary lender checks after evidence is added."/>
        : <div className="item-list">{evaluations.map(ev=><div className="decision-row" key={ev.id}>
          <div><strong>{name(ev.lender_id)} · Evaluation #{ev.id}</strong>
            <small>Policy #{ev.policy_id} · {ev.current ? 'Current' : 'Historical'} · Evidence versions: {JSON.stringify(ev.evidence_versions)}</small>
            <div className="decision-rules">{ev.rules.map(r=><span key={r.rule_id}>{r.explanation}</span>)}</div>
          </div><div className="decision-tags"><StatePill value={ev.decision}/><StatePill value={ev.stable===null?'Unknown stability':ev.stable?'Stable':'Unstable'}/></div>
        </div>)}</div>}</DataState>
    </Panel>
    <Panel title="Counterfactual stability" sub="Only considers supplied evidence alternatives">
      <DataState state={cf}>{items=>items.length===0
        ? <Empty title="No lender policies" description="Ask an administrator to configure the fictional lender rules."/>
        : <div className="data-table-wrap"><table className="data-table"><thead><tr>
          <th>Lender</th><th>Candidate worlds</th><th>Outcomes</th><th>Stability</th>
        </tr></thead><tbody>{items.map(x=><tr key={x.policy_id}>
          <td>{name(x.lender_id)}</td><td>{x.worlds}</td><td>{x.outcomes.join(' / ')||x.reason}</td>
          <td><StatePill value={x.stable===null?'Unknown':x.stable?'Stable':'Unstable'}/></td>
        </tr>)}</tbody></table></div>}</DataState>
    </Panel>
  </>;
}

function OffersPanel({appId}:{appId:number}) {
  const state=useLoad<LoanOffer[]>('/api/v1/applications/'+appId+'/offers');
  const lenders=useLoad<{id:number;name:string}[]>('/api/v1/lenders');
  const {execute,busy,error,success}=useAction();
  const navigate=useNavigate();
  const [selected,setSelected]=useState<number|null>(null);
  const [agreement,setAgreement]=useState('');
  async function open(offerId:number){
    const result=await execute<{text:string}>('GET','/api/v1/offers/'+offerId+'/agreement');
    if(result){setSelected(offerId);setAgreement(result.text);}
  }
  async function accept(){
    if(selected===null)return;
    const result=await execute<{loan_id:number}>('POST','/api/v1/offers/'+selected+'/accept',{},
      'Mock offer accepted.');
    if(result)navigate('/borrower/loans/'+result.loan_id);
  }
  return <>
    <Notice>Offer comparisons are simulated and not legally binding. No funds will be transferred.</Notice>
    <Panel title="Offers and loan terms">
      <DataState state={state}>{offers=>offers.length===0
        ? <Empty title="No provisional offers" description="The platform administrator creates offers only after verified, stable preliminary eligibility."/>
        : <div className="offer-grid">{offers.map(o=><div className="offer-card" key={o.id}>
          <span className="page-eyebrow">{lenders.data?.find(l=>l.id===o.lender_id)?.name||'Lender '+o.lender_id}</span>
          <h3>{money(o.amount)}</h3><p>Simulated APR: <strong>{o.apr}%</strong></p>
          <StatePill value={o.status}/>
          {o.status==='provisional'&&<button className="btn btn-primary" onClick={()=>void open(o.id)}>View demo terms <ArrowRight size={15}/></button>}
        </div>)}</div>}</DataState>
    </Panel>
    {selected!==null&&<Panel title="Nonbinding demo agreement"><p>{agreement}</p>
      <Feedback error={error} success={success}/><button className="btn btn-primary" onClick={()=>void accept()} disabled={busy}>Accept simulated offer</button>
      <button className="btn btn-secondary" onClick={()=>setSelected(null)}>Cancel</button>
    </Panel>}
    {selected===null&&error&&<ErrorBanner error={error}/>}
  </>;
}

export function BorrowerApplicationDetail() {
  const {id}=useParams();
  const appId=Number(id);
  const state=useLoad<LoanApplication>(Number.isInteger(appId)&&appId>0?'/api/v1/applications/'+appId:null);
  const [tab,setTab]=useState<'overview'|'evidence'|'documents'|'decisions'|'offers'>('overview');
  return <>
    <Link to="/borrower/applications" className="back-link"><ArrowLeft size={16}/> My applications</Link>
    <DataState state={state}>{app=><>
      <PageTitle eyebrow={"BORROWER / APPLICATION #"+app.id} title={app.loan_purpose}
        description="Follow the evidence and lending process for your synthetic application."
        action={<StatePill value={app.status}/>}/>
      <div className="metric-row"><Metric label="Requested amount" value={money(app.requested_amount)}/>
        <Metric label="Application ID" value={'#'+app.id}/><Metric label="Status" value={app.status}/></div>
      <div className="tab-bar" role="tablist">{(['overview','documents','evidence','decisions','offers'] as const).map(x=>
        <button key={x} type="button" role="tab" aria-selected={tab===x} className={tab===x?'tab-active':''}
          onClick={()=>setTab(x)}>{x[0].toUpperCase()+x.slice(1)}</button>)}</div>
      {tab==='overview'&&<Panel title="Application progress"><div className="journey">
        {['Application submitted','Documents and evidence','Manual verification','Lender comparison','Mock offers'].map((x,i)=>
          <div className={'journey-item '+(i===0?'journey-done':'')} key={x}><span>{i+1}</span><strong>{x}</strong>
            <small>{i===0?'Submitted in prototype':'Status depends on completed backend operations'}</small></div>)}</div>
        <Notice>The stages shown are a guide, not a computed application status for the remaining steps.</Notice>
      </Panel>}
      {tab==='evidence'&&<EvidencePanel appId={appId}/>}
      {tab==='documents'&&<DocumentsPanel appId={appId}/>}
      {tab==='decisions'&&<DecisionsPanel appId={appId}/>}
      {tab==='offers'&&<OffersPanel appId={appId}/>}
    </>}</DataState>
  </>;
}

export function BorrowerLoans() {
  const state=useLoad<SimulatedLoan[]>('/api/v1/loans');
  return <>
    <PageTitle eyebrow="BORROWER / LOANS" title="My simulated loans"
      description="Installments and repayment records are demonstrations, not real financial obligations."/>
    <Panel><DataState state={state}>{loans=>loans.length===0
      ? <Empty title="No simulated loans yet" description="Once a provisional offer is accepted, your mock loan appears here." href="/borrower/applications" action="View applications"/>
      : <div className="item-list">{loans.map(loan=><Link className="list-entry" key={loan.id}
        to={'/borrower/loans/'+loan.id}><span className="entry-icon"><Sprout size={19}/></span>
        <span className="entry-main"><strong>Mock Loan #{loan.id}</strong><small>Application #{loan.application_id} · APR {loan.apr}%</small></span>
        <strong>{money(loan.amount)}</strong><StatePill value={loan.status}/><ArrowRight size={17}/></Link>)}</div>}</DataState></Panel>
  </>;
}

export function LoanDetail() {
  const {id}=useParams();
  const loanId=Number(id);
  const valid=Number.isInteger(loanId)&&loanId>0;
  const loan=useLoad<SimulatedLoan>(valid?'/api/v1/loans/'+loanId:null);
  const schedule=useLoad<{installments:Installment[]}>(valid?'/api/v1/loans/'+loanId+'/schedule':null);
  const claims=useLoad<UtilizationClaim[]>(valid?'/api/v1/loans/'+loanId+'/utilization':null);
  const {execute,busy,error,success}=useAction();
  const [category,setCategory]=useState('Seeds');
  const [amount,setAmount]=useState('12000');
  const [note,setNote]=useState('Seed invoice for demonstration');
  async function submit(e:FormEvent){
    e.preventDefault();
    const result=await execute('POST','/api/v1/loans/'+loanId+'/utilization',
      {category,amount:Number(amount),note},'Unverified utilization claim recorded.');
    if(result)claims.refresh();
  }
  return <>
    <Link className="back-link" to="/borrower/loans"><ArrowLeft size={16}/> My simulated loans</Link>
    <DataState state={loan}>{l=><>
      <PageTitle eyebrow="BORROWER / MOCK LOAN" title={'Loan #'+l.id}
        description={'Application #'+l.application_id+' · All amounts are simulated'}
        action={<StatePill value={l.status}/>}/>
      <div className="metric-row"><Metric label="Mock principal" value={money(l.amount)}/>
        <Metric label="Simulated APR" value={l.apr+'%'}/><Metric label="Mock disbursement" value={formatDate(l.disbursed_at)}/></div>
    </>}</DataState>
    <Panel title="12-month demo repayment schedule" sub="No bank payment is due or processed">
      <DataState state={schedule}>{data=>data.installments.length===0
        ? <Empty title="Schedule not created" description="The administrator must first record a simulated disbursement."/>
        : <div className="data-table-wrap"><table className="data-table"><thead><tr>
          <th>Installment</th><th>Due date</th><th>Demo amount</th><th>Recorded payment</th><th>Status</th>
        </tr></thead><tbody>{data.installments.map(i=><tr key={i.installment}>
          <td>#{i.installment}</td><td>{formatDate(i.due_at)}</td><td>{money(i.amount_due)}</td>
          <td>{money(i.amount_paid)}</td><td><StatePill value={i.status}/></td></tr>)}</tbody></table></div>}</DataState>
    </Panel>
    <Panel title="Use-of-funds evidence" sub="Document whether the fictional loan was used for its intended purpose">
      <DataState state={claims}>{items=>items.length===0
        ? <Empty title="No expenditure claims" description="Add a synthetic claim below."/>
        : <div className="item-list">{items.map(c=><div className="list-entry" key={c.id}>
          <span className="entry-main"><strong>{c.category}</strong><small>{c.note}</small></span>
          <strong>{money(c.amount)}</strong><StatePill value={c.status}/></div>)}</div>}</DataState>
      <form className="form-stack max-form" onSubmit={submit}>
        <FormField label="Expense category"><input value={category} required onChange={e=>setCategory(e.target.value)}/></FormField>
        <FormField label="Amount"><input type="number" min="1" required value={amount} onChange={e=>setAmount(e.target.value)}/></FormField>
        <FormField label="Explanation"><textarea required value={note} onChange={e=>setNote(e.target.value)}/></FormField>
        <Feedback error={error} success={success}/><Submit busy={busy}>Add unverified claim</Submit>
      </form>
    </Panel>
  </>;
}
