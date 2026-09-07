"""
Ethiopian Pension Contribution Calculator

Based on Ethiopian pension law:
  - Employee contribution: 7% of basic salary
  - Employer contribution: 11% of basic salary

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

    Returns:
        (employee_rate: Decimal, employer_rate: Decimal)
    """
    try:
        from payroll_engine.models import TaxRule
        rule = TaxRule.get_active_rule(for_date)
        if rule:
            return _D(rule.pension_employee_rate), _D(rule.pension_employer_rate)
    except Exception:
        pass

    return DEFAULT_EMPLOYEE_RATE, DEFAULT_EMPLOYER_RATE


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
