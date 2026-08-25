# Known Limitations

This is a deliberate, honest list — every item here is a documented,
conscious scoping decision made during development, not a bug found
later. Review this with the client's payroll/compliance team **before
go-live** so each item is a knowing acceptance, not a surprise.

None of these affect the correctness of what *is* implemented — every
statutory calculation this suite performs is covered by automated
tests against hand-verified figures. These are things the suite
**doesn't yet do**.

---

## Payroll / statutory

### ESI contribution-period continuity
~~ESI eligibility was re-tested each month.~~ **Fixed**: once an employee
is covered at the start of a contribution period (April or October),
they remain covered for the entire period even if a mid-period raise
pushes their gross above the threshold. The threshold is only re-tested
when a new period starts. The anchor is the first *confirmed* payslip
of the period; if that payslip is still in draft, the month falls back
to the plain threshold test.

### ESI is levied on overtime wages *(previously not)*
~~Overtime pay was excluded from the ESI contribution base.~~ **Fixed**:
the ESI salary rules now use `GROSS + OT` as the contribution base.
The *eligibility* test (whether the employee is covered at all) still
uses GROSS only — OT is excluded from the threshold test per the Act.

### Statutory rate/slab data needs annual verification
PF/ESI rates, Professional Tax slabs, Labour Welfare Fund rates, TDS
slabs, and the gratuity cap are all seeded at the rates known at
build time. All of these are revised periodically by government
notification. **This software does not self-update them** — someone
needs to check and update the seeded config at least once a year
(TDS slabs, every financial year without exception).

### Professional Tax / Labour Welfare Fund coverage is partial
Now seeded for Kerala, Tamil Nadu, Karnataka, Andhra Pradesh,
Telangana, Maharashtra, and West Bengal. A client operating in other
states needs new configuration records added (the calculation engine
supports any state; only the seed data is limited).
See `docs/SETUP_GUIDE.md` §5.2.

**Caveats for newly added states:**
- **West Bengal PT**: women earning up to ₹25,000/month are exempt;
  this module does not distinguish by gender — set the PT State field
  blank for such employees.
- **Maharashtra PT**: women earning up to ₹10,000/month are exempt —
  same manual exclusion applies.
- **Maharashtra LWF**: some older sources cite a monthly ₹6+₹12 rate;
  the current (2025) rate is ₹25+₹75 per half-year — verify before
  go-live.
- **Telangana PT/LWF**: identical to AP at the time of seeding (rates
  retained after the 2014 bifurcation) — verify current gazettes as
  both states may diverge independently.

### Overtime pay for Daily Wage contracts *(previously not computed)*
~~Daily Wage OT computed to zero silently.~~ **Fixed**: OT for Daily
Wage contracts now uses `daily_wage_rate / 8` as the hourly ordinary
rate (Factories Act basis), multiplied by the company's OT multiplier.

### Contract Labour is flagged, not fully modelled
`bpro_employment_type`'s "Contract Labour" category defaults PF/ESI
off (the labour contractor's own establishment is normally the
responsible party, not the principal employer) but otherwise treats
it like any other contract in this system. In most real setups,
contract labour is paid through the contractor's own invoice, not run
through this payroll at all — if that's the client's actual practice,
these workers likely shouldn't be `hr.contract` records here in the
first place, just tracked elsewhere (site access/safety registers) if
tracked at all.

---

## Recruitment

### WhatsApp notifications are wired up but not yet live
The WhatsApp notification skeleton is in place — offer delivery and
interview scheduling now call `company._bpro_whatsapp_send()` after
the email is sent. To activate it: set **WhatsApp Provider** on the
company (Settings → Companies → WhatsApp Notifications tab), fill in
the API token and sender phone, then the next offer send or interview
notification will go through WhatsApp alongside email. Three providers
are stubbed: Meta Cloud API, Twilio, Gupshup. A developer needs to
implement the actual HTTP call in the relevant branch of
`bpro_recruitment/models/res_company.py:_bpro_whatsapp_send()` once
the client supplies API credentials — the integration point is clearly
marked with a comment in each branch.

---

## Attendance

### No live biometric device connector
Attendance import is CSV/Excel-based (device-agnostic — works with
any device whose bundled software can export a daily log). There is
no live pull integration for any specific device brand. Building one
requires knowing the actual device model and whether it shares a
network with this Odoo instance — see `docs/SETUP_GUIDE.md` §5.4.

---

## Infrastructure (see `docs/SETUP_GUIDE.md` for the fixes)

- No automated backups until `scripts/backup_db.sh` is scheduled via
  cron on the actual deployment server.
- No TLS/HTTPS until `docker-compose.prod.yml` + `deploy/Caddyfile`
  are deployed with the client's real domain.
- No outbound email until an SMTP relay is configured.

---

## What this list is *not*

This is a technical scope document, not a legal or compliance opinion.
It does not constitute tax, legal, or statutory-compliance advice —
the client's own CA/compliance team should review payroll output
(especially PT/LWF/TDS figures and the ESI items above) before relying
on it for real statutory filings.
