"""Employee pay-item assignments from the company catalog (catalog PR 5).

One place for every rule about adding, changing, ending and deleting a
``PayrollItemAssignment`` from the employee page, the assignment import and
the JSON bulk import. Routes only parse the request and show the result.

Rules
-----
* Only the company's own, active earning and deduction items can be
  assigned. Shared system items (basic salary, pension, income tax) are
  calculated by the engine and are never assigned here.
* Amount types: ``fixed`` (ETB per month), ``percent_of_basic`` (earnings)
  and ``percent_of_net`` (deductions). Rate-times-units items are not offered
  (the worksheet review cannot capture units yet).
* An assignment is **used** once an approved payslip carries it (its id in
  the payslip's line items or deduction details). A used assignment is never
  deleted and its past is never rewritten: its amount changes only from a
  date after the last approved month that used it (the old row is
  end-dated the day before and a new row starts), and it can only be ended
  on or after the end of that month. An unused assignment can be edited in
  place or deleted.
* Earnings: one running assignment per item per employee (date windows may
  not overlap). Deductions need a label and may overlap when the labels
  differ (two loans).
* Legacy allowances: the worksheet review pays an employee's legacy
  ``EmployeeAllowance`` records or ``Employee.allowances`` figure **only
  while the employee has no catalog earning other than basic salary**.
  Adding the first catalog earning therefore stops those legacy figures. That
  needs an explicit confirmation (``confirm_legacy``), never a silent switch.
* ``PayItemType.default_amount`` pre-fills new fixed assignments; an
  assignment whose own amount differs is shown as a per-employee override.
  Payroll always reads the amount stored on the assignment.

Every change writes an audit-log row. Callers commit.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from payroll_engine import db
from payroll_engine.models_payroll_elements import (
    PayItemClassification,
    PayItemType,
    PayrollItemAssignment,
    check_assignment_tenancy,
)
from payroll_engine.shared import create_audit_log

Q = Decimal('0.01')

MODE_FIXED = 'fixed'
MODE_PERCENT_OF_BASIC = 'percent_of_basic'
MODE_PERCENT_OF_NET = 'percent_of_net'

#: Amount types offered per classification (first = default).
MODES = {
    PayItemClassification.EARNING: (MODE_FIXED, MODE_PERCENT_OF_BASIC),
    PayItemClassification.DEDUCTION: (MODE_FIXED, MODE_PERCENT_OF_NET),
}
MODE_LABELS = {
    MODE_FIXED: 'ETB per month',
    MODE_PERCENT_OF_BASIC: '% of basic salary',
    MODE_PERCENT_OF_NET: '% of net pay',
}
_MODE_COLUMN = {
    MODE_FIXED: 'fixed_amount',
    MODE_PERCENT_OF_BASIC: 'percent_of_basic',
    MODE_PERCENT_OF_NET: 'percent_of_net',
}
MAX_FIXED = Decimal('9999999999.99')  # Numeric(12, 2)
LABEL_MAX = 100
REFERENCE_MAX = 100


class AssignmentError(ValueError):
    """A change was refused; the message is safe to show the user."""


class LegacyAllowanceConfirmationError(AssignmentError):
    """Adding the first catalog earning would stop the employee's legacy allowance figures."""


def month_end(d):
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def assignable_items(company_id):
    """The company's own active earning and deduction items, in catalog order."""
    return (
        PayItemType.query.filter(
            PayItemType.company_id == company_id,
            PayItemType.is_active.is_(True),
            PayItemType.is_system.is_(False),
            PayItemType.classification.in_([PayItemClassification.EARNING, PayItemClassification.DEDUCTION]),
        )
        .order_by(PayItemType.classification.desc(), PayItemType.sort_order, PayItemType.id)
        .all()
    )


