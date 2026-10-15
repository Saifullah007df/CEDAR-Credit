// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

const auth = vi.hoisted(() => ({
  role: 'borrower',
  authenticated: true,
}));
vi.mock('../lib/session', () => ({
  useSession: () => ({
    identity: auth.authenticated
      ? { id: 8, email: 'test@example.test', role: auth.role,
          lender_id: auth.role === 'lender_admin' ? 1 : null,
          csrf_token: 'test-csrf' }
      : null,
    loading: false,
    request: async (_method: string, path: string) => {
      if (path.endsWith('/lenders')) return [{ id: 1, name: 'Synthetic Lender A' }];
      if (path.endsWith('/products')) return [{ id: 1, lender_id: 1, name: 'Demo product',
        min_amount: 100000, max_amount: 1000000, apr: 11 }];
      if (path.endsWith('/health')) return { status: 'ok' };
      return [];
    },
    logout: async () => {},
    login: async () => {},
    register: async () => {},
  }),
}));

function startAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
}

beforeEach(() => {
  auth.role = 'borrower';
  auth.authenticated = true;
});
afterEach(() => cleanup());

describe('role-separated portal routing', () => {
  it('shows the borrower menu without platform administration links', () => {
    startAt('/borrower');
    const nav = screen.getByRole('navigation', { name: 'Borrower Portal navigation' });
    expect(nav.textContent).toContain('My Applications');
    expect(nav.textContent).toContain('Apply for Loan');
    expect(nav.textContent).not.toContain('Manage Lenders');
    expect(nav.textContent).not.toContain('Review Queue');
  });

  it('renders the lender portal without borrower application access', () => {
    auth.role = 'lender_admin';
    startAt('/lender');
    const nav = screen.getByRole('navigation', { name: 'Lender Portal navigation' });
    expect(nav.textContent).toContain('Loan Products');
    expect(nav.textContent).toContain('Lending Policies');
    expect(nav.textContent).not.toContain('My Applications');
  });

  it('shows administrator-specific navigation only for administrators', () => {
    auth.role = 'platform_admin';
    startAt('/admin');
    const nav = screen.getByRole('navigation', { name: 'Platform Admin navigation' });
    expect(nav.textContent).toContain('Manage Lenders');
    expect(nav.textContent).toContain('Applications');
    expect(nav.textContent).toContain('Review Queue');
  });

  it('redirects unauthorized borrower visits to their own portal', async () => {
    startAt('/admin');
    expect((await screen.findByRole('navigation', {
      name: 'Borrower Portal navigation',
    })).textContent).toContain('My Applications');
  });

  it('directs signed-out users to the sign-in screen', async () => {
    auth.authenticated = false;
    startAt('/borrower/apply');
    expect(await screen.findByText('Sign in to your workspace')).toBeTruthy();
  });
});
