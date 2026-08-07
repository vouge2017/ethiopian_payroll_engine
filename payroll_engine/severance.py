"""
Ethiopian Severance Pay Calculator

Labor Proclamation No. 1156/2019, Article 40:

Formula:
    Year 1: 30 days of average daily wages
    Each additional year: +1/3 of the base (≈10 days per year)
    Cap: 12 months of salary (Art. 40(3))

Daily rate = monthly_salary / 30

Example:
    1 year:  30 days = 1 month
    2 years: 30 + 10 = 40 days
    3 years: 30 + 20 = 50 days
    5 years: 30 + 40 = 70 days
    10 years: 30 + 90 = 120 days (10 months)
    Cap: 365 days (12 months)

Applies to:
    - Termination without cause
    - Redundancy
    - Mutual agreement
    - Other eligible reasons (Art. 39)

Does NOT apply to:
    - Resignation
    - Termination for cause (theft, gross misconduct, repeated violation)

All constants are configurable via TaxRule.rules_json['severance'].
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Q = Decimal('0.01')

# Default values per Ethiopian law Art. 40
DEFAULT_BASE_DAYS = 30  # Art. 40(1): 30 days for first year
DEFAULT_INCREMENT_FACTOR = Decimal('0.333')  # Art. 40(2): 1/3 increment per year
DEFAULT_MAX_SEVERANCE_MONTHS = 12  # Art. 40(3): cap at 12 months

# Cache
_rules_cache = {}
_rules_cache_ttl = 300
_rules_cache_timestamps = {}


def invalidate_severance_cache():
    """Clear the severance rules cache."""
    _rules_cache.clear()
    _rules_cache_timestamps.clear()


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _get_severance_rules(for_date=None) -> dict:
    """Fetch severance rules from database, falling back to defaults."""
    cache_key = str(for_date) if for_date else 'default'
    import time

    now = time.time()
    if cache_key in _rules_cache:
        cached_time = _rules_cache_timestamps.get(cache_key, 0)
        if now - cached_time < _rules_cache_ttl:
            return _rules_cache[cache_key]
        del _rules_cache[cache_key]
        del _rules_cache_timestamps[cache_key]

    result = {
        'base_days': DEFAULT_BASE_DAYS,
        'increment_factor': DEFAULT_INCREMENT_FACTOR,
        'max_months': DEFAULT_MAX_SEVERANCE_MONTHS,
    }

    try:
        from payroll_engine.models import TaxRule

        rule = TaxRule.get_active_rule(for_date)
        if rule:
            sv = rule.rules_json.get('severance', {})
            if 'base_days' in sv:
                result['base_days'] = int(sv['base_days'])
            if 'increment_factor' in sv:
                result['increment_factor'] = _D(sv['increment_factor'])
            if 'max_months' in sv:
                result['max_months'] = int(sv['max_months'])
    except Exception:
        pass

    _rules_cache[cache_key] = result
    _rules_cache_timestamps[cache_key] = now
    return result


class TerminationReason:
    RESIGNATION = 'resignation'
    TERMINATION_FOR_CAUSE = 'termination_for_cause'
    REDUNDANCY = 'redundancy'
    MUTUAL_AGREEMENT = 'mutual_agreement'

    SEVERANCE_ELIGIBLE = {REDUNDANCY, MUTUAL_AGREEMENT}
    SEVERANCE_INELIGIBLE = {RESIGNATION, TERMINATION_FOR_CAUSE}

    ALL = {RESIGNATION, TERMINATION_FOR_CAUSE, REDUNDANCY, MUTUAL_AGREEMENT}


def calculate_years_of_service(start_date, end_date) -> Decimal:
    """
    Calculate years of service as a decimal.

    Args:
        start_date: Employment start date (date object or YYYY-MM-DD string)
        end_date: Termination/last working date (date object or YYYY-MM-DD string)

    Returns:
        Years of service as Decimal (e.g., 5.50 for 5 years and 6 months)
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    if end_date <= start_date:
        return Decimal('0')

    delta = end_date - start_date
    return (Decimal(str(delta.days)) / Decimal('365.25')).quantize(Q, rounding=ROUND_HALF_UP)


