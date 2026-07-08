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

from typing import List, Tuple

# Default fallback brackets (Proclamation No. 1395/2025)
# Used only when no TaxRule exists in the database
DEFAULT_BRACKETS: List[Tuple[float, float]] = [
    (2000.0, 0.00),
    (4000.0, 0.15),
    (7000.0, 0.20),
    (10000.0, 0.25),
    (14000.0, 0.30),
    (float('inf'), 0.35),
]

DEFAULT_PERSONAL_RELIEF = 150.0  # ETB monthly personal relief


def _get_brackets_and_relief(for_date=None):
    """
    Fetch tax brackets and personal relief from the database.
    Falls back to hardcoded defaults if no TaxRule exists.

    Returns:
        (brackets: list of (upper_bound, rate), personal_relief: float)
    """
    try:
        from payroll_engine.models import TaxRule
        rule = TaxRule.get_active_rule(for_date)
        if rule and rule.brackets:
            brackets = []
            for b in rule.brackets:
                upper = b['max'] if b['max'] is not None else float('inf')
                brackets.append((float(upper), float(b['rate'])))
            return brackets, float(rule.personal_relief)
    except Exception:
        # Database not available (e.g., during tests without app context)
        pass

    return DEFAULT_BRACKETS, DEFAULT_PERSONAL_RELIEF


def calculate_tax(gross_salary: float, for_date=None) -> float:
    """
    Calculate monthly income tax on taxable salary using progressive brackets.

    Note: gross_salary here should be the TAXABLE amount (after pension deduction).
    The deduction order (pension before tax) is enforced by the calling code.

    Args:
        gross_salary: Monthly taxable salary in ETB (must be >= 0)
        for_date: Optional date for rule versioning (YYYY-MM-DD string or date object)

    Returns:
        Tax amount in ETB (minimum 0)
    """
    if gross_salary <= 0:
        return 0.0

    brackets, personal_relief = _get_brackets_and_relief(for_date)

    tax = 0.0
    previous_bound = 0.0

    for upper_bound, rate in brackets:
        if gross_salary <= previous_bound:
            break
        taxable_in_bracket = min(gross_salary, upper_bound) - previous_bound
        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate
        previous_bound = upper_bound

    # Apply personal relief
    tax = max(0.0, tax - personal_relief)
    return round(tax, 2)


def calculate_tax_breakdown(gross_salary: float, for_date=None) -> dict:
    """
    Calculate tax with full bracket-by-bracket breakdown.

    Args:
        gross_salary: Monthly taxable salary in ETB (after pension deduction)
        for_date: Optional date for rule versioning

    Returns:
        Dict with:
            total_tax: float
            personal_relief: float
            brackets: list of dicts with keys:
                lower, upper, rate, taxable_amount, bracket_tax
            gross_tax: tax before relief
    """
    if gross_salary <= 0:
        return {
            'total_tax': 0.0,
            'personal_relief': 0.0,
            'gross_tax': 0.0,
            'brackets': [],
        }

    brackets_config, personal_relief = _get_brackets_and_relief(for_date)

    bracket_details = []
    tax = 0.0
    previous_bound = 0.0

    for upper_bound, rate in brackets_config:
        if gross_salary <= previous_bound:
            break
        taxable_in_bracket = min(gross_salary, upper_bound) - previous_bound
        bracket_tax = round(taxable_in_bracket * rate, 2) if taxable_in_bracket > 0 else 0.0
        tax += bracket_tax

        upper_display = upper_bound if upper_bound != float('inf') else None
        bracket_details.append({
            'lower': previous_bound,
            'upper': upper_display,
            'rate': rate,
            'rate_pct': int(rate * 100),
            'taxable_amount': round(taxable_in_bracket, 2),
            'bracket_tax': bracket_tax,
        })
        previous_bound = upper_bound

    gross_tax = round(tax, 2)
    total_tax = round(max(0.0, tax - personal_relief), 2)

    return {
        'total_tax': total_tax,
        'personal_relief': personal_relief,
        'gross_tax': gross_tax,
        'brackets': bracket_details,
    }


def explain_tax_amharic(gross_salary: float, for_date=None) -> str:
    """
    Generate a bilingual (Amharic + English) explanation of the tax calculation.

    Args:
        gross_salary: Monthly taxable salary in ETB
        for_date: Optional date for rule versioning

    Returns:
        Multi-line string with bracket-by-bracket breakdown
    """
    if gross_salary <= 0:
        return "ምንም ገቢ የለም / No income — no tax."

    brackets, personal_relief = _get_brackets_and_relief(for_date)

    lines = [
        f"ጠቅላይ ወርሃዊ ደመወዝ / Monthly Gross: ETB {gross_salary:,.2f}",
        "=" * 50,
        "የታክስ ሥሌት / Tax Bracket Breakdown:",
        "-" * 50,
    ]

    tax = 0.0
    previous_bound = 0.0

    for upper_bound, rate in brackets:
        if gross_salary <= previous_bound:
            break
        taxable = min(gross_salary, upper_bound) - previous_bound
        if taxable > 0:
            bracket_tax = taxable * rate
            tax += bracket_tax
            upper_display = f"{upper_bound:,.0f}" if upper_bound != float('inf') else "∞"
            lines.append(
                f"  ETB {previous_bound:,.0f} – {upper_display}: "
                f"{rate*100:.0f}% × ETB {taxable:,.2f} = ETB {bracket_tax:,.2f}"
            )
        previous_bound = upper_bound

    lines.append("-" * 50)
    lines.append(f"  ጠቅላይ ታክስ ከነፃ እረፍት / Gross Tax: ETB {tax:,.2f}")
    lines.append(f"  የግል ነፃ እረፍት / Personal Relief: -ETB {personal_relief:,.2f}")
    net_tax = max(0.0, tax - personal_relief)
    lines.append(f"  የሚከፈል ታክስ / Tax Due: ETB {net_tax:,.2f}")
    lines.append("=" * 50)

    effective_rate = (net_tax / gross_salary * 100) if gross_salary > 0 else 0
    lines.append(
        f"ውጤታዊ ታክስ መጠን / Effective Tax Rate: {effective_rate:.1f}%"
    )

    return "\n".join(lines)
