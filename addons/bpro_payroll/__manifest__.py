{
    "name": "bpro Payroll — India Salary Structure Foundation",
    "summary": "Flexible-benefit CTC salary structure + PF + ESI + Professional Tax + LWF + TDS + Form 16 on top of the OCA payroll engine (BES HR & Payroll module, R3.1-3.6c — full payroll build)",
    "description": """
India payroll build-out on the OCA payroll engine. This release (R3.6c)
completes the payroll track scoped 2026-08-11.

R3.1 - salary structure foundation:

* Adds `ctc_annual`, `basic_percent` and `hra_percent` to hr.contract - the
  inputs an India CTC breakup is built from. Defaults (Basic 50% of CTC,
  HRA 40% of Basic) are configurable company/contract policy, not statutory
  figures.
* Defines the flexible-benefit components (LTA, Meal Vouchers, Conveyance,
  Special Allowance) as hr.contract.advantage.template records, using the
  bounded advantage mechanism from payroll_contract_advantages - HR sets
  each employee's split within employer-defined lower/upper bounds.
* Defines the base salary rule categories (Basic, HRA, FBP, Gross,
  Deductions, Net) and the "India CTC Structure" salary structure with
  rules for Basic, HRA and each flexible-benefit component.

R3.2 - Provident Fund:

* Adds PF rate/ceiling fields to res.company (pf_wage_ceiling,
  pf_employee_rate, pf_employer_rate, pf_employer_eps_rate, pf_edli_rate,
  pf_admin_charge_rate) - seed defaults from EPFO's commonly published
  figures, verify against the current notification before go-live, and
  revisit whenever EPFO changes them. Nothing is hardcoded into rule logic.
* Adds pf_applicable and pf_calculation_basis (capped/full_basic) to
  hr.contract.
* Employee PF (PF_EE) is parented under DED, so it flows into
  NET = GROSS - DED automatically. Employer PF (split into EPS and EPF
  shares), EDLI and admin charges are computed for visibility/future
  compliance reporting but never reduce Net Salary - EPS/EDLI/admin are
  always computed on wages capped at the ceiling regardless of the
  contract's own calculation-basis setting, per EPFO rules.

R3.3 - ESI:

* Adds esi_wage_threshold, esi_employee_rate, esi_employer_rate to
  res.company - seed defaults are the rates in force since July 2019
  (0.75%/3.25%) and the commonly published ₹21,000 gross wage threshold,
  verify against the current ESIC notification before go-live.
* Adds esi_applicable to hr.contract.
* ESI is computed on GROSS wages (not Basic, unlike PF) and re-checks the
  threshold every payslip. It does NOT implement ESI's contribution-period
  continuity rule (coverage should persist for a full Apr-Sep/Oct-Mar
  period once started, even if a mid-period raise crosses the threshold) -
  that's a known, documented gap, not an oversight.
* ESI_EE parents to DED like PF_EE. ESI_ER parents to the same
  "Employer Statutory Contributions" category PF's employer lines use, so
  employer-borne PF + ESI costs roll up together.

R3.4 - Professional Tax (multi-state):

* New models bpro.pt.config (one per state: name, state_id, periodicity
  monthly/half_yearly, charge months for half-yearly states) and
  bpro.pt.slab.line (income bounds + amount, with an optional
  topup_month/topup_amount for states like Karnataka/Andhra Pradesh that
  charge a higher amount in one specific month so the annual total lands
  on the ₹2,500 constitutional cap). Seeded with Karnataka, Andhra
  Pradesh, Tamil Nadu (Chennai Corporation slabs) and Kerala (Panchayat
  slabs) - all researched 2026-08-11, all flagged for verification against
  the current state gazette before go-live. Kerala's actual rate varies by
  local body (Panchayat/Municipality/Corporation); the seeded Panchayat
  table is a default, not necessarily the client's.
* Adds pt_state_id to hr.contract - which state's PT config applies to
  that employee (their work location, not necessarily company's
  registered state).
* Single PT rule (100% employee-borne, no employer share unlike PF/ESI).
  Monthly states do a straight slab lookup on GROSS every payslip.
  Half-yearly states (Tamil Nadu, Kerala) accumulate GROSS across the
  Apr-Sep/Oct-Mar period via payslips.sum() (which only reads CONFIRMED
  prior payslips - a real operational dependency, not a bug) plus the
  current month, but only actually charge the resulting slab amount in
  the state's designated charge month; every other month it's 0. No
  condition_python gate - all of this (missing pt_state_id, non-charge
  month) resolves to result=0.0 inside the rule itself.
* Two bugs found and fixed while building/testing this release, both
  worth knowing about beyond just PT: (1) OCA payroll's own
  hr.payslip.credit_note field has no default=False, so new payslips get
  NULL in Postgres, and Payslips.sum()'s raw SQL ("WHEN credit_note =
  False THEN total ELSE -total") silently negates every sum because
  NULL = False is NULL, not TRUE, in SQL - fixed by re-declaring the
  field with an explicit default in this module's hr_payslip.py.
  (2) payslips.sum() runs raw SQL that doesn't see the ORM's own
  unflushed pending writes - the PT rule now calls env.flush_all()
  before that query so it's correct regardless of whether prior months'
  payslips were confirmed in the same transaction or separate ones.

R3.5 - Labour Welfare Fund (multi-state):

* New models bpro.lwf.config and bpro.lwf.slab.line, mirroring the PT
  models' shape (income-band lookup, though every seeded state currently
  has exactly one unbounded band = a flat amount) so an income-tiered
  state can be added later via data alone. Seeded with Karnataka
  (Rs.50 employee / Rs.100 employer), Tamil Nadu (Rs.20/Rs.40) and Andhra
  Pradesh (Rs.30/Rs.70) - researched 2026-08-11, all annual, charged in
  December, all flagged for verification before go-live along with their
  respective applicability thresholds (Karnataka: 10+ employees since
  7 Jan 2026; Andhra Pradesh: factories regardless of headcount, shops/
  commercial establishments need 20+).
* Kerala is deliberately NOT seeded - sources conflict on whether it has
  one general LWF Act or several sector-specific boards (a 1975 Act, a
  separate 2007 Shops & Commercial Establishments Workers Welfare Fund
  Board, construction/headload-worker boards). Add a bpro.lwf.config for
  it via Settings > HR > Configuration > "Labour Welfare Fund States"
  once the client's applicable board is confirmed - no code change
  needed, that form is the entire configuration surface.
* Adds lwf_state_id to hr.contract.
* Two rules (LWF_EE under DED, reduces Net; LWF_ER under the same
  employer-cost rollup category PF/ESI's employer lines use) - unlike PT,
  LWF has both an employee and an employer share. Annual/monthly
  periodicity look up the slab against the CURRENT month's GROSS, not an
  accumulated period figure - no payslips.sum() call, so none of R3.4's
  flush-timing concern applies here.
* NET's sequence bumped 80 -> 90 (a field-only override on the existing
  R3.1 rule, not a rewrite of that file) to make room for LWF_EE/LWF_ER
  at 80/81, since PT/PF/ESI already filled sequences 71-79 contiguously.

R3.6a - TDS core tax engine (no investment declarations yet - that's
R3.6b; old regime here is annual Gross minus standard deduction only):

* New models bpro.tds.regime.config (regime new/old, fy_start_year,
  standard_deduction, 87A rebate threshold/amount, cess_rate) and
  bpro.tds.slab.line (bounds + rate) - tax slabs change nearly every
  Union Budget, more volatile than PF/ESI/PT/LWF, so next year's Budget
  is a data change here, not a code change. Seeded FY2026-27 (1 Apr 2026
  - 31 Mar 2027) for both regimes, researched 2026-08-11: New Regime -
  0-4L nil/4-8L 5%/8-12L 10%/12-16L 15%/16-20L 20%/20-24L 25%/24L+ 30%,
  std deduction 75000, 87A rebate up to 60000 if income <= 12L. Old
  Regime - 0-2.5L nil/2.5-5L 5%/5-10L 20%/10L+ 30%, std deduction 50000,
  87A rebate up to 12500 if income <= 5L. Both: 4% cess. Neither
  implements marginal relief near the rebate cliff or surcharge for very
  high incomes (>50L/1Cr) - known gaps, flag if relevant to the client.
  Old regime slabs shown are for individuals below 60; senior/super-
  senior relaxed thresholds aren't modelled (no age category yet).
* Adds tds_regime to hr.contract (new/old, default new) - optional per
  employee, either is valid; doesn't enforce the once-per-FY change
  restriction real tax law imposes.
* Single TDS rule (category TDS, parented to DED, reduces Net). Method:
  projected annual Gross = actual confirmed-payslip GROSS so far this FY
  (payslips.sum) + this month's GROSS x remaining months (incl. this
  one); subtract standard deduction for taxable income; run through the
  regime's progressive slabs; apply the 87A rebate if under threshold;
  add cess for annual TDS; subtract TDS already withheld this FY; spread
  across remaining months. Recomputes fresh every payslip, so a mid-year
  raise or bonus naturally reweights what's left to withhold - this is
  the standard method real payroll systems use. Same env.flush_all()
  defensiveness as R3.4's PT rule, same reason (payslips.sum() needs
  prior months confirmed and doesn't see unflushed ORM writes).

R3.6b - TDS investment declarations (Old Regime only - the New Regime
disallows HRA exemption, 80C and 80D under current law):

* New model bpro.tds.declaration (per contract per financial year):
  declared_80c, declared_80d, monthly_rent, plus a draft -> submitted ->
  approved/rejected workflow. Only an APPROVED declaration affects TDS -
  submitted-but-unreviewed behaves exactly like no declaration at all,
  deliberately, so an unverified claim never under-withholds tax.
* The TDS rule now computes HRA exemption using the same projected-
  annual accumulation pattern as Gross (actual BASIC/HRA so far this FY
  + this month's rate x remaining months, not a flat x12) as
  min(projected annual HRA, annual rent - 10% of projected annual Basic,
  40%/50% of projected annual Basic) - the 40/50 split reuses the
  contract's existing hra_percent as a metro/non-metro proxy (>=50 =
  metro) rather than adding a separate flag. 80C is capped at Rs.1,50,000
  and 80D at Rs.25,000 (a simplification - no senior-citizen category in
  this build, so the higher senior-citizen 80D caps aren't modelled).
  New Regime contracts and contracts with no approved declaration are
  completely unaffected - taxable income still comes out exactly as
  R3.6a computed it.

R3.6c - Form 16 Part B:

* Adds pan to hr.employee and tan to res.company - identifiers a real
  Form 16 displays, even though this build doesn't file anything with
  the government.
* New model bpro.tds.form16 (per contract per FY): an "Generate/Refresh"
  action aggregates ACTUAL confirmed-payslip figures for the full
  financial year (not the monthly rule's projection - at year-end the
  real numbers exist) - Gross paid, HRA exemption, standard deduction,
  80C/80D from an approved declaration if one exists, taxable income,
  progressive tax, 87A rebate, cess, total annual liability, actual TDS
  withheld, and the balance payable or refund-due. Deliberately does NOT
  deduct Professional Tax under Section 16(iii) - matches the R3.6a/b
  monthly TDS engine's own omission, kept consistent on purpose rather
  than introducing a document that disagrees with what was actually
  withheld during the year.
* QWeb PDF report (Print button once generated). Explicitly labelled on
  the document itself: this is Part B, the computation, not Part A - the
  actual government-filed TDS certificate, which needs the employer's
  TAN and TRACES portal filing and is out of scope for any payroll
  software, this one included.
""",
    "version": "18.0.1.8.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": [
        "bpro_base",
        "bpro_hr",
        "payroll",
        "payroll_account",
        "payroll_contract_advantages",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_salary_rule_category_data.xml",
        "data/hr_contract_advantage_template_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_salary_rule_category_data_pf.xml",
        "data/hr_payroll_structure_data_pf.xml",
        "data/hr_salary_rule_category_data_esi.xml",
        "data/hr_payroll_structure_data_esi.xml",
        "data/bpro_pt_config_data.xml",
        "data/hr_salary_rule_category_data_pt.xml",
        "data/hr_payroll_structure_data_pt.xml",
        "data/bpro_lwf_config_data.xml",
        "data/hr_salary_rule_category_data_lwf.xml",
        "data/hr_payroll_structure_data_lwf.xml",
        "data/bpro_tds_config_data.xml",
        "data/hr_salary_rule_category_data_tds.xml",
        "data/hr_payroll_structure_data_tds.xml",
        "views/hr_contract_views.xml",
        "views/hr_employee_views.xml",
        "views/res_company_views.xml",
        "views/bpro_pt_config_views.xml",
        "views/bpro_lwf_config_views.xml",
        "views/bpro_tds_config_views.xml",
        "views/bpro_tds_declaration_views.xml",
        "views/report_form16.xml",
        "views/report_payslip.xml",
        "views/bpro_tds_form16_views.xml",
    ],
    "installable": True,
    "application": False,
}
