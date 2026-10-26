#!/bin/sh
set -eu
: "${POSTGRES_USER:=cedar}"
: "${POSTGRES_DB:=cedar}"
DEST="${1:-/backups}"
mkdir -p "$DEST"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$DEST/cedar-$STAMP.dump"
pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$OUT"
sha256sum "$OUT" > "$OUT.sha256"
chmod 600 "$OUT" "$OUT.sha256"
printf 'Backup created: %s\n' "$OUT"
