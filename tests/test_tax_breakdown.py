"""
Tax breakdown tests — verifies bracket-by-bracket calculation
and that the breakdown total matches the tax amount.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.tax import calculate_tax, calculate_tax_breakdown
from decimal import Decimal


def test_breakdown_matches_total():
    """Breakdown total must match calculate_tax output."""
    for taxable in [0, 1000, 2000, 2001, 5000, 7000, 10000, 11300, 14000, 16950, 20000]:
        tax = calculate_tax(taxable)
        bd = calculate_tax_breakdown(taxable)
        assert bd['total_tax'] == tax, \
            f"Breakdown {bd['total_tax']} != tax {tax} on {taxable}"


def test_breakdown_zero():
    """Zero income returns empty brackets."""
    bd = calculate_tax_breakdown(0)
    assert bd['total_tax'] == 0.0
    assert bd['brackets'] == []


def test_breakdown_negative():
    """Negative income returns empty brackets."""
    bd = calculate_tax_breakdown(-1000)
    assert bd['total_tax'] == 0.0
    assert bd['brackets'] == []


def test_breakdown_first_bracket():
    """Income in first bracket (0%) shows one bracket."""
    bd = calculate_tax_breakdown(1500)
    assert len(bd['brackets']) == 1
    assert bd['brackets'][0]['rate_pct'] == 0
    assert bd['brackets'][0]['bracket_tax'] == 0.0


def test_breakdown_two_brackets():
    """Income crossing into second bracket shows two brackets."""
    bd = calculate_tax_breakdown(3000)
    assert len(bd['brackets']) == 2
    assert bd['brackets'][0]['rate_pct'] == 0
    assert bd['brackets'][1]['rate_pct'] == 15
    assert bd["brackets"][1]["bracket_tax"] == Decimal("150")  # 1000 * 0.15


def test_breakdown_all_brackets():
    """High income uses all brackets."""
    bd = calculate_tax_breakdown(20000)
    assert len(bd['brackets']) == 6  # 0%, 15%, 20%, 25%, 30%, 35%
    assert bd['brackets'][-1]['rate_pct'] == 35


def test_breakdown_personal_relief():
    """No personal relief in current law — total equals gross tax."""
    bd = calculate_tax_breakdown(5000)
    assert bd["personal_relief"] == Decimal("0")
    assert bd["total_tax"] == bd["gross_tax"]


def test_breakdown_bracket_amounts_sum():
    """Sum of bracket taxes equals gross tax (before relief)."""
    for taxable in [5000, 11300, 16950]:
        bd = calculate_tax_breakdown(taxable)
        bracket_sum = sum(b['bracket_tax'] for b in bd['brackets'])
        assert abs(bracket_sum - bd["gross_tax"]) < Decimal("0.01"), \
            f"Bracket sum {bracket_sum} != gross_tax {bd['gross_tax']} on {taxable}"


def test_dawit_taxable_11300():
    """Dawit's tax: 11300 taxable → 2040 total (no personal relief)."""
    bd = calculate_tax_breakdown(11300)
    assert bd['total_tax'] == 2040.0
    assert bd["personal_relief"] == Decimal("0")
    assert len(bd['brackets']) == 5


def test_hana_taxable_5150():
    """Hana's tax: 5150 taxable → 530 total (no personal relief)."""
    bd = calculate_tax_breakdown(5150)
    assert bd['total_tax'] == 530.0
    assert len(bd['brackets']) == 3


def test_kebede_taxable_16950():
    """Kebede's tax: 16950 taxable → 3882.50 total (no personal relief)."""
    bd = calculate_tax_breakdown(16950)
    assert bd['total_tax'] == 3882.5
    assert len(bd['brackets']) == 6
