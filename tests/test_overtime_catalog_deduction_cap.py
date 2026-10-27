"""Catalog PR 6: overtime types in the catalog and the one-third deduction cap.

Overtime: the four Art. 68 rates are shared system catalog items, read by
the overtime module for every engine with effective dates; migration
b5c6d7e8f9a0 copies the rates the app applied (code defaults, then each
active TaxRule) so no amount changes (see also
tests/test_catalog_assignment_golden.py); the items are locked, never
assigned and never monthly earnings.

Deduction cap (Labour Proc. 1156/2019 Art. 59): approval is blocked when a
month's deductions without written consent exceed one third of the basic
salary; the preview warns; amounts are never reduced; court orders are not
counted; consent per deduction or per employee unblocks.
"""

import importlib.util
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask import g

from payroll_engine import create_app, db
from payroll_engine.catalog import seed_company_catalog
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    PayItemType,
    PayItemTypeVersion,
    PayrollDraft,
    PayrollItemAssignment,
    PayrollRun,
    Payslip,
    TaxRule,
    User,
    UserCompany,
)
from payroll_engine.overtime_catalog import OVERTIME_KEYS, OVERTIME_TYPE_BY_KEY
from payroll_engine.services import employee_assignments as ea

REPO = Path(__file__).resolve().parents[1]
MIGRATION = REPO / 'migrations' / 'versions' / 'b5c6d7e8f9a0_overtime_catalog_deduction_consent.py'
PASSWORD = 'Test1234!'
RUN_DATE = date(2026, 9, 1)


@pytest.fixture
def app(monkeypatch):
    from payroll_engine.overtime import invalidate_overtime_cache

    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args, **kwargs: None)
    app = create_app()
    app.config.update(
        TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False
    )

    @app.before_request
    def _fresh_login_user():
        g.pop('_login_user', None)

    with app.app_context():
        db.create_all()
        invalidate_overtime_cache()
        yield app
        invalidate_overtime_cache()
        db.session.remove()
        db.drop_all()


def _company(name='Cap PLC'):
    co = Company(name=name, billing_status='active', plan_code='standard', paid_until=date.today() + timedelta(days=60))
    db.session.add(co)
    db.session.flush()
    seed_company_catalog(co.id, commit=False)
    db.session.commit()
    return co


def _user(company, phone, role):
    user = User(phone=phone, company_id=company.id, role=role, first_name='Synthetic', last_name='User')
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(UserCompany(user_id=user.id, company_id=company.id, role=role))
    db.session.commit()
    return user


def _login(app, user):
    client = app.test_client()
    resp = client.post('/auth/login', data={'login_id': user.phone, 'password': PASSWORD})
    assert resp.status_code == 302
    return client


def _employee(company_id, code='E1', salary='6000'):
    emp = Employee(
        company_id=company_id, employee_id=code, name=f'Emp {code}', phone='0912345670', basic_salary=Decimal(salary)
    )
    db.session.add(emp)
    db.session.commit()
    return emp


def _item(company_id, key):
    return PayItemType.query.filter_by(company_id=company_id, key=key).one()


def _system(key):
    return PayItemType.query.filter_by(company_id=None, key=key).one()


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _invalidate():
    from payroll_engine.overtime import invalidate_overtime_cache

    invalidate_overtime_cache()


# ---------------------------------------------------------------------------
# Overtime in the catalog
# ---------------------------------------------------------------------------


def test_overtime_items_seeded_locked_and_not_monthly_earnings(app):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments
    from payroll_engine.services import pay_item_settings as svc

    co = _company()
    rows = {key: _system(key) for key in OVERTIME_KEYS}
    assert {k: (str(r.rate), r.calculation_method, r.classification, r.is_system) for k, r in rows.items()} == {
        'overtime_day': ('1.5000', 'rate_x_units', 'earning', True),
        'overtime_night': ('1.7500', 'rate_x_units', 'earning', True),
        'overtime_holiday': ('2.0000', 'rate_x_units', 'earning', True),
        'overtime_rest_day_holiday': ('2.5000', 'rate_x_units', 'earning', True),
    }
    assert all(r.regulation_reference == 'Labour Proclamation No. 1156/2019, Art. 68' for r in rows.values())
    assert all(not r.pensionable and not r.counts_as_art53_wage for r in rows.values())
    assert svc.permissions(rows['overtime_day'], svc.Usage())['locked']
    with pytest.raises(ea.AssignmentError):
        ea.assignable_item(co.id, key='overtime_day')
    with pytest.raises(svc.PayItemSettingsError):
        svc.clean_key(co.id, 'overtime_night')  # reserved: a company cannot shadow it
    emp = _employee(co.id)
    result = calculate_payroll_from_assignments(emp, co.id, date(2026, 10, 31), consume_balances=False)
    assert not [li for li in result['line_items'] if li['item_key'] in OVERTIME_KEYS]


