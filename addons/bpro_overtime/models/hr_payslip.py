from datetime import datetime, time

from pytz import timezone as pytz_timezone, UTC

from odoo import models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def bpro_ot_hours(self, employee):
        """Approved overtime hours in this payslip's period. Same
        real-method-not-rule-code shape as bpro_lop_factor, and the
        same employee-tz boundary handling as R5.1's exception
        detection - naive datetimes are UTC to the ORM, so the local
        period edges must be converted or hours near month-end land in
        the wrong month."""
        self.ensure_one()
        tz = pytz_timezone(employee.tz or "Asia/Kolkata")
        start = tz.localize(datetime.combine(self.date_from, time.min)).astimezone(UTC).replace(tzinfo=None)
        end = tz.localize(datetime.combine(self.date_to, time.max)).astimezone(UTC).replace(tzinfo=None)
        attendances = self.env["hr.attendance"].sudo().search([
            ("employee_id", "=", employee.id),
            ("overtime_status", "=", "approved"),
            ("check_in", ">=", start),
            ("check_in", "<=", end),
        ])
        return sum(attendances.mapped("validated_overtime_hours"))

    def bpro_ot_amount(self, employee, contract):
        """OT pay: approved hours x hourly ordinary rate x company
        multiplier.

        For CTC-based contracts (Permanent, FTC, Trainee): ordinary rate
        = UNPRORATED contracted monthly gross / (26 x 8) - the statutory
        divisor convention; an employee's ordinary rate doesn't shrink
        because they were absent on other days of the month.

        For Daily Wage contracts: ordinary rate = daily_wage_rate / 8,
        the per-hour equivalent of the agreed per-day rate (Factories Act
        overtime doubles this, or applies whatever ot_multiplier is set).
        ctc_annual is undefined for this category, so the CTC path would
        compute zero - using daily_wage_rate is the correct statutory base.
        """
        self.ensure_one()
        if contract.company_id.ot_compensation != "pay":
            return 0.0
        hours = self.bpro_ot_hours(employee)
        if not hours:
            return 0.0
        if getattr(contract, "employment_category", None) == "daily_wage":
            if not contract.daily_wage_rate:
                return 0.0
            hourly = contract.daily_wage_rate / 8.0
        else:
            monthly_basic = contract.ctc_annual / 12.0 * (contract.basic_percent / 100.0)
            monthly_gross = monthly_basic * (1 + contract.hra_percent / 100.0)
            hourly = monthly_gross / (26.0 * 8.0)
        return hours * hourly * (contract.company_id.ot_multiplier or 2.0)
