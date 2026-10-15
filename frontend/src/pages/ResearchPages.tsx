import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, GitBranch } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useSession } from '../lib/session';
import { DataState, Empty, Metric, Notice, PageTitle, Panel, StatePill,
  useLoad } from '../components/Shared';
import type { Counterfactual, Evidence, Evaluation, Lender, LenderPolicy, LoanApplication } from '../lib/types';

export function ResearchDashboard(){
  const apps=useLoad<LoanApplication[]>('/api/v1/applications');
  return <>
    <PageTitle eyebrow="CEDAR / RESEARCH" title="Decision explainability laboratory"
      description="Explore evidence-to-rule dependencies, candidate-world stability and versioned lender outcomes."/>
    <div className="metric-row"><Metric label="Supported candidate space" value="≤ 128 worlds"/>
      <Metric label="Decision states" value="PASS / FAIL / UNKNOWN"/>
      <Metric label="Decision updates" value="Versioned"/></div>
    <Panel title="Choose an application" sub="Access is limited to your own borrower applications or authorized administrative/review accounts.">
      <DataState state={apps}>{items=>items.length===0
        ? <Empty title="No accessible applications" description="Create or obtain access to a synthetic borrower application first."/>
        : <div className="item-list">{items.map(a=><Link className="list-entry" key={a.id}
          to={'/research/applications/'+a.id}><span className="entry-icon"><GitBranch size={18}/></span>
          <span className="entry-main"><strong>Application #{a.id}</strong><small>{a.loan_purpose}</small></span>
          <StatePill value={a.status}/><ArrowRight size={17}/>
        </Link>)}</div>}</DataState>
    </Panel>
    <Notice>The counterfactual analyzer enumerates supplied candidates only; this is not proof of patent novelty or robust real-world creditworthiness.</Notice>
  </>;
}

type PolicyByLender = { lender: Lender; policies: LenderPolicy[] };

