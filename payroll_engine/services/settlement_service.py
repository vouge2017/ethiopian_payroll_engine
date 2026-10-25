"""
Settlement Service

Calculates final settlements for terminated employees.
Extracted from main.py to enable:
- Reuse (correction runs, re-processing)
- Testing (unit test without Flask context)
- Clarity (business logic separate from HTTP handling)
"""

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from payroll_engine import constants as _constants
from payroll_engine.leave import LeaveType
from payroll_engine.models import Company, Employee, EmployeeDeduction, FinalSettlement, LeaveBalance
from payroll_engine.pension import employee_pension
from payroll_engine.severance import calculate_severance
from payroll_engine.tax import calculate_tax

Q = Decimal('0.01')

# How severance, pay in lieu of notice and leave encashment are taxed.
# 'final_month_aggregate': add them to the taxable employment income of the
# month they are received (the final month) and apply the normal monthly
# brackets once. Adviser 2026-10-25 (Q2 ACCEPTED as the statutory default):
# taxable termination payments are aggregated with other taxable employment
# income in the month received (Proc. 979/2016 Arts 10, 12; withholding
# Art 88), unless a specific exemption or rule applies. Rates per Proc.
# 1395/2025. Not a confirmation that every directive was reviewed
# (docs/decisions/2026-10-25-settlement-rules.md).
SETTLEMENT_LUMP_SUM_TAX_METHOD = 'final_month_aggregate'
TAX_METHOD_STATUS = 'statutory_default'
TAX_METHOD_NOTE = 'Tax method: statutory default: aggregated in month received (Proc. 979/2016 Arts 10, 12, 88)'
NO_LEAVE_RECORD_WARNING = 'No leave records — enter unused leave days manually'
# Shown on a settlement while the company has not confirmed its leave-pay
# basis and divisor (adviser Q3 PARTIAL, 2026-10-25).
LEAVE_RULE_PENDING_NOTICE = (
    'Leave-pay basis and divisor pending: not yet confirmed by the company (Labour Proc. 1156/2019 Arts 53, 77)'
)
# Why a settlement with leave encashment > 0 cannot be finalized yet.
LEAVE_RULE_BLOCK_MESSAGE = (
    'Choose and confirm your leave-pay basis and divisor (Labour Proc. 1156/2019 Arts 53, 77) before finalizing'
)


class LeaveRuleNotConfirmedError(ValueError):
    """A settlement with leave encashment > 0 was finalized before the company
    confirmed its leave-pay basis and divisor."""

    def __init__(self, message: str = LEAVE_RULE_BLOCK_MESSAGE):
        super().__init__(message)


def _outstanding_breakdown(employee: Employee, end_date: date) -> dict:
    """Split the last working month's pay into basic and allowance components.

    If end_date is the last calendar day of the month, the employee is owed
    the full month. Otherwise the pay is prorated on the inclusive days
    within the final calendar month (Ethiopian 30-day convention), counted
    from the first of that month or the hire date, whichever is later.

    Returns:
        Dict with Decimal basic, allowances, total and int days_worked.
    """
    basic = Decimal(str(employee.basic_salary))
    allowances = Decimal(str(employee.allowances))
    gross = basic + allowances

    # Last calendar day of the month → full salary.
    if end_date.day == calendar.monthrange(end_date.year, end_date.month)[1]:
        return {'basic': basic, 'allowances': allowances, 'total': gross, 'days_worked': 30}

    period_start = end_date.replace(day=1)
    start = getattr(employee, 'start_date', None)
    if start is not None and start > period_start:
        period_start = start
    days_worked = (end_date - period_start).days + 1
    days_worked = max(0, min(days_worked, 30))

    factor = Decimal(str(days_worked)) / Decimal('30')
    total = (gross * factor).quantize(Q)
    prorated_basic = (basic * factor).quantize(Q)
    return {
        'basic': prorated_basic,
        'allowances': total - prorated_basic,
        'total': total,
        'days_worked': days_worked,
    }


def calculate_outstanding_salary(employee: Employee, end_date: date) -> Decimal:
    """Calculate prorated salary for the last working month.

    If the employee works the full month, they get full salary.
    If terminated mid-month, salary is prorated to the last working day,
    counted from the first of that month or the hire date, whichever is later.

    Args:
        employee: Employee record
        end_date: Last working day

    Returns:
        Outstanding salary amount (ETB)
    """
    return _outstanding_breakdown(employee, end_date)['total']


