{
    "name": "bpro HRMS Portal — Landing & Login Experience",
    "summary": "Marketing-grade landing page and premium login for bpro HCM HRMS Suite Pro",
    "description": """
Public-facing experience layer for the bpro HCM HRMS Suite Pro platform:

* Landing page (served at /) - animated hero, live-feel product mockup,
  module grid covering the full hire-to-retire suite (Core HR, Payroll
  with India statutory compliance, Recruitment/ATS, Attendance, Leave &
  LOP, Exit & F&F, ESS, LMS, PMS), stats band, lifecycle strip and CTA.
* Login page - split-screen design: animated brand panel on the left,
  clean login card on the right. Overrides bpro_branding's minimal
  card (priority 30 > 20) when both are installed; degrades gracefully
  on mobile (brand panel hides, card fills).

All motion respects prefers-reduced-motion. No external JS libraries -
scroll reveals, counters and parallax are ~100 lines of vanilla JS.
""",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["web", "website"],
    "data": [
        "views/landing_templates.xml",
        "views/login_templates.xml",
        "views/footer_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "bpro_hrms_portal/static/src/scss/hrms_portal.scss",
            "bpro_hrms_portal/static/src/js/hrms_portal.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
