"""
Ethiopian Leave Management Engine

Labor Proclamation No. 1156/2019:
    - Annual Leave: 16 days (Year 1), +1 day per 2 additional years (Art. 77)
    - Sick Leave: Max 6 months in 12-month period (Art. 85)
        - Month 1 (day 1-30): 100% pay (Art. 86(1))
        - Month 2-3 (day 31-90): 50% pay (Art. 86(2))
        - Month 4-6 (day 91-180): 0% pay (Art. 86(3))
    - Maternity Leave: 120 days (30 prenatal + 90 postnatal), 100% pay (Art. 88)
    - Paternity Leave: 3 working days, 100% pay (Art. 81(2))
    - Special Leave: 5 days unpaid, max 2 times per year (Art. 81(3))

Companies can offer MORE than statutory minimums but not less.

All leave constants are configurable via TaxRule.rules_json['leave'].
When no database rule exists, falls back to hardcoded defaults (Ethiopian law).
"""

from datetime import date, timedelta
from decimal import Decimal

# Default statutory minimums (cannot be reduced by company policy)
DEFAULT_ANNUAL_BASE = 16          # Art. 77(1)(a): 16 days for year 1
DEFAULT_ANNUAL_INCREMENT = 1      # Art. 77(1)(b): +1 day per 2 years of service
DEFAULT_ANNUAL_INCREMENT_YEARS = 2  # Increment applies every 2 years
DEFAULT_ANNUAL_MAX = 30           # reasonable cap (not in law)

DEFAULT_SICK_MAX_DAYS = 180       # Art. 85(2): 6 months in 12-month period
DEFAULT_SICK_TIER_1_DAYS = 30     # Art. 86(1): 100% pay
DEFAULT_SICK_TIER_2_DAYS = 60     # Art. 86(2): 50% pay (days 31-90)
# Days 91-180: 0% pay (Art. 86(3))

DEFAULT_MATERNITY_DAYS = 120      # Art. 88(3): 30 pre + 90 post
DEFAULT_PATERNITY_DAYS = 3        # Art. 81(2): 3 consecutive days, full pay
DEFAULT_SPECIAL_DAYS = 5          # Art. 81(3): 5 days unpaid, max 2x/year
DEFAULT_SPECIAL_UNPAID = True     # Art. 81(3): unpaid
DEFAULT_SPECIAL_MAX_PER_YEAR = 2  # Art. 81(3): max 2 times per budget year

# Cache for leave rules
_rules_cache = {}
_rules_cache_ttl = 300
_rules_cache_timestamps = {}


def invalidate_leave_cache():
    """Clear the leave rules cache. Call after updating TaxRule records."""
    _rules_cache.clear()
    _rules_cache_timestamps.clear()


def _get_leave_rules(for_date=None) -> dict:
    """Fetch leave rules from database, falling back to defaults."""
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
        'annual_base': DEFAULT_ANNUAL_BASE,
        'annual_increment': DEFAULT_ANNUAL_INCREMENT,
        'annual_increment_years': DEFAULT_ANNUAL_INCREMENT_YEARS,
        'annual_max': DEFAULT_ANNUAL_MAX,
        'sick_max_days': DEFAULT_SICK_MAX_DAYS,
        'sick_tier_1_days': DEFAULT_SICK_TIER_1_DAYS,
        'sick_tier_2_days': DEFAULT_SICK_TIER_2_DAYS,
        'maternity_days': DEFAULT_MATERNITY_DAYS,
        'paternity_days': DEFAULT_PATERNITY_DAYS,
        'special_days': DEFAULT_SPECIAL_DAYS,
        'special_unpaid': DEFAULT_SPECIAL_UNPAID,
        'special_max_per_year': DEFAULT_SPECIAL_MAX_PER_YEAR,
    }

    try:
        from payroll_engine.models import TaxRule
        rule = TaxRule.get_active_rule(for_date)
        if rule:
            lv = rule.rules_json.get('leave', {})
            for key in result:
                if key in lv:
                    result[key] = int(lv[key])
    except Exception:
        pass

    _rules_cache[cache_key] = result
    _rules_cache_timestamps[cache_key] = now
    return result


class LeaveType:
    ANNUAL = 'annual'
    SICK = 'sick'
    MATERNITY = 'maternity'
    PATERNITY = 'paternity'
    SPECIAL = 'special'
    UNPAID = 'unpaid'
    CUSTOM = 'custom'

    ALL_STATUTORY = {ANNUAL, SICK, MATERNITY, PATERNITY, SPECIAL}


