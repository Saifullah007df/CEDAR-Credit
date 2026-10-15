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
    <Heading eyebrow="RESEARCH PLATFORM · PHASE 1" title="A clearer path to responsible agricultural credit" description="CEDAR-Credit connects document evidence, lending rules, and transparent decision workflows. This release contains the verified application foundation; financial operations will be added in subsequent phases." />
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
    <Notice>No borrower records, lending decisions, bank integrations, or AI predictions are implemented in Phase 1. This interface does not simulate those capabilities.</Notice>
  </>;
}

const plannedPages: Record<string, { title: string; phase: string; description: string; items: string[] }> = {
  borrower: { title: 'Borrower Portal', phase: 'PHASE 3', description: 'Application and FPO profile workflows will be implemented with secured backend data.', items: ['Borrower profiles', 'Agricultural loan applications', 'Evidence upload', 'Loan status and offers'] },
  lender: { title: 'Lender Portal', phase: 'PHASES 3–4', description: 'Lender-specific loan products, versioned policies, and controlled decisions.', items: ['Lender product catalog', 'Configurable eligibility rules', 'Review of permitted applications', 'Explainable outcomes'] },
  admin: { title: 'Platform Administration', phase: 'PHASES 2–3', description: 'The administrative workspace will manage verified activity and permissions.', items: ['Identity and roles', 'Lender administration', 'Application monitoring', 'System audit events'] },
  review: { title: 'Human Review Workspace', phase: 'PHASE 7', description: 'Human verification is scheduled only after the evidence and dependency systems are functional.', items: ['Uncertain evidence queue', 'Decision-impact prioritization', 'Source-backed correction', 'Selective recalculation'] },
  research: { title: 'CEDAR Research Engine', phase: 'PHASES 4–7', description: 'The central algorithms will be implemented in testable server-side services.', items: ['RG-02 evidence records', 'RG-03 lending policies', 'Counterfactual stability', 'RG-09 adaptive review'] },
};

function Planned({ id }: { id: keyof typeof plannedPages }) {
  const content = plannedPages[id];
  return <>
    <Heading eyebrow={`${content.phase} · PLANNED`} title={content.title} description={content.description} />
    <section className="surface"><div className="section-header"><h2>Planned capabilities</h2><Badge status="planned" /></div><div className="future-grid">{content.items.map(item => <div className="future-item" key={item}><Layers size={18} aria-hidden="true"/><span>{item}</span></div>)}</div></section>
    <Notice>Not implemented in Phase 1. Controls for live applications or credit decisions are intentionally unavailable until database, authorization, and corresponding services are tested.</Notice>
    <NavLink className="text-link" to="/operations">Try the functional API workbench <ArrowRight size={16}/></NavLink>
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
      <div className="side-bottom"><div className="side-status"><CheckCircle2 size={17}/> Foundation · Phase 1</div><span>Synthetic-data research prototype</span></div>
    </aside>
    {open && <button className="overlay" aria-label="Close navigation" onClick={() => setOpen(false)} />}
    <div className="main-col"><header className="topbar"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setOpen(true)}><Menu size={22}/></button><div className="breadcrumb">CEDAR-Credit <span>/</span> Research Platform</div><div className="topbar-right"><span className="top-chip"><Database size={15}/> API-backed scaffold</span><span className="avatar" aria-label="Demo platform user">C</span></div></header>
      <main className="content"><Routes><Route path="/" element={<Overview/>}/><Route path="/operations" element={<Workbench/>}/><Route path="/borrower" element={<Planned id="borrower"/>}/><Route path="/lender" element={<Planned id="lender"/>}/><Route path="/admin" element={<Planned id="admin"/>}/><Route path="/review" element={<Planned id="review"/>}/><Route path="/research" element={<Planned id="research"/>}/><Route path="/architecture" element={<Architecture/>}/><Route path="*" element={<div className="surface"><h1>Page not found</h1><NavLink className="text-link" to="/">Return to overview</NavLink></div>}/></Routes></main>
      <footer className="footer">CEDAR-Credit · Research prototype · Not a banking or lending service</footer>
    </div>
  </div>;
}

export default Shell;
