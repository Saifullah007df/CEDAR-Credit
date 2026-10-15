import { useState, type FormEvent } from 'react';
import { ArrowRight, CheckCircle2, FlaskConical, LogIn, LogOut, RefreshCw } from 'lucide-react';
import { useSession } from './lib/session';

type Mode = 'borrower' | 'admin' | 'review' | 'research' | 'lender';
type FieldDef = { name: string; label: string; type?: string; defaultValue?: string };
type Action = {
  label: string; method: 'GET' | 'POST'; path: (values: Record<string, string>) => string;
  fields: FieldDef[]; json?: (values: Record<string, string>) => unknown;
  hint: string;
};
const num = (value: string) => Number(value);
const actions: Record<Mode, Action[]> = {
  borrower: [
    { label: 'Create application', method: 'POST', path: () => '/api/v1/applications',
      fields: [{name: 'amount', label: 'Requested amount (INR)', defaultValue: '500000'}, {name: 'purpose', label: 'Loan purpose', defaultValue: 'Seeds and fertilizer'}],
      json: v => ({ requested_amount: num(v.amount), loan_purpose: v.purpose }),
      hint: 'Creates a persisted synthetic loan application for your borrower account.' },
    { label: 'My applications', method: 'GET', path: () => '/api/v1/applications', fields: [],
      hint: 'Only applications owned by your borrower profile are accessible.' },
    { label: 'Record candidate evidence', method: 'POST', path: v => `/api/v1/applications/${v.application}/evidence`,
      fields: [{name: 'application', label: 'Application ID'}, {name: 'key', label: 'Field key', defaultValue: 'turnover'},
        {name: 'value', label: 'Extracted value (JSON number/string)', defaultValue: '1300000'},
        {name: 'candidates', label: 'Plausible alternatives (JSON list)', defaultValue: '[1800000]'}],
      json: v => ({ key: v.key, value: JSON.parse(v.value), candidates: JSON.parse(v.candidates) }),
      hint: 'Records unverified evidence and alternate interpretations. This is manual candidate entry, not live OCR.' },
    { label: 'View evidence', method: 'GET', path: v => `/api/v1/applications/${v.application}/evidence`,
      fields: [{name: 'application', label: 'Application ID'}], hint: 'Shows provenance, version and verification state.' },
    { label: 'View lender evaluations', method: 'GET', path: v => `/api/v1/applications/${v.application}/evaluations`,
      fields: [{name: 'application', label: 'Application ID'}], hint: 'Includes immutable earlier evaluations and current versions.' },
    { label: 'View provisional offers', method: 'GET', path: v => `/api/v1/applications/${v.application}/offers`,
      fields: [{name: 'application', label: 'Application ID'}], hint: 'All offers are fictional, nonbinding simulations.' },
    { label: 'Accept a simulated offer', method: 'POST', path: v => `/api/v1/offers/${v.offer}/accept`,
      fields: [{name: 'offer', label: 'Offer ID'}], json: () => ({}), hint: 'No financial obligation or money transfer.' },
    { label: 'Record utilization claim', method: 'POST', path: v => `/api/v1/loans/${v.loan}/utilization`,
      fields: [{name: 'loan', label: 'Mock loan ID'}, {name: 'category', label: 'Category', defaultValue: 'seeds'},
        {name: 'amount', label: 'Expenditure amount', defaultValue: '12000'},
        {name: 'note', label: 'Explanation', defaultValue: 'Seed invoice pending verification'}],
      json: v => ({ category: v.category, amount: num(v.amount), note: v.note }),
      hint: 'Captures unverified purpose evidence; it does not infer or label fraud.' },
  ],
  admin: [
    { label: 'Create fictional lender', method: 'POST', path: () => '/api/v1/admin/lenders',
      fields: [{name: 'name', label: 'Fictional lender name', defaultValue: 'Synthetic Agri Bank A'}],
      json: v => ({name: v.name}), hint: 'Only platform administrators can add lenders.' },
    { label: 'Create lender product', method: 'POST', path: v => `/api/v1/admin/lenders/${v.lender}/products`,
      fields: [{name: 'lender', label: 'Lender ID'}, {name: 'name', label: 'Product name', defaultValue: 'FPO Crop Loan'},
        {name: 'min', label: 'Minimum amount', defaultValue: '100000'}, {name: 'max', label: 'Maximum amount', defaultValue: '1000000'},
        {name: 'apr', label: 'Simulated APR (%)', defaultValue: '11'}],
      json: v => ({name: v.name, min_amount: num(v.min), max_amount: num(v.max), apr: num(v.apr)}),
      hint: 'Defines the product range used for simulated provisional offers.' },
    { label: 'Publish a versioned lender rule', method: 'POST', path: v => `/api/v1/admin/lenders/${v.lender}/policies`,
      fields: [{name: 'lender', label: 'Lender ID'}, {name: 'field', label: 'Evidence field', defaultValue: 'turnover'},
        {name: 'op', label: 'Operator (gte / lte / gt / lt / eq / neq / in)', defaultValue: 'gte'},
        {name: 'target', label: 'Comparison target (JSON)', defaultValue: '1500000'}],
      json: v => ({rules: [{field_key: v.field, operator: v.op, target: JSON.parse(v.target), required: true}]}),
      hint: 'Publishing creates an immutable policy version and explicit evidence-rule edge.' },
    { label: 'List lender products', method: 'GET', path: () => '/api/v1/products', fields: [],
      hint: 'Use these product IDs when creating provisional offers.' },
    { label: 'Evaluate across active lenders', method: 'POST', path: v => `/api/v1/applications/${v.application}/evaluate`,
      fields: [{name: 'application', label: 'Application ID'}], json: () => ({}),
      hint: 'Runs real deterministic predicates. PASS is preliminary, never actual credit approval.' },
    { label: 'Schedule evidence review', method: 'POST', path: v => `/api/v1/applications/${v.application}/schedule-review`,
      fields: [{name: 'application', label: 'Application ID'}], json: () => ({}),
      hint: 'Prioritizes source verification based on rule dependencies and decision instability.' },
    { label: 'Generate provisional offer', method: 'POST', path: v => `/api/v1/applications/${v.application}/offers`,
      fields: [{name: 'application', label: 'Application ID'}, {name: 'evaluation', label: 'Current passing evaluation ID'},
        {name: 'product', label: 'Product ID'}],
      json: v => ({evaluation_id: num(v.evaluation), product_id: num(v.product)}),
      hint: 'Requires a stable, current PASS and independently verified mandatory evidence.' },
    { label: 'Mock disbursement', method: 'POST', path: v => `/api/v1/loans/${v.loan}/mock-disburse`,
      fields: [{name: 'loan', label: 'Mock loan ID'}], json: () => ({}),
      hint: 'Records mock status only. No bank transfer.' },
    { label: 'Mock repayment', method: 'POST', path: v => `/api/v1/loans/${v.loan}/mock-repayments`,
      fields: [{name: 'loan', label: 'Mock loan ID'}, {name: 'amount', label: 'Simulated amount', defaultValue: '10000'}],
      json: v => ({amount: num(v.amount)}), hint: 'Simulation only: no payment gateway.' },
  ],
  review: [
    { label: 'Prioritized review queue', method: 'GET', path: () => '/api/v1/review/tasks', fields: [],
      hint: 'Only authorized reviewers and administrators can access this queue.' },
    { label: 'Verify or correct evidence', method: 'POST', path: v => `/api/v1/review/tasks/${v.task}/verify`,
      fields: [{name: 'task', label: 'Open review task ID'}, {name: 'value', label: 'Verified value (JSON)', defaultValue: '1800000'},
        {name: 'note', label: 'Verification note', defaultValue: 'Confirmed against original submitted evidence'}],
      json: v => ({value: JSON.parse(v.value), note: v.note}),
      hint: 'Creates a verified revision, retains old snapshots, selectively recalculates dependent lender rules.' },
  ],
  research: [
    { label: 'Counterfactual analysis', method: 'GET', path: v => `/api/v1/applications/${v.application}/counterfactual`,
      fields: [{name: 'application', label: 'Application ID'}],
      hint: 'Enumerates supported candidate worlds. Unstable/unknown are not silently treated as stable.' },
    { label: 'Versioned decisions', method: 'GET', path: v => `/api/v1/applications/${v.application}/evaluations`,
      fields: [{name: 'application', label: 'Application ID'}],
      hint: 'Compare decision snapshots before and after review.' },
    { label: 'Fact revision history', method: 'GET', path: v => `/api/v1/applications/${v.application}/evidence/${v.fact}/history`,
      fields: [{name: 'application', label: 'Application ID'}, {name: 'fact', label: 'Evidence fact ID'}],
      hint: 'Old extracted values and reviewers remain versioned for auditing.' },
  ],
  lender: [
    { label: 'List lender identities', method: 'GET', path: () => '/api/v1/lenders', fields: [],
      hint: 'Fictional lenders only.' },
    { label: 'Inspect versioned lender policies', method: 'GET', path: v => `/api/v1/lenders/${v.lender}/policies`,
      fields: [{name: 'lender', label: 'Lender ID'}],
      hint: 'Lender admins can only read their own lender policy versions.' },
    { label: 'Inspect available products', method: 'GET', path: () => '/api/v1/products', fields: [],
      hint: 'Synthetic products for platform testing.' },
  ],
};
const modes: { id: Mode; label: string; roles: string[] }[] = [
  { id: 'borrower', label: 'Borrower', roles: ['borrower'] },
  { id: 'admin', label: 'Platform Admin', roles: ['platform_admin'] },
  { id: 'review', label: 'Human Reviewer', roles: ['platform_admin', 'reviewer'] },
  { id: 'research', label: 'CEDAR Research', roles: ['borrower', 'platform_admin', 'reviewer'] },
  { id: 'lender', label: 'Lender', roles: ['lender_admin', 'platform_admin'] },
];

