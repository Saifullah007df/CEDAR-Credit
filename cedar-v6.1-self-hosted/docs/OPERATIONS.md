# CEDAR v6 — Operational instructions

## Runtime networking
- All application calls are to local `/v1/*` API endpoints.
- No required live external APIs, CDN assets, OAuth providers, or commercial OCR services.
- Database is on an internal Compose network. API is bound to the host loopback interface; never publish this directly to the Internet.
- TLS termination, system updates and approved network access are the deploying institution's responsibility.

## Offline preparation
Connected build machine: `sh scripts/export_offline_images.sh`, then verify image tar checksum and transfer it with the source tree to the offline host. Offline host: `sha256sum -c cedar-v6-images.tar.sha256 && docker load -i cedar-v6-images.tar`, then `docker compose up -d --no-build`. The offline host must already have Docker/Compose installed. Local malware signatures must be pre-provisioned and refreshed under an offline update policy; stale or missing signatures are a deployment blocker for document ingestion.

## Recovery
Before applying migrations: perform a PostgreSQL dump and back up encrypted document data separately. Example PostgreSQL backup on deployment host:

```sh
docker compose exec -T db pg_dump -U cedar -Fc cedar > cedar-backup.dump
sha256sum cedar-backup.dump > cedar-backup.dump.sha256
```

Restoration is a controlled maintenance operation requiring the company DBA, backup integrity check, full DB restore, document storage recovery, outbox/event replay reconciliation, and source watermark validation before publishing new assessments. Do not attempt arbitrary restoration against a running live service.

## Data retention and evidence
The package does not provide an approved institutional retention matrix or WORM archive. Document upload hashes and ordinary database audit rows are *not* a substitute for tamper-evident externally protected archives. Do not call this production certified until the requirements are implemented and independently validated.