def test_settings_page_shows_overtime_rates_read_only(app):
    co = _company()
    client = _login(app, _user(co, '911400001', 'owner'))
    page = client.get('/settings/pay-items').data
    assert b'Overtime: regular day (6am-10pm)' in page and b'Overtime: rest day + holiday' in page
    item = _system('overtime_day')
    assert client.post(f'/settings/pay-items/{item.id}/edit', data={'name_en': 'x'}).status_code == 403
    assert client.post(f'/settings/pay-items/{item.id}/deactivate').status_code == 403


def test_every_engine_reads_the_catalog_rate_for_the_period(app):
    from payroll_engine.item_versions import record_version
    from payroll_engine.overtime import calculate_overtime_pay, get_overtime_rates
    from payroll_engine.payroll import calculate_payroll
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    co = _company()
    emp = _employee(co.id, salary='20800')
    day = _system('overtime_day')
    day.rate = Decimal('1.6000')
    record_version(day, effective_from=date(2026, 11, 1), source='settings')
    db.session.commit()
    _invalidate()
    oct_, nov = date(2026, 10, 31), date(2026, 11, 30)
    assert get_overtime_rates(oct_)['day'] == Decimal('1.50')
    assert get_overtime_rates(nov)['day'] == Decimal('1.6000')
    # 20,800 / 208 = 100 per hour.
    assert calculate_overtime_pay(Decimal('20800'), 2, 'day', for_date=oct_) == Decimal('300.00')
    assert calculate_overtime_pay(Decimal('20800'), 2, 'day', for_date=nov) == Decimal('320.00')
    entries = [{'hours': 2, 'type': 'day'}]
    for d, expected in ((oct_, Decimal('300.00')), (nov, Decimal('320.00'))):
        elements = calculate_payroll_from_assignments(emp, co.id, d, overtime_entries=entries, consume_balances=False)
        legacy = calculate_payroll(Decimal('20800'), Decimal('0'), overtime_entries=entries, for_date=d)
        assert elements['overtime_pay'] == expected and legacy['overtime_pay'] == expected


def test_tax_rule_rates_copied_then_catalog_is_the_source(app):
    from payroll_engine.overtime import get_overtime_rates
    from payroll_engine.overtime_catalog import sync_overtime_items_from_tax_rules

    _company()
    rule = TaxRule(
        version_name='ot-2025',
        effective_date=date(2025, 7, 8),
        country='ET',
        status='active',
        rules_json={'overtime': {'rates': {'day': 1.25, 'night': 1.5}}},
    )
    db.session.add(rule)
    db.session.commit()
    sync_overtime_items_from_tax_rules()
    db.session.commit()
    counts = {
        k: PayItemTypeVersion.query.filter_by(company_id=None, pay_item_type_id=_system(k).id).count()
        for k in OVERTIME_KEYS
    }
    sync_overtime_items_from_tax_rules()  # idempotent
    db.session.commit()
    assert counts == {
        k: PayItemTypeVersion.query.filter_by(company_id=None, pay_item_type_id=_system(k).id).count()
        for k in OVERTIME_KEYS
    }
    _invalidate()
    assert get_overtime_rates(date(2025, 7, 7))['day'] == Decimal('1.50')
    assert get_overtime_rates(date(2025, 7, 8))['day'] == Decimal('1.25')
    assert get_overtime_rates(date(2030, 1, 1))['night'] == Decimal('1.5')
    assert get_overtime_rates(date(2030, 1, 1))['holiday'] == Decimal('2.00')
    # TaxRule rates are no longer read: archiving the rule leaves the catalog rates in place.
    rule.status = 'archived'
    db.session.commit()
    _invalidate()
    assert get_overtime_rates(date(2026, 10, 31))['day'] == Decimal('1.25')


