{
    "name": "bpro Probation — Confirmation Workflow",
    "summary": "Probation tracking, due reminders, confirm/extend decisions and the confirmation letter (R6.3)",
    "description": """
The lifecycle gap between hiring and tenure: the recruitment flow ends
at the appointment order, but nothing tracked the probation period
(typically 6 months in Indian manufacturing), reminded HR when a
decision was due, or produced the confirmation letter. Standard
practice, previously entirely manual.

* res.company.probation_months (default 6, policy not statute - there
  is no statutory probation length in India for factory workers).
* hr.employee gains probation_state (probation/confirmed) and
  probation_end_date - auto-set by bpro_recruitment's Finalize Hiring
  (joining date + company policy months) so every new hire enters
  probation without a manual step. Employees created outside the
  recruitment flow (e.g. data import at go-live) default to confirmed -
  migrating an existing workforce shouldn't put everyone back on
  probation.
* action_confirm_probation() (confirmation date + letter) and
  action_extend_probation(months) - extension moves the end date and
  logs to the chatter rather than pretending a separate state machine
  is needed.
* Daily cron chatter-posts on employees whose probation end has
  arrived while still unconfirmed, tagging HR - the reminder half of
  the requirement.
* Confirmation Letter QWeb PDF, same pattern as the appointment order.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_hr", "bpro_recruitment"],
    "data": [
        "data/bpro_probation_cron.xml",
        "views/report_confirmation_letter.xml",
        "views/hr_employee_views.xml",
        "views/res_company_views.xml",
    ],
    # No ir.model.access.csv: this module adds fields to existing
    # models (hr.employee, res.company, bpro.job.offer) only - their
    # access rules already govern everything here.
    "installable": True,
    "application": False,
}
