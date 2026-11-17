"""
Ethiopian Income Tax Calculator (2025/2026)

Progressive tax brackets on monthly taxable salary (ETB):
    0 – 2,000     : 0%
    2,001 – 4,000 : 15%
    4,001 – 7,000 : 20%
    7,001 – 10,000: 25%
    10,001 – 14,000: 30%
    14,001+      : 35%

No personal relief — not provided under Proclamation 979/2016 or 1395/2025.
Article 10(3) of 979/2016 prohibits deductions from employment income.

Bracket schedule: Proclamation No. 1395/2025, Article 11 (Employment Income
Tax Rates). Supporting evidence for the article number and the exact table
text is documented in docs/PENSION_BEFORE_TAX_RC38000_01.md (external
scans + an independent legal summary); a reviewer who cannot obtain the
Federal Negarit Gazette should treat the article number as
"source to be confirmed" until matched against the official text.
The effective dates of individual amendment items are listed differently
across public sources (1–8 July 2025 vs 1 September 2025); effective-date
applicability is to be confirmed by the accountant.

The order in which the employee pension contribution enters the PAYE
taxable base is set by constants.PENSION_DEDUCTED_BEFORE_TAX (default False:
PAYE on gross taxable pay before the 7% pension, Income Tax Proc. 979/2016;
RC-38000-01 closed).

Rules are configured via the TaxRule database model; missing rules block calculation.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Quantizer for 2 decimal places
Q = Decimal('0.01')

# Default fallback brackets
# Source: Ethiopian Income Tax (Amendment) Proclamation No. 1395/2025,
# Article 11 (Employment Income Tax Rates). Evidence trail for the article
# number: docs/PENSION_BEFORE_TAX_RC38000_01.md
# https://lawethiopia.com/images/proc1395-2025.pdf
# Used only when no TaxRule exists in the database
DEFAULT_BRACKETS: list[tuple[Decimal, Decimal]] = [
    (Decimal('2000'), Decimal('0.00')),
    (Decimal('4000'), Decimal('0.15')),
    (Decimal('7000'), Decimal('0.20')),
    (Decimal('10000'), Decimal('0.25')),
    (Decimal('14000'), Decimal('0.30')),
    (Decimal('Infinity'), Decimal('0.35')),
]

DEFAULT_PERSONAL_RELIEF = Decimal('0')  # Removed — not in Proclamation 1395/2025

# Kept for compatibility with callers that invalidate old cache state.
_brackets_cache = {}
_brackets_cache_ttl = 300  # seconds
_brackets_cache_timestamps = {}


def invalidate_tax_cache():
    """Clear the tax bracket cache. Call after updating TaxRule records."""
    _brackets_cache.clear()
    _brackets_cache_timestamps.clear()


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal.

    Non-finite values (NaN, Infinity) raise ValueError: money must be finite.
    """
    if isinstance(value, Decimal):
        d = value
    else:
        try:
            d = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal('0')
    if not d.is_finite():
        raise ValueError(f'Money value must be finite, got: {d}')
    return d


def _get_brackets_and_relief(for_date=None):
    """
    Fetch tax brackets and personal relief from the database.
    Missing or invalid rules stop calculation.
    Reads the rule for every lookup so deletion and database failures are visible.

    Returns:
        (brackets: list of (Decimal, Decimal), personal_relief: Decimal)
    """
    from payroll_engine.rule_errors import MissingPayrollRuleError, active_rule

    rule = active_rule(for_date, 'tax')
    try:
        raw = rule.brackets
        if not isinstance(raw, list) or not raw:
            raise ValueError
        brackets = []
        previous = Decimal('0')
        for index, bracket in enumerate(raw):
            upper = Decimal('Infinity') if bracket['max'] is None else Decimal(str(bracket['max']))
            rate = Decimal(str(bracket['rate']))
            if upper.is_nan() or upper <= previous or not rate.is_finite() or not 0 <= rate <= 1:
                raise ValueError
            if upper.is_infinite() and index != len(raw) - 1:
                raise ValueError
            brackets.append((upper, rate))
            previous = upper
        if not previous.is_infinite():
            raise ValueError
        result = (brackets, _D(rule.personal_relief))
    except (TypeError, KeyError, ValueError, InvalidOperation, AttributeError) as exc:
        raise MissingPayrollRuleError(
            'The tax rule for the payroll date is incomplete or invalid. Fix the rule before continuing.'
        ) from exc
    return result


