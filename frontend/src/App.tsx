import { useState } from 'react';
import { Activity, BookOpen, Building2, ChevronDown, ClipboardList, CreditCard,
  FileCheck2, FileSearch, FlaskConical, GitBranch, Landmark, LayoutDashboard,
  ListChecks, LogOut, Menu, ShieldCheck, Sprout, Wallet, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import Workbench from './Workbench';
import { useSession, type Role } from './lib/session';
import { AuthPage, roleHome } from './pages/AuthPages';
import { BorrowerDashboard, BorrowerApplications, ApplyLoan, BorrowerApplicationDetail, BorrowerLoans, LoanDetail } from './pages/BorrowerPages';
import { AdminDashboard, AdminLenders, AdminApplications, AdminApplicationDetail, AdminLoans } from './pages/AdminPages';
import { LenderDashboard, LenderProducts, LenderPolicies } from './pages/LenderPages';
import { ReviewerDashboard, ReviewTaskDetail } from './pages/ReviewPages';
import { ResearchDashboard, ResearchApplication } from './pages/ResearchPages';

type NavItem = { label: string; to: string; icon: LucideIcon; end?: boolean };
type Workspace = { title: string; tagline: string; links: NavItem[]; roles: Role[] };

const workspaces: Record<string, Workspace> = {
  borrower: {
    title: 'Borrower Portal', tagline: 'Apply · Track · Compare',
    roles: ['borrower'],
    links: [
      {label:'Dashboard',to:'/borrower',icon:LayoutDashboard,end:true},
      {label:'My Applications',to:'/borrower/applications',icon:ClipboardList},
      {label:'Apply for Loan',to:'/borrower/apply',icon:CreditCard},
      {label:'My Loans',to:'/borrower/loans',icon:Wallet},
    ],
  },
  lender: {
    title:'Lender Portal',tagline:'Products · Policies',roles:['lender_admin','platform_admin'],
    links:[
      {label:'Dashboard',to:'/lender',icon:LayoutDashboard,end:true},
      {label:'Loan Products',to:'/lender/products',icon:Landmark},
      {label:'Lending Policies',to:'/lender/policies',icon:ListChecks},
    ],
  },
  admin: {
    title:'Platform Admin',tagline:'Marketplace oversight',roles:['platform_admin'],
    links:[
      {label:'Dashboard',to:'/admin',icon:LayoutDashboard,end:true},
      {label:'Manage Lenders',to:'/admin/lenders',icon:Building2},
      {label:'Applications',to:'/admin/applications',icon:ClipboardList},
      {label:'Mock Loan Servicing',to:'/admin/loans',icon:Wallet},
      {label:'Review Queue',to:'/review',icon:FileCheck2},
      {label:'CEDAR Research',to:'/research',icon:GitBranch},
      {label:'API Console (dev)',to:'/developer',icon:FlaskConical},
    ],
  },
  review: {
    title:'Human Review',tagline:'Evidence · Corrections',roles:['reviewer','platform_admin'],
    links:[
      {label:'Review Queue',to:'/review',icon:FileSearch,end:true},
      {label:'Decision Analysis',to:'/research',icon:Activity},
    ],
  },
  research: {
    title:'CEDAR Research',tagline:'Explainability · Stability',roles:['reviewer','borrower','platform_admin'],
    links:[
      {label:'Research Dashboard',to:'/research',icon:LayoutDashboard,end:true},
      {label:'My Workspace',to:'/',icon:BookOpen},
    ],
  },
};

function Protected({ allow }: { allow: Role[] }) {
  const { identity, loading } = useSession();
  const location = useLocation();
  if (loading) return <div className="page-loader">Restoring your secure session…</div>;
  if (!identity) return <Navigate to="/login" replace state={{from:location.pathname}}/>;
  if (!allow.includes(identity.role)) return <Navigate to={roleHome(identity.role)} replace/>;
  return <Outlet/>;
}

function RoleLanding() {
  const { identity, loading } = useSession();
  if (loading) return <div className="page-loader">Loading workspace…</div>;
  return <Navigate to={identity ? roleHome(identity.role) : '/login'} replace/>;
}

function PortalLayout({ workspace }: { workspace: keyof typeof workspaces }) {
  const { identity, logout } = useSession();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const config = workspaces[workspace];
  const extra: NavItem[] = identity?.role === 'platform_admin' && workspace !== 'admin'
    ? [{label:'Admin Home',to:'/admin',icon:ShieldCheck}] : [];
  const shortName = identity?.email.split('@')[0] || 'User';
  return <div className="portal-layout">
    <aside className={'portal-sidebar ' + (open ? 'is-open' : '')}>
      <Link to="/" className="portal-brand"><span className="brand-symbol"><Sprout size={25}/></span>
        <span><strong>CEDAR-Credit</strong><small>Credit Marketplace</small></span>
      </Link>
      <div className="portal-workspace-tag"><span>YOUR WORKSPACE</span>
        <strong>{config.title}</strong><small>{config.tagline}</small>
      </div>
      <nav aria-label={config.title + ' navigation'} className="portal-nav">
        {config.links.concat(extra).map(item => <NavLink key={item.to} end={item.end} to={item.to}
          onClick={() => setOpen(false)}
          className={({isActive}) => 'portal-nav-item ' + (isActive ? 'selected' : '')}>
          <item.icon size={18}/><span>{item.label}</span></NavLink>)}
      </nav>
      <div className="portal-sidebar-bottom"><div className="sandbox-chip"><ShieldCheck size={15}/> Research sandbox</div>
        <p>Synthetic data only. No formal credit approvals or money transfers.</p></div>
    </aside>
    {open && <button type="button" className="portal-backdrop"
      onClick={() => setOpen(false)} aria-label="Close navigation"/>}
    <div className="portal-body">
      <header className="portal-topbar">
        <button className="menu-toggle" onClick={() => setOpen(!open)} aria-label="Toggle navigation">
          {open ? <X size={22}/> : <Menu size={22}/>}</button>
        <div className="portal-topbar-title"><span>CEDAR-Credit</span><span className="slash">/</span>
          <strong>{config.title}</strong></div>
        <div className="portal-topbar-user"><div className="user-badge">{shortName[0]?.toUpperCase() || 'U'}</div>
          <span><strong>{shortName}</strong><small>{identity?.role.replaceAll('_',' ')}</small></span>
          <ChevronDown size={15}/>
          <button className="signout" title="Sign out" aria-label="Sign out"
            onClick={() => { void logout(); }}><LogOut size={18}/></button>
        </div>
      </header>
      <main className="portal-content" key={location.pathname}><Outlet/></main>
      <footer className="portal-footer">CEDAR-Credit · Student research prototype · No live lender integrations</footer>
    </div>
  </div>;
}

export default function App() {
  return <Routes>
    <Route path="/" element={<RoleLanding/>}/>
    <Route path="/login" element={<AuthPage mode="login"/>}/>
    <Route path="/register" element={<AuthPage mode="register"/>}/>

    <Route element={<Protected allow={workspaces.borrower.roles}/>}>
      <Route element={<PortalLayout workspace="borrower"/>}>
        <Route path="/borrower" element={<BorrowerDashboard/>}/>
        <Route path="/borrower/applications" element={<BorrowerApplications/>}/>
        <Route path="/borrower/apply" element={<ApplyLoan/>}/>
        <Route path="/borrower/applications/:id" element={<BorrowerApplicationDetail/>}/>
        <Route path="/borrower/loans" element={<BorrowerLoans/>}/>
        <Route path="/borrower/loans/:id" element={<LoanDetail/>}/>
      </Route>
    </Route>
    <Route element={<Protected allow={workspaces.lender.roles}/>}>
      <Route element={<PortalLayout workspace="lender"/>}>
        <Route path="/lender" element={<LenderDashboard/>}/>
        <Route path="/lender/products" element={<LenderProducts/>}/>
        <Route path="/lender/policies" element={<LenderPolicies/>}/>
      </Route>
    </Route>
    <Route element={<Protected allow={workspaces.admin.roles}/>}>
      <Route element={<PortalLayout workspace="admin"/>}>
        <Route path="/admin" element={<AdminDashboard/>}/>
        <Route path="/admin/lenders" element={<AdminLenders/>}/>
        <Route path="/admin/applications" element={<AdminApplications/>}/>
        <Route path="/admin/applications/:id" element={<AdminApplicationDetail/>}/>
        <Route path="/admin/loans" element={<AdminLoans/>}/>
        <Route path="/developer" element={<Workbench/>}/>
      </Route>
    </Route>
    <Route element={<Protected allow={workspaces.review.roles}/>}>
      <Route element={<PortalLayout workspace="review"/>}>
        <Route path="/review" element={<ReviewerDashboard/>}/>
        <Route path="/review/tasks/:id" element={<ReviewTaskDetail/>}/>
      </Route>
    </Route>
    <Route element={<Protected allow={workspaces.research.roles}/>}>
      <Route element={<PortalLayout workspace="research"/>}>
        <Route path="/research" element={<ResearchDashboard/>}/>
        <Route path="/research/applications/:id" element={<ResearchApplication/>}/>
      </Route>
    </Route>

    <Route path="/operations" element={<RoleLanding/>}/>
    <Route path="*" element={<div className="missing-page"><h1>Page not found</h1><Link to="/">Return to your workspace</Link></div>}/>
  </Routes>;
}
