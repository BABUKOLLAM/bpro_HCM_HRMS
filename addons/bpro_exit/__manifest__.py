{
    "name": "bpro Exit — Separation, Clearance & Full-and-Final Settlement",
    "summary": "Resignation workflow, clearance checklist and F&F settlement with gratuity + EL encashment (BES Human Capital Management, R5.3)",
    "description": """
Exit/Separation build-out for the India client - the last BD-014 gap
after Attendance (R5.1) and Leave (R5.2). Native Odoo's departure
handling is a single wizard setting reason/date and archiving the
employee (bpro_hr already extends it to deactivate the login); the
entire resignation-to-settlement workflow before that point is what
this module adds.

R5.3 - exit workflow + clearance + F&F:

* bpro.exit.request: resignation workflow (draft -> submitted ->
  accepted -> clearance -> settled -> closed). Notice period prefilled
  from res.company.exit_notice_days (2026-08-13 scoping decision:
  configurable notice with HR able to waive/shorten per case) - the
  last working day is computed from acceptance date + notice but stays
  editable for exactly that reason.
* Clearance checklist: on acceptance, four standard lines are
  auto-created (Asset Return, Department/HOD Sign-off, Finance
  Sign-off, IT/Access Sign-off - all four confirmed in scoping) and
  ad-hoc lines can be added freely per exit ("anything extra as per
  position", per the same scoping answer). The Asset Return line
  refuses completion while any bpro.employee.asset record (from
  recruitment R4.5) is still issued to the departing employee - the
  register is the source of truth, not a manual tick.
* F&F settlement on the same record: gratuity per the Payment of
  Gratuity Act 1972 (15/26 x monthly Basic x completed years, 5-year
  eligibility, >6-month fraction rounds up a year, statutory cap
  configurable at the company - seeded Rs 20,00,000), EL encashment
  per Factories Act s79(11) (remaining Earned Leave balance x
  Basic/26), notice-shortfall recovery (prefilled, editable), plus
  free-form addition/deduction lines. F&F Statement PDF follows the
  same QWeb pattern as the offer letter/Form 16.
* Settling requires every clearance line done; closing registers the
  departure through the native wizard path, so bpro_hr's existing
  login-deactivation override fires - reused, not duplicated.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "bpro_hr", "bpro_leave", "bpro_recruitment"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_exit_security.xml",
        "views/report_fnf_statement.xml",
        "views/bpro_exit_request_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
}
