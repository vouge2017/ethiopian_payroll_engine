"""
What-If Scenario Engine

Calculates the impact of proposed changes before they're applied:
- Salary changes (basic, allowances)
- New employee additions
- Allowance changes (type, amount, tax treatment)
- Termination/severance preview

Returns comparison: BEFORE vs AFTER with impact summary.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from payroll_engine.payroll import calculate_payroll
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.tax import calculate_tax


Q = Decimal('0.01')


def _D(value) -> Decimal:
    """Safely convert to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def preview_salary_change(current_basic, current_allowances,
                          new_basic, new_allowances,
                          current_overtime_entries=None,
                          current_deductions=None) -> dict:
    """Preview impact of a salary change.

    Args:
        current_basic: Current basic salary
        current_allowances: Current total allowances
        new_basic: Proposed basic salary
        new_allowances: Proposed total allowances
        current_overtime_entries: Current overtime entries (optional)
        current_deductions: Current deductions (optional)

    Returns:
        Dict with before, after, and impact analysis
    """
    current_basic = _D(current_basic)
    current_allowances = _D(current_allowances)
    new_basic = _D(new_basic)
    new_allowances = _D(new_allowances)

    # Calculate current payroll
    before = calculate_payroll(
        basic_salary=current_basic,
        allowances=current_allowances,
        overtime_entries=current_overtime_entries,
        deductions=current_deductions,
    )

    # Calculate proposed payroll
    after = calculate_payroll(
        basic_salary=new_basic,
        allowances=new_allowances,
        overtime_entries=current_overtime_entries,
        deductions=current_deductions,
    )

    # Calculate impact
    net_change = after['net'] - before['net']
    net_change_pct = (net_change / before['net'] * 100) if before['net'] > 0 else Decimal('0')

    # Employer cost
    before_employer_cost = before['gross'] + before['pension_employer']
    after_employer_cost = after['gross'] + after['pension_employer']
    employer_cost_change = after_employer_cost - before_employer_cost

    # Tax bracket change
    before_rate = (before['tax'] / before['taxable'] * 100) if before['taxable'] > 0 else Decimal('0')
    after_rate = (after['tax'] / after['taxable'] * 100) if after['taxable'] > 0 else Decimal('0')

    return {
        'type': 'salary_change',
        'before': {
            'basic': current_basic,
            'allowances': current_allowances,
            'gross': before['gross'],
            'tax': before['tax'],
            'pension': before['pension_employee'],
            'net': before['net'],
            'employer_cost': before_employer_cost,
            'effective_tax_rate': before_rate.quantize(Q),
        },
        'after': {
            'basic': new_basic,
            'allowances': new_allowances,
            'gross': after['gross'],
            'tax': after['tax'],
            'pension': after['pension_employee'],
            'net': after['net'],
            'employer_cost': after_employer_cost,
            'effective_tax_rate': after_rate.quantize(Q),
        },
        'impact': {
            'net_change': net_change.quantize(Q),
            'net_change_pct': net_change_pct.quantize(Q),
            'employer_cost_change': employer_cost_change.quantize(Q),
            'annual_net_change': (net_change * 12).quantize(Q),
            'annual_employer_change': (employer_cost_change * 12).quantize(Q),
        },
    }


def preview_new_employee(basic_salary, allowances,
                         allowance_records=None) -> dict:
    """Preview cost of adding a new employee.

    Args:
        basic_salary: Proposed basic salary
        allowances: Proposed total allowances
        allowance_records: List of EmployeeAllowance objects (optional)

    Returns:
        Dict with monthly and annual cost breakdown
    """
    basic_salary = _D(basic_salary)
    allowances = _D(allowances)

    result = calculate_payroll(
        basic_salary=basic_salary,
        allowances=allowances,
        allowance_records=allowance_records,
    )

    employer_cost = result['gross'] + result['pension_employer']

    return {
        'type': 'new_employee',
        'monthly': {
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
        'exempt_allowances': result.get('exempt_allowances', Decimal('0')),
        'taxable_allowances': result.get('taxable_allowances', Decimal('0')),
    }


def preview_allowance_change(current_amount, new_amount,
                              allowance_type, basic_salary,
                              tax_treatment='taxable',
                              exempt_cap=None) -> dict:
    """Preview impact of changing an allowance.

    Args:
        current_amount: Current allowance amount
        new_amount: Proposed allowance amount
        allowance_type: Type of allowance (transport, hardship, etc.)
        basic_salary: Employee's basic salary
        tax_treatment: Tax treatment (taxable, exempt, partial)
        exempt_cap: Maximum exempt amount (for partial)

    Returns:
        Dict with before/after comparison and tax impact
    """
    current_amount = _D(current_amount)
    new_amount = _D(new_amount)
    basic_salary = _D(basic_salary)
    exempt_cap = _D(exempt_cap) if exempt_cap else None

    # Calculate exempt portions
    if tax_treatment == 'exempt':
        current_exempt = current_amount
        new_exempt = new_amount
    elif tax_treatment == 'partial' and exempt_cap:
        current_exempt = min(current_amount, exempt_cap)
        new_exempt = min(new_amount, exempt_cap)
    else:
        current_exempt = Decimal('0')
        new_exempt = Decimal('0')

    current_taxable = current_amount - current_exempt
    new_taxable = new_amount - new_exempt

    # Impact on tax
    # Simplified: calculate marginal tax impact
    pension = employee_pension(basic_salary)
    current_taxable_income = basic_salary + current_taxable - pension
    new_taxable_income = basic_salary + new_taxable - pension

    current_tax = calculate_tax(current_taxable_income)
    new_tax = calculate_tax(new_taxable_income)
    tax_change = new_tax - current_tax

    # Net pay impact
    net_change = (new_amount - current_amount) - tax_change

    return {
        'type': 'allowance_change',
        'allowance_type': allowance_type,
        'before': {
            'amount': current_amount,
            'exempt': current_exempt,
            'taxable': current_taxable,
            'tax': current_tax,
        },
        'after': {
            'amount': new_amount,
            'exempt': new_exempt,
            'taxable': new_taxable,
            'tax': new_tax,
        },
        'impact': {
            'amount_change': (new_amount - current_amount).quantize(Q),
            'exempt_change': (new_exempt - current_exempt).quantize(Q),
            'taxable_change': (new_taxable - current_taxable).quantize(Q),
            'tax_change': tax_change.quantize(Q),
            'net_change': net_change.quantize(Q),
            'annual_net_change': (net_change * 12).quantize(Q),
        },
        'exempt_cap': exempt_cap,
        'tax_treatment': tax_treatment,
    }


def format_etb(amount) -> str:
    """Format amount as ETB string."""
    return f"ETB {amount:,.2f}"
