"""
Ethiopian Pension Contribution Calculator

Based on Ethiopian pension law:
  - Employee contribution: 7% of basic salary
  - Employer contribution: 11% of basic salary
  - Source: Private Organizations Employees Social Security Proclamation No. 1268/2022
    (repealed No. 715/2011)
  - No statutory pension contribution ceiling exists in Ethiopian law.
    Contributions are calculated on full basic salary with no cap.

Applies to the basic salary only (not gross).
Minimum contribution floor: ETB 0 (no negative).

Rates and optional ceiling are configurable via the TaxRule database model.
When no database rule exists, falls back to hardcoded defaults (no ceiling).
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Quantizer for 2 decimal places
Q = Decimal('0.01')

# Default fallback rates
DEFAULT_EMPLOYEE_RATE = Decimal('0.07')
DEFAULT_EMPLOYER_RATE = Decimal('0.11')

# No default ceiling — Ethiopian law does not specify one.
# If a ceiling is introduced in the future, set it via TaxRule.rules_json.
DEFAULT_CEILING = None  # None means no ceiling

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


def _get_rates(for_date=None) -> tuple[Decimal, Decimal, Decimal | None]:
    """
    Fetch pension rates and optional ceiling from the database.
    Falls back to hardcoded defaults if no TaxRule exists.
    Caches result to avoid repeated DB queries.

    Returns:
        (employee_rate, employer_rate, ceiling)
        ceiling is None when there is no cap.
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
            pension_cfg = rule.rules_json.get('pension', {})
            emp_rate = _D(pension_cfg.get('employee_rate', DEFAULT_EMPLOYEE_RATE))
            empr_rate = _D(pension_cfg.get('employer_rate', DEFAULT_EMPLOYER_RATE))
            raw_ceiling = pension_cfg.get('ceiling')
            ceiling = _D(raw_ceiling) if raw_ceiling is not None else None
            result = (emp_rate, empr_rate, ceiling)
            _rates_cache[cache_key] = result
            _rates_cache_timestamps[cache_key] = now
            return result
    except Exception:
        pass

    result = (DEFAULT_EMPLOYEE_RATE, DEFAULT_EMPLOYER_RATE, DEFAULT_CEILING)
    _rates_cache[cache_key] = result
    _rates_cache_timestamps[cache_key] = now
    return result


def _insurable_salary(basic_salary: Decimal, ceiling: Decimal | None) -> Decimal:
    """Return the salary amount on which pension is calculated.

    If a ceiling is configured, pension is capped at that amount.
    If no ceiling (None), pension applies to the full basic salary.
    """
    if ceiling is not None and ceiling > 0:
        return min(basic_salary, ceiling)
    return basic_salary


def employee_pension(basic_salary, for_date=None) -> Decimal:
    """
    Calculate employee's monthly pension contribution (default 7%).

    If a ceiling is configured in the active TaxRule, contributions are
    capped at that amount. Otherwise, applies to the full basic salary.

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Employee pension contribution in ETB, as Decimal
    """
    basic_salary = _D(basic_salary)
    if basic_salary <= 0:
        return Decimal('0')
    rate, _, ceiling = _get_rates(for_date)
    insurable = _insurable_salary(basic_salary, ceiling)
    return (insurable * rate).quantize(Q, rounding=ROUND_HALF_UP)


def employer_pension(basic_salary, for_date=None) -> Decimal:
    """
    Calculate employer's monthly pension contribution (default 11%).

    If a ceiling is configured in the active TaxRule, contributions are
    capped at that amount. Otherwise, applies to the full basic salary.

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Employer pension contribution in ETB, as Decimal
    """
    basic_salary = _D(basic_salary)
    if basic_salary <= 0:
        return Decimal('0')
    _, rate, ceiling = _get_rates(for_date)
    insurable = _insurable_salary(basic_salary, ceiling)
    return (insurable * rate).quantize(Q, rounding=ROUND_HALF_UP)


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
