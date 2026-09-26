"""
Management Impact Preview

Shows management the financial impact of decisions BEFORE they happen:
- "What if I give Dawit a raise to ETB 15,000?"
- "What if I hire a new employee at ETB 20,000?"
- "What if I add ETB 3,000 transport allowance?"
- "What if I terminate Abebe?"

Simple, clear, actionable. No jargon. Just numbers.
"""

from decimal import Decimal, InvalidOperation
from datetime import date

from payroll_engine.payroll import calculate_payroll
from payroll_engine.pension import employee_pension
from payroll_engine.services.allowance_service import calculate_transport_exempt_amount
from payroll_engine.severance import calculate_severance
from payroll_engine.tax import calculate_tax

Q = Decimal('0.01')


def _D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def resolve_pay_item(company_id, key):
    """Look up a PayItemType by key for a company, falling back to the system row.

    What-if previews resolve their hypothetical items from the company's catalog
    instead of fabricating an EmployeeAllowance with a hardcoded
    allowance_type/tax_treatment. A company that has customised or renamed an
    item gets that behaviour in the preview, which is the whole point.
    """
    from payroll_engine.models_payroll_elements import PayItemType

    item = PayItemType.query.filter_by(company_id=company_id, key=key).first()
    if item is None:
        item = PayItemType.query.filter_by(company_id=None, key=key).first()
    return item


def virtual_assignment(company_id, key, amount, classification=None,
                       tax_treatment=None, calc_method=None, for_date=None,
                       units_field=None):
    """Build a transient PayrollItemAssignment for a what-if simulation.

    Never added to the session and never written. `item_type` is populated so
    the engine applies the catalog's own tax treatment, calculation method and
    regulatory caps exactly as it would for a persisted row.

    Returns None if the item is not in the catalog — callers fall back to the
    legacy bare-number calculation rather than inventing a rule.
    """
    from datetime import date as _date

    from payroll_engine.models_payroll_elements import (
        PayrollItemAssignment, PayItemCalcMethod,
    )

    item = resolve_pay_item(company_id, key)
    if item is None:
        return None

    a = PayrollItemAssignment()
    a.item_type = item
    # Lock-in 4: the amount parameter's meaning depends on the
    # item's calculation_method.  For rate_x_units it is the
    # RATE_PER_UNIT (the engine multiplies by units_input);
    # for percent_of_basic it is the PERCENT_BASIC value;
    # otherwise it is the fixed_amount.
    calc_method = calc_method or item.calculation_method
    if calc_method == PayItemCalcMethod.RATE_X_UNITS:
        a.rate_per_unit = _D(amount)
    elif calc_method == PayItemCalcMethod.PERCENT_OF_BASIC:
        a.percent_of_basic = _D(amount)
    else:
        a.fixed_amount = _D(amount)
    a.is_active = True
    a.tracking_mode = None
    a.custom_label = None
    a.effective_date = for_date or _date.today()
    a.end_date = None
    a.units_field = units_field
    if classification:
        a._override_classification = classification
    if tax_treatment:
        a._override_tax_treatment = tax_treatment
    if calc_method:
        a._override_calc_method = calc_method
    return a


def _what_if_employee(basic_salary, company_id, employee_id=None, hire_date=None):
    """A transient Employee for the engine. Never added to the session.

    The engine queries the employee's persisted assignments, so a transient row
    with no id simply contributes none; hypothetical items arrive via
    extra_items instead.
    """
    from datetime import date as _date

    from payroll_engine.models import Employee

    emp = Employee()
    emp.basic_salary = _D(basic_salary)
    emp.allowances = Decimal('0')
    emp.company_id = company_id
    emp.employee_id = employee_id or 'WHATIF'
    emp.name = 'What-If'
    emp.hire_date = hire_date or _date.today()
    return emp


