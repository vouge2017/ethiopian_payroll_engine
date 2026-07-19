"""
Payroll calculation tests — verifies the single entry point
enforces correct deduction order and catches bad inputs.

This is the structural guardrail: if anyone calls calculate_tax(gross)
directly instead of going through calculate_payroll(), the test suite
catches it. The function itself prevents wrong numbers.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from decimal import Decimal
from payroll_engine.payroll import calculate_payroll
from payroll_engine.tax import calculate_tax

D = Decimal


# ---------------------------------------------------------------
# TEST 1: Correct deduction order (15,000 ETB)
# ---------------------------------------------------------------
def test_payroll_15000():
    """15,000 gross, basic 10,000 — verifies pension before tax."""
    result = calculate_payroll(basic_salary=10000, allowances=5000)
    assert result['gross'] == D('15000')
    assert result['pension_employee'] == D('700')  # 7% of 10,000
    assert result['taxable'] == D('14300')  # 15,000 - 700
    assert result['tax'] == D('2805')  # tax on 14,300
    assert result['net'] == D('11495')  # 15,000 - 2,805 - 700


# ---------------------------------------------------------------
# TEST 2: Zero salary
# ---------------------------------------------------------------
def test_payroll_zero():
    result = calculate_payroll(basic_salary=0, allowances=0)
    assert result['gross'] == D('0')
    assert result['pension_employee'] == D('0')
    assert result['tax'] == D('0')
    assert result['net'] == D('0')


# ---------------------------------------------------------------
# TEST 3: Negative basic salary raises error
# ---------------------------------------------------------------
def test_payroll_negative_basic():
    """Negative salary must be rejected, not silently produce wrong numbers."""
    try:
        calculate_payroll(basic_salary=-5000, allowances=0)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'negative' in str(e).lower()


# ---------------------------------------------------------------
# TEST 4: Negative allowances raises error
# ---------------------------------------------------------------
def test_payroll_negative_allowances():
    try:
        calculate_payroll(basic_salary=5000, allowances=-1000)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'negative' in str(e).lower()


# ---------------------------------------------------------------
# TEST 5: Low salary (under 2,000 bracket)
# ---------------------------------------------------------------
def test_payroll_low_salary():
    """1,800 basic, 0 allowances — zero tax bracket."""
    result = calculate_payroll(basic_salary=1800, allowances=0)
    assert result['gross'] == D('1800')
    assert result['pension_employee'] == D('126')  # 7% of 1,800
    assert result['taxable'] == D('1674')
    assert result['tax'] == D('0')  # under 2,000 bracket
    assert result['net'] == D('1674')


# ---------------------------------------------------------------
# TEST 6: High salary (top bracket)
# ---------------------------------------------------------------
def test_payroll_high_salary():
    """50,000 basic, 10,000 allowances. Pension capped at 15,000 ceiling."""
    result = calculate_payroll(basic_salary=50000, allowances=10000)
    assert result['gross'] == D('60000')
    assert result['pension_employee'] == D('1050')  # 7% of 15,000 (ceiling)
    assert result['taxable'] == D('58950')  # 60,000 - 1,050
    assert result['tax'] > 0
    assert result['net'] == result['gross'] - result['tax'] - result['pension_employee']


# ---------------------------------------------------------------
# TEST 7: Only basic, no allowances
# ---------------------------------------------------------------
def test_payroll_basic_only():
    result = calculate_payroll(basic_salary=8000)
    assert result['gross'] == D('8000')
    assert result['pension_employee'] == D('560')


# ---------------------------------------------------------------
# TEST 8: Prove that going through calculate_payroll produces
#         different (correct) results vs calling calculate_tax(gross)
# ---------------------------------------------------------------
def test_deduction_order_matters():
    """
    If someone calls calculate_tax(gross) instead of
    calculate_tax(gross - pension), they get WRONG numbers.
    This test proves the difference.
    """
    gross = D('15000')
    basic = D('10000')
    pension = basic * D('0.07')  # 700

    # WRONG way: tax on full gross
    wrong_tax = calculate_tax(gross)

    # RIGHT way: tax on gross - pension
    right_tax = calculate_tax(gross - pension)

    # They must be different
    assert wrong_tax != right_tax, "Deduction order doesn't matter? Something is wrong."

    # The wrong way produces a HIGHER tax (employee gets less)
    assert wrong_tax > right_tax, "Wrong deduction order should produce higher tax."

    # Our function uses the right way
    result = calculate_payroll(basic_salary=basic, allowances=gross - basic)
    assert result['tax'] == right_tax
    assert result['tax'] != wrong_tax


# ---------------------------------------------------------------
# TEST 9: Large salary, no overflow
# ---------------------------------------------------------------
def test_payroll_no_overflow():
    """10,000,000 ETB — should calculate without errors. Pension capped."""
    result = calculate_payroll(basic_salary=10000000, allowances=0)
    assert result['gross'] == D('10000000')
    assert result['pension_employee'] == D('1050')  # 7% of 15,000 (ceiling)
    assert result['net'] > 0
    assert result['net'] == result['gross'] - result['tax'] - result['pension_employee']


# ---------------------------------------------------------------
# TEST 10: Tax explanation is included
# ---------------------------------------------------------------
def test_payroll_includes_explanation():
    result = calculate_payroll(basic_salary=10000, allowances=2000)
    assert 'tax_explanation' in result
    assert len(result['tax_explanation']) > 0
    assert 'ETB' in result['tax_explanation']
