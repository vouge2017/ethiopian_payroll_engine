"""
Ethiopian Overtime Rate Calculator

Labor Proclamation No. 1156/2019, Article 68:
    - Regular day overtime:     1.25x  (Art. 68(1))
    - Night overtime (10pm-6am): 1.5x  (Art. 68(2))
    - Public holiday:           2.0x   (Art. 68(3))
    - Rest day + public holiday: 2.5x  (Art. 68(4))

Hourly rate = basic_salary / 208
    208 = 26 working days × 8 hours (Ethiopian standard: 6 days/week, 48h/week)
Overtime pay = hourly_rate × hours × multiplier

Overtime is taxable income (included in gross for ERCA reporting).
Overtime limit: 20 hours/month, 100 hours/year (Art. 89).
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional

# Quantizer for 2 decimal places
Q = Decimal('0.01')

# Rate multipliers per Ethiopian labor law
OVERTIME_RATES = {
    'day': Decimal('1.25'),           # Regular day overtime
    'night': Decimal('1.50'),         # Nighttime (10pm-6am)
    'holiday': Decimal('2.00'),       # Public holiday
    'rest_day_holiday': Decimal('2.50'),  # Weekly rest day that falls on public holiday
}

# Legal limits
MAX_OVERTIME_HOURS_MONTH = 20   # Art. 89(1)
MAX_OVERTIME_HOURS_YEAR = 100   # Art. 89(2)


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def calculate_hourly_rate(basic_salary) -> Decimal:
    """
    Calculate hourly rate from monthly basic salary.

    Ethiopian Labor Proclamation No. 1156/2019:
    - Standard work week: 48 hours (6 days × 8 hours)
    - Monthly working days: 26 (6 days × 4.33 weeks)
    - Monthly working hours: 208 (26 × 8)
    - Hourly = basic_salary / 208

    Args:
        basic_salary: Monthly basic salary in ETB

    Returns:
        Hourly rate in ETB, as Decimal
    """
    basic_salary = _D(basic_salary)
    if basic_salary <= 0:
        return Decimal('0')
    return (basic_salary / Decimal('208')).quantize(Q, rounding=ROUND_HALF_UP)


def calculate_overtime_pay(basic_salary, hours, overtime_type: str = 'day') -> Decimal:
    """
    Calculate overtime pay for a given number of hours.

    Args:
        basic_salary: Monthly basic salary in ETB
        hours: Number of overtime hours
        overtime_type: One of 'day', 'night', 'holiday', 'rest_day_holiday'

    Returns:
        Overtime pay in ETB, as Decimal

    Raises:
        ValueError: If overtime_type is invalid
    """
    hours = _D(hours)
    if hours <= 0:
        return Decimal('0')

    if overtime_type not in OVERTIME_RATES:
        raise ValueError(
            f"Invalid overtime type '{overtime_type}'. "
            f"Must be one of: {', '.join(OVERTIME_RATES.keys())}"
        )

    hourly_rate = calculate_hourly_rate(basic_salary)
    multiplier = OVERTIME_RATES[overtime_type]
    return (hourly_rate * hours * multiplier).quantize(Q, rounding=ROUND_HALF_UP)


def calculate_total_overtime(basic_salary, overtime_entries: list) -> dict:
    """
    Calculate total overtime pay from multiple entries.

    Args:
        basic_salary: Monthly basic salary in ETB
        overtime_entries: List of dicts with 'hours' and 'type' keys

    Returns:
        Dict with:
            total_hours: Decimal
            total_pay: Decimal
            entries: list of processed entries
            exceeds_monthly_limit: bool
            warnings: list of warning messages
    """
    total_hours = Decimal('0')
    total_pay = Decimal('0')
    entries = []
    warnings = []

    for entry in overtime_entries:
        hours = _D(entry.get('hours', 0))
        ot_type = entry.get('type', 'day')

        if hours <= 0:
            continue

        pay = calculate_overtime_pay(basic_salary, hours, ot_type)
        total_hours += hours
        total_pay += pay

        entries.append({
            'hours': hours,
            'type': ot_type,
            'rate': OVERTIME_RATES.get(ot_type, Decimal('1')),
            'pay': pay,
        })

    # Check monthly limit
    if total_hours > MAX_OVERTIME_HOURS_MONTH:
        warnings.append(
            f"Overtime exceeds {MAX_OVERTIME_HOURS_MONTH}-hour monthly limit "
            f"(Labor Proclamation 1156/2019, Art. 89). "
            f"Total: {total_hours} hours."
        )

    return {
        'total_hours': total_hours.quantize(Q, rounding=ROUND_HALF_UP),
        'total_pay': total_pay.quantize(Q, rounding=ROUND_HALF_UP),
        'entries': entries,
        'exceeds_monthly_limit': total_hours > MAX_OVERTIME_HOURS_MONTH,
        'warnings': warnings,
    }


def get_overtime_type_label(overtime_type: str) -> str:
    """Get human-readable label for overtime type."""
    labels = {
        'day': 'Regular Day (1.25x)',
        'night': 'Night / 10pm-6am (1.5x)',
        'holiday': 'Public Holiday (2.0x)',
        'rest_day_holiday': 'Rest Day + Holiday (2.5x)',
    }
    return labels.get(overtime_type, overtime_type)
