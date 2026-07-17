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


def calculate_prorated_salary(monthly_salary, start_date, end_date=None) -> Decimal:
    """
    Prorate salary for partial-month employment.

    Ethiopian convention: 30 days/month. If an employee starts mid-month,
    they're paid for the days worked.

    Formula: (monthly_salary / 30) × days_worked

    Args:
        monthly_salary: Full monthly salary (basic or allowances)
        start_date: Employment start date (date or YYYY-MM-DD string)
        end_date: End of pay period (defaults to last day of start_date's month)

    Returns:
        Prorated salary amount in ETB, as Decimal
    """
    from datetime import date as _date, datetime as _dt

    monthly_salary = _D(monthly_salary)
    if monthly_salary <= 0:
        return Decimal('0')

    if isinstance(start_date, str):
        start_date = _dt.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = _dt.strptime(end_date, '%Y-%m-%d').date()

    if end_date is None:
        # Default to last day of start_date's month
        if start_date.month == 12:
            end_date = _date(start_date.year + 1, 1, 1) - _date.resolution
        else:
            end_date = _date(start_date.year, start_date.month + 1, 1) - _date.resolution

    if end_date < start_date:
        return Decimal('0')

    # Days worked = end_date - start_date + 1 (inclusive)
    days_worked = (end_date - start_date).days + 1
    days_in_month = 30  # Ethiopian convention

    if days_worked >= days_in_month:
        return monthly_salary  # Full month, no proration needed

    prorated = (monthly_salary / Decimal(str(days_in_month))) * Decimal(str(days_worked))
    return prorated.quantize(Q, rounding=ROUND_HALF_UP)


def calculate_daily_worker_payroll(daily_rate, days_worked) -> dict:
    """
    Calculate payroll for a daily-paid worker.

    Daily workers:
    - Paid: daily_rate × days_worked
    - No pension deduction (not covered by pension law)
    - Tax calculated on gross (no pension deduction first)
    - No allowances

    Args:
        daily_rate: Daily pay rate in ETB
        days_worked: Number of days worked in the month

    Returns:
        Same dict structure as calculate_payroll
    """
    daily_rate = _D(daily_rate)
    days_worked = _D(days_worked)

    if daily_rate < 0:
        raise ValueError(f"daily_rate cannot be negative: {daily_rate}")
    if days_worked < 0:
        days_worked = Decimal('0')

    gross = (daily_rate * days_worked).quantize(Q, rounding=ROUND_HALF_UP)

    # No pension for daily workers
    emp_pen = Decimal('0')
    empr_pen = Decimal('0')

    # Tax on full gross (no pension deduction)
    taxable = gross
    tax = calculate_tax(taxable)

    net = gross - tax

    return {
        'gross': gross,
        'taxable': taxable.quantize(Q, rounding=ROUND_HALF_UP),
        'tax': tax,
        'pension_employee': emp_pen,
        'pension_employer': empr_pen,
        'net_before_deductions': net.quantize(Q, rounding=ROUND_HALF_UP),
        'sick_leave_reduction': Decimal('0'),
        'total_deductions': Decimal('0'),
        'deduction_details': [],
        'net': net.quantize(Q, rounding=ROUND_HALF_UP),
        'tax_explanation': explain_tax_amharic(taxable),
        'overtime_pay': Decimal('0'),
        'overtime_total_hours': Decimal('0'),
        'overtime_result': None,
        'exempt_allowances': Decimal('0'),
        'taxable_allowances': Decimal('0'),
        'allowance_details': [],
    }