def assignable_item(company_id, *, item_id=None, key=None):
    """The assignable item with this id or key, or raise AssignmentError."""
    q = PayItemType.query.filter(PayItemType.company_id == company_id)
    item = q.filter(PayItemType.id == item_id).first() if item_id is not None else q.filter_by(key=key).first()
    shown = key if key is not None else item_id
    if item is None:
        system = PayItemType.query.filter_by(company_id=None, key=key).first() if key else None
        if system is not None:
            raise AssignmentError(
                f'"{system.name_en}" is calculated by the system each month and cannot be assigned to an employee.'
            )
        raise AssignmentError(f'"{shown}" is not a pay item in your company catalog.')
    if item.is_system:
        raise AssignmentError(f'"{item.name_en}" is calculated by the system and cannot be assigned.')
    if item.classification not in MODES:
        raise AssignmentError(f'"{item.name_en}" is not an earning or a deduction and cannot be assigned.')
    if not item.is_active:
        raise AssignmentError(f'"{item.name_en}" is deactivated in your pay item settings.')
    return item


def employee_assignments(company_id, employee_id):
    """Every assignment of one employee (active or not), oldest first."""
    return (
        PayrollItemAssignment.query.filter_by(company_id=company_id, employee_id=employee_id)
        .order_by(
            PayrollItemAssignment.pay_item_type_id, PayrollItemAssignment.effective_date, PayrollItemAssignment.id
        )
        .all()
    )


def usage(company_id, employee_id):
    """{assignment id: latest approved run date} for assignments carried by approved payslips."""
    from payroll_engine.models import PayrollRun, Payslip

    rows = (
        db.session.query(Payslip.line_items, Payslip.deduction_details, PayrollRun.run_date)
        .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)
        .filter(
            Payslip.company_id == company_id,
            Payslip.employee_id == employee_id,
            PayrollRun.company_id == company_id,
        )
        .all()
    )
    used = {}
    for line_items, deduction_details, run_date in rows:
        ids = set()
        for entry in list(line_items or []) + list(deduction_details or []):
            if isinstance(entry, dict) and entry.get('assignment_id') is not None:
                ids.add(entry['assignment_id'])
        for assignment_id in ids:
            prev = used.get(assignment_id)
            if prev is None or (run_date is not None and run_date > prev):
                used[assignment_id] = run_date
    return used


def first_open_date(last_used_run_date):
    """First day after the month of the last approved run that used an assignment."""
    if last_used_run_date is None:
        return None
    return month_end(last_used_run_date) + timedelta(days=1)


def mode_of(assignment):
    for mode, column in _MODE_COLUMN.items():
        if getattr(assignment, column) is not None:
            return mode
    if assignment.rate_per_unit is not None:
        return 'rate_x_units'
    return MODE_FIXED


def value_of(assignment):
    mode = mode_of(assignment)
    if mode == 'rate_x_units':
        return assignment.rate_per_unit
    return getattr(assignment, _MODE_COLUMN[mode])


def status_of(assignment, today):
    if not assignment.is_active:
        return 'inactive'
    if assignment.end_date is not None and assignment.end_date < today:
        return 'ended'
    if assignment.effective_date is not None and assignment.effective_date > today:
        return 'scheduled'
    return 'active'


@dataclass
class AssignmentView:
    assignment: PayrollItemAssignment
    item: PayItemType
    status: str
    mode: str
    value: Decimal
    used: bool
    last_used: date | None
    first_open: date | None
    is_override: bool
    managed: bool  # basic salary and other system rows: shown, not edited here
    can_delete: bool
    warnings: list = field(default_factory=list)

    @property
    def label(self):
        return self.assignment.custom_label or self.item.name_en


