{
    "name": "bpro Demo Data — Evaluation Sample Company",
    "summary": "A small, believable 'click around and see it working' dataset for evaluators - never installed in production",
    "description": """
A fresh install of this suite is otherwise empty - not a great first
impression for anyone evaluating it. This module populates:

* One department, with a manager hired through the REAL recruitment
  workflow (vacancy -> applicant -> offer -> accept -> finalize hiring)
  - proving the actual engine, not a facsimile of it.
* Four more employees spanning the remaining employment categories
  from bpro_employment_type: Fixed Term Contract, Trainee/Apprentice,
  and Daily Wage (with real attendance this month, so their Basic
  computes to something on a payslip rather than zero).
* A computed and confirmed payslip - calls the real payroll engine
  (compute_sheet), so every figure is exactly what production would
  produce.
* An Earned Leave allocation, so the leave-liability KPI on the
  dashboard shows something real.

Gated on the exact same tools.config['without_demo'] flag Odoo's own
native demo-loading code checks - every install command already used
throughout this repo (--without-demo=all, in the README, SETUP_GUIDE,
and the CI workflow) correctly skips this without any special-casing.
Dates are relative to install time, not hard-coded, so the demo always
looks current.

Do NOT depend on this module from anything else, and do NOT include it
in a production install command.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Dr. Babu & bpro Technologies",
    "website": "https://www.bpropms.com",
    "license": "LGPL-3",
    "depends": [
        "bpro_recruitment",
        "bpro_attendance",
        "bpro_leave",
        "bpro_employment_type",
        "bpro_hcm_dashboard",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
