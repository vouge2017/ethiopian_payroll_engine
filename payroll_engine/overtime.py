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

All multipliers and limits are configurable via TaxRule.rules_json['overtime'].
When no database rule exists, falls back to hardcoded defaults (Ethiopian law).
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, Dict, Tuple

# Quantizer for 2 decimal places
Q = Decimal('0.01')

# Default rate multipliers per Ethiopian labor law
DEFAULT_OVERTIME_RATES = {
    'day': Decimal('1.25'),           # Regular day overtime
    'night': Decimal('1.50'),         # Nighttime (10pm-6am)
    'holiday': Decimal('2.00'),       # Public holiday
    'rest_day_holiday': Decimal('2.50'),  # Weekly rest day that falls on public holiday
}

# Default legal limits
DEFAULT_MAX_HOURS_MONTH = 20   # Art. 89(1)
DEFAULT_MAX_HOURS_YEAR = 100   # Art. 89(2)

# Default hourly rate divisor (26 days × 8 hours)
DEFAULT_MONTHLY_HOURS = Decimal('208')

# Cache for overtime rules with TTL (5 minutes)
_rules_cache = {}
_rules_cache_ttl = 300
_rules_cache_timestamps = {}


def invalidate_overtime_cache():
    """Clear the overtime rules cache. Call after updating TaxRule records."""
    _rules_cache.clear()
    _rules_cache_timestamps.clear()


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _get_overtime_rules(for_date=None) -> dict:
    """
    Fetch overtime rules from the database.
    Falls back to hardcoded defaults if no TaxRule exists.
    Caches result to avoid repeated DB queries.

    Returns:
        Dict with keys: rates, max_hours_month, max_hours_year, monthly_hours
    """
    cache_key = str(for_date) if for_date else 'default'
    import time
    now = time.time()
    if cache_key in _rules_cache:
        cached_time = _rules_cache_timestamps.get(cache_key, 0)
        if now - cached_time < _rules_cache_ttl:
            return _rules_cache[cache_key]
        del _rules_cache[cache_key]
        del _rules_cache_timestamps[cache_key]

    result = {
        'rates': dict(DEFAULT_OVERTIME_RATES),
        'max_hours_month': DEFAULT_MAX_HOURS_MONTH,
        'max_hours_year': DEFAULT_MAX_HOURS_YEAR,
        'monthly_hours': DEFAULT_MONTHLY_HOURS,
    }

    try:
        from payroll_engine.models import TaxRule
        rule = TaxRule.get_active_rule(for_date)
        if rule:
            ot_cfg = rule.rules_json.get('overtime', {})
            if 'rates' in ot_cfg:
                for key, val in ot_cfg['rates'].items():
                    result['rates'][key] = _D(val)
            if 'max_hours_month' in ot_cfg:
                result['max_hours_month'] = int(ot_cfg['max_hours_month'])
            if 'max_hours_year' in ot_cfg:
                result['max_hours_year'] = int(ot_cfg['max_hours_year'])
            if 'monthly_hours' in ot_cfg:
                result['monthly_hours'] = _D(ot_cfg['monthly_hours'])
    except Exception:
        pass

    _rules_cache[cache_key] = result
    _rules_cache_timestamps[cache_key] = now
    return result


def calculate_hourly_rate(basic_salary, for_date=None) -> Decimal:
    """
    Calculate hourly rate from monthly basic salary.

    Ethiopian Labor Proclamation No. 1156/2019:
    - Standard work week: 48 hours (6 days × 8 hours)
    - Monthly working days: 26 (6 days × 4.33 weeks)
    - Monthly working hours: 208 (26 × 8)
    - Hourly = basic_salary / 208

    The divisor (208) is configurable via TaxRule.rules_json['overtime']['monthly_hours'].

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Hourly rate in ETB, as Decimal
    """
    basic_salary = _D(basic_salary)
    if basic_salary <= 0:
        return Decimal('0')
    rules = _get_overtime_rules(for_date)
    return (basic_salary / rules['monthly_hours']).quantize(Q, rounding=ROUND_HALF_UP)


