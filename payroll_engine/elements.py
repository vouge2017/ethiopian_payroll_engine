"""
Element Schema — Jurisdiction-Agnostic Payroll Calculation Core

Every payroll component is a configurable element stored in the database.
This allows:
- Ethiopia, Rwanda, Kenya to share the same code path
- Tax brackets to change without code changes
- New pay components to be added by admin, not developer
- Retroactive corrections via effective-dating

Element lifecycle:
1. Admin defines element (name, country, classification, calc_type)
2. Admin configures element parameters (amount, rate, bracket table)
3. Element is assigned to employees (or company-wide)
4. Payroll run evaluates all active elements for each employee
5. Result is frozen in Payslip (immutable)
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ElementClassification(Enum):
    EARNING = "earning"
    PRE_TAX_DEDUCTION = "pre_tax_deduction"
    POST_TAX_DEDUCTION = "post_tax_deduction"
    EMPLOYER_LIABILITY = "employer_liability"
    INFO_ONLY = "info_only"


class CalcType(Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENT_OF_BASE = "percent_of_base"
    BRACKET_TABLE = "bracket_table"
    FORMULA_REF = "formula_ref"


# ─── Ethiopia Reference Implementation ────────────────────────────────────────
# These are the elements that exist in Ethiopia's payroll system.
# They serve as the reference implementation for the element schema.

ETHIOPIA_ELEMENTS = [
    {
        "name": "basic_salary",
        "country": "ET",
        "classification": ElementClassification.EARNING.value,
        "calc_type": CalcType.FIXED_AMOUNT.value,
        "description": "Monthly basic salary",
        "is_taxable": True,
        "is_pension_base": True,
        "display_order": 10,
    },
    {
        "name": "allowance",
        "country": "ET",
        "classification": ElementClassification.EARNING.value,
        "calc_type": CalcType.FIXED_AMOUNT.value,
        "description": "Monthly allowances (transport, housing, etc.)",
        "is_taxable": True,
        "is_pension_base": False,
        "display_order": 20,
    },
    {
        "name": "overtime_pay",
        "country": "ET",
        "classification": ElementClassification.EARNING.value,
        "calc_type": CalcType.FORMULA_REF.value,
        "description": "Overtime pay (calculated from overtime entries)",
        "is_taxable": True,
        "is_pension_base": False,
        "display_order": 30,
    },
    {
        "name": "employee_pension",
        "country": "ET",
        "classification": ElementClassification.PRE_TAX_DEDUCTION.value,
        "calc_type": CalcType.PERCENT_OF_BASE.value,
        "description": "Employee pension contribution (7% of basic salary)",
        "rate": Decimal("0.07"),
        "base_element": "basic_salary",
        "is_taxable": False,
        "is_pension_base": False,
        "display_order": 40,
    },
    {
        "name": "income_tax",
        "country": "ET",
        "classification": ElementClassification.PRE_TAX_DEDUCTION.value,
        "calc_type": CalcType.BRACKET_TABLE.value,
        "description": "Income tax (progressive brackets, Proclamation 1395/2025)",
        "bracket_table": [
            {"lower": Decimal("0"), "upper": Decimal("2000"), "rate": Decimal("0.00")},
            {"lower": Decimal("2000"), "upper": Decimal("4000"), "rate": Decimal("0.15")},
            {"lower": Decimal("4000"), "upper": Decimal("7000"), "rate": Decimal("0.20")},
            {"lower": Decimal("7000"), "upper": Decimal("10000"), "rate": Decimal("0.25")},
            {"lower": Decimal("10000"), "upper": Decimal("14000"), "rate": Decimal("0.30")},
            {"lower": Decimal("14000"), "upper": None, "rate": Decimal("0.35")},
        ],
        "personal_relief": Decimal("0"),
        "is_taxable": False,
        "is_pension_base": False,
        "display_order": 50,
    },
    {
        "name": "employer_pension",
        "country": "ET",
        "classification": ElementClassification.EMPLOYER_LIABILITY.value,
        "calc_type": CalcType.PERCENT_OF_BASE.value,
        "description": "Employer pension contribution (11% of basic salary)",
        "rate": Decimal("0.11"),
        "base_element": "basic_salary",
        "is_taxable": False,
        "is_pension_base": False,
        "display_order": 60,
    },
    {
        "name": "other_deduction",
        "country": "ET",
        "classification": ElementClassification.POST_TAX_DEDUCTION.value,
        "calc_type": CalcType.FIXED_AMOUNT.value,
        "description": "Other deductions (loans, advances, penalties)",
        "is_taxable": False,
        "is_pension_base": False,
        "display_order": 70,
    },
]


# ─── Calculation Engine ──────────────────────────────────────────────────────

Q = Decimal("0.01")


def _D(value) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal("0")


def calculate_fixed_amount(element: Dict, employee_values: Dict) -> Decimal:
    """Calculate a fixed-amount element.
    
    For earnings (basic_salary, allowance), the value comes from employee_values.
    For deductions with a fixed amount, the value comes from the element definition.
    """
    name = element.get("name", "")
    if name in employee_values:
        return _D(employee_values[name])
    return _D(element.get("amount", 0))


def calculate_percent_of_base(element: Dict, employee_values: Dict) -> Decimal:
    """Calculate percentage of another element's value."""
    base_name = element.get("base_element", "")
    base_value = _D(employee_values.get(base_name, 0))
    rate = _D(element.get("rate", 0))
    return (base_value * rate).quantize(Q, rounding=ROUND_HALF_UP)


