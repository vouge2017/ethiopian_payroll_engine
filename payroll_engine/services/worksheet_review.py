"""Saved monthly worksheet reviews: pure preview, frozen amounts, one approval."""

import calendar
import json
from decimal import Decimal

from flask import abort

from payroll_engine import db
from payroll_engine.leave import DEFAULT_SICK_TIER_1_DAYS, LeaveType
from payroll_engine.models import (
    Company,
    Employee,
    EmployeeDeduction,
    Leave,
    OvertimeEntry,
    PayrollDraft,
    PayrollRun,
    PayrollValidationResult,
    Payslip,
    SpreadsheetInput,
)
from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment
from payroll_engine.payroll_elements import _load_employee_items, calculate_payroll_from_assignments
from payroll_engine.shared import create_audit_log

Q = Decimal('0.01')
MONEY_KEYS = (
    'basic',
    'allowances',
    'gross',
    'taxable',
    'tax',
    'pension_employee',
    'pension_employer',
    'net',
    'sick_leave_reduction',
    'unpaid_leave_reduction',
    'exempt_allowances',
    'total_deductions',
)


def month_end(start):
    return start.replace(day=calendar.monthrange(start.year, start.month)[1])


def _encoded(value):
    return json.loads(
        json.dumps(value, default=lambda item: str(item) if isinstance(item, Decimal) else item.isoformat())
    )


def display_rows(rows):
    """Copy JSON snapshots for numeric template/calculation helpers."""
    result = []
    for row in rows:
        copied = dict(row, **{key: Decimal(str(row[key])) for key in MONEY_KEYS if row.get(key) is not None})
        copied['line_items'] = [
            dict(item, earned_amount=Decimal(str(item['earned_amount']))) for item in row.get('line_items', [])
        ]
        result.append(copied)
    return result


def _earning(employee, key, label, amount, *, tax_treatment='taxable', exempt_cap=None):
    item = PayItemType(
        key=key,
        name_en=label,
        classification='earning',
        calculation_method='fixed',
        tax_treatment=tax_treatment,
        exempt_cap_amount=exempt_cap,
        is_active=True,
        sort_order=0,
    )
    return PayrollItemAssignment(
        company_id=employee.company_id, employee_id=employee.id, item_type=item, fixed_amount=amount, is_active=True
    )


def _leave_reductions(employee, start, end):
    daily = (employee.basic_salary + employee.allowances) / 30
    sick, unpaid = Decimal('0'), Decimal('0')
    year_ago = end.replace(year=end.year - 1, day=min(end.day, calendar.monthrange(end.year - 1, end.month)[1]))
    history = Leave.query.filter(
        Leave.company_id == employee.company_id,
        Leave.employee_id == employee.id,
        Leave.status == 'approved',
        Leave.start_date <= end,
        Leave.end_date >= year_ago,
    ).all()
    cumulative_sick = sum(
        lv.days_requested for lv in history if lv.leave_type == LeaveType.SICK and lv.start_date >= year_ago
    )
    for leave in history:
        overlap_start, overlap_end = max(start, leave.start_date), min(end, leave.end_date)
        if overlap_start > overlap_end:
            continue
        days = (overlap_end - overlap_start).days + 1
        if leave.leave_type == LeaveType.UNPAID:
            unpaid += daily * days
        elif leave.leave_type == LeaveType.SICK:
            before = cumulative_sick - leave.days_requested
            full = min(max(0, DEFAULT_SICK_TIER_1_DAYS - before), days)
            half = min(max(0, days - full), max(0, 2 * DEFAULT_SICK_TIER_1_DAYS - before - full))
            sick += daily * (Decimal(half) / 2 + days - full - half)
    return sick.quantize(Q), unpaid.quantize(Q)


def _balance_state(row):
    return {
        'is_active': row.is_active,
        'remaining_balance': str(row.remaining_balance) if row.remaining_balance is not None else None,
    }


