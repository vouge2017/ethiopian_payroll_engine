"""
Payroll calculation tests — verifies the single entry point
enforces correct deduction order and catches bad inputs.

This is the structural guardrail: if anyone calls calculate_tax(gross)
directly instead of going through calculate_payroll(), the test suite
catches it. The function itself prevents wrong numbers.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date
from decimal import Decimal

from payroll_engine.payroll import calculate_payroll
from payroll_engine.tax import calculate_tax

D = Decimal


# ---------------------------------------------------------------
# TEST 1: Correct deduction order (15,000 ETB)
# ---------------------------------------------------------------
def test_payroll_15000():
    """15,000 gross, basic 10,000 — PAYE on gross, pension not deducted first (RC-38000-01)."""
    result = calculate_payroll(basic_salary=10000, allowances=5000)
    assert result['gross'] == D('15000')
    assert result['pension_employee'] == D('700')  # 7% of 10,000
    assert result['taxable'] == D('15000')  # gross; pension does not reduce taxable income
    # tax on 15,000: 300 + 600 + 750 + 1,200 + 1,000 × 35% = 3,200 (no personal relief)
    assert result['tax'] == D('3200')
    assert result['net'] == D('11100')  # 15,000 - 3,200 - 700


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
        raise AssertionError('Should have raised ValueError')
    except ValueError as e:
        assert 'negative' in str(e).lower()


# ---------------------------------------------------------------
# TEST 4: Negative allowances raises error
# ---------------------------------------------------------------
def test_payroll_negative_allowances():
    try:
        calculate_payroll(basic_salary=5000, allowances=-1000)
        raise AssertionError('Should have raised ValueError')
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
    assert result['taxable'] == D('1800')  # gross (RC-38000-01)
    assert result['tax'] == D('0')  # under 2,000 bracket
    assert result['net'] == D('1674')


# ---------------------------------------------------------------
# TEST 6: High salary (top bracket)
# ---------------------------------------------------------------
def test_payroll_high_salary():
    """50,000 basic, 10,000 allowances. No pension ceiling in Ethiopian law."""
    result = calculate_payroll(basic_salary=50000, allowances=10000)
    assert result['gross'] == D('60000')
    assert result['pension_employee'] == D('3500')  # 7% of 50,000 (no ceiling)
    assert result['taxable'] == D('60000')  # gross; pension does not reduce it (RC-38000-01)
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
    PAYE is on gross taxable income (RC-38000-01, PLAN.md R1). Calling
    calculate_tax(gross - pension) — the legacy pension-first rule — gives a
    LOWER tax and under-withholds. This test proves the difference.
    """
    gross = D('15000')
    basic = D('10000')
    pension = basic * D('0.07')  # 700

    # WRONG way (legacy rule): tax on gross - pension
    wrong_tax = calculate_tax(gross - pension)

    # RIGHT way: tax on gross taxable income
    right_tax = calculate_tax(gross)

    # They must be different
    assert wrong_tax != right_tax, "Deduction order doesn't matter? Something is wrong."

    # The legacy way under-withholds tax
    assert wrong_tax < right_tax, 'Pension-first should produce lower (under-withheld) tax.'

    # Our function uses the right way
    result = calculate_payroll(basic_salary=basic, allowances=gross - basic)
    assert result['tax'] == right_tax
    assert result['tax'] != wrong_tax


# ---------------------------------------------------------------
# TEST 9: Large salary, no overflow
# ---------------------------------------------------------------
def test_payroll_no_overflow():
    """10,000,000 ETB — should calculate without errors. No pension ceiling."""
    result = calculate_payroll(basic_salary=10000000, allowances=0)
    assert result['gross'] == D('10000000')
    assert result['pension_employee'] == D('700000')  # 7% of 10,000,000 (no ceiling)
    assert result['net'] > 0
    assert result['net'] == result['gross'] - result['tax'] - result['pension_employee']


def test_no_pension_ceiling_by_default():
    """Ethiopian law has no pension ceiling — contributions on full salary."""
    from payroll_engine.pension import employee_pension, employer_pension

    emp = employee_pension(D('25000'))
    empr = employer_pension(D('25000'))
    assert emp == D('1750'), f'Employee pension should be 1750 (7% of 25000), got {emp}'
    assert empr == D('2750'), f'Employer pension should be 2750 (11% of 25000), got {empr}'

    result = calculate_payroll(basic_salary=25000, allowances=5000)
    assert result['pension_employee'] == D('1750')
    assert result['pension_employer'] == D('2750')
    # Taxable = gross = 30,000 (pension does not reduce it, RC-38000-01)
    assert result['taxable'] == D('30000')


def test_pension_ceiling_when_configured():
    """If a ceiling is set in TaxRule, pension is capped at that amount."""
    from payroll_engine import create_app, db
    from payroll_engine.models import TaxRule
    from payroll_engine.pension import employee_pension, employer_pension, invalidate_pension_cache

    app = create_app()
    with app.app_context():
        db.create_all()

        # Create a TaxRule with a 15,000 ceiling
        rule = TaxRule(
            version_name='ceiling-test',
            effective_date=date(2020, 1, 1),
            status='active',
            rules_json={
                'brackets': [{'min': 0, 'max': None, 'rate': 0.10}],
                'personal_relief': 0,
                'pension': {
                    'employee_rate': 0.07,
                    'employer_rate': 0.11,
                    'ceiling': 15000,
                },
            },
        )
        db.session.add(rule)
        db.session.commit()
        invalidate_pension_cache()

        try:
            emp = employee_pension(D('25000'))
            empr = employer_pension(D('25000'))
            assert emp == D('1050'), f'With 15k ceiling, employee pension should be 1050, got {emp}'
            assert empr == D('1650'), f'With 15k ceiling, employer pension should be 1650, got {empr}'

            # Below the ceiling — no capping
            emp_low = employee_pension(D('10000'))
            assert emp_low == D('700'), f'Below ceiling, pension should be 700, got {emp_low}'
        finally:
            db.session.delete(rule)
            db.session.commit()
            invalidate_pension_cache()


# ---------------------------------------------------------------
# TEST 10: Tax explanation is included
# ---------------------------------------------------------------
def test_payroll_includes_explanation():
    result = calculate_payroll(basic_salary=10000, allowances=2000)
    assert 'tax_explanation' in result
    assert len(result['tax_explanation']) > 0
    assert 'ETB' in result['tax_explanation']
