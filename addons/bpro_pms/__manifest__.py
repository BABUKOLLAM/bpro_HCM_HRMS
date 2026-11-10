{
    "name": "bpro PMS — Performance Management",
    "summary": "Goals, KPIs, review cycles and appraisals for organisations",
    "description": """
bpro Performance Management System
==================================
* Employee goals / OKRs with weighted progress tracking
* Review cycles (quarterly, half-yearly, annual)
* Appraisals with self and manager ratings
* Links training (bpro LMS) to performance goals
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources/Appraisals",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "hr", "mail"],
    "data": [
        "security/pms_security.xml",
        "security/ir.model.access.csv",
        "views/pms_goal_views.xml",
        "views/pms_cycle_views.xml",
        "views/pms_appraisal_views.xml",
        "views/pms_menus.xml",
        "views/pms_competency_views.xml",
    ],
    "application": True,
    "installable": True,
}
