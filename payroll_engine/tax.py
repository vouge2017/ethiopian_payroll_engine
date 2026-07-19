"""
Ethiopian Income Tax Calculator (2025/2026)

Progressive tax brackets on monthly taxable salary (ETB):
    0 – 2,000     : 0%
    2,001 – 4,000 : 15%
    4,001 – 7,000 : 20%
    7,001 – 10,000: 25%
    10,001 – 14,000: 30%
    14,001+      : 35%

Relief: A personal relief of ETB 150 is deducted from tax (if tax > 0).

Source: Proclamation No. 1395/2025, effective July 7, 2025.
Verified by: EY, PwC, DABLO Law, Liku Worku Law Office.

Rules are configurable via the TaxRule database model.
When no database rule exists, falls back to hardcoded defaults.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, Tuple

# Quantizer for 2 decimal places
Q = Decimal('0.01')

# Default fallback brackets
# Source: Ethiopian Income Tax (Amendment) Proclamation No. 1395/2025
# Article 36(1) — Rates of Income Tax
# https://lawethiopia.com/images/proc1395-2025.pdf
# Used only when no TaxRule exists in the database
DEFAULT_BRACKETS: List[Tuple[Decimal, Decimal]] = [
    (Decimal('2000'), Decimal('0.00')),
    (Decimal('4000'), Decimal('0.15')),
    (Decimal('7000'), Decimal('0.20')),
    (Decimal('10000'), Decimal('0.25')),
    (Decimal('14000'), Decimal('0.30')),
    (Decimal('Infinity'), Decimal('0.35')),
]

DEFAULT_PERSONAL_RELIEF = Decimal('150')  # ETB monthly personal relief

# Cache for tax brackets with TTL (5 minutes)
# Rules can change via admin UI — cache must not persist stale data forever
# Call invalidate_tax_cache() after updating TaxRule in the database
_brackets_cache = {}
_brackets_cache_ttl = 300  # seconds
_brackets_cache_timestamps = {}


def invalidate_tax_cache():
    """Clear the tax bracket cache. Call after updating TaxRule records."""
    _brackets_cache.clear()
    _brackets_cache_timestamps.clear()


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _get_brackets_and_relief(for_date=None):
    """
    Fetch tax brackets and personal relief from the database.
    Falls back to hardcoded defaults if no TaxRule exists.
    Caches result to avoid repeated DB queries during payroll calculation.

    Returns:
        (brackets: list of (Decimal, Decimal), personal_relief: Decimal)
    """
    cache_key = str(for_date) if for_date else 'default'
    import time
    now = time.time()
    if cache_key in _brackets_cache:
        cached_time = _brackets_cache_timestamps.get(cache_key, 0)
        if now - cached_time < _brackets_cache_ttl:
            return _brackets_cache[cache_key]
        # Cache expired — invalidate
        del _brackets_cache[cache_key]
        del _brackets_cache_timestamps[cache_key]

    try:
        from payroll_engine.models import TaxRule
        rule = TaxRule.get_active_rule(for_date)
        if rule and rule.brackets:
            brackets = []
            for b in rule.brackets:
                upper = Decimal('Infinity') if b['max'] is None else _D(b['max'])
                brackets.append((upper, _D(b['rate'])))
            result = (brackets, _D(rule.personal_relief))
            _brackets_cache[cache_key] = result
            _brackets_cache_timestamps[cache_key] = now
            return result
    except Exception:
        # Database not available (e.g., during tests without app context)
        pass

    result = (DEFAULT_BRACKETS, DEFAULT_PERSONAL_RELIEF)
    _brackets_cache[cache_key] = result
    _brackets_cache_timestamps[cache_key] = now
    return result


def calculate_tax(gross_salary, for_date=None) -> Decimal:
    """
    Calculate monthly income tax on taxable salary using progressive brackets.

    Note: gross_salary here should be the TAXABLE amount (after pension deduction).
    The deduction order (pension before tax) is enforced by the calling code.

    Args:
        gross_salary: Monthly taxable salary in ETB (must be >= 0)
        for_date: Optional date for rule versioning (YYYY-MM-DD string or date object)

    Returns:
        Tax amount in ETB (minimum 0), as Decimal
    """
    gross_salary = _D(gross_salary)
    if gross_salary <= 0:
        return Decimal('0')

    brackets, personal_relief = _get_brackets_and_relief(for_date)

    tax = Decimal('0')
    previous_bound = Decimal('0')

    for upper_bound, rate in brackets:
        if gross_salary <= previous_bound:
            break
        taxable_in_bracket = min(gross_salary, upper_bound) - previous_bound
        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate
        previous_bound = upper_bound

    # Apply personal relief
    tax = max(Decimal('0'), tax - personal_relief)
    return tax.quantize(Q, rounding=ROUND_HALF_UP)


def calculate_tax_breakdown(gross_salary, for_date=None) -> dict:
    """
    Calculate tax with full bracket-by-bracket breakdown.

    Args:
        gross_salary: Monthly taxable salary in ETB (after pension deduction)
        for_date: Optional date for rule versioning

    Returns:
        Dict with:
            total_tax: Decimal
            personal_relief: Decimal
            gross_tax: Decimal
            brackets: list of dicts
    """
    gross_salary = _D(gross_salary)
    if gross_salary <= 0:
        return {
            'total_tax': Decimal('0'),
            'personal_relief': Decimal('0'),
            'gross_tax': Decimal('0'),
            'brackets': [],
        }

    brackets_config, personal_relief = _get_brackets_and_relief(for_date)

    bracket_details = []
    tax = Decimal('0')
    previous_bound = Decimal('0')

    for upper_bound, rate in brackets_config:
        if gross_salary <= previous_bound:
            break
        taxable_in_bracket = min(gross_salary, upper_bound) - previous_bound
        bracket_tax = (taxable_in_bracket * rate).quantize(Q, rounding=ROUND_HALF_UP) if taxable_in_bracket > 0 else Decimal('0')
        tax += bracket_tax

        upper_display = upper_bound if upper_bound != Decimal('Infinity') else None
        bracket_details.append({
            'lower': previous_bound,
            'upper': upper_display,
            'rate': rate,
            'rate_pct': int(rate * 100),
            'taxable_amount': taxable_in_bracket.quantize(Q, rounding=ROUND_HALF_UP),
            'bracket_tax': bracket_tax,
        })
        previous_bound = upper_bound

    gross_tax = tax.quantize(Q, rounding=ROUND_HALF_UP)
    total_tax = max(Decimal('0'), tax - personal_relief).quantize(Q, rounding=ROUND_HALF_UP)

    return {
        'total_tax': total_tax,
        'personal_relief': personal_relief,
        'gross_tax': gross_tax,
        'brackets': bracket_details,
    }


def explain_tax_amharic(gross_salary, for_date=None) -> str:
    """
    Generate a bilingual (Amharic + English) explanation of the tax calculation.

    Args:
        gross_salary: Monthly taxable salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Multi-line string with bracket-by-bracket breakdown
    """
    gross_salary = _D(gross_salary)
    if gross_salary <= 0:
        return "ምንም ገቢ የለም / No income — no tax."

    brackets, personal_relief = _get_brackets_and_relief(for_date)

    lines = [
        f"ጠቅላይ ወርሃዊ ደመወዝ / Monthly Gross: ETB {gross_salary:,.2f}",
        "=" * 50,
        "የታክስ ሥሌት / Tax Bracket Breakdown:",
        "-" * 50,
    ]

    tax = Decimal('0')
    previous_bound = Decimal('0')

    for upper_bound, rate in brackets:
        if gross_salary <= previous_bound:
            break
        taxable = min(gross_salary, upper_bound) - previous_bound
        if taxable > 0:
            bracket_tax = taxable * rate
            tax += bracket_tax
            upper_display = f"{upper_bound:,.0f}" if upper_bound != Decimal('Infinity') else "∞"
            lines.append(
                f"  ETB {previous_bound:,.0f} – {upper_display}: "
                f"{rate*100:.0f}% × ETB {taxable:,.2f} = ETB {bracket_tax:,.2f}"
            )
        previous_bound = upper_bound

    lines.append("-" * 50)
    lines.append(f"  ጠቅላይ ታክስ ከነፃ እረፍት / Gross Tax: ETB {tax:,.2f}")
    lines.append(f"  የግል ነፃ እረፍት / Personal Relief: -ETB {personal_relief:,.2f}")
    net_tax = max(Decimal('0'), tax - personal_relief)
    lines.append(f"  የሚከፈል ታክስ / Tax Due: ETB {net_tax:,.2f}")
    lines.append("=" * 50)

    effective_rate = (net_tax / gross_salary * 100) if gross_salary > 0 else Decimal('0')
    lines.append(
        f"ውጤታዊ ታክስ መጠን / Effective Tax Rate: {effective_rate:.1f}%"
    )

    return "\n".join(lines)
