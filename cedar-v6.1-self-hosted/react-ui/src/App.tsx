import { useEffect, useMemo, useState } from 'react';

type Loan = { id:string; borrower:string; principal:string; categories:string[]; version:number };
type Payment = { id:string; external_id:string; payee:string; amount:string; allocated:string; available:string };
type Invoice = { id:string; number:string; supplier:string; category:string; amount:string; allocated:string; available:string; document_verified:boolean; delivery_verified:boolean; version:number };
type Allocation = { id:string; payment_id:string; invoice_id:string; amount:string; active:boolean };
type Case = { id:string; loan_id:string; title:string; severity:string; status:string; version:number; proposed_note?:string };
type Util = { loan_id:string; principal:string; observed_payments:string; supported:string; incomplete:string; policy_exception:string; unallocated:string; source_complete:boolean; status:string; findings:string[]; snapshot_id?:string|null };
type Dashboard = { loans:number; payments:number; invoices:number; open_cases:number; allocations:number };
type Audit = { id:number; at:string; actor:string; action:string; entity:string };
type Page = 'overview'|'ledger'|'evidence'|'utilization'|'review'|'audit';
const format = (value:string|number|undefined) => '₹'+Number(value??0).toLocaleString('en-IN',{maximumFractionDigits:2});
const tabs:{id:Page;label:string;icon:string}[]=[{id:'overview',label:'Overview',icon:'▦'},{id:'ledger',label:'Financial ledger',icon:'▤'},{id:'evidence',label:'Evidence & invoices',icon:'▧'},{id:'utilization',label:'Loan utilization',icon:'◉'},{id:'review',label:'Review queue',icon:'⚑'},{id:'audit',label:'Audit trail',icon:'↺'}];
async function request<T>(path:string,token:string,method='GET',payload?:unknown, idempotency?:string):Promise<T>{
 const headers:Record<string,string>={Authorization:'Bearer '+token};
 if(payload!==undefined && !(payload instanceof FormData))headers['Content-Type']='application/json';
 if(idempotency)headers['Idempotency-Key']=idempotency;
 const response=await fetch('/v1/'+path,{method,headers,body:payload===undefined?undefined:payload instanceof FormData?payload:JSON.stringify(payload)});
 const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data as T;
}
export default function App(){
 const [token,setToken]=useState(sessionStorage.getItem('cedar_token')??'');
 const [role,setRole]=useState(sessionStorage.getItem('cedar_role')??'');
 const [username,setUsername]=useState('reviewer');
 const [password,setPassword]=useState('DemoOnly!123');
 const [page,setPage]=useState<Page>('overview');
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 const [loans,setLoans]=useState<Loan[]>([]);
 const [payments,setPayments]=useState<Payment[]>([]);
 const [invoices,setInvoices]=useState<Invoice[]>([]);
 const [allocations,setAllocations]=useState<Allocation[]>([]);
 const [cases,setCases]=useState<Case[]>([]);
 const [util,setUtil]=useState<Util|null>(null);
 const [dashboard,setDashboard]=useState<Dashboard|null>(null);
 const [audit,setAudit]=useState<Audit[]>([]);
 const [otp,setOtp]=useState('');
 const [selectedPayment,setSelectedPayment]=useState('');
 const [selectedInvoice,setSelectedInvoice]=useState('');
 const [amount,setAmount]=useState('');
 const loan=loans[0];
 const alert=(text:string)=>setMessage(text);
 const load=async()=>{
  if(!token)return;
  const [ls,ps,ins,als,cs,ds]=await Promise.all([
   request<Loan[]>('loans',token),request<Payment[]>('payments',token),request<Invoice[]>('invoices',token),
   request<Allocation[]>('allocations',token),request<Case[]>('cases',token),request<Dashboard>('dashboard',token)
  ]);
  setLoans(ls);setPayments(ps);setInvoices(ins);setAllocations(als);setCases(cs);setDashboard(ds);
  if(ls[0])setUtil(await request<Util>(`loans/${ls[0].id}/utilization`,token));
 };
 useEffect(()=>{if(token)void load().catch(e=>alert(String(e)))},[token]);
 useEffect(()=>{if(!selectedPayment&&payments[0])setSelectedPayment(payments[0].id)},[payments]);
 useEffect(()=>{if(!selectedInvoice&&invoices[0])setSelectedInvoice(invoices[0].id)},[invoices]);
 const invoiceById=useMemo(()=>new Map(invoices.map(i=>[i.id,i])),[invoices]);
 const paymentById=useMemo(()=>new Map(payments.map(p=>[p.id,p])),[payments]);
 const perform=async(fn:()=>Promise<unknown>)=>{setBusy(true);try{await fn();await load();alert('Action completed; results refreshed.')}catch(e){alert(e instanceof Error?e.message:String(e))}finally{setBusy(false)}};
 const login=async()=>{setBusy(true);try{
  const resp=await fetch('/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password,otp:otp||undefined})});
  const result=await resp.json();if(!resp.ok)throw new Error(result.detail);
  setRole(result.role);setToken(result.token);sessionStorage.setItem('cedar_token',result.token);sessionStorage.setItem('cedar_role',result.role);
 }catch(e){alert(e instanceof Error?e.message:String(e))}finally{setBusy(false)}};
 if(!token)return <div className="login"><div className="brand dark"><div className="mark">C</div><div><strong>CEDAR</strong><small>LOAN INTEGRITY PLATFORM</small></div></div><h2>Operational workspace</h2><p>Development accounts and synthetic borrower records only.</p><label className="field">Demo role<select className="input" value={username} onChange={e=>setUsername(e.target.value)}>{['reviewer','approver','admin','operator','auditor'].map(x=><option key={x}>{x}</option>)}</select></label><label className="field">Password<input className="input" value={password} type="password" onChange={e=>setPassword(e.target.value)}/></label><label className="field">Authenticator code (if enabled)<input className="input" value={otp} onChange={e=>setOtp(e.target.value)} inputMode="numeric" maxLength={6} placeholder="6-digit code"/></label><button disabled={busy} className="primary" onClick={()=>void login()}>Sign in</button>{message&&<p className="notice">{message}</p>}</div>;
 const assess=(label:string,value:string|undefined,color:string)=><div className="stat-line" key={label}><span><i className="swatch" style={{background:color}}/>{label}</span><strong>{format(value)}</strong></div>;
 const utilCard=<div className="panel"><h3>Loan-purpose evidence coverage</h3><p className="muted">{loan?.id} · {util?.status||'Not assessed'} · source complete: {util?.source_complete?'yes':'no'}</p><div className="progress">{[['supported','#138a7b'],['incomplete','#ecae55'],['policy_exception','#c85e68'],['unallocated','#aebccb']].map(([field,color])=><div key={field} style={{background:color,width:(100*Number(util?.[field as keyof Util]||0)/Math.max(1,Number(util?.observed_payments||0)))+'%'}}/>)}</div><div className="summary-grid">{assess('Supported',util?.supported,'#138a7b')}{assess('Incomplete',util?.incomplete,'#ecae55')}{assess('Policy exception',util?.policy_exception,'#c85e68')}{assess('Unallocated',util?.unallocated,'#aebccb')}</div><p className="muted">Observed payments: {format(util?.observed_payments)}. This does not prove physical utilization.</p><button disabled={busy} className="primary" onClick={()=>void perform(()=>request(`loans/${loan.id}/evaluate`,token,'POST'))}>Re-evaluate</button></div>;
 return <div className="shell"><aside className="side"><div className="brand"><div className="mark">C</div><div><strong>CEDAR</strong><small>LOAN INTEGRITY PLATFORM</small></div></div><nav>{tabs.map(x=><button key={x.id} className={page===x.id?'active':''} onClick={()=>setPage(x.id)}>{x.icon}　{x.label}</button>)}</nav><div className="status"><span className="dot"/>Connected to local API<br/>Production authorization not established</div></aside><div className="main"><header className="top"><div><div className="eyebrow">CEDAR / OPERATIONS</div><h1>{tabs.find(x=>x.id===page)?.label}</h1></div><div className="auth"><span className="chip">{role.toUpperCase()}</span><button className="secondary" onClick={()=>{sessionStorage.clear();setToken('')}}>Sign out</button></div></header><div className="content"><div className="notice">DEVELOPMENT DEMO · All borrower and payment data are synthetic; findings are advisory.</div>{message&&<div className="notification" role="status">{message}<button onClick={()=>setMessage('')}>×</button></div>}
 {page==='overview'&&<><div className="metrics">{[['Loans',dashboard?.loans],['Transactions',dashboard?.payments],['Invoices',dashboard?.invoices],['Open cases',dashboard?.open_cases]].map(([label,value])=><div className="metric" key={label}><small>{label}</small><strong>{value??'—'}</strong></div>)}</div><h2>Current loan · {loan?.borrower}</h2><div className="twocol">{utilCard}<div className="panel"><h3>Current findings</h3>{(util?.findings||[]).map((f,i)=><div className="case" key={i}>{f}</div>)}</div></div></>}
 {page==='ledger'&&<><h2>Imported financial transactions</h2><div className="panel tablewrap"><table><thead><tr><th>Reference</th><th>Payee</th><th>Amount</th><th>Allocated</th><th>Available</th></tr></thead><tbody>{payments.map(p=><tr key={p.id}><td>{p.external_id}</td><td>{p.payee}</td><td>{format(p.amount)}</td><td>{format(p.allocated)}</td><td>{format(p.available)}</td></tr>)}</tbody></table></div><h2>Constrained payment allocation</h2><div className="panel form-grid"><label className="field">Payment<select className="input" value={selectedPayment} onChange={e=>setSelectedPayment(e.target.value)}>{payments.map(p=><option key={p.id} value={p.id}>{p.external_id} · {format(p.available)}</option>)}</select></label><label className="field">Verified invoice<select className="input" value={selectedInvoice} onChange={e=>setSelectedInvoice(e.target.value)}>{invoices.map(i=><option key={i.id} value={i.id}>{i.number} · {format(i.available)}</option>)}</select></label><label className="field">Amount<input className="input" value={amount} onChange={e=>setAmount(e.target.value)} placeholder="10000.00"/></label><button className="primary" disabled={busy} onClick={()=>void perform(()=>request('allocations',token,'POST',{payment_id:selectedPayment,invoice_id:selectedInvoice,amount},crypto.randomUUID()))}>Commit allocation</button></div></>}
 {page==='evidence'&&<><h2>Invoice evidence</h2><div className="panel tablewrap"><table><thead><tr><th>Invoice</th><th>Supplier</th><th>Category</th><th>Amount</th><th>Document</th><th>Delivery</th><th>Action</th></tr></thead><tbody>{invoices.map(i=><tr key={i.id}><td>{i.number}</td><td>{i.supplier}</td><td>{i.category}</td><td>{format(i.amount)}</td><td>{i.document_verified?'Verified':'Pending'}</td><td>{i.delivery_verified?'Verified':'Pending'}</td><td><button className="secondary" disabled={busy} onClick={()=>{const reason=prompt('Verification rationale:','Reviewed underlying source');if(!reason)return;const doc=confirm('Original invoice verified?');const delivery=confirm('Delivery evidence verified?');void perform(()=>request(`invoices/${i.id}/verify`,token,'POST',{document_verified:doc,delivery_verified:delivery,expected_version:i.version,reason}))}}>Review</button></td></tr>)}</tbody></table></div><h2>Secure document upload</h2><div className="panel"><input type="file" accept=".pdf,.png,.jpeg,.jpg" onChange={e=>{const file=e.currentTarget.files?.[0];if(!file||!loan)return;const form=new FormData();form.append('file',file);void perform(()=>request(`documents?loan_id=${encodeURIComponent(loan.id)}`,token,'POST',form))}}/><p className="muted">OCR extraction is treated as unverified text.</p></div></>}
 {page==='utilization'&&<>{utilCard}<h2>Expenditure allocations</h2><div className="panel tablewrap"><table><thead><tr><th>Payment</th><th>Invoice</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>{allocations.map(a=><tr key={a.id}><td>{paymentById.get(a.payment_id)?.external_id}</td><td>{invoiceById.get(a.invoice_id)?.number}</td><td>{format(a.amount)}</td><td>{a.active?'Active':'Reversed'}</td><td>{a.active&&<button className="secondary" disabled={busy} onClick={()=>{if(confirm('Reverse allocation?'))void perform(()=>request(`allocations/${a.id}/reverse`,token,'POST'))}}>Reverse</button>}</td></tr>)}</tbody></table></div></>}
 {page==='review'&&<><h2>Exceptions and review queue</h2><div className="panel">{cases.map(c=><div className="case" key={c.id}><div><strong>{c.title}</strong><small>{c.severity} · {c.status} · version {c.version}</small></div><button className="secondary" disabled={busy} onClick={()=>{const action=c.status==='OPEN'?'propose':c.status==='APPROVAL_PENDING'?'approve':'reopen';const note=prompt(action+' rationale:','Checked supporting evidence');if(note)void perform(()=>request(`cases/${c.id}/actions`,token,'POST',{action,expected_version:c.version,note}))}}>Review</button></div>)}</div></>}
 {page==='audit'&&<><h2>Audit history</h2><div className="panel"><button className="primary" onClick={()=>void request<Audit[]>('audit',token).then(setAudit).catch(e=>alert(String(e)))}>Load audit events</button><div className="tablewrap"><table><thead><tr><th>Actor</th><th>Action</th><th>Entity</th><th>Time</th></tr></thead><tbody>{audit.map(a=><tr key={a.id}><td>{a.actor}</td><td>{a.action}</td><td>{a.entity.slice(0,12)}</td><td>{a.at}</td></tr>)}</tbody></table></div></div></>}
 <footer>CEDAR v5 · Real API connected · Not certified for live financial data</footer></div></div></div>
}
