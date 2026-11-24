"""Issue #85 â€” stored annual leave must use the shared, dated rule calculator.

Pre-fix bug: ``leave_service.accrue_annual_leave`` granted +1 day per year of
service (16 + years, capped at a hardcoded 30) and never read the TaxRule leave
rules. Labour Proclamation 1156/2019 Art. 77(1) is 16 working days for the first
year plus one working day per every additional two years, which is what
``leave.calculate_annual_entitlement`` already implements.

All people, companies and rules here are synthetic. The tests exercise the real
service and public paths (accrual, get_leave_balance, leave request/approval,
settlement preview, the terminate route and the repair utility/CLI), never a
mocked calculator.

Fail-before / pass-after: the accrual, rule-source, dated-rule, settlement and
repair tests fail on clean pre-fix origin/main. The safety tests (repeat
accrual, manual balances not reduced on read, manual unused-days precedence)
pass before the fix too and are counted separately.
"""

import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine import create_app, db
from payroll_engine.leave import LeaveType, calculate_annual_entitlement, invalidate_leave_cache
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    EmployeeDeduction,
    FinalSettlement,
    Leave,
    LeaveBalance,
    TaxRule,
    TenantQuery,
    User,
)
from payroll_engine.services.leave_service import (
    accrue_annual_leave,
    approve_leave,
    get_leave_balance,
    request_leave,
)
from payroll_engine.services.settlement_service import calculate_settlement, create_settlement_record
from payroll_engine.severance import TerminationReason

ACCRUAL_YEAR = 2026
END_DATE = date(2026, 12, 31)

# Explicit synthetic leave values (statutory-shaped, obviously test data).
SYNTHETIC_LEAVE = {
    'annual_base': 16,
    'annual_increment': 1,
    'annual_increment_years': 2,
    'annual_max': 30,
    'sick_max_days': 180,
    'sick_tier_1_days': 30,
    'sick_tier_2_days': 60,
    'maternity_days': 120,
    'paternity_days': 3,
    'special_days': 5,
    'special_unpaid': True,
    'special_max_per_year': 2,
}


@pytest.fixture
def app(tmp_path):
    from helpers import seed_synthetic_payroll_rule

    application = create_app()
    application.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{tmp_path / "issue85.db"}',
        WTF_CSRF_ENABLED=False,
    )
    with application.app_context():
        db.create_all()
        # Explicit dated synthetic tax/pension rule for any payroll math.
        seed_synthetic_payroll_rule()
        for model in [Employee, EmployeeDeduction, Leave, LeaveBalance, FinalSettlement, AuditLog]:
            TenantQuery.register_model(model)
        # Never let a stale leave-rule cache decide a test's outcome.
        invalidate_leave_cache()
        yield application
        invalidate_leave_cache()
        db.session.remove()
        db.drop_all()


def _repair(*args, **kwargs):
    """Import lazily so pre-fix runs fail per test, not at collection."""
    from payroll_engine.services.leave_balance_repair import repair_annual_leave_balances

    return repair_annual_leave_balances(*args, **kwargs)


def _set_leave_rules(**overrides):
    """Give the existing synthetic rule explicit leave values (no competing row)."""
    rule = TaxRule.query.filter_by(version_name='synthetic-test-rule').one()
    rules = dict(rule.rules_json)
    rules['leave'] = {**SYNTHETIC_LEAVE, **overrides}
    rule.rules_json = rules
    db.session.commit()
    invalidate_leave_cache()
    return rule


def _add_dated_leave_rule(version_name, effective_date, **overrides):
    """Add an intentionally dated synthetic rule (older/newer accrual years)."""
    from helpers import synthetic_payroll_rules

    rule = TaxRule(
        version_name=version_name,
        effective_date=effective_date,
        status='active',
        rules_json={**synthetic_payroll_rules(), 'leave': {**SYNTHETIC_LEAVE, **overrides}},
    )
    db.session.add(rule)
    db.session.commit()
    invalidate_leave_cache()
    return rule


