{
    "name": "bpro HR Letters — Certificates & Employment Letters",
    "summary": "Salary certificate, address proof, experience/relieving letter and increment letter from one generator (R6.4)",
    "description": """
One model, one report action, four letter types - the letters HR
issues on request or at lifecycle events, previously drafted by hand
in Word each time:

* Salary Certificate: designation, current CTC and monthly gross from
  the active contract - the letter banks/landlords ask employees for.
* Address Proof: employment + registered address confirmation.
* Experience / Relieving Letter: service period and designation - and
  bpro_exit's Close action now auto-creates one, so every properly
  offboarded employee leaves with their relieving letter ready to
  print rather than requesting it weeks later.
* Increment Letter: revised CTC (entered on the letter record - a full
  salary-revision cycle with arrears is future scope, this covers the
  letter itself).

Letters are numbered (ir.sequence, LTR00001) since certificates get
cited back to the company - "as per your letter LTR00042" must be
resolvable.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_hr", "bpro_payroll", "bpro_exit"],
    "data": [
        "security/ir.model.access.csv",
        "data/bpro_hr_letter_sequence.xml",
        "views/report_hr_letter.xml",
        "views/bpro_hr_letter_views.xml",
    ],
    "installable": True,
    "application": False,
}