function AuthPanel() {
  const { login } = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [legalName, setLegalName] = useState('');
  const [register, setRegister] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setFeedback('');
    try {
      if (register) {
        const r = await fetch('/api/v1/auth/register', { method:'POST', headers:{'Content-Type':'application/json'},
          body:JSON.stringify({email, password, legal_name: legalName, borrower_type: 'fpo'}) });
        if (!r.ok) { const data = await r.json(); throw new Error(JSON.stringify(data.detail ?? data)); }
      }
      await login(email, password);
    } catch (err) { setFeedback(err instanceof Error ? err.message : 'Unable to authenticate'); }
    finally {setBusy(false);}
  }
  return <section className="surface auth-panel">
    <div className="section-header"><h2>{register ? 'Create borrower account' : 'Sign in to the sandbox'}</h2><LogIn size={20}/></div>
    <p className="muted">Demo accounts are stored in your local prototype database. Platform admins must be created using the CLI; there is no publicly accessible admin signup.</p>
    <form className="work-form" onSubmit={submit}>
      <label>Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="fpo@example.test" /></label>
      <label>Password<input required type="password" minLength={12} value={password} onChange={e => setPassword(e.target.value)} placeholder="12 or more characters" /></label>
      {register && <label>FPO / business name<input required minLength={2} value={legalName} onChange={e=>setLegalName(e.target.value)} /></label>}
      <button className="primary-action" disabled={busy}>{busy ? 'Working…' : register ? 'Register and sign in' : 'Sign in'} <ArrowRight size={16}/></button>
      <button type="button" className="quiet-action" onClick={()=>setRegister(!register)}>{register ? 'I already have an account' : 'Register a new borrower account'}</button>
      {feedback && <p className="work-error" role="alert">{feedback}</p>}
    </form>
  </section>;
}