def calculate_annual_entitlement(years_of_service: int, company_policy_days: int = None,
                                  for_date=None) -> int:
    """Calculate annual leave entitlement based on years of service.

    Art. 77(1): 16 days for year 1, +1 day per 2 additional years.

    Args:
        years_of_service: Complete years of employment
        company_policy_days: Company's policy (must be >= statutory minimum)
        for_date: Optional date for rule versioning

    Returns:
        Annual leave days entitled
    """
    rules = _get_leave_rules(for_date)
    increment_years = rules.get('annual_increment_years', 2)
    # Year 1: base days. After that: +increment per every increment_years
    additional_years = max(0, years_of_service - 1)
    increments = additional_years // increment_years
    statutory = rules['annual_base'] + (increments * rules['annual_increment'])
    statutory = min(statutory, rules['annual_max'])

    if company_policy_days is not None:
        # Company can offer more, but not less
        return max(statutory, company_policy_days)

    return statutory


def calculate_sick_leave_pay(sick_days_used: int, daily_rate: Decimal,
                              for_date=None) -> dict:
    """Calculate sick leave payment based on tiered system.

    Args:
        sick_days_used: Total sick days taken in current 12-month period
        daily_rate: Employee's daily rate (monthly salary / 30)
        for_date: Optional date for rule versioning

    Returns:
        Dict with: tier, pay_percentage, days_at_this_tier, pay_amount, total_pay
    """
    rules = _get_leave_rules(for_date)
    max_days = rules['sick_max_days']
    tier1 = rules['sick_tier_1_days']
    tier2 = rules['sick_tier_2_days']

    if sick_days_used <= 0:
        return {
            'tier': 0,
            'pay_percentage': 100,
            'days_at_this_tier': 0,
            'pay_amount': Decimal('0'),
            'total_pay': Decimal('0'),
            'tiers': [],
            'exhausted': False,
            'days_remaining': max_days,
        }

    tiers = []
    remaining_days = sick_days_used
    total_pay = Decimal('0')

    # Tier 1: Days 1-N at 100%
    tier1_days = min(remaining_days, tier1)
    if tier1_days > 0:
        tier1_pay = (daily_rate * Decimal(str(tier1_days))).quantize(Decimal('0.01'))
        tiers.append({
            'tier': 1,
            'days': tier1_days,
            'pay_percentage': 100,
            'pay': tier1_pay,
        })
        total_pay += tier1_pay
        remaining_days -= tier1_days

    # Tier 2: Days (tier1+1)-(tier1+tier2) at 50%
    tier2_days = min(remaining_days, tier2)
    if tier2_days > 0:
        tier2_pay = (daily_rate * Decimal('0.5') * Decimal(str(tier2_days))).quantize(Decimal('0.01'))
        tiers.append({
            'tier': 2,
            'days': tier2_days,
            'pay_percentage': 50,
            'pay': tier2_pay,
        })
        total_pay += tier2_pay
        remaining_days -= tier2_days

    # Tier 3: Remaining days at 0%
    tier3_days = min(remaining_days, max_days - tier1 - tier2)
    if tier3_days > 0:
        tiers.append({
            'tier': 3,
            'days': tier3_days,
            'pay_percentage': 0,
            'pay': Decimal('0'),
        })
        remaining_days -= tier3_days

    # Determine current tier
    if sick_days_used <= tier1:
        current_tier = 1
    elif sick_days_used <= tier1 + tier2:
        current_tier = 2
    else:
        current_tier = 3

    return {
        'tier': current_tier,
        'pay_percentage': tiers[-1]['pay_percentage'] if tiers else 100,
        'days_at_this_tier': tiers[-1]['days'] if tiers else 0,
        'pay_amount': tiers[-1]['pay'] if tiers else Decimal('0'),
        'total_pay': total_pay,
        'tiers': tiers,
        'exhausted': sick_days_used >= max_days,
        'days_remaining': max(0, max_days - sick_days_used),
    }


