#!/usr/bin/env bash
# Restores a backup into a scratch database, boots Odoo against it once,
# then optionally cleans the scratch database back up. This is the
# "prove the backup is restorable" rehearsal that production operators
# should run routinely instead of trusting dumps they have never tested.
#
# Usage: scripts/verify_backup.sh [--keep-restored-db] <backup_dir> <scratch_db_name>

set -euo pipefail

usage() {
    echo "Usage: verify_backup.sh [--keep-restored-db] <backup_dir> <scratch_db_name>" >&2
    exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEEP_RESTORED_DB=0
cleanup_restored_db() {
    docker compose exec -T db psql -U odoo -d postgres -v ON_ERROR_STOP=1 \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${SCRATCH_DB}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
    docker compose exec -T db dropdb -U odoo --if-exists "$SCRATCH_DB" >/dev/null 2>&1 || true
    docker compose exec -T odoo rm -rf "/var/lib/odoo/filestore/${SCRATCH_DB}" >/dev/null 2>&1 || true
}

while [ $# -gt 0 ]; do
    case "$1" in
        --keep-restored-db)
            KEEP_RESTORED_DB=1
            shift
            ;;
        --)
            shift
            break
            ;;
        -*)
            usage
            ;;
        *)
            break
            ;;
    esac
done

BACKUP_DIR="${1:-}"
SCRATCH_DB="${2:-}"

[ -n "$BACKUP_DIR" ] || usage
[ -n "$SCRATCH_DB" ] || usage

if [[ ! "$SCRATCH_DB" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Scratch database name '${SCRATCH_DB}' contains unsupported characters." >&2
    exit 1
fi

echo "[$(date)] Restoring ${BACKUP_DIR} into scratch database '${SCRATCH_DB}'..."
"${SCRIPT_DIR}/restore_db.sh" --yes "$BACKUP_DIR" "$SCRATCH_DB"
trap cleanup_restored_db EXIT

echo "[$(date)] Booting Odoo once against '${SCRATCH_DB}' to verify registry startup..."
docker compose run --rm --no-deps odoo \
    odoo -c /etc/odoo/odoo.conf -d "$SCRATCH_DB" \
    --without-demo=all --stop-after-init

echo "[$(date)] Running a simple SQL smoke check..."
MODULE_COUNT="$(docker compose exec -T db psql -U odoo -d "$SCRATCH_DB" -tAc 'SELECT COUNT(*) FROM ir_module_module;' | tr -d '[:space:]')"
if [ -z "$MODULE_COUNT" ] || [ "$MODULE_COUNT" = "0" ]; then
    echo "Scratch database '${SCRATCH_DB}' restored, but ir_module_module is empty." >&2
    exit 1
fi
if [ "$KEEP_RESTORED_DB" -eq 1 ]; then
if [ "$KEEP_RESTORED_DB" -eq 1 ]; then
    trap - EXIT
    echo "[$(date)] Backup verification succeeded. Kept scratch database '${SCRATCH_DB}' for inspection."
    exit 0
fi

echo "[$(date)] Cleaning scratch database '${SCRATCH_DB}' back up..."
cleanup_restored_db
trap - EXIT

echo "[$(date)] Backup verification succeeded."
