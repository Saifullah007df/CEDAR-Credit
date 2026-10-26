# CEDAR v6.1 — Role-separated portals

## What changed

The **same local FastAPI deployment** hosts three distinct entry points: `/` for sign-in and authorized internal workspaces, `/borrower.html` for Borrower/FPO self-service, and `/lender.html` for the lender's assigned portfolio. Server-side access controls, not HTML routing, enforce separation. No external/third-party API service is necessary at runtime.

## Account and module matrix

| Role | Portal | Access and actions | Explicitly restricted |
|---|---|---|---|
| borrower | `/borrower.html` | Own assigned loans; own invoice submission; document upload; document/invoice status | All staff financial APIs, other borrowers' loans, source batches, internal exceptions, audit, user creation |
| lender | `/lender.html` | Assigned portfolio, loan utilization and evidence overview, read-only imported reconciliation | Borrower submission endpoints, user administration, ledger writes, case approval, unrestricted portfolio access |
| operator | `/` | Imported financial sources, ledgers, allocation work | Final case approvals, user provisioning |
| reviewer | `/` | Document evidence verification, review proposals, limited operational views | Approve own case proposal, user provisioning, journal ingestion |
| approver | `/` | Independent review approval and selected audit/policy operations | New bank-source ingestion, borrower self-service, user provisioning |
| auditor | `/` | Read-only assigned financial/evidence history and audit | All mutation endpoints |
| admin | `/` | User provisioning, access grants/revocation, account administration (also legacy v6 privileged operations) | Production needs separate break-glass and least-privilege hardening |

**Important limitation:** The original v6 `admin` role retains legacy financial and review permissions to preserve existing behavior. This must be split into a least-privileged platform administrator and a separately audited break-glass role before institutional live rollout. The `lender` role in this release is intentionally read-only; underwriting and lending decisions remain under authorized finance/approver workflows.

## Demo account sign-in (synthetic development mode only)

1. Start the local development server with `CEDAR_DEMO_MODE=true` and seed using `python -m backend.seed` on a fresh database.
2. At `/`, sign in with account `borrower` or `lender`; password `DemoOnly!123` for these **synthetic demonstration accounts only**.
3. The server returns the authenticated user role; the UI sends the user to their role's portal.
4. Borrower creates an unverified invoice or uploads evidence. Lender can inspect assigned invoice evidence but cannot approve or change it. `reviewer` has separate evidence confirmation and review case tools. `admin` manages users and loan access.
5. Sign-out calls `/v1/auth/logout` and revokes the current token version (currently revokes all sessions for that user).

## Production staff and borrower provisioning

Only administrators can create accounts. There is **no public self-signup**. Use these internal endpoints:

| Endpoint | Role | Purpose |
|---|---|---|
| `POST /v1/admin/borrowers` | admin | Create borrower account; assign its initial loan |
| `POST /v1/staff` with role `lender` | admin | Create lender account, initially without loan access |
| `POST /v1/staff/loan-access` | admin | Grant an existing borrower/lender/staff user access to a specific loan |
| `POST /v1/admin/revoke-loan-access` | admin | Revoke a loan assignment immediately |
| `GET /v1/admin/users` | admin | List roles and scope assignments (no password disclosure) |
| `GET /v1/auth/me` | authenticated | Verified role, permitted portal, assigned loan IDs |

Borrower authentication uses the existing Argon2 password hashing and signed expiring JWTs. Production privileges enforce offline TOTP MFA for administrators and approvers; extending borrower MFA, account recovery, username enumeration controls, security headers, and fine-grained role administration requires institutional hardening before public exposure.

## Technical safeguards

- Borrower routes call `require('borrower')` and check `LoanAccess` even in development mode; borrower loans are scoped on *every* endpoint.
- Lender routes call `require('lender')` and use assigned-loan queries; they are read-only.
- Staff APIs explicitly reject borrower tokens. Borrower invoice submissions create `document_verified=False` and `delivery_verified=False`; users cannot mark their own evidence verified.
- Staff cannot directly access borrower submission endpoints because they require the borrower role.
- In the main UI, staff navigation and actions filter by verified role; server permissions are still checked on every request.
- The login role is resolved against the database on `/v1/auth/me`; changing local role labels cannot obtain new backend rights.
- Tests check direct unauthorized requests (403), cross-loan isolation, uploaded source status, grant revocation and token invalidation on logout.

## Verification and known limitations

- `python -m pytest -q tests`: **13 passed** in development SQLite test configuration.
- Embedded browser-interface JavaScript: passes `node --check` for all three portal pages.
- FastAPI endpoints tested using TestClient, not a full browser-to-PostgreSQL deployment. Browser navigation to the local server is blocked in the current testing environment; no live-browser end-to-end test is claimed.
- PostgreSQL/Docker/backup/real-institution integration remains to be tested before live deployment.
- The accompanying `CEDAR_role_portal_preview.html` is a standalone interactive **UI simulation**, not a connected banking product.

No GitHub changes or push have been performed.