def recorded_unused_leave_days(employee: Employee, end_date: date, company_id: int, db_session=None):
    """Unused annual leave days from the employee's LeaveBalance record.

    The leave year is the Gregorian calendar year of ``end_date``, because
    that is the key every LeaveBalance writer in the app uses (leave
    approval, accrual). Returns ``None`` when there is no record (or no
    session to look one up), never an assumed entitlement.
    """
    if db_session is None or getattr(employee, 'id', None) is None:
        return None
    balance = LeaveBalance.query.filter_by(
        company_id=company_id,
        employee_id=employee.id,
        leave_type=LeaveType.ANNUAL,
        year=end_date.year,
    ).first()
    if balance is None:
        return None
    return Decimal(str(balance.remaining))


def resolve_unused_leave_days(
    employee: Employee, end_date: date, company_id: int, db_session=None, manual_days=None
) -> dict:
    """Decide how many unused annual-leave days are paid out, and why.

    Order: days the user entered manually, then the LeaveBalance record.
    With neither, 0 days are paid and a warning is returned. Full annual
    entitlement is never assumed (PLAN.md R3).

    Returns:
        Dict with Decimal ``days``, ``source`` ('manual' | 'leave_record' |
        'none'), ``recorded_days`` (Decimal or None) and ``warnings`` (list).
    """
    warnings = []
    recorded = recorded_unused_leave_days(employee, end_date, company_id, db_session)

    if manual_days is not None:
        days = Decimal(str(manual_days))
        if not days.is_finite() or days < 0:
            raise ValueError('Unused leave days must be zero or more.')
        if recorded is not None and recorded != days:
            warnings.append(
                f'Unused leave entered manually ({days} days) differs from the leave record ({recorded} days). '
                'The manual figure was used.'
            )
        return {'days': days, 'source': 'manual', 'recorded_days': recorded, 'warnings': warnings}

    if recorded is not None:
        return {
            'days': max(Decimal('0'), recorded),
            'source': 'leave_record',
            'recorded_days': recorded,
            'warnings': warnings,
        }

    warnings.append(NO_LEAVE_RECORD_WARNING)
    return {'days': Decimal('0'), 'source': 'none', 'recorded_days': None, 'warnings': warnings}


def validate_leave_rate_settings(basis, divisor) -> tuple[str, int]:
    """Check a leave daily-rate basis and divisor; return them normalised.

    Raises ValueError for an unknown basis or a divisor outside 1-31.
    """
    if basis not in _constants.LEAVE_RATE_BASES:
        raise ValueError(f'Unknown leave daily-rate basis: {basis!r}')
    try:
        divisor_int = int(divisor)
    except (TypeError, ValueError):
        raise ValueError('Leave daily-rate divisor must be a whole number of days.') from None
    if (
        str(divisor).strip() != str(divisor_int)
        or not _constants.LEAVE_RATE_DIVISOR_MIN <= divisor_int <= _constants.LEAVE_RATE_DIVISOR_MAX
    ):
        raise ValueError(
            f'Leave daily-rate divisor must be a whole number from '
            f'{_constants.LEAVE_RATE_DIVISOR_MIN} to {_constants.LEAVE_RATE_DIVISOR_MAX}.'
        )
    return basis, divisor_int


def company_leave_rate_settings(company_id: int, db_session=None) -> tuple[str, int]:
    """The company's leave daily-rate basis and divisor (defaults if unset or no session)."""
    basis = _constants.DEFAULT_LEAVE_RATE_BASIS
    divisor = _constants.DEFAULT_LEAVE_RATE_DIVISOR
    if db_session is not None and company_id is not None:
        company = db_session.get(Company, company_id)
        if company is not None:
            basis = company.leave_rate_basis or basis
            divisor = company.leave_rate_divisor or divisor
    return validate_leave_rate_settings(basis, divisor)


def company_leave_rule_confirmation(company_id: int, db_session=None) -> dict:
    """Whether the company has confirmed its leave-pay basis and divisor.

    Returns ``{'confirmed': bool, 'confirmed_at': datetime | None,
    'basis': str, 'divisor': int}``. No session or no company → unconfirmed
    with the app defaults. The app defaults are never treated as approved.
    """
    basis, divisor = company_leave_rate_settings(company_id, db_session)
    confirmed_at = None
    if db_session is not None and company_id is not None:
        company = db_session.get(Company, company_id)
        if company is not None:
            confirmed_at = company.leave_rate_confirmed_at
    return {'confirmed': confirmed_at is not None, 'confirmed_at': confirmed_at, 'basis': basis, 'divisor': divisor}