def test_migration_frozen_copies_match_the_app():
    from payroll_engine.overtime import DEFAULT_OVERTIME_RATES
    from payroll_engine.overtime_catalog import EPOCH, LABELS, REGULATION, timeline_from_rules

    mig = _load(MIGRATION, 'mig_b5c6_frozen')
    assert mig.revision == 'b5c6d7e8f9a0' and mig.down_revision == 'a4b5c6d7e8f9'
    assert mig.DEFAULT_RATES == DEFAULT_OVERTIME_RATES and mig.EPOCH == EPOCH and mig.REGULATION == REGULATION
    assert {k: c for k, c, *_ in mig.ITEMS} == OVERTIME_TYPE_BY_KEY
    assert {c: (n, am, s) for _k, c, n, am, s in mig.ITEMS} == {c: (v[0], v[1], v[3]) for c, v in LABELS.items()}
    rules = [
        (date(2025, 7, 8), {'overtime': {'rates': {'day': 1.25, 'night': 1.5}}}),
        (date(2026, 1, 1), {'brackets': []}),
        (date(1990, 1, 1), {'overtime': {'rates': {'holiday': 3}}}),
    ]
    assert mig.timeline_from_rules(rules) == timeline_from_rules(rules)
    # The b7c1 catalog seeder must leave the overtime items to this migration, or
    # a fresh Alembic build would create them first and skip the TaxRule copy.
    seed = _load(REPO / 'migrations' / 'versions' / 'b7c1d2e3f4a5_seed_pay_item_catalog.py', 'mig_b7c1_frozen')
    system_specs, template_specs = seed._specs()
    assert not {s['key'] for s in system_specs + template_specs} & set(OVERTIME_KEYS)
    assert set(OVERTIME_KEYS) == seed._LATER_SYSTEM_KEYS


def test_migration_round_trip_on_sqlite(app):
    from payroll_engine.overtime import get_overtime_rates
    from payroll_engine.overtime_catalog import timeline_from_rules

    co = _company()
    emp_id = _employee(co.id).id
    db.session.add(
        TaxRule(
            version_name='ot',
            effective_date=date(2025, 7, 8),
            country='ET',
            status='active',
            rules_json={'overtime': {'rates': {'day': 1.25}}},
        )
    )
    db.session.commit()
    mig = _load(MIGRATION, 'mig_b5c6_round_trip')

    def ops(fn):
        conn = db.session.connection()
        with Operations.context(MigrationContext.configure(conn)):
            fn()

    db.session.expunge_all()
    ops(mig.downgrade)
    inspector = sa.inspect(db.session.connection())
    assert 'deduction_consent_on_file' not in {c['name'] for c in inspector.get_columns('employee')}
    assert not db.session.execute(sa.text("SELECT count(*) FROM pay_item_type WHERE key LIKE 'overtime_%'")).scalar()
    ops(mig.upgrade)
    db.session.commit()
    db.session.expire_all()
    _invalidate()
    day = _system('overtime_day')
    versions = PayItemTypeVersion.query.filter_by(company_id=None, pay_item_type_id=day.id).order_by('version_no').all()
    assert [(v.effective_from, str(v.rate), v.source) for v in versions] == [
        (date(2000, 1, 1), '1.5000', 'migration'),
        (date(2025, 7, 8), '1.2500', 'migration'),
    ]
    assert day.current_version_no == 2 and day.rate == Decimal('1.2500')
    assert get_overtime_rates(date(2024, 1, 1))['day'] == Decimal('1.50')
    assert get_overtime_rates(date(2026, 1, 1))['day'] == Decimal('1.25')
    night = _system('overtime_night')
    assert night.current_version_no == 1 and night.rate == Decimal('1.7500')
    assert len(timeline_from_rules([])) == 1
    assert mig.seed_overtime_items(db.session.connection()) == 0  # idempotent
    emp = db.session.get(Employee, emp_id)
    assert emp.deduction_consent_on_file is False
    # Downgrade refuses while consent is recorded.
    emp.deduction_consent_on_file, emp.deduction_consent_note = True, 'HR file'
    db.session.commit()
    with pytest.raises(RuntimeError, match='legal evidence'):
        ops(mig.downgrade)
    db.session.rollback()


# ---------------------------------------------------------------------------
# One-third deduction cap: the rule
# ---------------------------------------------------------------------------