def calculate_rows(company_id, start, *, lock=False):
    """Use the elements engine without consuming balances or writing assignments."""
    end = month_end(start)
    query = Employee.query.filter_by(company_id=company_id, is_deleted=False).order_by(Employee.id)
    employees = query.with_for_update().all() if lock else query.all()
    if not employees:
        raise ValueError('Add employees before preparing a payroll review.')
    rows = []
    for employee in employees:
        if employee.employee_type == 'daily':
            raise ValueError(
                f'{employee.employee_id}: daily-worker attendance must be confirmed before worksheet review is supported. Use the established daily-worker workflow.'
            )
        items = _load_employee_items(employee.id, company_id, end)
        if any(item.rate_per_unit is not None for bucket in items.values() for item in bucket):
            raise ValueError(
                f'{employee.employee_id}: a pay item requires units that this worksheet does not capture. Complete that payroll through the itemized workflow.'
            )
        if any(
            item.item_type.key == 'advance'
            and item.end_date is None
            and item.effective_date
            and item.effective_date < start
            for item in items['deductions']
        ):
            raise ValueError(
                f'{employee.employee_id}: an older advance has no end date. Reconcile that advance before review so it cannot repeat.'
            )
        basic_items = [item for item in items['earnings'] if item.item_type.key == 'basic_salary']
        if len(basic_items) > 1 or (basic_items and basic_items[0].fixed_amount != employee.basic_salary):
            raise ValueError(
                f'{employee.employee_id}: reconcile the basic salary pay item with the employee salary before review.'
            )
        extras = [] if basic_items else [_earning(employee, 'basic_salary', 'Basic Salary', employee.basic_salary)]
        if not [item for item in items['earnings'] if item.item_type.key != 'basic_salary']:
            allowances = [
                record
                for record in employee.allowance_records
                if record.is_active
                and (record.effective_date is None or record.effective_date <= end)
                and (record.end_date is None or record.end_date >= end)
            ]
            if allowances:
                for record in allowances:
                    extras.append(
                        _earning(
                            employee,
                            record.allowance_type,
                            record.custom_type_name or record.allowance_type,
                            record.amount,
                            tax_treatment='partial',
                            exempt_cap=record.calculated_exempt_amount,
                        )
                    )
            elif employee.allowances:
                extras.append(_earning(employee, 'general_allowance', 'General Allowance', employee.allowances))
        saved = SpreadsheetInput.query.filter_by(
            company_id=company_id, employee_id=employee.id, period_start=start
        ).first()
        bonus, absence_days = (saved.bonus, saved.absence_days) if saved else (Decimal('0'), 0)
        if bonus:
            extras.append(_earning(employee, 'worksheet_bonus', 'Monthly Bonus', bonus))
        overtime = (
            OvertimeEntry.query.filter(
                OvertimeEntry.company_id == company_id,
                OvertimeEntry.employee_id == employee.id,
                OvertimeEntry.date >= start,
                OvertimeEntry.date <= end,
            )
            .order_by(OvertimeEntry.id)
            .all()
        )
        ot = [{'hours': entry.hours, 'type': entry.overtime_type} for entry in overtime]
        backfilled = {item.legacy_source for bucket in items.values() for item in bucket if item.legacy_source}
        deductions = (
            EmployeeDeduction.query.filter(
                EmployeeDeduction.company_id == company_id,
                EmployeeDeduction.employee_id == employee.id,
                EmployeeDeduction.is_active.is_(True),
            )
            .order_by(EmployeeDeduction.id)
            .all()
        )
        deductions = [
            ded
            for ded in deductions
            if f'legacy_deduction:{ded.id}' not in backfilled
            and (ded.start_date is None or ded.start_date <= end)
            and (ded.end_date is None or ded.end_date >= end)
        ]
        sick, unpaid = _leave_reductions(employee, start, end)
        unpaid += ((employee.basic_salary + employee.allowances) / 30 * absence_days).quantize(Q)
        result = calculate_payroll_from_assignments(
            employee,
            company_id,
            end,
            overtime_entries=ot or None,
            deductions=deductions or None,
            extra_items=extras,
            sick_leave_reduction=sick + unpaid,
            consume_balances=False,
        )
        if result['net'] < 0:
            raise ValueError(f'{employee.employee_id}: deductions exceed available pay. Resolve this before review.')
        for key, label, amount in (
            ('unpaid_leave', 'Unpaid days deduction', unpaid),
            ('sick_leave', 'Sick leave reduction', sick),
        ):
            if amount:
                result['line_items'].append(
                    {
                        'item_key': key,
                        'item_label': label,
                        'classification': 'deduction',
                        'earned_amount': amount,
                        'is_deduction': True,
                        'is_system': False,
                    }
                )
        ledgers = []
        assignment_by_id = {item.id: item for item in items['deductions']}
        legacy_by_id = {ded.id: ded for ded in deductions}
        for detail in result['deduction_details']:
            is_assignment = detail.get('assignment_id') is not None
            ledger = assignment_by_id.get(detail['assignment_id']) if is_assignment else legacy_by_id.get(detail['id'])
            if ledger is not None and ledger.tracking_mode == 'declining':
                ledgers.append(
                    {
                        'kind': 'assignment' if is_assignment else 'legacy',
                        'id': ledger.id,
                        'amount': str(detail['amount']),
                        'before': _balance_state(ledger),
                    }
                )
        rows.append(
            _encoded(
                {
                    'id': employee.employee_id,
                    'employee_pk': employee.id,
                    'name': employee.name,
                    'basic': employee.basic_salary,
                    'allowances': employee.allowances,
                    'bank': employee.bank_account or employee.bank_or_telebirr or '',
                    'tin': employee.tin or '',
                    'department': employee.department or '',
                    'position': employee.position or '',
                    **{
                        key: result[key]
                        for key in (
                            'gross',
                            'taxable',
                            'tax',
                            'pension_employee',
                            'pension_employer',
                            'net',
                            'exempt_allowances',
                            'total_deductions',
                            'deduction_details',
                            'line_items',
                        )
                    },
                    'sick_leave_reduction': sick,
                    'unpaid_leave_reduction': unpaid,
                    'worksheet_inputs': {'bonus': str(bonus.quantize(Q)), 'absence_days': absence_days, 'overtime': ot},
                    'worksheet_period_start': start.isoformat(),
                    'calculation_date': end.isoformat(),
                    'balance_movements': ledgers,
                }
            )
        )
    return rows


