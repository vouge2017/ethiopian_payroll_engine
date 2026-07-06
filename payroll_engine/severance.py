"""
Ethiopian Severance Pay Calculator

Labor Proclamation No. 1156/2019, Articles 40-42:

Formula: monthly_salary × years_of_service
Cap: 12 months of salary (Art. 42)
Prorated for partial years: (monthly_salary / 365) × days_of_service

Applies to:
    - Termination without cause
    - Redundancy
    - Mutual agreement

Does NOT apply to:
    - Resignation
    - Termination for cause (theft, gross misconduct, repeated violation)
"""

from datetime import date, datetime
from typing import Optional

MAX_SEVERANCE_MONTHS = 12  # Art. 42 cap


class TerminationReason:
    RESIGNATION = 'resignation'
    TERMINATION_FOR_CAUSE = 'termination_for_cause'
    REDUNDANCY = 'redundancy'
    MUTUAL_AGREEMENT = 'mutual_agreement'

    SEVERANCE_ELIGIBLE = {REDUNDANCY, MUTUAL_AGREEMENT}
    SEVERANCE_INELIGIBLE = {RESIGNATION, TERMINATION_FOR_CAUSE}

    ALL = {RESIGNATION, TERMINATION_FOR_CAUSE, REDUNDANCY, MUTUAL_AGREEMENT}


def calculate_years_of_service(start_date, end_date) -> float:
    """
    Calculate years of service as a decimal.

    Args:
        start_date: Employment start date (date object or YYYY-MM-DD string)
        end_date: Termination/last working date (date object or YYYY-MM-DD string)

    Returns:
        Years of service as float (e.g., 5.5 for 5 years and 6 months)
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    if end_date <= start_date:
        return 0.0

    delta = end_date - start_date
    return round(delta.days / 365.25, 2)


def calculate_severance(monthly_salary: float, start_date, end_date,
                        termination_reason: str) -> dict:
    """
    Calculate severance pay for a terminated employee.

    Args:
        monthly_salary: Monthly basic salary in ETB
        start_date: Employment start date
        end_date: Last working date
        termination_reason: One of TerminationReason constants

    Returns:
        Dict with:
            eligible: bool (whether severance applies)
            years_of_service: float
            calculated_amount: float (before cap)
            capped_amount: float (after 12-month cap)
            final_amount: float (what the employee receives)
            reason: explanation string
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    years = calculate_years_of_service(start_date, end_date)

    # Check eligibility
    if termination_reason in TerminationReason.SEVERANCE_INELIGIBLE:
        return {
            'eligible': False,
            'years_of_service': years,
            'calculated_amount': 0.0,
            'capped_amount': 0.0,
            'final_amount': 0.0,
            'reason': _ineligibility_reason(termination_reason),
        }

    if termination_reason not in TerminationReason.ALL:
        return {
            'eligible': False,
            'years_of_service': years,
            'calculated_amount': 0.0,
            'capped_amount': 0.0,
            'final_amount': 0.0,
            'reason': f"Unknown termination reason: '{termination_reason}'",
        }

    # Calculate
    calculated = monthly_salary * years
    cap = monthly_salary * MAX_SEVERANCE_MONTHS
    capped = min(calculated, cap)
    final = round(capped, 2)

    return {
        'eligible': True,
        'years_of_service': years,
        'calculated_amount': round(calculated, 2),
        'capped_amount': round(cap, 2),
        'final_amount': final,
        'reason': _calculation_explanation(monthly_salary, years, calculated, cap, final),
    }


def _ineligibility_reason(reason: str) -> str:
    if reason == TerminationReason.RESIGNATION:
        return "Resignation — no severance payable (Labor Proclamation 1156/2019, Art. 40)"
    elif reason == TerminationReason.TERMINATION_FOR_CAUSE:
        return "Termination for cause — no severance payable (Labor Proclamation 1156/2019, Art. 40)"
    return f"Not eligible for severance: {reason}"


def _calculation_explanation(salary, years, calculated, cap, final) -> str:
    """Generate plain-language explanation of severance calculation."""
    lines = [
        f"Severance calculation (Labor Proclamation 1156/2019, Art. 40-42):",
        f"  Monthly salary: ETB {salary:,.2f}",
        f"  Years of service: {years}",
        f"  Formula: ETB {salary:,.2f} × {years} = ETB {calculated:,.2f}",
    ]
    if calculated > cap:
        lines.append(f"  Capped at {MAX_SEVERANCE_MONTHS} months: ETB {cap:,.2f}")
    lines.append(f"  Severance payable: ETB {final:,.2f}")
    return "\n".join(lines)


def format_severance_for_payslip(result: dict) -> dict:
    """
    Format severance result for inclusion in a payslip.

    Returns:
        Dict with label, amount, and explanation suitable for payslip display.
    """
    if not result['eligible']:
        return None

    return {
        'label': 'Severance Pay / የስራ ማቆያ ክፍያ',
        'amount': result['final_amount'],
        'explanation': result['reason'],
    }
