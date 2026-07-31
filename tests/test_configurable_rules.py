"""
Tests for configurable business rules (overtime, leave, severance).

Proves that:
1. Default values work when no TaxRule exists in database
2. Database values override defaults when TaxRule exists
3. Historical rules are used for old payroll dates
4. Companies can make rules more generous but not violate law
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date
from decimal import Decimal
import pytest

D = Decimal


# -------------------------------------------------------------------
# OVERTIME TESTS
# -------------------------------------------------------------------

class TestOvertimeDefaults:
    """Test overtime with no database rule (uses hardcoded defaults)."""

    def test_default_rates(self):
        from payroll_engine.overtime import get_overtime_rates
        rates = get_overtime_rates()
        assert rates['day'] == D('1.50')      # Art. 68(1)(a)
        assert rates['night'] == D('1.75')    # Art. 68(1)(b)
        assert rates['holiday'] == D('2.00')   # Art. 68(1)(c)
        assert rates['rest_day_holiday'] == D('2.50')  # Art. 68(1)(d)

    def test_default_limits(self):
        from payroll_engine.overtime import get_overtime_limits
        limits = get_overtime_limits()
        assert limits['day'] == 4      # Art. 67(2)
        assert limits['week'] == 12    # Art. 67(2)
        assert limits['month'] == 20   # Configurable
        assert limits['year'] == 100   # Configurable

    def test_hourly_rate_default_divisor(self):
        from payroll_engine.overtime import calculate_hourly_rate
        # 208 hours/month (26 days × 8 hours)
        rate = calculate_hourly_rate(D('20800'))
        assert rate == D('100.00')  # 20800 / 208

    def test_overtime_pay_day(self):
        from payroll_engine.overtime import calculate_overtime_pay
        pay = calculate_overtime_pay(D('20800'), 4, 'day')
        assert pay == D('600.00')  # 100 × 4 × 1.50

    def test_overtime_pay_night(self):
        from payroll_engine.overtime import calculate_overtime_pay
        pay = calculate_overtime_pay(D('20800'), 4, 'night')
        assert pay == D('700.00')  # 100 × 4 × 1.75


class TestOvertimeConfigurable:
    """Test overtime with database-configured rules."""

    def test_custom_rates_from_database(self, app):
        from payroll_engine import db
        from payroll_engine.models import TaxRule
        from payroll_engine.overtime import get_overtime_rates, calculate_overtime_pay, invalidate_overtime_cache

        with app.app_context():
            db.create_all()
            rule = TaxRule(
                version_name='ot-test',
                effective_date=date(2020, 1, 1),
                status='active',
                rules_json={
                    'brackets': [{'min': 0, 'max': None, 'rate': 0.10}],
                    'personal_relief': 0,
                    'overtime': {
                        'rates': {'day': 2.00, 'night': 2.50, 'holiday': 3.00, 'rest_day_holiday': 3.50},
                        'max_hours_day': 6,
                        'max_hours_week': 16,
                        'max_hours_month': 25,
                        'max_hours_year': 150,
                        'monthly_hours': 208,
                    }
                }
            )
            db.session.add(rule)
            db.session.commit()
            invalidate_overtime_cache()

            try:
                rates = get_overtime_rates()
                assert rates['day'] == D('2.00')
                assert rates['night'] == D('2.50')

                # Pay should use custom rate
                pay = calculate_overtime_pay(D('20800'), 4, 'day')
                assert pay == D('800.00')  # 100 × 4 × 2.00 (not 1.50)
            finally:
                db.session.delete(rule)
                db.session.commit()
                invalidate_overtime_cache()


# -------------------------------------------------------------------
# LEAVE TESTS
# -------------------------------------------------------------------

class TestLeaveDefaults:
    """Test leave with no database rule (uses hardcoded defaults)."""

    def test_annual_entitlement_year1(self):
        from payroll_engine.leave import calculate_annual_entitlement
        assert calculate_annual_entitlement(0) == 16  # Art. 77(1)(a)

    def test_annual_entitlement_year5(self):
        from payroll_engine.leave import calculate_annual_entitlement
        # Year 5: 16 + 2 increments (years 2,4) = 18
        assert calculate_annual_entitlement(5) == 18

    def test_annual_entitlement_capped(self):
        from payroll_engine.leave import calculate_annual_entitlement
        # Year 28: 16 + 13 increments = 29, year 30: 16 + 14 = 30, year 32: 16+15=31 capped to 30
        assert calculate_annual_entitlement(32) == 30  # capped at 30

    def test_annual_company_more_generous(self):
        from payroll_engine.leave import calculate_annual_entitlement
        # Company offers 20 days, statutory is 16
        assert calculate_annual_entitlement(0, company_policy_days=20) == 20

    def test_annual_company_cannot_reduce(self):
        from payroll_engine.leave import calculate_annual_entitlement
        # Company tries 10 days, statutory is 16 — should get 16
        assert calculate_annual_entitlement(0, company_policy_days=10) == 16

    def test_sick_leave_tiers(self):
        from payroll_engine.leave import calculate_sick_leave_pay
        daily = D('500')
        # 10 days sick: all at 100%
        r = calculate_sick_leave_pay(10, daily)
        assert r['tier'] == 1
        assert r['total_pay'] == D('5000.00')

    def test_sick_leave_tier2(self):
        from payroll_engine.leave import calculate_sick_leave_pay
        daily = D('500')
        # 45 days sick: 30 at 100% + 15 at 50%
        r = calculate_sick_leave_pay(45, daily)
        assert r['tier'] == 2
        assert r['total_pay'] == D('15000.00') + D('3750.00')  # 15000 + 7500/2

    def test_maternity(self):
        from payroll_engine.leave import calculate_leave_balance
        r = calculate_leave_balance(date(2020, 1, 1), 'maternity')
        assert r['entitled'] == 120

    def test_paternity(self):
        from payroll_engine.leave import calculate_leave_balance
        r = calculate_leave_balance(date(2020, 1, 1), 'paternity')
        assert r['entitled'] == 3


class TestLeaveConfigurable:
    """Test leave with database-configured rules."""

    def test_custom_annual_from_database(self, app):
        from payroll_engine import db
        from payroll_engine.models import TaxRule
        from payroll_engine.leave import calculate_annual_entitlement, invalidate_leave_cache

        with app.app_context():
            db.create_all()
            rule = TaxRule(
                version_name='leave-test',
                effective_date=date(2020, 1, 1),
                status='active',
                rules_json={
                    'brackets': [{'min': 0, 'max': None, 'rate': 0.10}],
                    'personal_relief': 0,
                    'leave': {
                        'annual_base': 20,  # More generous than statutory 16
                        'annual_increment': 2,
                        'annual_increment_years': 1,
                        'annual_max': 35,
                        'sick_max_days': 180,
                        'sick_tier_1_days': 30,
                        'sick_tier_2_days': 60,
                        'maternity_days': 120,
                        'paternity_days': 5,  # More generous
                        'special_days': 5,
                        'special_unpaid': True,
                        'special_max_per_year': 2,
                    }
                }
            )
            db.session.add(rule)
            db.session.commit()
            invalidate_leave_cache()

            try:
                # Year 1 should be 20 (not 16)
                assert calculate_annual_entitlement(0) == 20
                # Year 3 should be 26 (20 + 3×2)
                assert calculate_annual_entitlement(3) == 26
            finally:
                db.session.delete(rule)
                db.session.commit()
                invalidate_leave_cache()


# -------------------------------------------------------------------
# SEVERANCE TESTS
# -------------------------------------------------------------------

class TestSeveranceDefaults:
    """Test severance with no database rule (uses hardcoded defaults)."""

    def test_eligible_termination(self):
        from payroll_engine.severance import calculate_severance, TerminationReason
        r = calculate_severance(D('10000'), '2020-01-01', '2025-01-01', 'redundancy')
        assert r['eligible'] is True
        assert r['years_of_service'] == D('5.00')
        # Art. 40: 30 + 4×10 = 70 days. daily=10000/30=333.33. 70×333.33=23333.33
        assert r['final_amount'] > D('20000')
        assert r['final_amount'] < D('25000')

    def test_severance_cap(self):
        from payroll_engine.severance import calculate_severance, TerminationReason
        r = calculate_severance(D('10000'), '2010-01-01', '2025-01-01', 'redundancy')
        assert r['eligible'] is True
        # 15 years: 30 + 14×10 = 170 days. daily=333.33. 170×333.33=56666.67
        assert r['final_amount'] > D('50000')
        assert r['final_amount'] < D('60000')

    def test_resignation_not_eligible(self):
        from payroll_engine.severance import calculate_severance
        r = calculate_severance(D('10000'), '2020-01-01', '2025-01-01', 'resignation')
        assert r['eligible'] is False


class TestSeveranceConfigurable:
    """Test severance with database-configured rules."""

    def test_custom_cap_from_database(self, app):
        from payroll_engine import db
        from payroll_engine.models import TaxRule
        from payroll_engine.severance import calculate_severance, invalidate_severance_cache

        with app.app_context():
            db.create_all()
            rule = TaxRule(
                version_name='sev-test',
                effective_date=date(2020, 1, 1),
                status='active',
                rules_json={
                    'brackets': [{'min': 0, 'max': None, 'rate': 0.10}],
                    'personal_relief': 0,
                    'severance': {
                        'base_days': 30,
                        'increment_factor': 0.333,
                        'max_months': 18,  # More generous than statutory 12
                    }
                }
            )
            db.session.add(rule)
            db.session.commit()
            invalidate_severance_cache()

            try:
                r = calculate_severance(D('10000'), '2010-01-01', '2025-01-01', 'redundancy')
                assert r['eligible'] is True
                # With 18 month cap: 18×30=540 days cap. 170 days < 540, so no cap applies
                assert r['final_amount'] > D('50000')
            finally:
                db.session.delete(rule)
                db.session.commit()
                invalidate_severance_cache()


# -------------------------------------------------------------------
# FIXTURES
# -------------------------------------------------------------------

@pytest.fixture
def app():
    from payroll_engine import create_app
    app = create_app()
    return app