def employee_view(company_id, employee, today=None):
    """Rows for the employee page, newest first within each item."""
    today = today or date.today()
    used = usage(company_id, employee.id)
    rows = []
    for a in employee_assignments(company_id, employee.id):
        item = a.item_type
        mode = mode_of(a)
        value = value_of(a)
        managed = item is None or item.company_id is None or item.is_system or mode == 'rate_x_units'
        is_override = (
            not managed
            and mode == MODE_FIXED
            and item.default_amount is not None
            and value is not None
            and Decimal(value) != Decimal(item.default_amount)
        )
        last = used.get(a.id)
        rows.append(
            AssignmentView(
                assignment=a,
                item=item,
                status=status_of(a, today),
                mode=mode,
                value=value,
                used=a.id in used,
                last_used=last,
                first_open=first_open_date(last) if a.id in used else None,
                is_override=is_override,
                managed=managed,
                can_delete=not managed and a.id not in used,
            )
        )
    order = {'active': 0, 'scheduled': 1, 'ended': 2, 'inactive': 3}
    rows.sort(key=lambda r: (order[r.status], r.item.sort_order if r.item else 0, r.assignment.id))
    return rows


def legacy_allowance_total(employee, for_date=None):
    """ETB of legacy allowance figures the worksheet pays while there is no catalog earning."""
    for_date = for_date or date.today()
    records = [
        r
        for r in employee.allowance_records
        if r.is_active
        and (r.effective_date is None or r.effective_date <= for_date)
        and (r.end_date is None or r.end_date >= for_date)
    ]
    if records:
        return sum((Decimal(r.amount or 0) for r in records), Decimal('0'))
    return Decimal(employee.allowances or 0)


def has_catalog_earning(company_id, employee_id, exclude_id=None):
    """True when the employee has an active catalog earning other than basic salary."""
    q = (
        db.session.query(PayrollItemAssignment.id)
        .join(PayItemType, PayrollItemAssignment.pay_item_type_id == PayItemType.id)
        .filter(
            PayrollItemAssignment.company_id == company_id,
            PayrollItemAssignment.employee_id == employee_id,
            PayrollItemAssignment.is_active.is_(True),
            PayItemType.classification == PayItemClassification.EARNING,
            PayItemType.key != 'basic_salary',
            db.or_(PayrollItemAssignment.end_date.is_(None), PayrollItemAssignment.end_date >= date.today()),
        )
    )
    if exclude_id is not None:
        q = q.filter(PayrollItemAssignment.id != exclude_id)
    return q.first() is not None


# ---------------------------------------------------------------------------
# Parsing (shared by the employee page and the imports)
# ---------------------------------------------------------------------------


def parse_amount(raw, *, what='Amount'):
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise AssignmentError(f'{what} is required.')
    text = str(raw).strip().replace(',', '')
    for token in ('ETB', 'etb', 'Birr', 'birr', '%'):
        text = text.replace(token, '')
    try:
        value = Decimal(text.strip())
    except (InvalidOperation, ValueError):
        raise AssignmentError(f'{what} "{raw}" is not a number.') from None
    if not value.is_finite():
        raise AssignmentError(f'{what} "{raw}" is not a number.')
    if value != value.quantize(Q):
        raise AssignmentError(f'{what} "{raw}" has more than two decimal places.')
    return value.quantize(Q, rounding=ROUND_HALF_UP)


def parse_date(raw, *, what='Date', required=False):
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if required:
            raise AssignmentError(f'{what} is required.')
        return None
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise AssignmentError(f'{what} "{raw}" is not a date. Use YYYY-MM-DD (Gregorian).') from None


def clean_mode(item, mode):
    allowed = MODES[item.classification]
    mode = (mode or allowed[0]).strip()
    if mode not in allowed:
        raise AssignmentError(f'"{mode}" is not an amount type for {item.name_en}. Use one of: {", ".join(allowed)}.')
    return mode


def clean_value(mode, raw):
    value = parse_amount(raw, what='Percentage' if mode != MODE_FIXED else 'Amount')
    if value <= 0:
        raise AssignmentError('Amount must be more than zero.')
    if mode == MODE_FIXED and value > MAX_FIXED:
        raise AssignmentError('Amount is too large.')
    if mode != MODE_FIXED and value > 100:
        raise AssignmentError('A percentage cannot be more than 100.')
    return value


