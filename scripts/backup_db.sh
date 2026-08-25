#!/usr/bin/env bash
# Backs up the running Postgres database (and, optionally, the Odoo
# filestore — attachments, generated PDFs) to a timestamped archive
# under backups/. Intended to be run from a daily cron job; this
# script does not itself schedule anything.
#
# Usage: scripts/backup_db.sh <db_name> [backups_dir]
#
# Example crontab entry (daily at 02:00, keeping the repo's own
# backups/ directory - point BACKUP_DIR elsewhere if you'd rather
# back up to separate storage, e.g. an attached volume or object
# storage synced by a separate tool):
#   0 2 * * * cd /path/to/bpro-hrms-hcm && BACKUP_RETENTION_DAYS=30 ./scripts/backup_db.sh <db_name> >> /var/log/bpro-backup.log 2>&1
# 
# Produces:
# - db.dump (Postgres custom-format dump)
# - filestore.tar.gz (if the database has uploaded files)
# - SHA256SUMS (integrity checks for the backup artifacts)
# - metadata.env (plain key=value metadata for operators and restore tooling)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_NAME="${1:?Usage: backup_db.sh <db_name> [backups_dir]}"
BACKUP_DIR="${2:-${SCRIPT_DIR}/../backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEST="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}"
TEMP_DEST="${BACKUP_DIR}/.${DB_NAME}_${TIMESTAMP}.incomplete"

case "$RETENTION_DAYS" in
    ''|0|*[!0-9]*)
        echo "BACKUP_RETENTION_DAYS must be a positive integer, got '${RETENTION_DAYS}'." >&2
        exit 1
        ;;
esac

rm -rf "$TEMP_DEST"
mkdir -p "$TEMP_DEST"
trap 'rm -rf "$TEMP_DEST"' EXIT

echo "[$(date)] Backing up database '${DB_NAME}' to ${DEST}"

# Database dump - custom format (-Fc) so it can be restored selectively
# and is already compressed, unlike a plain SQL dump.
docker compose exec -T db pg_dump -U odoo -Fc "$DB_NAME" > "${TEMP_DEST}/db.dump"

# Filestore - attachments, generated payslip/letter/report PDFs live
# on disk, not in Postgres. Back it up alongside the DB dump so a
# restore is actually complete, not just the rows.
HAS_FILESTORE=0
if docker compose exec -T odoo test -d "/var/lib/odoo/filestore/${DB_NAME}"; then
    docker compose exec -T odoo tar -czf - -C /var/lib/odoo/filestore "$DB_NAME" \
        > "${TEMP_DEST}/filestore.tar.gz"
    HAS_FILESTORE=1
else
    echo "[$(date)] No filestore directory found for '${DB_NAME}' - skipping (nothing uploaded yet?)"
fi

{
    echo "db_name=${DB_NAME}"
    echo "created_at=$(date -Iseconds)"
    echo "retention_days=${RETENTION_DAYS}"
    echo "contains_filestore=${HAS_FILESTORE}"
    echo "git_commit=$(git -C "${SCRIPT_DIR}/.." rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "compose_project_name=${COMPOSE_PROJECT_NAME:-unknown}"
} > "${TEMP_DEST}/metadata.env"

(
    cd "$TEMP_DEST"
    sha256sum db.dump metadata.env > SHA256SUMS
    if [ "$HAS_FILESTORE" = "1" ]; then
        sha256sum filestore.tar.gz >> SHA256SUMS
    fi
)

mv "$TEMP_DEST" "$DEST"
trap - EXIT

echo "[$(date)] Backup complete: ${DEST}"

# Prune backups older than the configured retention window
# (BACKUP_RETENTION_DAYS, default 30) - adjust that to the client's
# actual policy and available storage.
find "$BACKUP_DIR" -maxdepth 1 -type d -name "${DB_NAME}_*" -mtime +"${RETENTION_DAYS}" -exec rm -rf {} \;