def preview_salary_raise(
    current_basic, current_allowances, new_basic, new_allowances, employee_name: str = 'Employee'
) -> dict:
    """Show management what happens if they give someone a raise.

    Returns a simple, readable comparison:
    - Current vs New
    - Monthly and annual impact
    - How much more the company pays
    - How much more the employee takes home
    """
    current_basic = _D(current_basic)
    current_allowances = _D(current_allowances)
    new_basic = _D(new_basic)
    new_allowances = _D(new_allowances)

    current = calculate_payroll(basic_salary=current_basic, allowances=current_allowances)
    new = calculate_payroll(basic_salary=new_basic, allowances=new_allowances)

    net_change = new['net'] - current['net']
    employer_change = (new['gross'] + new['pension_employer']) - (current['gross'] + current['pension_employer'])

    return {
        'type': 'salary_raise',
        'employee_name': employee_name,
        'current': {
            'basic': current_basic,
            'allowances': current_allowances,
            'gross': current['gross'],
            'tax': current['tax'],
            'pension': current['pension_employee'],
            'net': current['net'],
            'employer_cost': current['gross'] + current['pension_employer'],
        },
        'new': {
            'basic': new_basic,
            'allowances': new_allowances,
            'gross': new['gross'],
            'tax': new['tax'],
            'pension': new['pension_employee'],
            'net': new['net'],
            'employer_cost': new['gross'] + new['pension_employer'],
        },
        'impact': {
            'net_monthly_change': net_change.quantize(Q),
            'net_annual_change': (net_change * 12).quantize(Q),
            'employer_monthly_change': employer_change.quantize(Q),
            'employer_annual_change': (employer_change * 12).quantize(Q),
            'gross_increase': (new['gross'] - current['gross']).quantize(Q),
        },
    }


def preview_new_hire(
    basic_salary, allowances, transport_allowance: Decimal = Decimal('0'),
    employee_name: str = 'New Employee', company_id=None, item_key: str = 'transport',
) -> dict:
    """Show management what a new hire costs.

    Returns:
    - Monthly cost to company (salary + pension + allowances)
    - What the employee takes home
    - Annual projection
    - Tax and pension breakdown
    """
    basic_salary = _D(basic_salary)
    allowances = _D(allowances)
    transport_allowance = _D(transport_allowance)

    # Preferred path: resolve the item from the company's catalog and evaluate
    # it as a transient assignment. No EmployeeAllowance is fabricated, so a
    # company that renamed or re-taxed its transport item gets that behaviour
    # in the preview.
    extra_items = []
    if company_id:
        # Gross is assembled from assignments, so the hypothetical basic salary
        # must be supplied as one too -- employee.basic_salary alone only feeds
        # pension and tax, it never appears in gross.
        basic_item = virtual_assignment(company_id, 'basic_salary', basic_salary)
        if basic_item is not None:
            extra_items.append(basic_item)
        if transport_allowance > 0:
            va = virtual_assignment(company_id, item_key, transport_allowance)
            if va is not None:
                extra_items.append(va)

        # A bare `allowances` number needs an item to live on, or the engine
        # would silently drop it. Map it to the company's General Allowance
        # item; if that item does not exist, fall back to the legacy
        # calculation rather than under-reporting gross.
        if allowances > 0:
            gen = virtual_assignment(
                company_id, 'general_allowance', allowances
            )
            if gen is None:
                extra_items = []
            else:
                extra_items.append(gen)

    if extra_items:
        from payroll_engine.payroll_elements import calculate_payroll_from_assignments

        emp = _what_if_employee(basic_salary, company_id)

        # Build the units_input dict that the engine reads for
        # rate_x_units items. Lock-in 4: assignment.units_field is
        # the primary key, falling back to item_type.key.
        units_input = {}
        for item in extra_items:
            uf = getattr(item, 'units_field', None)
            if uf and item.fixed_amount and uf not in units_input:
                # For what-if previews the amount IS the unit count
                # when units_field is set on a rate_x_units item.
                units_input[uf] = int(item.fixed_amount)

        result = calculate_payroll_from_assignments(
            emp, company_id, date.today(),
            extra_items=extra_items, units_input=units_input,
        )
        total_allowances = allowances + transport_allowance
        exempt_allowances = result.get('exempt_allowances', Decimal('0'))
    else:
        # Legacy path: bare numbers. Kept for callers with no company context
        # (and for catalogs that do not define the item) so existing behaviour
        # is unchanged until the company is migrated.
        total_allowances = (
            allowances + transport_allowance if transport_allowance > 0 else allowances
        )
        if transport_allowance > 0:
            cap = calculate_transport_exempt_amount(basic_salary, transport_allowance)
            from payroll_engine.models import EmployeeAllowance

            allowance_records = [
                EmployeeAllowance(
                    allowance_type='transport',
                    amount=transport_allowance,
                    tax_treatment='partial',
                    exempt_cap_amount=cap,
                    is_active=True,
                )
            ]
        else:
            allowance_records = None

        result = calculate_payroll(
            basic_salary=basic_salary,
            allowances=total_allowances if not allowance_records else allowances,
            allowance_records=allowance_records,
        )
        exempt_allowances = result.get('exempt_allowances', Decimal('0'))

    employer_cost = result['gross'] + result['pension_employer']

    return {
        'type': 'new_hire',
        'employee_name': employee_name,
        'monthly': {
            'basic': basic_salary,
            'allowances': total_allowances,
            'gross': result['gross'],
            'pension_employee': result['pension_employee'],
            'pension_employer': result['pension_employer'],
            'tax': result['tax'],
            'net': result['net'],
            'employer_cost': employer_cost,
        },
        'annual': {
            'gross': (result['gross'] * 12).quantize(Q),
            'pension_employee': (result['pension_employee'] * 12).quantize(Q),
            'pension_employer': (result['pension_employer'] * 12).quantize(Q),
            'tax': (result['tax'] * 12).quantize(Q),
            'net': (result['net'] * 12).quantize(Q),
            'employer_cost': (employer_cost * 12).quantize(Q),
        },
        'exempt_transport': result.get('exempt_allowances', Decimal('0')),
    }


