"""
Compliance Scoring Module

Evaluates payroll compliance based on:
  - Timeliness of pension contributions (due by the 15th of the following month)
  - Tax filing deadlines (monthly, due by the 15th)
  - Disbursement timeliness (net pay due within 5 days of month end)

Score: 0-100 (percentage of deadlines met on time)
Status: 'green' (>=80), 'yellow' (50-79), 'red' (<50)
"""

from datetime import date, datetime
from typing import Tuple

# Deadlines (day of month)
PENSION_DEADLINE_DAY = 15
TAX_FILING_DEADLINE_DAY = 15
DISBURSEMENT_DEADLINE_DAYS_AFTER_MONTH_END = 5


def _days_late(deadline: date, actual: date) -> int:
    """Return number of days past the deadline (0 if on time or early)."""
    delta = (actual - deadline).days
    return max(0, delta)


def compute_compliance_score(
    payroll_date: str = None,
    pension_deadline: str = None,
    tax_deadline: str = None,
    disbursement_date: str = None,
) -> Tuple[float, str]:
    """
    Compute a compliance score based on deadline adherence.

    Args:
        payroll_date: Date payroll was processed (YYYY-MM-DD), defaults to today
        pension_deadline: Pension contribution deadline (YYYY-MM-DD), defaults to 15th of next month
        tax_deadline: Tax filing deadline (YYYY-MM-DD), defaults to 15th of next month
        disbursement_date: Date disbursement was made (YYYY-MM-DD), defaults to today

    Returns:
        Tuple of (score: float, status: str)
            score: 0.0 to 100.0
            status: 'green', 'yellow', or 'red'
    """
    today = date.today()

    # Parse dates
    try:
        payroll_dt = datetime.strptime(payroll_date, '%Y-%m-%d').date() if payroll_date else today
    except (ValueError, TypeError):
        payroll_dt = today

    # Pension deadline: 15th of the month following payroll
    if pension_deadline:
        try:
            pension_dl = datetime.strptime(pension_deadline, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pension_dl = _default_pension_deadline(payroll_dt)
    else:
        pension_dl = _default_pension_deadline(payroll_dt)

    # Tax filing deadline: 15th of the month following payroll
    if tax_deadline:
        try:
            tax_dl = datetime.strptime(tax_deadline, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            tax_dl = _default_tax_deadline(payroll_dt)
    else:
        tax_dl = _default_tax_deadline(payroll_dt)

    # Disbursement date
    if disbursement_date:
        try:
            disb_dt = datetime.strptime(disbursement_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            disb_dt = today
    else:
        disb_dt = today

    # Score each category (100 if on time, decreasing with lateness)
    pension_score = _deadline_score(pension_dl, today)
    tax_score = _deadline_score(tax_dl, today)
    disbursement_score = _disbursement_score(payroll_dt, disb_dt)

    # Weighted average: pension 40%, tax 40%, disbursement 20%
    total_score = (pension_score * 0.4 + tax_score * 0.4 + disbursement_score * 0.2)
    total_score = round(min(100.0, max(0.0, total_score)), 1)

    status = _status_from_score(total_score)
    return total_score, status


def _default_pension_deadline(payroll_date: date) -> date:
    """Pension due by the 15th of the month following payroll."""
    if payroll_date.month == 12:
        return date(payroll_date.year + 1, 1, PENSION_DEADLINE_DAY)
    return date(payroll_date.year, payroll_date.month + 1, PENSION_DEADLINE_DAY)


def _default_tax_deadline(payroll_date: date) -> date:
    """Tax filing due by the 15th of the month following payroll."""
    if payroll_date.month == 12:
        return date(payroll_date.year + 1, 1, TAX_FILING_DEADLINE_DAY)
    return date(payroll_date.year, payroll_date.month + 1, TAX_FILING_DEADLINE_DAY)


def _deadline_score(deadline: date, actual: date) -> float:
    """
    Score 100 if deadline not yet passed or met on time.
    Deduct 10 points per day late, minimum 0.
    """
    days_late = _days_late(deadline, actual)
    return max(0.0, 100.0 - days_late * 10.0)


def _disbursement_score(payroll_date: date, disbursement_date: date) -> float:
    """
    Score based on disbursement within 5 days of month end.
    """
    # Last day of payroll month
    if payroll_date.month == 12:
        month_end = date(payroll_date.year + 1, 1, 1)
    else:
        month_end = date(payroll_date.year, payroll_date.month + 1, 1)
    # Deadline = month_end + 5 days
    from datetime import timedelta
    deadline = month_end + timedelta(days=DISBURSEMENT_DEADLINE_DAYS_AFTER_MONTH_END)
    days_late = _days_late(deadline, disbursement_date)
    return max(0.0, 100.0 - days_late * 10.0)


def _status_from_score(score: float) -> str:
    """Convert numeric score to status label."""
    if score >= 80:
        return 'green'
    elif score >= 50:
        return 'yellow'
    else:
        return 'red'


def get_status_message(status: str) -> str:
    """
    Get a human-readable status message.

    Args:
        status: 'green', 'yellow', or 'red'

    Returns:
        Human-readable message string
    """
    messages = {
        'green': 'Compliant / ተገቢ — All deadlines met or on track.',
        'yellow': 'At Risk / አደጋ ላይ — Some deadlines approaching or recently missed.',
        'red': 'Non-Compliant / ያለግባት — Multiple deadlines missed. Action required.',
    }
    return messages.get(status, 'Unknown / ያልታወቀ')
