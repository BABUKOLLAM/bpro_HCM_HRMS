{
    "name": "bpro Statutory Filing — PF/ESI/PT/TDS Returns & Bank Advice",
    "summary": "Monthly compliance-cycle outputs from confirmed payslips: EPFO ECR, ESIC contribution, PT summary, Form 24Q data, bank salary advice (R6.1)",
    "description": """
Closes the loop between "the payroll engine computes correctly" and
"the payroll office operates the monthly compliance cycle" - without
this, someone re-keys payslip totals into each government portal by
hand every month.

One wizard (month + company) reads that month's CONFIRMED payslips
(state=done - drafts are work-in-progress and must never reach a
filing) and generates five downloadable files:

* EPFO ECR text file (the #~#-separated ECR 2.0 upload line format:
  UAN, name, gross, EPF/EPS/EDLI wages, EE share, EPS share, ER
  difference, NCP days, refund). NCP days come from
  hr.payslip.bpro_lop_days() - the SAME definition the LOP pay
  proration itself uses, so the filing can never disagree with the
  payslip.
* ESIC monthly contribution CSV (IP number, name, days worked, wages,
  EE contribution).
* Professional Tax summary CSV, grouped per PT state (each state's
  portal wants its own return - this gives the per-state numbers).
* Form 24Q quarterly TDS data CSV (PAN, per-month TDS for the quarter
  containing the selected month) - input for the NSDL RPU utility,
  not the .fvu file itself (that requires the RPU's own validations).
* Bank salary advice CSV (account, IFSC, NET) - the transfer sheet
  given to the bank.

Employees missing the identifier a file needs (UAN for ECR, IP number
for ESIC, PAN for 24Q, bank account for the advice) are REPORTED in
the wizard's summary and excluded from that file - never silently
dropped, same error-reporting discipline as the attendance import.

File-format caveat, same verify-before-go-live discipline as the PT/
LWF/TDS seed data: the ECR/ESIC layouts follow the widely-published
formats but portals revise them by notification - verify one generated
file against the portal's current spec before the first real upload.

New employee fields (this module, not bpro_payroll): uan, esi_number.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources/Payroll",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_payroll", "bpro_leave"],
    "data": [
        "security/ir.model.access.csv",
        "views/bpro_statutory_filing_views.xml",
        "views/hr_employee_views.xml",
    ],
    "installable": True,
    "application": False,
}