def clean_label(item, label):
    label = (label or '').strip()
    if len(label) > LABEL_MAX:
        raise AssignmentError(f'Label is longer than {LABEL_MAX} characters.')
    if item.classification == PayItemClassification.DEDUCTION and not label:
        raise AssignmentError('A deduction needs a label (e.g. "Staff loan 2026").')
    return label or None


def _windows_overlap(a_start, a_end, b_start, b_end):
    lo = max(a_start or date.min, b_start or date.min)
    hi = min(a_end or date.max, b_end or date.max)
    return lo <= hi


def _check_overlap(company_id, employee_id, item, start, end, label, exclude_ids=()):
    rows = PayrollItemAssignment.query.filter_by(
        company_id=company_id, employee_id=employee_id, pay_item_type_id=item.id, is_active=True
    ).all()
    for other in rows:
        if other.id in exclude_ids:
            continue
        if not _windows_overlap(start, end, other.effective_date, other.end_date):
            continue
        if item.classification == PayItemClassification.DEDUCTION and (other.custom_label or '') != (label or ''):
            continue
        since = other.effective_date.isoformat() if other.effective_date else 'the start'
        until = other.end_date.isoformat() if other.end_date else 'no end date'
        raise AssignmentError(
            f'{item.name_en} already runs for this employee ({since} to {until}). '
            'End that assignment first, or choose dates that do not overlap.'
        )


def _check_legacy(company_id, employee, item, confirm_legacy, exclude_id=None):
    if item.classification != PayItemClassification.EARNING or confirm_legacy:
        return
    if has_catalog_earning(company_id, employee.id, exclude_id=exclude_id):
        return
    legacy = legacy_allowance_total(employee)
    if legacy > 0:
        raise LegacyAllowanceConfirmationError(
            f'{employee.name} has legacy allowances of ETB {legacy:,.2f} that are not catalog items yet. '
            'Once an employee has a catalog earning, monthly payroll pays only catalog items, so those legacy '
            'allowances stop. Add them as catalog items too, then confirm.'
        )


def _audit(company_id, user_id, action, assignment, employee, item, **extra):
    create_audit_log(
        company_id=company_id,
        user_id=user_id,
        action=action,
        details={
            'assignment_id': assignment.id,
            'employee_id': employee.employee_id if employee is not None else None,
            'item_key': item.key,
            **{k: (str(v) if isinstance(v, (Decimal, date)) else v) for k, v in extra.items()},
        },
    )


def _employee(company_id, assignment):
    from payroll_engine.models import Employee

    return Employee.query.filter_by(id=assignment.employee_id, company_id=company_id).first()


def get_assignment(company_id, assignment_id):
    return PayrollItemAssignment.query.filter_by(id=assignment_id, company_id=company_id).first()


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def create_assignment(
    company_id,
    user_id,
    employee,
    item,
    *,
    mode=None,
    value,
    start=None,
    end=None,
    label=None,
    reference=None,
    confirm_legacy=False,
    source='employee_page',
):
    """Add a new assignment of ``item`` to ``employee``. Returns the row (flushed)."""
    if employee.company_id != company_id or employee.is_deleted:
        raise AssignmentError('Employee not found.')
    mode = clean_mode(item, mode)
    value = clean_value(mode, value)
    start = parse_date(start, what='Start date')
    end = parse_date(end, what='End date')
    if start and end and end < start:
        raise AssignmentError('End date is before the start date.')
    label = clean_label(item, label)
    reference = (reference or '').strip() or None
    if reference and len(reference) > REFERENCE_MAX:
        raise AssignmentError(f'Reference is longer than {REFERENCE_MAX} characters.')
    _check_overlap(company_id, employee.id, item, start, end, label)
    _check_legacy(company_id, employee, item, confirm_legacy)
    check_assignment_tenancy(company_id, employee.id, item.id)
    a = PayrollItemAssignment(
        company_id=company_id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        custom_label=label,
        reference_number=reference,
        effective_date=start,
        end_date=end,
        is_active=True,
        created_by=user_id,
    )
    setattr(a, _MODE_COLUMN[mode], value)
    if item.classification == PayItemClassification.DEDUCTION:
        a.tracking_mode = 'date_bounded'
    db.session.add(a)
    db.session.flush()
    _audit(
        company_id,
        user_id,
        'pay_item_assignment_created',
        a,
        employee,
        item,
        mode=mode,
        value=value,
        start=start,
        end=end,
        label=label,
        source=source,
        default_amount=item.default_amount,
    )
    return a


