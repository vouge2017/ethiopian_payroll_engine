"""Issue #85 on a generated, Alembic-migrated disposable PostgreSQL database.

Mirrors the SQLite proofs in ``test_issue_85_annual_leave_accrual.py`` on the
real migrated schema: stored annual accrual through the shared dated rule,
rule values reaching ``LeaveBalance``, dated-rule choice per accrual year,
company-policy semantics, the settlement money path and the explicit repair.

The database is created with a random name, migrated to head, and dropped at
the end of the module. No live or shared database is used. Skipped unless a
disposable ``TEST_DATABASE_URL`` pointing at PostgreSQL is configured.
"""

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import config
from payroll_engine import create_app, db, models
from payroll_engine.leave import LeaveType, calculate_annual_entitlement, invalidate_leave_cache
from payroll_engine.services.leave_service import (
    accrue_annual_leave,
    approve_leave,
    get_leave_balance,
    request_leave,
)
from payroll_engine.services.settlement_service import calculate_settlement
from payroll_engine.severance import TerminationReason

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')

ACCRUAL_YEAR = 2026
END_DATE = date(2026, 12, 31)
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


@pytest.fixture(scope='module')
def database():
    name = 'payroll_issue85_test_' + uuid4().hex
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    url = sa.engine.make_url(PG_URL).set(database=name)
    with control.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    repo = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(repo / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.render_as_string(hide_password=False).replace('%', '%%'))
    command.upgrade(cfg, 'head')
    try:
        yield url, cfg
    finally:
        with control.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        control.dispose()


@pytest.fixture
def leave_db(database, monkeypatch, tmp_path):
    from helpers import seed_synthetic_payroll_rule, synthetic_payroll_rules

    url, _cfg = database
    monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', url.render_as_string(hide_password=False))
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    extra_rule_ids = []
    with app.app_context():
        if not models.TaxRule.query.filter_by(version_name='synthetic-test-rule').first():
            seed_synthetic_payroll_rule()
        baseline = models.TaxRule.query.filter_by(version_name='synthetic-test-rule').one()
        baseline.rules_json = {**synthetic_payroll_rules(), 'leave': dict(SYNTHETIC_LEAVE)}
        db.session.commit()
        invalidate_leave_cache()

        company = models.Company(
            name='Synthetic issue85 ' + uuid4().hex, leave_rate_confirmed_at=datetime(2026, 10, 25)
        )
        db.session.add(company)
        db.session.flush()
        owner = models.User(company_id=company.id, email=uuid4().hex + '@example.invalid', role='owner')
        owner.set_password('Synthetic1!')
        db.session.add(owner)
        db.session.commit()
        ids = {'company': company.id, 'owner': owner.id}
        try:
            yield app, ids, extra_rule_ids
        finally:
            db.session.rollback()
            for table in ('final_settlement', 'leave_balance', 'leave'):
                db.session.execute(sa.text(f'DELETE FROM {table} WHERE company_id = :cid'), {'cid': ids['company']})
            db.session.execute(sa.text('DELETE FROM employee WHERE company_id = :cid'), {'cid': ids['company']})
            db.session.execute(sa.text('DELETE FROM "user" WHERE company_id = :cid'), {'cid': ids['company']})
            db.session.execute(sa.text('DELETE FROM company WHERE id = :cid'), {'cid': ids['company']})
            if extra_rule_ids:
                db.session.execute(sa.text('DELETE FROM tax_rule WHERE id = ANY(:ids)'), {'ids': extra_rule_ids})
            db.session.commit()
            invalidate_leave_cache()
            db.session.remove()


def _employee(ids, years, year=ACCRUAL_YEAR):
    start = date(year, 12, 31) - timedelta(days=365 * years + 10)
    emp = models.Employee(
        company_id=ids['company'],
        employee_id='I85-' + uuid4().hex[:10],
        name='Synthetic Worker',
        basic_salary=Decimal('10000'),
        allowances=Decimal('0'),
        start_date=start,
    )
    db.session.add(emp)
    db.session.commit()
    assert (date(year, 12, 31) - emp.start_date).days // 365 == years
    return emp


def _balance(ids, emp, year=ACCRUAL_YEAR, leave_type=LeaveType.ANNUAL):
    return models.LeaveBalance.query.filter_by(
        company_id=ids['company'], employee_id=emp.id, leave_type=leave_type, year=year
    ).one()


def _set_leave(extra_rule_ids, version_name, effective_date, **overrides):
    from helpers import synthetic_payroll_rules

    rule = models.TaxRule(
        version_name=version_name,
        effective_date=effective_date,
        status='active',
        rules_json={**synthetic_payroll_rules(), 'leave': {**SYNTHETIC_LEAVE, **overrides}},
    )
    db.session.add(rule)
    db.session.commit()
    extra_rule_ids.append(rule.id)
    invalidate_leave_cache()
    return rule


def _approve_leave(ids, emp, days=5):
    result = request_leave(
        employee=emp,
        company_id=ids['company'],
        leave_type=LeaveType.ANNUAL,
        start_date=date(ACCRUAL_YEAR, 8, 1),
        end_date=date(ACCRUAL_YEAR, 8, days),
        reason='Synthetic family visit',
        db_session=db.session,
    )
    assert result['success'], result['errors']
    assert approve_leave(result['leave'], approved_by=ids['owner'], db_session=db.session)['success']
    db.session.commit()


@pytest.mark.parametrize(('years', 'expected'), [(1, 16), (2, 16), (3, 17), (7, 19)])
def test_pg_persisted_accrual_art77(leave_db, years, expected):
    _app, ids, _extra = leave_db
    emp = _employee(ids, years)
    accrue_annual_leave(emp, ids['company'], ACCRUAL_YEAR, db.session)
    db.session.commit()
    assert _balance(ids, emp).entitled == expected


