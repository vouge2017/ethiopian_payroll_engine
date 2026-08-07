"""
Compliance Scoring Module

Evaluates payroll compliance based on company-configurable deadlines.

Default deadlines (sensible defaults based on common Ethiopian practice):
  - ERCA tax filing: 25th of following month
  - Pension contribution: 10th of following month (Proclamation 1268/2022, Art. 10(6))
  - Disbursement: 5 days after month end

Companies can override these via Company.compliance_deadlines JSON field.
Additional filing types (PSSA, custom) can be added per company.

Score: 0-100 (percentage of deadlines met on time)
Status: 'green' (>=80), 'yellow' (50-79), 'red' (<50)
"""

from datetime import date, datetime, timedelta

# Sensible defaults — companies override via Company.compliance_deadlines
DEFAULT_ERCA_FILING_DAY = 25
DEFAULT_PENSION_DEADLINE_DAY = 10
DEFAULT_DISBURSEMENT_DAYS = 5
DEFAULT_REMINDER_DAYS_BEFORE = 3

# All known filing types with their defaults
FILING_TYPE_DEFAULTS = {
    'erca': {
        'label': 'ERCA Tax Filing',
        'label_am': 'የERCA ግብር ማስገቢያ',
        'day': DEFAULT_ERCA_FILING_DAY,
        'enabled': True,
    },
    'pension': {
        'label': 'Pension Remittance',
        'label_am': 'የጡረታ መዋጮ',
        'day': DEFAULT_PENSION_DEADLINE_DAY,
        'enabled': True,
    },
    'pssa': {
        'label': 'PSSA Contribution',
        'label_am': 'የPSSA መዋጮ',
        'day': 10,
        'enabled': True,
    },
}


def get_company_deadlines(company) -> dict:
    """Get effective deadlines for a company.

    Merges company-specific overrides with defaults.
    Returns dict of filing_type -> {label, day, enabled, ...}.
    """
    stored = company.compliance_deadlines if company and company.compliance_deadlines else {}
    result = {}

    for ftype, defaults in FILING_TYPE_DEFAULTS.items():
        cfg = stored.get(ftype, {})
        result[ftype] = {
            'label': cfg.get('label', defaults['label']),
            'label_am': cfg.get('label_am', defaults['label_am']),
            'day': cfg.get('day', defaults['day']),
            'enabled': cfg.get('enabled', defaults['enabled']),
        }

    # Add custom filing types from company config
    for custom in stored.get('custom_deadlines', []):
        ftype = custom.get('name', '').lower().replace(' ', '_')
        if ftype and ftype not in result:
            result[ftype] = {
                'label': custom.get('name', ftype),
                'label_am': custom.get('label_am', ''),
                'day': custom.get('day', 10),
                'enabled': custom.get('enabled', True),
            }

    # Disbursement and reminder settings
    result['_disbursement_days'] = stored.get('disbursement_days', DEFAULT_DISBURSEMENT_DAYS)
    result['_reminder_days_before'] = stored.get('reminder_days_before', DEFAULT_REMINDER_DAYS_BEFORE)

    return result


def get_deadline_for_type(company, filing_type: str, payroll_date: date) -> date | None:
    """Get the deadline date for a specific filing type.

    Args:
        company: Company model instance
        filing_type: 'erca', 'pension', 'pssa', or custom type
        payroll_date: The payroll period date

    Returns:
        Deadline date, or None if filing type not found/disabled
    """
    deadlines = get_company_deadlines(company)
    cfg = deadlines.get(filing_type)

    if not cfg or not cfg.get('enabled', True):
        return None

    day = cfg['day']
    # Deadline is in the month following payroll
    if payroll_date.month == 12:
        target_month = 1
        target_year = payroll_date.year + 1
    else:
        target_month = payroll_date.month + 1
        target_year = payroll_date.year

    # Handle months with fewer days (e.g., day 31 in February)
    import calendar

    max_day = calendar.monthrange(target_year, target_month)[1]
    actual_day = min(day, max_day)

    return date(target_year, target_month, actual_day)