def update_assignment(
    company_id,
    user_id,
    assignment,
    *,
    mode=None,
    value=None,
    end=None,
    label=None,
    start=None,
    change_from=None,
    confirm_legacy=False,
    source='employee_page',
):
    """Change an assignment. Returns the row that now carries the change.

    Unused: edited in place (amount, type, start, end, label).
    Used: label and end date change in place; an amount or type change
    needs ``change_from`` (a date after the last approved month that used it):
    the row is end-dated the day before and a new row starts on that date.
    """
    item = assignment.item_type
    employee = _employee(company_id, assignment)
    if item is None or employee is None or item.company_id is None or item.is_system:
        raise AssignmentError('This assignment is managed by the system and cannot be edited here.')
    if mode_of(assignment) == 'rate_x_units':
        raise AssignmentError('Rate-times-units assignments cannot be edited here yet.')
    if not assignment.is_active:
        raise AssignmentError('This assignment is inactive and cannot be edited.')
    used = usage(company_id, employee.id)
    used_on = used.get(assignment.id)
    is_used = assignment.id in used

    old_mode, old_value = mode_of(assignment), value_of(assignment)
    new_mode = clean_mode(item, mode or old_mode)
    new_value = clean_value(new_mode, value) if value not in (None, '') else Decimal(old_value)
    new_end = parse_date(end, what='End date')
    new_label = clean_label(item, label if label is not None else assignment.custom_label)
    new_start = parse_date(start, what='Start date') if start not in (None, '') else assignment.effective_date
    money_changed = new_mode != old_mode or Decimal(new_value) != Decimal(old_value)

    if not is_used:
        if new_start and new_end and new_end < new_start:
            raise AssignmentError('End date is before the start date.')
        _check_overlap(company_id, employee.id, item, new_start, new_end, new_label, exclude_ids=(assignment.id,))
        before = {
            'mode': old_mode,
            'value': str(old_value),
            'start': assignment.effective_date.isoformat() if assignment.effective_date else None,
            'end': assignment.end_date.isoformat() if assignment.end_date else None,
            'label': assignment.custom_label,
        }
        for column in _MODE_COLUMN.values():
            setattr(assignment, column, None)
        setattr(assignment, _MODE_COLUMN[new_mode], new_value)
        assignment.effective_date = new_start
        assignment.end_date = new_end
        assignment.custom_label = new_label
        db.session.flush()
        _audit(
            company_id,
            user_id,
            'pay_item_assignment_updated',
            assignment,
            employee,
            item,
            before=before,
            mode=new_mode,
            value=new_value,
            start=new_start,
            end=new_end,
            label=new_label,
            source=source,
        )
        return assignment

    # Used: never rewrite approved months.
    open_from = first_open_date(used_on)
    if new_start != assignment.effective_date:
        raise AssignmentError(
            'This assignment is used in approved payroll, so its start date cannot change. '
            'Change the amount from a date instead.'
        )
    if not money_changed:
        if new_end is not None and open_from is not None and new_end < open_from - timedelta(days=1):
            raise AssignmentError(
                f'This assignment was paid in approved payroll up to {used_on:%B %Y}. '
                f'End it on {(open_from - timedelta(days=1)).isoformat()} or later.'
            )
        before = {
            'end': assignment.end_date.isoformat() if assignment.end_date else None,
            'label': assignment.custom_label,
        }
        assignment.end_date = new_end
        assignment.custom_label = new_label
        db.session.flush()
        _audit(
            company_id,
            user_id,
            'pay_item_assignment_updated',
            assignment,
            employee,
            item,
            before=before,
            end=new_end,
            label=new_label,
            used=True,
            source=source,
        )
        return assignment

    change_from = parse_date(change_from, what='Change from', required=True)
    if open_from is not None and change_from < open_from:
        raise AssignmentError(
            f'This assignment was paid in approved payroll up to {used_on:%B %Y}. '
            f'A new amount can start on {open_from.isoformat()} or later.'
        )
    if assignment.effective_date is not None and change_from <= assignment.effective_date:
        raise AssignmentError('The change must start after the assignment started.')
    if new_end is not None and new_end < change_from:
        raise AssignmentError('End date is before the change date.')
    if assignment.end_date is not None and change_from > assignment.end_date:
        raise AssignmentError('The assignment has already ended before that date.')
    successor = PayrollItemAssignment(
        company_id=company_id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        custom_label=new_label,
        reference_number=assignment.reference_number,
        document_path=assignment.document_path,
        units_field=assignment.units_field,
        effective_date=change_from,
        end_date=new_end,
        is_active=True,
        created_by=user_id,
        tracking_mode=assignment.tracking_mode,
        total_to_recover=assignment.remaining_balance if assignment.tracking_mode == 'declining' else None,
        remaining_balance=assignment.remaining_balance if assignment.tracking_mode == 'declining' else None,
    )
    setattr(successor, _MODE_COLUMN[new_mode], new_value)
    _check_overlap(
        company_id,
        employee.id,
        item,
        successor.effective_date,
        successor.end_date,
        new_label,
        exclude_ids=(assignment.id,),
    )
    assignment.end_date = change_from - timedelta(days=1)
    db.session.add(successor)
    db.session.flush()
    _audit(
        company_id,
        user_id,
        'pay_item_assignment_revised',
        successor,
        employee,
        item,
        replaces_assignment_id=assignment.id,
        old_mode=old_mode,
        old_value=old_value,
        mode=new_mode,
        value=new_value,
        change_from=change_from,
        end=successor.end_date,
        label=new_label,
        source=source,
    )
    return successor


