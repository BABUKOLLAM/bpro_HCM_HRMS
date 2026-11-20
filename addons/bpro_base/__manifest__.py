{
    "name": "bpro Base — Roles & Multi-Company Security",
    "summary": "Four-tier role model shared by bpro LMS and bpro PMS",
    "description": """
Four-tier role model per the bpro LMS & PMS Architecture Roadmap:
* bpro Super Admin — all companies, all data, client onboarding
* Client HR Admin  — full access within own company only
* Head of Department (HOD) — own department's employees only
* Employee — self-service only

Record rules follow the three-tier pattern (company / department / self)
that every bpro module must reuse.
""",
    "version": "18.0.1.0.1",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["hr"],
    "data": [
        "security/bpro_security.xml",
    ],
    "installable": True,
}
