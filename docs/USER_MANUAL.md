# bpro HCM | HRMS — User Manual

This is the day-to-day usage guide, organised by who's doing the
work. If you're setting up a new deployment, see
[`SETUP_GUIDE.md`](SETUP_GUIDE.md) instead.

The suite has four access levels, and what you see in the menu
depends on which one you have:

| Level | Typically | Sees |
|---|---|---|
| **Employee** | Every staff member | Their own payslips, leave, attendance, assets — the Employee Self-Service (ESS) area |
| **HOD** (Head of Department) | Department managers | Everything an Employee sees, plus their own department's vacancy requests, joining reports, exit requests, asset register (read-only on most of these) |
| **Client HR** | The HR/payroll team | Full read/write on everything below — this manual is written mainly from this level's point of view, since HR runs most of these workflows |
| **Super Admin** | System owner | Everything, across all companies if multi-company |

---

## Contents

1. [Recruitment — filling a vacancy](#1-recruitment--filling-a-vacancy)
2. [Onboarding & Probation](#2-onboarding--probation)
3. [Attendance](#3-attendance)
4. [Leave](#4-leave)
5. [Shifts](#5-shifts)
6. [Overtime](#6-overtime)
7. [Payroll](#7-payroll)
8. [Statutory Filings](#8-statutory-filings)
9. [HR Letters](#9-hr-letters)
10. [Exit & Full-and-Final Settlement](#10-exit--full-and-final-settlement)
11. [Learning (LMS) & Performance (PMS)](#11-learning-lms--performance-pms)
12. [Employee Self-Service (ESS)](#12-employee-self-service-ess)
13. [The HCM Dashboard](#13-the-hcm-dashboard)

---

## 1. Recruitment — filling a vacancy

**Menu: Recruitment**

1. **A department raises a request.** A Head of Department opens
   *Recruitment → Vacancy Requests*, creates a new request (job title,
   headcount, employment type, justification, target date), and
   submits it. It defaults to their own department.
2. **HR approves it.** HR reviews the request. Approving it
   automatically creates the underlying Job Position — no separate
   "publish" step. Rejecting it asks for a reason; a rejected request
   can be reset to draft and resubmitted.
3. **Candidates apply.** The job position, once published, is live on
   the company's public careers page (native Odoo functionality) —
   candidates apply and upload their CV there.
4. **Interviews.** Each interviewer records their own evaluation
   against the applicant (interview type, date, marks, remarks, and a
   recommendation: *Recommended for Selection / On Hold / Rejected / No
   Comments*). Multiple interviewers can each leave independent
   feedback — nobody overwrites anyone else's.
5. **Send the offer.** From *Recruitment → Job Offers*, HR fills in
   designation, proposed CTC, and joining date, then clicks **Send
   Offer**. This emails the candidate a secure link.
6. **Candidate responds.** The candidate opens the link (no login
   needed — the link itself is the access token), reviews the offer,
   fills in their own details (address, PAN, Aadhar, bank account,
   emergency contact), and accepts or declines.
7. **Finalize Hiring.** Once accepted, HR (with the recruitment
   manager role) clicks **Finalize Hiring** on the offer. This is
   irreversible and, in one step:
   - Creates the employee record
   - Assigns a permanent, unique **Employee Code**
   - Generates the **Appointment Order** PDF
   - Starts the employee's **probation** period automatically
   - Creates a **Joining Report** tracker with an SLA deadline
   - Triggers **induction course** auto-enrollment (LMS)

---

## 2. Onboarding & Probation

**Menu: Recruitment → Joining Reports, and each employee's own record**

- The **Joining Report** created at Finalize Hiring tracks whether the
  new hire actually submitted their joining paperwork by the SLA
  deadline (configurable — 2 days / 1 week / 15 days / 1 month). HR
  marks it submitted once received.
- **Assets**: issue laptops, phones, or other equipment against the
  new employee from *Recruitment → Employee Assets* — this register is
  what the exit clearance process checks later.
- **Probation**: every new hire starts on probation automatically
  (company-configured length, default 6 months). Their employee record
  shows *On Probation* with an end date. When that date arrives, HR
  gets a reminder on the employee's chatter. HR then either:
  - **Confirm Employment** — ends probation, stamps a confirmation
    date, and a Confirmation Letter can be printed.
  - **Extend Probation** — pushes the end date out (default +3
    months), logged to the chatter.

---

## 3. Attendance

**Menu: Attendance**

- **Manual check-in/out**: employees or HR can record attendance
  directly (native Odoo — the *Attendances* app, kiosk mode, or a web
  check-in).
- **Bulk import from a punch device**: *Attendance → Import Attendance
  Log*. Upload a CSV or Excel file with columns `badge_id, date,
  check_in, check_out` (exported from whatever device management
  software the client uses). Each employee's **Badge ID** field
  (Employees → HR Settings) is what matches rows to people. The import
  reports anything it couldn't match (unknown badge, missing time)
  rather than silently skipping it.
- **Overtime approval**: attendance records with extra hours flow
  through native Odoo's overtime approval (managers approve/refuse) —
  only approved hours count toward pay or comp-off (§6).
- **Absence review**: *Attendance → Detect Exceptions* scans a date
  range and flags any working day with no attendance record and no
  approved leave. This also runs automatically every night for
  yesterday. Review the flagged list at *Attendance → Attendance
  Exceptions*:
  - **Excuse** — no pay impact (e.g. they forgot to punch but were
    actually present, or there was a system issue).
  - **Confirm Absent** — this day becomes an unpaid (Loss of Pay) day
    once it reaches payroll (§7).

---

## 4. Leave

**Menu: Time Off (native Odoo), plus the types this suite adds**

- Employees request leave the normal Odoo way — pick a leave type,
  dates, submit. Their manager (or HR, depending on the type)
  approves it.
- **Leave types available out of the box**: Earned Leave, Casual
  Leave, Sick Leave, Maternity Leave, Paternity Leave, Compensatory
  Off, and Loss of Pay.
- **Earned Leave** accrues automatically over time worked (no manual
  allocation needed) — it's a running balance, visible on the
  employee's Time Off summary.
- **Loss of Pay** is a distinct leave type specifically for unpaid
  absence — using it (or having a confirmed attendance exception, §3)
  is what actually reduces pay, not just being "over the leave
  balance" on a normal type.
- **Compensatory Off** is credited via the overtime conversion wizard
  (§6), not requested directly like other types.

---

## 5. Shifts

**Menu: Attendance → Shift Assignments**

If the organisation runs multiple shifts, assign each employee a
**Shift Assignment** — an employee, a shift calendar (e.g. *Shift A
06:00–14:00*), and a date range (open-ended or bounded). This is what
keeps attendance-exception detection checking the *right* hours for
that employee. Two shifts are pre-configured (Shift A, Shift B);
ask HR/IT to add more if the organisation runs a night shift or a
different pattern. Assignments can't overlap for the same employee —
end one before starting the next.

---

## 6. Overtime

**Menu: Attendance → Convert OT to Comp-Off (if the company uses
Compensatory Off) or nothing extra (if the company pays OT — it flows
into payroll automatically)**

The company's overtime policy (set once, in company settings) decides
which of these two applies:

- **Pay with Salary**: approved overtime hours are automatically
  priced into that month's payslip at the configured multiplier
  (typically double the ordinary hourly rate) — nothing manual needed
  beyond approving the hours in Attendance.
- **Compensatory Off**: HR periodically runs *Convert OT to Comp-Off*
  for a date range. It turns approved, not-yet-converted overtime
  hours into Compensatory Off leave days (8 hours = 1 day) that the
  employee can then take like any other leave. Safe to re-run — it
  never double-credits the same hours.

---

## 7. Payroll

**Menu: Payroll**

1. **Contracts**: each employee's contract carries their Annual CTC,
   Basic %, HRA %, PF/ESI applicability, PT state, LWF state, and TDS
   regime choice (New or Old — the employee's own election). Also set
   **Employment Category** — Permanent (default), Fixed Term Contract
   (requires a Contract End Date — that's the legal definition of one),
   Trainee/Apprentice (PF/ESI default off, per the Apprentices Act —
   override if this is an informal "trainee" rather than a registered
   apprenticeship), Daily Wage (set a **Daily Wage Rate** instead of a
   CTC — pay is computed from actual attendance days worked, not a
   monthly figure), or Contract Labour (PF/ESI default off — see
   `docs/KNOWN_LIMITATIONS.md`, these workers are usually better
   tracked outside payroll entirely, paid via the contractor's own
   invoice).
2. **Run payslips**: generate payslips for the period (individually or
   in a batch via a Payslip Run). Each payslip automatically computes,
   in order: Basic, HRA, flexible benefits, PF, ESI, Professional Tax,
   Labour Welfare Fund, TDS, and — if there was any confirmed absence
   or unpaid leave that period — a **Loss of Pay proration** that
   correctly reduces Basic, HRA, PF and ESI together (not just a flat
   deduction at the end).
3. **Confirm the payslip**. Draft payslips are editable working
   copies; confirming (*Done*) locks the figures — this is also the
   trigger that makes a payslip visible to the employee in ESS and
   eligible for the statutory filing exports.
4. **Payslip PDF & email**: once confirmed, click **Email Payslip** to
   send the employee a PDF copy directly.
5. **Declarations & Form 16** (for employees on the Old regime):
   employees submit investment declarations (Section 80C, 80D, HRA
   exemption proofs); HR reviews and approves them, which feeds into
   the TDS calculation for the rest of the year. At year-end, generate
   **Form 16 Part B** per employee from the TDS menu.

---

## 8. Statutory Filings

**Menu: Payroll → Statutory Filings**

Once a month's payslips are all confirmed, open this wizard, pick the
month, and click **Generate Filings**. It produces five downloadable
files in one go:

- **EPFO ECR** — the text file uploaded to the PF portal.
- **ESIC contribution** — the CSV for the ESI portal.
- **Professional Tax summary** — grouped per state, matching each
  state's own filing requirement.
- **Form 24Q data** — the quarter's TDS figures, formatted as input
  for the NSDL return-preparation utility (not the final `.fvu` file
  itself — that still goes through NSDL's own tool).
- **Bank salary advice** — the transfer sheet to hand your bank.

Anyone missing a required identifier (UAN, ESI number, PAN, or bank
account) is **left out of that specific file and listed in the
summary** — check that list and fill in the missing data rather than
assuming everyone was included.

---

## 9. HR Letters

**Menu: Employees → HR Letters**

Generate a **Salary Certificate**, **Address Proof**, **Experience /
Relieving Letter**, or **Increment Letter** for any employee. Pick the
employee and letter type — most fields (designation, CTC, service
dates) prefill from their contract automatically; for an Increment
Letter, enter the new CTC. Each letter gets a permanent reference
number (e.g. `LTR00042`) so it can be cited back later. A relieving
letter is also created automatically when an employee's exit is
closed (§10) — no need to create it separately in that case.

---

## 10. Exit & Full-and-Final Settlement

**Menu: Employees → Exit / Separation** (employees can also file their
own resignation from ESS, §12)

1. **Resignation filed** — either the employee themselves (ESS) or HR
   on their behalf. It captures a reason and the notice period
   (prefilled from company policy, editable).
2. **HR accepts it.** This computes the last working day (acceptance
   date + notice period, editable if the notice is waived or
   shortened) and auto-creates four standard **clearance** checklist
   items: Asset Return, Department/HOD Sign-off, Finance Sign-off,
   IT/Access Sign-off. Add more line items if the role needs extra
   steps.
3. **Clearance.** Each line gets marked *Done* as it's completed. The
   **Asset Return** line specifically checks the employee's asset
   register (§2) and refuses to complete while anything is still
   marked issued to them — return it there first.
4. **Compute Settlement.** Once clearance is fully done, HR computes
   the Full & Final statement: **Gratuity** (for employees with 5+
   years of service), **Earned Leave encashment** (unused balance paid
   out), any **notice-period shortfall recovery**, plus free-form
   additions/deductions. Every figure is editable after computing —
   the calculation is a correct starting point, not the final word
   (the Act has special cases, like waiving the 5-year gratuity rule
   for death/disability, that need human judgement).
5. **Settle**, then **Close** — closing is the final step: it archives
   the employee record and deactivates their system login
   automatically. This is irreversible, so it's confirmed before
   running.

The employee's **final month's salary** (including any Loss-of-Pay for
that last, partial month) goes through the normal payslip process
(§7), not the F&F statement — the two don't overlap.

---

## 11. Learning (LMS) & Performance (PMS)

**Menu: eLearning / Performance**

- **LMS**: courses, videos, quizzes, and certifications. New hires are
  auto-enrolled in Induction courses the moment they're hired (§1) —
  nothing manual needed. An annual **Re-Induction** cycle re-enrolls
  everyone and resets completion, run automatically each year.
- **PMS**: set employee goals/OKRs with weighted progress, run review
  cycles (quarterly/half-yearly/annual), and record appraisals with
  both self and manager ratings. Training assigned in the LMS can be
  linked to specific performance goals.

---

## 12. Employee Self-Service (ESS)

**Menu: My HR** (visible to every employee, scoped to their own data
only)

- **My Payslips** — confirmed payslips only; drafts stay
  HR-internal until finalized.
- **My Absence Flags** — any pending attendance exceptions raised
  against them (§3) — read-only; if one looks wrong, raise it with HR
  rather than trying to resolve it here.
- **My Assets** — equipment currently issued to them.
- **My Resignation** — file and submit their own exit request. Once HR
  accepts it, the record becomes read-only to the employee — clearance
  and settlement figures are handled by HR from that point.
- Leave requests and attendance are available through Odoo's own
  native **Time Off** and **Attendances** apps, same as any employee.

---

## 13. The HCM Dashboard

**Menu: HCM Dashboard**

A one-screen summary for HR/management.

**Choosing the period.** At the top pick a **Period** preset — Today,
This week, This month to date (the default), Last month, Last 30 days,
This quarter, This FY to date — or type your own **From** and **To**
dates (the preset then shows *Custom*). Both dates are included, and
"today" is your own timezone's date (India time unless your user
preferences say otherwise). The financial year is April–March unless
your company has set a different fiscal year end. **To** is the old
**As of** date: every snapshot figure below is as at the end of that day.

**For the period (From → To)** — what happened in the range:

| Card | What it means |
|---|---|
| Gross Payout | Gross of confirmed payslips for pay periods starting in the range |
| Joiners | Employees whose first contract starts in the range |
| Leavers | Exit requests closed with a last working day in the range |
| Leave Days Taken | Approved leave days falling in the range (a leave that crosses the edge counts only its share of days) |
| Hours Worked | Attendance hours checked in during the range |
| Absences Flagged | Unexplained-absence exceptions raised for days in the range |
| Approved Overtime Hours | Approved overtime on attendances in the range |

**As of To** — a snapshot at the end of the To date:

| Card | What it means |
|---|---|
| Headcount | Employees on the books: joined by To and not departed by then |
| Payslips Pending Confirmation | Draft/awaiting-approval payslips for periods starting on or before To |
| Open Vacancies | Approved vacancy requests still short of their target headcount |
| Overdue Joining Reports | New hires past their joining-report SLA who haven't submitted |
| Pending Absence Reviews | Attendance exceptions HR hasn't excused or confirmed yet |
| Open Exit Requests | Resignations in progress (submitted through settled, not yet closed) |
| Attrition (12 months to To) | Exits closed in the 12 months ending To, over headcount as of To |
| EL Encashment Liability | Earned Leave balance as of To × the same formula the F&F settlement uses |

Company-wide figures need company-wide rights: Payroll cards need the
Payroll user role, leave cards the Time Off officer role, attendance and
overtime the Attendances administrator role, joiners/EL liability read
access to contracts. Without them a card shows 0 (never just your own
records) and a yellow note at the top names the figures affected.
