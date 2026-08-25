{
    "name": "bpro Employment Type — Permanent, FTC, Trainee, Daily Wage, Contract Labour",
    "summary": "Classifies each contract's engagement type and adjusts payroll defaults/computation accordingly",
    "description": """
Closes a real, confirmed gap: the payroll engine assumed every
contract was a standard monthly-salaried CTC employee. Real
manufacturing workforces mix several engagement types with genuinely
different statutory treatment.

This is a SEPARATE axis from bpro_probation's probation_state
(probation/confirmed) - that field tracks WHETHER a given employee's
initial trial period has ended, which applies regardless of engagement
type. This module classifies WHAT KIND of engagement it is. A Fixed
Term Contract hire can still be "on probation" within their FTC term,
for example - the two fields are orthogonal on purpose, not merged.

* hr.contract.employment_category (Selection): Permanent (default,
  the existing CTC/Basic%/HRA% engine, unchanged), Fixed Term Contract,
  Trainee/Apprentice, Daily Wage, Contract Labour.

* Fixed Term Contract: uses the SAME CTC engine as Permanent - the
  Industrial Employment (Standing Orders) Act 2018 amendment mandates
  statutory parity of benefits, pro-rata, with permanent employees, so
  there's no separate pay computation. What's enforced is a hard
  requirement that native hr.contract.date_end is set - FTC's whole
  legal definition IS having a fixed end date (that field already
  exists natively, its own help text says "if it's a fixed-term
  contract" - reused here rather than duplicated).

* Trainee/Apprentice: PF/ESI default to NOT applicable (registered
  apprentices under the Apprentices Act 1961 are generally outside
  PF/ESI coverage) - HR can override per contract for a company's own
  broader, informal use of "trainee" that isn't a registered
  apprenticeship. Confirmed with the client 2026-08-14 rather than
  assumed.

* Daily Wage: genuinely different computation, not just a label -
  Basic is daily_wage_rate x actual attendance days worked that
  period (from bpro_attendance), NOT the CTC/12-prorated figure
  everything else uses. Confirmed with the client 2026-08-14 rather
  than assumed. Deliberately NOT also multiplied by the LOP proration
  factor - a daily-wage worker is already inherently paid only for
  days worked, so applying LOP on top would double-penalize the same
  absence. HRA still computes as its usual % of Basic - no special
  case needed there, since Basic already carries the right base
  figure either way. Overtime for Daily Wage contracts uses
  daily_wage_rate / 8 as the hourly rate (bpro_overtime handles this
  when both modules are installed).

* Contract Labour: PF/ESI default to NOT applicable (statutorily the
  labour contractor's own establishment, not the principal employer's,
  is normally the responsible party) - flagged, not fully modelled;
  see KNOWN_LIMITATIONS.md. Workers in this category are typically NOT
  expected to be run through this payroll at all.


""",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Dr. Babu & bpro Technologies",
    "website": "https://www.bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_payroll", "bpro_leave", "bpro_attendance"],
    "data": [
        "views/hr_contract_views.xml",
        "data/hr_salary_rule_employment_type.xml",
    ],
    "installable": True,
    "application": False,
}