def calculate_bracket_table(element: Dict, employee_values: Dict) -> Decimal:
    """Calculate using progressive bracket table (e.g., income tax)."""
    taxable_income = _D(employee_values.get("taxable_income", 0))
    if taxable_income <= 0:
        return Decimal("0")

    brackets = element.get("bracket_table", [])
    personal_relief = _D(element.get("personal_relief", 0))

    tax = Decimal("0")
    for bracket in brackets:
        lower = _D(bracket["lower"])
        upper = _D(bracket["upper"]) if bracket["upper"] is not None else None
        rate = _D(bracket["rate"])

        if taxable_income <= lower:
            break

        if upper is None:
            taxable_in_bracket = taxable_income - lower
        else:
            taxable_in_bracket = min(taxable_income, upper) - lower

        if taxable_in_bracket > 0:
            tax += taxable_in_bracket * rate

    tax = max(Decimal("0"), tax - personal_relief)
    return tax.quantize(Q, rounding=ROUND_HALF_UP)


def calculate_element(element: Dict, employee_values: Dict) -> Decimal:
    """Route to the correct calculation method based on calc_type."""
    calc_type = element.get("calc_type", "")

    if calc_type == CalcType.FIXED_AMOUNT.value:
        return calculate_fixed_amount(element, employee_values)
    elif calc_type == CalcType.PERCENT_OF_BASE.value:
        return calculate_percent_of_base(element, employee_values)
    elif calc_type == CalcType.BRACKET_TABLE.value:
        return calculate_bracket_table(element, employee_values)
    elif calc_type == CalcType.FORMULA_REF.value:
        # For now, return 0 — formula evaluation is a future enhancement
        return Decimal("0")
    else:
        return Decimal("0")


