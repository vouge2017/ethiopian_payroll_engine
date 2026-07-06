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

from typing import Tuple

# Default fallback rates
DEFAULT_EMPLOYEE_RATE = 0.07
DEFAULT_EMPLOYER_RATE = 0.11


def _get_rates(for_date=None):
    """
    Fetch pension rates from the database.
    Falls back to hardcoded defaults if no TaxRule exists.

    Returns:
        (employee_rate: float, employer_rate: float)
    """
    try:
        from payroll_engine.models import TaxRule
        rule = TaxRule.get_active_rule(for_date)
        if rule:
            return rule.pension_employee_rate, rule.pension_employer_rate
    except Exception:
        pass

    return DEFAULT_EMPLOYEE_RATE, DEFAULT_EMPLOYER_RATE


def employee_pension(basic_salary: float, for_date=None) -> float:
    """
    Calculate employee's monthly pension contribution (default 7%).

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Employee pension contribution in ETB
    """
    if basic_salary <= 0:
        return 0.0
    rate, _ = _get_rates(for_date)
    return round(basic_salary * rate, 2)


def employer_pension(basic_salary: float, for_date=None) -> float:
    """
    Calculate employer's monthly pension contribution (default 11%).

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Employer pension contribution in ETB
    """
    if basic_salary <= 0:
        return 0.0
    _, rate = _get_rates(for_date)
    return round(basic_salary * rate, 2)


def total_pension(basic_salary: float, for_date=None) -> float:
    """
    Total pension contribution (employee + employer).

    Args:
        basic_salary: Monthly basic salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Combined pension contribution in ETB
    """
    return round(employee_pension(basic_salary, for_date) + employer_pension(basic_salary, for_date), 2)