def calculate_leave_balance(employee_start_date: date,
                             leave_type: str,
                             leave_taken: int = 0,
                             year: int = None,
                             company_policy_days: int = None,
                             for_date=None) -> dict:
    """Calculate current leave balance.

    Args:
        employee_start_date: Employment start date
        leave_type: Leave type (annual, sick, maternity, etc.)
        leave_taken: Days already taken
        year: Year to calculate for (default: current year)
        company_policy_days: Company's policy days (must >= statutory)
        for_date: Optional date for rule versioning

    Returns:
        Dict with: entitled, taken, remaining, accrued, details
    """
    today = date.today()
    if year is None:
        year = today.year

    rules = _get_leave_rules(for_date)

    # Calculate years of service
    years_of_service = (today - employee_start_date).days // 365

    if leave_type == LeaveType.ANNUAL:
        entitled = calculate_annual_entitlement(years_of_service, company_policy_days, for_date)

        # Accrual: proportional to time worked in the year
        if employee_start_date.year == year:
            # Started this year - prorate
            start_of_year = date(year, 1, 1)
            days_worked = (today - max(employee_start_date, start_of_year)).days
            days_in_year = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
            accrued = int(entitled * days_worked / days_in_year)
        else:
            accrued = entitled

        remaining = max(0, accrued - leave_taken)

        return {
            'leave_type': leave_type,
            'entitled': entitled,
            'accrued': accrued,
            'taken': leave_taken,
            'remaining': remaining,
            'years_of_service': years_of_service,
            'carry_forward': max(0, entitled - leave_taken) if leave_taken < entitled else 0,
        }

    elif leave_type == LeaveType.SICK:
        max_days = rules['sick_max_days']
        # Sick leave: 6 months per 12-month period
        # Reset on employment anniversary
        anniversary_this_year = employee_start_date.replace(year=year)
        if today < anniversary_this_year:
            period_start = employee_start_date.replace(year=year - 1)
        else:
            period_start = anniversary_this_year

        return {
            'leave_type': leave_type,
            'entitled': max_days,
            'taken': leave_taken,
            'remaining': max(0, max_days - leave_taken),
            'period_start': period_start,
            'period_end': period_start + timedelta(days=365),
            'pay_tiers': calculate_sick_leave_pay(leave_taken, Decimal('1'), for_date),
        }

    elif leave_type == LeaveType.MATERNITY:
        maternity = rules['maternity_days']
        return {
            'leave_type': leave_type,
            'entitled': maternity,
            'taken': leave_taken,
            'remaining': max(0, maternity - leave_taken),
            'note': f'{maternity} days: 30 prenatal + 90 postnatal',
        }

    elif leave_type == LeaveType.PATERNITY:
        paternity = rules['paternity_days']
        return {
            'leave_type': leave_type,
            'entitled': paternity,
            'taken': leave_taken,
            'remaining': max(0, paternity - leave_taken),
        }

    elif leave_type == LeaveType.SPECIAL:
        special = rules['special_days']
        unpaid = rules.get('special_unpaid', True)
        max_per_year = rules.get('special_max_per_year', 2)
        return {
            'leave_type': leave_type,
            'entitled': special,
            'taken': leave_taken,
            'remaining': max(0, special - leave_taken),
            'unpaid': unpaid,
            'max_per_year': max_per_year,
            'note': f'Art. 81(3): {special} days {"unpaid" if unpaid else "paid"}, max {max_per_year}x per year. For exceptional/serious events.',
        }

    return {
        'leave_type': leave_type,
        'entitled': company_policy_days or 0,
        'taken': leave_taken,
        'remaining': max(0, (company_policy_days or 0) - leave_taken),
    }


def validate_leave_request(leave_type: str,
                           start_date: date,
                           end_date: date,
                           balance: dict,
                           employee_name: str,
                           for_date=None) -> dict:
    """Validate a leave request against balances and rules.

    Returns:
        Dict with: valid (bool), errors (list), warnings (list)
    """
    rules = _get_leave_rules(for_date)
    errors = []
    warnings = []

    # Basic date validation
    if end_date < start_date:
        errors.append('End date cannot be before start date.')
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    # Calculate requested days (excluding rest days for simplicity)
    requested_days = (end_date - start_date).days + 1

    # Check balance
    remaining = balance.get('remaining', 0)
    if requested_days > remaining:
        errors.append(
            f'Requested {requested_days} days but only {remaining} remaining. '
            f'Entitled: {balance.get("entitled", 0)}, Taken: {balance.get("taken", 0)}.'
        )

    # Maternity: must be continuous
    maternity = rules['maternity_days']
    if leave_type == LeaveType.MATERNITY and requested_days < maternity:
        warnings.append(
            f'Maternity leave is typically {maternity} continuous days. '
            f'You requested {requested_days} days.'
        )

    # Sick leave: warn if approaching tier change
    if leave_type == LeaveType.SICK:
        tier1 = rules['sick_tier_1_days']
        tier2 = rules['sick_tier_2_days']
        current_taken = balance.get('taken', 0)
        if current_taken + requested_days > tier1 and current_taken <= tier1:
            warnings.append(
                f'This sick leave will cross the {tier1}-day mark. '
                f'Pay will drop to 50% after day {tier1}.'
            )
        if current_taken + requested_days > (tier1 + tier2):
            if current_taken <= (tier1 + tier2):
                warnings.append(
                    f'This sick leave will cross the {tier1 + tier2}-day mark. '
                    f'Pay will drop to 0% after day {tier1 + tier2}.'
                )

    # Annual leave: warn if requesting more than 5 consecutive days
    if leave_type == LeaveType.ANNUAL and requested_days > 5:
        warnings.append(
            f'Requesting {requested_days} consecutive days of annual leave. '
            f'Ensure this does not disrupt operations.'
        )

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'requested_days': requested_days,
    }
