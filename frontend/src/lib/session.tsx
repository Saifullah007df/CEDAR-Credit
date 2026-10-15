import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

type Identity = { email: string; role: string; lender_id: number | null; id: number };
type Session = {
  token: string | null;
  identity: Identity | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  request: <T=unknown>(method: string, path: string, body?: unknown, multipart?: boolean) => Promise<T>;
};
const Context = createContext<Session | null>(null);

async function apiRequest<T>(method: string, path: string, token?: string | null, body?: unknown, multipart = false): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body !== undefined && !multipart ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body === undefined ? undefined : multipart ? body as FormData : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail ?? data);
    throw new Error(`${response.status}: ${detail}`);
  }
  return data as T;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  async function login(email: string, password: string) {
    const result = await apiRequest<{ access_token: string }>('POST', '/api/v1/auth/login', null, { email, password });
    const me = await apiRequest<Identity>('GET', '/api/v1/auth/me', result.access_token);
    setToken(result.access_token);
    setIdentity(me);
  }
  function logout() { setToken(null); setIdentity(null); }
  async function request<T=unknown>(method: string, path: string, body?: unknown, multipart = false): Promise<T> {
    return apiRequest<T>(method, path, token, body, multipart);
  }
  return <Context.Provider value={{ token, identity, login, logout, request }}>{children}</Context.Provider>;
}
export function useSession() {
  const context = useContext(Context);
  if (!context) throw new Error('Authentication context unavailable');
  return context;
}