def create_review(company_id, user_id, start, refresh_run_id=None):
    """Serialize review creation on the company; existing reviews are immutable by default."""
    from payroll_engine.services.payroll_workflow import build_period_string

    if refresh_run_id is not None:
        run = PayrollRun.query.filter_by(id=refresh_run_id, company_id=company_id).with_for_update().first_or_404()
        if run.source != 'spreadsheet' or run.status != 'review' or run.run_date != start:
            raise ValueError('Only an unapproved worksheet review for this month can be refreshed.')
    else:
        Company.query.filter_by(id=company_id).with_for_update().one()
        period = build_period_string(start)
        existing = PayrollRun.query.filter(
            PayrollRun.company_id == company_id,
            PayrollRun.status.notin_(['failed', 'rejected']),
            db.or_(
                PayrollRun.period == period,
                db.and_(PayrollRun.run_date >= start, PayrollRun.run_date <= month_end(start)),
            ),
        ).first()
        if existing:
            return existing
        run = PayrollRun(company_id=company_id, run_date=start, source='spreadsheet', status='review', period=period)
        db.session.add(run)
        db.session.flush()
        run.generate_reference()
    rows = calculate_rows(company_id, start, lock=True)
    draft = PayrollDraft.query.filter_by(company_id=company_id, payroll_run_id=run.id).first()
    if draft is None:
        draft = PayrollDraft(company_id=company_id, payroll_run_id=run.id)
        db.session.add(draft)
    draft.employee_data = rows
    PayrollValidationResult.query.filter_by(payroll_run_id=run.id).delete()
    from payroll_engine.validation import validate_payroll_data

    for result in validate_payroll_data(display_rows(rows), company_id=company_id):
        db.session.add(
            PayrollValidationResult(
                payroll_run_id=run.id,
                rule_code=result.rule_code,
                severity=result.severity,
                message=result.message,
                details_json=result.details,
            )
        )
    create_audit_log(
        company_id,
        user_id,
        'payroll.worksheet_review_refreshed' if refresh_run_id else 'payroll.worksheet_review_created',
        {
            'run_id': run.id,
            'period_start': start.isoformat(),
            'employee_count': len(rows),
            'total_net': str(sum(Decimal(row['net']) for row in rows)),
        },
    )
    return run


