"""
Ethiopian public-holiday calendar (national seed data + helpers).

Legal source: Public Holidays Proclamation No. 1334/2024 (Federal Negarit
Gazette No. 55, 14 August 2024). Structure:

  Art. 4  celebrated national holidays — institutions closed, salaried:
            1 Meskerem (Enkutatash, Ethiopian New Year) -> Sep 11/12 GC
            23 Megabit (Adwa Victory Day)               -> Mar 2 GC
            May 1 GC   (Workers' Day)
            May 5 GC   (Patriots' Victory Day)
  Art. 5  memorial national holidays — institutions OPEN, NOT days off:
            Feb 20 (Martyrs' Day), Dec 9 (Nations/Nationalities Day).
            Deliberately NOT seeded as holidays.
  Art. 6  religious holidays — institutions closed, salaried:
            17 Meskerem (Meskel)          -> Sep 27/28 GC
            29 Tahsas   (Gena, Christmas) -> Jan 7 GC
            11 Ter      (Timket, Epiphany)-> Jan 19 GC
            Good Friday and Easter (movable, computed),
            Mawlid, Eid al-Fitr, Eid al-Adha (lunar, see below).
  Art. 7  public holidays are paid days.

  May 28 (Downfall of the Derg) was REMOVED by Proc. 1334/2024 and is no
  longer a public holiday. Patriots' Victory Day is May 5, not May 28 (the
  pre-2024 seed wrongly put both on May 28).

Gregorian mapping notes:
  * 1 Meskerem falls on Sep 11 GC, except when the FOLLOWING Gregorian year
    is a leap year, when it falls on Sep 12 (e.g. 2027, before 2028);
    17 Meskerem follows the same shift (Sep 27 / Sep 28). Verified for 2027
    by timeanddate.com, officeholidays.com and clockit.io (all Sep 12/Sep 28).
  * 29 Tahsas (Jan 7) and 11 Ter (Jan 19) are constant for the seeded window
    (2025-2027); before extending the window past it, re-check the next
    years against official announcements.

Movable feasts:
  * Orthodox Good Friday and Easter follow the Julian computus and are
    computed exactly by orthodox_easter().
  * Mawlid, Eid al-Fitr and Eid al-Adha are lunar. Proc. 1334/2024 names
    them as paid holidays, but their Gregorian dates move every year and
    are only fixed by the official announcement. Public aggregator sources
    conflict, so this module does NOT guess them: record each announced
    date with add_national_holiday(). Until a date is recorded, such a day
    is treated as an ordinary working day — a documented limitation
    (PLAN.md), not a statement that it is a working day.

Usage:
    flask seed-holidays    # Seeds national holidays for the default years
"""

from datetime import date, timedelta

from payroll_engine import db
from payroll_engine.models import Holiday

# Years the corrected list is verified for (Proc. 1334/2024 window).
BASE_YEARS = (2025, 2026, 2027)


