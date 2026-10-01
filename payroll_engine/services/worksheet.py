"""Validate and persist current-month worksheet inputs, without approval effects."""

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import abort

from payroll_engine import db
from payroll_engine.models import Employee, SpreadsheetInput
from payroll_engine.shared import create_audit_log

OT_FIELDS = ('ot_day', 'ot_night', 'ot_holiday', 'ot_rest')


def parse_changes(form, company_id):
    period_start = date.today().replace(day=1)
    if form.get('period_start') != period_start.isoformat():
        raise ValueError('The payroll month changed. Reload the worksheet before saving.')
    try:
        ids = [int(value) for value in form.getlist('emp_id')]
    except ValueError:
        abort(404)
    if any(value <= 0 or value > 2147483647 for value in ids):
        abort(404)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Select each employee once before saving.')
    # A stable employee lock serializes writes, including the first insertion.
    employees = (
        Employee.query.filter(Employee.company_id == company_id, Employee.id.in_(ids), Employee.is_deleted.is_(False))
        .order_by(Employee.id)
        .with_for_update()
        .all()
    )
    if len(employees) != len(ids):
        abort(404)
    changes = []
    for employee in employees:
        values = {'emp_id': employee.id, 'employee': employee}
        for field in (*OT_FIELDS, 'absences', 'advance', 'bonus'):
            raw = form.get(f'emp_{employee.id}_{field}', '0').strip() or '0'
            label = {'absences': 'Additional unpaid days', 'bonus': 'Bonus', 'advance': 'Advance'}.get(field, field)
            try:
                value = Decimal(raw)
                valid = value.is_finite() and value >= 0
                if field == 'absences':
                    valid = valid and value <= 30 and value == value.to_integral_value()
                elif field in OT_FIELDS:
                    valid = valid and value <= 200 and value % Decimal('0.5') == 0
                else:
                    valid = valid and value <= Decimal('9999999999.99') and value == value.quantize(Decimal('0.01'))
            except (InvalidOperation, ValueError):
                valid = False
            if not valid:
                rule = (
                    'a whole number from 0 to 30'
                    if field == 'absences'
                    else (
                        'hours from 0 to 200 in half-hour steps'
                        if field in OT_FIELDS
                        else 'a non-negative amount with at most two decimal places'
                    )
                )
                raise ValueError(f'{employee.employee_id}: {label} must be {rule}. No changes were saved.')
            values[field] = value
        if employee.employee_type == 'daily' and (values['bonus'] or values['absences']):
            raise ValueError(
                f'{employee.employee_id}: Additional unpaid days and bonus are currently supported for monthly employees only. No changes were saved.'
            )
        changes.append(values)
    return period_start, changes


def save_inputs(company_id, user_id, period_start, change):
    row = SpreadsheetInput.query.filter_by(
        company_id=company_id, employee_id=change['emp_id'], period_start=period_start
    ).first()
    before = {'bonus': str(row.bonus if row else Decimal('0')), 'absence_days': row.absence_days if row else 0}
    bonus, days = change['bonus'], int(change['absences'])
    if Decimal(before['bonus']) == bonus and before['absence_days'] == days:
        return
    if row is None:
        row = SpreadsheetInput(company_id=company_id, employee_id=change['emp_id'], period_start=period_start)
        db.session.add(row)
    row.bonus = bonus
    row.absence_days = days
    create_audit_log(
        company_id,
        user_id,
        'payroll.worksheet_inputs_saved',
        {
            'employee_id': change['emp_id'],
            'period_start': period_start.isoformat(),
            'previous': before,
            'new': {'bonus': str(bonus), 'absence_days': days},
        },
    )
