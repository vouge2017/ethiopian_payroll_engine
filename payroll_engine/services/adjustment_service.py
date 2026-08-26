"""
Adjustment Payslip Service — Correction after approval.

Handles the complete lifecycle of payroll corrections:
1. Create adjustment (positive or negative)
2. Calculate adjustment with proper tax recalculation
3. Link to original payslip
4. Track adjustment history per employee per period
5. Generate adjustment bank file
6. Month-end close integration

Design: Adjustments are separate Payslip records with payslip_type='adjustment'.
They don't modify the original — they create a delta. This preserves the audit trail.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Q = Decimal('0.01')


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


@dataclass
class AdjustmentResult:
    """Result of creating an adjustment payslip."""

    success: bool
    adjustment_id: int | None = None
    employee_name: str = ''
    original_gross: Decimal = Decimal('0')
    original_net: Decimal = Decimal('0')
    adjustment_gross: Decimal = Decimal('0')
    adjustment_tax: Decimal = Decimal('0')
    adjustment_pension: Decimal = Decimal('0')
    adjustment_net: Decimal = Decimal('0')
    new_total_net: Decimal = Decimal('0')
    reason: str = ''
    error: str = ''


@dataclass
class AdjustmentSummary:
    """Summary of all adjustments for a payroll run."""

    run_id: int
    period: str
    total_adjustments: int = 0
    total_positive_net: Decimal = Decimal('0')
    total_negative_net: Decimal = Decimal('0')
    net_adjustment: Decimal = Decimal('0')
    adjustments: list = field(default_factory=list)
    employees_affected: int = 0


def calculate_adjustment(
    original_gross: Decimal,
    original_tax: Decimal,
    original_pension: Decimal,
    original_net: Decimal,
    adjustment_amount: Decimal,
    adjustment_type: str = 'addition',
    basic_salary: Decimal = Decimal('0'),
) -> dict:
    """
    Calculate the impact of a payroll adjustment.

    Two modes:
    1. 'addition' / 'deduction': adjustment_amount is the GROSS change.
       Tax and pension are recalculated on the delta.
    2. 'net_override': adjustment_amount is the NET amount to pay/deduct.
       Gross is back-calculated.

    Args:
        original_gross: Original payslip gross
        original_tax: Original payslip tax
        original_pension: Original payslip pension
        original_net: Original payslip net
        adjustment_amount: The adjustment amount (positive)
        adjustment_type: 'addition', 'deduction', or 'net_override'
        basic_salary: Employee's basic salary (for pension calculation on additions)

    Returns:
        Dict with adjustment details
    """
    from payroll_engine.payroll import calculate_payroll

    amount = _D(adjustment_amount)

    if adjustment_type == 'net_override':
        # Net override: amount is what the employee should receive
        # No recalculation needed — this is a manual correction
        return {
            'adjustment_gross': Decimal('0'),
            'adjustment_tax': Decimal('0'),
            'adjustment_pension': Decimal('0'),
            'adjustment_net': amount,
            'new_total_net': original_net + amount,
            'mode': 'net_override',
        }

    if adjustment_type == 'deduction':
        amount = -amount

    # For additions: recalculate tax on the adjustment amount
    # The adjustment is treated as additional taxable income
    # Pension is only on basic salary adjustments, not on bonuses/allowances
    if basic_salary > 0 and adjustment_type == 'addition':
        # If this is a salary correction (basic salary change), recalculate pension
        result = calculate_payroll(basic_salary=amount, allowances=Decimal('0'))
        adj_tax = result['tax']
        adj_pension = result['pension_employee']
        adj_gross = amount
        adj_net = adj_gross - adj_tax - adj_pension
    else:
        # For bonuses, overtime corrections, etc. — tax on full amount, no pension
        from payroll_engine.tax import calculate_tax

        adj_gross = amount
        adj_tax = calculate_tax(abs(amount)) * (1 if amount > 0 else -1)
        adj_pension = Decimal('0')
        adj_net = adj_gross - adj_tax

    new_total = original_net + adj_net

    return {
        'adjustment_gross': adj_gross.quantize(Q, rounding=ROUND_HALF_UP),
        'adjustment_tax': adj_tax.quantize(Q, rounding=ROUND_HALF_UP),
        'adjustment_pension': adj_pension.quantize(Q, rounding=ROUND_HALF_UP),
        'adjustment_net': adj_net.quantize(Q, rounding=ROUND_HALF_UP),
        'new_total_net': new_total.quantize(Q, rounding=ROUND_HALF_UP),
        'mode': 'recalculated',
    }


def create_adjustment(
    db,
    models,
    run_id: int,
    company_id: int,
    employee_id: int,
    adjustment_amount: Decimal,
    adjustment_type: str,
    reason: str,
    user_id: int,
    basic_salary: Decimal = Decimal('0'),
) -> AdjustmentResult:
    """
    Create an adjustment payslip with full audit trail.

    Args:
        db: SQLAlchemy db instance
        models: Module with Payslip, PayrollRun, Employee, AuditLog
        run_id: PayrollRun ID
        company_id: Company ID
        employee_id: Employee ID (integer FK)
        adjustment_amount: Amount (positive)
        adjustment_type: 'addition', 'deduction', or 'net_override'
        reason: Why this adjustment is needed
        user_id: User creating the adjustment
        basic_salary: Employee's basic salary (for pension recalculation)

    Returns:
        AdjustmentResult
    """
    Payslip = models.Payslip
    PayrollRun = models.PayrollRun
    Employee = models.Employee
    AuditLog = models.AuditLog

    # Validate run
    run = PayrollRun.query.filter_by(id=run_id, company_id=company_id).first()
    if not run:
        return AdjustmentResult(success=False, error='Payroll run not found.')
    if run.status not in ('completed', 'locked'):
        return AdjustmentResult(success=False, error='Can only adjust completed or locked runs.')

    # Validate employee
    emp = Employee.query.filter_by(id=employee_id, company_id=company_id, is_deleted=False).first()
    if not emp:
        return AdjustmentResult(success=False, error='Employee not found.')

    # Find original payslip
    original = Payslip.query.filter_by(
        payroll_run_id=run_id,
        employee_id=employee_id,
        payslip_type='regular',
        company_id=company_id,
    ).first()

    if not original:
        return AdjustmentResult(success=False, error='No original payslip found for this employee in this run.')

    # Calculate adjustment
    calc = calculate_adjustment(
        original_gross=_D(original.gross_salary),
        original_tax=_D(original.tax),
        original_pension=_D(original.employee_pension),
        original_net=_D(original.net_pay),
        adjustment_amount=adjustment_amount,
        adjustment_type=adjustment_type,
        basic_salary=basic_salary,
    )

    # Create adjustment payslip
    adj = Payslip(
        payroll_run_id=run_id,
        employee_id=employee_id,
        company_id=company_id,
        gross_salary=calc['adjustment_gross'],
        tax=calc['adjustment_tax'],
        employee_pension=calc['adjustment_pension'],
        employer_pension=Decimal('0'),
        net_pay=calc['adjustment_net'],
        payslip_type='adjustment',
        reason=reason,
        original_payslip_id=original.id,
        pdf_status='not_generated',
    )
    db.session.add(adj)
    db.session.flush()

    # Audit log
    log = AuditLog(
        company_id=company_id,
        user_id=user_id,
        action='adjustment_payslip_created',
        details={
            'run_id': run_id,
            'reference': run.reference,
            'employee_id': emp.employee_id,
            'employee_name': emp.name,
            'adjustment_type': adjustment_type,
            'amount': str(adjustment_amount),
            'reason': reason,
            'adjustment_id': adj.id,
            'original_net': str(original.net_pay),
            'adjustment_net': str(calc['adjustment_net']),
            'new_total_net': str(calc['new_total_net']),
        },
    )
    db.session.add(log)
    db.session.commit()

    return AdjustmentResult(
        success=True,
        adjustment_id=adj.id,
        employee_name=emp.name,
        original_gross=_D(original.gross_salary),
        original_net=_D(original.net_pay),
        adjustment_gross=calc['adjustment_gross'],
        adjustment_tax=calc['adjustment_tax'],
        adjustment_pension=calc['adjustment_pension'],
        adjustment_net=calc['adjustment_net'],
        new_total_net=calc['new_total_net'],
        reason=reason,
    )


def get_adjustment_summary(db, models, run_id: int, company_id: int) -> AdjustmentSummary:
    """
    Get a summary of all adjustments for a payroll run.

    Args:
        db: SQLAlchemy db instance
        models: Module with Payslip, PayrollRun, Employee
        run_id: PayrollRun ID
        company_id: Company ID

    Returns:
        AdjustmentSummary
    """
    Payslip = models.Payslip
    PayrollRun = models.PayrollRun
    Employee = models.Employee

    run = PayrollRun.query.filter_by(id=run_id, company_id=company_id).first()
    if not run:
        return AdjustmentSummary(run_id=run_id, period='')

    adjustments = Payslip.query.filter_by(
        payroll_run_id=run_id,
        company_id=company_id,
        payslip_type='adjustment',
    ).all()

    total_positive = Decimal('0')
    total_negative = Decimal('0')
    employees_affected = set()
    adj_list = []

    for adj in adjustments:
        emp = Employee.query.filter_by(id=adj.employee_id, company_id=company_id).first()
        net = _D(adj.net_pay)

        if net > 0:
            total_positive += net
        else:
            total_negative += abs(net)

        employees_affected.add(adj.employee_id)

        # Find original
        original_net = Decimal('0')
        if adj.original_payslip_id:
            original = Payslip.query.filter_by(id=adj.original_payslip_id).first()
            if original:
                original_net = _D(original.net_pay)

        adj_list.append({
            'id': adj.id,
            'employee_id': emp.employee_id if emp else '',
            'employee_name': emp.name if emp else 'Unknown',
            'type': 'addition' if net >= 0 else 'deduction',
            'gross': _D(adj.gross_salary),
            'tax': _D(adj.tax),
            'pension': _D(adj.employee_pension),
            'net': net,
            'original_net': original_net,
            'new_total': original_net + net,
            'reason': adj.reason or '',
            'created_at': adj.generated_at.isoformat() if adj.generated_at else '',
        })

    return AdjustmentSummary(
        run_id=run_id,
        period=run.period or '',
        total_adjustments=len(adjustments),
        total_positive_net=total_positive,
        total_negative_net=total_negative,
        net_adjustment=total_positive - total_negative,
        adjustments=adj_list,
        employees_affected=len(employees_affected),
    )


def generate_adjustment_bank_file(db, models, run_id: int, company_id: int) -> bytes | None:
    """
    Generate a bank file for adjustment payslips only.

    Only includes positive adjustments (money owed to employees).
    Negative adjustments (deductions) are handled separately.

    Returns:
        CSV bytes or None if no positive adjustments
    """
    from payroll_engine.bank_file import generate_csv

    summary = get_adjustment_summary(db, models, run_id, company_id)

    if summary.total_adjustments == 0:
        return None

    # Only positive adjustments go in the bank file
    positive_adjustments = [a for a in summary.adjustments if a['net'] > 0]

    if not positive_adjustments:
        return None

    employees_data = []
    for adj in positive_adjustments:
        # Get bank account from employee
        Employee = models.Employee
        emp = Employee.query.filter_by(
            employee_id=adj['employee_id'],
            company_id=company_id,
        ).first()

        employees_data.append({
            'id': adj['employee_id'],
            'name': adj['employee_name'],
            'bank': emp.bank_or_telebirr if emp else '',
            'net': float(adj['net']),
        })

    if employees_data:
        return generate_csv(
            employees_data,
            bank='cbe',
            company_name='',
            period=f'{summary.period} (Adjustments)',
        )

    return None
