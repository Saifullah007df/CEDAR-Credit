# CEDAR-Credit architecture and phase boundaries

## Phase 1: implemented

```text
React + TypeScript + React Router
       | /api/v1 GET
       v
Vite development proxy -----> FastAPI
                                |-- health
                                |-- capabilities
                                +-- architecture
```

The `capabilities` and `architecture` endpoints are the single source of truth for planned/implemented module status in the UI. No lending results are generated.

## Planned modular monolith

```text
Borrower Portal / Lender Portal / Admin / Reviewer
       |
Authentication, Consent & Role Enforcement (Phase 2)
       |
Loan Application Service (Phase 3)
       |
Document Extraction & Evidence Registry (Phase 5, RG-02)
       |
Evidence-to-Rule Dependency Graph (Phase 6)
       |
Versioned Multi-Lender Business Rules Engine (Phase 4, RG-03)
       |
Counterfactual Decision Stability (Phase 6)
       |
Adaptive Human Review (Phase 7, RG-09)
       |
Evidence Revision & Selective Re-evaluation (Phase 7)
       |
Offer & Mock Loan Lifecycle (Phase 8)
       |
Purpose-Evidence Monitoring (Phase 9, RG-04)
```

The build order intentionally establishes an independent rules engine before connecting evidence dependencies and human review. Phase 6-7 will close the feedback loop.

## Implementation constraints

- PostgreSQL relational versioned evidence and policy tables, foreign keys, provenance.
- SQLAlchemy + Alembic migrations, server-side auth and RBAC in Phase 2.
- Rules must declare dependencies and generate explanations from executed predicates, not language-model guesses.
- Missing information must remain UNKNOWN; provisional lender eligibility is not formal lender approval.
- Counterfactual analysis considers only supported evidence candidates and constraints; unsupported cases remain unresolved.
- Review must preserve history and update decisions; targeted recomputation must agree with full evaluation.
- Keep post-disbursement utilization checking separate from automatic fraud classification.

## Phase 1 acceptance tests

1. `/api/v1/health` is online and versioned.
2. `/api/v1/capabilities` identifies exactly the implemented Phase 1 foundation.
3. `/api/v1/architecture` declares planned components honestly.
4. React portal routes render and link correctly.
5. Frontend consumes backend statuses rather than fabricated application counts or credit results.
6. Unknown API operations return 404 rather than pretending to function.