def test_cap_rule_counts_excludes_and_consents():
    from types import SimpleNamespace

    from payroll_engine.deduction_cap import check

    emp = SimpleNamespace(employee_id='E1', name='Emp', deduction_consent_on_file=False)
    details = [
        {'type': 'advance', 'label': 'Advance', 'amount': '1500.00', 'assignment_id': 1},
        {'type': 'loan', 'label': 'Loan', 'amount': '500.00', 'assignment_id': 2},
        {'type': 'court_order', 'label': 'Case', 'amount': '9000.00', 'assignment_id': 3},
        {'type': 'cost_sharing', 'label': 'MoE', 'amount': 100.0, 'legacy': True, 'id': 7},
    ]
    result = check(emp, Decimal('6300'), details)
    assert result.counted == Decimal('2100.00') and result.cap == Decimal('2100.00') and not result.exceeds
    result = check(emp, Decimal('6299.99'), details)
    assert result.exceeds  # exact comparison: 2,100.00 x 3 > 6,299.99
    assert check(emp, Decimal('6299.99'), details, consented_assignment_ids={1}).counted == Decimal('600.00')
    emp.deduction_consent_on_file = True
    assert not check(emp, Decimal('1'), details).exceeds
    assert [line.status for line in check(emp, Decimal('1'), details).lines] == [
        'consented',
        'consented',
        'excluded',
        'consented',
    ]


# ---------------------------------------------------------------------------
# One-third deduction cap: approval, preview, consent
# ---------------------------------------------------------------------------


@pytest.fixture
def cap_world(app):
    co = _company()
    owner = _user(co, '911400011', 'owner')
    accountant = _user(co, '911400012', 'accountant')
    emp_user = _user(co, '911400013', 'employee')
    emp = _employee(co.id, 'C1', salary='6000')
    advance = ea.create_assignment(
        co.id, owner.id, emp, _item(co.id, 'advance'), value='2500', start='2026-09-01', label='Salary advance'
    )
    ea.create_assignment(co.id, owner.id, emp, _item(co.id, 'other_deduction'), value='400', label='Canteen')
    ea.create_assignment(
        co.id, owner.id, emp, _item(co.id, 'court_order'), value='30', mode='percent_of_net', label='Case 7/2026'
    )
    ok = _employee(co.id, 'C2', salary='9000')
    ea.create_assignment(co.id, owner.id, ok, _item(co.id, 'loan'), value='1000', label='Small loan')
    db.session.commit()
    return {'co': co, 'owner': owner, 'accountant': accountant, 'emp_user': emp_user, 'emp': emp, 'advance': advance}


def _review(w):
    from payroll_engine.services.worksheet_review import create_review

    run = create_review(w['co'].id, w['owner'].id, RUN_DATE)
    db.session.commit()
    return run


def _approve(w, run):
    from payroll_engine.services.payroll_service import process_payroll

    return process_payroll(run, w['co'].id, w['owner'].id, 'owner@test.example', '127.0.0.1')


def test_worksheet_preview_warns_and_approval_is_blocked_without_reducing(app, cap_world):
    w = cap_world
    run = _review(w)
    draft_rows = {
        r['id']: r
        for r in PayrollDraft.query.filter_by(company_id=w['co'].id, payroll_run_id=run.id).one().employee_data
    }
    before = {k: (r['net'], r['total_deductions']) for k, r in draft_rows.items()}
    client = _login(app, w['owner'])
    page = client.get(f'/payroll/runs/{run.id}/review').data
    assert b'data-testid="deduction-cap-warning"' in page and b'C1 Emp C1' in page and b'C2 Emp C2' not in page
    result = _approve(w, run)
    assert not result.success
    assert 'Art. 59' in result.message and 'C1 Emp C1' in result.message and 'ETB 2,900.00' in result.message
    assert 'Salary advance 2,500.00' in result.message and 'Case 7/2026' not in result.message
    run = db.session.get(PayrollRun, run.id)
    assert run.status == 'review'
    assert Payslip.query.filter_by(company_id=w['co'].id, payroll_run_id=run.id).count() == 0
    rows = PayrollDraft.query.filter_by(company_id=w['co'].id, payroll_run_id=run.id).one().employee_data
    assert {r['id']: (r['net'], r['total_deductions']) for r in rows} == before

    # Consent on the advance: 400 left counted (< 2,000) -> approval goes through, amounts as reviewed.
    assert ea.set_assignment_consent(w['co'].id, w['owner'].id, w['advance'], True, 'Signed form, HR file 12')
    db.session.commit()
    result = _approve(w, run)
    assert result.success, result.message
    slip = Payslip.query.filter_by(company_id=w['co'].id, payroll_run_id=run.id, employee_id=w['emp'].id).one()
    assert str(slip.net_pay) == str(Decimal(before['C1'][0]))


