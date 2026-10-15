import { useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowLeft, ArrowRight, ClipboardCheck } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { DataState, Empty, ErrorBanner, Feedback, FormField, Metric, Notice,
  PageTitle, Panel, StatePill, Submit, useAction, useLoad } from '../components/Shared';
import type { Evidence, EvidenceRevision, ReviewTask } from '../lib/types';

export function ReviewerDashboard() {
  const tasks=useLoad<ReviewTask[]>('/api/v1/review/tasks');
  return <>
    <PageTitle eyebrow="HUMAN REVIEW WORKSPACE" title="Evidence review queue"
      description="Prioritized tasks are ranked by affected rules and potential decision instability."/>
    <div className="metric-row"><Metric label="Open review tasks" value={tasks.data?.length??'—'}/>
      <Metric label="Highest priority" value={tasks.data?.length?Math.max(...tasks.data.map(t=>t.priority)):'—'}/>
      <Metric label="Manual verification" value="Required"/></div>
    <Panel title="Pending verification" sub="Open a task to inspect candidate evidence and verify a corrected value">
      <DataState state={tasks}>{items=>items.length===0
        ? <Empty title="Queue is clear" description="No unverified evidence is currently scheduled for manual review."/>
        : <div className="item-list">{items.map(t=><Link className="list-entry" to={'/review/tasks/'+t.id} key={t.id}>
          <span className="entry-icon"><ClipboardCheck size={19}/></span>
          <span className="entry-main"><strong>Review task #{t.id} · Application #{t.application_id}</strong>
            <small>{t.reason} · Evidence fact #{t.fact_id}</small></span>
          <span className="priority-score">Priority {t.priority}</span><ArrowRight size={17}/>
        </Link>)}</div>}</DataState>
    </Panel>
    <Notice>The review priority score is an experimental decision-impact heuristic. It does not measure calibrated credit risk.</Notice>
  </>;
}

export function ReviewTaskDetail(){
  const {id}=useParams();
  const taskId=Number(id);
  const queue=useLoad<ReviewTask[]>('/api/v1/review/tasks');
  const task=queue.data?.find(t=>t.id===taskId);
  const evidence=useLoad<Evidence[]>(task?'/api/v1/applications/'+task.application_id+'/evidence':null);
  const history=useLoad<EvidenceRevision[]>(task?'/api/v1/applications/'+task.application_id+
    '/evidence/'+task.fact_id+'/history':null);
  const fact=evidence.data?.find(f=>f.id===task?.fact_id);
  const [verifiedValue,setVerifiedValue]=useState('');
  const [note,setNote]=useState('Confirmed against the original source document (demo)');
  const [confirmed,setConfirmed]=useState(false);
  const {execute,busy,error,success}=useAction();
  const navigate=useNavigate();
  async function verify(e:FormEvent){
    e.preventDefault();
    if(!task||!confirmed)return;
    let value:unknown;
    try{value=JSON.parse(verifiedValue);}
    catch{value=verifiedValue;}
    const result=await execute('POST','/api/v1/review/tasks/'+task.id+'/verify',
      {value,note},'Evidence revision saved. Affected lender decisions recalculated.');
    if(result)navigate('/review',{replace:true});
  }
  return <>
    <Link className="back-link" to="/review"><ArrowLeft size={16}/> Review queue</Link>
    <PageTitle eyebrow="HUMAN REVIEW / TASK" title={'Verification task #'+taskId}
      description="Review a source fact and its alternatives before recording a verified revision."/>
    <DataState state={queue}>{tasks=>{
      const current=tasks.find(t=>t.id===taskId);
      return !current
        ? <Empty title="Task no longer open" description="This task may have been resolved. Return to the queue." href="/review" action="Back to queue"/>
        : <div className="metric-row"><Metric label="Application" value={'#'+current.application_id}/>
          <Metric label="Evidence record" value={'#'+current.fact_id}/>
          <Metric label="Review priority" value={current.priority}/></div>;
    }}</DataState>
    {task&&<div className="portal-columns">
      <Panel title="Evidence under review" sub="Current extracted observation and alternatives">
        <DataState state={evidence}>{items=>{
          const f=items.find(x=>x.id===task.fact_id);
          return f ? <div className="fact-inspection">
            <div className="review-summary"><span>Field key</span><strong>{f.key}</strong></div>
            <div className="review-summary"><span>Observed value</span><strong>{JSON.stringify(f.value)}</strong></div>
            <div className="review-summary"><span>Alternatives</span>
              <strong>{f.candidates.map(String).join(', ')||'None'}</strong></div>
            <div className="review-summary"><span>Source document</span><strong>{f.document_id?('#'+f.document_id):'Not linked'}</strong></div>
            <div className="review-summary"><span>Evidence revision</span><strong>v{f.version}</strong></div>
            <StatePill value={f.verified?'verified':'unverified'}/>
          </div> : <Empty title="Evidence missing" description="The referenced evidence fact was not returned."/>;
        }}</DataState>
      </Panel>
      <Panel title="Verification action" sub="Confirm the corrected value only after inspecting real supporting evidence.">
        <form className="form-stack" onSubmit={verify}>
          <FormField label="Corrected verified value (number or text)">
            <input required value={verifiedValue} onChange={e=>setVerifiedValue(e.target.value)}
              placeholder={fact?.candidates[0]!==undefined?String(fact.candidates[0]):'Enter source-confirmed value'}/>
          </FormField>
          <FormField label="Verification note">
            <textarea required value={note} onChange={e=>setNote(e.target.value)}/></FormField>
          <label className="confirm-row"><input type="checkbox" checked={confirmed}
            onChange={e=>setConfirmed(e.target.checked)}/>
            <span>I have checked supporting evidence. This is a synthetic demonstration, not a real KYC confirmation.</span></label>
          <Feedback error={error} success={success}/>
          <button className="btn btn-primary" disabled={busy||!confirmed} type="submit">
            Verify and recompute <ArrowRight size={15}/></button>
        </form>
      </Panel>
    </div>}
    {task&&<Panel title="Evidence revision history">
      <DataState state={history}>{items=>items.length===0
        ? <Empty title="No revisions" description="The first recorded version appears here."/>
        : <div className="data-table-wrap"><table className="data-table"><thead><tr>
          <th>Revision</th><th>Recorded value</th><th>Alternatives</th><th>Status</th><th>Actor ID</th>
        </tr></thead><tbody>{items.map(r=><tr key={r.version}>
          <td>v{r.version}</td><td>{String(r.value)}</td><td>{r.candidates.map(String).join(', ')||'—'}</td>
          <td><StatePill value={r.verified?'verified':'unverified'}/></td><td>#{r.actor_id}</td>
        </tr>)}</tbody></table></div>}</DataState>
    </Panel>}
    <Notice>When you verify a value, the backend preserves the old evidence and evaluation snapshots, then selectively recalculates only dependent rules.</Notice>
  </>;
}