def end_assignment(company_id, user_id, assignment, end, *, source='employee_page'):
    """End-date an assignment (never deletes)."""
    end = parse_date(end, what='End date', required=True)
    item = assignment.item_type
    employee = _employee(company_id, assignment)
    if item is None or employee is None or item.company_id is None or item.is_system:
        raise AssignmentError('This assignment is managed by the system and cannot be ended here.')
    if assignment.effective_date is not None and end < assignment.effective_date:
        raise AssignmentError('End date is before the start date.')
    used_on = usage(company_id, employee.id).get(assignment.id)
    if used_on is not None:
        last_paid = month_end(used_on)
        if end < last_paid:
            raise AssignmentError(
                f'This assignment was paid in approved payroll up to {used_on:%B %Y}. '
                f'End it on {last_paid.isoformat()} or later.'
            )
    before = assignment.end_date
    assignment.end_date = end
    db.session.flush()
    _audit(
        company_id,
        user_id,
        'pay_item_assignment_ended',
        assignment,
        employee,
        item,
        end=end,
        before=before,
        source=source,
    )
    return assignment


def delete_assignment(company_id, user_id, assignment):
    """Delete an assignment that no approved payslip used."""
    item = assignment.item_type
    employee = _employee(company_id, assignment)
    if item is None or employee is None or item.company_id is None or item.is_system:
        raise AssignmentError('This assignment is managed by the system and cannot be deleted here.')
    if assignment.id in usage(company_id, employee.id):
        raise AssignmentError(
            'This assignment is used in approved payroll, so it cannot be deleted. End-date it instead.'
        )
    referenced = PayrollItemAssignment.query.filter_by(company_id=company_id, percent_of_item_id=assignment.id).first()
    if referenced is not None:
        raise AssignmentError('Another assignment is calculated from this one, so it cannot be deleted.')
    details = {'mode': mode_of(assignment), 'value': value_of(assignment), 'label': assignment.custom_label}
    _audit(company_id, user_id, 'pay_item_assignment_deleted', assignment, employee, item, **details)
    db.session.delete(assignment)
    db.session.flush()


