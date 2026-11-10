{
    "name": "bpro Attendance — Punch Import & Absence Review",
    "summary": "Device-agnostic attendance-log import and unauthorized-absence review (BES Human Capital Management, R5.1)",
    "description": """
Attendance build-out for the India client, layered on native
Odoo Attendance (hr_attendance) rather than replacing it: check-in/out,
overtime computation and approval, and the resource-calendar-based
expected-hours logic are all native here.

Gap this closes: the vendored payroll engine's own worked-days
computation (payroll/models/hr_payslip.py::_compute_worked_days) pays
the FULL expected calendar days regardless of actual attendance - a day
with no attendance record and no approved leave still counts as a paid
working day. This module is the first half of closing that gap: getting
real attendance data in, and turning "no record" into a reviewed
decision rather than a silent full-pay default. The payroll deduction
itself (Loss of Pay) is deliberately deferred to the Leave phase, where
it can be designed once, consistently, alongside unpaid-leave handling
and the PF/ESI wage-base proration question that both share.

R5.1 - punch import + absence exceptions:

* bpro.attendance.import: a device-agnostic CSV/XLSX import wizard.
  ME Polymers' actual biometric device brand/network setup wasn't known
  at build time (2026-08-13 scoping decision) - rather than guess a
  vendor SDK, this accepts the daily-summary export shape (badge_id,
  date, check_in, check_out) that virtually every punch-device's bundled
  management software can produce, matched to hr.employee via the
  native barcode (Badge ID) field. A live device connector is a clean
  future addition once the brand/network details are confirmed - not
  rebuilt, just added alongside this.
* bpro.attendance.exception: for every working day (per the employee's
  resource.calendar) with neither an hr.attendance record nor an
  approved/global leave (via employee.list_leaves() - the same leave-day
  definition the vendored payroll module itself uses, so "on leave"
  means the same thing here as it eventually will in payroll), a pending
  exception is raised for HR to Excuse or Confirm as Absence - per the
  client's explicit instruction that unexplained absence should be
  flagged for review, not auto-deducted.
* Detection runs on demand (wizard) or nightly via cron for the
  previous day.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_hr", "hr_attendance", "hr_holidays"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_attendance_security.xml",
        "data/bpro_attendance_cron.xml",
        "views/bpro_attendance_import_views.xml",
        "views/bpro_attendance_exception_views.xml",
    ],
    "installable": True,
    "application": False,
}
