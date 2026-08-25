{
    "name": "bpro Overtime — OT Pay & Compensatory Off",
    "summary": "Approved overtime hours reach the payslip (Factories Act double rate) or convert to comp-off leave (R6.5)",
    "description": """
Native Attendance already computes and approves overtime hours - but
they never reached the payslip. This closes that gap, with the
company choosing (per policy) between the two lawful compensations:

* PAY mode: an OT salary rule pays approved overtime hours at
  hourly-gross x multiplier. The multiplier is company-configurable,
  seeded at 2.0 - Factories Act 1948 s59's "twice the ordinary rate of
  wages" for factory workers. The hourly ordinary rate is determined by
  employment type:
  - CTC-based (Permanent, FTC, Trainee): UNPRORATED monthly gross /
    (26 x 8) - the statutory divisor convention.
  - Daily Wage: daily_wage_rate / 8 - the per-hour equivalent of the
    contracted daily rate.
  NET is extended (cross-module noupdate override, same technique as
  the LOP chain) to GROSS + OT - DED.

  ESI on OT wages: OT pay is included in the ESI contribution base
  as required (ESI Act s.2(22)). OT is excluded from the eligibility
  threshold test only - once an employee qualifies, ESI is levied on
  GROSS + OT.

* COMP-OFF mode: a conversion wizard turns approved, not-yet-converted
  overtime hours into validated Compensatory Off leave allocations
  (8 OT hours = 1 day, floor half-days). Converted attendances are
  flagged so re-running the wizard can never double-credit. The OT
  salary rule checks the company policy, so an employee can never get
  both pay AND comp-off for the same hours.
""",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_attendance", "bpro_leave"],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_leave_type_compoff.xml",
        "data/hr_salary_rule_ot.xml",
        "views/bpro_compoff_wizard_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
}
