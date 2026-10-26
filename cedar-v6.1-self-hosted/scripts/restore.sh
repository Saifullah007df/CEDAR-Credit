#!/bin/sh
set -eu
: "${POSTGRES_USER:=cedar}"
: "${POSTGRES_DB:=cedar}"
BACKUP="${1:?Supply backup dump path}"
: "${CEDAR_RESTORE_CONFIRM:?Set CEDAR_RESTORE_CONFIRM=I_UNDERSTAND_DATA_WILL_BE_REPLACED}"
[ "$CEDAR_RESTORE_CONFIRM" = I_UNDERSTAND_DATA_WILL_BE_REPLACED ] || exit 3
sha256sum -c "$BACKUP.sha256"
pg_restore --clean --if-exists --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$BACKUP"
printf 'Restore completed. Run source integrity/reconciliation gates BEFORE reopening publication.\n'
