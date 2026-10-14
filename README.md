# CEDAR-Credit — Phase 1

**Counterfactual Evidence-Dependency and Adaptive Review for Agricultural Credit**  
Research prototype for the Samunnati Finance × Isolated Labs × G19A project discussion.

**Current status:** Phase 1 application foundation. No lending decisions, borrower-data storage, authentication, real OCR, or financial transactions are implemented.

## Technology
- React 18, TypeScript, Vite, React Router, Lucide icons.
- Python FastAPI, Pydantic Settings, versioned REST endpoints.
- Planned Phase 2: PostgreSQL, SQLAlchemy and Alembic migrations. The database is intentionally not connected in Phase 1.

## Run locally

Requires Python 3.11+ and Node 20+.

**Terminal A — backend**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal B — frontend**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to FastAPI at `localhost:8000`.

For production builds configure an API reverse proxy or equivalent route forwarding; the Vite development proxy is not part of `vite preview`.

## Tests
```bash
cd backend && pytest -q
cd frontend && npm run typecheck && npm run build
```

API docs: http://localhost:8000/docs. Health: http://localhost:8000/api/v1/health.

## Architecture

A modular monolith is planned, with separate services for:

1. Identity and consent (Phase 2)
2. Applications and lender catalog (Phase 3)
3. RG-03 versioned business rules (Phase 4)
4. RG-02 documents and evidence registry (Phase 5)
5. Evidence dependency and counterfactual engine (Phase 6)
6. RG-09 review scheduler and selective re-evaluation (Phase 7)
7. Offers, mock disbursements and repayment (Phase 8)
8. RG-04 end-use evidence verification (Phase 9)
9. System integration, audit and regression checks (Phase 10)

See [docs/architecture.md](docs/architecture.md) for boundaries and phase acceptance criteria.

## Security

- No genuine identity, loan, or payment services are connected.
- Do not upload personal or financial records to this scaffold.
- No passwords, keys, or sensitive sample borrower data are committed.
- Server-side access control and persistent storage are **planned, not implemented**.

## Repository status

This code can be committed into a newly created `CEDAR-Credit` GitHub repository. Phase 1 does not claim production readiness or verified research novelty.
