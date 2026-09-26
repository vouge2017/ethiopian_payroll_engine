"""
Elements-aware payroll accumulation engine.

Replaces the hardcoded basic+allowances+overtime sequence in calculate_payroll()
with a generic accumulation loop over PayrollItemAssignment rows.

Returns the SAME dict shape as calculate_payroll() PLUS a 'line_items' list.
calculate_payroll() is kept for bare-number callers and marked LEGACY.

Spec (Phase 2 section 2d):
  - Overtime stays as its own module feeding overtime_pay into gross.
  - percent_of_item column exists but its logic is DEFERRED.
  - units_input key resolution (lock-in 4): try assignment.units_field first,
    then the item key. Called out here as the authoritative reference.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from payroll_engine import db
from payroll_engine.models import (
    PayItemCalcMethod,
    PayItemClassification,
    PayItemTaxTreatment,
    PayItemType,
    PayrollItemAssignment,
)
from payroll_engine.overtime import calculate_total_overtime
from payroll_engine.pension import employee_pension as _employee_pension
from payroll_engine.pension import employer_pension as _employer_pension
from payroll_engine.tax import calculate_tax as _calculate_tax
from payroll_engine.tax import explain_tax_amharic as _explain_tax_amharic

Q = Decimal('0.01')


def _item_sort_key(item):
    """Return sort_order for a PayItemType or PayrollItemAssignment.

    System catalog items (PayItemType) expose ``sort_order`` directly.
    Employee assignments (PayrollItemAssignment) get their sort_order from
    the linked item type — fall back to 999 when no type is attached.
    """
    so = getattr(item, 'sort_order', None)
    if so is not None:
        return so
    it = getattr(item, 'item_type', None)
    return it.sort_order if it else 999


def _D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _item_quantity(assignment, units_input):
    """Resolve the quantity for a rate_x_units item.

    Lock-in 4 — deterministic key resolution order:
      1. If assignment.units_field is set, look up units_input[assignment.units_field].
      2. Otherwise, look up units_input[item.key] (the item key itself).
      3. If neither is present, the quantity is 0 (no units this period).
    """
    if assignment.units_field and units_input and assignment.units_field in units_input:
        return _D(units_input[assignment.units_field])
    if units_input and assignment.item_type and assignment.item_type.key in units_input:
        return _D(units_input[assignment.item_type.key])
    return Decimal('0')


def calculate_payroll_from_assignments(
    employee,
    company_id,
    for_date,
    *,
    units_input=None,
    overtime_entries=None,
    deductions=None,
    extra_items=None,
    sick_leave_reduction=0,
) -> dict:
    """Calculate payroll from the per-company elements model.

    Args:
        employee: Employee ORM instance (provides basic_salary, hire_date).
        company_id: int — scopes PayItemType lookups to the company's catalog.
        for_date: date — the pay period date; used for rule versioning and
            effective-date gating.
        units_input: optional dict — per-period unit counts keyed by field name,
            consumed by rate_x_units items (lock-in 4). Example:
                {'night_shift_units': 20, 'overtime_hours': 12}
        overtime_entries: optional list — passed directly to the overtime module;
            overtime_pay is added into gross (NOT refactored in this phase).
        deductions: optional list of EmployeeDeduction objects for post-tax
            deductions (legacy bridge; kept for bare-deduction callers during
            transition). New code should express deductions as PayrollItemAssignment
            rows with tracking_mode='declining'.
        extra_items: optional list of IN-MEMORY PayrollItemAssignment objects to
            evaluate IN ADDITION to the employee's persisted rows. Used by
            what-if simulations, which must not write to the database. Each must
            have its `item_type` relationship populated (so the catalog's
            tax_treatment / calc method / caps apply exactly as they would for a
            real row). Rows here are never added to the session.
        sick_leave_reduction: Decimal or numeric — amount to deduct for sick-leave
            tier-1 reduction (same semantics as calculate_payroll).

    Returns:
        Dict with the same keys as calculate_payroll() PLUS:
            'line_items': list of dicts, one per pay item that contributed to the
                calculation, in accumulation order. Each dict has:
                    'item_key', 'item_label', 'classification',
                    'calculation_method', 'earned_amount', 'is_deduction',
                    'effective_date', 'is_system'.
        calculate_payroll() is kept for bare-number callers and marked LEGACY.
    """
    for_date = _normalize_date(for_date)
    basic_salary = _D(employee.basic_salary or 0)
    if basic_salary < 0:
        raise ValueError(f'basic_salary cannot be negative: {basic_salary}')

    # ------------------------------------------------------------------
    # 1. Load active, effective assignments for this employee + company.
    #    Excludes system catalog items (company_id IS NULL) because those are
    #    never assigned directly — the engine seeds them internally.
    # ------------------------------------------------------------------
    system_items = _load_system_items(company_id, for_date)
    employee_items = _load_employee_items(employee.id, company_id, for_date)

    # What-if simulations pass hypothetical rows in memory. They are bucketed
    # with the same classification mapping as persisted rows, so a hypothetical
    # item is taxed/capped identically to a real one.
    for extra in extra_items or []:
        item_type = getattr(extra, 'item_type', None)
        if item_type is None:
            continue
        if not getattr(item_type, 'is_active', True):
            continue
        extra_bucket = {
            PayItemClassification.EARNING: employee_items['earnings'],
            PayItemClassification.DEDUCTION: employee_items['deductions'],
            PayItemClassification.EMPLOYER_CHARGE: employee_items['employer_charges'],
            PayItemClassification.TAX: employee_items['tax'],
            PayItemClassification.INFORMATIONAL: employee_items['tax'],
        }.get(item_type.classification, employee_items['earnings'])
        extra_bucket.append(extra)

    # ------------------------------------------------------------------
    # 2. Accumulation.
    #    Order: earnings first (sorted by sort_order), then deductions
    #    (sorted by sort_order). Overtime is injected into gross as a separate
    #    step (kept as its own module per spec section 2d).
    # ------------------------------------------------------------------
    line_items = []
    total_earnings = Decimal('0')
    total_deductions_pre_tax = Decimal('0')
    exempt_allowances = Decimal('0')
    taxable_allowances = Decimal('0')
    allowance_details = []
    deduction_details = []

    # Earnings accumulation
    for item in sorted(system_items['earnings'] + employee_items['earnings'],
                       key=_item_sort_key):
        amount = _calculate_item_amount(item, employee, for_date, units_input,
                                        total_earnings + total_deductions_pre_tax)
        # Normalize: assignments carry their PayItemType via .item_type
        item_type = item if isinstance(item, PayItemType) else getattr(item, 'item_type', None)
        classification = item_type.classification if item_type else PayItemClassification.EARNING
        is_system = getattr(item_type, 'is_system', False) if item_type else False

        line_items.append(_line_item_dict(item, amount, classification, is_system))

        if classification == PayItemClassification.EMPLOYER_CHARGE:
            pass
        elif classification == PayItemClassification.EARNING:
            total_earnings += amount
            tt = getattr(item_type, 'tax_treatment', None) if item_type else None
            if tt == PayItemTaxTreatment.EXEMPT:
                exempt_allowances += amount
                allowance_details.append(_allowance_detail(item, amount, 0, amount))
            elif tt == PayItemTaxTreatment.TAXABLE:
                taxable_allowances += amount
                allowance_details.append(_allowance_detail(item, amount, amount, 0))
            elif tt == PayItemTaxTreatment.PARTIAL:
                exempt = _apply_exempt_cap(item_type or item, amount, basic_salary)
                exempt_allowances += exempt
                taxable_allowances += (amount - exempt)
                allowance_details.append(_allowance_detail(item, amount, exempt, amount - exempt))
            else:
                taxable_allowances += amount
                allowance_details.append(_allowance_detail(item, amount, 0, amount))

        elif classification == PayItemClassification.DEDUCTION:
            total_deductions_pre_tax += amount

        elif classification == PayItemClassification.TAX:
            # System tax items are informational line items; the engine computes
            # tax separately below.
            pass

    # Overtime (kept as its own module — spec section 2d)
    overtime_pay = Decimal('0')
    overtime_total_hours = Decimal('0')
    overtime_result = None
    if overtime_entries:
        overtime_result = calculate_total_overtime(basic_salary, overtime_entries)
        overtime_pay = overtime_result['total_pay']
        overtime_total_hours = overtime_result['total_hours']
        line_items.append(_line_item_dict(
            _make_overtime_placeholder(), overtime_pay,
            PayItemClassification.EARNING, False,
            custom_label='Overtime (from overtime module)',
        ))
    total_earnings += overtime_pay

    gross = total_earnings  # base_gross + overtime_pay (overtime already added above)

    # Pension (employee + employer) — BEFORE tax, on basic ONLY
    emp_pen = _employee_pension(basic_salary, for_date)
    empr_pen = _employer_pension(basic_salary, for_date)

    # Taxable = gross - employee pension (pre-tax) - other pre-tax deductions - exempt allowances
    taxable = gross - emp_pen - total_deductions_pre_tax - exempt_allowances
    taxable = max(Decimal('0'), taxable)

    # Tax (calculated by the existing tax module)
    tax = _calculate_tax(taxable, for_date)

    net_before_deductions = gross - tax - emp_pen

    # Post-tax deductions — from the legacy `deductions` list or from new
    # declining-balance assignment rows
    total_post_tax_deductions = _merge_post_tax_deductions(
        deductions, employee_items['deductions'],
        net_before_deductions, tax, deduction_details,
        line_items, Decimal('0'), for_date
    )

    sick_leave_reduction = _D(sick_leave_reduction)
    net_after_sick = net_before_deductions - sick_leave_reduction
    net_after_sick = max(Decimal('0'), net_after_sick)

    net = net_after_sick - total_post_tax_deductions

    tax_explanation = _explain_tax_amharic(taxable, for_date)

    result = {
        'gross': gross.quantize(Q, rounding=ROUND_HALF_UP),
        'taxable': taxable.quantize(Q, rounding=ROUND_HALF_UP),
        'tax': tax,
        'pension_employee': emp_pen,
        'pension_employer': empr_pen,
        'net_before_deductions': net_before_deductions.quantize(Q, rounding=ROUND_HALF_UP),
        'sick_leave_reduction': sick_leave_reduction.quantize(Q, rounding=ROUND_HALF_UP),
        'total_deductions': total_post_tax_deductions.quantize(Q, rounding=ROUND_HALF_UP),
        'deduction_details': deduction_details,
        'net': net.quantize(Q, rounding=ROUND_HALF_UP),
        'tax_explanation': tax_explanation,
        'overtime_pay': overtime_pay,
        'overtime_total_hours': overtime_total_hours,
        'overtime_result': overtime_result,
        'exempt_allowances': exempt_allowances.quantize(Q, rounding=ROUND_HALF_UP),
        'taxable_allowances': taxable_allowances.quantize(Q, rounding=ROUND_HALF_UP),
        'allowance_details': allowance_details,
        'line_items': line_items,
    }
    return result


def _normalize_date(for_date):
    if for_date is None:
        from datetime import date as _date
        return _date.today()
    if isinstance(for_date, str):
        from datetime import datetime as _dt
        return _dt.strptime(for_date, '%Y-%m-%d').date()
    return for_date


def seed_pay_item_types(company_id):
    """Seed a company's pay item catalog from the system catalog.

    Copies all active system items (company_id IS NULL) to the company
    as company-specific rows (company_id=<company_id>), skipping keys
    that already have a company-specific copy.

    Call this when a new company is created so the elements engine
    has per-company assignment rows to work with.
    """
    from payroll_engine import db
    from payroll_engine.models import PayItemType as _PPT

    system_items = db.session.query(_PPT).filter(
        _PPT.company_id.is_(None),
        _PPT.is_active == True,
    ).all()

    for sys_item in system_items:
        exists = db.session.query(_PPT).filter(
            _PPT.company_id == company_id,
            _PPT.key == sys_item.key,
        ).first()
        if exists:
            continue
        company_item = _PPT(
            company_id=company_id,
            key=sys_item.key,
            name_en=sys_item.name_en,
            name_am=sys_item.name_am,
            classification=sys_item.classification,
            calculation_method=sys_item.calculation_method,
            percent_of_item_key=sys_item.percent_of_item_key,
            rate=sys_item.rate,
            tax_treatment=sys_item.tax_treatment,
            exempt_cap_amount=sys_item.exempt_cap_amount,
            exempt_cap_percent=sys_item.exempt_cap_percent,
            exempt_cap_basis=sys_item.exempt_cap_basis,
            regulation_reference=sys_item.regulation_reference,
            sort_order=sys_item.sort_order,
            is_system=False,
            is_active=sys_item.is_active,
            effective_date=sys_item.effective_date,
            end_date=sys_item.end_date,
        )
        db.session.add(company_item)
    db.session.commit()


def _load_system_items(company_id, for_date):
    """Load system catalog items (company_id IS NULL) for the given company.

    Returns a dict with keys 'earnings', 'deductions', 'employer_charges', 'tax'.
    """
    from payroll_engine import db
    from datetime import date as _date

    effective = _effective_query(for_date)

    earnings = []
    deductions = []
    employer_charges = []
    tax_items = []

    rows = db.session.query(PayItemType).filter(
        PayItemType.company_id.is_(None),
        PayItemType.is_active == True,
    ).filter(effective).order_by(PayItemType.sort_order).all()

    for row in rows:
        bucket = {
            PayItemClassification.EARNING: earnings,
            PayItemClassification.DEDUCTION: deductions,
            PayItemClassification.EMPLOYER_CHARGE: employer_charges,
            PayItemClassification.TAX: tax_items,
            PayItemClassification.INFORMATIONAL: tax_items,  # informational treated as tax-ish
        }.get(row.classification, earnings)
        bucket.append(row)

    return {
        'earnings': earnings,
        'deductions': deductions,
        'employer_charges': employer_charges,
        'tax': tax_items,
    }


def _load_employee_items(employee_id, company_id, for_date):
    """Load PayrollItemAssignment rows for one employee + company.

    Returns dict with 'earnings', 'deductions', 'employer_charges', 'tax'.
    Filters by effective date and is_active.
    """
    from payroll_engine import db
    from datetime import date as _date

    effective = _effective_query(for_date)

    query = db.session.query(PayrollItemAssignment).join(
        PayItemType,
        PayrollItemAssignment.pay_item_type_id == PayItemType.id,
    ).filter(
        PayrollItemAssignment.employee_id == employee_id,
        PayrollItemAssignment.company_id == company_id,
        PayrollItemAssignment.is_active == True,
        PayItemType.is_active == True,
    ).filter(effective).order_by(PayItemType.sort_order, PayrollItemAssignment.id)

    rows = query.all()

    earnings = []
    deductions = []
    employer_charges = []
    tax_items = []

    for row in rows:
        bucket = {
            PayItemClassification.EARNING: earnings,
            PayItemClassification.DEDUCTION: deductions,
            PayItemClassification.EMPLOYER_CHARGE: employer_charges,
            PayItemClassification.TAX: tax_items,
            PayItemClassification.INFORMATIONAL: tax_items,
        }.get(row.item_type.classification, earnings)
        bucket.append(row)

    return {
        'earnings': earnings,
        'deductions': deductions,
        'employer_charges': employer_charges,
        'tax': tax_items,
    }


def _effective_query(for_date):
    """Return a SQLAlchemy filter criterion for effective-date gating.

    An item is effective for `for_date` when:
      - effective_date IS NULL OR effective_date <= for_date
      - AND end_date IS NULL OR end_date >= for_date
    """
    from sqlalchemy import or_, and_
    from datetime import date as _date

    if isinstance(for_date, _date):
        d = for_date
    else:
        d = _normalize_date(for_date)

    return and_(
        or_(PayItemType.effective_date.is_(None), PayItemType.effective_date <= d),
        or_(PayItemType.end_date.is_(None), PayItemType.end_date >= d),
    )


def _calculate_item_amount(item, employee, for_date, units_input, running_total):
    """Calculate the monetary amount for one pay item.

    item may be a PayItemType (system catalog) or a PayrollItemAssignment.
    """
    if isinstance(item, PayrollItemAssignment):
        item_type = item.item_type
        method = item_type.calculation_method if item_type else PayItemCalcMethod.FIXED
        fixed = item.fixed_amount
        rate = item.rate_per_unit
        pct_basic = item.percent_of_basic
        pct_net = item.percent_of_net
    else:
        item_type = item
        method = item.calculation_method
        fixed = None
        rate = item.rate
        pct_basic = None
        pct_net = None

    basic = _D(employee.basic_salary or 0) if hasattr(employee, 'basic_salary') else Decimal('0')

    if method == PayItemCalcMethod.FIXED:
        return _D(fixed or 0)
    elif method == PayItemCalcMethod.RATE_X_UNITS:
        qty = _item_quantity(item if isinstance(item, PayrollItemAssignment) else None,
                             units_input) if isinstance(item, PayrollItemAssignment) else _D(0)
        if not isinstance(item, PayrollItemAssignment):
            qty = _D(0)  # system items don't have per-period units
        return (rate or Decimal('0')) * qty
    elif method == PayItemCalcMethod.PERCENT_OF_BASIC:
        pct = _D(pct_basic or (item.rate if hasattr(item, 'rate') else 0))
        return (basic * pct / Decimal('100')).quantize(Q, rounding=ROUND_HALF_UP)
    elif method == PayItemCalcMethod.PERCENT_OF_NET:
        # percent_of_net — deduction-only per spec. Applied against net_before_deductions.
        # running_total param is net_before_deductions when called for deductions.
        pct = _D(pct_net or 0)

        # Legal ceiling (e.g. court_order capped at 50% of net). Read from the
        # PayItemType row, not hardcoded, so the rule lives in the catalog. The
        # route warns on a violation; here we enforce it, so a row that predates
        # the ceiling (or bypassed the route) still cannot over-deduct.
        #
        # `item` is normally a PayrollItemAssignment, so the ceiling lives on its
        # .item_type; fall back to `item` itself for a bare PayItemType.
        item_type = getattr(item, 'item_type', None) or item
        ceiling = getattr(item_type, 'max_percent_of_net', None)
        if ceiling is not None and pct > _D(ceiling):
            pct = _D(ceiling)

        base = _D(running_total) if running_total else Decimal('0')
        return (base * pct / Decimal('100')).quantize(Q, rounding=ROUND_HALF_UP)
    elif method == PayItemCalcMethod.PERCENT_OF_ITEM:
        raise NotImplementedError(
            'percent_of_item calculation not implemented in this phase. '
            'Set calculation_method to fixed, rate_x_units, percent_of_basic, or percent_of_net.'
        )
    return Decimal('0')


def _apply_exempt_cap(item, amount, basic_salary):
    """Apply exempt cap logic to an earning item.

    Uses the item's exempt_cap_amount (flat ETB cap) or exempt_cap_percent
    (percent of basic). Same logic as the legacy EmployeeAllowance.exempt cap.
    """
    cap_amount = item.exempt_cap_amount
    cap_percent = item.exempt_cap_percent

    if cap_amount is not None:
        return min(_D(amount), _D(cap_amount))
    if cap_percent is not None:
        cap = (basic_salary * _D(cap_percent) / Decimal('100')).quantize(Q, rounding=ROUND_HALF_UP)
        return min(_D(amount), cap)
    return _D(amount)


def _merge_post_tax_deductions(deductions, new_deductions, net_before_deductions,
                                tax, deduction_details, line_items, total, for_date):
    """Merge legacy EmployeeDeduction list and new PayrollItemAssignment deductions.

    New deduction assignments with tracking_mode='declining' decrement their
    remaining_balance each period (up to the amount recovered this period).
    """
    from payroll_engine.models import EmployeeDeduction

    total = _D(total) if total else Decimal('0')
    post_tax_detail_list = deduction_details  # already a list reference

    # Legacy deductions first (for backward compatibility during transition)
    if deductions:
        for ded in deductions:
            if not ded.is_active:
                continue
            ded_amount = ded.calculate_deduction(net_before_deductions)
            if ded_amount > 0:
                total += ded_amount
                post_tax_detail_list.append(
                    {
                        'id': ded.id,
                        'type': ded.deduction_type,
                        'type_label': ded.type_label,
                        'label': ded.label,
                        'amount': ded_amount,
                        'remaining_balance': ded.remaining_balance,
                        'warning': ded.warning_message,
                        'legacy': True,
                    }
                )
                # Line item for the deduction
                line_items.append(_line_item_dict(
                    _make_legacy_deduction_placeholder(ded), ded_amount,
                    PayItemClassification.DEDUCTION, False,
                    custom_label=ded.label or ded.type_label,
                    is_legacy=True,
                ))

    # New assignment-based deductions (declining-balance or date-bounded)
    for assignment in new_deductions:
        item_type = assignment.item_type
        method = item_type.calculation_method if item_type else PayItemCalcMethod.FIXED
        amount = _calculate_item_amount(assignment, None, for_date, None, net_before_deductions)

        # Declining-balance: recover up to remaining_balance this period
        if assignment.tracking_mode == 'declining' and assignment.remaining_balance is not None:
            recoverable = min(amount, _D(assignment.remaining_balance))
            amount = recoverable
            assignment.remaining_balance = (_D(assignment.remaining_balance) - amount).quantize(Q, rounding=ROUND_HALF_UP)
            db.session.add(assignment)

        if amount > 0:
            total += amount
            post_tax_detail_list.append(
                {
                    'id': assignment.id,
                    'type': item_type.key if item_type else 'unknown',
                    'type_label': item_type.name_en if item_type else 'Unknown',
                    'label': assignment.label,
                    'amount': amount,
                    'remaining_balance': assignment.remaining_balance or 0,
                    'warning': '',
                    'legacy': False,
                    'assignment_id': assignment.id,
                }
            )
            line_items.append(_line_item_dict(
                item_type if item_type else _make_placeholder('unknown'),
                amount,
                PayItemClassification.DEDUCTION, False,
                custom_label=assignment.label or (item_type.name_en if item_type else 'Unknown'),
                is_legacy=False,
            ))

    return total


def _line_item_dict(item, amount, classification, is_system, **kwargs):
    """Build a line item dict for the result's 'line_items' list."""
    custom_label = kwargs.get('custom_label')
    is_legacy = kwargs.get('is_legacy', False)

    if isinstance(item, PayrollItemAssignment):
        item_type = item.item_type
        key = item_type.key if item_type else 'unknown'
        label = custom_label or item.label
        label_am = custom_label or (item_type.name_am if item_type else None)
        calc_method = item_type.calculation_method if item_type else PayItemCalcMethod.FIXED
        effective_date = item.effective_date
        item_id = item.id
        assignment_id = item.id
    elif hasattr(item, 'key'):  # PayItemType
        key = item.key
        label = custom_label or (item.name_en if item.name_en else key)
        label_am = custom_label or item.name_am
        calc_method = item.calculation_method
        effective_date = item.effective_date
        item_id = item.id
        assignment_id = None
    else:
        key = kwargs.get('item_key', 'unknown')
        label = custom_label or kwargs.get('fallback_label', key)
        label_am = kwargs.get('fallback_label_am')
        calc_method = kwargs.get('calc_method', PayItemCalcMethod.FIXED)
        effective_date = None
        item_id = None
        assignment_id = None

    entry = {
        'item_key': key,
        'item_label': label,
        # Amharic counterpart for bilingual payslips (spec: labels come from
        # PayItemType.name_en / name_am, never hardcoded in the PDF template).
        'item_label_am': label_am,
        'classification': classification,
        'calculation_method': calc_method,
        'earned_amount': _D(amount).quantize(Q, rounding=ROUND_HALF_UP) if amount is not None else Decimal('0'),
        'is_deduction': classification in (PayItemClassification.DEDUCTION, PayItemClassification.EMPLOYER_CHARGE, PayItemClassification.TAX),
        'effective_date': effective_date,
        'is_system': is_system or getattr(item, 'is_system', False),
        'is_legacy': is_legacy,
        'item_id': item_id,
        'assignment_id': assignment_id,
    }
    return entry


