# User Acceptance Testing (UAT) Checklist

Automated tests prove the code matches the formulas it was built
against. They do **not** prove an actual HR/payroll person at the
client has run the real workflows with real (or realistic dummy) data
and confirmed the results look right to them. That's what this
checklist is for — walk through it with the client's own HR/payroll
staff before the first real payroll run, on a staging copy of the
database, not production.

If you want a production-like but non-public app stack for that, use the
repo's sample overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.uat.yml up -d
```

Use a **staging database with realistic but non-final data** — either
a handful of real employees the client is comfortable testing with, or
fabricated but realistic ones (correct salary bands, real state
assignments). Testing entirely with garbage data (₹1 salaries, no real
state config) won't actually validate anything.

For each row: run it, tick it, and write down anything that looked
wrong even if you're not sure it's actually wrong — better flagged and
dismissed than missed.

---

## 1. Recruitment → Hire

| # | Step | Expected result | ✓ | Notes |
|---|---|---|---|---|
| 1.1 | HOD raises a vacancy request | Appears in HR's approval queue | | |
| 1.2 | HR approves it | A Job Position is created automatically | | |
| 1.3 | Two interviewers each submit an evaluation for the same applicant | Both evaluations are saved independently — neither overwrites the other | | |
| 1.4 | HR sends an offer | Candidate receives an email with a working link | | |
| 1.5 | Candidate accepts via the link, fills in their details | Details save; offer status changes to Accepted | | |
| 1.6 | HR clicks Finalize Hiring | Employee record created, unique employee code assigned, Appointment Order PDF generates correctly, probation starts | | |

## 2. Attendance & Absence

| # | Step | Expected result | ✓ | Notes |
|---|---|---|---|---|
| 2.1 | Import a real (or realistic) punch-log CSV | Correct number of records imported; any bad rows are listed, not silently dropped | | |
| 2.2 | Check one imported record's time against the source file | Time matches — **specifically check this isn't off by 5.5 hours** (IST/UTC conversion) | | |
| 2.3 | Leave a working day with no attendance and no leave request | It's flagged as a pending Attendance Exception (same day or next morning via the cron) | | |
| 2.4 | HR excuses one exception, confirms another as absent | States update correctly; only the confirmed-absent one later affects pay | | |

## 3. Leave

| # | Step | Expected result | ✓ | Notes |
|---|---|---|---|---|
| 3.1 | An employee requests Casual Leave | Goes to their manager for approval | | |
| 3.2 | Check an employee's Earned Leave balance | Reflects the accrual so far — spot-check the number against manual calculation | | |
| 3.3 | Approve a Loss of Pay leave request | It's flagged correctly for payroll to pick up | | |

## 4. Payroll

| # | Step | Expected result | ✓ | Notes |
|---|---|---|---|---|
| 4.1 | Run a payslip for an employee with **full attendance, no leave** | Basic/HRA/Gross match their contract exactly — no unexpected proration | | |
| 4.2 | Run a payslip for an employee with **a confirmed absence or LOP day that month** | Basic/HRA/Gross/PF/ESI are all reduced proportionally — **have HR hand-calculate this one and compare** | | |
| 4.3 | Check PF, ESI, PT, LWF, TDS lines against the client's own manual/previous-system numbers for the same employee | Figures match (small last-digit rounding differences are expected; anything larger needs investigation) | | |
| 4.4 | Confirm the payslip | State changes to Done; it becomes visible in the employee's ESS "My Payslips" | | |
| 4.5 | Email the payslip | Employee receives a PDF that opens and reads correctly | | |

## 5. Statutory Filing

| # | Step | Expected result | ✓ | Notes |
|---|---|---|---|---|
| 5.1 | Generate the month's statutory filings | All five files download | | |
| 5.2 | Open the ECR file, spot-check one employee's row against their payslip | UAN, wages, PF figures match | | |
| 5.3 | Check the summary for any "missing identifier" warnings | Every real employee has UAN/ESI number/PAN/bank account on file (or the gap is a known, accepted one) | | |

## 6. Exit & Full-and-Final

| # | Step | Expected result | ✓ | Notes |
|---|---|---|---|---|
| 6.1 | File a test resignation, accept it | Standard clearance checklist appears (Asset/HOD/Finance/IT) | | |
| 6.2 | Try to complete the Asset Return line while an asset is still marked issued | It's blocked with a clear message | | |
| 6.3 | Return the asset, complete all clearance lines, compute settlement | Gratuity and EL encashment figures look right — **hand-calculate gratuity for a 5+ year test employee and compare** | | |
| 6.4 | Close the exit | Employee is archived, their login is deactivated, relieving letter is auto-created | | |

## 7. Employee Self-Service

| # | Step | Expected result | ✓ | Notes |
|---|---|---|---|---|
| 7.1 | Log in as a regular employee | Only "My HR" menu items are visible — no HR/admin menus | | |
| 7.2 | Check My Payslips | Only their own confirmed payslips show — nobody else's | | |
| 7.3 | File a resignation from ESS | Works the same as HR filing on their behalf | | |

---

## Sign-off

| Area | Tested by | Date | Accepted? |
|---|---|---|---|
| Recruitment | | | |
| Attendance | | | |
| Leave | | | |
| Payroll | | | |
| Statutory Filing | | | |
| Exit / F&F | | | |
| ESS | | | |

Once every row above is ticked and signed off, the deployment is
ready for its first real payroll run — but run that first real payroll
in parallel with the client's existing system/spreadsheet for at
least one cycle before fully cutting over, so any discrepancy is
caught before it becomes a real payment.