function Operation({ action }: { action: Action }) {
  const { request } = useSession();
  const [inputs, setInputs] = useState<Record<string, string>>(
    Object.fromEntries(action.fields.map(f => [f.name, f.defaultValue ?? '']))
  );
  const [result, setResult] = useState<unknown | null>(null);
  const [error, setError] = useState('');
  const [working, setWorking] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault(); setWorking(true); setError(''); setResult(null);
    try {
      const path = action.path(inputs);
      const data = await request(action.method, path, action.method === 'POST' ? (action.json ? action.json(inputs) : {}) : undefined);
      setResult(data);
    } catch (err) { setError(err instanceof Error ? err.message : 'Operation failed'); }
    finally { setWorking(false); }
  }
  return <section className="operation"><div className="section-header"><h2>{action.label}</h2><span className="method-tag">{action.method}</span></div>
    <p className="muted">{action.hint}</p>
    <form className="work-form" onSubmit={submit}>
      {action.fields.map(f => <label key={f.name}>{f.label}<input type={f.type ?? 'text'} required value={inputs[f.name]} onChange={e => setInputs(x => ({ ...x, [f.name]: e.target.value }))}/></label>)}
      <button className="primary-action" disabled={working}>{working ? 'Working…' : 'Execute'} <ArrowRight size={15}/></button>
    </form>
    {error && <p className="work-error" role="alert">{error}</p>}
    {result !== null && <div className="work-result"><div><CheckCircle2 size={15}/> API response</div><pre>{JSON.stringify(result, null, 2)}</pre></div>}
  </section>;
}

export default function Workbench() {
  const { identity, logout } = useSession();
  const [mode, setMode] = useState<Mode>('borrower');
  const available = modes.filter(m => !identity || m.roles.includes(identity.role));
  const displayedMode = available.some(m=>m.id===mode) ? mode : available[0]?.id ?? 'borrower';
  return <div className="workbench">
    <div className="heading"><p className="eyebrow">CEDAR CREDIT · LIVE API WORKFLOWS</p><h1>Operations Workbench</h1>
      <p>Functional application, evidence, rules, review and mock loan operations against the FastAPI backend. All loan and lender activity is synthetic.</p></div>
    {identity ? <>
      <div className="session-bar"><span><CheckCircle2 size={17}/> Signed in as <strong>{identity.email}</strong> · {identity.role}</span>
        <button type="button" onClick={() => void logout()}><LogOut size={16}/> Sign out</button></div>
      <div className="mode-selector">{available.map(m => <button key={m.id} type="button" className={displayedMode===m.id?'selected':''} onClick={()=>setMode(m.id)}>{m.label}</button>)}</div>
      <div className="notice"><FlaskConical size={19}/> These operations are not production credit decisions. API authorization still applies regardless of the selected visual tab.</div>
      <div className="operations">{actions[displayedMode].map(action => <Operation key={action.label} action={action}/>)}</div>
      <button type="button" className="refresh-hint" onClick={() => window.scrollTo({top:0,behavior:'smooth'})}><RefreshCw size={15}/> Back to top</button>
    </> : <AuthPanel/>}
  </div>;
}
