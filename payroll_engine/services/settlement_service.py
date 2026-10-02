"""
Settlement Service

Calculates final settlements for terminated employees.
Extracted from main.py to enable:
- Reuse (correction runs, re-processing)
- Testing (unit test without Flask context)
- Clarity (business logic separate from HTTP handling)
"""

from datetime import date
from decimal import Decimal

from payroll_engine.leave import LeaveType
from payroll_engine.models import Employee, EmployeeDeduction, FinalSettlement, LeaveBalance
from payroll_engine.pension import employee_pension
from payroll_engine.severance import calculate_severance
from payroll_engine.tax import calculate_tax

Q = Decimal('0.01')


def calculate_outstanding_salary(employee: Employee, end_date: date) -> Decimal:
    """Calculate prorated salary for the last working month.

    If the employee works the full month, they get full salary.
    If terminated mid-month, salary is prorated to the last working day.

    Args:
        employee: Employee record
        end_date: Last working day

    Returns:
        Outstanding salary amount (ETB)
    """
    basic = Decimal(str(employee.basic_salary))
    allowances = Decimal(str(employee.allowances))
    gross = basic + allowances

    # If end_date is the last day of the month, full salary
    if end_date.month != (end_date.replace(day=28) + __import__('datetime').timedelta(days=4)).day:
        # Not the last day - prorate
        days_in_month = 30  # Ethiopian convention
        days_worked = end_date.day
        prorated = gross * Decimal(str(days_worked)) / Decimal(str(days_in_month))
        return prorated.quantize(Q)

    return gross


def calculate_leave_encashment(employee: Employee, end_date: date, company_id: int, db_session=None) -> Decimal:
    """Calculate encashment for unused annual leave.

    Queries actual LeaveBalance records to get accurate unused days.
    Falls back to statutory calculation if no balance records exist.

    Args:
        employee: Employee record
        end_date: Last working day
        company_id: Company ID for balance lookup
        db_session: SQLAlchemy session (optional, for queries)

    Returns:
        Leave encashment amount (ETB)
    """
    basic = Decimal(str(employee.basic_salary))
    allowances = Decimal(str(employee.allowances))
    daily_rate = (basic + allowances) / Decimal('30')

    # Try to get actual leave balance
    if db_session:
        balance = LeaveBalance.query.filter_by(
            company_id=company_id,
            employee_id=employee.id,
            leave_type=LeaveType.ANNUAL,
            year=end_date.year,
        ).first()

        if balance:
            unused_days = balance.remaining
        else:
            # No balance record - calculate from statutory
            start = employee.start_date or employee.created_at.date()
            years_service = (end_date - start).days // 365
            entitled = 14 + years_service  # Statutory minimum
            unused_days = entitled  # Assume no leave taken (conservative)
    else:
        # No session - use statutory calculation
        start = employee.start_date or employee.created_at.date()
        years_service = (end_date - start).days // 365
        entitled = 14 + years_service
        unused_days = entitled

    unused_days = max(0, unused_days)
    encashment = (daily_rate * Decimal(str(unused_days))).quantize(Q)
    return encashment


def calculate_settlement(
    employee: Employee, termination_reason: str, end_date: date, company_id: int, db_session=None
) -> dict:
    """Calculate complete final settlement for a terminated employee.

    This is the SINGLE SOURCE OF TRUTH for settlement calculations.
    All settlement-related code must call this function.

    Args:
        employee: Employee record
        termination_reason: One of TerminationReason constants
        end_date: Last working day
        company_id: Company ID
        db_session: SQLAlchemy session for queries

    Returns:
        Dict with all settlement components:
        - severance: dict with eligible, amount, years_of_service
        - outstanding_salary: Decimal
        - leave_encashment: Decimal
        - pension_deduction: Decimal
        - tax_on_salary: Decimal
        - pending_deductions: Decimal
        - deduction_details: list
        - total_earnings: Decimal
        - total_deductions: Decimal
        - net_final_payment: Decimal
    """
    start = employee.start_date or employee.created_at.date()

    # 1. Severance
    sev_result = calculate_severance(employee.basic_salary, start, end_date, termination_reason)
    severance_amount = sev_result['final_amount'] if sev_result['eligible'] else Decimal('0')

    # 2. Outstanding salary
    outstanding_salary = calculate_outstanding_salary(employee, end_date)

    # 3. Leave encashment
    leave_encashment = calculate_leave_encashment(employee, end_date, company_id, db_session)

    # 4. Pension deduction on outstanding salary
    pension_ded = employee_pension(employee.basic_salary)

    # 5. Tax on outstanding salary (after pension deduction)
    taxable_salary = outstanding_salary - pension_ded
    taxable_salary = max(Decimal('0'), taxable_salary)
    tax_on_salary = calculate_tax(taxable_salary)

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
    total_earnings = outstanding_salary + severance_amount + leave_encashment
    total_deductions = pension_ded + tax_on_salary + pending_deductions
    net_final = total_earnings - total_deductions

    return {
        'severance': sev_result,
        'severance_amount': severance_amount,
        'outstanding_salary': outstanding_salary,
        'leave_encashment': leave_encashment,
        'pension_deduction': pension_ded,
        'tax_on_salary': tax_on_salary,
        'pending_deductions': pending_deductions,
        'deduction_details': deduction_details,
        'total_earnings': total_earnings,
        'total_deductions': total_deductions,
        'net_final_payment': net_final,
        'start_date': start,
        'end_date': end_date,
        'years_of_service': sev_result['years_of_service'],
    }


def create_settlement_record(
    employee: Employee, termination_reason: str, end_date: date, company_id: int, created_by: int, db_session
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

    Returns:
        FinalSettlement record (already added to session, not committed)
    """
    calc = calculate_settlement(employee, termination_reason, end_date, company_id, db_session)

    settlement = FinalSettlement(
        company_id=company_id,
        employee_id=employee.id,
        termination_reason=termination_reason,
        start_date=calc['start_date'],
        end_date=end_date,
        years_of_service=calc['years_of_service'],
        outstanding_salary=calc['outstanding_salary'],
        severance_pay=calc['severance_amount'],
        leave_encashment=calc['leave_encashment'],
        total_earnings=calc['total_earnings'],
        pension_deduction=calc['pension_deduction'],
        tax_on_salary=calc['tax_on_salary'],
        pending_deductions=calc['pending_deductions'],
        deduction_details=calc['deduction_details'],
        total_deductions=calc['total_deductions'],
        net_final_payment=calc['net_final_payment'],
        payment_method=employee.bank_account or employee.bank_or_telebirr or 'Cash',
        created_by=created_by,
    )
    db_session.add(settlement)
    return settlement
