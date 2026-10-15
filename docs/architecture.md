# CEDAR-Credit architecture — integrated prototype

## Runtime

```
React/TypeScript/Vite  →  FastAPI modular monolith
         |                       |
         |                 JWT authentication
         |                       |
         |  ┌────────────────────┴─────────────────────┐
         |  | Borrowers, lender products, applications |
         |  | Docs & RG-02 versioned evidence registry |
         |  | RG-03 policies and executable predicates |
         |  | Evidence-to-rule dependency edge table   |
         |  | Bounded counterfactual stability checks  |
         |  | RG-09 prioritized human review           |
         |  | New evidence revision + targeted rules   |
         |  | Immutable prior evaluation snapshots     |
         |  | Mock offers/payments/amortization         |
         |  | RG-04 purpose-evidence claim links        |
         |  └────────────────────┬─────────────────────┘
         |                       |
         └────────────── PostgreSQL / SQLAlchemy
                                 |
                       Alembic schema migrations
```

All application operations require server-side authorization. The front-end holds the bearer token in React memory; it does not persist to localStorage. Lender administrators do not receive access to raw borrower applications pending a consent-sharing model.

## Domain invariants

1. **Evidence provenance:** files are SHA-256 identified in private local storage, extraction records preserve the engine and language, and evidence revisions preserve previous observations, candidate values and actor IDs.
2. **Versioned rules:** each lender policy version contains deterministic predicates referencing explicit evidence keys. Publishing a new version does not edit the prior policy's rules.
3. **No unknown-as-pass:** absent or invalid values yield UNKNOWN. Mandatory failures yield FAIL; only all-passing mandatory rules produce PASS.
4. **Counterfactual space:** finite candidate worlds (including the current observation) are enumerated with a 128-world cap. Oversized/unsupported spaces return unknown stability rather than 'stable'.
5. **Review priority:** affected lender decisions and dependency counts influence task ordering. This is a proof-of-concept priority score, **not** an optimized cost-sensitive research scheduler.
6. **Recalculation:** human verification creates a new immutable evidence revision. Dependent policy evaluations are regenerated, old snapshots remain, and targeted rule result reuse must equal full deterministic evaluation results in the supported scope.
7. **Finance boundaries:** PASS ≠ lender approval. Offers, agreement text, disbursement, amortization and repayment are simulated; no bank API is called.
8. **Post-disbursement checks:** utilization claims are attached to optional evidence documents. A manual 'evidence present' review is not a fraud verdict.

## API boundaries

- Identity: `/api/v1/auth/*`
- Lenders/policies/products: `/api/v1/admin/lenders/*`, `/api/v1/lenders`, `/api/v1/products`
- Borrower applications/documents/evidence: `/api/v1/applications/*`
- Counterfactual and evaluation snapshots: `/api/v1/applications/{id}/counterfactual`, `/evaluations`
- Reviewer: `/api/v1/review/tasks` and `/api/v1/review/tasks/{task_id}/verify`
- Mock offers/loan: `/api/v1/offers/*`, `/api/v1/loans/*`
- Utilization: `/api/v1/loans/{id}/utilization`, `/api/v1/admin/utilization/{claim_id}/review`

Refer to the FastAPI `/docs` UI for detailed schemas.

## Explicit limits

- Optional Tesseract OCR requires binary, language packs and OCR dependencies; scanned PDFs are not rasterized. The financial-field suggestion extractor is heuristic and unverified.
- Evidence dependencies currently map individual evidence keys to rules; the project does not implement arbitrary multi-hop semantic provenance graphs or automatic evidence confidence calibration.
- Counterfactual enumeration and review priorities do not provide calibrated decision-risk estimates or a globally optimal verification sequence.
- Simulated financial lifecycle is not legally binding or suitable for real funds.
- Requires privacy/security assessment, consent management, encryption, malware scanning, rate limiting, comprehensive fairness and integration tests before real-world financial use.
- Architecture novelty and nonobviousness require a separate documented prior-art study; no patentability assurance is made.