def calculate_severance(monthly_salary, start_date, end_date, termination_reason: str, for_date=None) -> dict:
    """
    Calculate severance pay for a terminated employee.

    Args:
        monthly_salary: Monthly basic salary in ETB
        start_date: Employment start date
        end_date: Last working date
        termination_reason: One of TerminationReason constants
        for_date: Optional date for rule versioning

    Returns:
        Dict with: eligible, years_of_service, calculated_amount,
                   capped_amount, final_amount, reason
        All monetary values are Decimal.
    """
    monthly_salary = _D(monthly_salary)

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    years = calculate_years_of_service(start_date, end_date)
    rules = _get_severance_rules(for_date)
    max_months = rules['max_months']

    # Check eligibility
    if termination_reason in TerminationReason.SEVERANCE_INELIGIBLE:
        return {
            'eligible': False,
            'years_of_service': years,
            'calculated_amount': Decimal('0'),
            'capped_amount': Decimal('0'),
            'final_amount': Decimal('0'),
            'reason': _ineligibility_reason(termination_reason),
        }

    if termination_reason not in TerminationReason.ALL:
        return {
            'eligible': False,
            'years_of_service': years,
            'calculated_amount': Decimal('0'),
            'capped_amount': Decimal('0'),
            'final_amount': Decimal('0'),
            'reason': f"Unknown termination reason: '{termination_reason}'",
        }

    # Calculate using Art. 40 formula:
    # Year 1: base_days (30 days)
    # Each additional year: +increment_factor (1/3) of base_days
    # Cap: max_months (12 months = 365 days)
    base_days = Decimal(str(rules['base_days']))
    increment_factor = rules['increment_factor']
    max_days = Decimal(str(max_months)) * Decimal('30')  # 12 months = 360 days

    whole_years = int(years)
    fractional = years - Decimal(str(whole_years))

    # Base: 30 days for first year
    total_days = base_days

    # Additional years: +1/3 of base per year
    if whole_years >= 1:
        additional_years = whole_years - 1
        total_days += base_days * increment_factor * Decimal(str(additional_years))

    # Prorate partial year
    if fractional > 0 and whole_years >= 1:
        total_days += base_days * increment_factor * fractional
    elif fractional > 0 and whole_years == 0:
        # Less than 1 year: prorate base
        total_days = base_days * fractional

    # Cap
    total_days = min(total_days, max_days)

    # Convert to money: daily_rate × days
    daily_rate = monthly_salary / Decimal('30')
    calculated = daily_rate * total_days
    cap = monthly_salary * max_months
    capped = min(calculated, cap)
    final = capped.quantize(Q, rounding=ROUND_HALF_UP)

    return {
        'eligible': True,
        'years_of_service': years,
        'calculated_amount': calculated.quantize(Q, rounding=ROUND_HALF_UP),
        'capped_amount': cap.quantize(Q, rounding=ROUND_HALF_UP),
        'final_amount': final,
        'reason': _calculation_explanation(monthly_salary, years, calculated, cap, final, max_months),
    }


def _ineligibility_reason(reason: str) -> str:
    if reason == TerminationReason.RESIGNATION:
        return 'Resignation — no severance payable (Labor Proclamation 1156/2019, Art. 40)'
    elif reason == TerminationReason.TERMINATION_FOR_CAUSE:
        return 'Termination for cause — no severance payable (Labor Proclamation 1156/2019, Art. 40)'
    return f'Not eligible for severance: {reason}'


def _calculation_explanation(salary, years, calculated, cap, final, max_months) -> str:
    """Generate plain-language explanation of severance calculation."""
    daily_rate = salary / Decimal('30')
    lines = [
        'Severance calculation (Labor Proclamation 1156/2019, Art. 40):',
        f'  Monthly salary: ETB {salary:,.2f}',
        f'  Daily rate (salary/30): ETB {daily_rate:,.2f}',
        f'  Years of service: {years}',
        '  Formula: 30 days (year 1) + 10 days per additional year',
        f'  Calculated: ETB {calculated:,.2f}',
    ]
    if calculated > cap:
        lines.append(f'  Capped at {max_months} months: ETB {cap:,.2f}')
    lines.append(f'  Severance payable: ETB {final:,.2f}')
    return '\n'.join(lines)


def format_severance_for_payslip(result: dict) -> dict:
    """
    Format severance result for inclusion in a payslip.

    Returns:
        Dict with label, amount, and explanation suitable for payslip display.
    """
    if not result['eligible']:
        return None

    return {
        'label': 'Severance Pay / የስራ ማቆያ ክፍያ',
        'amount': result['final_amount'],
        'explanation': result['reason'],
    }
