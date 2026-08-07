"""
Leave Service

Business logic for leave management.
Extracted from main.py and leave.py to provide a clean API for:
- Leave request/approval workflows
- Balance management
- Integration with payroll (sick leave pay reduction)
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from payroll_engine import db
from payroll_engine.leave import (
    DEFAULT_ANNUAL_BASE,
    DEFAULT_ANNUAL_INCREMENT,
    DEFAULT_SICK_MAX_DAYS,
    DEFAULT_SICK_TIER_1_DAYS,
    DEFAULT_SICK_TIER_2_DAYS,
    LeaveType,
    calculate_sick_leave_pay,
    validate_leave_request,
)
from payroll_engine.models import Employee, Leave, LeaveBalance


def get_or_create_balance(company_id: int, employee_id: int,
                           leave_type: str, year: int,
                           db_session) -> LeaveBalance:
    """Get existing leave balance or create a new one.

    Args:
        company_id: Company ID
        employee_id: Employee ID (integer PK)
        leave_type: Leave type string
        year: Year
        db_session: SQLAlchemy session

    Returns:
        LeaveBalance record
    """
    balance = LeaveBalance.query.filter_by(
        company_id=company_id,
        employee_id=employee_id,
        leave_type=leave_type,
        year=year,
    ).first()

    if not balance:
        balance = LeaveBalance(
            company_id=company_id,
            employee_id=employee_id,
            leave_type=leave_type,
            year=year,
            entitled=0,
            taken=0,
        )
        db_session.add(balance)
        db_session.flush()

    return balance


def accrue_annual_leave(employee: Employee, company_id: int,
                         year: int, db_session) -> LeaveBalance:
    """Accrue annual leave for an employee for the given year.

    Called once per year (or on first access) to set the entitled days.

    Args:
        employee: Employee record
        company_id: Company ID
        year: Year to accrue for
        db_session: SQLAlchemy session

    Returns:
        Updated LeaveBalance record
    """
    balance = get_or_create_balance(
        company_id, employee.id, LeaveType.ANNUAL, year, db_session
    )

    # Only accrue if not already done for this year
    if balance.entitled > 0 and balance.last_accrual_date:
        return balance

    start = employee.start_date or employee.created_at.date()
    years_of_service = (date(year, 12, 31) - start).days // 365

    # Statutory: 14 days + 1 per year, capped at 30
    entitled = DEFAULT_ANNUAL_BASE + (years_of_service * DEFAULT_ANNUAL_INCREMENT)
    entitled = min(entitled, 30)

    # Company policy override
    if balance.company_policy_days and balance.company_policy_days > entitled:
        entitled = balance.company_policy_days

    balance.entitled = entitled
    balance.last_accrual_date = date.today()

    return balance


def get_leave_taken(company_id: int, employee_id: int,
                     leave_type: str, year: int,
                     db_session) -> int:
    """Get total approved leave days for an employee in a year.

    Args:
        company_id: Company ID
        employee_id: Employee ID (integer PK)
        leave_type: Leave type
        year: Year
        db_session: SQLAlchemy session

    Returns:
        Total days taken
    """
    total = db_session.query(
        db.func.sum(Leave.days_requested)
    ).filter(
        Leave.company_id == company_id,
        Leave.employee_id == employee_id,
        Leave.leave_type == leave_type,
        Leave.status == 'approved',
        db.extract('year', Leave.start_date) == year,
    ).scalar()

    return total or 0


def get_leave_balance(employee: Employee, company_id: int,
                       leave_type: str, year: int,
                       db_session) -> dict:
    """Get complete leave balance for an employee.

    This is the SINGLE SOURCE OF TRUTH for leave balance queries.
    Always returns current balance with proper accrual.

    Args:
        employee: Employee record
        company_id: Company ID
        leave_type: Leave type
        year: Year
        db_session: SQLAlchemy session

    Returns:
        Dict with entitled, taken, remaining, and type-specific details
    """
    if leave_type == LeaveType.ANNUAL:
        balance = accrue_annual_leave(employee, company_id, year, db_session)
        taken = get_leave_taken(company_id, employee.id, leave_type, year, db_session)
        balance.taken = taken

        return {
            'leave_type': leave_type,
            'entitled': balance.entitled,
            'taken': taken,
            'remaining': balance.remaining,
            'years_of_service': (date.today() - (employee.start_date or employee.created_at.date())).days // 365,
        }

    elif leave_type == LeaveType.SICK:
        balance = get_or_create_balance(
            company_id, employee.id, leave_type, year, db_session
        )
        # Always derive from Leave table (single source of truth)
        taken = get_leave_taken(
            company_id, employee.id, leave_type, year, db_session
        )
        balance.taken = taken
        daily_rate = (Decimal(str(employee.basic_salary)) + Decimal(str(employee.allowances))) / Decimal('30')
        pay_info = calculate_sick_leave_pay(taken, daily_rate)

        return {
            'leave_type': leave_type,
            'entitled': DEFAULT_SICK_MAX_DAYS,
            'taken': taken,
            'remaining': max(0, DEFAULT_SICK_MAX_DAYS - taken),
            'pay_tiers': pay_info['tiers'],
            'current_tier': pay_info['tier'],
            'current_pay_percentage': pay_info['pay_percentage'],
            'exhausted': pay_info['exhausted'],
        }

    elif leave_type == LeaveType.MATERNITY:
        taken = get_leave_taken(company_id, employee.id, leave_type, year, db_session)
        return {
            'leave_type': leave_type,
            'entitled': 120,
            'taken': taken,
            'remaining': max(0, 120 - taken),
        }

    elif leave_type == LeaveType.PATERNITY or leave_type == LeaveType.SPECIAL:
        taken = get_leave_taken(company_id, employee.id, leave_type, year, db_session)
        return {
            'leave_type': leave_type,
            'entitled': 3,
            'taken': taken,
            'remaining': max(0, 3 - taken),
        }

    return {'leave_type': leave_type, 'entitled': 0, 'taken': 0, 'remaining': 0}


def request_leave(employee: Employee, company_id: int,
                   leave_type: str, start_date: date, end_date: date,
                   reason: str, db_session) -> dict:
    """Create a leave request with validation.

    Args:
        employee: Employee record
        company_id: Company ID
        leave_type: Leave type
        start_date: Start date
        end_date: End date
        reason: Reason (optional)
        db_session: SQLAlchemy session

    Returns:
        Dict with: success, leave (record), errors, warnings
    """
    days_requested = (end_date - start_date).days + 1
    if days_requested <= 0:
        return {'success': False, 'errors': ['End date must be after start date.'], 'warnings': []}

    # Get current balance
    balance = get_leave_balance(employee, company_id, leave_type, date.today().year, db_session)

    # Validate
    validation = validate_leave_request(
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        balance=balance,
        employee_name=employee.name,
    )

    if not validation['valid']:
        return {'success': False, 'errors': validation['errors'], 'warnings': validation.get('warnings', [])}

    # Create request
    leave = Leave(
        company_id=company_id,
        employee_id=employee.id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days_requested=days_requested,
        reason=reason,
        status='pending',
    )
    db_session.add(leave)
    db_session.flush()

    return {
        'success': True,
        'leave': leave,
        'errors': [],
        'warnings': validation.get('warnings', []),
    }


def approve_leave(leave: Leave, approved_by: int, db_session) -> dict:
    """Approve a leave request and update balance.

    Args:
        leave: Leave record
        approved_by: User ID approving
        db_session: SQLAlchemy session

    Returns:
        Dict with: success, message
    """
    if leave.status != 'pending':
        return {'success': False, 'message': 'Leave request is not pending.'}

    leave.status = 'approved'
    leave.approved_by = approved_by
    leave.approved_at = datetime.now(UTC).replace(tzinfo=None)
    db_session.flush()  # Flush so the DB sum below includes this leave

    # Derive balance.taken from the authoritative source (Leave table)
    balance = get_or_create_balance(
        leave.company_id, leave.employee_id,
        leave.leave_type, date.today().year, db_session
    )
    balance.taken = get_leave_taken(
        leave.company_id, leave.employee_id,
        leave.leave_type, date.today().year, db_session
    )

    return {'success': True, 'message': f'Leave approved: {leave.days_requested} days.'}


def reject_leave(leave: Leave, reason: str, db_session) -> dict:
    """Reject a leave request.

    Args:
        leave: Leave record
        reason: Rejection reason
        db_session: SQLAlchemy session

    Returns:
        Dict with: success, message
    """
    if leave.status != 'pending':
        return {'success': False, 'message': 'Leave request is not pending.'}

    if not reason or not reason.strip():
        return {'success': False, 'message': 'Rejection reason is required.'}

    leave.status = 'rejected'
    leave.rejection_reason = reason.strip()

    return {'success': True, 'message': 'Leave request rejected.'}


def get_sick_leave_pay_reduction(employee: Employee, company_id: int,
                                  db_session) -> Decimal:
    """Get the sick leave pay reduction for payroll calculation.

    If an employee has taken more than 30 days of sick leave,
    their pay is reduced according to the tiered system:
    - Days 1-30: 100% pay
    - Days 31-90: 50% pay
    - Days 91-180: 0% pay

    This function returns the AMOUNT TO DEDUCT from the employee's
    normal salary for the current month.

    Args:
        employee: Employee record
        company_id: Company ID
        db_session: SQLAlchemy session

    Returns:
        Amount to deduct from salary (ETB). 0 if no sick leave or within tier 1.
    """

    today = date.today()
    taken = get_leave_taken(company_id, employee.id, LeaveType.SICK, today.year, db_session)

    if taken <= DEFAULT_SICK_TIER_1_DAYS:
        # Within first 30 days - full pay, no reduction
        return Decimal('0')

    daily_rate = (Decimal(str(employee.basic_salary)) + Decimal(str(employee.allowances))) / Decimal('30')

    # Calculate the reduction for the CURRENT month
    # This month's sick days that fall in tier 2 or tier 3
    month_start = today.replace(day=1)

    # Get this month's approved sick leave
    month_sick_days = db_session.query(
        db.func.sum(Leave.days_requested)
    ).filter(
        Leave.company_id == company_id,
        Leave.employee_id == employee.id,
        Leave.leave_type == LeaveType.SICK,
        Leave.status == 'approved',
        Leave.start_date >= month_start,
        Leave.start_date <= today,
    ).scalar() or 0

    if month_sick_days == 0:
        return Decimal('0')

    # Determine which tier we're in
    if taken <= DEFAULT_SICK_TIER_1_DAYS + DEFAULT_SICK_TIER_2_DAYS:
        # Tier 2: 50% pay → deduct 50% of daily rate × sick days this month
        reduction = (daily_rate * Decimal('0.5') * Decimal(str(month_sick_days))).quantize(Decimal('0.01'))
    else:
        # Tier 3: 0% pay → deduct 100% of daily rate × sick days this month
        reduction = (daily_rate * Decimal(str(month_sick_days))).quantize(Decimal('0.01'))

    return reduction
