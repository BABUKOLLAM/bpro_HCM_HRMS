from datetime import date, datetime, time

from .common import PayrollTestCommon


class TestEsi(PayrollTestCommon):
    """ESI is a pure threshold test on GROSS (not Basic, unlike PF) -
    either wages are at or below the company's esi_wage_threshold and
    ESI applies in full, or they aren't and it's zero. No capping/basis
    choice the way PF has. PF and TDS are switched off on every contract
    here to isolate ESI."""

    def _esi_contract(self, ctc_annual, **kwargs):
        kwargs.setdefault("pf_applicable", False)
        kwargs.setdefault("tds_regime", False)
        return self._make_contract(ctc_annual, **kwargs)

    def test_esi_applies_when_gross_is_at_or_below_threshold(self):
        # ctc_annual=200000 -> monthly 16666.67, Basic 8333.33 (50%),
        # HRA 3333.33 (40% of Basic), Gross 11666.67 - comfortably under
        # the default 21000 threshold.
        contract = self._esi_contract(200000.0)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        gross = self._line_amount(payslip, "GROSS")
        self.assertLess(gross, 21000.0)
        self.assertAlmostEqual(
            self._line_amount(payslip, "ESI_EE"), gross * 0.0075, places=2
        )
        self.assertAlmostEqual(
            self._line_amount(payslip, "ESI_ER"), gross * 0.0325, places=2
        )

    def test_esi_does_not_apply_when_gross_exceeds_threshold(self):
        # ctc_annual=600000 -> Gross 35000, above the 21000 threshold.
        contract = self._esi_contract(600000.0)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertGreater(self._line_amount(payslip, "GROSS"), 21000.0)
        self.assertEqual(self._line_amount(payslip, "ESI_EE"), 0.0)
        self.assertEqual(self._line_amount(payslip, "ESI_ER"), 0.0)

    def test_esi_applicable_false_overrides_a_below_threshold_gross(self):
        # Even though this contract's Gross would otherwise qualify,
        # esi_applicable=False must still zero it out - an HR-set
        # exclusion, not just a wage check.
        contract = self._esi_contract(200000.0, esi_applicable=False)
        payslip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertLess(self._line_amount(payslip, "GROSS"), 21000.0)
        self.assertEqual(self._line_amount(payslip, "ESI_EE"), 0.0)
        self.assertEqual(self._line_amount(payslip, "ESI_ER"), 0.0)

    def test_esi_base_includes_ot_wages(self):
        """ESI contribution base must include overtime pay — OT is only
        excluded from the initial *eligibility* test, not from the
        contribution *base* (Employees' State Insurance Act, s.2(22))."""
        contract = self._esi_contract(200000.0)
        employee = self.env["hr.employee"].browse(contract.employee_id.id)
        employee.write({"tz": "Asia/Kolkata"})
        # Add 4 approved OT hours in the payslip period
        attendance = self.env["hr.attendance"].create({
            "employee_id": employee.id,
            "check_in": datetime.combine(date(2026, 5, 2), time(3, 30)),
            "check_out": datetime.combine(date(2026, 5, 2), time(16, 30)),
        })
        attendance.write({
            "overtime_status": "approved",
            "validated_overtime_hours": 4.0,
        })
        self.company.ot_compensation = "pay"
        self.company.ot_multiplier = 2.0
        payslip = self._make_payslip(contract, "2026-05-01", "2026-05-31")
        gross = self._line_amount(payslip, "GROSS")
        ot = self._line_amount(payslip, "OT")
        self.assertGreater(ot, 0.0)
        self.assertAlmostEqual(
            self._line_amount(payslip, "ESI_EE"),
            (gross + ot) * 0.0075,
            places=2,
        )
        self.assertAlmostEqual(
            self._line_amount(payslip, "ESI_ER"),
            (gross + ot) * 0.0325,
            places=2,
        )

    def test_esi_period_continuity_covered_employee_stays_covered(self):
        """An employee covered at the start of April stays covered for the
        whole April-September period, even if a raise in June pushes their
        gross above the threshold that month."""
        contract = self._esi_contract(200000.0)
        # April payslip: gross under threshold, confirmed -> sets the anchor
        april_slip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        self.assertGreater(self._line_amount(april_slip, "ESI_EE"), 0.0)
        april_slip.action_payslip_done()

        # Raise the CTC so June gross exceeds the threshold
        contract.write({"ctc_annual": 600000.0})
        june_slip = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        gross_june = self._line_amount(june_slip, "GROSS")
        self.assertGreater(gross_june, 21000.0, "Gross must exceed threshold to test continuity")
        # ESI must still apply because the April anchor payslip had it
        self.assertGreater(
            self._line_amount(june_slip, "ESI_EE"), 0.0,
            "ESI should remain active mid-period even though gross now exceeds threshold"
        )

    def test_esi_period_continuity_not_covered_stays_out(self):
        """An employee whose gross exceeds the threshold in April (start
        of the H1 period) must NOT be covered in May even if a pay cut
        brings their gross back below the threshold."""
        contract = self._esi_contract(600000.0)
        # April: gross above threshold -> not covered
        april_slip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        self.assertEqual(self._line_amount(april_slip, "ESI_EE"), 0.0)
        april_slip.action_payslip_done()

        # Drop CTC so May gross is below threshold
        contract.write({"ctc_annual": 200000.0})
        may_slip = self._make_payslip(contract, "2026-05-01", "2026-05-31")
        gross_may = self._line_amount(may_slip, "GROSS")
        self.assertLess(gross_may, 21000.0)
        # ESI must still be zero: the April anchor payslip had no ESI
        self.assertEqual(
            self._line_amount(may_slip, "ESI_EE"), 0.0,
            "ESI must stay zero mid-period if the anchor month had none"
        )

    def test_esi_period_resets_at_october(self):
        """October is the start of a new contribution period: coverage is
        re-determined from the current gross regardless of what April-
        September showed."""
        contract = self._esi_contract(200000.0)
        # April covered
        april_slip = self._make_payslip(contract, "2026-04-01", "2026-04-30")
        april_slip.action_payslip_done()
        # Raise CTC; October is a new period start — plain threshold test applies
        contract.write({"ctc_annual": 600000.0})
        oct_slip = self._make_payslip(contract, "2026-10-01", "2026-10-31")
        gross_oct = self._line_amount(oct_slip, "GROSS")
        self.assertGreater(gross_oct, 21000.0)
        self.assertEqual(
            self._line_amount(oct_slip, "ESI_EE"), 0.0,
            "New period: high gross at October start must zero ESI"
        )

    def test_esi_re_checks_the_threshold_every_payslip(self):
        # Same contract, two different CTCs across two months - confirms
        # the rule reacts to whatever Gross actually is that month, not a
        # value cached from an earlier payslip.
        contract = self._esi_contract(200000.0)
        below = self._make_payslip(contract, "2026-06-01", "2026-06-30")
        self.assertGreater(self._line_amount(below, "ESI_EE"), 0.0)

        contract.write({"ctc_annual": 600000.0})
        above = self._make_payslip(contract, "2026-07-01", "2026-07-31")
        self.assertEqual(self._line_amount(above, "ESI_EE"), 0.0)
