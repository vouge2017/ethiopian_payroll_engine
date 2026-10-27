"""Bulk import of employee pay-item assignments (catalog PR 5).

A CSV or Excel file with one row per assignment:

    employee_id, item_key, amount, start_date, end_date, amount_type, label

``employee_id``, ``item_key`` and ``amount`` are required. ``amount_type`` is
``fixed`` (default), ``percent_of_basic`` (earnings) or ``percent_of_net``
(deductions). Dates are Gregorian ``YYYY-MM-DD``; a blank start date means
"no start date". ``label`` is required for deductions.

Flow: ``plan_import`` validates every row and says what would happen
(create / update / unchanged / error) without writing anything (dry run).
``apply_import`` re-validates the same rows and writes them only when no row
has an error (all or nothing). Re-importing the same file is a no-op
(every row ``unchanged``), so an import can be repeated safely.

Matching: an existing assignment is "the same row" when employee, item and
start date match (and, for deductions, the label). Same values: unchanged.
Different values on an assignment no approved payslip used: updated in
place. On a used assignment: an error (change it from a date on the
employee page, or import a row with a new start date after ending it).

Employee IDs are matched exactly (after trimming spaces). Rows are rejected,
never guessed, when:
  * no employee has that exact ID but one does after dropping leading zeros
    or letter case (e.g. "1" vs "0001": format the column as text);
  * the cell was a number in Excel (leading zeros lost) and the company has
    more than one ID that reads as that number (e.g. "1" and "0001");
  * the same employee + item + start date (+ label) appears twice in the file;
  * the employee is deleted.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal

from payroll_engine import db
from payroll_engine.models_payroll_elements import PayItemClassification, PayItemType, PayrollItemAssignment
from payroll_engine.services import employee_assignments as ea

MAX_ROWS = 2000
COLUMNS = ('employee_id', 'item_key', 'amount', 'start_date', 'end_date', 'amount_type', 'label')
REQUIRED = ('employee_id', 'item_key', 'amount')
_HEADER_ALIASES = {
    'employee': 'employee_id',
    'emp_id': 'employee_id',
    'employee_code': 'employee_id',
    'staff_id': 'employee_id',
    'id': 'employee_id',
    'item': 'item_key',
    'pay_item': 'item_key',
    'pay_item_key': 'item_key',
    'key': 'item_key',
    'code': 'item_key',
    'value': 'amount',
    'start': 'start_date',
    'from': 'start_date',
    'effective_date': 'start_date',
    'end': 'end_date',
    'to': 'end_date',
    'type': 'amount_type',
    'mode': 'amount_type',
    'description': 'label',
}


class ImportFileError(ValueError):
    """The file itself cannot be read (not a row problem)."""


@dataclass
class ImportRow:
    """One file row: raw values, and whether employee_id came from a numeric Excel cell."""

    number: int
    values: dict
    numeric_id: bool = False


@dataclass
class RowResult:
    number: int
    raw: dict
    action: str = 'error'  # create | update | unchanged | error
    errors: list = field(default_factory=list)
    message: str = ''
    employee: object = None
    item: object = None
    mode: str | None = None
    value: Decimal | None = None
    start: object = None
    end: object = None
    label: str | None = None
    existing: object = None

    @property
    def ok(self):
        return not self.errors


@dataclass
class ImportPlan:
    rows: list
    header_errors: list = field(default_factory=list)

    @property
    def errors(self):
        return [r for r in self.rows if r.errors]

    @property
    def counts(self):
        out = {'create': 0, 'update': 0, 'unchanged': 0, 'error': 0}
        for r in self.rows:
            out['error' if r.errors else r.action] += 1
        return out

    @property
    def can_apply(self):
        return not self.header_errors and not self.errors and any(r.action in ('create', 'update') for r in self.rows)


# ---------------------------------------------------------------------------
# Reading the file
# ---------------------------------------------------------------------------


def _norm_header(h):
    h = re.sub(r'[^a-z0-9_]', '_', str(h or '').strip().lower())
    h = re.sub(r'_+', '_', h).strip('_')
    return _HEADER_ALIASES.get(h, h)


def _cell_text(value):
    if value is None:
        return ''
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()[:10]
    return str(value).strip()


def read_rows(file_storage):
    """Rows of an uploaded .csv or .xlsx file (header row first)."""
    filename = (getattr(file_storage, 'filename', '') or '').lower()
    if filename.endswith('.csv'):
        import csv
        import io

        try:
            text = file_storage.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ImportFileError('The CSV file is not UTF-8 text. Save it as "CSV UTF-8" and upload again.') from None
        reader = csv.reader(io.StringIO(text))
        table = [list(r) for r in reader]
        numeric = None
    elif filename.endswith('.xlsx'):
        import openpyxl

        try:
            wb = openpyxl.load_workbook(file_storage.stream, read_only=True, data_only=True)
        except Exception:
            raise ImportFileError('The Excel file could not be read. Upload an .xlsx file.') from None
        ws = wb.active
        table = [list(r) for r in ws.iter_rows(values_only=True)]
        wb.close()
        numeric = True
    else:
        raise ImportFileError('Upload a .csv or .xlsx file.')
    if not table:
        raise ImportFileError('The file is empty.')
    headers = [_norm_header(h) for h in table[0]]
    rows = []
    for index, raw in enumerate(table[1:], start=2):
        if not raw or all(c is None or str(c).strip() == '' for c in raw):
            continue
        values, numeric_id = {}, False
        for i, cell in enumerate(raw):
            if i >= len(headers) or not headers[i]:
                continue
            if headers[i] == 'employee_id' and numeric and isinstance(cell, (int, float)):
                numeric_id = True
            values[headers[i]] = _cell_text(cell)
        rows.append(ImportRow(number=index, values=values, numeric_id=numeric_id))
    if len(rows) > MAX_ROWS:
        raise ImportFileError(f'The file has {len(rows)} rows; the limit is {MAX_ROWS}. Split it into smaller files.')
    return headers, rows


# ---------------------------------------------------------------------------
# Employee ID matching
# ---------------------------------------------------------------------------


def canonical_id(text):
    """Case-folded ID with leading zeros dropped from every digit run ("EMP001" -> "emp1", "0001" -> "1")."""
    return re.sub(r'\d+', lambda m: str(int(m.group())), str(text).strip().casefold())


class EmployeeDirectory:
    def __init__(self, company_id):
        from payroll_engine.models import Employee

        self.active = {}
        self.deleted = set()
        self.by_canonical = {}
        for emp in Employee.with_deleted().filter_by(company_id=company_id).all():
            if emp.is_deleted:
                self.deleted.add(emp.employee_id)
                continue
            self.active[emp.employee_id] = emp
            self.by_canonical.setdefault(canonical_id(emp.employee_id), []).append(emp.employee_id)

    def match(self, raw, numeric_cell=False):
        """(employee, error)."""
        text = (raw or '').strip()
        if not text:
            return None, 'employee_id is empty.'
        similar = [e for e in self.by_canonical.get(canonical_id(text), []) if e != text]
        if numeric_cell and similar:
            ids = ', '.join(sorted(similar + ([text] if text in self.active else [])))
            return None, (
                f'employee_id {text} was a number in Excel, so leading zeros may have been lost, and more than one '
                f'employee matches it ({ids}). Format the column as text and type the exact ID.'
            )
        if text in self.active:
            return self.active[text], None
        if text in self.deleted:
            return None, f'Employee {text} is deleted.'
        if similar:
            return None, (
                f'No employee has the ID "{text}". Did you mean {", ".join(sorted(similar))}? '
                'Use the exact ID (format the column as text so leading zeros stay).'
            )
        return None, f'No employee has the ID "{text}".'


# ---------------------------------------------------------------------------
# Planning (dry run)
# ---------------------------------------------------------------------------


def _same_values(existing, mode, value, end, label):
    return (
        ea.mode_of(existing) == mode
        and Decimal(ea.value_of(existing)) == value
        and existing.end_date == end
        and (existing.custom_label or None) == (label or None)
    )


def plan_import(company_id, headers, rows, *, confirm_legacy=False):
    """Validate every row; write nothing."""
    plan = ImportPlan(rows=[])
    missing = [c for c in REQUIRED if c not in headers]
    if missing:
        plan.header_errors.append(f'Missing column(s): {", ".join(missing)}. Expected columns: {", ".join(COLUMNS)}.')
        return plan
    directory = EmployeeDirectory(company_id)
    items = {i.key: i for i in PayItemType.query.filter_by(company_id=company_id).all()}
    used_cache = {}
    keys_seen = {}
    pending_earnings = {}  # employee id -> True when this file adds a catalog earning
    for row in rows:
        v = row.values
        res = RowResult(number=row.number, raw={c: v.get(c, '') for c in COLUMNS})
        plan.rows.append(res)
        emp, err = directory.match(v.get('employee_id'), row.numeric_id)
        if err:
            res.errors.append(err)
        res.employee = emp
        key = (v.get('item_key') or '').strip()
        try:
            if not key:
                raise ea.AssignmentError('item_key is empty.')
            item = items.get(key)
            res.item = (
                ea.assignable_item(company_id, item_id=item.id) if item else ea.assignable_item(company_id, key=key)
            )
        except ea.AssignmentError as exc:
            res.errors.append(str(exc))
        if res.item is not None:
            try:
                res.mode = ea.clean_mode(res.item, v.get('amount_type'))
                res.value = ea.clean_value(res.mode, v.get('amount'))
            except ea.AssignmentError as exc:
                res.errors.append(str(exc))
            try:
                res.label = ea.clean_label(res.item, v.get('label'))
            except ea.AssignmentError as exc:
                res.errors.append(str(exc))
        for name, column, what in (('start', 'start_date', 'Start date'), ('end', 'end_date', 'End date')):
            try:
                setattr(res, name, ea.parse_date(v.get(column), what=what))
            except ea.AssignmentError as exc:
                res.errors.append(str(exc))
        if res.start and res.end and res.end < res.start:
            res.errors.append('End date is before the start date.')
        if emp is None or res.item is None:
            continue
        identity = (emp.id, res.item.id, res.start, res.label if _is_deduction(res.item) else None)
        if identity in keys_seen:
            first = keys_seen[identity]
            msg = f'Same employee, item and start date as row {first.number}. Keep one row.'
            res.errors.append(msg)
            if not any('Same employee' in e for e in first.errors):
                first.errors.append(f'Same employee, item and start date as row {res.number}. Keep one row.')
            continue
        keys_seen[identity] = res
        if res.errors:
            continue
        _plan_against_existing(company_id, res, used_cache)
        if res.ok and res.action == 'create' and res.item.classification == PayItemClassification.EARNING:
            if not confirm_legacy and not pending_earnings.get(emp.id):
                try:
                    ea._check_legacy(company_id, emp, res.item, False)
                except ea.LegacyAllowanceConfirmationError as exc:
                    res.errors.append(str(exc) + ' Tick the confirmation box to import anyway.')
            pending_earnings[emp.id] = True
    _check_in_file_overlaps(plan)
    return plan


def _is_deduction(item):
    return item.classification == PayItemClassification.DEDUCTION


def _plan_against_existing(company_id, res, used_cache):
    emp, item = res.employee, res.item
    rows = PayrollItemAssignment.query.filter_by(
        company_id=company_id, employee_id=emp.id, pay_item_type_id=item.id, is_active=True
    ).all()
    same = [
        a
        for a in rows
        if a.effective_date == res.start and (not _is_deduction(item) or (a.custom_label or None) == res.label)
    ]
    if len(same) > 1:
        res.errors.append(
            f'{emp.employee_id} already has more than one {item.name_en} assignment starting '
            f'{res.start or "with no start date"}. Fix them on the employee page first.'
        )
        return
    if same:
        existing = same[0]
        res.existing = existing
        if ea.mode_of(existing) == 'rate_x_units':
            res.errors.append('The existing assignment is rate-times-units; it cannot be changed by import.')
            return
        if _same_values(existing, res.mode, res.value, res.end, res.label):
            res.action, res.message = 'unchanged', 'Already imported; nothing to change.'
            return
        if emp.id not in used_cache:
            used_cache[emp.id] = ea.usage(company_id, emp.id)
        if existing.id in used_cache[emp.id]:
            res.errors.append(
                f'This {item.name_en} assignment is already used in approved payroll, so the import cannot change '
                'it. Change the amount from a date on the employee page, or end it and import a row with a new '
                'start date.'
            )
            return
        others = [a for a in rows if a.id != existing.id]
    else:
        others = rows
    for other in others:
        if not ea._windows_overlap(res.start, res.end, other.effective_date, other.end_date):
            continue
        if _is_deduction(item) and (other.custom_label or None) != res.label:
            continue
        since = other.effective_date.isoformat() if other.effective_date else 'no start date'
        until = other.end_date.isoformat() if other.end_date else 'no end date'
        res.errors.append(
            f'Overlaps the existing {item.name_en} assignment ({since} to {until}). End it first or change the dates.'
        )
        return
    if same:
        res.action, res.message = 'update', 'Will update the existing assignment (not used in approved payroll yet).'
    else:
        res.action, res.message = 'create', 'Will add a new assignment.'


def _check_in_file_overlaps(plan):
    by_key = {}
    for res in plan.rows:
        if res.errors or res.employee is None or res.item is None:
            continue
        group = (res.employee.id, res.item.id, res.label if _is_deduction(res.item) else None)
        by_key.setdefault(group, []).append(res)
    for group_rows in by_key.values():
        for i, a in enumerate(group_rows):
            for b in group_rows[i + 1 :]:
                if ea._windows_overlap(a.start, a.end, b.start, b.end):
                    for x, y in ((a, b), (b, a)):
                        x.errors.append(f'Dates overlap row {y.number} for the same employee and item.')


# ---------------------------------------------------------------------------
# Applying
# ---------------------------------------------------------------------------


def apply_import(company_id, user_id, headers, rows, *, confirm_legacy=False):
    """Re-validate and write every row, or nothing. Returns the plan (caller commits on success)."""
    plan = plan_import(company_id, headers, rows, confirm_legacy=confirm_legacy)
    if not plan.can_apply:
        return plan
    for res in plan.rows:
        if res.action == 'create':
            ea.create_assignment(
                company_id,
                user_id,
                res.employee,
                res.item,
                mode=res.mode,
                value=res.value,
                start=res.start,
                end=res.end,
                label=res.label,
                confirm_legacy=True,  # checked per employee in plan_import
                source='import',
            )
        elif res.action == 'update':
            ea.update_assignment(
                company_id,
                user_id,
                res.existing,
                mode=res.mode,
                value=res.value,
                end=res.end,
                label=res.label,
                start=res.start,
                source='import',
            )
    db.session.flush()
    return plan


def rows_to_payload(rows):
    """Serialise rows for the confirm form (re-validated on apply)."""
    return [{'n': r.number, 'v': r.values, 'num': r.numeric_id} for r in rows]


def rows_from_payload(payload):
    out = []
    for entry in payload or []:
        if not isinstance(entry, dict) or not isinstance(entry.get('v'), dict):
            raise ImportFileError('The preview has expired. Upload the file again.')
        values = {str(k): str(v) for k, v in entry['v'].items() if str(k) in COLUMNS}
        out.append(ImportRow(number=int(entry.get('n') or 0), values=values, numeric_id=bool(entry.get('num'))))
    if len(out) > MAX_ROWS:
        raise ImportFileError('Too many rows.')
    return out
