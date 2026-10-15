import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

export type Role = 'borrower' | 'lender_admin' | 'platform_admin' | 'reviewer';
export type Identity = {
  id: number;
  email: string;
  role: Role;
  lender_id: number | null;
  csrf_token: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function call<T>(
  method: string, path: string, body?: unknown, csrf?: string | null,
): Promise<T> {
  const isForm = body instanceof FormData;
  const response = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(body !== undefined && !isForm ? { 'Content-Type': 'application/json' } : {}),
      ...(csrf && method !== 'GET' ? { 'X-CSRF-Token': csrf } : {}),
    },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });
  const data: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data
      ? (data as { detail: unknown }).detail : data;
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
    throw new ApiError(response.status, message || 'Request failed');
  }
  return data as T;
}

type SessionContextValue = {
  identity: Identity | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, legalName: string, borrowerType: string) => Promise<void>;
  logout: () => Promise<void>;
  request: <T = unknown>(method: string, path: string, body?: unknown) => Promise<T>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let live = true;
    call<Identity>('GET', '/api/v1/auth/me')
      .then(user => { if (live) setIdentity(user); })
      .catch(() => { if (live) setIdentity(null); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await call('POST', '/api/v1/auth/login', { email, password });
    const user = await call<Identity>('GET', '/api/v1/auth/me');
    setIdentity(user);
  }, []);

  const register = useCallback(async (email: string, password: string, legalName: string, borrowerType: string) => {
    await call('POST', '/api/v1/auth/register', {
      email, password, legal_name: legalName, borrower_type: borrowerType,
    });
    await login(email, password);
  }, [login]);

  const logout = useCallback(async () => {
    try {
      await call('POST', '/api/v1/auth/logout');
    } finally {
      setIdentity(null);
    }
  }, []);

  const request = useCallback(async <T,>(method: string, path: string, body?: unknown): Promise<T> => {
    try {
      return await call<T>(method, path, body, identity?.csrf_token);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setIdentity(null);
      throw error;
    }
  }, [identity?.csrf_token]);

  const value = useMemo(() => ({ identity, loading, login, register, logout, request }),
    [identity, loading, login, register, logout, request]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const session = useContext(SessionContext);
  if (!session) throw new Error('Session context is missing');
  return session;
}
