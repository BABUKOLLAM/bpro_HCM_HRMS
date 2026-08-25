#!/usr/bin/env bash
# Finds the newest backup for a database and runs the full restore + Odoo
# boot verification against it, using a timestamped scratch database so
# the command is suitable for unattended cron/systemd scheduling.
#
# Usage: scripts/verify_latest_backup.sh <db_name> [backups_dir] [scratch_db_prefix]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_NAME="${1:?Usage: verify_latest_backup.sh <db_name> [backups_dir] [scratch_db_prefix]}"
BACKUPS_DIR="${2:-${SCRIPT_DIR}/../backups}"
SCRATCH_DB_PREFIX="${3:-${DB_NAME}_verify}"

if [[ ! "$SCRATCH_DB_PREFIX" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Scratch database prefix '${SCRATCH_DB_PREFIX}' contains unsupported characters." >&2
    exit 1
fi

if [ ! -d "$BACKUPS_DIR" ]; then
    echo "Backups directory '${BACKUPS_DIR}' does not exist." >&2
    exit 1
fi

LATEST_BACKUP_NAME="$(
    find "$BACKUPS_DIR" -maxdepth 1 -mindepth 1 -type d -name "${DB_NAME}_*" -printf '%f\n' \
        | LC_ALL=C sort \
        | tail -n 1
)"

if [ -z "$LATEST_BACKUP_NAME" ]; then
    echo "No backup directories matching '${DB_NAME}_*' found under ${BACKUPS_DIR}." >&2
    exit 1
fi

SCRATCH_DB="${SCRATCH_DB_PREFIX}_$(date +%Y%m%d_%H%M%S)"

echo "[$(date)] Verifying latest backup '${LATEST_BACKUP_NAME}' using scratch database '${SCRATCH_DB}'..."
exec "${SCRIPT_DIR}/verify_backup.sh" "${BACKUPS_DIR}/${LATEST_BACKUP_NAME}" "$SCRATCH_DB"