@pytest.mark.parametrize('years', [0, 4, 5, 6, 29, 30, 31, 32])
def test_pg_accrual_equals_shared_calculator(leave_db, years):
    _app, ids, _extra = leave_db
    emp = _employee(ids, years)
    accrue_annual_leave(emp, ids['company'], ACCRUAL_YEAR, db.session)
    db.session.commit()
    assert _balance(ids, emp).entitled == calculate_annual_entitlement(years, None, date(ACCRUAL_YEAR, 12, 31))


def test_pg_rule_values_reach_stored_balance(leave_db):
    _app, ids, extra = leave_db
    _set_leave(extra, 'synthetic-issue85-base20', date(2020, 1, 1), annual_base=20)
    emp = _employee(ids, 1)
    accrue_annual_leave(emp, ids['company'], ACCRUAL_YEAR, db.session)
    db.session.commit()
    assert _balance(ids, emp).entitled == 20


def test_pg_dated_rule_choice_per_accrual_year(leave_db):
    _app, ids, extra = leave_db
    _set_leave(extra, 'synthetic-issue85-2024', date(2024, 1, 1), annual_base=20)
    _set_leave(extra, 'synthetic-issue85-2026', date(2026, 1, 1), annual_base=16)
    for year, expected in [(2024, 21), (2026, 17)]:
        emp = _employee(ids, 3, year=year)
        accrue_annual_leave(emp, ids['company'], year, db.session)
        db.session.commit()
        assert _balance(ids, emp, year=year).entitled == expected


@pytest.mark.parametrize(('policy', 'expected'), [(35, 35), (10, 19)])
def test_pg_company_policy_semantics(leave_db, policy, expected):
    _app, ids, _extra = leave_db
    emp = _employee(ids, 7)
    balance = accrue_annual_leave(emp, ids['company'], ACCRUAL_YEAR, db.session)
    balance.company_policy_days = policy
    balance.entitled = 0
    balance.last_accrual_date = None
    accrue_annual_leave(emp, ids['company'], ACCRUAL_YEAR, db.session)
    db.session.commit()
    assert _balance(ids, emp).entitled == expected


def test_pg_get_leave_balance_and_settlement_preview(leave_db):
    _app, ids, _extra = leave_db
    emp = _employee(ids, 7)
    _approve_leave(ids, emp, days=5)

    result = get_leave_balance(emp, ids['company'], LeaveType.ANNUAL, ACCRUAL_YEAR, db.session)
    db.session.commit()
    assert (result['entitled'], result['taken'], result['remaining']) == (19, 5, 14)
    assert _balance(ids, emp).entitled == 19

    calc = calculate_settlement(emp, TerminationReason.REDUNDANCY, END_DATE, ids['company'], db.session)
    assert calc['calculation_details']['leave']['unused_days'] == '14'
    assert calc['leave_encashment'] == Decimal('4666.67')

    manual = calculate_settlement(
        emp, TerminationReason.REDUNDANCY, END_DATE, ids['company'], db.session, unused_leave_days=Decimal('7')
    )
    assert manual['calculation_details']['leave']['source'] == 'manual'
    assert manual['leave_encashment'] == Decimal('2333.33')


def test_pg_repair_dry_run_apply_and_idempotence(leave_db):
    from payroll_engine.services.leave_balance_repair import repair_annual_leave_balances

    _app, ids, _extra = leave_db
    emp = _employee(ids, 7)
    old = models.LeaveBalance(
        company_id=ids['company'],
        employee_id=emp.id,
        leave_type=LeaveType.ANNUAL,
        year=ACCRUAL_YEAR,
        entitled=23,
        taken=5,
        carried_forward=2,
        last_accrual_date=date(ACCRUAL_YEAR, 1, 1),
    )
    sick = models.LeaveBalance(
        company_id=ids['company'],
        employee_id=emp.id,
        leave_type=LeaveType.SICK,
        year=ACCRUAL_YEAR,
        entitled=180,
        taken=10,
    )
    db.session.add_all([old, sick])
    db.session.commit()
    old_id, sick_id = old.id, sick.id

    dry = repair_annual_leave_balances(ids['company'], year=ACCRUAL_YEAR)
    assert dry['dry_run'] is True
    assert dry['rows'][0]['status'] == 'review'
    assert db.session.get(models.LeaveBalance, old_id).entitled == 23

    with pytest.raises(ValueError, match='explicit balance_ids'):
        repair_annual_leave_balances(ids['company'], apply=True, reviewed=True)

    flagged = repair_annual_leave_balances(ids['company'], balance_ids=[old_id], apply=True)
    assert flagged['rows'][0]['status'] == 'skipped_needs_review'
    assert db.session.get(models.LeaveBalance, old_id).entitled == 23

    applied = repair_annual_leave_balances(ids['company'], balance_ids=[old_id], apply=True, reviewed=True)
    assert applied['counts']['corrected'] == 1
    stored = db.session.get(models.LeaveBalance, old_id)
    assert (stored.entitled, stored.taken, stored.carried_forward) == (19, 5, 2)
    assert stored.last_accrual_date == date(ACCRUAL_YEAR, 1, 1)
    assert db.session.get(models.LeaveBalance, sick_id).entitled == 180

    again = repair_annual_leave_balances(ids['company'], balance_ids=[old_id], apply=True, reviewed=True)
    assert again['counts']['corrected'] == 0
    assert again['counts']['unchanged'] == 1

    preview = calculate_settlement(emp, TerminationReason.REDUNDANCY, END_DATE, ids['company'], db.session)
    assert preview['leave_encashment'] == Decimal('5333.33')
