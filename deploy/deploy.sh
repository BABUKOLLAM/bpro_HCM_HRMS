#!/usr/bin/env bash
# Single, repeatable production deploy for bpro-hrms-hcm.
#
# Exists because of a real incident: this repo's VPS checkout sat frozen
# at its original `git clone` for weeks with nobody noticing, because
# every "deploy" was a hand-typed sequence of shell commands and `git
# pull` was silently never actually run. This script replaces that whole
# sequence with one command that's either fully correct or loudly fails -
# no partial, unverified state left behind.
#
# Usage (run from anywhere, on the VPS, as the user that owns the repo):
#   /root/bpro-hrms-hcm/deploy/deploy.sh
#
# One-time setup before the first run: copy .env.example to .env and fill
# in the real values for this specific deployment. This is the ONLY place
# secrets and instance-specific names live now. config/odoo.prod.conf
# keeps harmless CHANGE-ME placeholders in git - this script overwrites
# them from .env on every run, so a `git reset --hard` can never again
# silently revert a live instance to public placeholder values.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# --- Phase 1: get the exact latest code, then re-exec a fresh copy of ------
# this very script. This script lives INSIDE the repo it resets, so
# `git reset --hard` can overwrite deploy.sh's own source file while
# bash is still mid-way through interpreting it - bash does not
# guarantee correct behavior when a running script's underlying file
# changes underneath it (confirmed the hard way: a fixed guard message
# further down kept printing its OLD text even after the reset had
# genuinely landed the new commit on disk). Re-exec'ing after the reset
# guarantees everything from here on runs from a freshly-read file.
if [ "${DEPLOY_SH_REEXECED:-0}" != "1" ]; then
    echo "[deploy $(date '+%Y-%m-%d %H:%M:%S')] Starting deploy in $REPO_DIR"
    echo "[deploy $(date '+%Y-%m-%d %H:%M:%S')] Fetching latest code..."
    git fetch origin
    BEFORE_SHA="$(git rev-parse HEAD)"
    git reset --hard origin/main
    AFTER_SHA="$(git rev-parse HEAD)"
    echo "[deploy $(date '+%Y-%m-%d %H:%M:%S')] HEAD: $BEFORE_SHA -> $AFTER_SHA"

    if [ ! -d "$REPO_DIR/addons/bpro_employment_type" ]; then
        echo "[deploy] FATAL: addons/bpro_employment_type missing after reset - the checkout is still wrong. Aborting." >&2
        exit 1
    fi

    export DEPLOY_SH_REEXECED=1
    export DEPLOY_SH_AFTER_SHA="$AFTER_SHA"
    exec "$REPO_DIR/deploy/deploy.sh" "$@"
fi

# --- Everything below only ever runs from the freshly re-exec'd copy ------

# Every module this suite ships, minus bpro_demo_data (evaluation-only,
# must never run in production - see its own manifest for why).
MODULES="bpro_approval,bpro_attendance,bpro_base,bpro_employment_type,bpro_ess,bpro_exit,bpro_hcm_dashboard,bpro_hr,bpro_hr_letters,bpro_hrms_portal,bpro_leave,bpro_lms,bpro_overtime,bpro_payroll,bpro_pms,bpro_probation,bpro_recruitment,bpro_shifts,bpro_statutory_filing,bpro_theme_switcher"

log() { echo "[deploy $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# --- 2. Re-apply the real secret (never stored in git) ---------------------
if [ ! -f "$REPO_DIR/.env" ]; then
    cat >&2 <<'EOF'
[deploy] FATAL: .env not found at the repo root.
Create it once from .env.example, fill in the real values, then:
  chmod 600 .env
and then re-run this script.
EOF
    exit 1
fi

# shellcheck disable=SC1091
source "$REPO_DIR/.env"
if [ -z "${ODOO_ADMIN_PASSWD:-}" ]; then
    echo "[deploy] FATAL: ODOO_ADMIN_PASSWD is empty in .env. Aborting." >&2
    exit 1
fi

if [ -z "${ODOO_DB_NAME:-}" ]; then
    echo "[deploy] FATAL: ODOO_DB_NAME is empty in .env. Aborting." >&2
    exit 1
fi

ODOO_DBFILTER="${ODOO_DBFILTER:-^${ODOO_DB_NAME}$}"

case "${DEPLOY_MODE:-}" in
    standalone)
        if [ -z "${APP_DOMAIN:-}" ]; then
            echo "[deploy] FATAL: APP_DOMAIN is required when DEPLOY_MODE=standalone." >&2
            exit 1
        fi
        COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
        ;;
    shared-caddy)
        if [ -z "${SHARED_CADDY_NETWORK:-}" ]; then
            echo "[deploy] FATAL: SHARED_CADDY_NETWORK is required when DEPLOY_MODE=shared-caddy." >&2
            exit 1
        fi
        if [ -z "${ODOO_SHARED_ALIAS:-}" ]; then
            echo "[deploy] FATAL: ODOO_SHARED_ALIAS is required when DEPLOY_MODE=shared-caddy." >&2
            exit 1
        fi
        COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.shared-caddy.yml"
        ;;
    *)
        echo "[deploy] FATAL: DEPLOY_MODE must be either 'standalone' or 'shared-caddy' in .env." >&2
        exit 1
        ;;
esac

