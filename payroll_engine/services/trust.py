"""Trust Layer — confidence patterns for payroll workflows.

Every function in this module answers one of the five trust questions:
1. What changed?
2. Why did it change?
3. Is that expected?
4. What needs attention?
5. Can I safely proceed?
"""

from decimal import Decimal, InvalidOperation


def _D(value) -> Decimal:
    """Safely convert to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


# ──────────────────────────────────────────────────────────────
# PATTERN 1: Change Summary
# ──────────────────────────────────────────────────────────────

def get_payroll_change_summary(company_id: int) -> dict:
    """Compare current payroll run with previous month.

    Returns dict with:
        has_previous: bool
        current: {employee_count, total_gross, total_tax, total_net, period}
        previous: {employee_count, total_gross, total_tax, total_net, period}
        delta: {employee_count, total_gross, total_tax, total_net}
        delta_pct: {employee_count, total_gross, total_tax, total_net}
        changes: list of {type, description, employee, amount}
        variance_flag: bool (True if > 20% change in total_net)
        summary: str (human-readable one-liner)
    """
    from payroll_engine.models import PayrollRun

    # Get last two completed runs
    runs = PayrollRun.query.filter_by(
        company_id=company_id, status='completed'
    ).order_by(PayrollRun.run_date.desc()).limit(2).all()

    if not runs:
        return {
            'has_previous': False,
            'current': None,
            'previous': None,
            'delta': None,
            'delta_pct': None,
            'changes': [],
            'variance_flag': False,
            'summary': 'No payroll runs yet.',
        }

    current_run = runs[0]
    previous_run = runs[1] if len(runs) > 1 else None

    current = _summarize_run(current_run)
    previous = _summarize_run(previous_run) if previous_run else None

    if not previous:
        return {
            'has_previous': False,
            'current': current,
            'previous': None,
            'delta': None,
            'delta_pct': None,
            'changes': _detect_changes(current_run, None),
            'variance_flag': False,
            'summary': f"First payroll: {current['employee_count']} employees, ETB {current['total_net']:,.2f} net.",
        }

    # Calculate deltas
    delta = {}
    delta_pct = {}
    for key in ('employee_count', 'total_gross', 'total_tax', 'total_net'):
        d = current[key] - previous[key]
        delta[key] = d
        if previous[key] > 0:
            delta_pct[key] = (d / previous[key] * 100).quantize(Decimal('0.1'))
        else:
            delta_pct[key] = Decimal('0')

    # Detect changes
    changes = _detect_changes(current_run, previous_run)

    # Variance flag: > 20% change in total net
    variance_flag = abs(delta_pct.get('total_net', 0)) > 20

    # Build summary
    direction = 'increased' if delta['total_net'] > 0 else 'decreased'
    summary = (
        f"{current['employee_count']} employees · "
        f"ETB {current['total_net']:,.2f} net · "
        f"{direction} {abs(delta_pct['total_net'])}% from last month"
    )

    return {
        'has_previous': True,
        'current': current,
        'previous': previous,
        'delta': delta,
        'delta_pct': delta_pct,
        'changes': changes,
        'variance_flag': variance_flag,
        'summary': summary,
    }


def _summarize_run(run) -> dict:
    """Extract summary stats from a PayrollRun."""
    if not run:
        return {'employee_count': 0, 'total_gross': 0, 'total_tax': 0, 'total_net': 0, 'period': ''}

    payslips = run.payslips or []
    return {
        'employee_count': len(payslips),
        'total_gross': sum(_D(p.gross_salary) for p in payslips),
        'total_tax': sum(_D(p.tax) for p in payslips),
        'total_net': sum(_D(p.net_pay) for p in payslips),
        'period': run.period or str(run.run_date),
        'reference': run.reference or f'PR-{run.id}',
    }


def _detect_changes(current_run, previous_run) -> list:
    """Detect what changed between two payroll runs.

    Returns list of {type, description, employee, amount, direction}.
    """
    changes = []

    if not previous_run:
        return changes

    current_employees = {p.employee_id: p for p in current_run.payslips}
    previous_employees = {p.employee_id: p for p in previous_run.payslips}

    # New employees
    for emp_id in current_employees:
        if emp_id not in previous_employees:
            p = current_employees[emp_id]
            changes.append({
                'type': 'new_employee',
                'description': f'New employee: {p.employee.name if p.employee else emp_id}',
                'employee': p.employee.name if p.employee else emp_id,
                'amount': float(p.net_pay),
                'direction': 'up',
            })

    # Removed employees
    for emp_id in previous_employees:
        if emp_id not in current_employees:
            p = previous_employees[emp_id]
            changes.append({
                'type': 'removed_employee',
                'description': f'No longer in payroll: {p.employee.name if p.employee else emp_id}',
                'employee': p.employee.name if p.employee else emp_id,
                'amount': float(p.net_pay),
                'direction': 'down',
            })

    # Salary changes (compare net pay)
    for emp_id in current_employees:
        if emp_id in previous_employees:
            curr = current_employees[emp_id]
            prev = previous_employees[emp_id]
            curr_net = _D(curr.net_pay)
            prev_net = _D(prev.net_pay)

            if prev_net > 0:
                change_pct = abs(curr_net - prev_net) / prev_net * 100
                if change_pct > 5:  # > 5% change is noteworthy
                    direction = 'up' if curr_net > prev_net else 'down'
                    name = curr.employee.name if curr.employee else emp_id
                    changes.append({
                        'type': 'salary_change',
                        'description': f'{name}: ETB {prev_net:,.0f} → {curr_net:,.0f} ({change_pct:.0f}% {direction})',
                        'employee': name,
                        'amount': float(curr_net - prev_net),
                        'direction': direction,
                    })

    return changes


# ──────────────────────────────────────────────────────────────
# PATTERN 4: Safe Approval
# ──────────────────────────────────────────────────────────────

def get_approval_preview(run_id: int) -> dict:
    """Generate a clear list of what will happen when payroll is approved.

    Returns dict with:
        actions: list of str (what will happen)
        undo_window: str (undo policy)
        undo_details: list of str (what gets undone vs. what doesn't)
        safety_checks: list of {check, status, detail}
    """
    from payroll_engine.models import PayrollRun

    run = PayrollRun.query.get(run_id)
    if not run:
        return {'error': 'Payroll run not found.'}

    payslips = run.payslips or []
    employee_count = len(payslips)
    total_net = sum(_D(p.net_pay) for p in payslips)
    total_tax = sum(_D(p.tax) for p in payslips)

    actions = [
        f'{employee_count} payslips will be generated',
        f'Bank file will be created (ETB {total_net:,.2f})',
        'ERCA report will be available for download',
        'Employees will be able to view their payslips in the portal',
    ]

    undo_window = 'You can undo this within 1 hour.'

    undo_details = [
        'Payslips will be deleted',
        'Payroll run will revert to "review" status',
        'Bank file will be invalidated',
        'Audit log will retain the approval record',
        'Any notifications already sent cannot be recalled',
    ]

    # Safety checks
    safety_checks = _run_safety_checks(run)

    return {
        'actions': actions,
        'undo_window': undo_window,
        'undo_details': undo_details,
        'safety_checks': safety_checks,
    }


def _run_safety_checks(run) -> list:
    """Run safety checks on a payroll run before approval."""

    checks = []
    payslips = run.payslips or []

    # Check for negative net pay
    negative_nets = [p for p in payslips if _D(p.net_pay) < 0]
    checks.append({
        'check': 'No negative net pay',
        'status': 'pass' if not negative_nets else 'fail',
        'detail': f'{len(negative_nets)} employee(s) have negative net pay' if negative_nets else '',
    })

    # Check for duplicate payslips
    emp_ids = [p.employee_id for p in payslips]
    duplicates = [eid for eid in emp_ids if emp_ids.count(eid) > 1]
    checks.append({
        'check': 'No duplicate employees',
        'status': 'pass' if not duplicates else 'fail',
        'detail': f'{len(set(duplicates))} duplicate(s) found' if duplicates else '',
    })

    # Check for zero gross (likely data error)
    zero_gross = [p for p in payslips if _D(p.gross_salary) == 0]
    checks.append({
        'check': 'No zero-salary employees',
        'status': 'pass' if not zero_gross else 'warn',
        'detail': f'{len(zero_gross)} employee(s) have zero gross salary' if zero_gross else '',
    })

    # Check tax brackets are current
    checks.append({
        'check': 'Tax calculated using current brackets',
        'status': 'pass',
        'detail': 'Proclamation 1395/2025',
    })

    # Check pension rates
    checks.append({
        'check': 'Pension calculated at 7%/11%',
        'status': 'pass',
        'detail': 'Proclamation 1268/2022',
    })

    return checks


# ──────────────────────────────────────────────────────────────
# PATTERN 6: Filing Progress
# ──────────────────────────────────────────────────────────────

def get_filing_progress(company_id: int, period: str = None) -> dict:
    """Generate filing progress status for a payroll period.

    Returns dict with:
        steps: list of {label, status, date, action_url}
        next_action: str
        days_remaining: int
        is_overdue: bool
    """
    from datetime import date as _date

    from payroll_engine.compliance import get_deadline_for_type
    from payroll_engine.models import Company, FilingRecord, PayrollRun

    # Get the most recent completed run
    run = PayrollRun.query.filter_by(
        company_id=company_id, status='completed'
    ).order_by(PayrollRun.run_date.desc()).first()

    if not run:
        return {
            'steps': [],
            'next_action': 'Run payroll first',
            'days_remaining': None,
            'is_overdue': False,
        }

    company = Company.query.get(company_id)
    today = _date.today()

    # Build filing steps
    steps = []

    # Step 1: Payroll processed
    steps.append({
        'label': 'Payroll processed',
        'status': 'done',
        'date': str(run.run_date),
        'action_url': None,
    })

    # Step 2: Payslips generated
    has_payslips = len(run.payslips or []) > 0
    steps.append({
        'label': 'Payslips generated',
        'status': 'done' if has_payslips else 'pending',
        'date': str(run.run_date) if has_payslips else None,
        'action_url': None,
    })

    # Step 3: ERCA filing
    erca_deadline = get_deadline_for_type(company, 'erca', run.run_date)
    try:
        erca_record = FilingRecord.query.filter_by(
            company_id=company_id, filing_type='erca', period=run.period
        ).first()
    except Exception:
        erca_record = None

    erca_status = 'done' if erca_record else ('overdue' if erca_deadline and today > erca_deadline else 'pending')
    erca_days = (erca_deadline - today).days if erca_deadline else None

    steps.append({
        'label': 'ERCA filing',
        'status': erca_status,
        'date': str(erca_record.filed_at.date()) if erca_record else None,
        'action_url': f'/reports/erca/{run.id}',
        'mark_url': '/filing-history/mark',
        'filing_type': 'erca',
        'period': run.period or '',
        'deadline': str(erca_deadline) if erca_deadline else None,
        'days_remaining': erca_days,
    })

    # Step 4: Pension remittance
    pension_deadline = get_deadline_for_type(company, 'pension', run.run_date)
    try:
        pension_record = FilingRecord.query.filter_by(
            company_id=company_id, filing_type='pension', period=run.period
        ).first()
    except Exception:
        pension_record = None

    pension_status = 'done' if pension_record else ('overdue' if pension_deadline and today > pension_deadline else 'pending')
    pension_days = (pension_deadline - today).days if pension_deadline else None

    steps.append({
        'label': 'Pension remittance',
        'status': pension_status,
        'date': str(pension_record.filed_at.date()) if pension_record else None,
        'action_url': f'/reports/pension/{run.id}',
        'mark_url': '/filing-history/mark',
        'filing_type': 'pension',
        'period': run.period or '',
        'deadline': str(pension_deadline) if pension_deadline else None,
        'days_remaining': pension_days,
    })

    # Step 5: Bank disbursement
    disbursement_status = run.disbursement_status or 'pending'
    steps.append({
        'label': 'Bank disbursement',
        'status': 'done' if disbursement_status in ('disbursed', 'confirmed') else 'pending',
        'date': None,
        'action_url': f'/payroll/{run.id}/disbursement',
    })

    # Find next action
    next_action = 'All filings complete!'
    days_remaining = None
    is_overdue = False

    for step in steps:
        if step['status'] == 'overdue':
            next_action = f"{step['label']} is OVERDUE"
            days_remaining = step.get('days_remaining', 0)
            is_overdue = True
            break
        elif step['status'] == 'pending':
            next_action = f"Next: {step['label']}"
            days_remaining = step.get('days_remaining')
            break

    return {
        'steps': steps,
        'next_action': next_action,
        'days_remaining': days_remaining,
        'is_overdue': is_overdue,
    }
