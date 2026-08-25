import base64
from calendar import monthrange
from datetime import date

from odoo import fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    # OCA payroll's own credit_note field has no default=False, so new
    # payslips get NULL in Postgres. Payslips.sum() (used by the
    # half-yearly PT accumulation in this module) does
    # "WHEN hp.credit_note = False THEN pl.total ELSE -pl.total" - and
    # NULL = False is NULL in SQL, not TRUE, so it silently falls into the
    # ELSE branch and negates every sum. Re-declaring the field here with
    # an explicit default is the supported way to fix this without
    # touching the vendored module.
    credit_note = fields.Boolean(default=False)

    def bpro_esi_period_eligible(self, current_gross):
        """ESI contribution-period continuity: once an employee is covered
        at the start of a contribution period (April 1 or October 1), they
        stay covered for the full period even if a mid-period raise pushes
        their gross above the threshold. The threshold is re-tested only at
        the start of each new period.

        For the first payslip in a period (no prior confirmed payslip to
        anchor from), falls back to the plain threshold test on
        current_gross - same behaviour as before for that first month.
        """
        self.ensure_one()
        threshold = self.contract_id.company_id.esi_wage_threshold
        slip_date = self.date_from

        # Determine this payslip's contribution period start
        month = slip_date.month
        year = slip_date.year
        if 4 <= month <= 9:
            period_start = date(year, 4, 1)
        elif month >= 10:
            period_start = date(year, 10, 1)
        else:  # Jan-Mar: Oct-Mar period, started in the previous year
            period_start = date(year - 1, 10, 1)

        # If this IS the first month of the period, no prior payslip
        # exists in the period - fall back to the plain threshold test.
        if slip_date.month == period_start.month and slip_date.year == period_start.year:
            return current_gross <= threshold

        # Search for any confirmed payslip from the first month of the
        # period for this contract.
        last_day_of_start_month = monthrange(period_start.year, period_start.month)[1]
        period_first_month_end = period_start.replace(day=last_day_of_start_month)
        first_slip = self.env["hr.payslip"].search([
            ("contract_id", "=", self.contract_id.id),
            ("state", "=", "done"),
            ("date_from", ">=", period_start),
            ("date_to", "<=", period_first_month_end),
        ], order="date_from asc", limit=1)

        if not first_slip:
            # No confirmed anchor slip: fall back to plain threshold test.
            return current_gross <= threshold

        esi_line = first_slip.line_ids.filtered(lambda l: l.code == "ESI_EE")
        return bool(esi_line and sum(esi_line.mapped("total")) > 0)

    def action_email_payslip(self):
        """Push distribution (R6.2): email each confirmed slip's PDF to
        the employee. ESS gives pull access ('My Payslips'); factory
        workers respond better to push. Multi-record safe, so it can be
        called from a list selection for the whole payroll run."""
        sent, skipped = 0, []
        for slip in self:
            if slip.state != "done":
                raise UserError(
                    f"{slip.employee_id.name}'s slip is not confirmed - "
                    "only done payslips are distributed."
                )
            email_to = slip.employee_id.work_email or slip.employee_id.private_email
            if not email_to:
                skipped.append(slip.employee_id.name)
                continue
            pdf, _dummy = self.env["ir.actions.report"]._render_qweb_pdf(
                "bpro_payroll.action_report_bpro_payslip", res_ids=slip.ids
            )
            attachment = self.env["ir.attachment"].sudo().create({
                "name": f"Payslip_{slip.employee_id.name}_{slip.date_from.strftime('%Y%m')}.pdf",
                "datas": base64.b64encode(pdf),
                "res_model": "hr.payslip",
                "res_id": slip.id,
            })
            self.env["mail.mail"].sudo().create({
                "subject": f"Payslip — {slip.date_from.strftime('%B %Y')}",
                "email_to": email_to,
                "body_html": (
                    f"<p>Dear {slip.employee_id.name},</p>"
                    f"<p>Please find attached your payslip for "
                    f"{slip.date_from.strftime('%B %Y')}.</p>"
                ),
                "attachment_ids": [(4, attachment.id)],
            }).send()
            sent += 1
        if skipped:
            # Surface the gap rather than silently not delivering -
            # same discipline as the filing wizard.
            raise UserError(
                f"Sent {sent} payslip(s). No email address on file for: "
                + ", ".join(skipped)
            )
        return True