def calculate_payroll(basic_salary, allowances=Decimal('0'),
                      overtime_entries: list = None,
                      for_date=None,
                      deductions: list = None,
                      allowance_records: list = None,
                      sick_leave_reduction: Decimal = Decimal('0')) -> dict:
    """
    Calculate complete payroll for one employee.

    Enforces deduction order:
        Gross (basic + allowances + overtime)
        → Subtract pension (7% of basic ONLY — not affected by overtime)
        → Calculate exempt allowances (transport cap, hardship, etc.)
        → Apply sick leave reduction (if employee exceeded tier 1)
        → Calculate tax on remainder
        → Subtract tax
        → Apply post-tax deductions (cost-sharing, court orders, etc.)
        = Net pay

    Args:
        basic_salary: Monthly basic salary in ETB
        allowances: Monthly allowances in ETB (default 0) — used if no allowance_records
        overtime_entries: List of dicts with 'hours' and 'type' keys (optional)
        for_date: Optional date for rule versioning
        deductions: List of EmployeeDeduction objects (optional, applied post-tax)
        allowance_records: List of EmployeeAllowance objects (optional, for exemption calculation)
        sick_leave_reduction: Amount to deduct for sick leave pay reduction (optional)
            When employee exceeds 30 sick days, pay drops to 50%. This is the reduction amount.

    Returns:
        Dict with: gross, taxable, tax, pension_employee, pension_employer,
                   net, tax_explanation, overtime_pay, overtime_total_hours,
                   total_deductions, deduction_details, exempt_allowances, taxable_allowances,
                   sick_leave_reduction

    Raises:
        ValueError: If basic_salary is negative
    """
    basic_salary = _D(basic_salary)
    allowances = _D(allowances)

    if basic_salary < 0:
        raise ValueError(f"basic_salary cannot be negative: {basic_salary}")
    if allowances < 0:
        raise ValueError(f"allowances cannot be negative: {allowances}")

    # Step 1: Calculate allowance breakdown with exemptions
    exempt_allowances = Decimal('0')
    taxable_allowances = Decimal('0')
    allowance_details = []

    if allowance_records:
        for record in allowance_records:
            if not record.is_active:
                continue
            exempt_amount = record.calculated_exempt_amount
            taxable_amount = record.taxable_amount
            exempt_allowances += exempt_amount
            taxable_allowances += taxable_amount
            allowance_details.append({
                'type': record.allowance_type,
                'type_label': record.type_label,
                'amount': record.amount,
                'exempt': exempt_amount,
                'taxable': taxable_amount,
                'tax_treatment': record.tax_treatment,
            })
        total_allowances = exempt_allowances + taxable_allowances
    else:
        # Fallback: treat all allowances as taxable (backward compatibility)
        total_allowances = allowances
        taxable_allowances = allowances
        exempt_allowances = Decimal('0')

    # Step 2: Base gross
    base_gross = basic_salary + total_allowances

    # Step 3: Overtime (added to gross BEFORE tax)
    overtime_pay = Decimal('0')
    overtime_total_hours = Decimal('0')
    overtime_result = None
    if overtime_entries:
        overtime_result = calculate_total_overtime(basic_salary, overtime_entries)
        overtime_pay = overtime_result['total_pay']
        overtime_total_hours = overtime_result['total_hours']

    # Step 4: Total gross (including overtime)
    gross = base_gross + overtime_pay

    # Step 5: Pension (BEFORE tax — legal requirement)
    # Pension is on basic salary ONLY, not affected by overtime or allowances
    emp_pen = employee_pension(basic_salary, for_date)
    empr_pen = employer_pension(basic_salary, for_date)

    # Step 6: Taxable = Gross - Pension - Exempt Allowances
    taxable = gross - emp_pen - exempt_allowances
    taxable = max(Decimal('0'), taxable)  # Cannot be negative

    # Step 7: Tax on taxable amount
    tax = calculate_tax(taxable, for_date)

    # Step 8: Net before post-tax deductions
    net_before_deductions = gross - tax - emp_pen

    # Step 9: Post-tax deductions (cost-sharing, court orders, penalties, loans)
    total_deductions = Decimal('0')
    deduction_details = []
    if deductions:
        for ded in deductions:
            if not ded.is_active:
                continue
            ded_amount = ded.calculate_deduction(net_before_deductions)
            if ded_amount > 0:
                total_deductions += ded_amount
                deduction_details.append({
                    'id': ded.id,
                    'type': ded.deduction_type,
                    'type_label': ded.type_label,
                    'label': ded.label,
                    'amount': ded_amount,
                    'remaining_balance': ded.remaining_balance,
                    'warning': ded.warning_message,
                })

    # Step 10: Apply sick leave reduction (if employee exceeded tier 1)
    sick_leave_reduction = _D(sick_leave_reduction)
    net_after_sick = net_before_deductions - sick_leave_reduction
    net_after_sick = max(Decimal('0'), net_after_sick)  # Cannot go below zero

    # Step 11: Final net = Net after sick reduction - post-tax deductions
    net = net_after_sick - total_deductions

    # Step 12: Tax explanation (bilingual)
    tax_explanation = explain_tax_amharic(taxable, for_date)

    return {
        'gross': gross.quantize(Q, rounding=ROUND_HALF_UP),
        'taxable': taxable.quantize(Q, rounding=ROUND_HALF_UP),
        'tax': tax,
        'pension_employee': emp_pen,
        'pension_employer': empr_pen,
        'net_before_deductions': net_before_deductions.quantize(Q, rounding=ROUND_HALF_UP),
        'sick_leave_reduction': sick_leave_reduction.quantize(Q, rounding=ROUND_HALF_UP),
        'total_deductions': total_deductions.quantize(Q, rounding=ROUND_HALF_UP),
        'deduction_details': deduction_details,
        'net': net.quantize(Q, rounding=ROUND_HALF_UP),
        'tax_explanation': tax_explanation,
        'overtime_pay': overtime_pay,
        'overtime_total_hours': overtime_total_hours,
        'overtime_result': overtime_result,
        'exempt_allowances': exempt_allowances.quantize(Q, rounding=ROUND_HALF_UP),
        'taxable_allowances': taxable_allowances.quantize(Q, rounding=ROUND_HALF_UP),
        'allowance_details': allowance_details,
    }


