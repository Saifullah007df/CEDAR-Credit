# CEDAR-Credit

**Counterfactual Evidence-Dependency and Adaptive Review for Agricultural Credit** — a full-stack **research prototype**, developed for the Samunnati Finance × Isolated Labs × G19A student-project context.

> **Important:** Everything here uses synthetic lenders and mock transactions. The system does **not** approve real credit, transfer money, verify real KYC or establish that its research architecture is patentably novel.

[Frontend/Backend CI](.github/workflows/) · [Local setup](docs/local-run.md) · [Architecture](docs/architecture.md) · [API and safety](docs/api-and-safety.md)

## What is implemented

| Phase | Component | Status in this prototype |
|---|---|---|
| 1 | React, TypeScript, Vite, FastAPI, responsive portals | Functional |
| 2 | PostgreSQL/SQLAlchemy schema, Alembic migrations, JWT and roles | Functional prototype |
| 3 | FPO/borrower applications, fictional lenders and loan products | Functional prototype |
| 4 | RG-03: versioned deterministic multi-lender rules | Functional prototype |
| 5 | RG-02: versioned evidence, private documents, optional OCR/text extraction | Partial: OCR depends on local Tesseract; human verification mandatory |
| 6 | Evidence-to-rule edges and bounded counterfactual stability | Functional for supported finite rules and evidence candidates |
| 7 | RG-09: review priority, verified revisions, targeted recomputation and snapshots | Functional prototype |
| 8 | Offers, nonbinding agreements, simulated disbursement and amortization | Mock-only, no real financial activity |
| 9 | RG-04: end-use evidence links and manual utilization review | Mock-only, no automatic fraud conclusion |
| 10 | Unit/integration tests, CI, seed script, API/architecture docs | Automated checks provided |

A **single React Operations Workbench** is accessible from the project sidebar and from each module's route. It calls real authenticated FastAPI endpoints, not hardcoded eligibility screens. API details are at `/docs` on the backend.

## Quick start (Linux / Fedora)

Requirements: Python 3.11–3.13, Node 20+, PostgreSQL or SQLite. Docker Compose is optional for PostgreSQL.

In two terminals, from the repository root:

**Terminal 1 — API**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,ocr]'
cp .env.example .env
# In backend/.env, set JWT_SECRET to 48+ random characters.
# For the simplest local demo, keep DATABASE_URL=sqlite:///./cedar_credit.db.
alembic upgrade head
python -m app.cli create-admin admin@example.test
python -m app.cli seed-demo
python -m uvicorn app.main:app --reload --port 8000
```

Generate a development JWT secret with:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

**Terminal 2 — Web UI**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173/operations**. For PostgreSQL/Docker instructions, see [docs/local-run.md](docs/local-run.md). The example admin account must be created using the CLI; borrower accounts can register in the workbench.

## Synthetic turnover demonstration

1. Create a borrower application for INR 500,000.
2. Enter an unverified `turnover` observation of `1300000` and alternative `[1800000]`.
3. Evaluate seeded fictional Lender A (minimum INR 1,500,000) and Lender B (minimum INR 1,000,000).
4. A fails and is counterfactually unstable; B passes and remains stable relative to the supplied candidates.
5. Schedule human review. Verify/correct the fact to INR 1,800,000, creating evidence revision 2.
6. Check that affected rules are selectively recomputed and old evaluations remain in history.
7. Explore optional synthetic offers, mock payments, and utilization evidence.

Note that **counterfactual stability only quantifies over provided candidate values** and that the decision result is **preliminary**.

## Tests and safety

The CI workflows run TypeScript checking, a Vite production build, PostgreSQL migrations, synthetic seeding, and Python unit/integration tests. Green checks verify source/build/test behavior, **not** bank-grade security, OCR accuracy or production readiness.

No private credentials, actual borrower documents, or payment information should be committed. Keep any `.env` file, virtual environments, uploads and local databases outside version control.

**Research status:** Individual approaches (OCR, rule engines, provenance, feature acquisition, decision review) have known prior art. The particular architecture's novelty, robustness and empirical advantage are **not proven** by this prototype.
