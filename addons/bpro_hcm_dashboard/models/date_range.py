"""Period maths for the HCM dashboard - plain functions, no ORM, so the
range rules are unit-testable on their own.

Rules (one place, so every KPI agrees):
* Both ends are INCLUSIVE dates: a range (1 Nov, 10 Nov) covers ten
  whole days in the user's timezone.
* "Today" is the user's local date (user tz, else Asia/Kolkata) - never
  the server's UTC date, which is still yesterday until 05:30 IST.
* Financial year: Indian Apr-Mar unless the company has set a different
  fiscal year end (account's fiscalyear_last_month/day). Odoo ships
  31 Dec as the untouched default; that is treated as "not set" because
  this suite is India-first (Companies Act s2(41) fixes Apr-Mar for
  almost every Indian company).
* Every preset ends today ("to date") - a dashboard "as of" a future
  date has no meaning for balances and headcount.
"""

import calendar
from datetime import date, datetime, time, timedelta

import pytz

DEFAULT_TZ = "Asia/Kolkata"
INDIAN_FY_END = (3, 31)

PRESETS = [
    ("today", "Today"),
    ("this_week", "This week"),
    ("month_to_date", "This month to date"),
    ("last_month", "Last month"),
    ("last_30_days", "Last 30 days"),
    ("this_quarter", "This quarter"),
    ("fy_to_date", "This FY to date"),
    ("custom", "Custom"),
]


def local_today(tz_name=None, now_utc=None):
    """The calendar date right now in ``tz_name`` (default Asia/Kolkata)."""
    try:
        tz = pytz.timezone(tz_name or DEFAULT_TZ)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone(DEFAULT_TZ)
    now_utc = now_utc or datetime.utcnow()
    return pytz.utc.localize(now_utc).astimezone(tz).date()


def _fy_end_in_year(year, fy_end):
    month, day = fy_end
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def company_fy_end(company):
    """(month, day) of the company's fiscal-year end; Apr-Mar by default."""
    if company is not None and "fiscalyear_last_month" in company._fields:
        month = int(company.fiscalyear_last_month or 12)
        day = int(company.fiscalyear_last_day or 31)
        if (month, day) != (12, 31):
            return (month, day)
    return INDIAN_FY_END


def fy_start(day, fy_end=INDIAN_FY_END):
    """First day of the financial year containing ``day``."""
    end_this_year = _fy_end_in_year(day.year, fy_end)
    if day <= end_this_year:
        return _fy_end_in_year(day.year - 1, fy_end) + timedelta(days=1)
    return end_this_year + timedelta(days=1)


def _add_months(day, months):
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def quarter_start(day, fy_end=INDIAN_FY_END):
    """First day of the FY quarter containing ``day``. With Apr-Mar
    (or any FY that starts on the 1st of Jan/Apr/Jul/Oct) this is the
    calendar quarter."""
    start = fy_start(day, fy_end)
    for _ in range(4):
        nxt = _add_months(start, 3)
        if day < nxt:
            return start
        start = nxt
    return start


def preset_range(preset, today, fy_end=INDIAN_FY_END):
    """(date_from, date_to), both inclusive, for a named preset."""
    if preset == "today":
        return today, today
    if preset == "this_week":
        return today - timedelta(days=today.weekday()), today
    if preset == "month_to_date":
        return today.replace(day=1), today
    if preset == "last_month":
        last_day = today.replace(day=1) - timedelta(days=1)
        return last_day.replace(day=1), last_day
    if preset == "last_30_days":
        return today - timedelta(days=29), today
    if preset == "this_quarter":
        return quarter_start(today, fy_end), today
    if preset == "fy_to_date":
        return fy_start(today, fy_end), today
    raise ValueError("Unknown date-range preset: %r" % (preset,))


def utc_bounds(date_from, date_to, tz_name=None):
    """Naive-UTC [start, stop) datetimes covering the inclusive local
    dates - for filtering Datetime columns (stored as naive UTC).
    Use ``>= start`` and ``< stop``."""
    try:
        tz = pytz.timezone(tz_name or DEFAULT_TZ)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone(DEFAULT_TZ)
    start = tz.localize(datetime.combine(date_from, time.min))
    stop = tz.localize(datetime.combine(date_to + timedelta(days=1), time.min))
    return (
        start.astimezone(pytz.utc).replace(tzinfo=None),
        stop.astimezone(pytz.utc).replace(tzinfo=None),
    )


def overlap_days(start, end, date_from, date_to):
    """Whole days the inclusive [start, end] shares with [date_from, date_to]."""
    lo, hi = max(start, date_from), min(end, date_to)
    return (hi - lo).days + 1 if hi >= lo else 0
