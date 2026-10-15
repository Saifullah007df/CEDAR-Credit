import { useState } from 'react';
import type { FormEvent } from 'react';
import { Building2, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { DataState, Empty, Feedback, FormField, Notice, PageTitle, Panel,
  StatePill, Submit, money, useAction, useLoad } from '../components/Shared';
import type { Lender, LenderPolicy, LoanProduct } from '../lib/types';

function InstitutionSelect({ lenders, value, onChange }: {
  lenders: Lender[];
  value: string;
  onChange: (value:string) => void;
}) {
  return <FormField label="Fictional institution">
    <select required value={value} onChange={e=>onChange(e.target.value)}>
      {lenders.length===0?<option value="">No institutions available</option>
        : lenders.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}
    </select>
  </FormField>;
}

export function ManageLenders() {
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const {execute,busy,error,success}=useAction();
  const [name,setName]=useState('');
  async function submit(e:FormEvent){
    e.preventDefault();
    const result=await execute('POST','/api/v1/admin/lenders',{name},
      'Fictional lending institution created.');
    if(result){setName('');lenders.refresh();}
  }
  return <>
    <PageTitle eyebrow="PLATFORM ADMIN / INSTITUTIONS" title="Lending institutions"
      description="Register fictional banks and NBFCs for the research marketplace."/>
    <div className="portal-columns">
      <Panel title="Registered lenders">
        <DataState state={lenders}>{items=>items.length===0
          ? <Empty title="No lenders yet" description="Register a fictional institution to start."/>
          : <div className="item-list">{items.map(l=><div className="list-entry" key={l.id}>
            <span className="entry-icon"><Building2 size={18}/></span>
            <span className="entry-main"><strong>{l.name}</strong><small>Institution #{l.id}</small></span>
            <StatePill value="active"/></div>)}</div>}</DataState>
      </Panel>
      <Panel title="Register a fictional lender">
        <form className="form-stack" onSubmit={submit}>
          <FormField label="Institution name">
            <input required minLength={2} value={name} onChange={e=>setName(e.target.value)}
              placeholder="e.g. Demo Rural Finance Ltd"/></FormField>
          <Submit busy={busy}><Plus size={16}/> Add institution</Submit>
        </form>
        <Feedback error={error} success={success}/>
      </Panel>
    </div>
    <div className="portal-subnav">
      <Link to="/admin/products">Manage products →</Link>
      <Link to="/admin/policies">Configure lending policies →</Link>
      <Link to="/admin/users">Provision lender administrators →</Link>
    </div>
  </>;
}

export function ManageProducts() {
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const products=useLoad<LoanProduct[]>('/api/v1/products');
  const {execute,busy,error,success}=useAction();
  const [lenderId,setLenderId]=useState('');
  const [name,setName]=useState('FPO Crop Loan');
  const [min,setMin]=useState('100000');
  const [max,setMax]=useState('1000000');
  const [apr,setApr]=useState('11');
  const chosen=lenderId || String(lenders.data?.[0]?.id||'');
  async function submit(e:FormEvent){
    e.preventDefault();
    const result=await execute('POST','/api/v1/admin/lenders/'+chosen+'/products',
      {name,min_amount:Number(min),max_amount:Number(max),apr:Number(apr)},
      'Synthetic loan product added.');
    if(result)products.refresh();
  }
  return <>
    <PageTitle eyebrow="PLATFORM ADMIN / PRODUCTS" title="Loan products"
      description="Configure simulated loan ranges and APRs for fictional lenders."/>
    <Panel title="Product catalog">
      <DataState state={products}>{items=>items.length===0
        ? <Empty title="No products" description="Use the form below to publish a synthetic product."/>
        : <div className="data-table-wrap"><table className="data-table"><thead><tr>
          <th>Product</th><th>Institution</th><th>Minimum</th><th>Maximum</th><th>Demo APR</th>
        </tr></thead><tbody>{items.map(p=><tr key={p.id}>
          <td><strong>{p.name}</strong></td><td>{lenders.data?.find(l=>l.id===p.lender_id)?.name||'Lender #'+p.lender_id}</td>
          <td>{money(p.min_amount)}</td><td>{money(p.max_amount)}</td><td>{p.apr}%</td>
        </tr>)}</tbody></table></div>}</DataState>
    </Panel>
    <Panel title="Create a product">
      <form className="form-stack max-form" onSubmit={submit}>
        <InstitutionSelect lenders={lenders.data||[]} value={chosen} onChange={setLenderId}/>
        <FormField label="Product name"><input value={name} required onChange={e=>setName(e.target.value)}/></FormField>
        <div className="form-two">
          <FormField label="Minimum amount (INR)"><input type="number" min="1" required value={min}
            onChange={e=>setMin(e.target.value)}/></FormField>
          <FormField label="Maximum amount (INR)"><input type="number" min="1" required value={max}
            onChange={e=>setMax(e.target.value)}/></FormField>
        </div>
        <FormField label="Demonstration annual APR (%)"><input type="number" min="0" max="100"
          required value={apr} onChange={e=>setApr(e.target.value)}/></FormField>
        <Submit busy={busy}>Create synthetic product</Submit>
      </form>
      <Feedback error={error} success={success}/>
    </Panel>
  </>;
}

export function ManagePolicies() {
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const [chosen,setChosen]=useState('');
  const lenderId=chosen||String(lenders.data?.[0]?.id||'');
  const policies=useLoad<LenderPolicy[]>(lenderId?'/api/v1/lenders/'+lenderId+'/policies':null);
  const {execute,busy,error,success}=useAction();
  const [field,setField]=useState('turnover');
  const [op,setOp]=useState('gte');
  const [target,setTarget]=useState('1500000');
  async function submit(e:FormEvent){
    e.preventDefault();
    let parsed:unknown;
    try {parsed=JSON.parse(target);}catch{parsed=target;}
    const result=await execute('POST','/api/v1/admin/lenders/'+lenderId+'/policies',
      {rules:[{field_key:field,operator:op,target:parsed,required:true}]},
      'New versioned policy published. The previous version remains in history.');
    if(result)policies.refresh();
  }
  return <>
    <PageTitle eyebrow="PLATFORM ADMIN / POLICIES" title="Lending rules and policies"
      description="Define versioned eligibility predicates and examine the lender's historical rules."/>
    <Panel title="Select lending institution">
      <div className="max-form">
        <InstitutionSelect lenders={lenders.data||[]} value={lenderId} onChange={setChosen}/>
      </div>
    </Panel>
    <div className="portal-columns">
      <Panel title="Published policy history">
        <DataState state={policies}>{items=>items.length===0
          ? <Empty title="No policy versions" description="Create the first policy for this fictional lender."/>
          : <div className="policy-stack">{items.map(p=><div className="policy-card" key={p.id}>
            <div className="portal-panel-head"><div><h3>Version {p.version}</h3><p>Policy #{p.id}</p></div>
              <StatePill value={p.active?'active':'historical'}/></div>
            <div className="item-list">{p.rules.map(r=><div className="list-entry" key={r.id}>
              <span className="entry-main"><strong>{r.field_key} {r.operator} {JSON.stringify(r.target)}</strong>
                <small>{r.required?'Mandatory rule':'Optional rule'}</small></span>
            </div>)}</div>
          </div>)}</div>}</DataState>
      </Panel>
      <Panel title="Publish a new policy version" sub="The demonstration form creates one required rule per new policy.">
        <form className="form-stack" onSubmit={submit}>
          <FormField label="Evidence field"><input required pattern="[a-z][a-z0-9_]*" value={field}
            onChange={e=>setField(e.target.value)}/></FormField>
          <div className="form-two">
            <FormField label="Comparison"><select value={op} onChange={e=>setOp(e.target.value)}>
              {['gte','gt','lte','lt','eq','neq','in'].map(x=><option key={x}>{x}</option>)}
            </select></FormField>
            <FormField label="Threshold (JSON)"><input required value={target} onChange={e=>setTarget(e.target.value)}/></FormField>
          </div>
          <Notice>Publishing marks the old policy inactive. Previously calculated evaluations remain historical snapshots.</Notice>
          <Submit busy={busy}>Publish policy version</Submit>
        </form>
        <Feedback error={error} success={success}/>
      </Panel>
    </div>
  </>;
}

export function ManageUsers() {
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const {execute,busy,error,success}=useAction();
  const [chosen,setChosen]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const lenderId=chosen||String(lenders.data?.[0]?.id||'');
  async function submit(e:FormEvent){
    e.preventDefault();
    const result=await execute('POST','/api/v1/admin/lenders/'+lenderId+'/users',
      {email,password},'Lender administrator account created.');
    if(result){setEmail('');setPassword('');}
  }
  return <>
    <PageTitle eyebrow="PLATFORM ADMIN / ACCESS" title="User access and roles"
      description="Provision accounts for fictional lender administrators. Borrowers self-register."/>
    <div className="portal-columns">
      <Panel title="Create lender administrator">
        <form className="form-stack" onSubmit={submit}>
          <InstitutionSelect lenders={lenders.data||[]} value={lenderId} onChange={setChosen}/>
          <FormField label="Work email"><input type="email" required value={email}
            onChange={e=>setEmail(e.target.value)}/></FormField>
          <FormField label="Temporary password (12+ characters)"><input type="password"
            minLength={12} required value={password} onChange={e=>setPassword(e.target.value)}/></FormField>
          <Submit busy={busy}>Create lender administrator</Submit>
        </form>
        <Feedback error={error} success={success}/>
      </Panel>
      <Panel title="Role boundaries">
        <div className="item-list">
          <div className="list-entry"><span className="entry-main"><strong>Borrower</strong><small>Own applications, documents, demo offers and mock loan servicing</small></span></div>
          <div className="list-entry"><span className="entry-main"><strong>Lender administrator</strong><small>Read products and policies; no raw borrower applications without consent</small></span></div>
          <div className="list-entry"><span className="entry-main"><strong>Human reviewer</strong><small>Assigned synthetic evidence verification and research views</small></span></div>
          <div className="list-entry"><span className="entry-main"><strong>Platform administrator</strong><small>Manage fictional institutions and run preliminary lending evaluations</small></span></div>
        </div>
        <Notice>A full user directory, account disabling interface, and audited role assignment workflow are not yet exposed by the backend. This page only provisions lender admins.</Notice>
      </Panel>
    </div>
  </>;
}
