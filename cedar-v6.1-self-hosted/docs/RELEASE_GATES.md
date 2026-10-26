# CEDAR v6 — Go/no-go and missing production requirements

## Evidence from this build
- [x] Python API regression tests (10 test groups) pass in SQLite test environment.
- [x] Two Alembic revisions apply against a clean SQLite database.
- [x] Offline CSV/XLSX ingestion, balanced journal, policy change and document correction APIs exercised.
- [x] Local outbox worker exercised under SQLite.
- [ ] PostgreSQL Compose boot with migrations and persistence after restart (Docker unavailable in current environment).
- [ ] PostgreSQL concurrent allocation race/load tests (SQLite tests are not a substitute).
- [ ] React production build (`npm` package install unavailable); no-build operational browser UI supplied.
- [ ] Browser E2E against live backend (browser navigation blocked by host policy; HTTP API separately tested).
- [ ] Malware scanner signatures provisioned and signature freshness verified.
- [ ] Comprehensive financial ledger import/GL and bank settlement mapping validated with company accounting SMEs.
- [ ] Company-approved source completeness watermark, bank-transaction authenticity, and period close controls.
- [ ] Multi-supplier, refunds, credit notes, partial deliveries, cross-loan invoice-line capacity and fund-attribution methodology.
- [ ] Approved effective-dated loan-purpose policies and exceptions for the actual product.
- [ ] Enterprise authorization/privacy penetration test, audit tamper evidence and legal retention policy.
- [ ] Operational backup+restore, recovery, and incident response drills.
- [ ] Authorized real-data pilot with reconciliation and false-allegation/critical-error metrics.
- [ ] Formal company compliance/IT/risk/finance operational sign-off.

**Go** for code review, development and authorized isolated testing. **No-go** for live financial processing or external exposure.