def settlement_finalize_block(calc: dict) -> str | None:
    """Why this calculated settlement may not be finalized, or None.

    Blocks only when leave encashment > 0 and the company has not confirmed
    its leave-pay basis and divisor. Previews may still show the figures.
    """
    leave = (calc.get('calculation_details') or {}).get('leave') or {}
    if Decimal(str(calc.get('leave_encashment') or '0')) > 0 and not leave.get('rule_confirmed'):
        return LEAVE_RULE_BLOCK_MESSAGE
    return None


def leave_daily_rate_details(employee: Employee, basis=None, divisor=None) -> dict:
    """Daily wage for leave encashment and the components it was built from.

    ``basis``: 'basic_plus_regular_allowances' (default) → (basic + the
    employee's regular monthly allowances on record) / divisor;
    'basic_only' → basic / divisor. ``divisor`` defaults to 30. Uses the full
    monthly figures (not the prorated final month). ``daily_rate`` is
    unrounded; round only the encashment amount.
    """
    basis, divisor = validate_leave_rate_settings(
        basis or _constants.DEFAULT_LEAVE_RATE_BASIS,
        divisor if divisor is not None else _constants.DEFAULT_LEAVE_RATE_DIVISOR,
    )
    basic = Decimal(str(employee.basic_salary))
    allowances = Decimal(str(employee.allowances or 0))
    include_allowances = basis == _constants.LEAVE_RATE_BASIS_BASIC_PLUS_REGULAR_ALLOWANCES
    monthly_base = basic + allowances if include_allowances else basic
    return {
        'basis': basis,
        'basis_label': _constants.LEAVE_RATE_BASIS_LABELS[basis],
        'divisor': divisor,
        'basic_salary': basic,
        'regular_allowances': allowances,
        'allowances_included': include_allowances,
        'monthly_base': monthly_base,
        'daily_rate': monthly_base / Decimal(divisor),
    }


def leave_daily_rate(employee: Employee, basis=None, divisor=None) -> Decimal:
    """Daily wage for leave encashment, unrounded (default (basic + allowances) / 30)."""
    return leave_daily_rate_details(employee, basis, divisor)['daily_rate']


def calculate_leave_encashment(
    employee: Employee, end_date: date, company_id: int, db_session=None, manual_days=None
) -> Decimal:
    """Encashment for unused annual leave, from recorded or entered days only.

    Uses the company's leave daily-rate basis and divisor. No record and no
    manual figure → 0 (see ``resolve_unused_leave_days``).
    """
    days = resolve_unused_leave_days(employee, end_date, company_id, db_session, manual_days)['days']
    basis, divisor = company_leave_rate_settings(company_id, db_session)
    return (leave_daily_rate(employee, basis, divisor) * days).quantize(Q, rounding=ROUND_HALF_UP)


def _s(value: Decimal) -> str:
    """Money as a 2-decimal string for JSON."""
    return str(Decimal(value).quantize(Q, rounding=ROUND_HALF_UP))


def _money(value, field: str) -> Decimal:
    d = Decimal(str(value if value is not None else '0'))
    if not d.is_finite() or d < 0:
        raise ValueError(f'{field} must be zero or more.')
    return d.quantize(Q, rounding=ROUND_HALF_UP)