def _company(name='Synthetic Leave Co 85'):
    company = Company(name=name, leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0))
    db.session.add(company)
    db.session.flush()
    user = User(phone='911' + uuid4().hex[:7], company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    return company, user


def _employee(company, years, year=ACCRUAL_YEAR):
    """Synthetic employee with exactly ``years`` complete service years at year end."""
    start = date(year, 12, 31) - timedelta(days=365 * years + 10)
    emp = Employee(
        employee_id='SYN85-' + uuid4().hex[:8],
        name='Synthetic Worker',
        basic_salary=Decimal('10000'),
        allowances=Decimal('0'),
        company_id=company.id,
        start_date=start,
    )
    db.session.add(emp)
    db.session.commit()
    assert (date(year, 12, 31) - emp.start_date).days // 365 == years
    return emp


def _stored_balance(company, emp, year=ACCRUAL_YEAR, leave_type=LeaveType.ANNUAL):
    return LeaveBalance.query.filter_by(
        company_id=company.id, employee_id=emp.id, leave_type=leave_type, year=year
    ).one()


def _approve_annual_leave(company, user, emp, days=5, year=ACCRUAL_YEAR):
    result = request_leave(
        employee=emp,
        company_id=company.id,
        leave_type=LeaveType.ANNUAL,
        start_date=date(year, 8, 1),
        end_date=date(year, 8, days),
        reason='Synthetic family visit',
        db_session=db.session,
    )
    assert result['success'], result['errors']
    approval = approve_leave(result['leave'], approved_by=user.id, db_session=db.session)
    assert approval['success'], approval['message']
    db.session.commit()


# --------------------------------------------------------------------------
# 1. Persisted accrual follows Art. 77(1) through the shared rule source
# --------------------------------------------------------------------------


@pytest.mark.parametrize(('years', 'expected'), [(1, 16), (2, 16), (3, 17), (7, 19)])
def test_persisted_accrual_art77_service_years(app, years, expected):
    company, _user = _company()
    emp = _employee(company, years)

    balance = accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert balance.entitled == expected
    assert _stored_balance(company, emp).entitled == expected


@pytest.mark.parametrize('years', [0])
def test_first_year_zero_service_years_regression(app, years):
    """First-year behaviour is unchanged: the base grant, no increment."""
    company, _user = _company()
    emp = _employee(company, years)

    accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert _stored_balance(company, emp).entitled == 16


def test_mid_year_joiner_gets_base_grant_not_prorated(app):
    """The stored accrual path has never prorated; keep that behaviour."""
    company, _user = _company()
    emp = Employee(
        employee_id='SYN85-MID',
        name='Synthetic Midyear Worker',
        basic_salary=Decimal('10000'),
        allowances=Decimal('0'),
        company_id=company.id,
        start_date=date(ACCRUAL_YEAR, 6, 1),
    )
    db.session.add(emp)
    db.session.commit()

    accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert _stored_balance(company, emp).entitled == 16


@pytest.mark.parametrize('years', [*range(0, 13), 29, 30, 31, 32])
def test_accrual_equals_shared_calculator(app, years):
    """The two paths must agree, including the configured cap boundary."""
    company, _user = _company()
    emp = _employee(company, years)

    accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    expected = calculate_annual_entitlement(years, None, date(ACCRUAL_YEAR, 12, 31))
    assert _stored_balance(company, emp).entitled == expected


@pytest.mark.parametrize('policy', [None, 0, 10, 20, 35])
def test_accrual_equals_shared_calculator_with_company_policy(app, policy):
    company, _user = _company()
    emp = _employee(company, 7)
    balance = accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    balance.company_policy_days = policy
    # Re-accrue from scratch so the policy is an input, not a stored snapshot.
    balance.entitled = 0
    balance.last_accrual_date = None
    accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    expected = calculate_annual_entitlement(7, policy, date(ACCRUAL_YEAR, 12, 31))
    assert _stored_balance(company, emp).entitled == expected


# --------------------------------------------------------------------------
# 2. The dated TaxRule leave values reach the stored balance
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('overrides', 'years', 'expected'),
    [
        ({'annual_base': 20}, 1, 20),
        ({'annual_increment': 2}, 3, 18),
        ({'annual_increment_years': 1}, 3, 18),
        ({'annual_max': 18}, 7, 18),
        ({'annual_base': 20, 'annual_increment': 2, 'annual_increment_years': 1, 'annual_max': 35}, 3, 24),
    ],
)
def test_rule_values_reach_stored_balance(app, overrides, years, expected):
    company, _user = _company()
    emp = _employee(company, years)
    _set_leave_rules(**overrides)

    accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert _stored_balance(company, emp).entitled == expected


