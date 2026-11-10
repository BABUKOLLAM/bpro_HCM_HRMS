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
        string="Gross Payout (payslips for periods starting in the range)",
        compute="_compute_kpis",
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
        warning = None
        for rec in self:
            if not (rec.date_from and rec.as_of_date):
                continue
            if rec.date_from > rec.as_of_date:
                warning = {
                    "title": "Check the period",
                    "message": "'From' must be on or before 'To'.",
                }
            if rec.period_preset == "custom":
                continue
            if (rec.date_from, rec.as_of_date) != rec._preset_dates(rec.period_preset):
                rec.period_preset = "custom"
        if warning:
            return {"warning": warning}

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
    def _can(self, group_xmlid, *models_):
        """True when this user may see the whole company's records of a
        KPI: in the officer/user group AND with read access on every
        model it touches. Group, not just model access, because e.g.
        ESS grants every employee read on their OWN payslips/attendance
        - a figure built on that would silently be own-records-only."""
        if not self.env.su and group_xmlid and not self.env.user.has_group(group_xmlid):
            return False
        return all(self.env[m].has_access("read") for m in models_)

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
        rows = self.env["hr.employee"].with_context(active_test=False).search_read(
            [
                ("company_id", "=", company.id),
                "|", ("active", "=", True), ("departure_date", "!=", False),
                "|", ("departure_date", "=", False), ("departure_date", ">", as_of_date),
            ],
            ["id"],
        )
        return sum(
            1 for row in rows
            if not (first_contract.get(row["id"]) and first_contract[row["id"]] > as_of_date)
        )

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
        can_payroll = self._can("payroll.group_payroll_user", "hr.payslip", "hr.payslip.line")
        can_contracts = self._can(None, "hr.contract")
        can_leave = self._can(
            "hr_holidays.group_hr_holidays_user", "hr.leave", "hr.leave.allocation"
        )
        # Attendance *Administrator*, not Officer: in Odoo 18 an Officer's
        # record rule only shows employees they are attendance manager of,
        # which would make the company total silently team-only.
        can_attendance = self._can("hr_attendance.group_hr_attendance_manager", "hr.attendance")
        if not can_payroll:
            hidden.append("Payroll")
        if not can_contracts:
            hidden += ["Joiners", "Headcount (joining dates unavailable - counted from the current roster)"]
        if not can_leave:
            hidden.append("Leave Days Taken")
        if not can_attendance:
            hidden += ["Hours Worked", "Approved Overtime"]
        if not (can_contracts and can_leave):
            hidden.append("EL Liability")

        # ---------------- flows ----------------
        data["payroll_mtd_gross"] = 0.0
        if can_payroll:
            gross = self.env["hr.payslip.line"]._read_group([
                ("slip_id.company_id", "=", company.id),
                ("slip_id.state", "=", "done"),
                ("slip_id.date_from", ">=", date_from),
                ("slip_id.date_from", "<=", date_to),
                ("code", "=", "GROSS"),
            ], [], ["total:sum"])
            data["payroll_mtd_gross"] = gross[0][0] or 0.0

        first_contract = self._first_contract_dates(company) if can_contracts else {}
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
        leave_days = 0.0
        if can_leave:
            leaves = self.env["hr.leave"].search_read([
                ("employee_id.company_id", "=", company.id),
                ("state", "=", "validate"),
                ("request_date_from", "<=", date_to),
                ("request_date_to", ">=", date_from),
            ], ["request_date_from", "request_date_to", "number_of_days"])
            for leave in leaves:
                start = leave["request_date_from"]
                end = leave["request_date_to"] or start
                span = (end - start).days + 1
                inside = dr.overlap_days(start, end, date_from, date_to)
                leave_days += leave["number_of_days"] * inside / span if span > 0 else 0.0
        data["leave_days_taken"] = leave_days

        attendance_domain = [
            ("employee_id.company_id", "=", company.id),
            ("check_in", ">=", utc_start),
            ("check_in", "<", utc_stop),
        ]
        data["attendance_worked_hours"] = 0.0
        data["overtime_approved_hours"] = 0.0
        if can_attendance:
            Attendance = self.env["hr.attendance"]
            data["attendance_worked_hours"] = (
                Attendance._read_group(attendance_domain, [], ["worked_hours:sum"])[0][0] or 0.0
            )
            data["overtime_approved_hours"] = Attendance._read_group(
                attendance_domain + [
                    ("overtime_status", "=", "approved"),
                    ("validated_overtime_hours", ">", 0),  # undertime is not overtime
                ],
                [], ["validated_overtime_hours:sum"],
            )[0][0] or 0.0

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
        ]) if can_payroll else 0

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
        if el_type and can_contracts and can_leave:
            balance = {}
            for employee, days in self.env["hr.leave.allocation"]._read_group([
                ("employee_id.company_id", "=", company.id),
                ("holiday_status_id", "=", el_type.id),
                ("state", "=", "validate"),
                ("date_from", "<=", date_to),
            ], ["employee_id"], ["number_of_days:sum"]):
                balance[employee.id] = balance.get(employee.id, 0.0) + (days or 0.0)
            for employee, days in self.env["hr.leave"]._read_group([
                ("employee_id.company_id", "=", company.id),
                ("holiday_status_id", "=", el_type.id),
                ("state", "=", "validate"),
                ("request_date_from", "<=", date_to),
            ], ["employee_id"], ["number_of_days:sum"]):
                balance[employee.id] = balance.get(employee.id, 0.0) - (days or 0.0)
            positive = [emp_id for emp_id, days in balance.items() if days > 0]
            # One query for all open contracts; first in hr.contract's
            # own order per employee, as the old per-employee search(limit=1).
            contract_by_employee = {}
            for contract in self.env["hr.contract"].search([
                ("employee_id", "in", positive), ("state", "=", "open"),
            ]):
                contract_by_employee.setdefault(contract.employee_id.id, contract)
            for emp_id in positive:
                contract = contract_by_employee.get(emp_id)
                if contract:
                    monthly_basic = (
                        contract.ctc_annual / 12.0 * (contract.basic_percent / 100.0)
                    )
                    el_liability += balance[emp_id] * monthly_basic / 26.0
        data["el_liability"] = el_liability

        data["access_note"] = (
            "Not visible with your access: %s" % ", ".join(hidden) if hidden else False
        )
        return data
