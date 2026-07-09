"""
Single entry point for payroll calculation.

This is THE ONLY ALLOWED WAY to calculate payroll.
It enforces the deduction order: Gross → Pension → Taxable → Tax → Net.

Why this exists:
    The deduction order (pension before tax) is a legal requirement.
    If any code path calls calculate_tax(gross) instead of
    calculate_tax(gross - pension), employees are overtaxed.
    This function makes that mistake structurally impossible.

Usage:
    from payroll_engine.payroll import calculate_payroll
    result = calculate_payroll(basic_salary=10000, allowances=2000)
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from payroll_engine.tax import calculate_tax, explain_tax_amharic
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.overtime import calculate_total_overtime

Q = Decimal('0.01')


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def calculate_payroll(basic_salary, allowances=Decimal('0'),
                      overtime_entries: list = None,
                      for_date=None) -> dict:
    """
    Calculate complete payroll for one employee.

    Enforces deduction order:
        Gross (basic + allowances + overtime)
        → Subtract pension (7% of basic ONLY — not affected by overtime)
        → Calculate tax on remainder
        → Subtract tax
        = Net pay

    Args:
        basic_salary: Monthly basic salary in ETB
        allowances: Monthly allowances in ETB (default 0)
        overtime_entries: List of dicts with 'hours' and 'type' keys (optional)
        for_date: Optional date for rule versioning

    Returns:
        Dict with: gross, taxable, tax, pension_employee, pension_employer,
                   net, tax_explanation, overtime_pay, overtime_total_hours
        All monetary values are Decimal.

    Raises:
        ValueError: If basic_salary is negative
    """
    basic_salary = _D(basic_salary)
    allowances = _D(allowances)

    if basic_salary < 0:
        raise ValueError(f"basic_salary cannot be negative: {basic_salary}")
    if allowances < 0:
        raise ValueError(f"allowances cannot be negative: {allowances}")

    # Step 1: Base gross
    base_gross = basic_salary + allowances

    # Step 2: Overtime (added to gross BEFORE tax)
    overtime_pay = Decimal('0')
    overtime_total_hours = Decimal('0')
    overtime_result = None
    if overtime_entries:
        overtime_result = calculate_total_overtime(basic_salary, overtime_entries)
        overtime_pay = overtime_result['total_pay']
        overtime_total_hours = overtime_result['total_hours']

    # Step 3: Total gross (including overtime)
    gross = base_gross + overtime_pay

    # Step 4: Pension (BEFORE tax — legal requirement)
    # Pension is on basic salary ONLY, not affected by overtime
    emp_pen = employee_pension(basic_salary, for_date)
    empr_pen = employer_pension(basic_salary, for_date)

    # Step 5: Taxable = Gross - Pension
    taxable = gross - emp_pen

    # Step 6: Tax on taxable amount
    tax = calculate_tax(taxable, for_date)

    # Step 7: Net = Gross - Tax - Pension
    net = gross - tax - emp_pen

    # Step 8: Tax explanation (bilingual)
    tax_explanation = explain_tax_amharic(taxable, for_date)

    return {
        'gross': gross.quantize(Q, rounding=ROUND_HALF_UP),
        'taxable': taxable.quantize(Q, rounding=ROUND_HALF_UP),
        'tax': tax,
        'pension_employee': emp_pen,
        'pension_employer': empr_pen,
        'net': net.quantize(Q, rounding=ROUND_HALF_UP),
        'tax_explanation': tax_explanation,
        'overtime_pay': overtime_pay,
        'overtime_total_hours': overtime_total_hours,
        'overtime_result': overtime_result,
    }