def _days_late(deadline: date, actual: date) -> int:
    """Return number of days past the deadline (0 if on time or early)."""
    delta = (actual - deadline).days
    return max(0, delta)


def compute_compliance_score(
    company=None,
    payroll_date: str | None = None,
    pension_deadline: str | None = None,
    tax_deadline: str | None = None,
    disbursement_date: str | None = None,
) -> tuple[float, str]:
    """
    Compute a compliance score based on deadline adherence.

    Args:
        company: Company instance (reads deadlines from company config)
        payroll_date: Date payroll was processed (YYYY-MM-DD), defaults to today
        pension_deadline: Override pension deadline (YYYY-MM-DD)
        tax_deadline: Override tax deadline (YYYY-MM-DD)
        disbursement_date: Date disbursement was made (YYYY-MM-DD), defaults to today

    Returns:
        Tuple of (score: float, status: str)
    """
    today = date.today()

    try:
        payroll_dt = datetime.strptime(payroll_date, '%Y-%m-%d').date() if payroll_date else today
    except (ValueError, TypeError):
        payroll_dt = today

    deadlines = get_company_deadlines(company) if company else {}

    # Pension deadline
    if pension_deadline:
        try:
            pension_dl = datetime.strptime(pension_deadline, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pension_dl = get_deadline_for_type(company, 'pension', payroll_dt) or _fallback_deadline(
                payroll_dt, DEFAULT_PENSION_DEADLINE_DAY
            )
    else:
        pension_dl = get_deadline_for_type(company, 'pension', payroll_dt) or _fallback_deadline(
            payroll_dt, DEFAULT_PENSION_DEADLINE_DAY
        )

    # ERCA tax filing deadline
    if tax_deadline:
        try:
            tax_dl = datetime.strptime(tax_deadline, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            tax_dl = get_deadline_for_type(company, 'erca', payroll_dt) or _fallback_deadline(
                payroll_dt, DEFAULT_ERCA_FILING_DAY
            )
    else:
        tax_dl = get_deadline_for_type(company, 'erca', payroll_dt) or _fallback_deadline(
            payroll_dt, DEFAULT_ERCA_FILING_DAY
        )

    # Disbursement date
    if disbursement_date:
        try:
            disb_dt = datetime.strptime(disbursement_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            disb_dt = today
    else:
        disb_dt = today

    # Score each category
    pension_score = _deadline_score(pension_dl, today)
    tax_score = _deadline_score(tax_dl, today)
    disbursement_score = _disbursement_score(
        payroll_dt, disb_dt, deadlines.get('_disbursement_days', DEFAULT_DISBURSEMENT_DAYS)
    )

    # Weighted average: pension 40%, tax 40%, disbursement 20%
    total_score = pension_score * 0.4 + tax_score * 0.4 + disbursement_score * 0.2
    total_score = round(min(100.0, max(0.0, total_score)), 1)

    status = _status_from_score(total_score)
    return total_score, status


def _fallback_deadline(payroll_date: date, day: int) -> date:
    """Compute deadline in the month following payroll for a given day."""
    if payroll_date.month == 12:
        return date(payroll_date.year + 1, 1, day)
    return date(payroll_date.year, payroll_date.month + 1, day)


def _deadline_score(deadline: date, actual: date) -> float:
    """Score 100 if deadline not yet passed or met on time. Deduct 10/day late."""
    days_late = _days_late(deadline, actual)
    return max(0.0, 100.0 - days_late * 10.0)


def _disbursement_score(payroll_date: date, disbursement_date: date, days_after: int = 5) -> float:
    """Score based on disbursement within N days of month end."""
    if payroll_date.month == 12:
        month_end = date(payroll_date.year + 1, 1, 1)
    else:
        month_end = date(payroll_date.year, payroll_date.month + 1, 1)
    deadline = month_end + timedelta(days=days_after)
    days_late = _days_late(deadline, disbursement_date)
    return max(0.0, 100.0 - days_late * 10.0)


def _status_from_score(score: float) -> str:
    if score >= 80:
        return 'green'
    elif score >= 50:
        return 'yellow'
    else:
        return 'red'


def get_status_message(status: str) -> str:
    messages = {
        'green': 'Compliant / ተገቢ — All deadlines met or on track.',
        'yellow': 'At Risk / አደጋ ላይ — Some deadlines approaching or recently missed.',
        'red': 'Non-Compliant / ያለግባት — Multiple deadlines missed. Action required.',
    }
    return messages.get(status, 'Unknown / ያልታወቀ')


def get_upcoming_deadlines(company=None, payroll_date: str | None = None) -> dict:
    """Get upcoming compliance deadlines for display on dashboard.

    Returns dict with deadline dates, days remaining, and status color
    for each enabled filing type.
    """
    today = date.today()
    try:
        payroll_dt = datetime.strptime(payroll_date, '%Y-%m-%d').date() if payroll_date else today
    except (ValueError, TypeError):
        payroll_dt = today

    deadlines = get_company_deadlines(company) if company else {}

    def _status(days_left):
        if days_left < 0:
            return 'danger'
        elif days_left <= 3:
            return 'warning'
        return 'success'

    result = {}

    # Built-in filing types
    for ftype in ['erca', 'pension', 'pssa']:
        cfg = deadlines.get(ftype, FILING_TYPE_DEFAULTS.get(ftype, {}))
        if not cfg.get('enabled', True):
            continue

        dl = (
            get_deadline_for_type(company, ftype, payroll_dt)
            if company
            else _fallback_deadline(payroll_dt, cfg.get('day', 10))
        )
        days_left = (dl - today).days

        result[f'{ftype}_deadline'] = dl.isoformat()
        result[f'{ftype}_days_left'] = days_left
        result[f'{ftype}_status'] = _status(days_left)

    # Disbursement
    disb_days = deadlines.get('_disbursement_days', DEFAULT_DISBURSEMENT_DAYS)
    if payroll_dt.month == 12:
        month_end = date(payroll_dt.year + 1, 1, 1)
    else:
        month_end = date(payroll_dt.year, payroll_dt.month + 1, 1)
    disb_dl = month_end + timedelta(days=disb_days)
    disb_days_left = (disb_dl - today).days
    result['disbursement_deadline'] = disb_dl.isoformat()
    result['disbursement_days_left'] = disb_days_left
    result['disbursement_status'] = _status(disb_days_left)

    # Custom filing types
    for ftype, cfg in deadlines.items():
        if ftype.startswith('_') or ftype in ('erca', 'pension', 'pssa'):
            continue
        if not cfg.get('enabled', True):
            continue
        dl = (
            get_deadline_for_type(company, ftype, payroll_dt)
            if company
            else _fallback_deadline(payroll_dt, cfg.get('day', 10))
        )
        if dl:
            days_left = (dl - today).days
            result[f'{ftype}_deadline'] = dl.isoformat()
            result[f'{ftype}_days_left'] = days_left
            result[f'{ftype}_status'] = _status(days_left)

    return result


def get_reminder_candidates(company=None, days_before: int | None = None) -> list:
    """Get filing types that need reminders sent.

    Returns list of dicts: [{filing_type, label, deadline, days_left}, ...]
    for any deadline within the reminder window.
    """
    if days_before is None:
        deadlines = get_company_deadlines(company) if company else {}
        days_before = deadlines.get('_reminder_days_before', DEFAULT_REMINDER_DAYS_BEFORE)

    upcoming = get_upcoming_deadlines(company)
    reminders = []

    deadlines_cfg = get_company_deadlines(company) if company else {}

    for key, value in upcoming.items():
        if not key.endswith('_days_left'):
            continue
        ftype = key.replace('_days_left', '')
        days_left = value

        if 0 < days_left <= days_before:
            cfg = deadlines_cfg.get(ftype, FILING_TYPE_DEFAULTS.get(ftype, {}))
            reminders.append(
                {
                    'filing_type': ftype,
                    'label': cfg.get('label', ftype.upper()),
                    'label_am': cfg.get('label_am', ''),
                    'deadline': upcoming.get(f'{ftype}_deadline'),
                    'days_left': days_left,
                }
            )

    return reminders