def calculate_settlement(
    employee: Employee,
    termination_reason: str,
    end_date: date,
    company_id: int,
    db_session=None,
    unused_leave_days=None,
    notice_pay=None,
    leave_rate_basis=None,
    leave_rate_divisor=None,
) -> dict:
    """Calculate complete final settlement for a terminated employee.

    This is the SINGLE SOURCE OF TRUTH for settlement calculations.
    All settlement-related code must call this function.

    Taxation (PLAN.md R2): severance, pay in lieu of notice and leave
    encashment are employment income (Proc. 979/2016 Art. 12(1)(c), rates as
    amended by Proc. 1395/2025). With SETTLEMENT_LUMP_SUM_TAX_METHOD =
    'final_month_aggregate' they are added to the final month's taxable
    employment income and taxed once with the normal monthly brackets
    (Art. 10(2): tax on total employment income received for the month).
    Whether the 7 % pension reduces the base follows
    constants.PENSION_DEDUCTED_BEFORE_TAX, read as-is.

    Args:
        employee: Employee record
        termination_reason: One of TerminationReason constants
        end_date: Last working day
        company_id: Company ID
        db_session: SQLAlchemy session for queries
        unused_leave_days: Optional manual unused annual-leave days
            (overrides the leave record).
        notice_pay: Optional pay in lieu of notice (ETB), entered by the user.
        leave_rate_basis / leave_rate_divisor: Override the company's leave
            daily-rate setting (default: read from the Company row; falls
            back to 'basic_plus_regular_allowances' / 30).

    Returns:
        Dict with all settlement components. ``income_tax`` is the total tax
        on the final month; ``tax_on_salary`` is kept as an alias of it for
        older callers. ``calculation_details`` is JSON-safe (money as str).
    """
    if SETTLEMENT_LUMP_SUM_TAX_METHOD != 'final_month_aggregate':
        raise ValueError(f'Unsupported settlement tax method: {SETTLEMENT_LUMP_SUM_TAX_METHOD!r}')

    start = employee.start_date or employee.created_at.date()
    notice_amount = _money(notice_pay, 'Notice pay')

    # 1. Severance
    sev_result = calculate_severance(employee.basic_salary, start, end_date, termination_reason)
    severance_amount = sev_result['final_amount'] if sev_result['eligible'] else Decimal('0')

    # 2. Outstanding salary
    breakdown = _outstanding_breakdown(employee, end_date)
    outstanding_salary = breakdown['total']

    # 3. Leave encashment: recorded or entered days only, never assumed.
    leave = resolve_unused_leave_days(employee, end_date, company_id, db_session, unused_leave_days)
    confirmation = company_leave_rule_confirmation(company_id, db_session)
    leave_rate_basis = leave_rate_basis or confirmation['basis']
    leave_rate_divisor = leave_rate_divisor if leave_rate_divisor is not None else confirmation['divisor']
    rate = leave_daily_rate_details(employee, leave_rate_basis, leave_rate_divisor)
    daily_rate = rate['daily_rate']
    leave_encashment = (daily_rate * leave['days']).quantize(Q, rounding=ROUND_HALF_UP)
    # Confirmed only if the company confirmed exactly the basis/divisor used.
    rule_confirmed = confirmation['confirmed'] and (rate['basis'], rate['divisor']) == (
        confirmation['basis'],
        confirmation['divisor'],
    )
    warnings = list(leave['warnings'])
    if leave_encashment > 0 and not rule_confirmed:
        warnings.append(LEAVE_RULE_BLOCK_MESSAGE + '. This figure is a preview only.')

    # 4. Pension deduction on the prorated basic share of the final month
    # (pension is on basic salary only; lump sums carry none).
    pension_ded = employee_pension(breakdown['basic'])
    pension_off_base = pension_ded if _constants.PENSION_DEDUCTED_BEFORE_TAX else Decimal('0')

    # 5. Tax: salary + severance + notice pay + leave encashment, one month.
    lump_sums = severance_amount + notice_amount + leave_encashment
    salary_base = max(Decimal('0'), outstanding_salary - pension_off_base)
    taxable_income = max(Decimal('0'), outstanding_salary + lump_sums - pension_off_base)
    tax_salary_only = calculate_tax(salary_base)
    income_tax = calculate_tax(taxable_income)
    tax_on_termination_payments = income_tax - tax_salary_only

    # 6. Pending deductions (active loans, cost-sharing, etc.)
    pending_deductions = Decimal('0')
    deduction_details = []

    if db_session:
        active_deductions = EmployeeDeduction.query.filter_by(
            employee_id=employee.id, company_id=company_id, is_active=True
        ).all()

        for ded in active_deductions:
            remaining = ded.remaining_balance or ded.amount
            pending_deductions += remaining
            deduction_details.append(
                {
                    'type': ded.deduction_type,
                    'label': ded.label,
                    'amount': str(remaining),
                }
            )

    # 7. Calculate totals
    total_earnings = outstanding_salary + severance_amount + notice_amount + leave_encashment
    total_deductions = pension_ded + income_tax + pending_deductions
    net_final = total_earnings - total_deductions

    calculation_details = {
        'tax_method': SETTLEMENT_LUMP_SUM_TAX_METHOD,
        'tax_method_status': TAX_METHOD_STATUS,
        'tax_method_note': TAX_METHOD_NOTE,
        'pending_confirmation': None if rule_confirmed else LEAVE_RULE_PENDING_NOTICE,
        'pension_deducted_before_tax': bool(_constants.PENSION_DEDUCTED_BEFORE_TAX),
        'taxable_lines': [
            {'code': 'outstanding_salary', 'label': 'Outstanding salary', 'amount': _s(outstanding_salary)},
            {'code': 'severance', 'label': 'Severance pay', 'amount': _s(severance_amount)},
            {'code': 'notice_pay', 'label': 'Pay in lieu of notice', 'amount': _s(notice_amount)},
            {'code': 'leave_encashment', 'label': 'Leave encashment', 'amount': _s(leave_encashment)},
        ],
        'pension_off_tax_base': _s(pension_off_base),
        'taxable_income': _s(taxable_income),
        'tax_salary_only': _s(tax_salary_only),
        'tax_on_termination_payments': _s(tax_on_termination_payments),
        'income_tax': _s(income_tax),
        'leave': {
            'unused_days': str(leave['days']),
            'source': leave['source'],
            'recorded_days': None if leave['recorded_days'] is None else str(leave['recorded_days']),
            'leave_year': end_date.year,
            'daily_rate': str(daily_rate.quantize(Q, rounding=ROUND_HALF_UP)),
            'daily_rate_unrounded': str(daily_rate.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)),
            'rate_basis': rate['basis'],
            'rate_basis_label': rate['basis_label'],
            'rate_divisor': rate['divisor'],
            'rate_monthly_base': _s(rate['monthly_base']),
            'rate_components': [
                {'code': 'basic_salary', 'label': 'Basic salary', 'amount': _s(rate['basic_salary']), 'included': True},
                {
                    'code': 'regular_allowances',
                    'label': 'Regular allowances',
                    'amount': _s(rate['regular_allowances']),
                    'included': rate['allowances_included'],
                },
            ],
            'rule_confirmed': rule_confirmed,
            'rule_confirmed_at': (
                confirmation['confirmed_at'].isoformat() if rule_confirmed and confirmation['confirmed_at'] else None
            ),
            'rate_formula': (
                f'{rate["basis_label"]} / {rate["divisor"]} = daily rate; '
                'daily rate x unused days, rounded once to 0.01'
            ),
        },
        'warnings': warnings,
    }

    return {
        'severance': sev_result,
        'severance_amount': severance_amount,
        'outstanding_salary': outstanding_salary,
        'notice_pay': notice_amount,
        'leave_encashment': leave_encashment,
        'unused_leave_days': leave['days'],
        'leave_days_source': leave['source'],
        'pension_deduction': pension_ded,
        'taxable_income': taxable_income,
        'tax_salary_only': tax_salary_only,
        'tax_on_termination_payments': tax_on_termination_payments,
        'income_tax': income_tax,
        'tax_on_salary': income_tax,
        'pending_deductions': pending_deductions,
        'deduction_details': deduction_details,
        'total_earnings': total_earnings,
        'total_deductions': total_deductions,
        'net_final_payment': net_final,
        'warnings': warnings,
        'calculation_details': calculation_details,
        'start_date': start,
        'end_date': end_date,
        'years_of_service': sev_result['years_of_service'],
    }


