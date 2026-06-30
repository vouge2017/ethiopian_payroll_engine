"""
Ethiopian Pension Contribution Calculator

Based on Ethiopian pension law:
  - Employee contribution: 7% of basic salary
  - Employer contribution: 11% of basic salary

Applies to the basic salary only (not gross). 
Minimum contribution floor: ETB 0 (no negative).
"""

from typing import Tuple

EMPLOYEE_RATE = 0.07
EMPLOYER_RATE = 0.11


def employee_pension(basic_salary: float) -> float:
    """
    Calculate employee's monthly pension contribution (7%).

    Args:
        basic_salary: Monthly basic salary in ETB

    Returns:
        Employee pension contribution in ETB
    """
    if basic_salary <= 0:
        return 0.0
    return round(basic_salary * EMPLOYEE_RATE, 2)


def employer_pension(basic_salary: float) -> float:
    """
    Calculate employer's monthly pension contribution (11%).

    Args:
        basic_salary: Monthly basic salary in ETB

    Returns:
        Employer pension contribution in ETB
    """
    if basic_salary <= 0:
        return 0.0
    return round(basic_salary * EMPLOYER_RATE, 2)


def total_pension(basic_salary: float) -> float:
    """
    Total pension contribution (employee + employer).

    Args:
        basic_salary: Monthly basic salary in ETB

    Returns:
        Combined pension contribution in ETB
    """
    return round(employee_pension(basic_salary) + employer_pension(basic_salary), 2)
