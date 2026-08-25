from odoo import api, fields, models
from odoo.exceptions import UserError


class BproJobOffer(models.Model):
    _name = "bpro.job.offer"
    _inherit = ["portal.mixin"]
    _description = "Job Offer"
    _order = "create_date desc"

    applicant_id = fields.Many2one("hr.applicant", required=True, ondelete="cascade")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    offer_date = fields.Date(default=lambda self: fields.Date.context_today(self))
    proposed_designation = fields.Char(
        required=True,
        help="Defaults from the job position but editable - the offered "
        "title doesn't always match the requisitioned one exactly.",
    )
    proposed_ctc = fields.Float(string="Proposed CTC (Annual)")
    joining_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("expired", "Expired"),
        ],
        default="draft",
        required=True,
    )

    # Filled in by the candidate via the public portal link, not HR.
    candidate_address = fields.Text(string="Address")
    candidate_dob = fields.Date(string="Date of Birth")
    candidate_pan = fields.Char(string="PAN")
    candidate_aadhar = fields.Char(string="Aadhar Number")
    candidate_emergency_contact_name = fields.Char(string="Emergency Contact Name")
    candidate_emergency_contact_phone = fields.Char(string="Emergency Contact Phone")
    candidate_bank_account_number = fields.Char(string="Bank Account Number")
    candidate_bank_ifsc = fields.Char(string="Bank IFSC")

    accepted_date = fields.Datetime(readonly=True, copy=False)
    declined_date = fields.Datetime(readonly=True, copy=False)
    declined_reason = fields.Text(readonly=True, copy=False)

    employee_id = fields.Many2one(
        "hr.employee", readonly=True, copy=False,
        help="Set by Finalize Hiring - the 'final approval of the HR "
        "Dept' the requirement describes. Presence of this field is the "
        "finalization marker; there's no separate state value for it "
        "since accept/decline is the candidate's decision and this is a "
        "distinct, later HR-side action.",
    )
    finalized_date = fields.Datetime(readonly=True, copy=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/bpro/offer/{rec.id}"

    def action_send(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("Only draft offers can be sent.")
            if not rec.applicant_id.email_from:
                raise UserError(
                    "The applicant/candidate has no email on file - "
                    "cannot send the offer link."
                )
            rec._portal_ensure_token()
        self.write({"state": "sent"})
        for rec in self:
            rec._bpro_send_offer_email()

    def _bpro_send_offer_email(self):
        self.ensure_one()
        url = self.get_portal_url()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        link = f"{base_url}{url}"
        self.env["mail.mail"].sudo().create({
            "subject": f"Offer of Employment - {self.proposed_designation}",
            "email_to": self.applicant_id.email_from,
            "body_html": (
                f"<p>Dear {self.applicant_id.partner_name or 'Candidate'},</p>"
                f"<p>We are pleased to offer you the position of "
                f"<strong>{self.proposed_designation}</strong>.</p>"
                f"<p>Please review the offer and complete your details "
                f'here: <a href="{link}">{link}</a></p>'
            ),
        }).send()
        # WhatsApp notification alongside email: sends only if a provider
        # is configured on the company (see res.company.whatsapp_provider).
        # Falls back gracefully to email-only when provider is 'none' or
        # the applicant has no mobile number on file.
        phone = (
            self.applicant_id.partner_mobile
            or self.applicant_id.partner_phone
        )
        if phone:
            self.company_id.sudo()._bpro_whatsapp_send(
                phone,
                f"Dear {self.applicant_id.partner_name or 'Candidate'}, "
                f"you have received an offer for {self.proposed_designation}. "
                f"Review and respond here: {link}",
            )

    def action_accept_from_portal(self):
        self.ensure_one()
        if self.state != "sent":
            raise UserError("This offer is not open for a response.")
        self.write({
            "state": "accepted",
            "accepted_date": fields.Datetime.now(),
        })

    def action_decline_from_portal(self, reason=None):
        self.ensure_one()
        if self.state != "sent":
            raise UserError("This offer is not open for a response.")
        self.write({
            "state": "declined",
            "declined_date": fields.Datetime.now(),
            "declined_reason": reason,
        })

    def action_finalize_hiring(self):
        """The 'unique employee code + Appointment Order on final HR
        approval' requirement. Reuses native hr_recruitment's own
        applicant-to-employee conversion rather than duplicating it -
        this only adds the employee_code assignment and the link back
        from the offer.
        """
        for rec in self:
            if rec.state != "accepted":
                raise UserError(
                    "Only an accepted offer can be finalized into hiring."
                )
            if rec.employee_id:
                raise UserError(
                    f"This offer was already finalized on "
                    f"{rec.finalized_date} - {rec.employee_id.name} "
                    f"({rec.employee_id.employee_code})."
                )
            # sudo(): create_employee_from_applicant() is native
            # hr_recruitment logic gated by its own manager group; the
            # real permission gate for THIS action is
            # group_hr_recruitment_manager on the button/ir.model.access,
            # same scoped-sudo() pattern as R4.1/R4.2.
            action = rec.applicant_id.sudo().create_employee_from_applicant()
            employee = rec.env["hr.employee"].browse(action["res_id"])
            code = rec.env["ir.sequence"].sudo().next_by_code("bpro.employee.code")
            employee.sudo().write({"employee_code": code})
            rec.write({
                "employee_id": employee.id,
                "finalized_date": fields.Datetime.now(),
            })
            # Auto-create the joining-report tracker (R4.5) - HR
            # shouldn't have to remember to do this as a separate step.
            # bpro_lms's own hr.employee.create() override (already
            # fired above, via create_employee_from_applicant) handles
            # induction auto-enrollment - nothing to do for that here.
            rec.env["bpro.joining.report"].sudo().create({
                "employee_id": employee.id,
                "offer_id": rec.id,
                "expected_joining_date": rec.joining_date or fields.Date.context_today(rec),
            })