def test_employee_level_consent_unblocks(app, cap_world):
    w = cap_world
    run = _review(w)
    assert not _approve(w, run).success
    client = _login(app, w['accountant'])
    resp = client.post(
        f'/employees/{w["emp"].id}/deduction-consent', data={'consent_on_file': '1'}, follow_redirects=True
    )
    assert b'Say where the written consent is kept' in resp.data
    client.post(
        f'/employees/{w["emp"].id}/deduction-consent',
        data={'consent_on_file': '1', 'consent_note': 'Signed 2026-09-01, HR file'},
    )
    emp = db.session.get(Employee, w['emp'].id)
    assert emp.deduction_consent_on_file and emp.deduction_consent_recorded_by == w['accountant'].id
    assert AuditLog.query.filter_by(company_id=w['co'].id, action='employee_deduction_consent_changed').count() == 1
    assert _approve(w, db.session.get(PayrollRun, run.id)).success


def test_court_order_alone_is_not_counted(app):
    co = _company()
    owner = _user(co, '911400021', 'owner')
    emp = _employee(co.id, 'K1', salary='3000')
    ea.create_assignment(
        co.id, owner.id, emp, _item(co.id, 'court_order'), value='50', mode='percent_of_net', label='Case'
    )
    db.session.commit()
    w = {'co': co, 'owner': owner}
    run = _review(w)
    assert _approve(w, run).success


def test_itemized_draft_approval_is_blocked_too(app, cap_world):
    from payroll_engine.services.payroll_service import process_payroll

    w = cap_world
    run = PayrollRun(company_id=w['co'].id, period='2026-09', status='review', run_date=RUN_DATE)
    db.session.add(run)
    db.session.flush()
    db.session.add(
        PayrollDraft(
            payroll_run_id=run.id,
            company_id=w['co'].id,
            employee_data=[
                {
                    'id': 'C1',
                    'name': 'Emp C1',
                    'basic': 6000.0,
                    'allowances': 0.0,
                    'gross': 6000.0,
                    'tax': 0.0,
                    'pension_employee': 0.0,
                    'pension_employer': 0.0,
                    'net': 6000.0,
                }
            ],
        )
    )
    db.session.commit()
    result = process_payroll(run, w['co'].id, w['owner'].id, 'owner@test.example', '127.0.0.1')
    assert not result.success and 'Art. 59' in result.message
    assert db.session.get(PayrollRun, run.id).status == 'review'
    assert Payslip.query.filter_by(company_id=w['co'].id, payroll_run_id=run.id).count() == 0
    assignment = db.session.get(PayrollItemAssignment, w['advance'].id)
    assert assignment.remaining_balance is None  # nothing consumed


def test_consent_routes_roles_and_validation(app, cap_world):
    w = cap_world
    emp, advance = w['emp'], w['advance']
    employee_client = _login(app, w['emp_user'])
    assert (
        employee_client.post(
            f'/employees/{emp.id}/pay-items/{advance.id}/consent', data={'consent_on_file': '1', 'consent_note': 'x'}
        ).status_code
        == 403
    )
    owner = _login(app, w['owner'])
    page = owner.get(f'/employees/{emp.id}/pay-items/{advance.id}/edit').data
    assert b'data-testid="consent-card"' in page
    owner.post(
        f'/employees/{emp.id}/pay-items/{advance.id}/consent',
        data={'consent_on_file': '1', 'consent_note': 'HR file 12'},
    )
    a = db.session.get(PayrollItemAssignment, advance.id)
    assert a.deduction_consent_on_file and a.deduction_consent_note == 'HR file 12'
    assert a.deduction_consent_recorded_by == w['owner'].id and a.deduction_consent_recorded_at is not None
    log = AuditLog.query.filter_by(company_id=w['co'].id, action='deduction_consent_changed').one()
    assert log.details['on_file'] is True and log.details['before'] == {'on_file': False, 'note': None}
    assert b'Written Consent' in owner.get(f'/employees/{emp.id}').data
    # Withdraw.
    owner.post(f'/employees/{emp.id}/pay-items/{advance.id}/consent', data={'consent_note': ''})
    db.session.refresh(a)
    assert not a.deduction_consent_on_file
    # Earnings have no consent.
    transport = ea.create_assignment(w['co'].id, None, w['emp'], _item(w['co'].id, 'transport'), value='100')
    db.session.commit()
    with pytest.raises(ea.AssignmentError, match='deductions only'):
        ea.set_assignment_consent(w['co'].id, None, transport, True, 'x')
