# Running the CEDAR-Credit research prototype

This is a **synthetic-data** platform. There is no live lender API, KYC provider,
financial approval, bank transfer or real repayment processing.

## Prerequisites

- Python 3.11–3.13, Node.js 20–22 and npm
- PostgreSQL 16 via Docker Compose (recommended) or local PostgreSQL
- Optional PDF text extraction: `pip install -e '.[ocr]'`
- Optional image OCR: system Tesseract, the required language packs, and the Python OCR extras

## Start a durable PostgreSQL database

From the project root, create a `.env` file containing
`POSTGRES_PASSWORD=<a-strong-local-password>`. The Compose port binds only
to localhost; change this default carefully. Start with `docker compose up -d postgres`.

In `backend/.env`:

```ini
DATABASE_URL=postgresql+psycopg://cedar:YOUR_PASSWORD@localhost:5432/cedar
JWT_SECRET=REPLACE_WITH_48_OR_MORE_RANDOM_CHARACTERS
CORS_ORIGINS=http://localhost:5173
ENVIRONMENT=development
STORAGE_DIR=./uploads
```

Generate a JWT secret using `python -c 'import secrets; print(secrets.token_urlsafe(48))'`.
Never commit credentials or a populated `.env`.

## Start backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,ocr]'
alembic upgrade head
python -m app.cli create-admin admin@example.test
python -m app.cli seed-demo
python -m uvicorn app.main:app --reload --port 8000
```

The admin password is entered interactively. Never use actual identity/financial
data in this demonstration. For a simpler local-only SQLite setup, use
`DATABASE_URL=sqlite:///./cedar_credit.db` and still run migrations.

## Start frontend

In a **second** terminal from the project root:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173/operations. Sign in with the administrator you
created, or register a separate borrower account via the workbench.

## Demonstrate CEDAR

1. Use the seeded fictional lenders A and B (thresholds INR 1.5m and INR 1.0m).
2. Create borrower account and an INR 500,000 application.
3. As borrower add `turnover = 1300000` with candidates `[1800000]`.
4. As admin evaluate all active lenders. A = FAIL and unstable; B = PASS and stable.
5. As admin schedule review. As admin/reviewer verify INR 1,800,000.
6. Revisit evaluations and check prior snapshots are retained; both lenders PASS.
7. With a matching product, create **provisional simulated** offer as admin.
8. Borrower accepts mock offer; admin records mock disbursement and payment.
9. Borrower adds an end-use claim linked to supporting evidence where available.

Use the browser workbench to submit all API calls or explore http://localhost:8000/docs.
If you change accounts, sign out and sign back in; browser tokens are stored in
memory only, not localStorage.

## Caveats

- Password and role checks are backend-enforced; this is not a security audit.
- File uploads are private on disk by default but require encrypted storage and
  malware scanning before production use.
- Manual evidence and OCR suggestions are *unverified*; the system never treats
  text extraction as confirmed truth.
- Numeric review priority and candidate-world enumeration are prototypes with
  supported-domain limits, not validated credit-risk models.
- The PDF text-layer extractor does not OCR scanned PDFs; Tesseract image OCR
  requires a local binary and configured language packs.
- A real repayment amortization plan, legal agreement, regulatory KYC, consent
  management and remote lender integrations are out of production scope.
- The original architecture's research novelty is unproven pending prior art
  verification and controlled experiments.
