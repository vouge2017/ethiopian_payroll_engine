"""
Ethiopian Income Tax Calculator (2025/2026)

Progressive tax brackets on monthly gross salary (ETB):
    0 – 2,000     : 0%
    2,001 – 4,000 : 15%
    4,001 – 7,000 : 20%
    7,001 – 10,000: 25%
    10,001 – 14,000: 30%
    14,001+      : 35%

Relief: A personal relief of ETB 150 is deducted from tax (if tax > 0).
"""

from typing import List, Tuple

# (upper_bound, rate) — upper_bound of None means "infinity"
BRACKETS: List[Tuple[float, float]] = [
    (2000.0, 0.00),
    (4000.0, 0.15),
    (7000.0, 0.20),
    (10000.0, 0.25),
    (14000.0, 0.30),
    (float('inf'), 0.35),
]

PERSONAL_RELIEF = 150.0  # ETB monthly personal relief


def calculate_tax(gross_salary: float) -> float:
    """
    Calculate monthly income tax on gross salary using progressive brackets.

    Args:
        gross_salary: Monthly gross salary in ETB (must be >= 0)

    Returns:
        Tax amount in ETB (minimum 0)
    """
    if gross_salary <= 0:
        return 0.0

    tax = 0.0
    previous_bound = 0.0

    for upper_bound, rate in BRACKETS:
        if gross_salary <= previous_bound:
            break
        taxable_in_bracket = min(gross_salary, upper_bound) - previous_bound
        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate
        previous_bound = upper_bound

    # Apply personal relief
    tax = max(0.0, tax - PERSONAL_RELIEF)
    return round(tax, 2)


def explain_tax_amharic(gross_salary: float) -> str:
    """
    Generate a bilingual (Amharic + English) explanation of the tax calculation.

    Args:
        gross_salary: Monthly gross salary in ETB

    Returns:
        Multi-line string with bracket-by-bracket breakdown
    """
    if gross_salary <= 0:
        return "ምንም ገቢ የለም / No income — no tax."

    lines = [
        f"ጠቅላይ ወርሃዊ ደመወዝ / Monthly Gross: ETB {gross_salary:,.2f}",
        "=" * 50,
        "የታክስ ሥሌት / Tax Bracket Breakdown:",
        "-" * 50,
    ]

    tax = 0.0
    previous_bound = 0.0

    for upper_bound, rate in BRACKETS:
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
    lines.append(f"  የግል ነፃ እረፍት / Personal Relief: -ETB {PERSONAL_RELIEF:,.2f}")
    net_tax = max(0.0, tax - PERSONAL_RELIEF)
    lines.append(f"  የሚከፈል ታክስ / Tax Due: ETB {net_tax:,.2f}")
    lines.append("=" * 50)

    effective_rate = (net_tax / gross_salary * 100) if gross_salary > 0 else 0
    lines.append(
        f"ውጤታዊ ታክስ መጠን / Effective Tax Rate: {effective_rate:.1f}%"
    )

    return "\n".join(lines)
