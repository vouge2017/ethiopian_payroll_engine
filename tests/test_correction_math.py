"""Correction arithmetic uses frozen full-period facts, never an isolated payment."""

from datetime import date
from decimal import Decimal

import pytest

from payroll_engine.services.adjustment_service import calculate_adjustment
from payroll_engine.services.correction_context import freeze_context, frozen_tax, money


def context():
    return freeze_context(date(2026, 9, 30), employee_id='SYNTHETIC', name='Synthetic', bank='1000123456789')


def test_retained_period_tax_delta():
    retained = context()
    result = calculate_adjustment(
        Decimal('10000'),
        Decimal('1475'),
        Decimal('700'),
        Decimal('7825'),
        Decimal('2000'),
        taxable_income=Decimal('9300'),
        tax_context=retained,
    )
    assert result['adjustment_tax'] == Decimal('565.00')
    assert result['adjustment_net'] == Decimal('1435.00')
    assert result['new_total_net'] == Decimal('9260.00')
    assert result['adjustment_pension'] == 0


@pytest.mark.parametrize(
    'value', ['NaN', 'sNaN', 'Infinity', '-Infinity', 'nonsense', '0', '-1', '1.001', '10000000000']
)
def test_invalid_money_rejected(value):
    with pytest.raises(ValueError):
        money(value, positive=True)


@pytest.mark.parametrize('mode', ['net_override', 'deduction', 'unknown'])
def test_unsupported_treatment_rejected(mode):
    with pytest.raises(ValueError, match='policy review'):
        calculate_adjustment(10000, 1475, 700, 7825, 2000, mode, taxable_income=9300, tax_context=context())


def test_missing_or_non_reconciling_history_rejected():
    with pytest.raises(ValueError, match='frozen calculation context'):
        frozen_tax(9300, None)
    with pytest.raises(ValueError, match='reconcile'):
        calculate_adjustment(10000, 1, 700, 7825, 2000, taxable_income=9300, tax_context=context())
