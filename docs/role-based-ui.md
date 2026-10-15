# Role-specific frontend redesign

The original Operations Workbench placed every operation on one screen. The new
React Router frontend uses separate pages and role-gated navigation. API
authorization remains the authoritative enforcement point.

## Route hierarchy

| Role | Dashboard | Other screens |
| --- | --- | --- |
| Borrower | /borrower | /borrower/apply; /borrower/applications; /borrower/applications/:id (Overview / Documents / Evidence / Decisions / Offers); /borrower/loans; /borrower/loans/:id |
| Lender admin | /lender | /lender/products; /lender/policies |
| Platform admin | /admin | /admin/lenders; /admin/products; /admin/policies; /admin/users; /admin/applications; /admin/applications/:id; /admin/loans; /developer |
| Reviewer | /review | /review/tasks/:id |
| Research (authorized roles) | /research | /research/applications/:id |

The administrator may also enter the lender, reviewer, and research workspaces.
Reviewers and borrowers can only access research views for applications that
their existing backend authorization allows. Lender admins **cannot** view raw
borrower applications until consent-based disclosure is implemented.

The old operations interface is retained only at **/developer**, accessible to
platform administrators, for low-level API testing.

## Authentication behavior

- The browser logs in using a short-lived session cookie set by FastAPI.
- The cookie is HttpOnly, SameSite=Strict, and is flagged Secure in production.
- Browser POST requests include a CSRF token obtained from /api/v1/auth/me.
- The session is restored across browser refreshes; sign-out clears the cookie.
- Existing programmatic bearer-token API clients continue to work.
- No bearer tokens or login credentials are written to localStorage or sessionStorage.
- Protected routes use the role from the authenticated server session. The
  frontend route guard is a usability control; backend RBAC remains mandatory.

## Guided borrower flow

1. Register as a borrower or sign in.
2. Create a synthetic loan request through a three-step wizard.
3. Open the application detail page.
4. Upload synthetic supporting documents; optionally run local text extraction.
5. Record unverified candidate evidence and alternatives.
6. An administrator runs preliminary lender rules and schedules a review.
7. The reviewer opens an actual queue entry, inspects evidence and verifies.
8. Borrower and research screens display recalculated and historical outcomes.
9. Administrator may generate a provisional **mock** offer only when backend
   eligibility constraints permit it.
10. A borrower can accept a mock offer and inspect a simulated payment schedule.

## Status and scope

- All counts and application records are retrieved from APIs, not hardcoded.
- The demo includes a document upload limit of 5 MB and server-side file-type checks.
- The CEDAR graph illustrates explicit single-field rule dependencies and is not
  a general-purpose semantic knowledge graph.
- No automatic actual credit approvals, live KYC, real payments, or fraud
  judgments are implemented.
- The role-based frontend is a research prototype, not an audited financial UI.

## Updating an existing Fedora clone without losing test data

From a VS Code terminal:

    cd ~/Downloads/CEDAR-Credit
    git status
    git pull origin main

If git reports local uncommitted edits, review them before pulling; don't run
a destructive reset. Keep \`backend/.env\` and \`backend/cedar_credit.db\` intact.
The SQLite database and .env are ignored by Git; they should not be deleted.

Backend (Terminal 1):

    cd ~/Downloads/CEDAR-Credit/backend
    source .venv/bin/activate
    python -m pip install -e '.[dev,ocr]'
    alembic upgrade head
    python -m uvicorn app.main:app --reload --port 8000

Frontend (Terminal 2):

    cd ~/Downloads/CEDAR-Credit/frontend
    npm install
    npm run dev

Then open http://localhost:5173/. The app redirects to /login (signed out)
or the dashboard matching the current authenticated role.

For regression tests run \`cd backend && python -m pytest -q\` and
\`cd frontend && npm run test && npm run typecheck && npm run build\`.