def _allowance_detail(item, amount, exempt, taxable):
    """Build an allowance detail dict compatible with calculate_payroll's shape."""
    if isinstance(item, PayrollItemAssignment):
        item_type = item.item_type
        key = item_type.key if item_type else 'unknown'
        label = item.label
        tax_treatment = item_type.tax_treatment if item_type else PayItemTaxTreatment.TAXABLE
    else:
        key = item.key
        label = item.name_en if item.name_en else key
        tax_treatment = item.tax_treatment

    return {
        'type': key,
        'type_label': label,
        'amount': _D(amount).quantize(Q, rounding=ROUND_HALF_UP),
        'exempt': _D(exempt).quantize(Q, rounding=ROUND_HALF_UP),
        'taxable': _D(taxable).quantize(Q, rounding=ROUND_HALF_UP),
        'tax_treatment': tax_treatment,
    }


def _make_overtime_placeholder():
    """Placeholder PayItemType-like object for overtime line items."""
    class _Placeholder:
        key = 'overtime'
        name_en = 'Overtime'
        name_am = 'ፈተና ስርዓት'
        classification = PayItemClassification.EARNING
        calculation_method = PayItemCalcMethod.FIXED
        tax_treatment = PayItemTaxTreatment.TAXABLE
        is_system = False
        sort_order = 9999
        effective_date = None
        end_date = None
        is_active = True
    return _Placeholder()


