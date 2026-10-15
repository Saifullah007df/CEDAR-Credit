import { useCallback, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { AlertCircle, ArrowRight, Inbox, LoaderCircle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useSession } from '../lib/session';

export function useLoad<T>(path: string | null) {
  const { request } = useSession();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion(v => v + 1), []);
  useEffect(() => {
    if (!path) {
      setLoading(false);
      setData(null);
      return;
    }
    let live = true;
    setLoading(true);
    setError('');
    request<T>('GET', path).then(value => {
      if (live) setData(value);
    }).catch((err: unknown) => {
      if (live) { setData(null); setError(err instanceof Error ? err.message : 'Request failed'); }
    }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [path, version, request]);
  return { data, loading, error, refresh };
}

export function money(value: number | string | undefined | null) {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(Number(value));
}

export function StatePill({ value }: { value: string | boolean | null | undefined }) {
  const label = value === null || value === undefined ? 'Unknown' : String(value);
  const positive = ['pass', 'verified', 'paid', 'stable', 'active', 'resolved', 'implemented', 'true', 'reviewed_evidence_present'].includes(label.toLowerCase());
  const negative = ['fail', 'unstable', 'overdue', 'false'].includes(label.toLowerCase());
  return <span className={'state-pill ' + (positive ? 'positive' : negative ? 'negative' : 'neutral')}>
    {label.replaceAll('_', ' ')}
  </span>;
}

export function PageTitle({ eyebrow, title, description, action }: {
  eyebrow: string; title: string; description?: string; action?: ReactNode;
}) {
  return <div className="page-heading">
    <div><div className="page-eyebrow">{eyebrow}</div><h1>{title}</h1>
      {description && <p>{description}</p>}</div>{action}
  </div>;
}

export function Panel({ title, sub, action, children }: {
  title?: string; sub?: string; action?: ReactNode; children: ReactNode;
}) {
  return <section className="portal-panel">
    {(title || action) && <div className="portal-panel-head"><div>
      {title && <h2>{title}</h2>}{sub && <p>{sub}</p>}
    </div>{action}</div>}{children}
  </section>;
}

export function Metric({ label, value, note }: {
  label: string; value: string | number; note?: string;
}) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</div>;
}

export function Loading({ label = 'Loading data…' }: { label?: string }) {
  return <div className="load-message"><LoaderCircle className="spin" size={19}/>{label}</div>;
}

export function ErrorBanner({ error, retry }: { error: string; retry?: () => void }) {
  return <div className="ui-error" role="alert">
    <AlertCircle size={18}/><span>{error}</span>
    {retry && <button type="button" onClick={retry}><RefreshCw size={15}/> Retry</button>}
  </div>;
}

export function Empty({ title, description, href, action }: {
  title: string; description: string; href?: string; action?: string;
}) {
  return <div className="empty-view">
    <Inbox size={29}/><h3>{title}</h3><p>{description}</p>
    {href && <Link className="action-link" to={href}>{action || 'Continue'} <ArrowRight size={16}/></Link>}
  </div>;
}

export function DataState<T>({ state, children, emptyTitle = 'Nothing here yet' }: {
  state: { data: T | null; loading: boolean; error: string; refresh: () => void };
  children: (data: T) => ReactNode;
  emptyTitle?: string;
}) {
  if (state.loading) return <Loading/>;
  if (state.error) return <ErrorBanner error={state.error} retry={state.refresh}/>;
  if (state.data === null) return <Empty title={emptyTitle} description="No information is available."/>;
  return <>{children(state.data)}</>;
}

export function Notice({ children }: { children: ReactNode }) {
  return <div className="portal-notice"><AlertCircle size={18}/><span>{children}</span></div>;
}

export function FormField({ label, children }: { label: string; children: ReactNode }) {
  return <label className="field-label">{label}{children}</label>;
}

export function Submit({ busy, children }: { busy?: boolean; children: ReactNode }) {
  return <button className="btn btn-primary" disabled={busy} type="submit">
    {busy ? <LoaderCircle size={16} className="spin"/> : null}{children}
  </button>;
}

export function useAction() {
  const { request } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const execute = useCallback(async <T,>(
    method: string, path: string, body?: unknown, notice?: string,
  ): Promise<T | null> => {
    setBusy(true); setError(''); setSuccess('');
    try {
      const result = await request<T>(method, path, body);
      if (notice) setSuccess(notice);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed');
      return null;
    } finally {
      setBusy(false);
    }
  }, [request]);
  return { execute, busy, error, success, clear: () => { setError(''); setSuccess(''); } };
}

export function Feedback({ error, success }: { error?: string; success?: string }) {
  return <>{error && <ErrorBanner error={error}/>}
    {success && <div className="ui-success" role="status">{success}</div>}</>;
}

export function formatDate(value: string | null | undefined) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}