def test_dated_rules_choose_the_accrual_year_not_today(app):
    """An older accrual year uses its own rule even when today's rule differs."""
    company, _user = _company()
    _add_dated_leave_rule('synthetic-leave-2024', date(2024, 1, 1), annual_base=20)
    _add_dated_leave_rule('synthetic-leave-2026', date(2026, 1, 1), annual_base=16)
    _add_dated_leave_rule('synthetic-leave-2027', date(2027, 1, 1), annual_base=25)

    # Today's rule is the 2026 one (16), not the 2024 one (20).
    assert TaxRule.get_active_rule().version_name == 'synthetic-leave-2026'

    for year, expected in [(2024, 21), (2025, 21), (2026, 17)]:
        emp = _employee(company, 3, year=year)
        accrue_annual_leave(emp, company.id, year, db.session)
        db.session.commit()
        assert _stored_balance(company, emp, year=year).entitled == expected, year
        assert calculate_annual_entitlement(3, None, date(year, 12, 31)) == expected

    # A rule effective after the accrual year's 31 December must not be used.
    emp = _employee(company, 3, year=2026)
    accrue_annual_leave(emp, company.id, 2026, db.session)
    db.session.commit()
    assert _stored_balance(company, emp, year=2026).entitled == 17


# --------------------------------------------------------------------------
# 3. Company policy: more is kept, less cannot undercut the shared minimum
# --------------------------------------------------------------------------


@pytest.mark.parametrize(('policy', 'expected'), [(35, 35), (20, 20), (10, 19), (0, 19), (None, 19)])
def test_company_policy_semantics(app, policy, expected):
    company, _user = _company()
    emp = _employee(company, 7)
    balance = accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    balance.company_policy_days = policy
    balance.entitled = 0
    balance.last_accrual_date = None
    accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    stored = _stored_balance(company, emp)
    assert stored.entitled == expected
    assert stored.company_policy_days == policy


def test_generous_policy_above_configured_cap_is_kept(app):
    company, _user = _company()
    emp = _employee(company, 32)
    balance = accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    balance.company_policy_days = 40
    balance.entitled = 0
    balance.last_accrual_date = None
    accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert _stored_balance(company, emp).entitled == 40


# --------------------------------------------------------------------------
# 4. Safety: repeat accrual and stored balances on routine reads
# --------------------------------------------------------------------------


