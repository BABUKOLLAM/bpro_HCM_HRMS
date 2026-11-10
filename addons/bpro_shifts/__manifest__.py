{
    "name": "bpro Shifts — Shift Assignment & Rotation",
    "summary": "Dated shift assignments that keep each employee's working calendar current (R6.6)",
    "description": """
Multi-shift factories can't run on one standard calendar: the
attendance-exception detection, LOP proration and OT expectations all
read the employee's resource.calendar - so an employee on B shift
checked against the general calendar gets flagged absent at 09:00
while correctly working 14:00-22:00.

* A shift IS a resource.calendar - no parallel concept. This module
  adds the missing piece: bpro.shift.assignment, a dated history of
  which calendar applies to which employee from when (open-ended or
  bounded), overlap-checked per employee.
* The employee's resource_calendar_id is kept current automatically:
  set immediately when an assignment starting today-or-earlier is
  created, and by a daily cron that applies whichever assignment
  covers today - so a rotation entered in advance (A shift this week,
  B shift next) takes effect on the right morning without anyone
  remembering to flip it.
* Seeds two factory shifts as calendars: Shift A (06:00-14:00) and
  Shift B (14:00-22:00), Monday-Saturday - the common 6-day
  manufacturing pattern; edit or add per the plant's real roster. A
  night shift (crossing midnight) needs its calendar built with
  care at go-live - Odoo calendars are per-day, so 22:00-06:00 is two
  attendance lines - deliberately not seeded blind.
""",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["bpro_hr", "hr_attendance"],
    "data": [
        "security/ir.model.access.csv",
        "data/shift_calendars.xml",
        "data/bpro_shifts_cron.xml",
        "views/bpro_shift_assignment_views.xml",
    ],
    "installable": True,
    "application": False,
}