def is_gregorian_leap(year: int) -> bool:
    """True for Gregorian leap years."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def orthodox_easter(year: int) -> date:
    """Orthodox (Julian-computus) Easter Sunday as a Gregorian date.

    Meeus' Julian algorithm; the +13 day offset is valid 1900-2099.
    Pinned by tests: 2025-04-20, 2026-04-12, 2027-05-02.
    """
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    return date(year, month, day) + timedelta(days=13)


def _enkutatash(year: int) -> date:
    """1 Meskerem in Gregorian terms: Sep 12 when the next year is a leap year."""
    if is_gregorian_leap(year + 1):
        return date(year, 9, 12)
    return date(year, 9, 11)


def national_holidays(year: int) -> list[dict]:
    """Proc. 1334/2024 closed, salaried national holidays for a Gregorian year."""
    easter = orthodox_easter(year)
    return [
        {
            'name': 'Ethiopian Christmas',
            'name_am': 'ገና',
            'date': date(year, 1, 7),
            'description': 'Gena, 29 Tahsas — Public Holidays Proc. 1334/2024 Art. 6',
        },
        {
            'name': 'Epiphany',
            'name_am': 'ጥምቀት',
            'date': date(year, 1, 19),
            'description': 'Timket, 11 Ter — Public Holidays Proc. 1334/2024 Art. 6',
        },
        {
            'name': 'Adwa Victory Day',
            'name_am': 'የአድዋ ድል በዓል',
            'date': date(year, 3, 2),
            'description': '23 Megabit — Public Holidays Proc. 1334/2024 Art. 4',
        },
        {
            'name': 'Ethiopian Good Friday',
            'name_am': 'ስቅለት',
            'date': easter - timedelta(days=2),
            'description': 'Siklet (movable) — Public Holidays Proc. 1334/2024 Art. 6',
        },
        {
            'name': 'Ethiopian Easter',
            'name_am': 'ፋሲካ',
            'date': easter,
            'description': 'Fasika (movable) — Public Holidays Proc. 1334/2024 Art. 6',
        },
        {
            'name': "International Workers' Day",
            'name_am': 'የሰራተኞች ቀን',
            'date': date(year, 5, 1),
            'description': 'Public Holidays Proc. 1334/2024 Art. 4',
        },
        {
            'name': "Patriots' Victory Day",
            'name_am': 'የአርበኞች ድል በዓል',
            'date': date(year, 5, 5),
            'description': 'Public Holidays Proc. 1334/2024 Art. 4 (was wrongly May 28 before 2024)',
        },
        {
            'name': 'Enkutatash (New Year)',
            'name_am': 'እንቁጣጣሽ',
            'date': _enkutatash(year),
            'description': '1 Meskerem — Public Holidays Proc. 1334/2024 Art. 4',
        },
        {
            'name': 'Finding of the True Cross',
            'name_am': 'መስቀል',
            'date': _enkutatash(year) + timedelta(days=16),
            'description': 'Meskel, 17 Meskerem — Public Holidays Proc. 1334/2024 Art. 6',
        },
    ]


def seed_holidays(years=None):
    """Seed the national holidays. Idempotent; returns the number of rows added."""
    if years is None:
        years = sorted(set(BASE_YEARS) | {date.today().year, date.today().year + 1})
    added = 0
    for year in years:
        for h in national_holidays(year):
            existing = Holiday.query.filter_by(
                name=h['name'], holiday_date=h['date'], is_national=True, company_id=None
            ).first()
            if existing:
                continue
            db.session.add(
                Holiday(
                    company_id=None,
                    name=h['name'],
                    name_am=h.get('name_am'),
                    holiday_date=h['date'],
                    is_national=True,
                    is_recurring=False,
                    description=h.get('description', 'Ethiopian national holiday'),
                )
            )
            added += 1
    db.session.commit()
    return added


def add_national_holiday(name, holiday_date, name_am=None, description=None):
    """Record one officially announced national holiday date.

    This is the intended entry point for the lunar holidays Proc. 1334/2024
    Art. 6 names but whose Gregorian dates move every year: Mawlid,
    Eid al-Fitr and Eid al-Adha. Enter each date from the official
    government announcement. Idempotent by (name, date); returns the new
    Holiday, or None when that row already exists.
    """
    existing = Holiday.query.filter_by(name=name, holiday_date=holiday_date, is_national=True, company_id=None).first()
    if existing:
        return None
    holiday = Holiday(
        company_id=None,
        name=name,
        name_am=name_am,
        holiday_date=holiday_date,
        is_national=True,
        is_recurring=False,
        description=description or 'Officially announced national holiday',
    )
    db.session.add(holiday)
    db.session.commit()
    return holiday


def get_holidays_for_month(year, month, company_id=None):
    """Get all holidays for a given month (national + company-specific)."""
    from datetime import date as dt_date

    start = dt_date(year, month, 1)
    if month == 12:
        end = dt_date(year + 1, 1, 1)
    else:
        end = dt_date(year, month + 1, 1)

    holidays = (
        Holiday.query.filter(
            Holiday.holiday_date >= start,
            Holiday.holiday_date < end,
            db.or_(Holiday.is_national, Holiday.company_id == company_id),
        )
        .order_by(Holiday.holiday_date)
        .all()
    )

    return holidays


def is_holiday(check_date, company_id=None):
    """Check if a date is a holiday."""
    return (
        Holiday.query.filter(
            Holiday.holiday_date == check_date, db.or_(Holiday.is_national, Holiday.company_id == company_id)
        ).first()
        is not None
    )


def get_working_days(year, month, company_id=None):
    """Count working days in a month (excluding weekends and holidays)."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    holidays = set()
    for h in get_holidays_for_month(year, month, company_id):
        holidays.add(h.holiday_date)

    working_days = 0
    current = start
    while current < end:
        # Ethiopian work week: Mon-Sat (6 days). Sunday is rest day.
        if current.weekday() != 6 and current not in holidays:  # 6 = Sunday
            working_days += 1
        current += timedelta(days=1)

    return working_days
