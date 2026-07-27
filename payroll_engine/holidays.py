"""
Ethiopian Holiday Calendar

Public holidays in Ethiopia. Mix of fixed Gregorian dates and
Orthodox Christian moveable feasts (Easter-based).

Ethiopian calendar reference:
    Meskerem 1 = Enkutatash (New Year) ≈ Sep 11 (Gregorian)
    The Ethiopian year runs Sep 11 – Sep 10 (Gregorian)

All holidays are seeded for 2025 and 2026.
Moveable feasts (Easter, Good Friday, Eid) are calculated or
manually set each year.

Usage:
    flask seed-holidays    # Seeds holidays for current + next year
"""

from datetime import date, timedelta
from payroll_engine.models import Holiday
from payroll_engine import db
from payroll_engine.models import Company


# Ethiopian National Holidays (fixed Gregorian dates)
# These are the standard public holidays recognized by the Ethiopian government
NATIONAL_HOLIDAYS_2025 = [
    {'name': 'Ethiopian Christmas', 'name_am': 'ገና', 'date': date(2025, 1, 7), 'recurring': False},
    {'name': 'Epiphany', 'name_am': 'ጥምቀት', 'date': date(2025, 1, 19), 'recurring': False},
    {'name': 'Adwa Victory Day', 'name_am': 'የአድዋ ድል በዓል', 'date': date(2025, 3, 2), 'recurring': False},
    {'name': 'Ethiopian Good Friday', 'name_am': 'ስቅለት', 'date': date(2025, 4, 18), 'recurring': False},
    {'name': 'Ethiopian Easter', 'name_am': 'ፋሲካ', 'date': date(2025, 4, 20), 'recurring': False},
    {'name': 'International Workers\' Day', 'name_am': 'የሰራተኞች ቀን', 'date': date(2025, 5, 1), 'recurring': True},
    {'name': 'Patriots\' Victory Day', 'name_am': 'የአርበኞች ድል በዓል', 'date': date(2025, 5, 28), 'recurring': False},
    {'name': 'Downfall of the Dergue', 'name_am': 'ደርግ የወደቀበት ቀን', 'date': date(2025, 5, 28), 'recurring': False},
    {'name': 'Enkutatash (New Year)', 'name_am': 'እንኳታሽ', 'date': date(2025, 9, 11), 'recurring': False},
    {'name': 'Finding of the True Cross', 'name_am': 'መስቀል', 'date': date(2025, 9, 27), 'recurring': False},
]

NATIONAL_HOLIDAYS_2026 = [
    {'name': 'Ethiopian Christmas', 'name_am': 'ገና', 'date': date(2026, 1, 7), 'recurring': False},
    {'name': 'Epiphany', 'name_am': 'ጥምቀት', 'date': date(2026, 1, 19), 'recurring': False},
    {'name': 'Adwa Victory Day', 'name_am': 'የአድዋ ድል በዓል', 'date': date(2026, 3, 2), 'recurring': False},
    {'name': 'Ethiopian Good Friday', 'name_am': 'ስቅለት', 'date': date(2026, 4, 10), 'recurring': False},
    {'name': 'Ethiopian Easter', 'name_am': 'ፋሲካ', 'date': date(2026, 4, 12), 'recurring': False},
    {'name': 'International Workers\' Day', 'name_am': 'የሰራተኞች ቀን', 'date': date(2026, 5, 1), 'recurring': True},
    {'name': 'Patriots\' Victory Day', 'name_am': 'የአርበኞች ድል በዓል', 'date': date(2026, 5, 28), 'recurring': False},
    {'name': 'Downfall of the Dergue', 'name_am': 'ደርግ የወደቀበት ቀን', 'date': date(2026, 5, 28), 'recurring': False},
    {'name': 'Enkutatash (New Year)', 'name_am': 'እንኳታሽ', 'date': date(2026, 9, 11), 'recurring': False},
    {'name': 'Finding of the True Cross', 'name_am': 'መስቀል', 'date': date(2026, 9, 27), 'recurring': False},
]


def seed_holidays():
    """Seed national holidays for current and next year."""
    all_holidays = NATIONAL_HOLIDAYS_2025 + NATIONAL_HOLIDAYS_2026
    
    added = 0
    for h in all_holidays:
        existing = Holiday.query.filter_by(
            name=h['name'],
            holiday_date=h['date'],
            is_national=True,
            company_id=None
        ).first()
        
        if not existing:
            holiday = Holiday(
                company_id=None,
                name=h['name'],
                name_am=h.get('name_am'),
                holiday_date=h['date'],
                is_national=True,
                is_recurring=h.get('recurring', False),
                description=f"Ethiopian national holiday"
            )
            db.session.add(holiday)
            added += 1
    
    db.session.commit()
    return added


def get_holidays_for_month(year, month, company_id=None):
    """Get all holidays for a given month (national + company-specific)."""
    from datetime import date as dt_date
    
    start = dt_date(year, month, 1)
    if month == 12:
        end = dt_date(year + 1, 1, 1)
    else:
        end = dt_date(year, month + 1, 1)
    
    holidays = Holiday.query.filter(
        Holiday.holiday_date >= start,
        Holiday.holiday_date < end,
        db.or_(
            Holiday.is_national == True,
            Holiday.company_id == company_id
        )
    ).order_by(Holiday.holiday_date).all()
    
    return holidays


def is_holiday(check_date, company_id=None):
    """Check if a date is a holiday."""
    return Holiday.query.filter(
        Holiday.holiday_date == check_date,
        db.or_(
            Holiday.is_national == True,
            Holiday.company_id == company_id
        )
    ).first() is not None


def get_working_days(year, month, company_id=None):
    """Count working days in a month (excluding weekends and holidays)."""
    from datetime import date as dt_date, timedelta
    
    start = dt_date(year, month, 1)
    if month == 12:
        end = dt_date(year + 1, 1, 1)
    else:
        end = dt_date(year, month + 1, 1)
    
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
