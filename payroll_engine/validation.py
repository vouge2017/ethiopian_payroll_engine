"""
Pre-Processing Validation Engine

Runs before any payroll is finalized. Catches typos, duplicates,
missing data, and legal violations before they become real money mistakes.

Severity levels:
    BLOCK — Must fix before processing. Cannot proceed.
    FLAG  — Can override with a reason. Requires explicit approval.
    WARN  — Informational only. Shows but doesn't block.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


class ValidationResult:
    """A single validation finding."""

    def __init__(self, rule_code: str, severity: str, message: str,
                 employee_id: str = None, details: dict = None,
                 employee_name: str = None, hint: str = None):
        self.rule_code = rule_code
        self.severity = severity  # BLOCK / FLAG / WARN
        self.message = message
        self.employee_id = employee_id  # None = global issue
        self.employee_name = employee_name or ''
        self.hint = hint or ''
        self.details = details or {}
        self.overridden = False
        self.override_reason = None
        self.overridden_by = None

    def to_dict(self):
        return {
            'rule_code': self.rule_code,
            'severity': self.severity,
            'message': self.message,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'hint': self.hint,
            'details': self.details,
            'overridden': self.overridden,
            'override_reason': self.override_reason,
        }


def validate_payroll_data(employees_data: List[Dict[str, Any]],
                          company_id: int = None,
                          previous_payslips: Dict[str, dict] = None) -> List[ValidationResult]:
    """
    Run all pre-processing validation checks on payroll data.

    Args:
        employees_data: List of employee dicts with keys:
            id, name, basic, allowances, gross, tax, pension_employee, net, bank
        company_id: Company ID for database lookups
        previous_payslips: Dict mapping employee_id to previous payslip data

    Returns:
        List of ValidationResult objects
    """
    results = []

    if not employees_data:
        results.append(ValidationResult(
            rule_code='EMPTY_DATA',
            severity='BLOCK',
            message='No employee data provided. CSV file may be empty.'
        ))
        return results

    # --- BLOCK checks (must fix before processing) ---

    _check_duplicate_employees(employees_data, results)
    _check_negative_net_pay(employees_data, results)
    _check_missing_bank(employees_data, results)

    # --- FLAG checks (can override with reason) ---

    _check_salary_typos(employees_data, previous_payslips, results)
    _check_salary_change_significant(employees_data, previous_payslips, results)
    _check_pension_mismatch(employees_data, results)
    _check_tax_mismatch(employees_data, results)
    _check_cash_compliance(employees_data, results)
    _check_payroll_variance(employees_data, company_id, results)
    _check_pending_leave_impact(employees_data, company_id, results)

    # --- WARN checks (informational) ---

    _check_missing_tin(employees_data, results)

    # --- Deduction checks ---
    _check_active_deductions(employees_data, company_id, results)

    return results


def _check_duplicate_employees(data: List[Dict], results: List[ValidationResult]):
    """BLOCK: Same name + same bank account = likely duplicate."""
    seen = {}
    for emp in data:
        name = emp.get('name', '').strip().lower()
        bank = emp.get('bank', '').strip().lower()
        if not name or not bank:
            continue
        key = (name, bank)
        if key in seen:
            results.append(ValidationResult(
                rule_code='DUPLICATE_EMPLOYEE',
                severity='BLOCK',
                message=f"Possible duplicate: '{emp['name']}' appears twice with the same bank account. "
                        f"Check if this is the same person.",
                employee_id=emp.get('id'),
                employee_name=emp.get('name', ''),
                hint='Check if this is the same person listed twice.',
                details={'matched_with': seen[key]}
            ))
        else:
            seen[key] = emp.get('id', '')


def _check_negative_net_pay(data: List[Dict], results: List[ValidationResult]):
    """BLOCK: Net pay cannot be negative."""
    for emp in data:
        net = emp.get('net', 0)
        if net < 0:
            results.append(ValidationResult(
                rule_code='NEGATIVE_NET_PAY',
                severity='BLOCK',
                message=f"Negative net pay: ETB {net:,.2f}. "
                        f"Gross ({emp.get('gross', 0):,.2f}) < "
                        f"Deductions (tax {emp.get('tax', 0):,.2f} + "
                        f"pension {emp.get('pension_employee', 0):,.2f})",
                employee_id=emp.get('id'),
                employee_name=emp.get('name', ''),
                hint='Check the salary, tax, and pension values for this employee.'
            ))


def _check_missing_bank(data: List[Dict], results: List[ValidationResult]):
    """BLOCK: Bank or Telebirr details required for disbursement."""
    for emp in data:
        bank = emp.get('bank', '').strip()
        if not bank:
            results.append(ValidationResult(
                rule_code='MISSING_BANK',
                severity='BLOCK',
                message=f"No bank/Telebirr details for '{emp.get('name', 'Unknown')}'",
                employee_id=emp.get('id'),
                employee_name=emp.get('name', ''),
                hint='Add a bank account or Telebirr number so they can be paid.'
            ))


def _check_salary_typos(data: List[Dict], previous: Dict[str, dict],
                        results: List[ValidationResult]):
    """FLAG: Salary > 10× previous month or > 500,000 ETB.

    This catches data entry errors (extra zeros, wrong decimal place).
    For real salary changes, see _check_salary_change_significant.
    """
    for emp in data:
        basic = emp.get('basic', 0)
        allowances = emp.get('allowances', 0)
        total = basic + allowances
        emp_name = emp.get('name', '')

        # Absolute threshold
        if total > 500000:
            results.append(ValidationResult(
                rule_code='SALTYPO_ABSOLUTE',
                severity='FLAG',
                message=f"{emp_name}'s salary is unusually high: ETB {total:,.2f}. "
                        f"Is this correct?",
                employee_id=emp.get('id'),
                employee_name=emp_name,
                hint='Check with the employee if this amount is correct.',
                details={'salary': total, 'threshold': 500000}
            ))
            continue

        # Relative threshold (compared to previous month)
        if previous and emp.get('id') in previous:
            prev = previous[emp['id']]
            prev_total = prev.get('basic', 0) + prev.get('allowances', 0)
            if prev_total > 0 and total > prev_total * 10:
                results.append(ValidationResult(
                    rule_code='SALTYPO_RELATIVE',
                    severity='FLAG',
                    message=f"{emp_name}'s salary changed significantly "
                            f"(ETB {prev_total:,.2f} → {total:,.2f}). "
                            f"Is this correct?",
                    employee_id=emp.get('id'),
                    employee_name=emp_name,
                    hint='Check with the employee if this change is correct.',
                    details={'current': total, 'previous': prev_total}
                ))


def _check_salary_change_significant(data: List[Dict], previous: Dict[str, dict],
                                     results: List[ValidationResult]):
    """FLAG: Salary changed by more than 30% from previous month.

    Catches real salary changes (raises, demotions) that Tigist should verify.
    The 10x threshold in _check_salary_typos catches typos; this catches
    intentional but unusual changes that need confirmation.
    """
    if not previous:
        return

    for emp in data:
        emp_id = emp.get('id')
        if emp_id not in previous:
            continue

        prev = previous[emp_id]
        prev_total = float(prev.get('basic', 0)) + float(prev.get('allowances', 0))
        curr_total = float(emp.get('basic', 0)) + float(emp.get('allowances', 0))

        if prev_total <= 0:
            continue

        change_pct = abs(curr_total - prev_total) / prev_total * 100

        if change_pct > 30:
            direction = 'increased' if curr_total > prev_total else 'decreased'
            results.append(ValidationResult(
                rule_code='SALARY_CHANGE_30PCT',
                severity='FLAG',
                message=(
                    f"{emp.get('name', 'Employee')}'s salary {direction} by {change_pct:.0f}% "
                    f"(ETB {prev_total:,.0f} → ETB {curr_total:,.0f}). "
                    f'Is this correct?'
                ),
                employee_id=emp_id,
                employee_name=emp.get('name', ''),
                hint='Verify this salary change with the employee or their contract.',
                details={
                    'previous': prev_total,
                    'current': curr_total,
                    'change_pct': round(change_pct, 1),
                }
            ))


def _check_payroll_variance(data: List[Dict], company_id: int,
                            results: List[ValidationResult]):
    """FLAG: Total payroll differs from last month by more than 20%.

    A large swing in total payroll is unusual and should be verified.
    Common causes: new hires, terminations, bonuses, data errors.
    """
    if company_id is None:
        return
    try:
        from payroll_engine.models import PayrollRun, Payslip
        last_run = PayrollRun.query.filter_by(
            company_id=company_id, status='completed'
        ).order_by(PayrollRun.run_date.desc()).first()
        if not last_run:
            return

        previous_net = sum(float(p.net_pay) for p in last_run.payslips)
        current_net = sum(float(e.get('net', 0)) for e in data)

        if previous_net <= 0:
            return

        change_pct = abs(current_net - previous_net) / previous_net * 100

        if change_pct > 20:
            direction = 'increased' if current_net > previous_net else 'decreased'
            diff = abs(current_net - previous_net)
            # Count employees in each run for context
            prev_count = len(last_run.payslips)
            curr_count = len(data)
            count_note = ''
            if curr_count != prev_count:
                count_note = f' ({prev_count} → {curr_count} employees)'
            results.append(ValidationResult(
                rule_code='PAYROLL_VARIANCE',
                severity='FLAG',
                message=(
                    f'Total payroll {direction} by {change_pct:.0f}% '
                    f'(ETB {previous_net:,.0f} → ETB {current_net:,.0f}, '
                    f'difference: ETB {diff:,.0f}){count_note}. '
                    f'Is this correct?'
                ),
                hint=(
                    'Common causes: new hires, terminations, salary changes, '
                    'bonuses, or data entry errors. '
                    'Check the employee list for unexpected additions or changes.'
                ),
                details={
                    'previous_total': previous_net,
                    'current_total': current_net,
                    'change_pct': round(change_pct, 1),
                    'previous_count': prev_count,
                    'current_count': curr_count,
                }
            ))
    except Exception as e:
        import logging
        logging.getLogger('payroll_engine.validation').warning(
            'Payroll variance check skipped: %s', e
        )


def _check_pending_leave_impact(data: List[Dict], company_id: int,
                                results: List[ValidationResult]):
    """FLAG: Employee with approved unpaid leave still shows full salary.

    If an employee has approved unpaid leave this month, their salary
    may need to be prorated. This flags it for Tigist's review.
    """
    if company_id is None:
        return
    try:
        from payroll_engine.models import Leave, Employee

        today = date.today()
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1)
        else:
            month_end = date(today.year, today.month + 1, 1)

        # Find employees with approved unpaid leave this month
        unpaid_leaves = Leave.query.filter(
            Leave.company_id == company_id,
            Leave.leave_type == 'unpaid',
            Leave.status == 'approved',
            Leave.start_date < month_end,
            Leave.end_date >= month_start,
        ).all()

        emp_ids_on_leave = {l.employee_id for l in unpaid_leaves}
        if not emp_ids_on_leave:
            return

        employees = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.id.in_(emp_ids_on_leave),
            Employee.is_deleted == False,
        ).all()
        emp_by_id = {e.id: e for e in employees}

        for leave in unpaid_leaves:
            emp = emp_by_id.get(leave.employee_id)
            if not emp:
                continue
            # Check if this employee appears in the payroll data with full salary
            for emp_data in data:
                if emp_data.get('id') == emp.employee_id:
                    # Calculate overlap days
                    overlap_start = max(leave.start_date, month_start)
                    overlap_end = min(leave.end_date, month_end)
                    leave_days = (overlap_end - overlap_start).days + 1
                    if leave_days > 0:
                        # Estimate the salary deduction
                        monthly_gross = float(emp.basic_salary) + float(emp.allowances)
                        daily_rate = monthly_gross / 30
                        est_deduction = daily_rate * leave_days
                        results.append(ValidationResult(
                            rule_code='PENDING_UNPAID_LEAVE',
                            severity='FLAG',
                            message=(
                                f'{emp.name} has {leave_days} days of approved unpaid leave '
                                f'({leave.start_date} to {leave.end_date}). '
                                f'Salary may need prorating.'
                            ),
                            employee_id=emp.employee_id,
                            employee_name=emp.name,
                            hint=(
                                f'Estimated deduction: ETB {est_deduction:,.0f} '
                                f'({leave_days} days × ETB {daily_rate:,.0f}/day). '
                                f'Use the salary proration or sick leave reduction field.'
                            ),
                            details={
                                'leave_days': leave_days,
                                'leave_start': str(leave.start_date),
                                'leave_end': str(leave.end_date),
                                'estimated_deduction': round(est_deduction, 2),
                                'daily_rate': round(daily_rate, 2),
                            }
                        ))
    except Exception as e:
        import logging
        logging.getLogger('payroll_engine.validation').warning(
            'Unpaid leave check skipped: %s', e
        )


def _check_pension_mismatch(data: List[Dict], results: List[ValidationResult]):
    """FLAG: Pension should be 7% of basic salary."""
    for emp in data:
        basic = _D(emp.get('basic', 0))
        pension = _D(emp.get('pension_employee', 0))
        expected = (basic * Decimal('0.07')).quantize(Decimal('0.01'))
        emp_name = emp.get('name', '')

        if basic > 0 and abs(pension - expected) > Decimal('0.01'):
            results.append(ValidationResult(
                rule_code='PENSION_MISMATCH',
                severity='FLAG',
                message=f"{emp_name}'s pension doesn't match: "
                        f"expected ETB {expected:,.2f} (7% of {basic:,.2f}), "
                        f"got ETB {pension:,.2f}",
                employee_id=emp.get('id'),
                employee_name=emp_name,
                hint='Pension should be 7% of basic salary. Check the calculation.',
                details={'expected': expected, 'actual': pension, 'basic': basic}
            ))


def _check_tax_mismatch(data: List[Dict], results: List[ValidationResult]):
    """FLAG: Tax should match the bracket calculation."""
    # We can't fully verify without re-running the tax engine,
    # but we can do a basic sanity check
    for emp in data:
        gross = emp.get('gross', 0)
        tax = emp.get('tax', 0)
        emp_name = emp.get('name', '')

        # Tax can never exceed gross
        if tax > gross:
            results.append(ValidationResult(
                rule_code='TAX_EXCEEDS_GROSS',
                severity='FLAG',
                message=f"{emp_name}'s tax (ETB {tax:,.2f}) exceeds gross salary (ETB {gross:,.2f}). "
                        f"This should never happen.",
                employee_id=emp.get('id'),
                employee_name=emp_name,
                hint='Check the tax calculation for this employee.',
                details={'tax': tax, 'gross': gross}
            ))

        # Tax on 0 salary should be 0
        if gross == 0 and tax != 0:
            results.append(ValidationResult(
                rule_code='TAX_ON_ZERO',
                severity='FLAG',
                message=f"{emp_name} has tax of ETB {tax:,.2f} on zero salary.",
                employee_id=emp.get('id'),
                employee_name=emp_name,
                hint='Check if this employee should have a salary.'
            ))


def _check_missing_tin(data: List[Dict], results: List[ValidationResult]):
    """WARN: TIN needed for ERCA reporting."""
    for emp in data:
        tin = emp.get('tin', '').strip()
        emp_name = emp.get('name', '')
        if not tin:
            results.append(ValidationResult(
                rule_code='MISSING_TIN',
                severity='WARN',
                message=f"{emp_name} has no TIN number. "
                        f"Required for ERCA filing.",
                employee_id=emp.get('id'),
                employee_name=emp_name,
                hint='Ask the employee for their TIN number before filing.'
            ))


def _check_cash_compliance(data: List[Dict], results: List[ValidationResult]):
    """FLAG: Ethiopian law requires electronic payment for salaries above ETB 30,000.

    Per the Income Tax (Amendment) Proclamation No. 1395/2025, cash payments
    above ETB 30,000 must go through a bank or official electronic channel.
    This is a FLAG (not BLOCK) — the system informs, the owner decides.
    """
    CASH_LIMIT = 30000
    for emp in data:
        net = emp.get('net', 0)
        bank = emp.get('bank', '').strip()
        emp_name = emp.get('name', '')

        if net > CASH_LIMIT and not bank:
            results.append(ValidationResult(
                rule_code='CASH_COMPLIANCE',
                severity='FLAG',
                message=f"{emp_name}'s net pay (ETB {net:,.2f}) exceeds the "
                        f"ETB {CASH_LIMIT:,} cash payment limit. Ethiopian law "
                        f"requires electronic payment (bank transfer or Telebirr) "
                        f"for salaries above this amount.",
                employee_id=emp.get('id'),
                employee_name=emp_name,
                hint='Add a bank account for this employee to avoid a compliance violation.',
                details={'net_pay': net, 'cash_limit': CASH_LIMIT}
            ))


def _check_active_deductions(data: List[Dict], company_id: int,
                              results: List[ValidationResult]):
    """FLAG: Check for active deductions and their warnings.

    Pulls active deductions for each employee and flags:
    - Balance nearing zero (yellow)
    - Court order exceeding statutory cap (red)
    - Expired date-bounded deductions
    """
    if company_id is None:
        return
    try:
        from payroll_engine.models import EmployeeDeduction
        from decimal import Decimal

        # Collect all employee IDs from the data
        emp_ids = [e.get('id') for e in data if e.get('id')]
        if not emp_ids:
            return

        # Batch-fetch active deductions
        # We need to match by employee_id (string) which is stored in the Employee table
        # The deduction's employee_id is the FK to Employee.id (integer)
        # We need to look up by Employee.employee_id
        from payroll_engine.models import Employee
        employees = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.employee_id.in_(emp_ids),
            Employee.is_deleted == False,
        ).all()
        emp_by_eid = {e.employee_id: e for e in employees}

        emp_int_ids = [e.id for e in employees]
        if not emp_int_ids:
            return

        deductions = EmployeeDeduction.query.filter(
            EmployeeDeduction.company_id == company_id,
            EmployeeDeduction.employee_id.in_(emp_int_ids),
            EmployeeDeduction.is_active == True
        ).all()

        # Group deductions by employee_id (integer)
        ded_by_emp = {}
        for d in deductions:
            if d.employee_id not in ded_by_emp:
                ded_by_emp[d.employee_id] = []
            ded_by_emp[d.employee_id].append(d)

        for emp_data in data:
            eid = emp_data.get('id')
            emp_obj = emp_by_eid.get(eid)
            if not emp_obj:
                continue
            emp_deds = ded_by_emp.get(emp_obj.id, [])
            net = Decimal(str(emp_data.get('net', 0)))
            emp_name = emp_data.get('name', '')

            for ded in emp_deds:
                # Check for balance warning
                warning = ded.warning_message
                if warning:
                    results.append(ValidationResult(
                        rule_code='DEDUCTION_LOW_BALANCE',
                        severity='FLAG',
                        message=f"{emp_name}: {warning}",
                        employee_id=eid,
                        employee_name=emp_name,
                        hint='This deduction will stop after this payment. Verify the amount is correct.',
                    ))

                # Court order cap check
                if ded.deduction_type == 'court_order' and ded.amount_mode == 'percentage':
                    cap = Decimal('33.33')  # 1/3 standard cap
                    if ded.amount > cap:
                        # Check if it exceeds 1/2 (child support max)
                        if ded.amount > Decimal('50'):
                            results.append(ValidationResult(
                                rule_code='COURT_ORDER_EXCEEDS_CAP',
                                severity='BLOCK',
                                message=f"{emp_name}: Court order deduction ({ded.amount}%) exceeds "
                                        f"the statutory maximum of 50% (child support cap). "
                                        f"This is illegal.",
                                employee_id=eid,
                                employee_name=emp_name,
                                hint='Reduce the deduction percentage to 50% or less.',
                            ))
                        else:
                            results.append(ValidationResult(
                                rule_code='COURT_ORDER_ABOVE_STANDARD',
                                severity='FLAG',
                                message=f"{emp_name}: Court order deduction ({ded.amount}%) exceeds "
                                        f"the standard 1/3 (33.33%) cap. Only allowed for "
                                        f"child support/maintenance.",
                                employee_id=eid,
                                employee_name=emp_name,
                                hint='Verify this is a child support/maintenance order.',
                            ))

                # Net pay cap check: total deductions can't exceed net
                total_ded_amount = sum(d.calculate_deduction(net) for d in emp_deds)
                if total_ded_amount > net:
                    results.append(ValidationResult(
                        rule_code='DEDUCTIONS_EXCEED_NET',
                        severity='BLOCK',
                        message=f"{emp_name}: Total deductions (ETB {total_ded_amount:,.2f}) exceed "
                                f"net pay (ETB {net:,.2f}). Paycheck would be negative.",
                        employee_id=eid,
                        employee_name=emp_name,
                        hint='Reduce deduction amounts or stop one of the deductions.',
                    ))

    except Exception as e:
        # Database not available during tests or CSV-only validation.
        # Log so operators can see when deduction checks silently skipped.
        import logging
        logging.getLogger('payroll_engine.validation').warning(
            'Deduction validation skipped (DB unavailable): %s', e
        )


def get_summary(results: List[ValidationResult]) -> Dict[str, Any]:
    """
    Summarize validation results.

    Returns:
        Dict with counts and boolean 'can_proceed'
    """
    blocks = [r for r in results if r.severity == 'BLOCK' and not r.overridden]
    flags = [r for r in results if r.severity == 'FLAG' and not r.overridden]
    warns = [r for r in results if r.severity == 'WARN']

    return {
        'total': len(results),
        'blocks': len(blocks),
        'flags': len(flags),
        'warns': len(warns),
        'can_proceed': len(blocks) == 0,
        'requires_approval': len(flags) > 0,
        'block_messages': [r.message for r in blocks],
        'flag_messages': [r.message for r in flags],
        'warn_messages': [r.message for r in warns],
    }