def get_overtime_rates(for_date=None) -> Dict[str, Decimal]:
    """Get overtime rate multipliers. Returns dict of type -> multiplier."""
    return _get_overtime_rules(for_date)['rates']


def get_overtime_limits(for_date=None) -> Tuple[int, int]:
    """Get overtime limits. Returns (max_monthly, max_yearly)."""
    rules = _get_overtime_rules(for_date)
    return rules['max_hours_month'], rules['max_hours_year']


def calculate_overtime_pay(basic_salary, hours, overtime_type: str = 'day',
                           for_date=None) -> Decimal:
    """
    Calculate overtime pay for a given number of hours.

    Args:
        basic_salary: Monthly basic salary in ETB
        hours: Number of overtime hours
        overtime_type: One of 'day', 'night', 'holiday', 'rest_day_holiday'
        for_date: Optional date for rule versioning

    Returns:
        Overtime pay in ETB, as Decimal

    Raises:
        ValueError: If overtime_type is invalid
    """
    hours = _D(hours)
    if hours <= 0:
        return Decimal('0')

    rules = _get_overtime_rules(for_date)
    rates = rules['rates']

    if overtime_type not in rates:
        raise ValueError(
            f"Invalid overtime type '{overtime_type}'. "
            f"Must be one of: {', '.join(rates.keys())}"
        )

    hourly_rate = calculate_hourly_rate(basic_salary, for_date)
    multiplier = rates[overtime_type]
    return (hourly_rate * hours * multiplier).quantize(Q, rounding=ROUND_HALF_UP)


def calculate_total_overtime(basic_salary, overtime_entries: list,
                             for_date=None) -> dict:
    """
    Calculate total overtime pay from multiple entries.

    Args:
        basic_salary: Monthly basic salary in ETB
        overtime_entries: List of dicts with 'hours' and 'type' keys
        for_date: Optional date for rule versioning

    Returns:
        Dict with:
            total_hours: Decimal
            total_pay: Decimal
            entries: list of processed entries
            exceeds_monthly_limit: bool
            warnings: list of warning messages
    """
    rules = _get_overtime_rules(for_date)
    rates = rules['rates']
    max_monthly = rules['max_hours_month']

    total_hours = Decimal('0')
    total_pay = Decimal('0')
    entries = []
    warnings = []

    for entry in overtime_entries:
        hours = _D(entry.get('hours', 0))
        ot_type = entry.get('type', 'day')

        if hours <= 0:
            continue

        pay = calculate_overtime_pay(basic_salary, hours, ot_type, for_date)
        total_hours += hours
        total_pay += pay

        entries.append({
            'hours': hours,
            'type': ot_type,
            'rate': rates.get(ot_type, Decimal('1')),
            'pay': pay,
        })

    # Check monthly limit
    if total_hours > max_monthly:
        warnings.append(
            f"Overtime exceeds {max_monthly}-hour monthly limit "
            f"(Labor Proclamation 1156/2019, Art. 89). "
            f"Total: {total_hours} hours."
        )

    return {
        'total_hours': total_hours.quantize(Q, rounding=ROUND_HALF_UP),
        'total_pay': total_pay.quantize(Q, rounding=ROUND_HALF_UP),
        'entries': entries,
        'exceeds_monthly_limit': total_hours > max_monthly,
        'warnings': warnings,
    }


def get_overtime_type_label(overtime_type: str, for_date=None) -> str:
    """Get human-readable label for overtime type."""
    rates = get_overtime_rates(for_date)
    labels = {
        'day': f'Regular Day ({rates["day"]}x)',
        'night': f'Night / 10pm-6am ({rates["night"]}x)',
        'holiday': f'Public Holiday ({rates["holiday"]}x)',
        'rest_day_holiday': f'Rest Day + Holiday ({rates["rest_day_holiday"]}x)',
    }
    return labels.get(overtime_type, overtime_type)
