"""Payroll approval service.

Extracted from payroll_bp.py to separate business logic from HTTP handling.
The route handler handles auth/flash/redirects; this service handles the data.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from payroll_engine import db
from payroll_engine.compliance import compute_compliance_score
from payroll_engine.models import (
    Employee,
    PayrollDraft,
    PayrollRun,
    PayrollValidationResult,
    Payslip,
)
from payroll_engine.models_payroll_elements import PayrollItemAssignment
from payroll_engine.constants import COMPANY_TEMPLATE_ITEM_KEYS, SYSTEM_ITEM_KEYS
from payroll_engine.shared import create_audit_log, create_notification, tenant_get


class ApprovalResult:
    """Result of a payroll approval attempt."""

    def __init__(self, success, message=None, error=None, employee_count=0, compliance_score=None, redirect_to=None):
        self.success = success
        self.message = message
        self.error = error
        self.employee_count = employee_count
        self.compliance_score = compliance_score
        self.redirect_to = redirect_to  # 'detail', 'runs', or 'upload'


def _ensure_basic_assignment(employee, company_id, basic_amount):
    """Guarantee the employee has an active basic_salary assignment.

    Gross is assembled ENTIRELY from assignments, so an employee that reaches
    the engine path with any assignment but no basic_salary row is paid their
    allowances and nothing else. Creating the employee (CSV import) or the
    backfill migration both produce that state, so this is enforced here
    rather than trusted to the caller.

    Idempotent; returns None when the company has no basic_salary item at all
    (the catalog is incomplete), in which case the engine simply omits it.
    """
    from decimal import Decimal

    from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment

    amount = Decimal(str(basic_amount or 0))
    if amount <= 0:
        return None

    item = PayItemType.query.filter_by(
        company_id=company_id, key=SYSTEM_ITEM_KEYS.BASIC_SALARY.value
    ).first()
    if item is None:
        item = PayItemType.query.filter_by(
            company_id=None, key=SYSTEM_ITEM_KEYS.BASIC_SALARY.value
        ).first()
    if item is None:
        return None

    existing = PayrollItemAssignment.query.filter_by(
        company_id=company_id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        is_active=True,
    ).first()
    if existing is not None:
        return existing

    a = PayrollItemAssignment(
        company_id=company_id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        fixed_amount=amount,
        is_active=True,
    )
    db.session.add(a)
    db.session.flush()
    return a


def _ensure_general_allowance(employee, company_id, amount):
    """Create a General Allowance assignment for a legacy CSV import row.

    The CSV carries one undifferentiated `allowances` number. Under the elements
    model gross is assembled from assignments, so that number would silently
    vanish from the payslip. This materialises it as a single assignment against
    the company's General Allowance item (created from the catalog if missing).

    Idempotent: an existing active assignment for that item is left alone.
    """
    from decimal import Decimal

    from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment

    amount = Decimal(str(amount or 0))
    if amount <= 0:
        return None

    item = PayItemType.query.filter_by(
        company_id=company_id, key=COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value
    ).first()
    if item is None:
        return None

    existing = PayrollItemAssignment.query.filter_by(
        company_id=company_id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        is_active=True,
    ).first()
    if existing is not None:
        return existing

    a = PayrollItemAssignment(
        company_id=company_id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        fixed_amount=amount,
        is_active=True,
    )
    db.session.add(a)
    db.session.flush()
    return a


def _build_units_input(emp_data):
    """Collect per-period units for rate_x_units pay items from a draft row.

    The engine resolves a key in this order (lock-in 4):
      1. assignment.units_field
      2. the pay item key itself
    So we pass through every unit-ish field the draft carries, keyed both by
    the raw field name and by a normalized alias, and let the engine match.

    Draft rows may supply:
      - 'units': {name: qty}                  explicit map (preferred)
      - 'overtime_hours' / 'ot_hours'        shorthand for the common case
    """
    units = {}

    explicit = emp_data.get('units')
    if isinstance(explicit, dict):
        for k, v in explicit.items():
            if v is None or v == '':
                continue
            units[str(k)] = v

    for field in ('overtime_hours', 'ot_hours'):
        if emp_data.get(field) not in (None, ''):
            units.setdefault(field, emp_data[field])
            units.setdefault('overtime', emp_data[field])

    return units or None


def _decline_balances(employee_id, company_id, deduction_details):
    """Decrement remaining_balance on declining deductions after a run.

    The engine returns deduction_details without the ledger id for new
    assignment rows, so this walks the employee's declining deductions and
    applies the matched amount. Idempotent within a run: a deduction whose
    balance is already zero is skipped.
    """
    from decimal import Decimal

    from payroll_engine.models import EmployeeDeduction
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    # New-model rows: match on the item key we recorded in the detail dict.
    for detail in deduction_details or []:
        item_key = detail.get('item_key')
        if not item_key:
            continue
        amount = Decimal(str(detail.get('amount') or 0))
        if amount <= 0:
            continue
        rows = PayrollItemAssignment.query.filter_by(
            company_id=company_id,
            employee_id=employee_id,
            tracking_mode='declining',
            is_active=True,
        ).all()
        for a in rows:
            if a.item_type and a.item_type.key == item_key and a.remaining_balance is not None:
                a.remaining_balance = max(Decimal('0'), a.remaining_balance - amount)
                if a.remaining_balance <= 0:
                    a.is_active = False
                break

    # Legacy bridge rows carry their id in the detail dict.
    by_id = {d.get('id'): d for d in (deduction_details or []) if d.get('id')}
    if not by_id:
        return
    legacy = EmployeeDeduction.query.filter(
        EmployeeDeduction.employee_id == employee_id,
        EmployeeDeduction.company_id == company_id,
        EmployeeDeduction.tracking_mode == 'declining',
    ).all()
    for ded in legacy:
        detail = by_id.get(ded.id)
        if not detail or ded.remaining_balance is None:
            continue
        amount = Decimal(str(detail.get('amount') or 0))
        if amount <= 0:
            continue
        ded.remaining_balance = max(Decimal('0'), ded.remaining_balance - amount)
        if ded.remaining_balance <= 0:
            ded.is_active = False


def apply_flag_overrides(run_id, form_data):
    """Apply FLAG overrides from form data. Returns list of unresolved BLOCKs."""
    flags = PayrollValidationResult.query.filter_by(payroll_run_id=run_id, severity='FLAG').all()

    for i, flag in enumerate(flags):
        override_key = f'override_{i}'
        reason_key = f'reason_{i}'
        if form_data.get(override_key):
            flag.overridden = True
            flag.override_reason = form_data.get(reason_key, '')
            flag.overridden_by = form_data.get('_user_id')

    db.session.flush()

    # Check for unresolved BLOCKs
    blocks = (
        PayrollValidationResult.query.filter_by(payroll_run_id=run_id, severity='BLOCK')
        .filter(PayrollValidationResult.overridden.is_(False) | PayrollValidationResult.overridden.is_(None))
        .all()
    )

    return blocks


def process_payroll(run, company_id, user_id, user_email, request_ip):
    """
    Process an approved payroll run. Single transaction — all or nothing.

    Args:
        run: PayrollRun instance (already locked with FOR UPDATE)
        company_id: Company ID
        user_id: User ID of approver
        user_email: User email (for audit log)
        request_ip: Request IP (for audit log)

    Returns:
        ApprovalResult
    """
    draft = PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).first()
    if not draft:
        db.session.rollback()
        return ApprovalResult(
            success=False,
            message='Payroll data not found. The draft may have been deleted. Please re-upload the CSV.',
            redirect_to='upload',
        )

    if run.status in ('completed', 'locked', 'processing'):
        db.session.rollback()
        return ApprovalResult(
            success=False,
            message=f'Payroll run #{run.id} is already {run.status} and cannot be reprocessed.',
            redirect_to='runs',
        )

    employees_data = draft.employee_data

    try:
        run.status = 'processing'
        run.approved_by = user_id
        run.approved_at = datetime.now(UTC).replace(tzinfo=None)
        run.approval_ip = request_ip

        # Batch-fetch existing employees to avoid N+1 queries
        emp_ids = [emp_data['id'] for emp_data in employees_data]
        existing_emps = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.employee_id.in_(emp_ids),
            Employee.is_deleted == False,
        ).all()
        emp_by_eid = {e.employee_id: e for e in existing_emps}

        # --- BUG FIX: Compute leave reductions from actual Leave records ---
        # The draft has stale values; we need real leave data at approval time.
        from payroll_engine.models import Leave, EmployeeDeduction
        from payroll_engine.leave import LeaveType, DEFAULT_SICK_TIER_1_DAYS
        from decimal import Decimal

        today = date.today() if 'date' not in dir() else date.today()
        month_start = today.replace(day=1)

        # Pre-compute leave reductions per employee
        leave_reductions = {}  # emp_id -> (sick_reduction, unpaid_reduction)
        for emp in existing_emps:
            sick_reduction = Decimal('0')
            unpaid_reduction = Decimal('0')

            # Fetch approved leave for this employee in current month
            emp_leave = Leave.query.filter(
                Leave.employee_id == emp.id,
                Leave.company_id == company_id,
                Leave.status == 'approved',
                Leave.start_date <= today,
                Leave.end_date >= month_start,
            ).all()

            for lv in emp_leave:
                overlap_start = max(lv.start_date, month_start)
                overlap_end = min(lv.end_date, today)
                if overlap_start > overlap_end:
                    continue
                overlap_days = (overlap_end - overlap_start).days + 1
                daily_rate = (Decimal(str(emp.basic_salary)) + Decimal(str(emp.allowances))) / Decimal('30')

                if lv.leave_type == LeaveType.UNPAID:
                    unpaid_reduction += daily_rate * Decimal(str(overlap_days))
                elif lv.leave_type == LeaveType.SICK:
                    # Tiered: first SICK_TIER_1_DAYS at 100%, next at 50%, rest unpaid
                    # We need cumulative sick days in the 12-month period
                    year_ago = today.replace(year=today.year - 1)
                    sick_history = Leave.query.filter(
                        Leave.employee_id == emp.id,
                        Leave.company_id == company_id,
                        Leave.leave_type == LeaveType.SICK,
                        Leave.status == 'approved',
                        Leave.start_date >= year_ago,
                    ).all()
                    cumulative_sick = sum(lv2.days_requested for lv2 in sick_history)
                    tier1 = DEFAULT_SICK_TIER_1_DAYS

                    # Days in this leave that fall into each tier
                    days_at_100 = min(max(0, tier1 - (cumulative_sick - lv.days_requested)), overlap_days)
                    days_at_50 = min(max(0, overlap_days - days_at_100), max(0, (tier1 * 2) - (cumulative_sick - lv.days_requested) - days_at_100))
                    # Remaining are unpaid (100% reduction)
                    days_unpaid = overlap_days - days_at_100 - days_at_50

                    sick_reduction += daily_rate * Decimal(str(days_at_50)) * Decimal('0.5')
                    sick_reduction += daily_rate * Decimal(str(days_unpaid))  # unpaid portion

            leave_reductions[emp.id] = (sick_reduction.quantize(Decimal('0.01')), unpaid_reduction.quantize(Decimal('0.01')))

        # Pre-compute active deductions (advances, loans, etc.) per employee
        active_deductions = {}  # emp_id -> list of deduction dicts
        for emp in existing_emps:
            deductions = EmployeeDeduction.query.filter(
                EmployeeDeduction.employee_id == emp.id,
                EmployeeDeduction.company_id == company_id,
                EmployeeDeduction.is_active == True,
            ).all()
            emp_deds = []
            for ded in deductions:
                # For date-bounded, check if within range
                if ded.tracking_mode == 'date_bounded' and ded.end_date and ded.end_date < today:
                    continue
                # For declining, check exhausted
                if ded.tracking_mode == 'declining' and ded.remaining_balance is not None and ded.remaining_balance <= 0:
                    continue
                emp_deds.append(ded)
            active_deductions[emp.id] = emp_deds

        # Create/update employees and payslips
        # PDFs are generated lazily on download (not at approval time)
        from payroll_engine.payroll_elements import calculate_payroll_from_assignments

        for emp_data in employees_data:
            emp = emp_by_eid.get(emp_data['id'])
            if not emp:
                emp = Employee(
                    employee_id=emp_data['id'],
                    name=emp_data['name'],
                    basic_salary=emp_data['basic'],
                    allowances=emp_data['allowances'],
                    bank_or_telebirr=emp_data.get('bank', ''),
                    tin=emp_data.get('tin') or None,
                    company_id=company_id,
                )
                db.session.add(emp)
                db.session.flush()
                emp_by_eid[emp_data['id']] = emp
            else:
                emp.basic_salary = emp_data['basic']
                emp.allowances = emp_data['allowances']
                emp.bank_or_telebirr = emp_data.get('bank', '')
                if emp_data.get('tin'):
                    emp.tin = emp_data['tin']
                db.session.flush()

            # --- BUG FIX: Apply leave reductions and deductions ---
            sick_red, unpaid_red = leave_reductions.get(emp.id, (Decimal('0'), Decimal('0')))

            # ---- The bridge (spec: "new assignments if present, else old records")
            #
            # An employee with no pay-item assignments at all has not been
            # backfilled yet. The elements engine can only assemble gross FROM
            # assignments, so calling it blind returns gross=0 / net=0 and
            # silently pays the employee nothing. In that case keep the legacy
            # path (the draft's pre-computed figures) until the backfill
            # migration runs. Once the employee has any active assignment the
            # engine is authoritative.
            has_assignments = PayrollItemAssignment.query.filter_by(
                company_id=company_id, employee_id=emp.id, is_active=True
            ).first() is not None

            # Legacy CSV import: the draft row's `allowances` column was
            # annotated by the upload path. Materialise it as an assignment
            # BEFORE the bridge check, so an imported employee is not silently
            # treated as un-backfilled and dropped to the legacy path.
            if emp_data.get('general_allowance'):
                _ensure_general_allowance(
                    emp, company_id, emp_data.get('general_allowance')
                )
                has_assignments = True

            if has_assignments:
                # Basic salary must be represented as an assignment for gross to
                # include it. Without this an employee carrying only a General
                # Allowance row is paid 2,500 instead of 12,500.
                _ensure_basic_assignment(emp, company_id, emp_data.get('basic'))

                # Units for rate_x_units pay items (lock-in 4). The draft carries
                # whatever the upload/autosave collected; keys are matched against
                # assignment.units_field first, then the item key itself.
                units_input = _build_units_input(emp_data)

                # Overtime entries still come from their own module (spec 2d).
                ot_entries = [
                    {'hours': e.get('hours', 0), 'type': e.get('type', 'day')}
                    for e in (emp_data.get('overtime') or [])
                ]

                # Elements engine: reads the employee's active
                # PayrollItemAssignment rows for the run period. `deductions` is
                # the legacy bridge -- EmployeeDeduction rows are still honoured
                # until the backfill migration moves them, but they are no longer
                # computed by hand here. The engine merges bridge rows with new
                # assignment rows and returns the merged deduction_details.
                calc = calculate_payroll_from_assignments(
                    emp,
                    company_id,
                    today,
                    units_input=units_input,
                    overtime_entries=ot_entries or None,
                    deductions=active_deductions.get(emp.id, []) or None,
                    sick_leave_reduction=sick_red + unpaid_red,
                )

                deduction_details = calc['deduction_details']
                final_net = calc['net']
                gross = calc['gross']
                tax = calc['tax']
                pension_employee = calc['pension_employee']
                pension_employer = calc['pension_employer']
                line_items = calc.get('line_items')
            else:
                # Legacy path, unchanged: pre-computed draft figures, with the
                # hand-rolled deduction loop that pre-dates the engine.
                net_before_deductions = Decimal(str(emp_data['net'])) - sick_red - unpaid_red
                deduction_details = []
                total_deductions = Decimal('0')
                for ded in active_deductions.get(emp.id, []):
                    if ded.amount_mode == 'percentage':
                        ded_amount = (net_before_deductions * ded.amount / Decimal('100')).quantize(Decimal('0.01'))
                    else:
                        ded_amount = ded.amount
                    if ded.tracking_mode == 'declining' and ded.remaining_balance is not None:
                        ded_amount = min(ded_amount, ded.remaining_balance)
                    ded_amount = min(ded_amount, net_before_deductions - total_deductions)
                    if ded_amount > 0:
                        total_deductions += ded_amount
                        deduction_details.append({
                            'id': ded.id,
                            'type': ded.deduction_type,
                            'type_label': ded.type_label,
                            'label': ded.label,
                            'amount': float(ded_amount),
                            'remaining_balance': float(ded.remaining_balance) if ded.remaining_balance else None,
                        })
                        if ded.tracking_mode == 'declining' and ded.remaining_balance is not None:
                            ded.remaining_balance = max(Decimal('0'), ded.remaining_balance - ded_amount)
                            if ded.remaining_balance <= 0:
                                ded.is_active = False
                final_net = net_before_deductions - total_deductions
                gross = Decimal(str(emp_data['gross']))
                tax = Decimal(str(emp_data['tax']))
                pension_employee = Decimal(str(emp_data['pension_employee']))
                pension_employer = Decimal(str(emp_data['pension_employer']))
                line_items = None  # legacy path has no engine breakdown

            payslip = Payslip(
                payroll_run_id=run.id,
                employee_id=emp.id,
                company_id=company_id,
                pdf_status='not_generated',  # Lazy: generated on first download
                gross_salary=gross,
                tax=tax,
                employee_pension=pension_employee,
                employer_pension=pension_employer,
                net_pay=final_net.quantize(Decimal('0.01')),
                sick_leave_reduction=sick_red,
                unpaid_leave_reduction=unpaid_red,
                deduction_details=deduction_details,
                line_items=line_items,
            )
            db.session.add(payslip)

            # Decrement declining-balance balances from the engine's result so
            # the ledger stays in step with what was actually deducted.
            _decline_balances(emp.id, company_id, deduction_details)

        run.status = 'completed'

        # Compliance scoring
        from payroll_engine.models import Company

        company = db.session.get(Company, company_id)
        run_date_str = run.run_date.isoformat()
        score, _status = compute_compliance_score(
            company=company,
            payroll_date=run_date_str,
            disbursement_date=run.approved_at.date().isoformat() if run.approved_at else None,
        )

        # Audit log
        create_audit_log(
            company_id=company_id,
            user_id=user_id,
            action='payroll_run_completed',
            details={
                'run_id': run.id,
                'employee_count': len(employees_data),
                'compliance_score': score,
                'approved_by': user_email,
                'approval_ip': request_ip,
            },
        )

        # Notify each employee that their payslip is ready
        from payroll_engine.notifications import notify

        all_payslips = Payslip.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).all()
        for ps in all_payslips:
            emp = ps.employee
            if emp and emp.user_id:
                try:
                    notify(
                        company_id=company_id,
                        user_id=emp.user_id,
                        message=f'Your payslip for {run.period or "this month"} is ready. Net pay: ETB {ps.net_pay:,.2f}.',
                        notif_type='success',
                        link=f'/my/payslips/{ps.id}',
                        employee_phone=emp.phone,
                        whatsapp_message=f'Hello {emp.name}, your salary of ETB {ps.net_pay:,.2f} has been processed. Log in to view your payslip.',
                    )
                except Exception as e:
                    import logging

                    logging.getLogger('payroll_engine').error('Failed to notify employee %s: %s', emp.id, e)

        # Clean up draft
        PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).delete()

        # Notify the approver
        create_notification(
            company_id=company_id,
            user_id=user_id,
            message=f'Payroll processed: {len(employees_data)} employees paid, compliance score {score}%.',
            type='success',
            link=f'/payroll/runs/{run.id}',
        )

        # Single commit — all or nothing
        db.session.commit()

        # Trigger background PDF generation via RQ (or fall back to inline on download)
        from payroll_engine.tasks import enqueue_batch

        enqueue_batch(run.id, company_id)

        # Fire webhook — payroll completed
        try:
            from payroll_engine.webhooks import fire_webhook

            fire_webhook(
                company_id,
                'payroll.completed',
                {
                    'run_id': run.id,
                    'reference': run.reference,
                    'period': run.period,
                    'employee_count': len(employees_data),
                    'total_gross': float(sum(e.get('gross', 0) for e in employees_data)),
                    'total_tax': float(sum(e.get('tax', 0) for e in employees_data)),
                    'total_net': float(sum(e.get('net', 0) for e in employees_data)),
                    'compliance_score': score,
                },
            )
        except Exception:
            pass

        # Build result message
        message = f'Payroll processed! {len(employees_data)} employees paid, compliance score {score}%. PDFs will be generated on download.'

        return ApprovalResult(
            success=True,
            message=message,
            employee_count=len(employees_data),
            compliance_score=score,
            redirect_to='detail',
        )

    except Exception as e:
        # Roll back the entire approval attempt
        db.session.rollback()

        # Log the failure in a separate transaction
        try:
            failed_run = tenant_get(PayrollRun, run.id, company_id)
            if failed_run:
                failed_run.status = 'failed'
            create_audit_log(
                company_id=company_id,
                user_id=user_id,
                action='payroll_run_failed',
                details={'run_id': run.id, 'error': str(e)},
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

        return ApprovalResult(
            success=False,
            error=str(e),
            redirect_to='upload',
        )