def preview_termination(
    basic_salary, allowances, start_date, end_date, termination_reason: str, employee_name: str = 'Employee'
) -> dict:
    """Show management what termination costs.

    Returns:
    - Severance amount
    - Final settlement breakdown
    - Net cost to company
    """
    basic_salary = _D(basic_salary)
    allowances = _D(allowances)

    sev = calculate_severance(basic_salary, start_date, end_date, termination_reason)

    monthly_salary = basic_salary + allowances
    daily_rate = monthly_salary / Decimal('30')
    years = sev['years_of_service']
    entitled_leave = 14 + int(years)
    leave_encashment = (daily_rate * entitled_leave).quantize(Q)

    pension = employee_pension(basic_salary)
    outstanding = monthly_salary  # Assume full month
    taxable = outstanding - pension
    tax = calculate_tax(taxable)

    total_cost = outstanding + sev['final_amount'] + leave_encashment

    return {
        'type': 'termination',
        'employee_name': employee_name,
        'reason': termination_reason,
        'eligible': sev['eligible'],
        'years_of_service': years,
        'breakdown': {
            'outstanding_salary': outstanding,
            'severance': sev['final_amount'],
            'leave_encashment': leave_encashment,
            'total_earnings': (outstanding + sev['final_amount'] + leave_encashment).quantize(Q),
            'pension_deduction': pension,
            'tax': tax,
            'total_deductions': (pension + tax).quantize(Q),
            'net_payout': (outstanding + sev['final_amount'] + leave_encashment - pension - tax).quantize(Q),
        },
        'company_cost': total_cost.quantize(Q),
        'cap': sev.get('capped_amount', Decimal('0')),
        'cap_applied': sev['final_amount'] < sev.get('calculated_amount', sev['final_amount']),
    }