# ---------------------------------------------------------------------------
# Company default amount (settings page)
# ---------------------------------------------------------------------------


def set_default_amount(item, user_id, raw):
    """Set or clear a company item's default monthly amount. Returns True if changed."""
    if item.company_id is None or item.is_system:
        raise AssignmentError('System items have no default amount.')
    if item.classification not in MODES:
        raise AssignmentError('Only earnings and deductions have a default amount.')
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        new = None
    else:
        new = clean_value(MODE_FIXED, raw)
    old = item.default_amount
    if (old is None and new is None) or (old is not None and new is not None and Decimal(old) == new):
        return False
    item.default_amount = new
    db.session.flush()
    create_audit_log(
        company_id=item.company_id,
        user_id=user_id,
        action='pay_item_default_amount_changed',
        details={
            'pay_item_id': item.id,
            'key': item.key,
            'old': str(old) if old is not None else None,
            'new': str(new) if new is not None else None,
        },
    )
    return True


# ---------------------------------------------------------------------------
# Written consent for deductions (catalog PR 6, Labour Proc. 1156/2019 Art. 59)
# ---------------------------------------------------------------------------

CONSENT_NOTE_MAX = 200


def _consent_values(on_file, note):
    note = (note or '').strip() or None
    if note and len(note) > CONSENT_NOTE_MAX:
        raise AssignmentError(f'Consent note is longer than {CONSENT_NOTE_MAX} characters.')
    if on_file and not note:
        raise AssignmentError('Say where the written consent is kept (e.g. "Signed form, HR file 12, 2026-10-02").')
    return bool(on_file), note


def _apply_consent(target, user_id, on_file, note):
    from datetime import UTC, datetime

    before = {'on_file': bool(target.deduction_consent_on_file), 'note': target.deduction_consent_note}
    target.deduction_consent_on_file = on_file
    target.deduction_consent_note = note
    target.deduction_consent_recorded_at = datetime.now(UTC).replace(tzinfo=None)
    target.deduction_consent_recorded_by = user_id
    return before


def set_assignment_consent(company_id, user_id, assignment, on_file, note):
    """Record (or withdraw) the employee's written consent for one deduction assignment."""
    item = assignment.item_type
    if item is None or item.classification != PayItemClassification.DEDUCTION:
        raise AssignmentError('Written consent applies to deductions only.')
    on_file, note = _consent_values(on_file, note)
    if bool(assignment.deduction_consent_on_file) == on_file and assignment.deduction_consent_note == note:
        return False
    before = _apply_consent(assignment, user_id, on_file, note)
    db.session.flush()
    _audit(
        company_id,
        user_id,
        'deduction_consent_changed',
        assignment,
        _employee(company_id, assignment),
        item,
        before=before,
        on_file=on_file,
        note=note,
    )
    return True


def set_employee_consent(company_id, user_id, employee, on_file, note):
    """Record (or withdraw) an employee's written consent covering all their deductions."""
    if employee.company_id != company_id:
        raise AssignmentError('Employee not found.')
    on_file, note = _consent_values(on_file, note)
    if bool(employee.deduction_consent_on_file) == on_file and employee.deduction_consent_note == note:
        return False
    before = _apply_consent(employee, user_id, on_file, note)
    db.session.flush()
    create_audit_log(
        company_id=company_id,
        user_id=user_id,
        action='employee_deduction_consent_changed',
        details={'employee_id': employee.employee_id, 'before': before, 'on_file': on_file, 'note': note},
    )
    return True
