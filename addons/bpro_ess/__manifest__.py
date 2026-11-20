{
    "name": "bpro ESS — Employee Self-Service",
    "summary": "Employees see their own payslips, absence flags, assets and file their own resignation (BES Human Capital Management)",
    "description": """
Employee self-service layer - pure security + menus, no new models.
Native Odoo already gives internal employee users their own leave
requests ("My Time Off", hr_holidays) and their own attendance records;
what it does NOT give them:

* Payslips: OCA payroll grants hr.payslip read only to
  payroll.group_payroll_user - employees cannot see their own slips at
  all. This module grants bpro_base.group_employee read on their OWN,
  DONE payslips only (drafts stay HR-internal until confirmed).
* Attendance exceptions: employees can now see their own pending
  absence flags (read-only - resolving them stays an HR action), so a
  wrongly-flagged day surfaces to the person who can explain it before
  it becomes a pay deduction.
* Assets: read-only view of equipment currently issued to them.
* Resignation: employees can file and submit their OWN exit request.
  Write access is deliberately scoped by ir.rule to draft/submitted
  states only - once HR accepts, the record (clearance, F&F figures)
  is out of the employee's hands. The HR-only transitions
  (accept/compute/settle/close) are additionally guarded at METHOD
  level in bpro_exit itself, because button visibility is not
  authorization.

Security-shape note (the R4.6 lesson applies here too):
bpro_base.group_client_hr implies group_hod implies group_employee, so
every own-records rule added for group_employee needs the counterpart
unrestricted rule for the staff group that already had full access -
otherwise HR/payroll staff would silently get narrowed to their own
records. hr.payslip previously had NO ir.rule at all (ACL-only), so
this module adds the payroll-user unrestricted rule explicitly.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_payroll", "bpro_attendance", "bpro_exit"],
    "data": [
        "security/ir.model.access.csv",
        "security/bpro_ess_security.xml",
        "views/bpro_ess_menus.xml",
    ],
    "installable": True,
    "application": False,
}
