"""
Ethiopian Pension Contribution Calculator

Based on Ethiopian pension law:
  - Employee contribution: 7% of basic salary
  - Employer contribution: 11% of basic salary
  - Source: Private Organizations Employees Social Security Proclamation No. 715/2011
    Article 43 — Contribution Rates

Applies to the basic salary only (not gross).
Minimum contribution floor: ETB 0 (no negative).

Rates are configurable via the TaxRule database model.
When no database rule exists, falls back to hardcoded defaults.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Tuple

# Quantizer for 2 decimal places
Q = Decimal('0.01')

# Default fallback rates
DEFAULT_EMPLOYEE_RATE = Decimal('0.07')
DEFAULT_EMPLOYER_RATE = Decimal('0.11')

# Cache for pension rates with TTL (5 minutes)
# Call invalidate_pension_cache() after updating TaxRule records
_rates_cache = {}
_rates_cache_ttl = 300  # seconds
_rates_cache_timestamps = {}


def invalidate_pension_cache():
    """Clear the pension rate cache. Call after updating TaxRule records."""
    _rates_cache.clear()
    _rates_cache_timestamps.clear()


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _get_rates(for_date=None) -> Tuple[Decimal, Decimal]:
    """
    Fetch pension rates from the database.
    Falls back to hardcoded defaults if no TaxRule exists.
    Caches result to avoid repeated DB queries.

    Returns:
        (employee_rate: Decimal, employer_rate: Decimal)
    """
    cache_key = str(for_date) if for_date else 'default'
    import time
    now = time.time()
    if cache_key in _rates_cache:
        cached_time = _rates_cache_timestamps.get(cache_key, 0)
        if now - cached_time < _rates_cache_ttl:
            return _rates_cache[cache_key]
        # Cache expired — invalidate
        del _rates_cache[cache_key]
        del _rates_cache_timestamps[cache_key]

    try:
        from payroll_engine.models import TaxRule
        rule = TaxRule.get_active_rule(for_date)
        if rule:
            result = _D(rule.pension_employee_rate), _D(rule.pension_employer_rate)
            _rates_cache[cache_key] = result
            _rates_cache_timestamps[cache_key] = now
            return result
    except Exception:
        pass

    result = (DEFAULT_EMPLOYEE_RATE, DEFAULT_EMPLOYER_RATE)
    _rates_cache[cache_key] = result
    _rates_cache_timestamps[cache_key] = now
    return result


def employee_pension(basic_salary, for_date=None) -> Decimal:
    """
    Calculate employee's monthly pension contribution (default 7%).

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Employee pension contribution in ETB, as Decimal
    """
    basic_salary = _D(basic_salary)
    if basic_salary <= 0:
        return Decimal('0')
    rate, _ = _get_rates(for_date)
    return (basic_salary * rate).quantize(Q, rounding=ROUND_HALF_UP)


def employer_pension(basic_salary, for_date=None) -> Decimal:
    """
    Calculate employer's monthly pension contribution (default 11%).

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Employer pension contribution in ETB, as Decimal
    """
    basic_salary = _D(basic_salary)
    if basic_salary <= 0:
        return Decimal('0')
    _, rate = _get_rates(for_date)
    return (basic_salary * rate).quantize(Q, rounding=ROUND_HALF_UP)


def total_pension(basic_salary, for_date=None) -> Decimal:
    """
    Total pension contribution (employee + employer).

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Combined pension contribution in ETB, as Decimal
    """
    return (employee_pension(basic_salary, for_date) + employer_pension(basic_salary, for_date)).quantize(Q, rounding=ROUND_HALF_UP)
