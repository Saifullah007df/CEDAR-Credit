# CEDAR v6.1 — Self-hosted, role-separated loan evidence and financial reconciliation

**Status: functional self-hosted development build; NOT a production-authorized banking product.** No GitHub push has occurred. This package contains real backend operations and local browser UI, plus reproducible migration/tests. It requires **no external bank, lending, OCR, SMS, authentication or cloud API during normal runtime.** The browser calls only the locally hosted FastAPI application (`/v1/*`).

## Implemented and tested in this package

- FastAPI + SQLAlchemy financial and evidence operations; PostgreSQL is the configured deployment database.
- Versioned Alembic migrations (two revisions). Clean **SQLite** migration run verified here; **PostgreSQL migration/container execution not verifiable in the current environment**.
- Controlled loan records; signed-off *imported* balanced double-entry journal records, journal readout and provisional loan-level checks.
- Offline UTF-8 CSV / XLSX transaction import with required row identifiers, count checks and duplicate rejection.
- Source payment batches; amount-and-category-constrained transaction-to-invoice allocation and reversals.
- Invoice evidence review; immutable original files, local PDF text extraction and English/Tamil Tesseract OCR; versioned text corrections remain separate from source OCR.
- Effective-dated policy versions, provisional evidence utilization assessment and stored versioned snapshots.
- Local hashed-password accounts, role-based permissions, account lockout, offline TOTP MFA for provisioned accounts, and scoped loan access outside demo mode.
- Durable PostgreSQL outbox table, local polling worker that recomputes changed-loan snapshots, activity audit records and operations queue status.
- Browser UI served directly by FastAPI (no Node or external CDN at runtime), with role-specific operations, plus a separate Borrower/FPO portal and read-only Lender Workspace.
- Existing React+TypeScript UI *source* also included, but not compiled/verified: npm dependency installation was blocked in this environment. The directly served no-build UI is the operational frontend in this package.
- Thirteen automated Python backend test groups pass, including strict borrower/lender API isolation, account provisioning, loan-grant revocation and document submission. An initial and an additive Alembic migration were applied to a clean SQLite database.

### Not yet demonstrated / not ready to claim

**DO NOT process live borrower data until independently approved and tested.** This release does NOT establish completeness of data received from an external LMS/GL; it cannot prove physical loan utilization; it does not replace a bank core ledger. It does not implement complex multiple-tranche source posting/settlement reconciliation, robust invoice-line/quantity-based goods-receipt matching, multi-step evidence approval for invoice verification, audit WORM archival, full malware-signature distribution, independent privileged access certification, verified HA or RPO/RTO, production load testing, regulatory approval or a bank-approved source connector. These require actual institutional contracts/data policies and additional engineering. See `docs/RELEASE_GATES.md` and `docs/ROLE_PORTALS.md`.

## Deployment (Docker Compose, on a prepared host)

Requirements: Docker Engine with Compose v2, sufficient disk, Linux host, reviewed local images. **No third-party API at runtime.** The container build from source needs package downloads unless images/dependencies have been pre-provisioned; for an offline host use `scripts/export_offline_images.sh` on a connected staging host and `docker load` after checksum verification.

1. Copy `.env.example` to `.env`; replace all placeholder passwords with random strong values. Never commit `.env`.
2. To enable production document uploads, provision **offline ClamAV signature databases** in `deploy/clamav`. If signatures are absent or local `clamscan` fails, uploads fail closed; financial ingestion and case work still run.
3. Start:

   ```sh
   docker compose up -d --build
   docker compose ps
   ```

   `api` applies Alembic migrations before starting; `worker` starts after API health passes. PostgreSQL is private to the Compose network. The browser application is bound to **127.0.0.1:8000**; access through a company-approved TLS reverse proxy or a secured tunnel before exposing it to any network. It is **not** Internet-exposed by the supplied manifest.

4. Bootstrap the first admin through the controlled container command, using a secret supplied securely into `CEDAR_ADMIN_PASSWORD` (minimum 16 characters). For example, inside a private container shell:

   ```sh
   export CEDAR_ADMIN_PASSWORD='REPLACE_WITH_A_PRIVATE_STRONG_PASSWORD'
   python -m backend.create_admin
   unset CEDAR_ADMIN_PASSWORD
   ```

   The command outputs a **one-time offline TOTP key** for private enrollment in an authenticator app. The admin must provide that six-digit code during login. Keep the key secret. The seed command is **not** run in production.

5. Go to http://127.0.0.1:8000, log in with your provisioned username/password/TOTP, create staff from the API (see `/docs`), and grant loan access to non-admin staff (`POST /v1/staff/loan-access`). Explicitly import authorized source data via CSV/XLSX or the internal API.

**Deployment limitation:** The supplied Compose, including its PostgreSQL migration and worker, has been prepared and syntax-inspected but has **not** been run in this container because Docker/PostgreSQL are unavailable here. Before any real operation, run the release gates and source-specific validation with a company security/finance owner.

## Local development without Docker

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export CEDAR_DEMO_MODE=true
export CEDAR_AUTO_CREATE_SCHEMA=true
export DATABASE_URL=sqlite:///./cedar_demo.db
python -m backend.seed      # SYNTHETIC USERS/RECORDS ONLY
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Development fixtures: `admin`, `reviewer`, `operator`, `approver`, `auditor`, `lender`, `borrower`, password `DemoOnly!123`. Borrower and lender users see different portals with backend-enforced access. **Never expose demo mode or its fixed credentials to an untrusted network.**

Tests:

```sh
PYTHONPATH=. pytest -q
CEDAR_DEMO_MODE=true CEDAR_AUTO_CREATE_SCHEMA=false DATABASE_URL=sqlite:////tmp/cedar_test_migrate.db alembic upgrade head
```

## Source/data governance

CEDAR does **not** claim to know Samunnati's real chart of accounts, authoritative journal mapping or loan-purpose rules. Files and examples are synthetic. Use original source IDs and signed-off balance and completeness controls. The distinction between recorded transfer, documented purchase, delivery, approved purpose and final human decision is mandatory. A `SUPPORTED` expenditure is evidence-supported under the implemented checks, **not conclusive proof** that funds were physically used as claimed.

## Role-separated portals

- `/` — unified login, redirects borrower to `/borrower.html`, lender to `/lender.html`, and shows role-filtered internal staff workspaces.
- Borrower: assigned loans, invoice submissions, document uploads, submission statuses. No internal case notes, source journals or lender access.
- Lender: assigned loan portfolio, read-only evidence, utilization and journal-reconciliation summary. No borrower uploads or staff approvals.
- Admin: local account provisioning, loan assignment and revocation.
- No public signup, and no external API provider required. The frontend communicates with its own local FastAPI backend only.

## Operational documentation

- `docs/RELEASE_GATES.md`: acceptance gates and unverified production components.
- `docs/ROLE_PORTALS.md`: complete role matrix, endpoints and isolation-test notes.
- `docs/OPERATIONS.md`: backups, restore, offline images, and security constraints.
- `examples/`: synthetic offline bank CSV and sample journal API JSON.
- `alembic.ini` and `migrations/`: database schema revisions.
- `tests/`: API and regression tests.

## GitHub

No GitHub repository has been created or updated. Obtain explicit review and approval before publication.
