"""
Ethiopian Leave Management Engine

Labor Proclamation No. 1156/2019:
    - Annual Leave: 14 days (Year 1), +1 day per additional year
    - Sick Leave: Max 6 months in 12-month period
        - Month 1 (day 1-30): 100% pay
        - Month 2-3 (day 31-90): 50% pay
        - Month 4-6 (day 91-180): 0% pay
    - Maternity Leave: 120 days (30 prenatal + 90 postnatal), 100% pay
    - Paternity Leave: 3 working days, 100% pay
    - Special Leave: 3 days (marriage, death of spouse/child), 100% pay

Companies can offer MORE than statutory minimums but not less.
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


# Statutory minimums (cannot be reduced by company policy)
STATUTORY_ANNUAL_BASE = 14  # days for year 1
STATUTORY_ANNUAL_INCREMENT = 1  # +1 day per year of service
STATUTORY_ANNUAL_MAX = 30  # reasonable cap

STATUTORY_SICK_MAX_DAYS = 180  # 6 months in 12-month period
SICK_TIER_1_DAYS = 30  # 100% pay
SICK_TIER_2_DAYS = 60  # 50% pay (days 31-90)
# Days 91-180: 0% pay

STATUTORY_MATERNITY_DAYS = 120  # 30 pre + 90 post
STATUTORY_PATERNITY_DAYS = 3
STATUTORY_SPECIAL_DAYS = 3  # marriage, bereavement


class LeaveType:
    ANNUAL = 'annual'
    SICK = 'sick'
    MATERNITY = 'maternity'
    PATERNITY = 'paternity'
    SPECIAL = 'special'
    UNPAID = 'unpaid'
    CUSTOM = 'custom'

    ALL_STATUTORY = {ANNUAL, SICK, MATERNITY, PATERNITY, SPECIAL}


def calculate_annual_entitlement(years_of_service: int, company_policy_days: int = None) -> int:
    """Calculate annual leave entitlement based on years of service.

    Args:
        years_of_service: Complete years of employment
        company_policy_days: Company's policy (must be >= statutory minimum)

    Returns:
        Annual leave days entitled
    """
    statutory = STATUTORY_ANNUAL_BASE + (years_of_service * STATUTORY_ANNUAL_INCREMENT)
    statutory = min(statutory, STATUTORY_ANNUAL_MAX)

    if company_policy_days is not None:
        # Company can offer more, but not less
        return max(statutory, company_policy_days)

    return statutory


def calculate_sick_leave_pay(sick_days_used: int, daily_rate: Decimal) -> dict:
    """Calculate sick leave payment based on tiered system.

    Args:
        sick_days_used: Total sick days taken in current 12-month period
        daily_rate: Employee's daily rate (monthly salary / 30)

    Returns:
        Dict with: tier, pay_percentage, days_at_this_tier, pay_amount, total_pay
    """
    if sick_days_used <= 0:
        return {
            'tier': 0,
            'pay_percentage': 100,
            'days_at_this_tier': 0,
            'pay_amount': Decimal('0'),
            'total_pay': Decimal('0'),
            'tiers': [],
            'exhausted': False,
            'days_remaining': STATUTORY_SICK_MAX_DAYS,
        }

    tiers = []
    remaining_days = sick_days_used
    total_pay = Decimal('0')

    # Tier 1: Days 1-30 at 100%
    tier1_days = min(remaining_days, SICK_TIER_1_DAYS)
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

    # Tier 2: Days 31-90 at 50%
    tier2_days = min(remaining_days, SICK_TIER_2_DAYS)
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

    # Tier 3: Days 91-180 at 0%
    tier3_days = min(remaining_days, STATUTORY_SICK_MAX_DAYS - SICK_TIER_1_DAYS - SICK_TIER_2_DAYS)
    if tier3_days > 0:
        tiers.append({
            'tier': 3,
            'days': tier3_days,
            'pay_percentage': 0,
            'pay': Decimal('0'),
        })
        remaining_days -= tier3_days

    # Determine current tier
    if sick_days_used <= SICK_TIER_1_DAYS:
        current_tier = 1
    elif sick_days_used <= SICK_TIER_1_DAYS + SICK_TIER_2_DAYS:
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
        'exhausted': sick_days_used >= STATUTORY_SICK_MAX_DAYS,
        'days_remaining': max(0, STATUTORY_SICK_MAX_DAYS - sick_days_used),
    }


def calculate_leave_balance(employee_start_date: date,
                             leave_type: str,
                             leave_taken: int = 0,
                             year: int = None,
                             company_policy_days: int = None) -> dict:
    """Calculate current leave balance.

    Args:
        employee_start_date: Employment start date
        leave_type: Leave type (annual, sick, maternity, etc.)
        leave_taken: Days already taken
        year: Year to calculate for (default: current year)
        company_policy_days: Company's policy days (must >= statutory)

    Returns:
        Dict with: entitled, taken, remaining, accrued, details
    """
    today = date.today()
    if year is None:
        year = today.year

    # Calculate years of service
    years_of_service = (today - employee_start_date).days // 365

    if leave_type == LeaveType.ANNUAL:
        entitled = calculate_annual_entitlement(years_of_service, company_policy_days)

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
        # Sick leave: 6 months per 12-month period
        # Reset on employment anniversary
        anniversary_this_year = employee_start_date.replace(year=year)
        if today < anniversary_this_year:
            period_start = employee_start_date.replace(year=year - 1)
        else:
            period_start = anniversary_this_year

        return {
            'leave_type': leave_type,
            'entitled': STATUTORY_SICK_MAX_DAYS,
            'taken': leave_taken,
            'remaining': max(0, STATUTORY_SICK_MAX_DAYS - leave_taken),
            'period_start': period_start,
            'period_end': period_start + timedelta(days=365),
            'pay_tiers': calculate_sick_leave_pay(leave_taken, Decimal('1')),  # Simplified
        }

    elif leave_type == LeaveType.MATERNITY:
        return {
            'leave_type': leave_type,
            'entitled': STATUTORY_MATERNITY_DAYS,
            'taken': leave_taken,
            'remaining': max(0, STATUTORY_MATERNITY_DAYS - leave_taken),
            'note': '120 days: 30 prenatal + 90 postnatal',
        }

    elif leave_type == LeaveType.PATERNITY:
        return {
            'leave_type': leave_type,
            'entitled': STATUTORY_PATERNITY_DAYS,
            'taken': leave_taken,
            'remaining': max(0, STATUTORY_PATERNITY_DAYS - leave_taken),
        }

    elif leave_type == LeaveType.SPECIAL:
        return {
            'leave_type': leave_type,
            'entitled': STATUTORY_SPECIAL_DAYS,
            'taken': leave_taken,
            'remaining': max(0, STATUTORY_SPECIAL_DAYS - leave_taken),
            'note': 'For marriage or death of spouse/child/close relative',
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
                           employee_name: str) -> dict:
    """Validate a leave request against balances and rules.

    Returns:
        Dict with: valid (bool), errors (list), warnings (list)
    """
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
    if leave_type == LeaveType.MATERNITY and requested_days < STATUTORY_MATERNITY_DAYS:
        warnings.append(
            f'Maternity leave is typically {STATUTORY_MATERNITY_DAYS} continuous days. '
            f'You requested {requested_days} days.'
        )

    # Sick leave: warn if approaching tier change
    if leave_type == LeaveType.SICK:
        current_taken = balance.get('taken', 0)
        if current_taken + requested_days > SICK_TIER_1_DAYS and current_taken <= SICK_TIER_1_DAYS:
            warnings.append(
                f'This sick leave will cross the {SICK_TIER_1_DAYS}-day mark. '
                f'Pay will drop to 50% after day {SICK_TIER_1_DAYS}.'
            )
        if current_taken + requested_days > (SICK_TIER_1_DAYS + SICK_TIER_2_DAYS):
            if current_taken <= (SICK_TIER_1_DAYS + SICK_TIER_2_DAYS):
                warnings.append(
                    f'This sick leave will cross the 90-day mark. '
                    f'Pay will drop to 0% after day 90.'
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