def calculate_payroll_with_elements(
    elements: List[Dict],
    employee_values: Dict,
    for_date: date = None,
) -> Dict:
    """
    Calculate complete payroll using the element-based engine.

    This is the single entry point for all payroll calculations.
    It enforces the deduction order:
        1. Calculate all earnings → gross
        2. Calculate pre-tax deductions (pension, tax) → taxable income, tax
        3. Calculate post-tax deductions → net pay
        4. Calculate employer liabilities (not on payslip)

    Args:
        elements: List of element definitions (from database or config)
        employee_values: Dict of employee-specific values (basic_salary, allowance, etc.)
        for_date: Optional date for rule versioning

    Returns:
        Dict with all calculated values and breakdown
    """
    result = {
        "gross": Decimal("0"),
        "taxable_income": Decimal("0"),
        "total_tax": Decimal("0"),
        "total_pre_tax_deductions": Decimal("0"),
        "total_post_tax_deductions": Decimal("0"),
        "total_employer_liability": Decimal("0"),
        "net_pay": Decimal("0"),
        "breakdown": [],
    }

    # Step 1: Calculate earnings
    for element in elements:
        if element.get("classification") == ElementClassification.EARNING.value:
            value = calculate_element(element, employee_values)
            result["gross"] += value
            result["breakdown"].append({
                "name": element["name"],
                "classification": element["classification"],
                "amount": value,
            })

    # Step 2: Calculate pre-tax deductions (pension first, then tax)
    # Pension is calculated on basic salary only
    pension_base = _D(employee_values.get("basic_salary", 0))
    pre_tax_total = Decimal("0")
    pension_total = Decimal("0")

    for element in elements:
        if element.get("classification") == ElementClassification.PRE_TAX_DEDUCTION.value:
            # For pension, use basic salary as base
            if element.get("base_element") == "basic_salary":
                temp_values = {**employee_values, "basic_salary": pension_base}
                value = calculate_element(element, temp_values)
                pension_total += value
            else:
                # For tax, use (gross - pension) as taxable income
                taxable_for_tax = result["gross"] - pension_total
                temp_values = {**employee_values, "taxable_income": taxable_for_tax}
                value = calculate_element(element, temp_values)

            pre_tax_total += value
            result["breakdown"].append({
                "name": element["name"],
                "classification": element["classification"],
                "amount": value,
            })

    result["total_pre_tax_deductions"] = pre_tax_total
    # Taxable income = gross - pension (the amount tax is calculated on)
    result["taxable_income"] = result["gross"] - pension_total

    # Step 3: Calculate post-tax deductions
    for element in elements:
        if element.get("classification") == ElementClassification.POST_TAX_DEDUCTION.value:
            value = calculate_element(element, employee_values)
            result["total_post_tax_deductions"] += value
            result["breakdown"].append({
                "name": element["name"],
                "classification": element["classification"],
                "amount": value,
            })

    # Step 4: Calculate employer liabilities
    for element in elements:
        if element.get("classification") == ElementClassification.EMPLOYER_LIABILITY.value:
            value = calculate_element(element, employee_values)
            result["total_employer_liability"] += value
            result["breakdown"].append({
                "name": element["name"],
                "classification": element["classification"],
                "amount": value,
            })

    # Final: Net pay
    result["net_pay"] = (
        result["gross"]
        - result["total_pre_tax_deductions"]
        - result["total_post_tax_deductions"]
    )

    return result


# ─── Verification ────────────────────────────────────────────────────────────

def test_element_engine_matches_existing():
    """
    Verify the element engine produces the same result as the existing
    calculate_payroll() function for the same inputs.
    """
    # Test case: basic_salary=8000, allowances=2000
    employee_values = {
        "basic_salary": Decimal("8000"),
        "allowance": Decimal("2000"),
        "overtime_pay": Decimal("0"),
        "other_deduction": Decimal("0"),
    }

    result = calculate_payroll_with_elements(ETHIOPIA_ELEMENTS, employee_values)

    # Expected (from manual calculation + existing tests):
    # Gross: 10,000
    # Employee pension: 560 (7% of 8000)
    # Taxable: 9,440
    # Tax: 1,360
    # Net: 8,080

    assert result["gross"] == Decimal("10000.00"), f"Gross: {result['gross']}"
    assert result["taxable_income"] == Decimal("9440.00"), f"Taxable: {result['taxable_income']}"
    assert result["total_pre_tax_deductions"] == Decimal("1920.00"), f"Pre-tax: {result['total_pre_tax_deductions']}"
    assert result["net_pay"] == Decimal("8080.00"), f"Net: {result['net_pay']}"
    assert result["total_employer_liability"] == Decimal("880.00"), f"Employer: {result['total_employer_liability']}"

    print("✓ Element engine matches existing calculation")
    print(f"  Gross: {result['gross']}")
    print(f"  Pre-tax deductions: {result['total_pre_tax_deductions']}")
    print(f"  Taxable income: {result['taxable_income']}")
    print(f"  Net pay: {result['net_pay']}")
    print(f"  Employer liability: {result['total_employer_liability']}")

    return True


if __name__ == "__main__":
    test_element_engine_matches_existing()
