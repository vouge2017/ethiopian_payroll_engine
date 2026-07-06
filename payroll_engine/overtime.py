"""
Ethiopian Overtime Rate Calculator

Labor Proclamation No. 1156/2019, Article 68:
    - Regular day overtime:     1.25x  (Art. 68(1))
    - Night overtime (10pm-6am): 1.5x  (Art. 68(2))
    - Public holiday:           2.0x   (Art. 68(3))
    - Rest day + public holiday: 2.5x  (Art. 68(4))

Hourly rate = basic_salary / 30 days / 8 hours
Overtime pay = hourly_rate × hours × multiplier

Overtime is taxable income (included in gross for ERCA reporting).
Overtime limit: 20 hours/month, 100 hours/year (Art. 89).
"""

from typing import Optional

# Rate multipliers per Ethiopian labor law
OVERTIME_RATES = {
    'day': 1.25,           # Regular day overtime
    'night': 1.50,         # Nighttime (10pm-6am)
    'holiday': 2.00,       # Public holiday
    'rest_day_holiday': 2.50,  # Weekly rest day that falls on public holiday
}

# Legal limits
MAX_OVERTIME_HOURS_MONTH = 20   # Art. 89(1)
MAX_OVERTIME_HOURS_YEAR = 100   # Art. 89(2)


def calculate_hourly_rate(basic_salary: float) -> float:
    """
    Calculate hourly rate from monthly basic salary.

    Ethiopian convention: 30 days/month, 8 hours/day.
    Hourly = basic_salary / 30 / 8

    Args:
        basic_salary: Monthly basic salary in ETB

    Returns:
        Hourly rate in ETB
    """
    if basic_salary <= 0:
        return 0.0
    return round(basic_salary / 30.0 / 8.0, 2)


def calculate_overtime_pay(basic_salary: float, hours: float,
                           overtime_type: str = 'day') -> float:
    """
    Calculate overtime pay for a given number of hours.

    Args:
        basic_salary: Monthly basic salary in ETB
        hours: Number of overtime hours
        overtime_type: One of 'day', 'night', 'holiday', 'rest_day_holiday'

    Returns:
        Overtime pay in ETB

    Raises:
        ValueError: If overtime_type is invalid
    """
    if hours <= 0:
        return 0.0

    if overtime_type not in OVERTIME_RATES:
        raise ValueError(
            f"Invalid overtime type '{overtime_type}'. "
            f"Must be one of: {', '.join(OVERTIME_RATES.keys())}"
        )

    hourly_rate = calculate_hourly_rate(basic_salary)
    multiplier = OVERTIME_RATES[overtime_type]
    return round(hourly_rate * hours * multiplier, 2)


def calculate_total_overtime(basic_salary: float, overtime_entries: list) -> dict:
    """
    Calculate total overtime pay from multiple entries.

    Args:
        basic_salary: Monthly basic salary in ETB
        overtime_entries: List of dicts with 'hours' and 'type' keys
            e.g., [{'hours': 4, 'type': 'day'}, {'hours': 2, 'type': 'night'}]

    Returns:
        Dict with:
            total_hours: total overtime hours
            total_pay: total overtime pay
            entries: list of processed entries with pay amounts
            exceeds_monthly_limit: bool (True if > 20 hours)
            warnings: list of warning messages
    """
    total_hours = 0.0
    total_pay = 0.0
    entries = []
    warnings = []

    for entry in overtime_entries:
        hours = entry.get('hours', 0)
        ot_type = entry.get('type', 'day')

        if hours <= 0:
            continue

        pay = calculate_overtime_pay(basic_salary, hours, ot_type)
        total_hours += hours
        total_pay += pay

        entries.append({
            'hours': hours,
            'type': ot_type,
            'rate': OVERTIME_RATES.get(ot_type, 1.0),
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
        'total_hours': round(total_hours, 2),
        'total_pay': round(total_pay, 2),
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
