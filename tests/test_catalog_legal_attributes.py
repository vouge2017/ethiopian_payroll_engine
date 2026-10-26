"""Catalog PR 3: legal item attributes and centralised exemption caps.

* ``pensionable`` / ``counts_as_art53_wage`` are seeded from one place
  (``catalog.LEGAL_ATTRIBUTE_DEFAULTS`` lists), frozen identically in
  migration d1e2f3a4b5c6, and backfilled onto existing rows.
* They are informational: flipping them changes no payroll, pension or
  settlement amount (unconfirmed legal rules must not change calculations).
* The settings page shows tax treatment, caps and the flags read-only, with a
  "pending legal confirmation" note; nothing can edit them.
* Every exemption-cap number lives in ``payroll_engine.exemption_caps``.
"""

import importlib.util
import pathlib
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from flask import g

from payroll_engine import create_app, db
from payroll_engine import exemption_caps as caps
from payroll_engine.catalog import (
    ART53_EXCLUDED_KEYS,
    ART53_WAGE_KEYS,
    COMPANY_TEMPLATE_ITEMS,
    PENSIONABLE_KEYS,
    SYSTEM_ITEMS,
    legal_attribute_defaults,
    seed_company_catalog,
)
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    EmployeeDeduction,
    FinalSettlement,
    LeaveBalance,
    PayItemType,
    TenantQuery,
    User,
    UserCompany,
)
from payroll_engine.services import pay_item_settings as svc

REPO = pathlib.Path(__file__).resolve().parents[1]
MIGRATION = REPO / 'migrations' / 'versions' / 'd1e2f3a4b5c6_pay_item_legal_attributes.py'
EARNING = 'earning'
PASSWORD = 'Test1234!'


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
    )

    @app.before_request
    def _fresh_login_user():
        g.pop('_login_user', None)

    with app.app_context():
        db.create_all()
        for model in [Employee, EmployeeDeduction, LeaveBalance, FinalSettlement, AuditLog]:
            TenantQuery.register_model(model)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def company(app):
    co = Company(
        name='Legal Attr PLC',
        leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0),
        billing_status='active',
        plan_code='standard',
        paid_until=date.today() + timedelta(days=60),
    )
    db.session.add(co)
    db.session.flush()
    seed_company_catalog(co.id, commit=True)
    return co