export function ResearchApplication(){
  const {id}=useParams();
  const appId=Number(id);
  const {request}=useSession();
  const app=useLoad<LoanApplication>('/api/v1/applications/'+appId);
  const facts=useLoad<Evidence[]>('/api/v1/applications/'+appId+'/evidence');
  const evaluations=useLoad<Evaluation[]>('/api/v1/applications/'+appId+'/evaluations');
  const stability=useLoad<Counterfactual[]>('/api/v1/applications/'+appId+'/counterfactual');
  const lenders=useLoad<Lender[]>('/api/v1/lenders');
  const [policySets,setPolicySets]=useState<PolicyByLender[]>([]);
  const [policyError,setPolicyError]=useState('');
  useEffect(()=>{
    if(!lenders.data)return;
    let live=true;
    Promise.all(lenders.data.map(async lender=>({
      lender, policies:await request<LenderPolicy[]>('GET','/api/v1/lenders/'+lender.id+'/policies'),
    }))).then(sets=>{if(live){setPolicySets(sets);setPolicyError('');}})
      .catch((err:unknown)=>{if(live)setPolicyError(err instanceof Error?err.message:'Unable to load policies');});
    return()=>{live=false;};
  },[lenders.data,request]);
  const name=(id:number)=>lenders.data?.find(l=>l.id===id)?.name||'Lender #'+id;
  const current=evaluations.data?.filter(e=>e.current)||[];
  const edges=policySets.flatMap(group=>group.policies.filter(p=>p.active).flatMap(policy=>
    policy.rules.map(rule=>({key:rule.field_key,lender:group.lender.name,
      rule:rule.field_key+' '+rule.operator+' '+JSON.stringify(rule.target),id:rule.id}))));
  return <>
    <Link className="back-link" to="/research"><ArrowLeft size={16}/> Research dashboard</Link>
    <PageTitle eyebrow="CEDAR / APPLICATION ANALYSIS" title={'Application #'+appId+' · Research'}
      description={app.data?.loan_purpose||'Counterfactual and rule-dependency analysis'}/>
    <div className="metric-row"><Metric label="Recorded evidence fields" value={facts.data?.length??'—'}/>
      <Metric label="Current lender evaluations" value={current.length}/>
      <Metric label="Rule dependencies" value={edges.length||'—'}/></div>
    <Panel title="Evidence-to-rule dependency explorer" sub="Edges are rendered from active lender policy predicates; the backend persists rule-to-key dependencies.">
      {policyError&&<p className="work-error">{policyError}</p>}
      {!edges.length?<Empty title="No active rule dependencies" description="The platform admin must publish lender policies before dependency analysis."/>
        : <div className="graph-list" aria-label="Evidence dependency graph">
          <div className="graph-head"><strong>EVIDENCE REGISTRY</strong><strong>LENDER RULES</strong></div>
          {edges.map(e=><div className="graph-edge" key={e.lender+'-'+e.id}>
            <div className="graph-node"><span>Evidence field</span><strong>{e.key}</strong>
              <small>{facts.data?.find(f=>f.key===e.key)?.verified?'Verified':'Unverified or missing'}</small></div>
            <div className="graph-arrow"><span></span><ArrowRight size={19}/></div>
            <div className="graph-node policy-node"><span>{e.lender}</span><strong>{e.rule}</strong></div>
          </div>)}
        </div>}
    </Panel>
    <div className="portal-columns">
      <Panel title="Counterfactual stability" sub="Current value and supported candidate alternatives">
        <DataState state={stability}>{items=>items.length===0
          ? <Empty title="No analyzer output" description="Create lender policies to inspect supported candidate worlds."/>
          : <div className="item-list">{items.map(x=><div className="stability-entry" key={x.policy_id}>
            <strong>{name(x.lender_id)}</strong><StatePill value={x.stable===null?'Unknown':x.stable?'Stable':'Unstable'}/>
            <p>{x.worlds} supported world(s) · Outcomes: {x.outcomes.join(' / ')||'unresolved'}</p>
            <small>{x.reason}</small>
          </div>)}</div>}</DataState>
      </Panel>
      <Panel title="Evidence provenance">
        <DataState state={facts}>{items=>items.length===0
          ? <Empty title="No evidence" description="No evidence has been entered for this application."/>
          : <div className="item-list">{items.map(f=><div className="list-entry" key={f.id}>
            <span className="entry-main"><strong>{f.key} · v{f.version}</strong>
              <small>Observed: {String(f.value)} · Candidates: {f.candidates.map(String).join(', ')||'none'} · Source: {f.document_id?'document #'+f.document_id:'manual'}</small></span>
            <StatePill value={f.verified?'verified':'unverified'}/>
          </div>)}</div>}</DataState>
      </Panel>
    </div>
    <Panel title="Versioned decision history" sub="Current and historical snapshots support before/after comparisons">
      <DataState state={evaluations}>{items=>items.length===0
        ? <Empty title="No evaluations" description="An administrator must run a preliminary lender evaluation first."/>
        : <div className="data-table-wrap"><table className="data-table"><thead><tr>
          <th>Snapshot</th><th>Lender</th><th>Policy version</th><th>Evidence versions</th>
          <th>Outcome</th><th>Stability</th><th>Current?</th>
        </tr></thead><tbody>{items.map(x=><tr key={x.id}>
          <td>#{x.id}</td><td>{name(x.lender_id)}</td><td>#{x.policy_id}</td>
          <td>{JSON.stringify(x.evidence_versions)}</td><td><StatePill value={x.decision}/></td>
          <td><StatePill value={x.stable===null?'Unknown':x.stable?'Stable':'Unstable'}/></td>
          <td>{x.current?'Yes':'Historical'}</td></tr>)}</tbody></table></div>}</DataState>
    </Panel>
    <Notice>Incremental evaluation equality is checked by the backend. This UI visualizes declared single-field dependencies; it does not constitute a complete semantic provenance graph.</Notice>
  </>;
}
