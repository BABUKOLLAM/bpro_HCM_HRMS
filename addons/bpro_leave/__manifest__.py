{
    "name": "bpro Leave — India Leave Types & Loss-of-Pay Payroll Proration",
    "summary": "Factories Act leave types, EL accrual, and LOP payslip proration wired to attendance exceptions (BES Human Capital Management, R5.2)",
    "description": """
Leave build-out for the India client, layered on native Odoo Time Off
(hr_holidays) rather than replacing it: leave request/approval workflow,
allocations, and the accrual engine are all native and untouched here.

Statutory grounding (researched per-state 2026-08-13 for Kerala, Tamil
Nadu, Karnataka, Andhra Pradesh - the client's four states, same as
bpro_payroll's PT/LWF configs; a factory context, so the Factories Act
1948 governs, not the states' Shops & Establishments Acts):

* Earned Leave IS statutory and uniform across all four states
  (Factories Act s79: 1 day per 20 worked, 240-day qualifying year,
  30-day carry-forward cap, encashment on separation) - seeded as a
  worked-time accrual plan.
* Casual/Sick leave have NO statutory floor for factories in any of the
  four states (the oft-quoted 12+12 comes from S&E Acts that don't apply
  to factories) - seeded as adjustable company policy, clearly marked.
* Maternity (26 weeks, central) uniform; Paternity has no private-sector
  mandate anywhere - seeded at the 15-day central-government benchmark
  as company policy.
* National/festival holidays (Kerala 13 / TN 9 / Karnataka 10 / AP 8 per
  their own N&FH Acts) are deliberately NOT leave types - they belong in
  resource.calendar global leaves per work location at go-live.

R5.2 - LOP payroll proration (the point of this phase):

* hr.leave.type gains bpro_is_lop_type; a seeded "Loss of Pay" type
  carries it.
* hr.payslip.bpro_lop_factor(): payable fraction of the period =
  (working days - LOP days) / working days, where LOP days are the
  date-set union of HR-confirmed bpro.attendance.exception records
  (bpro_attendance R5.1) and approved LOP-type leave days.
* A hidden LOP_FACTOR salary rule (sequence 5, before BASIC) exposes
  that factor to the rule chain; BASIC/LTA/MEAL/CONV/SALW are overridden
  to multiply by it. HRA/GROSS/NET prorate automatically as derived
  values, and - per the client's confirmed 2026-08-13 decision - PF and
  ESI prorate too, with zero changes to their rules: PF_WAGE follows the
  shrunken BASIC, ESI follows the shrunken GROSS.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_hr", "bpro_attendance", "bpro_payroll", "hr_holidays"],
    "data": [
        "data/hr_leave_type_data.xml",
        "data/hr_salary_rule_lop.xml",
        "views/hr_leave_type_views.xml",
    ],
    "installable": True,
    "application": False,
}