def test_repeat_accrual_is_safe(app):
    company, _user = _company()
    emp = _employee(company, 7)

    first = accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()
    first_date = first.last_accrual_date
    second = accrue_annual_leave(emp, company.id, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert second.entitled == first.entitled == 19
    assert second.last_accrual_date == first_date
    assert LeaveBalance.query.filter_by(company_id=company.id, employee_id=emp.id).count() == 1


def test_manual_higher_balance_not_reduced_on_read(app):
    company, _user = _company()
    emp = _employee(company, 7)
    db.session.add(
        LeaveBalance(
            company_id=company.id,
            employee_id=emp.id,
            leave_type=LeaveType.ANNUAL,
            year=ACCRUAL_YEAR,
            entitled=25,
            taken=0,
            last_accrual_date=date(ACCRUAL_YEAR, 1, 1),
        )
    )
    db.session.commit()

    result = get_leave_balance(emp, company.id, LeaveType.ANNUAL, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert result['entitled'] == 25
    assert result['remaining'] == 25
    assert _stored_balance(company, emp).entitled == 25


def test_get_leave_balance_integration(app):
    """Stored and returned entitlement/remaining through the public service."""
    company, user = _company()
    emp = _employee(company, 7)
    _approve_annual_leave(company, user, emp, days=5)

    result = get_leave_balance(emp, company.id, LeaveType.ANNUAL, ACCRUAL_YEAR, db.session)
    db.session.commit()

    assert result['entitled'] == 19
    assert result['taken'] == 5
    assert result['remaining'] == 14
    stored = _stored_balance(company, emp)
    assert stored.entitled == 19
    assert stored.taken == 5
    assert stored.remaining == 14


# --------------------------------------------------------------------------
# 5. Money path: settlement preview uses the corrected recorded days
# --------------------------------------------------------------------------


def test_settlement_preview_uses_rule_correct_recorded_days(app):
    company, user = _company()
    emp = _employee(company, 7)
    _approve_annual_leave(company, user, emp, days=5)

    calc = calculate_settlement(emp, TerminationReason.REDUNDANCY, END_DATE, company.id, db.session)

    # 19 entitled - 5 taken = 14 unused days x (10,000 / 30).
    assert calc['calculation_details']['leave']['source'] == 'leave_record'
    assert calc['calculation_details']['leave']['unused_days'] == '14'
    assert calc['leave_encashment'] == Decimal('4666.67')


def test_manual_unused_days_override_keeps_precedence(app):
    company, user = _company()
    emp = _employee(company, 7)
    _approve_annual_leave(company, user, emp, days=5)

    calc = calculate_settlement(
        emp, TerminationReason.REDUNDANCY, END_DATE, company.id, db.session, unused_leave_days=Decimal('7')
    )

    assert calc['calculation_details']['leave']['source'] == 'manual'
    assert calc['leave_encashment'] == Decimal('2333.33')
    assert any('manually' in warning for warning in calc['warnings'])


def test_repair_changes_future_preview_but_not_recorded_settlement(app):
    """An old over-granted snapshot is corrected deliberately; history is kept."""
    company, user = _company()
    emp = _employee(company, 7)
    # Simulate a pre-#85 stored snapshot: 16 + 7 = 23 days, 5 taken.
    db.session.add(
        LeaveBalance(
            company_id=company.id,
            employee_id=emp.id,
            leave_type=LeaveType.ANNUAL,
            year=ACCRUAL_YEAR,
            entitled=23,
            taken=5,
            carried_forward=2,
            last_accrual_date=date(ACCRUAL_YEAR, 1, 1),
        )
    )
    db.session.commit()

    recorded = create_settlement_record(emp, TerminationReason.REDUNDANCY, END_DATE, company.id, user.id, db.session)
    db.session.commit()
    recorded_id = recorded.id
    before = {
        'leave_encashment': recorded.leave_encashment,
        'net_final_payment': recorded.net_final_payment,
        'tax_on_salary': recorded.tax_on_salary,
        'severance_pay': recorded.severance_pay,
        'total_earnings': recorded.total_earnings,
    }
    # 23 + 2 carried - 5 taken = 20 unused days on the old snapshot.
    assert before['leave_encashment'] == Decimal('6666.67')

    dry = _repair(company.id, year=ACCRUAL_YEAR)
    assert dry['dry_run'] is True
    assert _stored_balance(company, emp).entitled == 23
    assert calculate_settlement(emp, TerminationReason.REDUNDANCY, END_DATE, company.id, db.session)[
        'leave_encashment'
    ] == Decimal('6666.67')

    result = _repair(
        company.id,
        year=ACCRUAL_YEAR,
        balance_ids=[_stored_balance(company, emp).id],
        apply=True,
        reviewed=True,
    )
    assert result['counts']['corrected'] == 1
    stored = _stored_balance(company, emp)
    assert stored.entitled == 19
    assert stored.taken == 5
    assert stored.carried_forward == 2

    preview = calculate_settlement(emp, TerminationReason.REDUNDANCY, END_DATE, company.id, db.session)
    # 19 + 2 carried - 5 taken = 16 unused days after the deliberate correction.
    assert preview['leave_encashment'] == Decimal('5333.33')

    untouched = db.session.get(FinalSettlement, recorded_id)
    assert untouched.leave_encashment == before['leave_encashment']
    assert untouched.net_final_payment == before['net_final_payment']
    assert untouched.tax_on_salary == before['tax_on_salary']
    assert untouched.severance_pay == before['severance_pay']
    assert untouched.total_earnings == before['total_earnings']
    assert untouched.calculation_details['leave']['unused_days'] == '20'


def test_terminate_route_preview_shows_corrected_days_and_saves_nothing(app):
    company, user = _company()
    emp = _employee(company, 7)
    _approve_annual_leave(company, user, emp, days=5)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data={
            'termination_reason': 'redundancy',
            'end_date': END_DATE.isoformat(),
            'action': 'preview',
        },
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert '14 days' in html
    assert 'ETB 4666.67' in html
    assert FinalSettlement.query.filter_by(company_id=company.id, employee_id=emp.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False


# --------------------------------------------------------------------------
# 6. The explicit repair utility
# --------------------------------------------------------------------------


def _old_snapshot(company, emp, entitled=23, year=ACCRUAL_YEAR, **fields):
    balance = LeaveBalance(
        company_id=company.id,
        employee_id=emp.id,
        leave_type=LeaveType.ANNUAL,
        year=year,
        entitled=entitled,
        taken=fields.pop('taken', 5),
        carried_forward=fields.pop('carried_forward', 2),
        company_policy_days=fields.pop('company_policy_days', None),
        last_accrual_date=date(year, 1, 1),
        **fields,
    )
    db.session.add(balance)
    db.session.commit()
    return balance


def test_repair_dry_run_is_default_and_writes_nothing(app):
    company, _user = _company()
    emp = _employee(company, 7)
    balance = _old_snapshot(company, emp)

    report = _repair(company.id)

    assert report['dry_run'] is True
    row = report['rows'][0]
    assert row['balance_id'] == balance.id
    assert row['old_entitled'] == 23
    assert row['new_entitled'] == 19
    assert row['status'] == 'review'
    assert 'Human review' in row['reason']
    assert _stored_balance(company, emp).entitled == 23
    assert _stored_balance(company, emp).taken == 5
    assert _stored_balance(company, emp).carried_forward == 2


def test_repair_apply_requires_explicit_selection(app):
    company, _user = _company()
    emp = _employee(company, 7)
    _old_snapshot(company, emp)

    with pytest.raises(ValueError, match='explicit balance_ids'):
        _repair(company.id, apply=True, reviewed=True)
    assert _stored_balance(company, emp).entitled == 23


def test_repair_apply_without_review_flags_and_writes_nothing(app):
    company, _user = _company()
    emp = _employee(company, 7)
    balance = _old_snapshot(company, emp)

    report = _repair(company.id, balance_ids=[balance.id], apply=True)

    assert report['rows'][0]['status'] == 'skipped_needs_review'
    assert report['counts']['corrected'] == 0
    assert _stored_balance(company, emp).entitled == 23


def test_repair_selected_correction_changes_only_entitled(app):
    company, _user = _company()
    emp = _employee(company, 7)
    balance = _old_snapshot(company, emp, company_policy_days=None)
    accrual_date = balance.last_accrual_date

    report = _repair(company.id, balance_ids=[balance.id], apply=True, reviewed=True)

    assert report['counts']['corrected'] == 1
    stored = _stored_balance(company, emp)
    assert stored.entitled == 19
    assert stored.taken == 5
    assert stored.carried_forward == 2
    assert stored.company_policy_days is None
    assert stored.last_accrual_date == accrual_date
    assert stored.leave_type == LeaveType.ANNUAL
    assert stored.year == ACCRUAL_YEAR


def test_repair_is_idempotent(app):
    company, _user = _company()
    emp = _employee(company, 7)
    balance = _old_snapshot(company, emp)

    first = _repair(company.id, balance_ids=[balance.id], apply=True, reviewed=True)
    second = _repair(company.id, balance_ids=[balance.id], apply=True, reviewed=True)

    assert first['counts']['corrected'] == 1
    assert second['counts']['corrected'] == 0
    assert second['counts']['unchanged'] == 1
    assert _stored_balance(company, emp).entitled == 19


def test_repair_leaves_other_companies_years_and_leave_types_untouched(app):
    company, _user = _company()
    other_company, _other_user = _company('Synthetic Other Co 85')
    emp = _employee(company, 7)
    other_emp = _employee(other_company, 7)

    target = _old_snapshot(company, emp)
    other_year = _old_snapshot(company, emp, year=2025)
    other_tenant = _old_snapshot(other_company, other_emp)
    sick = LeaveBalance(
        company_id=company.id,
        employee_id=emp.id,
        leave_type=LeaveType.SICK,
        year=ACCRUAL_YEAR,
        entitled=180,
        taken=10,
    )
    db.session.add(sick)
    db.session.commit()

    report = _repair(company.id, year=ACCRUAL_YEAR, balance_ids=[target.id], apply=True, reviewed=True)

    assert report['counts']['corrected'] == 1
    assert len(report['rows']) == 1
    assert _stored_balance(company, emp).entitled == 19
    assert _stored_balance(company, emp, year=2025).entitled == 23
    assert _stored_balance(other_company, other_emp).entitled == 23
    assert db.session.get(LeaveBalance, sick.id).entitled == 180
    assert db.session.get(LeaveBalance, sick.id).taken == 10
    assert other_year.entitled == 23
    assert other_tenant.entitled == 23


def test_repair_apply_only_writes_the_selected_record(app):
    company, _user = _company()
    emp = _employee(company, 7)
    second = _employee(company, 7)
    chosen = _old_snapshot(company, emp)
    unchosen = _old_snapshot(company, second)

    report = _repair(company.id, year=ACCRUAL_YEAR, balance_ids=[chosen.id], apply=True, reviewed=True)

    statuses = {row['balance_id']: row['status'] for row in report['rows']}
    assert statuses[chosen.id] == 'corrected'
    assert statuses[unchosen.id] == 'skipped_not_selected'
    assert db.session.get(LeaveBalance, chosen.id).entitled == 19
    assert db.session.get(LeaveBalance, unchosen.id).entitled == 23


def test_repair_flags_lower_and_ambiguous_balances_without_changing_them(app):
    company, _user = _company()
    emp = _employee(company, 7)
    lower = _old_snapshot(company, emp, entitled=10)
    higher = LeaveBalance(
        company_id=company.id,
        employee_id=emp.id,
        leave_type=LeaveType.ANNUAL,
        year=2025,
        entitled=23,
        taken=0,
        last_accrual_date=date(2025, 1, 1),
    )
    db.session.add(higher)
    db.session.commit()

    report = _repair(company.id)

    statuses = {row['balance_id']: row['status'] for row in report['rows']}
    assert statuses[lower.id] == 'review'
    assert statuses[higher.id] == 'review'
    assert all('Human review' in row['reason'] for row in report['rows'])
    assert db.session.get(LeaveBalance, lower.id).entitled == 10
    assert db.session.get(LeaveBalance, higher.id).entitled == 23


def test_repair_cli_dry_run_and_apply_guard(app):
    company, _user = _company()
    emp = _employee(company, 7)
    balance = _old_snapshot(company, emp)
    runner = app.test_cli_runner()

    dry = runner.invoke(args=['repair-annual-leave', '--company-id', str(company.id)])
    assert dry.exit_code == 0, dry.output
    assert 'DRY RUN' in dry.output
    assert f'balance {balance.id}' in dry.output
    assert 'entitled 23 -> 19' in dry.output
    assert _stored_balance(company, emp).entitled == 23

    guarded = runner.invoke(args=['repair-annual-leave', '--company-id', str(company.id), '--apply', '--reviewed'])
    assert guarded.exit_code != 0
    assert 'explicit balance_ids' in guarded.output
    assert _stored_balance(company, emp).entitled == 23

    applied = runner.invoke(
        args=[
            'repair-annual-leave',
            '--company-id',
            str(company.id),
            '--balance-id',
            str(balance.id),
            '--apply',
            '--reviewed',
        ]
    )
    assert applied.exit_code == 0, applied.output
    assert 'corrected=1' in applied.output
    assert _stored_balance(company, emp).entitled == 19
