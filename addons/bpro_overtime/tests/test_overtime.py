from datetime import date, datetime, time, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestOvertime(TransactionCase):
    """R6.5 - approved OT reaches the payslip at the double rate, or
    converts to comp-off, never both."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.struct = cls.env.ref("bpro_payroll.structure_india_ctc")
        cls.employee = cls.env["hr.employee"].create({
            "name": "OT Test Employee", "company_id": cls.company.id,
            "tz": "Asia/Kolkata",
        })
        cls.contract = cls.env["hr.contract"].create({
            "name": "OT contract", "employee_id": cls.employee.id,
            "wage": 20000, "ctc_annual": 240000.0,
            "basic_percent": 50.0, "hra_percent": 40.0,
            "struct_id": cls.struct.id, "date_start": date(2026, 1, 1),
            "state": "open",
        })

    def _add_ot(self, day, hours, status="approved"):
        attendance = self.env["hr.attendance"].create({
            "employee_id": self.employee.id,
            "check_in": datetime.combine(day, time(3, 30)),
            "check_out": datetime.combine(day, time(12, 30) if hours == 0 else time(12 + int(hours), 30)),
        })
        attendance.write({
            "overtime_status": status,
            "validated_overtime_hours": hours,
        })
        return attendance

    def _payslip_lines(self):
        payslip = self.env["hr.payslip"].create({
            "employee_id": self.employee.id, "contract_id": self.contract.id,
            "struct_id": self.struct.id,
            "date_from": date(2026, 8, 1), "date_to": date(2026, 8, 31),
            "name": "OT slip",
        })
        payslip.compute_sheet()
        return {line.code: line.total for line in payslip.line_ids}

    def test_ot_paid_at_double_rate_and_reaches_net(self):
        self.company.ot_compensation = "pay"
        self.company.ot_multiplier = 2.0
        self._add_ot(date(2026, 8, 3), 4.0)
        self._add_ot(date(2026, 8, 4), 2.0)
        self._add_ot(date(2026, 8, 5), 3.0, status="refused")  # never paid
        lines = self._payslip_lines()
        # Gross 14000 -> hourly 14000/208; 6 approved hours x 2.
        expected = 6.0 * (14000.0 / 208.0) * 2.0
        self.assertAlmostEqual(lines["OT"], expected, places=2)
        self.assertAlmostEqual(
            lines["NET"],
            lines["GROSS"] + expected - (lines["PF_EE"] + lines["ESI_EE"]),
            places=2,
        )

    def test_no_ot_line_in_compoff_mode(self):
        self.company.ot_compensation = "compoff"
        self._add_ot(date(2026, 8, 3), 4.0)
        lines = self._payslip_lines()
        self.assertFalse(lines.get("OT"))

    def test_compoff_conversion_credits_and_never_doubles(self):
        self.company.ot_compensation = "compoff"
        self._add_ot(date(2026, 8, 3), 8.0)
        self._add_ot(date(2026, 8, 4), 4.0)
        wizard = self.env["bpro.compoff.wizard"].create({
            "date_from": date(2026, 8, 1), "date_to": date(2026, 8, 31),
        })
        wizard.action_convert()
        compoff_type = self.env.ref("bpro_overtime.leave_type_compoff")
        allocations = self.env["hr.leave.allocation"].search([
            ("employee_id", "=", self.employee.id),
            ("holiday_status_id", "=", compoff_type.id),
        ])
        # 12 hours -> 1.5 days.
        self.assertAlmostEqual(sum(allocations.mapped("number_of_days")), 1.5)
        # Re-run: nothing new.
        wizard2 = self.env["bpro.compoff.wizard"].create({
            "date_from": date(2026, 8, 1), "date_to": date(2026, 8, 31),
        })
        wizard2.action_convert()
        allocations = self.env["hr.leave.allocation"].search([
            ("employee_id", "=", self.employee.id),
            ("holiday_status_id", "=", compoff_type.id),
        ])
        self.assertAlmostEqual(sum(allocations.mapped("number_of_days")), 1.5)

    def test_conversion_refused_in_pay_mode(self):
        self.company.ot_compensation = "pay"
        wizard = self.env["bpro.compoff.wizard"].create({
            "date_from": date(2026, 8, 1), "date_to": date(2026, 8, 31),
        })
        with self.assertRaises(UserError):
            wizard.action_convert()

    def test_daily_wage_ot_uses_daily_rate_not_ctc(self):
        """A Daily Wage employee's OT hourly rate is daily_wage_rate / 8,
        not derived from ctc_annual (which is undefined/zero for this
        category - previously computed to zero silently)."""
        self.company.ot_compensation = "pay"
        self.company.ot_multiplier = 2.0
        dw_employee = self.env["hr.employee"].create({
            "name": "Daily Wage OT Employee",
            "company_id": self.company.id,
            "tz": "Asia/Kolkata",
        })
        dw_contract = self.env["hr.contract"].create({
            "name": "Daily Wage OT contract",
            "employee_id": dw_employee.id,
            "wage": 500,
            "employment_category": "daily_wage",
            "daily_wage_rate": 600.0,
            "struct_id": self.struct.id,
            "date_start": date(2026, 1, 1),
            "state": "open",
        })
        att = self.env["hr.attendance"].create({
            "employee_id": dw_employee.id,
            "check_in": datetime.combine(date(2026, 8, 3), time(3, 30)),
            "check_out": datetime.combine(date(2026, 8, 3), time(16, 30)),
        })
        att.write({"overtime_status": "approved", "validated_overtime_hours": 4.0})

        payslip = self.env["hr.payslip"].create({
            "employee_id": dw_employee.id, "contract_id": dw_contract.id,
            "struct_id": self.struct.id,
            "date_from": date(2026, 8, 1), "date_to": date(2026, 8, 31),
            "name": "Daily Wage OT slip",
        })
        payslip.compute_sheet()
        lines = {line.code: line.total for line in payslip.line_ids}
        # Hourly rate = 600 / 8 = 75; 4 hours x 2.0 multiplier = 600
        expected = 4.0 * (600.0 / 8.0) * 2.0
        self.assertAlmostEqual(lines.get("OT", 0.0), expected, places=2)