def create_settlement_record(
    employee: Employee,
    termination_reason: str,
    end_date: date,
    company_id: int,
    created_by: int,
    db_session,
    unused_leave_days=None,
    notice_pay=None,
) -> FinalSettlement:
    """Calculate and persist a FinalSettlement record.

    This is the ONLY way to create a settlement record.
    It calculates everything, creates the record, and returns it.

    Args:
        employee: Employee record
        termination_reason: One of TerminationReason constants
        end_date: Last working day
        company_id: Company ID
        created_by: User ID creating the settlement
        db_session: SQLAlchemy session
        unused_leave_days: Optional manual unused annual-leave days
        notice_pay: Optional pay in lieu of notice (ETB)

    Returns:
        FinalSettlement record (already added to session, not committed)

    Raises:
        LeaveRuleNotConfirmedError: leave encashment > 0 and the company has
            not confirmed its leave-pay basis and divisor. Nothing is added.
    """
    calc = calculate_settlement(
        employee,
        termination_reason,
        end_date,
        company_id,
        db_session,
        unused_leave_days=unused_leave_days,
        notice_pay=notice_pay,
    )
    block = settlement_finalize_block(calc)
    if block:
        raise LeaveRuleNotConfirmedError(block)

    settlement = FinalSettlement(
        company_id=company_id,
        employee_id=employee.id,
        termination_reason=termination_reason,
        start_date=calc['start_date'],
        end_date=end_date,
        years_of_service=calc['years_of_service'],
        outstanding_salary=calc['outstanding_salary'],
        severance_pay=calc['severance_amount'],
        notice_pay=calc['notice_pay'],
        leave_encashment=calc['leave_encashment'],
        total_earnings=calc['total_earnings'],
        pension_deduction=calc['pension_deduction'],
        taxable_income=calc['taxable_income'],
        tax_on_salary=calc['income_tax'],
        pending_deductions=calc['pending_deductions'],
        deduction_details=calc['deduction_details'],
        calculation_details=calc['calculation_details'],
        total_deductions=calc['total_deductions'],
        net_final_payment=calc['net_final_payment'],
        payment_method=employee.bank_account or employee.bank_or_telebirr or 'Cash',
        created_by=created_by,
    )
    db_session.add(settlement)
    return settlement
