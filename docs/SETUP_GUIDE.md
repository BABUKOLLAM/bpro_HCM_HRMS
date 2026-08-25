# bpro HCM | HRMS — Setup & Onboarding Guide

Audience: whoever is deploying this suite for a new organisation (the
bpro team, an implementation partner, or a technically confident admin
on the client's own side). If you're an end user looking for how to
*use* the system day to day, see [`USER_MANUAL.md`](USER_MANUAL.md)
instead.

Three companion documents worth reading alongside this one:
[`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) (what's deliberately
not built yet — review with the client before go-live),
[`UAT_CHECKLIST.md`](UAT_CHECKLIST.md) (the acceptance-testing script
to run before the first real payroll), and
[`DATA_PRIVACY.md`](DATA_PRIVACY.md) (what personal data this stores
and what compliance review it needs).

---

## 1. What you're deploying

This is an Odoo 18 Community installation with 18 custom modules
(`addons/bpro_*`) plus three vendored OCA modules (`addons/payroll*`)
that supply the payroll engine native Odoo Community doesn't include.
Each client gets **their own separate database** — this is a
single-tenant deployment model, not a shared multi-tenant SaaS. There
is no cross-client data sharing to worry about; a fresh `docker compose
up` gives you a clean slate every time.

---

## 2. Prerequisites

- A server (or laptop, for evaluation) with **Docker** and **Docker
  Compose** installed.
- For production: a domain name and a reverse proxy that terminates
  TLS (Caddy, Nginx, or similar) in front of Odoo's port 8069. This
  repo does not ship a reverse-proxy config — add one before exposing
  the instance to the internet.
- Roughly **4 GB RAM minimum** for a small deployment (under ~50
  employees); scale up for larger headcounts or if you enable more
  worker processes.

---

## 3. First boot

```bash
git clone https://github.com/BABUKOLLAM/bpro-hrms-hcm.git
cd bpro-hrms-hcm
docker compose up -d
```

Wait for Postgres to report healthy (`docker compose ps`), then
install the full module set into a named database:

```bash
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d <client_db_name> \
  -i bpro_hrms_portal,bpro_hcm_dashboard,bpro_leave,bpro_exit,bpro_ess,bpro_probation,\
bpro_hr_letters,bpro_overtime,bpro_shifts,bpro_statutory_filing,bpro_lms,bpro_pms,\
bpro_employment_type \
  --without-demo=all --stop-after-init
docker compose restart odoo
```

That single `-i` list pulls in every other module transitively
(`bpro_payroll`, `bpro_recruitment`, `bpro_attendance`, `bpro_hr`,
`bpro_base`, the vendored payroll engine, and native Odoo HR modules)
through their own dependency chains — you don't need to list those
separately. `bpro_employment_type` is listed explicitly because nothing
else in this set depends on it, so it wouldn't be pulled in on its own.

Do **not** add `bpro_demo_data` to a production install command — see
the [README](../README.md#whats-in-the-suite) for what it does and why
it's evaluation-only.

Replace `<client_db_name>` with something identifiable, e.g.
`acme_manufacturing_prod`. Visit `http://localhost:8069`, select that
database, and log in with the master password you set in step 4 to
create your first real user.

---

## 4. Before this touches real data — security hardening

The repo ships with **development defaults that must be changed**
before any real company data goes in:

| File | Setting | Change to |
|---|---|---|
| `config/odoo.conf` | `admin_passwd` | A strong, unique password — this is the database-manager master password, separate from any user login |
| `docker-compose.yml` | `POSTGRES_PASSWORD`, `PASSWORD` | A strong, unique Postgres password (keep both values identical to each other) |

Also set `list_db = False` in `config/odoo.conf` once the client
database exists, so the database-selection screen doesn't advertise
every database on the server to anyone who visits the login page.

---

## 4.5 Production deployment — TLS and a production-sized config

The default `docker-compose.yml` is a development setup: it exposes
Odoo's port 8069 directly and runs unencrypted HTTP. **Do not put this
on the internet as-is.** For a real deployment:

1. Point the client's domain's DNS A record at the server.
2. Copy `.env.example` to `.env`, then fill in the real values for this
   specific deployment:
   - `COMPOSE_PROJECT_NAME` = a unique project name for this app on this
     VPS (keeps its containers, networks, and volumes independent of
     other programs)
   - `DEPLOY_MODE` = `standalone` or `shared-caddy`
   - `ODOO_ADMIN_PASSWD` = strong database-manager password
   - `ODOO_DB_NAME` = this instance's production database name
   - `APP_DOMAIN` for standalone mode, or `SHARED_CADDY_NETWORK` +
     `ODOO_SHARED_ALIAS` for shared-Caddy mode
3. Use `config/odoo.prod.conf` instead of the dev config — it has
   production-sized worker/memory settings, a hidden database-manager
   screen, and commented-out SMTP settings (see the next section). Leave
   its tracked placeholders alone; `deploy/deploy.sh` rewrites them from
   `.env` on each deploy.
4. Bring the stack up with both compose files together, which layers
   in a Caddy reverse proxy (automatic HTTPS via Let's Encrypt) and
   stops publishing Odoo's ports directly — only Caddy is
   internet-facing:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

Caddy needs ports 80 and 443 reachable from the internet (80 is used
for the one-time ACME certificate challenge, then everything redirects
to 443). No manual certificate renewal is needed — Caddy handles it.

### Redeploying after the first install: use `deploy/deploy.sh`

Every step below this point (co-hosting, first install) is done once.
After that, use `deploy/deploy.sh` for every subsequent deploy instead
of repeating these commands by hand. It exists because of a real
incident: a hand-typed deploy sequence left this exact repo's VPS
checkout frozen at its original clone for weeks, with `git pull`
silently never actually taking effect and nobody noticing — several
shipped fixes simply never reached the live site. The script instead:
resets to the exact latest commit (verifiable, not a hope), re-injects
the real `admin_passwd` from a gitignored `.env` file so a reset can
never again revert it to the public placeholder, installs/upgrades
every module, restarts, and refuses to report success unless
`/web/health` actually returns `200` afterward.

One-time setup, on the server, before the first run:

```bash
cp /root/bpro-hrms-hcm/.env.example /root/bpro-hrms-hcm/.env
chmod 600 /root/bpro-hrms-hcm/.env
```

Then edit `/root/bpro-hrms-hcm/.env` with the real values for this
instance. The important production-safety fields are:

- `COMPOSE_PROJECT_NAME`: unique per program on the VPS
- `DEPLOY_MODE`: `standalone` or `shared-caddy`
- `ODOO_DB_NAME`: unique per production instance
- `APP_DOMAIN` or `ODOO_SHARED_ALIAS`: unique per published site

Every deploy after that is just:

```bash
/root/bpro-hrms-hcm/deploy/deploy.sh
```

The script now also validates the merged Compose config before touching
the live stack, warns if `.env` is more permissive than `chmod 600`, and
appends a timestamped line to `logs/deploy/history.log` after every
successful deploy so you have a local audit trail of what SHA/database
went live when.

If it's co-hosted with another Caddy instance (see below), set
`DEPLOY_MODE=shared-caddy` in `.env`; the script then skips this stack's
own `caddy` service, matching the manual sequence documented next.

### Co-hosting on a server that already runs a Caddy instance

Only one process can bind ports 80/443 on a given server, so if this
stack is going on a box that already fronts another site with its own
Caddy (bpro's own production VPS does exactly this, alongside a
client's ME Polymers ERP), **do not start this stack's own `caddy`
service** — instead:

1. Bring up only `db` and `odoo`, joined to the other project's
   existing Docker network under a distinct alias, using the
   `docker-compose.shared-caddy.yml` overlay in this repo. Set
   `SHARED_CADDY_NETWORK` and `ODOO_SHARED_ALIAS` in `.env` first:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     -f docker-compose.shared-caddy.yml up -d db odoo
   ```

2. Run the one-time database install with `run --rm --no-deps`, **not**
   `exec` — `exec` runs inside the already-listening container and
   fails with `OSError: Address already in use`; `run` starts a
   separate, temporary container instead:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     -f docker-compose.shared-caddy.yml run --rm --no-deps odoo \
     odoo -c /etc/odoo/odoo.prod.conf -d <your_prod_db_name> -i <modules> \
     --without-demo=all --stop-after-init
   ```

3. Add a new site block to the *other* project's Caddyfile pointing at
   this stack's alias (e.g. `reverse_proxy <ODOO_SHARED_ALIAS>:8069`),
   separate from its existing site block — never add this domain to an
   existing block for a different site, or both domains will serve the
   same backend. Validate before reloading, and reload (not restart) to
   avoid dropping the other site's live connections:

   ```bash
   docker exec <other-caddy-container> caddy validate --config /etc/caddy/Caddyfile
   docker exec <other-caddy-container> caddy reload --config /etc/caddy/Caddyfile
   ```

### Outbound email (SMTP)

Payslip emails, offer letters, and reminder notifications all send
real mail. Configure a relay either of two ways (both work; UI config
wins if both are set):

- **In `config/odoo.prod.conf`**: uncomment and fill in the
  `smtp_server` / `smtp_port` / `smtp_user` / `smtp_password` /
  `smtp_ssl` lines with the client's actual mail provider details.
- **In the running app**: Settings → Technical → Email → Outgoing Mail
  Servers.

Send a test email (e.g. trigger an offer-letter send) after
configuring, before relying on it for anything real.

---

## 4.6 Backups

**No backup runs automatically — you must schedule one.**
`scripts/backup_db.sh` dumps both the Postgres database and the Odoo
filestore (attachments, generated PDFs — a database-only backup is
incomplete) to a timestamped directory under `backups/`. Each backup now
also includes:

- `SHA256SUMS` for integrity verification during restore
- `metadata.env` with the source database name, creation time, git SHA,
  retention, and whether a filestore archive was present

```bash
# One-off backup:
./scripts/backup_db.sh <db_name>

# Scheduled via cron - e.g. daily at 02:00:
0 2 * * * cd /path/to/bpro-hrms-hcm && BACKUP_RETENTION_DAYS=30 ./scripts/backup_db.sh <db_name> >> /var/log/bpro-backup.log 2>&1
```

Copy the `backups/` directory (or wherever you point it) to storage
that isn't the same disk as the live server — a backup that lives next
to what it's backing up doesn't survive a disk failure.

**Test the restore path before you need it for real:**

```bash
./scripts/restore_db.sh backups/<db_name>_<timestamp> <scratch_db_name>
```

`restore_db.sh` now verifies `SHA256SUMS` automatically when present and
terminates existing sessions before dropping the target database, which
makes scratch-restore rehearsals more reliable.

**Rehearse the full restore + Odoo boot path regularly:**

```bash
./scripts/verify_backup.sh backups/<db_name>_<timestamp> <scratch_db_name>
```

That command restores the backup into a scratch database, boots Odoo
once against it, runs a simple SQL smoke check, and deletes the scratch
database again unless you pass `--keep-restored-db`.

A backup nobody has ever restored is a hope, not a backup.

---

## 4.7 Login brute-force protection

Odoo Community's own login throttling is minimal. Caddy's stock image
has no built-in rate limiter (the plugin that adds one needs a custom
build — not worth the extra image-maintenance burden here), so this
uses the standard, well-understood tool instead: **fail2ban on the
host**, watching Odoo's own login-failure log and banning repeat
offenders at the firewall.

1. Install fail2ban on the host (`apt install fail2ban` on
   Debian/Ubuntu, or your distro's equivalent).
2. Copy the filter: `deploy/fail2ban/odoo-auth.conf` →
   `/etc/fail2ban/filter.d/odoo-auth.conf`.
3. Copy the jail: `deploy/fail2ban/jail.local` →
   `/etc/fail2ban/jail.d/odoo-auth.local`, and fix the `logpath` to
   point at this repo's actual location on the host (it reads
   `logs/odoo/odoo.log`, the bind-mounted log path from
   `docker-compose.prod.yml`).
4. `systemctl restart fail2ban`, then `fail2ban-client status
   odoo-auth` to confirm the jail is active.
5. Install the sample logrotate policy from `deploy/logrotate.odoo`
   into `/etc/logrotate.d/` (after fixing the path) so Odoo's bind-mounted
   log file does not grow forever and eventually fill the disk.

Default policy: 5 failed logins in 10 minutes bans the IP for 1 hour —
adjust `maxretry`/`findtime`/`bantime` in the jail file to the client's
actual tolerance.

---

## 4.8 Uptime monitoring

Nothing in this stack tells you if the site goes down — that needs an
**external** check (external deliberately: something checking from
outside the server can tell the difference between "the server is
down" and "the server can't reach itself," which a monitor running on
the same box cannot). Not a coding task — pick one:

- **[healthchecks.io](https://healthchecks.io)** or
  **[UptimeRobot](https://uptimerobot.com)** (both have workable free
  tiers) — point either at `https://<the client's domain>/web/health`
  on a 5-minute interval, and set it to alert (email/SMS/Slack) on
  failure or on an unexpected HTTP status.
- This repo's production stack already uses `/web/health` for the Odoo
  container healthcheck and `deploy/deploy.sh` uses the same endpoint
  for its post-deploy smoke test, so external monitors should follow the
  same convention.
- If the client already runs infrastructure monitoring (Datadog, a
  Grafana/Prometheus stack, etc.), add this instance as one more
  target there instead of a separate standalone tool.

---

## 5. Company setup checklist

Work through this in order. Every item below is a *company policy or
statutory* value — none of it is guessed by the software; each field
has a sensible default and an explanatory tooltip, but a real
deployment must confirm each one against the client's actual
situation.

### 5.1 Company record & branding
- **Settings → General Settings → Companies**: legal name, registered
  address, PAN, TAN (for TDS/Form 16), logo.
- If replacing bpro's own branding in the landing/login pages
  (`bpro_hrms_portal`), see §8 below.

### 5.2 Statutory payroll configuration (`bpro_payroll`)

Also decide each employee's **Employment Category** on their contract
(`bpro_employment_type`) before running their first payslip — it's not
just a label: Trainee/Apprentice and Contract Labour change the PF/ESI
defaults, Fixed Term Contract requires a Contract End Date, and Daily
Wage switches Basic to a rate-per-attendance-day computation entirely
instead of the CTC/12 figure everything else uses. See
`docs/USER_MANUAL.md` §7 for the per-category detail.

Under **Settings → Companies → [company] → Payroll** tabs:

- **PF**: wage ceiling, employee/employer/EPS/EDLI/admin rates. Seeded
  at the standard EPFO figures — confirm current rates before go-live,
  they're revised by notification from time to time.
- **ESI**: wage threshold, employee/employer rates. Same caveat.
- **Professional Tax** (`bpro.pt.config`, one record per state): this
  suite ships **pre-seeded slabs for Kerala, Tamil Nadu, Karnataka,
  and Andhra Pradesh only**, because that's what the first deployment
  needed. **A client operating in any other state needs a new
  `bpro.pt.config` record added** (Payroll menu → PT Configuration) —
  the engine handles any state, the seed data just doesn't cover every
  state yet. Verify the seeded four against the current-year slabs too.
- **Labour Welfare Fund** (`bpro.lwf.config`): seeded for Karnataka,
  Tamil Nadu, Andhra Pradesh. Kerala LWF depends on establishment
  type/board rather than a flat rate — add it once that's confirmed
  for the specific client. Other states: add as needed, same as PT.
- **TDS**: regime slabs (new & old) seeded for the current financial
  year — **re-seed at the start of each financial year** when the
  Union Budget revises slabs. Each employee separately declares New or
  Old regime on their contract.
- **Gratuity cap** (`bpro_exit`, company settings): seeded at the
  current statutory ceiling (₹20,00,000) — this moves by government
  notification, check it's still current.

### 5.3 Leave & attendance policy
- **Probation period** (`bpro_probation`, company settings): default 6
  months — company policy, adjust freely.
- **Exit notice period** (`bpro_exit`, company settings): default 30
  days — company policy, adjust freely.
- **Overtime compensation** (`bpro_overtime`, company settings): choose
  *Pay* (at a configurable multiplier, seeded 2.0× per the Factories
  Act) or *Compensatory Off*.
- **Leave types** (`bpro_leave`): Earned Leave is seeded as a
  worked-time accrual approximating the Factories Act's "1 day per 20
  worked" rule. Casual and Sick Leave have **no statutory minimum for
  factories** — the seeded day counts are a starting point, not a
  legal requirement; set them to the client's actual policy.
- **State public holidays**: not seeded at all — each state's National
  & Festival Holidays Act sets a different count (Kerala 13, Tamil
  Nadu 9, Karnataka 10, Andhra Pradesh 8, as examples). Load the
  client's actual holiday list into each work location's working
  calendar (**Employees → Configuration → Working Schedules**) before
  go-live, or attendance-exception detection will flag real holidays
  as absences.
- **Shifts** (`bpro_shifts`): two example calendars are seeded (Shift A
  06:00–14:00, Shift B 14:00–22:00, Mon–Sat). A **night shift crossing
  midnight needs its own calendar built deliberately** — Odoo working
  calendars are per-day, so a 22:00–06:00 shift is two attendance
  lines, not seeded blind here.

### 5.4 Attendance capture
`bpro_attendance` ships a **device-agnostic CSV/XLSX import** — it
does not include a live connector to any specific biometric device
brand. If the client has a punch device, confirm:
1. The device brand/model and whether its bundled software can export
   a daily CSV/Excel log (columns: badge ID, date, check-in, check-out)
   — if so, the seeded import wizard works as-is.
2. Whether the device is on the same network as this Odoo instance. If
   Odoo is cloud-hosted and the device is only reachable from the
   client's own site network, a live pull integration needs a local
   middleware agent — that's custom work per device, not included.

Each employee needs a **Badge ID** set (Employees → [employee] →
HR Settings) matching whatever identifier the device export uses.

### 5.5 Employee master data
Before running the first payroll:
- Set **PAN** on every employee (required for TDS/Form 16).
- Set **UAN** and **ESI Number** on every employee who's covered
  (`bpro_statutory_filing` — needed for the ECR/ESIC exports;
  employees missing these are excluded from those files and reported,
  not silently dropped, but it's better to fill them in first).
- Set a **bank account** on every employee (needed for the bank salary
  advice export).
- Confirm each employee's **contract**: CTC, Basic %, HRA %, PF/ESI
  applicability, PT state, LWF state, TDS regime.

---

## 6. Go-live checklist (summary)

- [ ] `admin_passwd` and Postgres credentials changed from defaults
- [ ] `list_db = False` set once the real database exists
- [ ] Reverse proxy + TLS in front of Odoo (§4.5 — `docker-compose.prod.yml` + `deploy/Caddyfile`, production only)
- [ ] Outbound email (SMTP) configured and test-sent
- [ ] Automated backups scheduled via cron (§4.6 — `scripts/backup_db.sh`) and a restore rehearsed at least once
- [ ] fail2ban installed and the `odoo-auth` jail active (§4.7)
- [ ] External uptime monitoring pointed at the live domain (§4.8)
- [ ] Company legal details, PAN, TAN, logo set
- [ ] PF/ESI rates confirmed current
- [ ] PT/LWF config exists for every state the client operates in
- [ ] TDS slabs confirmed for the current financial year
- [ ] Gratuity cap confirmed current
- [ ] Probation months, notice period, OT policy set to client's actual policy
- [ ] Casual/Sick leave day-counts set to client's actual policy
- [ ] State public holiday calendars loaded per work location
- [ ] Shift calendars built for every shift the client actually runs (including night shifts, if any)
- [ ] Attendance capture method confirmed (CSV import is the default; live device integration is separate custom work if needed)
- [ ] Every employee has PAN, UAN, ESI number (if covered), bank account, Badge ID
- [ ] [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) reviewed and knowingly accepted by the client's payroll/compliance team
- [ ] [`DATA_PRIVACY.md`](DATA_PRIVACY.md) reviewed by the client's compliance/legal function
- [ ] [`UAT_CHECKLIST.md`](UAT_CHECKLIST.md) fully run and signed off on a staging copy
- [ ] First real payroll run in parallel with the client's existing system for at least one cycle before full cutover

---

## 7. Verifying the install

Run the full automated test suite against a throwaway database — this
exercises every statutory calculation (PF/ESI/PT/LWF/TDS math, LOP
proration, gratuity, EL encashment) against hand-verified expected
values, so a clean run is real evidence the engine is computing
correctly on this deployment's Odoo/Postgres versions:

```bash
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d verify_test \
  --test-enable \
  --test-tags /bpro_approval,/bpro_attendance,/bpro_base,/bpro_employment_type,/bpro_ess,/bpro_exit,/bpro_hcm_dashboard,/bpro_hr,/bpro_hr_letters,/bpro_leave,/bpro_lms,/bpro_overtime,/bpro_payroll,/bpro_pms,/bpro_probation,/bpro_recruitment,/bpro_shifts,/bpro_statutory_filing \
  -i bpro_ess,bpro_hrms_portal,bpro_hcm_dashboard,bpro_statutory_filing,\
bpro_probation,bpro_hr_letters,bpro_overtime,bpro_shifts,bpro_employment_type \
  --stop-after-init --without-demo=all
```

The `--test-tags` list scopes the run to this repo's own tests only —
without it, `--test-enable` also runs every native Odoo module's test
suite it transitively installs (accounting, sales, etc.), which adds
upwards of ten minutes for zero extra signal on this deployment.

Look for `0 failed, 0 error(s)` in the output, then drop the throwaway
database.

---

## 8. White-labelling (optional)

`bpro_hrms_portal` carries bpro's own branding (name, logo mark,
credits) on the public landing and login pages. To rebrand for a
client or reseller:
- `addons/bpro_hrms_portal/views/landing_templates.xml` and
  `login_templates.xml` — text, links, module descriptions.
- `addons/bpro_hrms_portal/static/src/scss/hrms_portal.scss` — colours
  and the logo mark styling.
- Settings → General Settings → company logo (used inside the app and
  on the login card).

---

## 9. Support model

This repository does not itself define a support/licensing agreement.
Before handing a deployment to a client as a paid product, decide and
document separately: warranty scope, support-response expectations,
and how statutory-rate updates (PF/ESI/PT/TDS revisions) will be kept
current for that client over time — these change periodically by
government notification and are not something the software
self-updates.