def _load_migration():
    spec = importlib.util.spec_from_file_location('mig_d1e2f3a4b5c6', MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ops(fn):
    conn = db.session.connection()
    with Operations.context(MigrationContext.configure(conn)):
        fn()


def _flags(company_id):
    scope = PayItemType.company_id.is_(None) if company_id is None else PayItemType.company_id == company_id
    return {
        key: (bool(p), bool(w))
        for key, p, w in db.session.query(
            PayItemType.key, PayItemType.pensionable, PayItemType.counts_as_art53_wage
        ).filter(scope)
    }


# ---------------------------------------------------------------------------
# Seeded defaults
# ---------------------------------------------------------------------------


def test_seeded_flags_mirror_current_behaviour(company):
    system = _flags(None)
    assert system['basic_salary'] == (True, True)  # pension is on basic salary only
    for key in ('employee_pension', 'employer_pension', 'income_tax'):
        assert system[key] == (False, False)

    template = _flags(company.id)
    for spec in COMPANY_TEMPLATE_ITEMS:
        pensionable, wage = template[spec['key']]
        assert pensionable is False, f'{spec["key"]}: no allowance is pensionable today'
        if spec['classification'] != EARNING:
            assert wage is False, f'{spec["key"]}: only earnings can be wage'
    # Art. 53(2) exclusions are never wage.
    for key in ('transport', 'hardship', 'per_diem'):
        assert template[key] == (False, False)
    for key in ('housing', 'communication', 'general_allowance'):
        assert template[key] == (False, True)


def test_defaults_helper_covers_every_standard_key():
    for spec in SYSTEM_ITEMS + COMPANY_TEMPLATE_ITEMS:
        flags = legal_attribute_defaults(spec['key'], spec['classification'])
        assert set(flags) == {'pensionable', 'counts_as_art53_wage'}
    assert legal_attribute_defaults('basic_salary', 'deduction') == {
        'pensionable': False,
        'counts_as_art53_wage': False,
    }
    assert legal_attribute_defaults('my_custom_bonus', EARNING) == {
        'pensionable': False,
        'counts_as_art53_wage': False,
    }
    assert not (ART53_WAGE_KEYS & ART53_EXCLUDED_KEYS)
    assert PENSIONABLE_KEYS <= ART53_WAGE_KEYS


def test_custom_items_are_not_pensionable_or_wage(company):
    item = svc.create_item(company.id, None, key='fuel_allowance', kind='earning', name_en='Fuel')
    db.session.commit()
    assert (item.pensionable, item.counts_as_art53_wage) == (False, False)
    audit = AuditLog.query.filter_by(company_id=company.id, action='pay_item_created').one()
    assert audit.details['pensionable'] is False and audit.details['counts_as_art53_wage'] is False


# ---------------------------------------------------------------------------
# Migration d1e2f3a4b5c6 (SQLite; PostgreSQL in test_pg_catalog_legal_attributes.py)
# ---------------------------------------------------------------------------


def test_migration_lists_equal_catalog_lists():
    mig = _load_migration()
    assert set(mig.PENSIONABLE_KEYS) == PENSIONABLE_KEYS
    assert set(mig.ART53_WAGE_KEYS) == ART53_WAGE_KEYS
    assert mig.down_revision == '9b4e6d2a8c13'


def test_migration_downgrade_then_upgrade_backfills(company):
    # A custom earning and a non-earning that reuses a wage key must stay false.
    db.session.add(
        PayItemType(
            company_id=company.id,
            key='bonus_x',
            name_en='Bonus',
            classification=EARNING,
            calculation_method='fixed',
            tax_treatment='taxable',
            sort_order=200,
        )
    )
    other = Company(name='Other PLC')
    db.session.add(other)
    db.session.flush()
    db.session.add(
        PayItemType(
            company_id=other.id,
            key='food',
            name_en='Food deduction',
            classification='deduction',
            calculation_method='fixed',
            tax_treatment='taxable',
            sort_order=600,
        )
    )
    db.session.commit()
    before = _flags(company.id)
    before_system = _flags(None)

    mig = _load_migration()
    _ops(mig.downgrade)
    cols = {c['name'] for c in sa.inspect(db.session.connection()).get_columns('pay_item_type')}
    assert 'pensionable' not in cols and 'counts_as_art53_wage' not in cols
    # Partial unique indexes survive (no table rebuild).
    idx = {i['name'] for i in sa.inspect(db.session.connection()).get_indexes('pay_item_type')}
    assert {'uq_pay_item_type_system_key', 'uq_pay_item_type_company_key'} <= idx

    _ops(mig.upgrade)
    db.session.commit()
    db.session.expire_all()
    assert _flags(company.id) == before
    assert _flags(None) == before_system
    assert _flags(company.id)['bonus_x'] == (False, False)
    assert _flags(other.id)['food'] == (False, False)
    # Re-running the backfill is idempotent.
    assert mig.backfill(db.session.connection()) >= 1
    assert _flags(company.id) == before


# ---------------------------------------------------------------------------
# The flags are informational: no amount moves when they change
# ---------------------------------------------------------------------------


def _employee(company):
    emp = Employee(
        company_id=company.id,
        employee_id='LA-1',
        name='Legal Attr',
        basic_salary=Decimal('8800'),
        allowances=Decimal('1500'),
        start_date=date(2021, 3, 15),
    )
    db.session.add(emp)
    db.session.flush()
    return emp


def _amounts(company, emp):
    from payroll_engine.impact import virtual_assignment
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments
    from payroll_engine.services.settlement_service import calculate_settlement
    from payroll_engine.severance import TerminationReason

    for_date = date(2026, 10, 15)
    extras = [
        virtual_assignment(company.id, key, Decimal(amount), for_date=for_date)
        for key, amount in (
            ('basic_salary', '8800'),
            ('transport', '3000'),
            ('housing', '2000'),
            ('hardship', '700'),
            ('per_diem', '900'),
        )
    ]
    pay = calculate_payroll_from_assignments(
        emp, company.id, for_date, extra_items=extras, overtime_entries=[{'hours': 6, 'type': 'day'}]
    )
    settle = calculate_settlement(
        emp,
        TerminationReason.REDUNDANCY,
        date(2026, 7, 31),
        company.id,
        db.session,
        unused_leave_days=Decimal('5'),
        notice_pay=Decimal('3000'),
    )
    keys = ('gross', 'taxable', 'tax', 'pension_employee', 'pension_employer', 'net', 'exempt_allowances')
    settle_keys = ('severance_amount', 'leave_encashment', 'income_tax', 'pension_deduction', 'net_final_payment')
    return {k: pay[k] for k in keys} | {f's.{k}': settle[k] for k in settle_keys}


def test_flipping_flags_changes_no_amount(company):
    emp = _employee(company)
    baseline = _amounts(company, emp)
    PayItemType.query.filter(PayItemType.company_id == company.id).update(
        {PayItemType.pensionable: True, PayItemType.counts_as_art53_wage: True}, synchronize_session=False
    )
    PayItemType.query.filter(PayItemType.company_id.is_(None)).update(
        {PayItemType.pensionable: False, PayItemType.counts_as_art53_wage: False}, synchronize_session=False
    )
    db.session.flush()
    db.session.expire_all()
    assert _amounts(company, emp) == baseline
    # Pension is still exactly 7 % / 11 % of basic salary.
    assert baseline['pension_employee'] == Decimal('616.00')
    assert baseline['pension_employer'] == Decimal('968.00')


# ---------------------------------------------------------------------------
# Settings page: read-only display
# ---------------------------------------------------------------------------


def test_tax_labels(company):
    item = PayItemType.query.filter_by(company_id=company.id, key='transport').one()
    assert svc.tax_label(item) == 'Exempt up to the lower of ETB 2,200 or 25% of basic salary; the rest is taxable'
    hardship = PayItemType.query.filter_by(company_id=company.id, key='hardship').one()
    assert 'no cap is set' in svc.tax_label(hardship)
    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    assert svc.tax_label(housing) == 'Taxable'
    advance = PayItemType.query.filter_by(company_id=company.id, key='advance').one()
    assert svc.tax_label(advance) is None and svc.legal_view(advance) is None
    view = svc.legal_view(housing)
    assert view == {
        'tax': 'Taxable',
        'pensionable': False,
        'counts_as_art53_wage': True,
        'pending_note': 'Pending legal confirmation',
    }


def _login(app, company, phone, role):
    user = User(phone=phone, company_id=company.id, role=role, first_name='Synthetic', last_name='User')
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(UserCompany(user_id=user.id, company_id=company.id, role=role))
    db.session.commit()
    client = app.test_client()
    resp = client.post('/auth/login', data={'login_id': phone, 'password': PASSWORD})
    assert resp.status_code == 302, resp.data[:300]
    return client


@pytest.fixture
def owner(app, company):
    return _login(app, company, '911222333', 'owner')


@pytest.mark.parametrize('role', ['accountant', 'employee'])
def test_page_stays_owner_only(app, company, role):
    client = _login(app, company, '911222344', role)
    assert client.get('/settings/pay-items').status_code in (302, 403)


def test_settings_page_shows_flags_read_only(owner, company):
    resp = owner.get('/settings/pay-items')
    assert resp.status_code == 200, resp.status_code
    html = resp.get_data(as_text=True)
    assert 'id="legal-attributes-note"' in html
    assert 'pending legal confirmation' in html
    assert 'Exempt up to the lower of ETB 2,200 or 25% of basic salary' in html
    assert html.count('Pending legal confirmation') >= len(
        [s for s in COMPANY_TEMPLATE_ITEMS if s['classification'] == EARNING]
    )
    # No form field can set a legal flag.
    assert 'name="pensionable"' not in html and 'name="counts_as_art53_wage"' not in html


def test_posted_flags_are_ignored(owner, company):
    resp = owner.post(
        '/settings/pay-items',
        data={
            'kind': 'earning',
            'key': 'risk_pay',
            'name_en': 'Risk pay',
            'pensionable': '1',
            'counts_as_art53_wage': '1',
        },
    )
    assert resp.status_code in (200, 302)
    item = PayItemType.query.filter_by(company_id=company.id, key='risk_pay').one()
    assert (item.pensionable, item.counts_as_art53_wage) == (False, False)
    # Renaming a template item cannot change its flags either.
    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    owner.post(
        f'/settings/pay-items/{housing.id}/edit',
        data={'name_en': 'Housing', 'pensionable': '1', 'counts_as_art53_wage': '0'},
    )
    db.session.expire_all()
    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    assert (housing.pensionable, housing.counts_as_art53_wage) == (False, True)


# ---------------------------------------------------------------------------
# One source of truth for exemption caps
# ---------------------------------------------------------------------------


def test_transport_cap_is_defined_once_and_seeded_from_it(company):
    assert (caps.TRANSPORT.cap_amount, caps.TRANSPORT.cap_percent) == (Decimal('2200'), Decimal('25'))
    row = PayItemType.query.filter_by(company_id=company.id, key='transport').one()
    assert (row.exempt_cap_amount, row.exempt_cap_percent, row.exempt_cap_basis) == (
        caps.TRANSPORT.cap_amount,
        caps.TRANSPORT.cap_percent,
        caps.TRANSPORT.cap_basis,
    )
    from payroll_engine.services import allowance_service

    assert Decimal('2200') == allowance_service.TRANSPORT_EXEMPT_CAP_ETB
    assert Decimal('0.25') == allowance_service.TRANSPORT_EXEMPT_CAP_PERCENT
    assert Decimal('25') == allowance_service.TRANSPORT_EXEMPT_CAP_PERCENT_OF_BASIC


@pytest.mark.parametrize(
    'path',
    [
        'payroll_engine/services/allowance_service.py',
        'payroll_engine/catalog.py',
        'payroll_engine/payroll_elements.py',
        'payroll_engine/impact.py',
        'payroll_engine/employees_bp.py',
        'payroll_engine/models.py',
    ],
)
def test_no_cap_literals_outside_exemption_caps(path):
    source = (REPO / path).read_text()
    code = '\n'.join(line.split('#', 1)[0] for line in source.splitlines())
    assert not re.search(r"Decimal\(['\"](2200|2,200|255|0\.25|0\.04|600)['\"]\)", code), path


def test_home_to_work_cap_is_defined_but_never_applied():
    assert caps.HOME_TO_WORK_TRANSPORT.applied is False
    assert caps.HOME_TO_WORK_TRANSPORT.status == caps.STATUS_PENDING_LEGAL_CONFIRMATION
    keys = {s['key'] for s in SYSTEM_ITEMS + COMPANY_TEMPLATE_ITEMS}
    assert 'home_to_work_transport' not in keys
    for path in (REPO / 'payroll_engine').rglob('*.py'):
        if path.name == 'exemption_caps.py':
            continue
        assert 'HOME_TO_WORK_TRANSPORT' not in path.read_text(), path


def test_legacy_per_diem_cap_is_unchanged():
    # min(max(255 x 30, 4 % of basic), 2,200): the flat 2,200 for any real salary.
    for basic in ('0', '5000', '55000', '191250', '500000'):
        assert caps.LEGACY_PER_DIEM.cap(Decimal(basic)) == Decimal('2200')
    assert caps.LEGACY_PER_DIEM.status == caps.STATUS_LEGACY_UNREVIEWED


def test_lower_of_caps():
    d = Decimal
    assert caps.lower_of_caps(d('3000'), d('2200'), d('25'), d('5000')) == d('1250.00')
    assert caps.lower_of_caps(d('3000'), d('2200'), d('25'), d('18000')) == d('2200')
    assert caps.lower_of_caps(d('1000'), d('2200'), None, d('0')) == d('1000')
    assert caps.lower_of_caps(d('2000'), None, d('25'), d('3333.33')) == d('833.33')
    assert caps.lower_of_caps(d('2000'), None, None, d('5000')) is None
