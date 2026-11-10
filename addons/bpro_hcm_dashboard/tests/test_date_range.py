from datetime import date, datetime

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.bpro_hcm_dashboard.models import date_range as dr
from odoo.addons.bpro_hcm_dashboard.models.bpro_hcm_dashboard import (
    FLOW_KPIS,
    STOCK_KPIS,
)

# Tuesday. Every expectation below is hand-computed from this date.
TODAY = date(2026, 11, 10)


@tagged("post_install", "-at_install")
class TestDateRangeMaths(TransactionCase):
    """The pure period rules - no records involved."""

    def test_presets_inclusive_and_to_date(self):
        expected = {
            "today": (date(2026, 11, 10), date(2026, 11, 10)),
            "this_week": (date(2026, 11, 9), date(2026, 11, 10)),  # Monday start
            "month_to_date": (date(2026, 11, 1), date(2026, 11, 10)),
            "last_month": (date(2026, 10, 1), date(2026, 10, 31)),
            "last_30_days": (date(2026, 10, 12), date(2026, 11, 10)),
            "this_quarter": (date(2026, 10, 1), date(2026, 11, 10)),
            "fy_to_date": (date(2026, 4, 1), date(2026, 11, 10)),
        }
        for preset, rng in expected.items():
            with self.subTest(preset=preset):
                self.assertEqual(dr.preset_range(preset, TODAY), rng)
        start, end = dr.preset_range("last_30_days", TODAY)
        self.assertEqual((end - start).days + 1, 30)

    def test_year_and_fy_edges(self):
        self.assertEqual(
            dr.preset_range("last_month", date(2026, 1, 15)),
            (date(2025, 12, 1), date(2025, 12, 31)),
        )
        self.assertEqual(
            dr.preset_range("last_month", date(2028, 3, 5)),
            (date(2028, 2, 1), date(2028, 2, 29)),  # leap year
        )
        self.assertEqual(dr.fy_start(date(2026, 3, 31)), date(2025, 4, 1))
        self.assertEqual(dr.fy_start(date(2026, 4, 1)), date(2026, 4, 1))
        self.assertEqual(dr.quarter_start(date(2026, 2, 14)), date(2026, 1, 1))
        self.assertEqual(dr.quarter_start(date(2026, 4, 1)), date(2026, 4, 1))

    def test_custom_fiscal_year(self):
        july_june = (6, 30)
        self.assertEqual(
            dr.preset_range("fy_to_date", TODAY, july_june),
            (date(2026, 7, 1), TODAY),
        )
        self.assertEqual(
            dr.preset_range("this_quarter", TODAY, july_june),
            (date(2026, 10, 1), TODAY),
        )
        self.assertEqual(dr.fy_start(date(2026, 6, 30), july_june), date(2025, 7, 1))

    def test_company_fiscal_year_setting(self):
        company = self.env["res.company"].create({"name": "FY Test Co"})
        if "fiscalyear_last_month" not in company._fields:
            self.assertEqual(dr.company_fy_end(company), dr.INDIAN_FY_END)
            return
        company.write({"fiscalyear_last_month": "12", "fiscalyear_last_day": 31})
        self.assertEqual(dr.company_fy_end(company), (3, 31))  # untouched default
        company.write({"fiscalyear_last_month": "6", "fiscalyear_last_day": 30})
        self.assertEqual(dr.company_fy_end(company), (6, 30))

    def test_timezone_today_and_bounds(self):
        # 20:00 UTC on 9 Nov is already 01:30 on 10 Nov in India.
        late_utc = datetime(2026, 11, 9, 20, 0)
        self.assertEqual(dr.local_today("Asia/Kolkata", late_utc), date(2026, 11, 10))
        self.assertEqual(dr.local_today(None, late_utc), date(2026, 11, 10))
        self.assertEqual(dr.local_today("UTC", late_utc), date(2026, 11, 9))
        self.assertEqual(dr.local_today("Not/AZone", late_utc), date(2026, 11, 10))
        start, stop = dr.utc_bounds(TODAY, TODAY, "Asia/Kolkata")
        self.assertEqual(start, datetime(2026, 11, 9, 18, 30))
        self.assertEqual(stop, datetime(2026, 11, 10, 18, 30))

    def test_overlap_days(self):
        rng = (date(2026, 11, 1), date(2026, 11, 10))
        self.assertEqual(dr.overlap_days(date(2026, 10, 30), date(2026, 11, 2), *rng), 2)
        self.assertEqual(dr.overlap_days(date(2026, 11, 10), date(2026, 11, 10), *rng), 1)
        self.assertEqual(dr.overlap_days(date(2026, 10, 1), date(2026, 10, 31), *rng), 0)


