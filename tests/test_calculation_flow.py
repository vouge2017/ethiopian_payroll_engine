"""Transparent calculation flow tests — verify the step-by-step breakdown."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from decimal import Decimal
from payroll_engine.payroll import calculate_payroll, generate_calculation_flow


def test_calc_flow_has_all_steps():
    """generate_calculation_flow returns all expected steps."""
    result = calculate_payroll(basic_salary=10000, allowances=2000)
    flow = generate_calculation_flow(result)

    assert 'steps' in flow
    assert 'effective_tax_rate' in flow
    assert 'summary' in flow

    labels = [s['label'] for s in flow['steps']]
    assert 'Gross Salary' in labels
    assert 'Employee Pension (7%)' in labels
    assert 'Taxable Income' in labels
    assert 'Income Tax' in labels
    assert 'Net Pay' in labels


def test_calc_flow_amounts_match_result():
    """Flow step amounts match the payroll result dict."""
    result = calculate_payroll(basic_salary=15000, allowances=3000)
    flow = generate_calculation_flow(result)

    step_map = {s['label']: s['amount'] for s in flow['steps']}
    assert step_map['Gross Salary'] == result['gross']
    assert step_map['Employee Pension (7%)'] == result['pension_employee']
    assert step_map['Taxable Income'] == result['taxable']
    assert step_map['Income Tax'] == result['tax']
    assert step_map['Net Pay'] == result['net']


def test_calc_flow_effective_tax_rate():
    """Effective tax rate is correctly computed."""
    result = calculate_payroll(basic_salary=10000, allowances=0)
    flow = generate_calculation_flow(result)

    # Tax on 10000 - 700 (pension) = 9300 taxable
    # Brackets: 2000*0 + 2000*0.15 + 3000*0.20 + 2300*0.25 = 0 + 300 + 600 + 575 = 1475
    # Relief: 150 → tax = 1325
    # Effective rate: 1325/10000 = 13.25%
    assert flow['effective_tax_rate'] == Decimal('13.25')


def test_calc_flow_summary_contains_amounts():
    """Summary line contains the key amounts."""
    result = calculate_payroll(basic_salary=8000, allowances=1000)
    flow = generate_calculation_flow(result)

    assert 'gross' in flow['summary'].lower() or str(result['gross']) in flow['summary']
    assert '7,330.00' in flow['summary']


def test_calc_flow_deduction_flags():
    """Deduction steps are flagged correctly."""
    result = calculate_payroll(basic_salary=10000, allowances=0)
    flow = generate_calculation_flow(result)

    pension_step = next(s for s in flow['steps'] if 'Pension' in s['label'])
    tax_step = next(s for s in flow['steps'] if 'Income Tax' in s['label'])
    net_step = next(s for s in flow['steps'] if 'Net' in s['label'])

    assert pension_step['is_deduction'] is True
    assert tax_step['is_deduction'] is True
    assert net_step['is_deduction'] is False
    assert net_step.get('is_final') is True


def test_calc_flow_zero_salary():
    """Flow handles zero salary gracefully."""
    result = calculate_payroll(basic_salary=0, allowances=0)
    flow = generate_calculation_flow(result)

    assert flow['effective_tax_rate'] == Decimal('0')
    assert len(flow['steps']) > 0


def test_calc_flow_high_salary():
    """Flow handles high salary (top tax bracket) correctly."""
    result = calculate_payroll(basic_salary=50000, allowances=10000)
    flow = generate_calculation_flow(result)

    # Should have all steps including exempt allowances (0 in this case)
    assert flow['steps'][-1]['is_final'] is True
    assert flow['effective_tax_rate'] > Decimal('20')  # High earner


def test_calc_flow_with_overtime():
    """Flow includes overtime in gross."""
    result = calculate_payroll(
        basic_salary=10000,
        allowances=0,
        overtime_entries=[{'hours': 10, 'type': 'day'}],
    )
    flow = generate_calculation_flow(result)

    gross_step = next(s for s in flow['steps'] if 'Gross' in s['label'])
    # Gross should be higher than basic due to overtime
    assert gross_step['amount'] > Decimal('10000')
