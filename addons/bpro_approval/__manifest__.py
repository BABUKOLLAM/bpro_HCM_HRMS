{
    "name": "bpro Approval — Threshold-Gated Approval Workflow",
    "summary": "Generic approval-request mixin used by bpro ERP modules to gate actions above a configurable threshold",
    "description": """
Shared foundation for the bpro ERP modules (Sales, Inventory, Finance):

* bpro.policy — per-company configurable numeric thresholds (discount pct, stock-adjustment value, 3-way-match tolerance pct, ...)
* bpro.approval.mixin — abstract model other addons inherit to gate an action (confirm, post, adjust) behind manager approval once a configurable threshold is exceeded. Uses Odoo's native mail.activity system to notify the approver — no separate approval-inbox UI needed.

Concrete models must override _approval_policy_key(), _approval_amount() and _approval_group_xmlid() before calling the mixin's actions.
""",
    "version": "18.0.1.0.1",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/policy_views.xml",
    ],
    "installable": True,
    "application": False,
}