def _make_legacy_deduction_placeholder(ded):
    """Placeholder for legacy EmployeeDeduction line items."""
    class _Placeholder:
        key = ded.deduction_type or 'unknown'
        name_en = ded.type_label or 'Deduction'
        name_am = ''
        classification = PayItemClassification.DEDUCTION
        calculation_method = PayItemCalcMethod.FIXED
        tax_treatment = PayItemTaxTreatment.TAXABLE
        is_system = False
        sort_order = 9999
        effective_date = None
        end_date = None
        is_active = True
    return _Placeholder()


def _make_placeholder(key):
    """Generic placeholder for unknown items."""
    class _Placeholder:
        key = key
        name_en = key
        name_am = ''
        classification = PayItemClassification.EARNING
        calculation_method = PayItemCalcMethod.FIXED
        tax_treatment = PayItemTaxTreatment.TAXABLE
        is_system = False
        sort_order = 9999
        effective_date = None
        end_date = None
        is_active = True
    return _Placeholder()


# ===========================================================================
# LEGACY COMPATIBILITY — calculate_payroll kept for bare-number callers.
# The real implementation lives in payroll.py (imported below).
# New code should use calculate_payroll_from_assignments.
# ===========================================================================


def calculate_payroll_legacy(
    basic_salary,
    allowances=Decimal('0'),
    overtime_entries: list | None = None,
    for_date=None,
    deductions: list | None = None,
    allowance_records: list | None = None,
    sick_leave_reduction: Decimal = Decimal('0'),
) -> dict:
    """LEGACY — kept for bare-number callers during transition.

    Will be removed once all callers migrate to calculate_payroll_from_assignments.
    See migration plan (Phase 2 section 2e) for the consumer migration order.
    """
    from payroll_engine.payroll import calculate_payroll as _real
    return _real(basic_salary, allowances, overtime_entries, for_date,
                 deductions, allowance_records, sick_leave_reduction)


# Re-export the LEGACY name under the old name so existing imports continue to
# work during the transition. New code should import calculate_payroll_from_assignments.
calculate_payroll = calculate_payroll_legacy