@tagged("post_install", "-at_install")
class TestDashboardRange(TransactionCase):
    """The form behaviour and one KPI of each kind (flow / stock)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Range Test Co"})
        cls.Dash = cls.env["bpro.hcm.dashboard"].with_context(tz="Asia/Kolkata")

    def _employee(self, name, **vals):
        return self.env["hr.employee"].create(
            dict({"name": name, "company_id": self.company.id}, **vals)
        )

    def _contract(self, employee, start, state="open"):
        return self.env["hr.contract"].create({
            "name": "Range contract %s" % employee.name,
            "employee_id": employee.id, "company_id": self.company.id,
            "wage": 20000, "ctc_annual": 240000.0,
            "basic_percent": 50.0, "hra_percent": 40.0,
            "date_start": start, "state": state,
        })

    def _kpi(self, date_from, date_to):
        return self.Dash._get_kpi_data(self.company, date_to, date_from)

    # ---------------- form behaviour ----------------
    def test_every_kpi_is_classified(self):
        data = self._kpi(date(2026, 11, 1), TODAY)
        self.assertEqual(set(FLOW_KPIS) | set(STOCK_KPIS) | {"access_note"}, set(data))
        self.assertFalse(set(FLOW_KPIS) & set(STOCK_KPIS))

    def test_defaults_and_as_of_compatibility(self):
        dash = self.Dash.create({})
        self.assertEqual(dash.period_preset, "month_to_date")
        self.assertEqual(dash.date_from, dash.as_of_date.replace(day=1))
        # Old callers that only pass "As of" get month-to-date, as before.
        old = self.Dash.with_context(default_as_of_date="2026-10-20").create({})
        self.assertEqual((old.date_from, old.as_of_date), (date(2026, 10, 1), date(2026, 10, 20)))
        self.assertEqual(
            self.Dash._get_kpi_data(self.company, TODAY),
            self._kpi(date(2026, 11, 1), TODAY),
        )

    def test_preset_onchange_and_hand_edit_goes_custom(self):
        dash = self.Dash.new({"period_preset": "month_to_date"})
        dash.period_preset = "last_month"
        dash._onchange_period_preset()
        expected = self.Dash._preset_dates("last_month")
        self.assertEqual((dash.date_from, dash.as_of_date), expected)
        dash._onchange_dates_to_custom()  # re-entry from the preset write
        self.assertEqual(dash.period_preset, "last_month")
        dash.date_from = expected[0].replace(day=5)
        dash._onchange_dates_to_custom()
        self.assertEqual(dash.period_preset, "custom")

    def test_from_after_to_rejected(self):
        with self.assertRaises(ValidationError):
            self.Dash.create({
                "period_preset": "custom",
                "date_from": date(2026, 11, 10), "as_of_date": date(2026, 11, 1),
            })

    # ---------------- flow KPIs follow From..To ----------------
    def test_flow_attendance_hours_use_local_day_edges(self):
        employee = self._employee("Range Attendance Employee")
        # 1 Nov 00:30 IST (31 Oct 19:00 UTC) - a November attendance.
        self.env["hr.attendance"].create({
            "employee_id": employee.id,
            "check_in": datetime(2026, 10, 31, 19, 0),
            "check_out": datetime(2026, 10, 31, 23, 0),
        })
        self.assertAlmostEqual(
            self._kpi(date(2026, 11, 1), date(2026, 11, 30))["attendance_worked_hours"], 4.0, places=2
        )
        self.assertEqual(
            self._kpi(date(2026, 10, 1), date(2026, 10, 31))["attendance_worked_hours"], 0.0
        )

    def test_flow_joiners_leavers_and_exceptions(self):
        joiner = self._employee("Range Joiner")
        self._contract(joiner, date(2026, 11, 3))
        veteran = self._employee("Range Veteran")
        self._contract(veteran, date(2020, 1, 1))
        leaver = self._employee("Range Leaver")
        self._contract(leaver, date(2021, 1, 1))
        exit_request = self.env["bpro.exit.request"].create({
            "employee_id": leaver.id, "resignation_date": date(2026, 10, 1),
        })
        exit_request.write({"state": "closed", "last_working_day": date(2026, 10, 31)})
        Exception_ = self.env["bpro.attendance.exception"]
        Exception_.create({"employee_id": veteran.id, "date": date(2026, 11, 2)})
        Exception_.create({"employee_id": veteran.id, "date": date(2026, 10, 30)})

        nov = self._kpi(date(2026, 11, 1), date(2026, 11, 10))
        self.assertEqual(nov["joiners_count"], 1)
        self.assertEqual(nov["leavers_count"], 0)
        self.assertEqual(nov["attendance_exceptions_raised"], 1)

        last_30 = self._kpi(date(2026, 10, 12), date(2026, 11, 10))
        self.assertEqual(last_30["joiners_count"], 1)
        self.assertEqual(last_30["leavers_count"], 1)  # 31 Oct, inclusive end
        self.assertEqual(last_30["attendance_exceptions_raised"], 2)

        oct_only = self._kpi(date(2026, 10, 31), date(2026, 10, 31))
        self.assertEqual(oct_only["leavers_count"], 1)  # From == To, inclusive

    def test_flow_leave_days_prorated_at_range_edge(self):
        employee = self._employee("Range Leave Employee")
        leave_type = self.env["hr.leave.type"].create({
            "name": "Range Test Leave", "requires_allocation": "no",
        })
        leave = self.env["hr.leave"].create({
            "employee_id": employee.id, "holiday_status_id": leave_type.id,
            "request_date_from": date(2026, 10, 29),  # Thu
            "request_date_to": date(2026, 11, 3),    # Tue: 6 calendar days
        })
        leave.action_approve()
        self.assertEqual(leave.state, "validate")
        nov = self._kpi(date(2026, 11, 1), date(2026, 11, 30))["leave_days_taken"]
        octo = self._kpi(date(2026, 10, 1), date(2026, 10, 31))["leave_days_taken"]
        self.assertAlmostEqual(nov, leave.number_of_days * 3 / 6, places=4)
        self.assertAlmostEqual(nov + octo, leave.number_of_days, places=4)

    # ---------------- stock KPIs are as of To ----------------
    def test_stock_headcount_is_as_of_to_not_range(self):
        current = self._employee("Range Current")
        self._contract(current, date(2025, 1, 1))
        self._employee("Range No Contract")  # joining unknown: counted
        future = self._employee("Range Future Joiner")
        self._contract(future, date(2026, 12, 1), state="draft")
        gone = self._employee("Range Gone", departure_date=date(2026, 9, 30))
        self._contract(gone, date(2024, 1, 1), state="close")
        gone.active = False
        late = self._employee("Range Left In Nov", departure_date=date(2026, 11, 20))
        self._contract(late, date(2024, 1, 1), state="close")
        late.active = False

        nov = self._kpi(date(2026, 11, 1), date(2026, 11, 10))
        # current + no-contract + left-on-20-Nov; not the Dec joiner,
        # not the September leaver.
        self.assertEqual(nov["headcount"], 3)
        # Widening From doesn't change a stock - only To matters.
        self.assertEqual(self._kpi(date(2026, 4, 1), date(2026, 11, 10))["headcount"], 3)
        self.assertEqual(self._kpi(date(2026, 9, 1), date(2026, 9, 29))["headcount"], 4)

    def test_stock_pending_payslips_as_of_to(self):
        struct = self.env.ref("bpro_payroll.structure_india_ctc")
        employee = self._employee("Range Payslip Employee")
        contract = self._contract(employee, date(2026, 1, 1))
        contract.struct_id = struct
        for start, end in ((date(2026, 10, 1), date(2026, 10, 31)),
                           (date(2026, 11, 1), date(2026, 11, 30))):
            self.env["hr.payslip"].create({
                "employee_id": employee.id, "contract_id": contract.id,
                "struct_id": struct.id, "company_id": self.company.id,
                "date_from": start, "date_to": end, "name": "Range slip %s" % start,
            })
        self.assertEqual(self._kpi(date(2026, 10, 1), date(2026, 10, 31))["payroll_pending_confirmation"], 1)
        self.assertEqual(self._kpi(date(2026, 11, 10), date(2026, 11, 10))["payroll_pending_confirmation"], 2)
