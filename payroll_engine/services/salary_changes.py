"""Guard salary writes and stage the audit evidence and owner notices."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from payroll_engine import db, shared
from payroll_engine.models import User, UserCompany

SALARY_REASONS = {
    'promotion': 'Promotion',
    'annual_raise': 'Annual raise',
    'correction': 'Correction',
    'new_hire': 'New hire',
    'other': 'Other',
}
SALARY_FIELDS = ('basic_salary', 'allowances')


class SalaryChangeRefusedError(ValueError):
    def __init__(self, message, status, employee_id=None):
        super().__init__(message)
        self.status = status
        self.employee_id = employee_id


def salary_amount(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or not 0 <= amount < Decimal('9999999999.995'):
        raise ValueError('Salary and allowances must be valid non-negative amounts.')
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def salary_values(employee, new_basic, new_allowances):
    """Return old and new amounts only for fields whose stored value changes."""
    old, new = {}, {}
    for field, value in zip(SALARY_FIELDS, (new_basic, new_allowances), strict=True):
        previous = getattr(employee, field) if employee is not None else Decimal('0.00')
        if previous != value:
            old[field], new[field] = format(previous, '.2f'), format(value, '.2f')
    return old, new


def check_salary_target(actor, employee):
    if employee is not None and employee.user_id == actor.id:
        raise SalaryChangeRefusedError('You cannot change your own salary.', 403, employee.employee_id)


def authorize_salary_change(company_id, actor, employee, fields):
    check_salary_target(actor, employee)
    employee_id = employee.employee_id if employee is not None else None
    membership = (
        UserCompany.query.filter_by(company_id=company_id, user_id=actor.id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    role = membership.role if membership else (actor.role if actor.company_id == company_id else None)
    if role != 'owner' and not (role == 'accountant' and membership and membership.can_edit_salary):
        raise SalaryChangeRefusedError('You do not have permission to edit salaries in this company.', 403, employee_id)

    choice = fields.get('salary_reason')
    note = fields.get('salary_note')
    if not isinstance(choice, str) or choice not in SALARY_REASONS or not isinstance(note, str) or not note.strip():
        raise SalaryChangeRefusedError('Select a salary change reason and enter a note.', 422, employee_id)
    if len(note.strip()) > 1000:
        raise SalaryChangeRefusedError('The salary change note must be 1,000 characters or fewer.', 422, employee_id)
    password = fields.get('password')
    if not isinstance(password, str) or not password or not actor.check_password(password):
        raise SalaryChangeRefusedError('Enter your correct password to save a salary change.', 422, employee_id)
    return {'choice': choice, 'note': note.strip()}


def record_salary_refusal(company_id, actor_id, refusal):
    # Only authorization denials produce a separate audit row. Roll back any
    # staged employee, draft or approval changes before writing that row.
    db.session.rollback()
    if refusal.status == 403:
        shared.create_audit_log(
            company_id=company_id,
            user_id=actor_id,
            action='permission_denied',
            details={'operation': 'salary_edit', 'employee_id': refusal.employee_id, 'reason': str(refusal)},
        )
        db.session.commit()


def stage_salary_change(company_id, actor, employee, reason, old, new, *, action, details=None, effective_date=None):
    effective_date = effective_date or datetime.now(ZoneInfo('Africa/Addis_Ababa')).date()
    shared.create_audit_log(
        company_id=company_id,
        user_id=actor.id,
        action=action,
        details={
            **(details or {}),
            'employee_id': employee.employee_id,
            'employee_name': employee.name,
            'old_values': old,
            'new_values': new,
            'reason': reason,
            'effective_date': effective_date.isoformat(),
        },
    )

    owners = UserCompany.query.filter_by(company_id=company_id).all()
    roles = {membership.user_id: membership.role for membership in owners}
    owner_ids = {uid for uid, role in roles.items() if role == 'owner'}
    # Retain support for owners of legacy companies that have no membership row.
    owner_ids.update(
        uid for (uid,) in db.session.query(User.id).filter_by(company_id=company_id, role='owner') if uid not in roles
    )
    actor_name = ' '.join(filter(None, (actor.first_name, actor.middle_name, actor.last_name)))
    actor_name = actor_name or actor.email or actor.phone or f'User {actor.id}'
    amounts = ', '.join(
        f'{field.replace("_", " ").capitalize()} ETB {old[field]} to ETB {value}'
        for field, value in new.items()
        if field in SALARY_FIELDS
    )
    label = SALARY_REASONS[reason['choice']]
    message = (
        f'{actor_name} changed salary for {employee.name} ({employee.employee_id}). '
        f'{amounts}. Reason: {label} ({reason["choice"]}) — {reason["note"]}. Effective {effective_date.isoformat()}.'
    )
    for owner_id in sorted(owner_ids):
        shared.create_notification(company_id, owner_id, message)
