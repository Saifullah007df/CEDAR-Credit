# API behavior and safety boundaries

## Authentication
`POST /api/v1/auth/register` creates borrower accounts only. Administrators
are created through the CLI. `POST /api/v1/auth/login` returns an 8-hour JWT.
`GET /api/v1/auth/me` accepts a bearer token or a browser session cookie.
The browser uses an HttpOnly SameSite=Strict cookie, with Secure enabled in
production, and obtains a CSRF token via /me for modifying requests. The cookie
persists across page refreshes (8-hour token expiration). The existing bearer
API remains supported. Neither JWTs nor login passwords are stored in browser
localStorage or sessionStorage.

## Market lifecycle
`/api/v1/admin/lenders`, `/api/v1/admin/lenders/{id}/products`, and
`/api/v1/admin/lenders/{id}/policies` configure fictional lender products and
versioned policies. `/api/v1/applications` stores borrower-owned applications.
`/api/v1/applications/{id}/documents` stores validated PDF/PNG/JPEG documents
locally with SHA-256 provenance. Optional extraction paths return text and
human-review candidate suggestions; these do not directly grant eligibility.
`/api/v1/applications/{id}/evidence` accepts manual unverified candidate facts.

## CEDAR research loop
- Versioned rules and evidence-to-rule dependency edges are persisted.
- `/evaluate` executes the deterministic predicate evaluator (PASS/FAIL/UNKNOWN).
- `/counterfactual` enumerates finite supported candidate worlds (capped at 128).
- `/schedule-review` ranks unverified evidence by dependencies and potential
  decision change.
- `/review/tasks/{id}/verify` commits a new evidence version, preserves old
  snapshots and selectively recomputes dependent rules. Exact equality with a
  full recomputation is asserted at the algorithm boundary.
- No proof of global counterfactual invariance or statistical fairness is claimed.

## Restricted/off-limits functionality
The simulator does **not** contact banks, disburse funds, make legally enforceable
agreements, infer fraud from a claim, or provide actual credit approvals.
The `/mock-` routes persist simulated statuses and audit events only.
Only an authenticated application owner, authorized administrator, or reviewer
can access an application's records. Lender administrators are intentionally
restricted to product and policy information, pending explicit lender-consent
and per-application sharing controls.

## Remaining production gaps
Formal KYC/consent enforcement, access revocation, encryption at rest,
file scanning, rate limiting, privacy governance, detailed lender-access consent,
complete repayment servicing, OCR accuracy evaluation and legal review are
required before real-world use.