log "Re-applying instance settings from .env into config/odoo.prod.conf..."
ODOO_ADMIN_PASSWD="$ODOO_ADMIN_PASSWD" ODOO_DB_NAME="$ODOO_DB_NAME" ODOO_DBFILTER="$ODOO_DBFILTER" python3 <<'PY'
from pathlib import Path
import os

path = Path("config/odoo.prod.conf")
with path.open("r", newline="") as handle:
    content = handle.read()
replacements = {
    "admin_passwd = ": os.environ["ODOO_ADMIN_PASSWD"],
    "db_name = ": os.environ["ODOO_DB_NAME"],
    "dbfilter = ": os.environ["ODOO_DBFILTER"],
}
lines = []
for line in content.splitlines(keepends=True):
    stripped = line.lstrip()
    for prefix, value in replacements.items():
        if stripped.startswith((";", "#")):
            break
        if line.startswith(prefix):
            newline = ""
            if line.endswith("\r\n"):
                newline = "\r\n"
            elif line.endswith("\n"):
                newline = "\n"
            line = f"{prefix}{value}{newline}"
            break
    lines.append(line)
with path.open("w", newline="") as handle:
    handle.write("".join(lines))
PY

if grep -q "^admin_passwd = CHANGE-ME" config/odoo.prod.conf; then
    # Anchored to the admin_passwd line specifically - the file also
    # has an intentionally-still-placeholder, commented-out
    # smtp_password (optional, configured via the UI instead), which
    # a broader "CHANGE-ME anywhere" check would wrongly trip on.
    echo "[deploy] FATAL: admin_passwd in config/odoo.prod.conf still contains a CHANGE-ME placeholder after the secret substitution. Aborting rather than going live insecure." >&2
    exit 1
fi

if grep -q "^db_name = CHANGE-ME-prod-db$" config/odoo.prod.conf || grep -q "^dbfilter = \^CHANGE-ME-prod-db\$$" config/odoo.prod.conf; then
    echo "[deploy] FATAL: db_name/dbfilter in config/odoo.prod.conf still contain placeholders after substitution. Aborting." >&2
    exit 1
fi

# --- 3. Bring up Postgres only, not odoo yet ------------------------------
# Deliberately NOT starting the persistent odoo process here too. On a
# brand-new database, the persistent process's own boot sequence races
# the explicit install command below to CREATE DATABASE $ODOO_DB_NAME -
# confirmed directly: the exact same install command fails with
# "duplicate key value violates ... pg_database_datname_index" when the
# persistent container is already up, and succeeds cleanly when it
# isn't. Initialize the database first, only then start the process
# that serves it.
log "Starting db..."
$COMPOSE up -d db

log "Waiting for Postgres to be healthy..."
for i in $(seq 1 30); do
    health=$($COMPOSE ps db --format '{{.Health}}' 2>/dev/null || true)
    [ "$health" = "healthy" ] && break
    sleep 2
done

# --- 4. Install anything new, upgrade everything else -----------------------
log "Installing/upgrading all modules into database '$ODOO_DB_NAME': $MODULES"
$COMPOSE run --rm --no-deps odoo \
    odoo -c /etc/odoo/odoo.prod.conf -d "$ODOO_DB_NAME" \
    -i "$MODULES" -u "$MODULES" \
    --without-demo=all --stop-after-init

log "Starting/restarting the live odoo process..."
# A single atomic recreate, not `up -d` followed by `restart` - doing
# both back-to-back interrupted odoo mid-boot (confirmed the hard way:
# the container stayed "Up" but its logs never got past font-cache
# warnings, no "modules loaded" or "HTTP service running" line ever
# appeared, and /web/login hung rather than just refusing - restart
# was firing while the first start was still mid-initialization).
# --remove-orphans - Compose sometimes decides a currently-running
# container doesn't match "its" current service config (its internal
# config-hash bookkeeping) and refuses to recreate in place, instead
# erroring "container name already in use" - confirmed live: it blocked
# a deploy outright and needed a manual --remove-orphans run to recover.
# This flag makes that class of failure impossible instead of hoping it
# doesn't recur.
$COMPOSE up -d --force-recreate --remove-orphans odoo

# --- 5. Verify it's actually serving before declaring success ---------------
# Poll rather than a single fixed sleep - a fresh restart right after
# installing every module can reasonably take longer than a few seconds
# to bind its HTTP port. Checked via `docker exec ... curl localhost`
# from inside the container, not by curling its bridge-network IP from
# the host - the latter depends on host-to-bridge routing being
# permitted, which isn't universal across Docker setups (confirmed the
# hard way: works fine from another container on the same network, but
# is unreachable from the host on Docker Desktop for Mac, where
# containers run inside a VM). Checking from inside sidesteps that
# entirely and works identically everywhere.
ODOO_CONTAINER=$($COMPOSE ps -q odoo)

STATUS="000"
for i in $(seq 1 30); do
    STATUS=$(docker exec "$ODOO_CONTAINER" curl -s -m 5 -o /dev/null -w '%{http_code}' http://localhost:8069/web/login 2>/dev/null || echo "000")
    [ "$STATUS" = "200" ] && break
    sleep 2
done

if [ "$STATUS" != "200" ]; then
    echo "[deploy] FAILED: /web/login returned HTTP $STATUS after waiting up to 60s. Check: docker compose logs odoo" >&2
    exit 1
fi

log "SUCCESS - deployed ${DEPLOY_SH_AFTER_SHA:-unknown}, /web/login returned 200."
