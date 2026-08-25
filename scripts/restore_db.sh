#!/usr/bin/env bash
# Restores a database + filestore from a backup produced by
# backup_db.sh. DESTRUCTIVE: drops the target database first if it
# already exists. Always test a restore on a throwaway database name
# before you ever need to do it for real - a backup you haven't
# rehearsed restoring is not a verified backup.
#
# Usage: scripts/restore_db.sh [--yes] [--skip-checksums] <backup_dir> <target_db_name>
# Example: scripts/restore_db.sh --yes backups/acme_prod_20260401_020000 acme_prod_restored

set -euo pipefail

usage() {
    echo "Usage: restore_db.sh [--yes] [--skip-checksums] <backup_dir> <target_db_name>" >&2
    exit 1
}

ASSUME_YES=0
SKIP_CHECKSUMS=0

while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes)
            ASSUME_YES=1
            shift
            ;;
        --skip-checksums)
            SKIP_CHECKSUMS=1
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
TARGET_DB="${2:-}"

[ -n "$BACKUP_DIR" ] || usage
[ -n "$TARGET_DB" ] || usage

if [[ ! "$TARGET_DB" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Target database name '${TARGET_DB}' contains unsupported characters." >&2
    exit 1
fi

if [ ! -f "${BACKUP_DIR}/db.dump" ]; then
    echo "No db.dump found in ${BACKUP_DIR} - is this a valid backup directory?" >&2
    exit 1
fi

if [ -f "${BACKUP_DIR}/SHA256SUMS" ] && [ "$SKIP_CHECKSUMS" -ne 1 ]; then
    echo "[$(date)] Verifying backup checksums..."
    (
        cd "$BACKUP_DIR"
        sha256sum -c SHA256SUMS
    )
fi

if [ "$ASSUME_YES" -ne 1 ]; then
    read -r -p "This will DROP database '${TARGET_DB}' if it exists, then restore from ${BACKUP_DIR}. Continue? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Aborted."
        exit 1
    fi
fi

TEMP_FILESTORE_DIR="/tmp/restore_filestore_${TARGET_DB}_$$"
cleanup() {
    docker compose exec -T odoo rm -rf "$TEMP_FILESTORE_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[$(date)] Dropping '${TARGET_DB}' if it exists..."
docker compose exec -T db psql -U odoo -d postgres -v ON_ERROR_STOP=1 \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${TARGET_DB}' AND pid <> pg_backend_pid();" >/dev/null
docker compose exec -T db dropdb -U odoo --if-exists "$TARGET_DB"

echo "[$(date)] Creating '${TARGET_DB}'..."
docker compose exec -T db createdb -U odoo "$TARGET_DB"

echo "[$(date)] Restoring database dump..."
docker compose exec -T db pg_restore -U odoo -d "$TARGET_DB" --no-owner < "${BACKUP_DIR}/db.dump"

if [ -f "${BACKUP_DIR}/filestore.tar.gz" ]; then
    echo "[$(date)] Restoring filestore..."
    docker compose exec -T odoo rm -rf "/var/lib/odoo/filestore/${TARGET_DB}"
    # The archive's top-level folder is named after the ORIGINAL
    # database, not necessarily TARGET_DB (e.g. restoring a prod
    # backup into a differently-named scratch DB to verify it) -
    # extract to a temp name, then move into place under the target
    # name so the filestore path Odoo expects always matches.
    docker compose exec -T odoo mkdir -p "$TEMP_FILESTORE_DIR"
    docker compose exec -T odoo tar -xzf - -C "$TEMP_FILESTORE_DIR" < "${BACKUP_DIR}/filestore.tar.gz"
    ORIGINAL_NAME=$(docker compose exec -T odoo sh -c "find '$TEMP_FILESTORE_DIR' -mindepth 1 -maxdepth 1 -type d | head -1 | xargs -r basename" | tr -d '\r')
    if [ -z "$ORIGINAL_NAME" ]; then
        echo "Unable to determine the original filestore directory name from ${BACKUP_DIR}/filestore.tar.gz." >&2
        exit 1
    fi
    docker compose exec -T odoo mv "${TEMP_FILESTORE_DIR}/${ORIGINAL_NAME}" "/var/lib/odoo/filestore/${TARGET_DB}"
else
    echo "[$(date)] No filestore.tar.gz in backup - attachments/PDFs will be missing after restore."
fi

trap - EXIT
cleanup

echo "[$(date)] Restore complete. Log in and verify before treating '${TARGET_DB}' as trustworthy."
