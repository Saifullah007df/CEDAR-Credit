import { useEffect, useState } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import { Activity, ArrowRight, BookOpen, Building2, CheckCircle2, Database, FileSearch, GitBranch, Layers, LockKeyhole, Menu, ShieldCheck, Sprout, Users, Workflow, X } from 'lucide-react';
import Workbench from './Workbench';
import { api, type ArchitectureLayer, type Capability } from './lib/api';

type LoadState<T> = { data: T | null; error: string | null; loading: boolean };

function useRemote<T>(load: (signal: AbortSignal) => Promise<T>): LoadState<T> {
  const [state, setState] = useState<LoadState<T>>({ data: null, error: null, loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ data: null, error: null, loading: true });
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ data, error: null, loading: false });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ data: null, error: error instanceof Error ? error.message : 'Request failed', loading: false });
    });
    return () => controller.abort();
  }, [load]);
  return state;
}

const pages = [
  { name: 'Overview', path: '/', icon: Activity },
  { name: 'Operations Workbench', path: '/operations', icon: Layers },
  { name: 'Borrower Portal', path: '/borrower', icon: Users },
  { name: 'Lender Portal', path: '/lender', icon: Building2 },
  { name: 'Platform Admin', path: '/admin', icon: ShieldCheck },
  { name: 'Human Review', path: '/review', icon: FileSearch },
  { name: 'Research Engine', path: '/research', icon: GitBranch },
  { name: 'Architecture', path: '/architecture', icon: Workflow },
];

function Badge({ status }: { status: 'implemented' | 'planned' | 'mocked' }) {
  return <span className={`badge badge-${status}`}>{status === 'implemented' ? 'Implemented' : status === 'planned' ? 'Planned' : 'Mocked'}</span>;
}

function Heading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="heading"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>;
}

function Notice({ children }: { children: React.ReactNode }) {
  return <div className="notice"><LockKeyhole size={18} aria-hidden="true" /><div>{children}</div></div>;
}

function ErrorState({ message }: { message: string }) {
  return <div className="error" role="alert"><strong>Backend connection unavailable</strong><p>{message}</p><small>Start FastAPI on port 8000 and try refreshing. No demonstration results will be fabricated.</small></div>;
}

function Overview() {
  const health = useRemote(api.health);
  const capabilities = useRemote(api.capabilities);
  const implemented = capabilities.data?.capabilities.filter(c => c.status === 'implemented').length ?? 0;
  return <>
    <Heading eyebrow="RESEARCH PLATFORM · INTEGRATION PHASE" title="A clearer path to responsible agricultural credit" description="CEDAR-Credit connects document evidence, lending rules, and transparent decision workflows. This prototype contains API-backed research workflows and mock loan services. Real financial integrations remain out of scope." />
    <div className="stats">
      <div className="stat"><span>Backend API</span><strong className={health.data?.status === 'ok' ? 'healthy' : ''}>{health.loading ? 'Checking…' : health.data?.status === 'ok' ? 'Online' : 'Offline'}</strong><small>Real FastAPI health endpoint</small></div>
      <div className="stat"><span>Current phase</span><strong>{capabilities.data?.current_phase ?? '—'} / 10</strong><small>Incremental research build</small></div>
      <div className="stat"><span>Implemented modules</span><strong>{capabilities.data ? `${implemented} / ${capabilities.data.capabilities.length}` : '—'}</strong><small>From the backend capability catalog</small></div>
    </div>
    {health.error && <ErrorState message={health.error} />}
    <section className="surface"><div className="section-header"><div><h2>Engineering roadmap</h2><p>Live module status from the backend.</p></div><BookOpen size={21} /></div>
      {capabilities.error ? <ErrorState message={capabilities.error} /> : capabilities.loading ? <p className="muted">Loading module catalog…</p> :
        <div className="module-grid">{capabilities.data?.capabilities.map((c: Capability) => <article key={c.id} className="module"><div className="module-top"><span className="phase">PHASE {c.phase}</span><Badge status={c.status}/></div><h3>{c.title}</h3><p>{c.description}</p></article>)}</div>}
    </section>
    <Notice>This research prototype supports synthetic borrower records and preliminary lender-rule outcomes. No real bank approvals, transfers, KYC, or AI fraud verdicts are offered.</Notice>
  </>;
}

function Architecture() {
  const state = useRemote(api.architecture);
  return <>
    <Heading eyebrow="SYSTEM DESIGN · VERSIONED" title="Architecture Explorer" description="Four logical layers of the planned modular monolith. Each layer displays its actual implementation status, retrieved from FastAPI." />
    {state.error ? <ErrorState message={state.error}/> : state.loading ? <p className="muted">Loading architecture…</p> :
      <section className="architecture">{state.data?.layers.map((layer: ArchitectureLayer, index: number) => <div key={layer.name} className="architecture-stage">
        <div className="arch-card"><div className="section-header"><div><span className="phase">LAYER {index+1}</span><h2>{layer.name}</h2></div><Badge status={layer.status}/></div><div className="chips">{layer.modules.map(mod => <span className="chip" key={mod}>{mod}</span>)}</div></div>
        {index !== (state.data?.layers.length ?? 0)-1 && <div className="arch-link"><ArrowRight size={20} /></div>}
      </div>)}</section>}
    <Notice>Architecture documentation reflects intended module boundaries. Planned layers are not connected to operational financial integrations or decision services.</Notice>
  </>;
}

function Shell() {
  const [open, setOpen] = useState(false);
  return <div className="layout">
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-icon"><Sprout size={25}/></div><div><strong>CEDAR-Credit</strong><span>Research Marketplace</span></div><button className="mobile-close" onClick={() => setOpen(false)} aria-label="Close navigation"><X size={21}/></button></div>
      <div className="side-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{pages.map(p => <NavLink end={p.path === '/'} key={p.path} to={p.path} onClick={() => setOpen(false)} className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}><p.icon size={18} aria-hidden="true"/><span>{p.name}</span></NavLink>)}</nav>
      <div className="side-bottom"><div className="side-status"><CheckCircle2 size={17}/> Research prototype · Phase 10</div><span>Synthetic-data research prototype</span></div>
    </aside>
    {open && <button className="overlay" aria-label="Close navigation" onClick={() => setOpen(false)} />}
    <div className="main-col"><header className="topbar"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setOpen(true)}><Menu size={22}/></button><div className="breadcrumb">CEDAR-Credit <span>/</span> Research Platform</div><div className="topbar-right"><span className="top-chip"><Database size={15}/> API-backed scaffold</span><span className="avatar" aria-label="Demo platform user">C</span></div></header>
      <main className="content"><Routes><Route path="/" element={<Overview/>}/><Route path="/operations" element={<Workbench/>}/><Route path="/borrower" element={<Workbench/>}/><Route path="/lender" element={<Workbench/>}/><Route path="/admin" element={<Workbench/>}/><Route path="/review" element={<Workbench/>}/><Route path="/research" element={<Workbench/>}/><Route path="/architecture" element={<Architecture/>}/><Route path="*" element={<div className="surface"><h1>Page not found</h1><NavLink className="text-link" to="/">Return to overview</NavLink></div>}/></Routes></main>
      <footer className="footer">CEDAR-Credit · Research prototype · Not a banking or lending service</footer>
    </div>
  </div>;
}

export default Shell;
