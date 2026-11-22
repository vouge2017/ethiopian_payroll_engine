from datetime import date
from decimal import Decimal

import pytest


@pytest.fixture
def app(tmp_path):
    from payroll_engine import create_app, db

    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{tmp_path / "issue79.db"}',
        WTF_CSRF_ENABLED=False,
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        from sqlalchemy import inspect

        assert inspect(db.engine).has_table('tax_rule')
        yield app
        db.session.remove()
        db.drop_all()


def test_seeded_2025_overtime_and_leave_values():
    from seed_tax_rules import RULES_2025

    assert RULES_2025['overtime']['rates'] == {
        'day': 1.50,
        'night': 1.75,
        'holiday': 2.00,
        'rest_day_holiday': 2.50,
    }
    assert RULES_2025['leave']['annual_base'] == 16


def test_overtime_key_meanings_are_pinned():
    from payroll_engine.overtime import get_overtime_type_label

    assert get_overtime_type_label('day') == 'Regular Day (1.50x)'
    assert get_overtime_type_label('night') == 'Night / 10pm-6am (1.75x)'
    assert get_overtime_type_label('holiday') == 'Weekly Rest Day (2.00x)'
    assert get_overtime_type_label('rest_day_holiday') == 'Public Holiday (2.50x)'


def test_seeded_values_match_code_defaults():
    from payroll_engine.leave import (
        DEFAULT_ANNUAL_BASE,
        DEFAULT_ANNUAL_INCREMENT,
        DEFAULT_ANNUAL_MAX,
        DEFAULT_MATERNITY_DAYS,
        DEFAULT_PATERNITY_DAYS,
        DEFAULT_SICK_MAX_DAYS,
        DEFAULT_SICK_TIER_1_DAYS,
        DEFAULT_SICK_TIER_2_DAYS,
    )
    from payroll_engine.overtime import DEFAULT_OVERTIME_RATES
    from seed_tax_rules import RULES_2025

    for key, default in DEFAULT_OVERTIME_RATES.items():
        assert Decimal(str(RULES_2025['overtime']['rates'][key])) == default

    leave_seed = RULES_2025['leave']
    shared_leave_defaults = {
        'annual_base': DEFAULT_ANNUAL_BASE,
        'annual_increment': DEFAULT_ANNUAL_INCREMENT,
        'annual_max': DEFAULT_ANNUAL_MAX,
        'sick_max_days': DEFAULT_SICK_MAX_DAYS,
        'sick_tier_1_days': DEFAULT_SICK_TIER_1_DAYS,
        'sick_tier_2_days': DEFAULT_SICK_TIER_2_DAYS,
        'maternity_days': DEFAULT_MATERNITY_DAYS,
        'paternity_days': DEFAULT_PATERNITY_DAYS,
    }
    for key, default in shared_leave_defaults.items():
        assert leave_seed[key] == default

    # special_days is intentionally excluded pending issue #84.
    assert 'special_days' in leave_seed


@pytest.mark.parametrize(
    ('overtime_type', 'old_pay', 'fixed_pay'),
    [
        ('day', Decimal('500.00'), Decimal('600.00')),
        ('night', Decimal('600.00'), Decimal('700.00')),
    ],
)
def test_money_before_and_after_overtime(overtime_type, old_pay, fixed_pay):
    from payroll_engine.overtime import calculate_hourly_rate

    hourly = calculate_hourly_rate(Decimal('20800'))
    assert hourly == Decimal('100.00')

    old_rate = Decimal('1.25') if overtime_type == 'day' else Decimal('1.50')
    fixed_rate = Decimal('1.50') if overtime_type == 'day' else Decimal('1.75')
    assert (hourly * Decimal('4') * old_rate).quantize(Decimal('0.01')) == old_pay
    assert (hourly * Decimal('4') * fixed_rate).quantize(Decimal('0.01')) == fixed_pay


def test_repair_existing_row_is_idempotent(app, monkeypatch):
    from payroll_engine import db
    from payroll_engine.models import TaxRule
    from repair_2025_v1_rules import repair_2025_v1_rules
    from seed_tax_rules import RULES_2025

    old_rules = {
        **RULES_2025,
        'overtime': {
            **RULES_2025['overtime'],
            'rates': {'day': 1.25, 'night': 1.50, 'holiday': 2.00, 'rest_day_holiday': 2.50},
        },
        'leave': {**RULES_2025['leave'], 'annual_base': 14},
    }
    row = TaxRule(
        version_name='2025-v1',
        effective_date=date(2025, 7, 7),
        rules_json=old_rules,
        status='active',
    )
    db.session.add(row)
    db.session.commit()

    invalidated = []
    monkeypatch.setattr('payroll_engine.overtime.invalidate_overtime_cache', lambda: invalidated.append('overtime'))
    monkeypatch.setattr('payroll_engine.leave.invalidate_leave_cache', lambda: invalidated.append('leave'))

    changed = repair_2025_v1_rules()
    assert changed is True
    assert invalidated == ['overtime', 'leave']
    assert row.rules_json['overtime']['rates']['day'] == 1.50
    assert row.rules_json['overtime']['rates']['night'] == 1.75
    assert row.rules_json['leave']['annual_base'] == 16

    invalidated.clear()
    changed = repair_2025_v1_rules()
    assert changed is False
    assert invalidated == []


def test_repair_does_nothing_when_row_is_absent(app):
    from repair_2025_v1_rules import repair_2025_v1_rules

    assert repair_2025_v1_rules() is False


def test_repaired_row_matches_fresh_seed_values(app):
    from payroll_engine import db
    from payroll_engine.models import TaxRule
    from repair_2025_v1_rules import repair_2025_v1_rules
    from seed_tax_rules import RULES_2025

    old_rules = {
        **RULES_2025,
        'overtime': {
            **RULES_2025['overtime'],
            'rates': {'day': 1.25, 'night': 1.50, 'holiday': 2.00, 'rest_day_holiday': 2.50},
        },
        'leave': {**RULES_2025['leave'], 'annual_base': 14},
    }
    old_row = TaxRule(
        version_name='2025-v1',
        effective_date=date(2025, 7, 7),
        rules_json=old_rules,
        status='active',
    )
    db.session.add(old_row)
    db.session.commit()
    repair_2025_v1_rules()

    fresh_row = TaxRule(
        version_name='2025-v1-fresh',
        effective_date=date(2025, 7, 7),
        rules_json=RULES_2025,
        status='active',
    )
    db.session.add(fresh_row)
    db.session.commit()

    assert old_row.rules_json['overtime']['rates'] == fresh_row.rules_json['overtime']['rates']
    assert old_row.rules_json['leave']['annual_base'] == fresh_row.rules_json['leave']['annual_base']


def test_paye_pension_regression_guard(app):
    from helpers import seed_synthetic_payroll_rule

    from payroll_engine.payroll import calculate_payroll

    with app.app_context():
        seed_synthetic_payroll_rule()
        result = calculate_payroll(basic_salary=Decimal('10000'), allowances=Decimal('0'))

    assert result['pension_employee'] == Decimal('700')
    assert result['pension_employer'] == Decimal('1100')
    assert result['tax'] == Decimal('1650')
    assert result['net'] == Decimal('7650')
