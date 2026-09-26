"""Data backfill: EmployeeAllowance / EmployeeDeduction -> PayrollItemAssignment.

This is NOT an Alembic migration. It is an idempotent, resumable data
conversion run via `flask migrate-pay-items`, because it must be re-runnable,
support --dry-run, and be reportable per company.

Design rules:
  * Per-company atomic. One transaction per company: either every row for that
    company converts or none of them do. A failure rolls that company back and
    records the error; other companies still run.
  * Idempotent. Every created assignment is tagged in `reference_number` as
    `legacy_basic:<employee_id>` or `legacy_allowance:<id>` /
    `legacy_deduction:<id>`. A second run finds those tags and creates nothing.
    No extra column or migration needed.
  * Old rows are NEVER deleted in this phase. The read bridge keeps honouring
    them until the deprecation step.
  * Basic salary is migrated FIRST, so no employee can end up holding
    assignments without a basic_salary row (the underpayment hole).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation



BASIC_TAG = 'legacy_basic'
ALLOWANCE_TAG = 'legacy_allowance'
DEDUCTION_TAG = 'legacy_deduction'

BASIC_KEY = 'basic_salary'


def _same_key(a, b) -> bool:
    """Case/whitespace-insensitive key comparison.

    NOTE: catalog._norm() is for NUMERIC fields -- it calls Decimal() and will
    raise InvalidOperation on a string key. Do not use it here.
    """
    return str(a).strip().lower() == str(b).strip().lower()


def _tag(kind: str, ident) -> str:
    return f'{kind}:{ident}'


def _D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == '':
        return Decimal('0')
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _already_backfilled(company_id, tag) -> bool:
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    return (
        PayrollItemAssignment.query.filter_by(
            company_id=company_id, legacy_source=tag
        ).first()
        is not None
    )


# ---------------------------------------------------------------------------
# PayItemType resolution
# ---------------------------------------------------------------------------


def _resolve_type(company_id, key, classification, label=None):
    """Find the company's PayItemType for `key`, creating it from the template.

    A company may legitimately have customised the template row (renamed it,
    changed its tax treatment). If the row already exists we never overwrite it
    -- the company owns its catalog. We only create from
    COMPANY_TEMPLATE_ITEMS when the company genuinely lacks the item.
    """
    from payroll_engine import db
    from payroll_engine.models import PayItemCalcMethod
    from payroll_engine.catalog import COMPANY_TEMPLATE_ITEMS
    from payroll_engine.models_payroll_elements import PayItemType

    item = PayItemType.query.filter_by(company_id=company_id, key=key).first()
    if item is not None:
        return item, False

    tmpl = next((t for t in COMPANY_TEMPLATE_ITEMS if _same_key(t.get('key'), key)), None)
    if tmpl is None:
        # Unknown key in legacy data (e.g. a custom_type_name the catalog never
        # defined). Create a minimal company item so the money is not lost.
        item = PayItemType(
            company_id=company_id,
            key=key,
            name_en=label or key,
            name_am=None,
            classification=classification,
            calculation_method='fixed',
            tax_treatment='taxable',
            is_system=False,
        )
    else:
        item = PayItemType(
            company_id=company_id,
            key=tmpl['key'],
            name_en=tmpl.get('name_en'),
            name_am=tmpl.get('name_am'),
            classification=tmpl.get('classification', classification),
            calculation_method=tmpl.get('calculation_method', 'fixed'),
            tax_treatment=tmpl.get('tax_treatment', 'taxable'),
            exempt_cap_amount=tmpl.get('exempt_cap_amount'),
            exempt_cap_percent=tmpl.get('exempt_cap_percent'),
            exempt_cap_basis=tmpl.get('exempt_cap_basis'),
            max_percent_of_net=tmpl.get('max_percent_of_net'),
            regulation_reference=tmpl.get('regulation_reference'),
            sort_order=tmpl.get('sort_order'),
            is_system=False,
        )
    from payroll_engine import db

    db.session.add(item)
    db.session.flush()
    return item, True


# ---------------------------------------------------------------------------
# effective_date rule for basic salary
# ---------------------------------------------------------------------------


def basic_effective_date(employee, legacy_rows):
    """The rule for a backfilled basic_salary assignment's effective_date.

    Chosen so the assignment covers every period the employee could legally be
    paid for -- back-dating it to the earliest real datum means no payroll run
    is ever evaluated against a window where basic pay does not exist.

    Order:
      1. Employee.start_date          -- employment start, the true origin.
      2. Earliest effective/start date among the employee's legacy rows.
      3. The date of the company's earliest payroll run, if any.
      4. Today (last resort; company has no history at all).
    """
    if employee.start_date:
        return employee.start_date

    dates = []
    for row in legacy_rows:
        d = getattr(row, 'effective_date', None) or getattr(row, 'start_date', None)
        if d:
            dates.append(d)
    if dates:
        return min(dates)

    from payroll_engine.models import PayrollRun

    first_run = (
        PayrollRun.query.filter_by(company_id=employee.company_id)
        .order_by(PayrollRun.run_date.asc())
        .first()
    )
    if first_run and first_run.run_date:
        return first_run.run_date.date() if hasattr(first_run.run_date, 'date') else first_run.run_date

    return date.today()


# ---------------------------------------------------------------------------
# Per-row conversion
# ---------------------------------------------------------------------------


def _assign_common(a, emp, item, company_id, tag, effective, legacy_is_active, label=None):
    a.company_id = company_id
    a.employee_id = emp.id
    a.pay_item_type_id = item.id
    a.effective_date = effective
    a.is_active = bool(legacy_is_active)
    a.legacy_source = tag
    a.custom_label = label
    return a


def _convert_allowance(allowance, emp, company_id, effective):
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    key = (allowance.allowance_type or 'other').strip() or 'other'
    label = allowance.custom_type_name or None
    item, _created = _resolve_type(company_id, key, 'earning', label=label)

    a = PayrollItemAssignment()
    _assign_common(
        a, emp, item, company_id,
        _tag(ALLOWANCE_TAG, allowance.id),
        effective, allowance.is_active,
        label=label or item.name_en,
    )
    a.end_date = allowance.end_date

    basis = (allowance.calculation_basis or 'fixed').strip().lower()
    if basis == 'percentage':
        pct = _D(allowance.amount)
        of = (allowance.percentage_of or 'basic_salary').strip().lower()
        if of in ('gross_salary', 'gross'):
            # The engine has no percent-of-gross; percent_of_basic is the
            # closest faithful mapping and is recorded on the type.
            a.percent_of_basic = pct
        else:
            a.percent_of_basic = pct
    else:
        a.fixed_amount = _D(allowance.amount)

    created_by = getattr(allowance, 'created_by', None)
    if created_by:
        a.created_by = created_by
    return a


def _ensure_calc_method(item, method, conflicts):
    """Align a PayItemType's calculation_method with the legacy row's mode.

    The engine switches on item_type.calculation_method, NOT on which column
    the assignment happens to populate. Every deduction template ships as
    'fixed', so a legacy percentage deduction written to assignment.percent_of_net
    was read as fixed_amount (None) and deducted ZERO -- the money stayed with
    the employee. This is the overpayment.

    If a company uses the same item both ways, the last one wins and the
    conflict is reported so an operator can look, rather than being silently
    mangled.
    """
    if method is None or item.calculation_method == method:
        return
    if item.calculation_method not in (None, '', 'fixed') and (
        item.calculation_method != method
    ):
        pair = (item.key, item.calculation_method, method)
        if pair not in conflicts:
            conflicts.append(pair)
    item.calculation_method = method


def _convert_deduction(deduction, emp, company_id, effective, conflicts):
    from payroll_engine.models import PayItemCalcMethod
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    key = (deduction.deduction_type or 'other_deduction').strip() or 'other_deduction'
    item, _created = _resolve_type(company_id, key, 'deduction')

    a = PayrollItemAssignment()
    _assign_common(
        a, emp, item, company_id,
        _tag(DEDUCTION_TAG, deduction.id),
        effective, deduction.is_active,
        label=deduction.label or item.name_en,
    )
    a.end_date = deduction.end_date
    a.tracking_mode = deduction.tracking_mode
    a.total_to_recover = deduction.total_to_recover
    a.remaining_balance = deduction.remaining_balance
    # Preserve the court-order / MoE document trail verbatim.
    a.reference_number = deduction.reference_number
    a.document_path = deduction.document_path

    mode = (deduction.amount_mode or 'fixed').strip().lower()
    if mode == 'percentage':
        _ensure_calc_method(item, PayItemCalcMethod.PERCENT_OF_NET, conflicts)
        a.percent_of_net = _D(deduction.amount)
    else:
        _ensure_calc_method(item, PayItemCalcMethod.FIXED, conflicts)
        a.fixed_amount = _D(deduction.amount)

    created_by = getattr(deduction, 'created_by', None)
    if created_by:
        a.created_by = created_by
    return a


# ---------------------------------------------------------------------------
# Company-level driver
# ---------------------------------------------------------------------------


def _source_checksum(allowances, deductions):
    """Sum of every source amount, for the before/after proof."""
    total = Decimal('0')
    for a in allowances:
        total += _D(a.amount)
    for d in deductions:
        total += _D(d.amount)
    return total


def backfill_company(company_id, dry_run=False):
    """Backfill one company atomically. Returns a counts dict."""
    from payroll_engine import db
    from payroll_engine.models import PayItemCalcMethod
    from payroll_engine.models import Employee, EmployeeAllowance, EmployeeDeduction
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    employees = (
        Employee.query.filter_by(company_id=company_id, is_deleted=False)
        .order_by(Employee.id)
        .all()
    )
    allowances = (
        EmployeeAllowance.query.filter_by(company_id=company_id)
        .order_by(EmployeeAllowance.id)
        .all()
    )
    deductions = (
        EmployeeDeduction.query.filter_by(company_id=company_id)
        .order_by(EmployeeDeduction.id)
        .all()
    )

    conflicts = []
    counts = {
        'company_id': company_id,
        'employees': len(employees),
        'basic_created': 0,
        'basic_skipped': 0,
        'allowances_created': 0,
        'allowances_skipped': 0,
        'deductions_created': 0,
        'deductions_skipped': 0,
        'types_created': 0,
        'source_checksum': _source_checksum(allowances, deductions),
        'conflicts': conflicts,
        'error': None,
    }

    rows_by_emp = {}
    for row in list(allowances) + list(deductions):
        rows_by_emp.setdefault(row.employee_id, []).append(row)

    for emp in employees:
        emp_rows = rows_by_emp.get(emp.id, [])

        # --- 1. Basic salary FIRST -------------------------------------
        tag = _tag(BASIC_TAG, emp.id)
        if _already_backfilled(company_id, tag):
            counts['basic_skipped'] += 1
        else:
            item, type_created = _resolve_type(company_id, BASIC_KEY, 'earning')
            if type_created:
                counts['types_created'] += 1
            if not dry_run:
                from payroll_engine.models_payroll_elements import PayrollItemAssignment as PIA

                a = PIA()
                _assign_common(a, emp, item, company_id, tag,
                               basic_effective_date(emp, emp_rows), True,
                               label=item.name_en)
                a.fixed_amount = _D(emp.basic_salary)
                db.session.add(a)
                db.session.flush()
            counts['basic_created'] += 1

        # --- 2. Allowances ----------------------------------------------
        for al in [r for r in emp_rows if hasattr(r, 'allowance_type')]:
            atag = _tag(ALLOWANCE_TAG, al.id)
            if _already_backfilled(company_id, atag):
                counts['allowances_skipped'] += 1
                continue
            effective = al.effective_date or basic_effective_date(emp, emp_rows)
            if not dry_run:
                db.session.add(_convert_allowance(al, emp, company_id, effective))
                db.session.flush()
            counts['allowances_created'] += 1

        # --- 3. Deductions ----------------------------------------------
        for de in [r for r in emp_rows if hasattr(r, 'deduction_type')]:
            dtag = _tag(DEDUCTION_TAG, de.id)
            if _already_backfilled(company_id, dtag):
                counts['deductions_skipped'] += 1
                continue
            effective = de.start_date or basic_effective_date(emp, emp_rows)
            if not dry_run:
                db.session.add(_convert_deduction(de, emp, company_id, effective, conflicts))
                db.session.flush()
            counts['deductions_created'] += 1

    if not dry_run:
        db.session.commit()
    return counts


def backfill_all(dry_run=False):
    """Backfill every company, one transaction each.

    A company that raises is rolled back whole and its error recorded; the
    remaining companies still run, so one bad tenant cannot block the rollout.
    """
    from payroll_engine import db
    from payroll_engine.models import PayItemCalcMethod
    from payroll_engine.models import Company

    results = []
    for company in Company.query.order_by(Company.id).all():
        try:
            if dry_run:
                db.session.rollback()
                results.append(backfill_company(company.id, dry_run=True))
            else:
                try:
                    results.append(backfill_company(company.id, dry_run=False))
                except Exception as exc:  # noqa: BLE001
                    db.session.rollback()
                    failed = backfill_company(company.id, dry_run=True)
                    failed['error'] = str(exc)
                    failed['rolled_back'] = True
                    results.append(failed)
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            results.append({
                'company_id': company.id,
                'error': str(exc),
                'rolled_back': True,
            })
    return results


def verify_basic_present(company_id):
    """Assert invariant: nobody has assignments but no basic_salary assignment.

    This is the underpayment hole, and the backfill's whole point. Returns a
    list of offending employee ids (empty when healthy).
    """
    from payroll_engine.models import Employee
    from payroll_engine.models_payroll_elements import (
        PayItemType,
        PayrollItemAssignment,
    )

    basic = PayItemType.query.filter(
        PayItemType.key == BASIC_KEY,
        (PayItemType.company_id == company_id) | (PayItemType.company_id.is_(None)),
    ).all()
    basic_ids = [i.id for i in basic]

    offenders = []
    for emp in Employee.query.filter_by(company_id=company_id, is_deleted=False).all():
        rows = PayrollItemAssignment.query.filter_by(
            company_id=company_id, employee_id=emp.id, is_active=True
        ).all()
        if not rows:
            continue
        if not any(r.pay_item_type_id in basic_ids for r in rows):
            offenders.append(emp.id)
    return offenders