def preview_allowance_change(current_amount, new_amount, basic_salary,
                              allowance_type: str = 'transport',
                              company_id=None) -> dict:
    """Show management what changing an allowance costs.

    Returns:
    - Tax impact
    - Net pay change for employee
    - Cost change for company
    """
    current_amount = _D(current_amount)
    new_amount = _D(new_amount)
    basic_salary = _D(basic_salary)

    # Catalog-driven path: build transient assignments for the OLD and NEW
    # amounts and let the elements engine apply the item's own tax treatment and
    # exempt cap. This replaces the `if allowance_type == 'transport'` hardcode
    # below, which assumed exactly one regulatory rule.
    if company_id:
        cur_item = virtual_assignment(company_id, allowance_type, current_amount)
        new_item = virtual_assignment(company_id, allowance_type, new_amount)
        if cur_item is not None and new_item is not None:
            from payroll_engine.payroll_elements import calculate_payroll_from_assignments

            emp = _what_if_employee(basic_salary, company_id)
            cur_item_basic = virtual_assignment(
                company_id, 'basic_salary', basic_salary,
            )
            new_item_basic = virtual_assignment(
                company_id, 'basic_salary', basic_salary,
            )
            cur = calculate_payroll_from_assignments(
                emp, company_id, date.today(),
                extra_items=[cur_item_basic, cur_item],
            )
            new = calculate_payroll_from_assignments(
                emp, company_id, date.today(),
                extra_items=[new_item_basic, new_item],
            )
            tax_change = new['tax'] - cur['tax']
            net_change = (new['net'] - cur['net'])
            return {
                'type': 'allowance_change',
                'allowance_type': allowance_type,
                'current_amount': current_amount,
                'new_amount': new_amount,
                'exempt_current': cur.get('exempt_allowances', Decimal('0')),
                'exempt_new': new.get('exempt_allowances', Decimal('0')),
                'impact': {
                    'amount_change': (new_amount - current_amount).quantize(Q),
                    'tax_change': tax_change.quantize(Q),
                    'net_monthly_change': net_change.quantize(Q),
                    'net_annual_change': (net_change * 12).quantize(Q),
                },
                'current': cur,
                'new': new,
            }

    # Legacy path: no company catalog context, or the item is not defined.
    if allowance_type == 'transport':
        current_exempt = calculate_transport_exempt_amount(basic_salary, current_amount)
        new_exempt = calculate_transport_exempt_amount(basic_salary, new_amount)
    else:
        current_exempt = Decimal('0')
        new_exempt = Decimal('0')

    current_taxable_allowance = current_amount - current_exempt
    new_taxable_allowance = new_amount - new_exempt

    pension = employee_pension(basic_salary)
    current_taxable = basic_salary + current_taxable_allowance - pension
    new_taxable = basic_salary + new_taxable_allowance - pension

    current_tax = calculate_tax(max(Decimal('0'), current_taxable))
    new_tax = calculate_tax(max(Decimal('0'), new_taxable))

    tax_change = new_tax - current_tax
    net_change = (new_amount - current_amount) - tax_change

    current = calculate_payroll(basic_salary=basic_salary, allowances=current_amount)
    new = calculate_payroll(basic_salary=basic_salary, allowances=new_amount)

    return {
        'type': 'allowance_change',
        'allowance_type': allowance_type,
        'current_amount': current_amount,
        'new_amount': new_amount,
        'exempt_current': current_exempt,
        'exempt_new': new_exempt,
        'impact': {
            'amount_change': (new_amount - current_amount).quantize(Q),
            'tax_change': tax_change.quantize(Q),
            'net_monthly_change': net_change.quantize(Q),
            'net_annual_change': (net_change * 12).quantize(Q),
            'employer_monthly_change': (
                new['gross'] + new['pension_employer'] - current['gross'] - current['pension_employer']
            ).quantize(Q),
            'employer_annual_change': (
                (new['gross'] + new['pension_employer'] - current['gross'] - current['pension_employer']) * 12
            ).quantize(Q),
        },
    }