def calculate_tax(gross_salary, for_date=None) -> Decimal:
    """
    Calculate monthly income tax on taxable salary using progressive brackets.

    Note: gross_salary here should be the TAXABLE amount. Whether the 7%
    employee pension reduces taxable income is decided by
    constants.PENSION_DEDUCTED_BEFORE_TAX (RC-38000-01) and is applied by
    the calling code, not in this module.

    Args:
        gross_salary: Monthly taxable salary in ETB (must be >= 0)
        for_date: Optional date for rule versioning (YYYY-MM-DD string or date object)

    Returns:
        Tax amount in ETB (minimum 0), as Decimal
    """
    gross_salary = _D(gross_salary)
    if gross_salary <= 0:
        return Decimal('0')

    brackets, _personal_relief = _get_brackets_and_relief(for_date)

    tax = Decimal('0')
    previous_bound = Decimal('0')

    for upper_bound, rate in brackets:
        if gross_salary <= previous_bound:
            break
        taxable_in_bracket = min(gross_salary, upper_bound) - previous_bound
        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate
        previous_bound = upper_bound

    tax = tax.quantize(Q, rounding=ROUND_HALF_UP)
    return max(Decimal('0'), tax)


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

    brackets_config, _personal_relief = _get_brackets_and_relief(for_date)

    bracket_details = []
    tax = Decimal('0')
    previous_bound = Decimal('0')

    for upper_bound, rate in brackets_config:
        if gross_salary <= previous_bound:
            break
        taxable_in_bracket = min(gross_salary, upper_bound) - previous_bound
        bracket_tax = (
            (taxable_in_bracket * rate).quantize(Q, rounding=ROUND_HALF_UP) if taxable_in_bracket > 0 else Decimal('0')
        )
        tax += bracket_tax

        upper_display = upper_bound if upper_bound != Decimal('Infinity') else None
        bracket_details.append(
            {
                'lower': previous_bound,
                'upper': upper_display,
                'rate': rate,
                'rate_pct': int(rate * 100),
                'taxable_amount': taxable_in_bracket.quantize(Q, rounding=ROUND_HALF_UP),
                'bracket_tax': bracket_tax,
            }
        )
        previous_bound = upper_bound

    total_tax = tax.quantize(Q, rounding=ROUND_HALF_UP)

    return {
        'total_tax': total_tax,
        'personal_relief': Decimal('0'),  # Removed — not in Proclamation 1395/2025
        'gross_tax': total_tax,
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
        return 'ምንም ገቢ የለም / No income — no tax.'

    brackets, _personal_relief = _get_brackets_and_relief(for_date)

    lines = [
        f'ጠቅላላ ወርሃዊ ደመወዝ / Monthly Gross: ETB {gross_salary:,.2f}',
        '=' * 50,
        'የታክስ ሥሌት / Tax Bracket Breakdown:',
        '-' * 50,
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
            upper_display = f'{upper_bound:,.0f}' if upper_bound != Decimal('Infinity') else '∞'
            lines.append(
                f'  ETB {previous_bound:,.0f} – {upper_display}: '
                f'{rate * 100:.0f}% × ETB {taxable:,.2f} = ETB {bracket_tax:,.2f}'
            )
        previous_bound = upper_bound

    lines.append('-' * 50)
    lines.append(f'  የሚከፈል ታክስ / Tax Due: ETB {tax:,.2f}')
    lines.append('=' * 50)

    effective_rate = (tax / gross_salary * 100) if gross_salary > 0 else Decimal('0')
    lines.append(f'ውጤታዊ ታክስ መጠን / Effective Tax Rate: {effective_rate:.1f}%')

    return '\n'.join(lines)
