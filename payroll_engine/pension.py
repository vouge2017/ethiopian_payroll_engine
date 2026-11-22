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

Rates and optional ceiling are configured via the TaxRule database model.
Missing or incomplete rates stop calculation.
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

# Kept for compatibility with callers that invalidate old cache state.
_rates_cache = {}
_rates_cache_ttl = 300  # seconds
_rates_cache_timestamps = {}


def invalidate_pension_cache():
    """Clear the pension rate cache. Call after updating TaxRule records."""
    _rates_cache.clear()
    _rates_cache_timestamps.clear()


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal.

    Non-finite values (NaN, Infinity) raise ValueError: money must be finite.
    """
    if isinstance(value, Decimal):
        d = value
    else:
        try:
            d = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal('0')
    if not d.is_finite():
        raise ValueError(f'Money value must be finite, got: {d}')
    return d


def _get_rates(for_date=None) -> tuple[Decimal, Decimal, Decimal | None]:
    """
    Fetch pension rates and optional ceiling from the database.
    Missing or invalid rules stop calculation.
    Reads the rule for every lookup so deletion and database failures are visible.

    Returns:
        (employee_rate, employer_rate, ceiling)
        ceiling is None when there is no cap.
    """
    from payroll_engine.rule_errors import MissingPayrollRuleError, active_rule

    rule = active_rule(for_date, 'pension')
    try:
        pension_cfg = rule.rules_json['pension']
        emp_rate = Decimal(str(pension_cfg['employee_rate']))
        empr_rate = Decimal(str(pension_cfg['employer_rate']))
        raw_ceiling = pension_cfg.get('ceiling')
        ceiling = Decimal(str(raw_ceiling)) if raw_ceiling is not None else None
        if any(not rate.is_finite() or not 0 <= rate <= 1 for rate in (emp_rate, empr_rate)):
            raise ValueError
        if ceiling is not None and (not ceiling.is_finite() or ceiling < 0):
            raise ValueError
        result = (emp_rate, empr_rate, ceiling)
    except (TypeError, KeyError, ValueError, InvalidOperation, AttributeError) as exc:
        raise MissingPayrollRuleError(
            'The pension rule for the payroll date is incomplete or invalid. Fix the rule before continuing.'
        ) from exc
    return result


def pension_rates_for_date(for_date=None) -> tuple[Decimal, Decimal]:
    """Return the dated employee and employer pension rates.

    Missing or invalid pension rules propagate from _get_rates; review and
    validation code must not silently substitute a default rate.
    """
    employee_rate, employer_rate, _ceiling = _get_rates(for_date)
    return employee_rate, employer_rate


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
    return (employee_pension(basic_salary, for_date) + employer_pension(basic_salary, for_date)).quantize(
        Q, rounding=ROUND_HALF_UP
    )
