import { useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, LockKeyhole, Sprout } from 'lucide-react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useSession, type Role } from '../lib/session';
import { ErrorBanner, FormField, Submit } from '../components/Shared';

export function roleHome(role: Role) {
  return role === 'borrower' ? '/borrower'
    : role === 'platform_admin' ? '/admin'
    : role === 'lender_admin' ? '/lender' : '/review';
}

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { identity, loading, login, register } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [legalName, setLegalName] = useState('');
  const [borrowerType, setBorrowerType] = useState('fpo');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!loading && identity) return <Navigate to={roleHome(identity.role)} replace/>;
  const isRegister = mode === 'register';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      if (isRegister) await register(email, password, legalName, borrowerType);
      else await login(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      // Prevent authentication redirect into a location from another role.
      navigate(from && from.startsWith('/') && !from.startsWith('//') ? from : '/',
               { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in');
    } finally { setBusy(false); }
  }

  return <div className="auth-page">
    <aside className="auth-story">
      <div className="auth-story-brand"><Sprout size={26}/> CEDAR-Credit</div>
      <div><span className="auth-small">AGRICULTURAL FINANCE · RESEARCH</span>
        <h1>Better credit journeys begin with clearer evidence.</h1>
        <p>One secure workspace for borrower applications, lender policies, human review, and traceable decisions.</p>
      </div>
      <div className="auth-disclaimer">Student research environment · Fictional lenders · No real disbursements</div>
    </aside>
    <main className="auth-main">
      <div className="auth-box">
        <div className="auth-lock"><LockKeyhole size={23}/></div>
        <span className="page-eyebrow">WELCOME TO CEDAR</span>
        <h2>{isRegister ? 'Create a borrower account' : 'Sign in to your workspace'}</h2>
        <p>{isRegister ? 'Set up your fictional farming organization profile.' :
          'Your workspace and navigation will adapt to your role.'}</p>
        <form className="form-stack" onSubmit={handleSubmit}>
          {isRegister && <>
            <FormField label="FPO or business name">
              <input required minLength={2} maxLength={150} value={legalName} onChange={e => setLegalName(e.target.value)}/>
            </FormField>
            <FormField label="Borrower category">
              <select value={borrowerType} onChange={e => setBorrowerType(e.target.value)}>
                <option value="fpo">Farmer Producer Organization (FPO)</option>
                <option value="farmer">Farmer</option>
                <option value="business">Agricultural business</option>
              </select>
            </FormField>
          </>}
          <FormField label="Email">
            <input required type="email" autoComplete="username" value={email}
                   onChange={e => setEmail(e.target.value)} placeholder="you@example.test"/>
          </FormField>
          <FormField label="Password">
            <input required type="password" minLength={isRegister ? 12 : undefined}
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              value={password} onChange={e => setPassword(e.target.value)}
              placeholder={isRegister ? 'At least 12 characters' : 'Enter your password'}/>
          </FormField>
          {error && <ErrorBanner error={error}/>}
          <Submit busy={busy}>{isRegister ? 'Create account' : 'Sign in'} <ArrowRight size={17}/></Submit>
        </form>
        <p className="auth-switch">{isRegister ? 'Already registered?' : 'New borrower?'}{' '}
          <Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Sign in' : 'Create account'}</Link>
        </p>
        <p className="auth-foot">Administrators are provisioned by the backend CLI. Browser sessions use HttpOnly cookies and CSRF protection.</p>
      </div>
    </main>
  </div>;
}
