from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from . import date_range as dr

# Which KPI follows which date. FLOW figures add up what happened
# between From and To (inclusive); STOCK figures are a snapshot as of
# To. Kept as data so the view labels, tests and anyone porting a KPI
# can see the rule in one place.
FLOW_KPIS = (
    "payroll_mtd_gross",
    "joiners_count",
    "leavers_count",
    "leave_days_taken",
    "attendance_worked_hours",
    "attendance_exceptions_raised",
    "overtime_approved_hours",
)
STOCK_KPIS = (
    "headcount",
    "payroll_pending_confirmation",
    "recruitment_open_vacancies",
    "recruitment_overdue_joining_reports",
    "attendance_pending_exceptions",
    "exit_open_requests",
    "attrition_rate_pct",
    "el_liability",
)


def _default_to(model):
    ctx_to = model.env.context.get("default_as_of_date")
    if ctx_to:
        return fields.Date.to_date(ctx_to)
    return model._local_today()


class BproHcmDashboard(models.TransientModel):
    _name = "bpro.hcm.dashboard"
    _description = "bpro HCM Dashboard"

    period_preset = fields.Selection(
        dr.PRESETS, string="Period", default="month_to_date", required=True,
    )
    date_from = fields.Date(
        string="From", required=True,
        default=lambda self: _default_to(self).replace(day=1),
        help="First day of the period, inclusive. Flow figures (joiners, "
        "leavers, leave taken, attendance, payroll cost, overtime) count "
        "what happened from this day to To.",
    )
    # Kept under its original name for compatibility: "As of" now means
    # the To end of the range. Stock figures (headcount, balances,
    # backlogs) are a snapshot as of this date.
    as_of_date = fields.Date(
        string="To", required=True,
        default=lambda self: _default_to(self),
        help="Last day of the period, inclusive - and the 'as of' date "
        "for headcount, balances and open backlogs.",
    )
    period_label = fields.Char(compute="_compute_period_label")
    access_note = fields.Char(
        compute="_compute_kpis",
        help="Figures this user's access rights don't cover (shown as 0).",
    )
    as_of_label = fields.Char(compute="_compute_period_label")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    # --- flows: From..To -------------------------------------------------
    payroll_mtd_gross = fields.Monetary(
        string="Gross Payout (period)", compute="_compute_kpis",
        help="GROSS of confirmed payslips whose pay period starts From..To.",
    )
    joiners_count = fields.Integer(string="Joiners (period)", compute="_compute_kpis")
    leavers_count = fields.Integer(string="Leavers (period)", compute="_compute_kpis")
    leave_days_taken = fields.Float(
        string="Leave Days Taken (period)", compute="_compute_kpis", digits=(16, 1),
    )
    attendance_worked_hours = fields.Float(
        string="Hours Worked (period)", compute="_compute_kpis", digits=(16, 1),
    )
    attendance_exceptions_raised = fields.Integer(
        string="Absences Flagged (period)", compute="_compute_kpis",
    )
    overtime_approved_hours = fields.Float(
        string="Approved Overtime Hours (period)", compute="_compute_kpis", digits=(16, 1),
    )

    # --- stocks: as of To ------------------------------------------------
    headcount = fields.Integer(string="Headcount (as of To)", compute="_compute_kpis")
    payroll_pending_confirmation = fields.Integer(compute="_compute_kpis")
    recruitment_open_vacancies = fields.Integer(compute="_compute_kpis")
    recruitment_overdue_joining_reports = fields.Integer(compute="_compute_kpis")
    attendance_pending_exceptions = fields.Integer(compute="_compute_kpis")
    exit_open_requests = fields.Integer(compute="_compute_kpis")
    attrition_rate_pct = fields.Float(compute="_compute_kpis", digits=(16, 2))
    el_liability = fields.Monetary(compute="_compute_kpis")

    # ------------------------------------------------------------------
    # Period handling
    # ------------------------------------------------------------------
    @api.model
    def _user_tz(self):
        return self.env.context.get("tz") or self.env.user.tz or dr.DEFAULT_TZ

    @api.model
    def _local_today(self):
        return dr.local_today(self._user_tz())

    @api.model
    def _preset_dates(self, preset, company=None):
        company = company or self.env.company
        return dr.preset_range(preset, self._local_today(), dr.company_fy_end(company))

    @api.onchange("period_preset")
    def _onchange_period_preset(self):
        for rec in self:
            if rec.period_preset and rec.period_preset != "custom":
                rec.date_from, rec.as_of_date = rec._preset_dates(rec.period_preset)

    @api.onchange("date_from", "as_of_date")
    def _onchange_dates_to_custom(self):
        # Idempotent: the preset onchange above writes the dates, which
        # re-enters here - only a real hand edit flips the label.
        for rec in self:
            if not (rec.date_from and rec.as_of_date) or rec.period_preset == "custom":
                continue
            if (rec.date_from, rec.as_of_date) != rec._preset_dates(rec.period_preset):
                rec.period_preset = "custom"

    @api.constrains("date_from", "as_of_date")
    def _check_range(self):
        for rec in self:
            if rec.date_from and rec.as_of_date and rec.date_from > rec.as_of_date:
                raise ValidationError("'From' must be on or before 'To'.")

    @api.depends("date_from", "as_of_date")
    def _compute_period_label(self):
        def fmt(day):
            return day.strftime("%d %b %Y") if day else ""

        for rec in self:
            rec.period_label = "%s – %s" % (fmt(rec.date_from), fmt(rec.as_of_date))
            rec.as_of_label = fmt(rec.as_of_date)

    @api.depends("date_from", "as_of_date")
    def _compute_kpis(self):
        for rec in self:
            if not rec.as_of_date:
                for name in FLOW_KPIS + STOCK_KPIS:
                    rec[name] = 0
                rec.access_note = False
                continue
            data = self._get_kpi_data(
                self.env.company, rec.as_of_date, rec.date_from or rec.as_of_date
            )
            for field_name, value in data.items():
                rec[field_name] = value

    # ------------------------------------------------------------------
    # KPI maths
    # ------------------------------------------------------------------
    @api.model
    def _first_contract_dates(self, company):
        """{employee_id: earliest non-cancelled contract start}."""
        if not self.env["hr.contract"].has_access("read"):
            return {}
        rows = self.env["hr.contract"].with_context(active_test=False)._read_group(
            [("employee_id.company_id", "=", company.id), ("state", "!=", "cancel")],
            ["employee_id"], ["date_start:min"],
        )
        return {employee.id: start for employee, start in rows if employee}

    @api.model
    def _headcount_as_of(self, company, as_of_date, first_contract=None):
        """Employees on the books at the end of ``as_of_date``: joined on
        or before it (first contract; no contract = joining unknown, so
        counted) and not departed by then. Archived employees count only
        if their departure date is after ``as_of_date``."""
        if first_contract is None:
            first_contract = self._first_contract_dates(company)
        employees = self.env["hr.employee"].with_context(active_test=False).search([
            ("company_id", "=", company.id),
            "|", ("active", "=", True), ("departure_date", "!=", False),
        ])
        count = 0
        for employee in employees:
            if employee.departure_date and employee.departure_date <= as_of_date:
                continue
            joined = first_contract.get(employee.id)
            if joined and joined > as_of_date:
                continue
            count += 1
        return count

    @api.model
    def _get_kpi_data(self, company, as_of_date, date_from=None):
        """Plain @api.model method, directly unit testable - same
        convention as the ERP-wide bpro_dashboard this repo was
        extracted from, kept for anyone porting KPIs back and forth.

        ``as_of_date`` is the inclusive To; ``date_from`` the inclusive
        From, defaulting to the 1st of To's month (the pre-range
        "month to date" behaviour, so old callers get old figures)."""
        date_to = as_of_date
        date_from = date_from or date_to.replace(day=1)
        utc_start, utc_stop = dr.utc_bounds(date_from, date_to, self._user_tz())
        data = {}
        # Never sudo: record rules/ACLs decide what this user may count.
        # A model the user can't read at all gives 0 plus a note, rather
        # than an AccessError that would blank the whole dashboard.
        hidden = []
        can_read_contracts = self.env["hr.contract"].has_access("read")
        if not can_read_contracts:
            hidden += ["Joiners", "EL Liability"]

        # ---------------- flows ----------------
        payslips_done = self.env["hr.payslip"].search([
            ("company_id", "=", company.id),
            ("state", "=", "done"),
            ("date_from", ">=", date_from),
            ("date_from", "<=", date_to),
        ])
        gross_lines = self.env["hr.payslip.line"].search([
            ("slip_id", "in", payslips_done.ids), ("code", "=", "GROSS"),
        ])
        data["payroll_mtd_gross"] = sum(gross_lines.mapped("total"))

        first_contract = self._first_contract_dates(company)
        data["joiners_count"] = sum(
            1 for start in first_contract.values() if date_from <= start <= date_to
        )

        data["leavers_count"] = self.env["bpro.exit.request"].search_count([
            ("company_id", "=", company.id),
            ("state", "=", "closed"),
            ("last_working_day", ">=", date_from),
            ("last_working_day", "<=", date_to),
        ])

        # A leave crossing the range edge counts only its share of days
        # inside the range (pro rata by calendar days).
        leaves = self.env["hr.leave"].search([
            ("employee_id.company_id", "=", company.id),
            ("state", "=", "validate"),
            ("request_date_from", "<=", date_to),
            ("request_date_to", ">=", date_from),
        ])
        leave_days = 0.0
        for leave in leaves:
            start = leave.request_date_from
            end = leave.request_date_to or start
            span = (end - start).days + 1
            inside = dr.overlap_days(start, end, date_from, date_to)
            leave_days += leave.number_of_days * inside / span if span > 0 else 0.0
        data["leave_days_taken"] = leave_days

        attendance_domain = [
            ("employee_id.company_id", "=", company.id),
            ("check_in", ">=", utc_start),
            ("check_in", "<", utc_stop),
        ]
        if self.env["hr.attendance"].has_access("read"):
            attendances = self.env["hr.attendance"].search(attendance_domain)
        else:
            attendances = self.env["hr.attendance"]
            hidden += ["Hours Worked", "Approved Overtime"]
        data["attendance_worked_hours"] = sum(attendances.mapped("worked_hours"))
        data["overtime_approved_hours"] = sum(
            attendances.filtered(lambda a: a.overtime_status == "approved")
            .mapped("validated_overtime_hours")
        )

        data["attendance_exceptions_raised"] = self.env[
            "bpro.attendance.exception"
        ].search_count([
            ("employee_id.company_id", "=", company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ])

        # ---------------- stocks, as of To ----------------
        headcount = self._headcount_as_of(company, date_to, first_contract)
        data["headcount"] = headcount

        data["payroll_pending_confirmation"] = self.env["hr.payslip"].search_count([
            ("company_id", "=", company.id),
            ("state", "in", ("draft", "verify")),
            ("date_from", "<=", date_to),
        ])

        approved_requests = self.env["bpro.vacancy.request"].search([
            ("company_id", "=", company.id), ("state", "=", "approved"),
            "|", ("approved_date", "=", False), ("approved_date", "<=", date_to),
        ])
        data["recruitment_open_vacancies"] = len(
            approved_requests.filtered(
                lambda r: r.job_id.no_of_hired_employee < r.job_id.no_of_recruitment
            )
        )

        data["recruitment_overdue_joining_reports"] = self.env[
            "bpro.joining.report"
        ].search_count([
            ("employee_id.company_id", "=", company.id),
            ("state", "=", "pending"),
            ("sla_deadline", "<", date_to),
        ])

        data["attendance_pending_exceptions"] = self.env[
            "bpro.attendance.exception"
        ].search_count([
            ("employee_id.company_id", "=", company.id), ("state", "=", "pending"),
            ("date", "<=", date_to),
        ])

        data["exit_open_requests"] = self.env["bpro.exit.request"].search_count([
            ("company_id", "=", company.id),
            ("state", "in", ("submitted", "accepted", "settled")),
            ("resignation_date", "<=", date_to),
        ])

        # Trailing 12 months ending To - a fixed-window rate, deliberately
        # not the From..To range (a 1-day range would make it meaningless).
        exits_12m = self.env["bpro.exit.request"].search_count([
            ("company_id", "=", company.id),
            ("state", "=", "closed"),
            ("last_working_day", ">", date_to - timedelta(days=365)),
            ("last_working_day", "<=", date_to),
        ])
        data["attrition_rate_pct"] = (
            exits_12m / headcount * 100.0 if headcount else 0.0
        )

        # EL balance as of To: allocations starting and leave taken on or
        # before To. Rate uses the current open contract (as bpro_exit's
        # F&F does on the settlement day).
        el_liability = 0.0
        el_type = self.env.ref("bpro_leave.leave_type_earned", raise_if_not_found=False)
        if el_type and can_read_contracts:
            allocations = self.env["hr.leave.allocation"].search([
                ("employee_id.company_id", "=", company.id),
                ("holiday_status_id", "=", el_type.id),
                ("state", "=", "validate"),
                ("date_from", "<=", date_to),
            ])
            taken = self.env["hr.leave"].search([
                ("employee_id.company_id", "=", company.id),
                ("holiday_status_id", "=", el_type.id),
                ("state", "=", "validate"),
                ("request_date_from", "<=", date_to),
            ])
            balance_by_employee = {}
            for allocation in allocations:
                balance_by_employee[allocation.employee_id] = (
                    balance_by_employee.get(allocation.employee_id, 0.0)
                    + allocation.number_of_days
                )
            for leave in taken:
                balance_by_employee[leave.employee_id] = (
                    balance_by_employee.get(leave.employee_id, 0.0)
                    - leave.number_of_days
                )
            for employee, balance in balance_by_employee.items():
                if balance <= 0:
                    continue
                contract = self.env["hr.contract"].search(
                    [("employee_id", "=", employee.id), ("state", "=", "open")],
                    limit=1,
                )
                if contract:
                    monthly_basic = (
                        contract.ctc_annual / 12.0 * (contract.basic_percent / 100.0)
                    )
                    el_liability += balance * monthly_basic / 26.0
        data["el_liability"] = el_liability

        data["access_note"] = (
            "Not visible with your access: %s" % ", ".join(hidden) if hidden else False
        )
        return data
