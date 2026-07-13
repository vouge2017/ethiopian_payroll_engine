"""
Management Impact Preview

Shows management the financial impact of decisions BEFORE they happen:
- "What if I give Dawit a raise to ETB 15,000?"
- "What if I hire a new employee at ETB 20,000?"
- "What if I add ETB 3,000 transport allowance?"
- "What if I terminate Abebe?"

Simple, clear, actionable. No jargon. Just numbers.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from payroll_engine.payroll import calculate_payroll
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.tax import calculate_tax
from payroll_engine.severance import calculate_severance, TerminationReason
from payroll_engine.services.allowance_service import (
    calculate_transport_exempt_amount, get_effective_allowances
)


Q = Decimal('0.01')


def _D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def preview_salary_raise(current_basic, current_allowances,
                          new_basic, new_allowances,
                          employee_name: str = 'Employee') -> dict:
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


def preview_new_hire(basic_salary, allowances,
                      transport_allowance: Decimal = Decimal('0'),
                      employee_name: str = 'New Employee') -> dict:
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

    # If transport is specified, calculate with exemption
    allowance_records = None
    if transport_allowance > 0:
        from payroll_engine.models import EmployeeAllowance
        cap = calculate_transport_exempt_amount(basic_salary, transport_allowance)
        record = EmployeeAllowance(
            allowance_type='transport',
            amount=transport_allowance,
            tax_treatment='partial',
            exempt_cap_amount=cap,
            is_active=True,
        )
        allowance_records = [record]
        total_allowances = allowances + transport_allowance
    else:
        total_allowances = allowances

    result = calculate_payroll(
        basic_salary=basic_salary,
        allowances=total_allowances if not allowance_records else allowances,
        allowance_records=allowance_records,
    )

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


def preview_termination(basic_salary, allowances, start_date, end_date,
                          termination_reason: str,
                          employee_name: str = 'Employee') -> dict:
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


def preview_allowance_change(current_amount, new_amount,
                              basic_salary, allowance_type: str = 'transport') -> dict:
    """Show management what changing an allowance costs.

    Returns:
    - Tax impact
    - Net pay change for employee
    - Cost change for company
    """
    current_amount = _D(current_amount)
    new_amount = _D(new_amount)
    basic_salary = _D(basic_salary)

    # Current tax calculation
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
            'employer_monthly_change': (new['gross'] + new['pension_employer'] - current['gross'] - current['pension_employer']).quantize(Q),
            'employer_annual_change': ((new['gross'] + new['pension_employer'] - current['gross'] - current['pension_employer']) * 12).quantize(Q),
        },
    }
