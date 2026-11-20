{
    "name": "bpro LMS — Learning Management",
    "summary": "Courses, training paths and certifications under the bpro brand",
    "description": """
bpro Learning Management System
===============================
Builds on Odoo eLearning (website_slides):
* Courses with videos, documents and quizzes
* Certifications and completion tracking
* Training linked to performance goals (with bpro PMS)
""",
    "version": "18.0.1.0.1",
    "category": "Website/eLearning",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["website_slides", "hr", "bpro_base", "bpro_pms"],
    "data": [
        "security/ir.model.access.csv",
        "security/lms_security.xml",
        "data/course_taxonomy.xml",
        "data/lms_cron.xml",
        "views/lms_menus.xml",
        "views/training_report_views.xml",
        "views/lms_360_views.xml",
    ],
    "application": True,
    "installable": True,
}