def generate_calculation_flow(result: dict) -> dict:
    """Generate a step-by-step calculation flow from payroll result.

    Returns a dict with:
        steps: list of {label, amount, note, is_deduction} dicts
        effective_tax_rate: Decimal (percentage)
        summary: plain-language one-liner
    """
    gross = _D(result.get('gross', 0))
    pension = _D(result.get('pension_employee', 0))
    exempt = _D(result.get('exempt_allowances', 0))
    taxable = _D(result.get('taxable', 0))
    tax = _D(result.get('tax', 0))
    net = _D(result.get('net', 0))

    steps = [
        {
            'label': 'Gross Salary',
            'amount': gross,
            'note': 'Basic + Allowances + Overtime',
            'is_deduction': False,
            'icon': '💰',
        },
        {
            'label': 'Employee Pension (7%)',
            'amount': pension,
            'note': f'7% of basic salary — deducted before tax',
            'is_deduction': True,
            'icon': '🏦',
        },
    ]

    if exempt > 0:
        steps.append({
            'label': 'Exempt Allowances',
            'amount': exempt,
            'note': 'Tax-free allowances (transport cap, hardship, etc.)',
            'is_deduction': True,
            'icon': '📋',
        })

    steps.append({
        'label': 'Taxable Income',
        'amount': taxable,
        'note': 'Gross − Pension − Exempt Allowances',
        'is_deduction': False,
        'icon': '📊',
        'is_highlight': True,
    })

    steps.append({
        'label': 'Income Tax',
        'amount': tax,
        'note': 'Progressive brackets (Proclamation 1395/2025)',
        'is_deduction': True,
        'icon': '🏛️',
    })

    steps.append({
        'label': 'Net Pay',
        'amount': net,
        'note': 'What the employee takes home',
        'is_deduction': False,
        'icon': '✅',
        'is_final': True,
    })

    # Effective tax rate
    effective_rate = (tax / gross * 100).quantize(Q) if gross > 0 else Decimal('0')

    # Plain-language summary
    summary = (
        f"ETB {gross:,.2f} gross → "
        f"Pension {pension:,.2f} → "
        f"Taxable {taxable:,.2f} → "
        f"Tax {tax:,.2f} → "
        f"Net {net:,.2f}"
    )

    return {
        'steps': steps,
        'effective_tax_rate': effective_rate,
        'summary': summary,
    }