def apply_approved_rows(run, company_id, rows):
    """Persist frozen figures; balance locks and checks precede any writes."""
    if run.company_id != company_id or not rows:
        abort(404)
    ids = [row['employee_pk'] for row in rows]
    employees = (
        Employee.query.filter(Employee.company_id == company_id, Employee.id.in_(ids), Employee.is_deleted.is_(False))
        .order_by(Employee.id)
        .with_for_update()
        .all()
    )
    if len(employees) != len(set(ids)) or len(ids) != len(set(ids)):
        raise ValueError('A reviewed employee is no longer available. Refresh the review before approval.')
    ledgers = []
    for row in sorted(rows, key=lambda row: row['employee_pk']):
        if row['worksheet_period_start'] != run.run_date.isoformat():
            raise ValueError('The review month does not match this run. Refresh the review.')
        for movement in sorted(row['balance_movements'], key=lambda movement: (movement['kind'], movement['id'])):
            model = PayrollItemAssignment if movement['kind'] == 'assignment' else EmployeeDeduction
            ledger = (
                model.query.filter_by(id=movement['id'], employee_id=row['employee_pk'], company_id=company_id)
                .with_for_update()
                .first()
            )
            if ledger is None or _balance_state(ledger) != movement['before']:
                raise ValueError('A deduction balance changed since review. Please refresh the review before approval.')
            amount = Decimal(movement['amount'])
            if amount < 0 or ledger.remaining_balance is None or amount > ledger.remaining_balance:
                raise ValueError('A reviewed deduction is no longer available. Refresh the review.')
            ledgers.append((ledger, amount))
    for row in rows:
        db.session.add(
            Payslip(
                company_id=company_id,
                payroll_run_id=run.id,
                employee_id=row['employee_pk'],
                gross_salary=Decimal(row['gross']),
                tax=Decimal(row['tax']),
                employee_pension=Decimal(row['pension_employee']),
                employer_pension=Decimal(row['pension_employer']),
                net_pay=Decimal(row['net']),
                sick_leave_reduction=Decimal(row['sick_leave_reduction']),
                unpaid_leave_reduction=Decimal(row['unpaid_leave_reduction']),
                exempt_allowances=Decimal(row['exempt_allowances']),
                taxable_income=Decimal(row['taxable']),
                deduction_details=row['deduction_details'],
                line_items=row['line_items'],
                pdf_status='not_generated',
            )
        )
    for ledger, amount in ledgers:
        ledger.remaining_balance -= amount
        if ledger.remaining_balance <= 0:
            ledger.is_active = False


def published_row(payslip):
    """Reuse retained approved facts for both inline and worker output."""
    run = PayrollRun.query.filter_by(id=payslip.payroll_run_id, company_id=payslip.company_id).first()
    if run is None or run.source != 'spreadsheet':
        return None
    draft = PayrollDraft.query.filter_by(company_id=payslip.company_id, payroll_run_id=run.id).first()
    if draft is None:
        raise ValueError('The approved worksheet snapshot is missing. Contact support before exporting.')
    row = next((row for row in draft.employee_data if row.get('employee_pk') == payslip.employee_id), None)
    if row is None:
        raise ValueError('The approved employee snapshot is missing.')
    return display_rows([row])[0]


def review_evidence(run, rows):
    """Report actual saved amounts before payslips exist; no invented compliance verdict."""
    from payroll_engine.evidence import EvidenceReport, Signal

    active_ids = {employee.id for employee in Employee.query.filter_by(company_id=run.company_id, is_deleted=False)}
    reviewed_ids = {row['employee_pk'] for row in rows}
    complete = bool(rows) and reviewed_ids == active_ids and len(rows) == len(reviewed_ids)
    gross = sum((row['gross'] for row in rows), Decimal('0'))
    net = sum((row['net'] for row in rows), Decimal('0'))
    deductions = sum(
        (
            row['tax']
            + row['pension_employee']
            + row['total_deductions']
            + row['sick_leave_reduction']
            + row['unpaid_leave_reduction']
            for row in rows
        ),
        Decimal('0'),
    )
    balanced = bool(rows) and all(
        row['gross']
        == row['tax']
        + row['pension_employee']
        + row['total_deductions']
        + row['sick_leave_reduction']
        + row['unpaid_leave_reduction']
        + row['net']
        for row in rows
    )
    return EvidenceReport(
        signals=[
            Signal(
                name='Employees in saved review',
                status='pass' if complete else 'fail',
                category='validation',
                explanation='The saved review is compared with this company’s active employees.',
                detail=f'{len(reviewed_ids)}/{len(active_ids)} employees',
                blocking=True,
            ),
            Signal(
                name='Saved amounts balanced',
                status='pass' if balanced else 'fail',
                category='integrity',
                explanation='Gross equals tax, pension, other deductions, leave deductions and net for every reviewed employee.',
                detail=f'Gross ETB {gross:,.2f} = total deductions ETB {deductions:,.2f} + net ETB {net:,.2f}',
                blocking=True,
            ),
        ]
    )
