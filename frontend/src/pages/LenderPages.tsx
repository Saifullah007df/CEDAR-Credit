import { useState } from 'react';
import { ArrowRight, Landmark, ListChecks } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useSession } from '../lib/session';
import { DataState, Empty, Metric, Notice, PageTitle, Panel, StatePill,
  money, useLoad } from '../components/Shared';
import type { Lender, LoanProduct, LenderPolicy } from '../lib/types';

export function LenderDashboard() {
  const {identity}=useSession();
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const products=useLoad<LoanProduct[]>('/api/v1/products');
  const visible=products.data?.filter(p=>identity?.role==='platform_admin'||p.lender_id===identity?.lender_id);
  const lenderName=lenders.data?.find(l=>l.id===identity?.lender_id)?.name;
  return <>
    <PageTitle eyebrow="LENDER WORKSPACE" title={lenderName||'Lender overview'}
      description="Review fictional lending products and versioned eligibility policies."/>
    <div className="metric-row">
      <Metric label="Visible products" value={visible?.length??'—'}/>
      <Metric label="Lender account" value={identity?.lender_id?('#'+identity.lender_id):'Platform admin'}/>
      <Metric label="Financial integrations" value="None" note="Synthetic lender sandbox"/>
    </div>
    <div className="panel-grid">
      <Link to="/lender/products" className="quick-card"><Landmark size={25}/>
        <h3>Loan products</h3><p>Inspect simulated loan amounts and APRs.</p><ArrowRight size={17}/></Link>
      <Link to="/lender/policies" className="quick-card"><ListChecks size={25}/>
        <h3>Lending policies</h3><p>Review active and historical eligibility rules.</p><ArrowRight size={17}/></Link>
    </div>
    <Notice>Borrower applications are not shared with lender administrators until an explicit consent-based sharing workflow is implemented. Only the platform admin can run preliminary evaluations.</Notice>
  </>;
}

export function LenderProducts(){
  const {identity}=useSession();
  const state=useLoad<LoanProduct[]>('/api/v1/products');
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  return <>
    <PageTitle eyebrow="LENDER / PRODUCTS" title="Loan product catalog"
      description="Synthetic products published for each fictional lending institution."/>
    <Panel><DataState state={state}>{rows=>{
      const visible=rows.filter(x=>identity?.role==='platform_admin'||x.lender_id===identity?.lender_id);
      return visible.length===0
        ? <Empty title="No products configured" description="A platform administrator can configure synthetic loan products."/>
        : <div className="product-grid">{visible.map(p=><article className="product-card" key={p.id}>
          <span className="page-eyebrow">{lenders.data?.find(l=>l.id===p.lender_id)?.name||'Lender #'+p.lender_id}</span>
          <h3>{p.name}</h3><div className="product-rate">{p.apr}% <small>demo annual APR</small></div>
          <div className="product-range"><span>Minimum {money(p.min_amount)}</span><span>Maximum {money(p.max_amount)}</span></div>
          <StatePill value="synthetic"/>
        </article>)}</div>;
    }}</DataState></Panel>
    <Notice>Products are demonstration records and cannot be directly purchased or applied for at a real financial institution.</Notice>
  </>;
}

export function LenderPolicies() {
  const {identity}=useSession();
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const [chosen,setChosen]=useState('');
  const visible=lenders.data?.filter(l=>identity?.role==='platform_admin'||l.id===identity?.lender_id)||[];
  const lenderId=Number(chosen||visible[0]?.id||0);
  const state=useLoad<LenderPolicy[]>(lenderId?'/api/v1/lenders/'+lenderId+'/policies':null);
  return <>
    <PageTitle eyebrow="LENDER / POLICIES" title="Versioned lending policies"
      description="Inspect deterministic predicates with an auditable version history."/>
    <Panel title="Institution">
      {lenders.loading?<p>Loading lenders…</p>:visible.length===0
        ? <Empty title="No authorized lender" description="Your account is not associated with a fictional lending institution."/>
        : <label className="field-label max-form">Choose lender
          <select value={chosen||String(visible[0].id)} onChange={e=>setChosen(e.target.value)}>
            {visible.map(l=><option value={l.id} key={l.id}>{l.name}</option>)}</select></label>}
    </Panel>
    {lenderId>0&&<Panel title="Policy history" sub="Previous versions are retained, even after replacement.">
      <DataState state={state}>{policies=>policies.length===0
        ? <Empty title="No policies published" description="A platform administrator must publish an initial lending policy."/>
        : <div className="policy-stack">{policies.map(p=><div className="policy-card" key={p.id}>
          <div className="portal-panel-head"><div><h3>Version {p.version}</h3><p>Policy #{p.id}</p></div>
            <StatePill value={p.active?'active':'historical'}/></div>
          <div className="data-table-wrap"><table className="data-table"><thead><tr>
            <th>Evidence dependency</th><th>Operator</th><th>Threshold</th><th>Mandatory</th>
          </tr></thead><tbody>{p.rules.map(r=><tr key={r.id}>
            <td><strong>{r.field_key}</strong></td><td>{r.operator}</td>
            <td>{JSON.stringify(r.target)}</td><td>{r.required?'Yes':'No'}</td>
          </tr>)}</tbody></table></div></div>)}</div>}</DataState>
    </Panel>}
    <Notice>Lender policies are read-only here. Publishing and changing lender rules requires platform administrator privileges.</Notice>
  </>;
}
