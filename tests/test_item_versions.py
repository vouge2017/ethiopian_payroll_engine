"""Versioned pay-item settings with effective dates (catalog PR 4b).

Covers:
* every item (system and company) gets version 1 equal to its row, the
  migration's frozen field list equals the app's, and the SQLite
  downgrade / upgrade backfills version 1 for every item;
* golden equivalence: the PR 3 golden matrix (elements engine + what-if
  previews, ``tests/golden/catalog_caps_golden.json``) is byte-identical
  after label / active versions are recorded, and amounts are identical
  before and after those versions on the dates they cover;
* effective-dated resolution in the engine (tax treatment, exemption caps,
  active flag) for unlocked periods, and the approval snapshot recording the
  version effective on the calculation date;
* the settings page: renames, deactivation and reactivation create versions
  (who, when, what, effective date), effective-date validation, history page
  (owner-only, tenant-scoped, system items visible), delete of unused items;
* guards: versions are immutable and company-scoped, direct ORM changes are
  versioned with overwrite semantics, unscoped version queries raise.
"""

import importlib.util
import json
import pathlib
from datetime import date, timedelta
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask import g

from payroll_engine import create_app, db
from payroll_engine.catalog import seed_company_catalog
from payroll_engine.item_snapshot import capture_run_item_snapshot
from payroll_engine.item_versions import (
    VERSIONED_FIELDS,
    ResolvedItemType,
    record_version,
    resolve_item_types,
    resolve_rows,
    settings_of,
)
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    PayItemType,
    PayItemTypeVersion,
    PayrollItemAssignment,
    PayrollRun,
    User,
    UserCompany,
)
from payroll_engine.models_payroll_elements import ImmutableVersionError
from payroll_engine.payroll_elements import calculate_payroll_from_assignments
from payroll_engine.services import pay_item_settings as svc

REPO = pathlib.Path(__file__).resolve().parents[1]
MIGRATION = REPO / 'migrations' / 'versions' / 'f3a4b5c6d7e8_pay_item_type_version.py'
GOLDEN_TEST = REPO / 'tests' / 'test_catalog_caps_golden.py'
PASSWORD = 'Test1234!'
TODAY = date.today()
FUTURE = TODAY + timedelta(days=5)


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
        yield app
        db.session.remove()
        db.drop_all()


def _company(name):
    co = Company(name=name, billing_status='active', plan_code='standard', paid_until=TODAY + timedelta(days=60))
    db.session.add(co)
    db.session.flush()
    seed_company_catalog(co.id, commit=False)
    db.session.commit()
    return co


def _user(company, phone, role):
    user = User(phone=phone, company_id=company.id, role=role, first_name='Synthetic', last_name='Owner')
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(UserCompany(user_id=user.id, company_id=company.id, role=role))
    db.session.commit()
    return user


@pytest.fixture
def world(app):
    a = _company('Versions A PLC')
    b = _company('Versions B PLC')
    owner = _user(a, '911200001', 'owner')
    return {
        'a': a.id,
        'b': b.id,
        'owner_id': owner.id,
        'owner': owner.phone,
        'accountant': _user(a, '911200002', 'accountant').phone,
        'owner_b': _user(b, '911200003', 'owner').phone,
    }


def _login(app, phone):
    client = app.test_client()
    resp = client.post('/auth/login', data={'login_id': phone, 'password': PASSWORD})
    assert resp.status_code == 302, resp.data[:300]
    return client


@pytest.fixture
def owner(app, world):
    return _login(app, world['owner'])


def _item(company_id, key):
    return PayItemType.query.filter_by(company_id=company_id, key=key).one()


def _versions(item):
    return (
        PayItemTypeVersion.query.filter(
            PayItemTypeVersion.pay_item_type_id == item.id,
            db.or_(PayItemTypeVersion.company_id == item.company_id, PayItemTypeVersion.company_id.is_(None)),
        )
        .order_by(PayItemTypeVersion.version_no)
        .all()
    )


def _employee(company_id, code='E1', salary='10000'):
    emp = Employee(company_id=company_id, employee_id=code, name=f'Emp {code}', basic_salary=Decimal(salary))
    db.session.add(emp)
    db.session.commit()
    return emp


def _assign(company_id, emp, item, amount):
    row = PayrollItemAssignment(
        company_id=company_id, employee_id=emp.id, pay_item_type_id=item.id, fixed_amount=Decimal(amount)
    )
    db.session.add(row)
    db.session.commit()
    return row


def _calc(emp, company_id, for_date):
    return calculate_payroll_from_assignments(emp, company_id, for_date, consume_balances=False)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Version 1 for every item; migration
# ---------------------------------------------------------------------------


def test_every_item_has_version_one_equal_to_its_row(world):
    items = PayItemType.query.filter(
        db.or_(PayItemType.company_id.in_([world['a'], world['b']]), PayItemType.company_id.is_(None))
    ).all()
    assert items
    for item in items:
        versions = _versions(item)
        assert [v.version_no for v in versions] == [item.current_version_no]
        v1 = versions[0]
        assert v1.company_id == item.company_id
        assert settings_of(v1) == settings_of(item), item.key
        assert v1.effective_from == TODAY
        assert v1.changes is None


def test_migration_matches_app_and_single_head():
    mig = _load(MIGRATION, 'mig_f3a4b5c6d7e8')
    assert mig.revision == 'f3a4b5c6d7e8' and mig.down_revision == 'e2f3a4b5c6d7'
    assert mig.VERSIONED_FIELDS == VERSIONED_FIELDS
    model_cols = {c.name for c in PayItemTypeVersion.__table__.columns}
    assert {c.name for c in mig._columns()} == model_cols
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    # Later migrations build on this one (catalog PR 5: a4b5c6d7e8f9).
    assert 'f3a4b5c6d7e8' in {rev.revision for rev in script.walk_revisions(base='base', head=heads[0])}


def _ops(fn):
    conn = db.session.connection()
    with Operations.context(MigrationContext.configure(conn)):
        fn()


def test_migration_downgrade_upgrade_backfills_version_one(world):
    mig = _load(MIGRATION, 'mig_f3a4b5c6d7e8_round_trip')
    transport = _item(world['a'], 'transport')
    svc.rename_item(transport, world['owner_id'], name_en='Transport (fuel)', effective_from=FUTURE, today=FUTURE)
    db.session.commit()
    expected = {
        r.id: settings_of(r)
        for r in PayItemType.query.filter(
            db.or_(PayItemType.company_id.in_([world['a'], world['b']]), PayItemType.company_id.is_(None))
        )
    }
    db.session.expunge_all()

    _ops(mig.downgrade)
    inspector = sa.inspect(db.session.connection())
    assert 'pay_item_type_version' not in inspector.get_table_names()
    assert 'current_version_no' not in {c['name'] for c in inspector.get_columns('pay_item_type')}

    _ops(mig.upgrade)
    db.session.commit()
    db.session.expire_all()
    for item_id, settings in expected.items():
        item = db.session.get(PayItemType, item_id)
        versions = _versions(item)
        assert len(versions) == 1 and versions[0].version_no == 1 and item.current_version_no == 1
        assert versions[0].source == 'migration' and versions[0].changed_by_user_id is None
        assert settings_of(versions[0]) == settings, item.key
        assert versions[0].effective_from == (item.effective_date or item.created_at.date())
    # The renamed label is now version 1 (settings current at migration time).
    assert settings_of(_versions(db.session.get(PayItemType, transport.id))[0])['name_en'] == 'Transport (fuel)'
    assert mig.backfill(db.session.connection()) == 0


# ---------------------------------------------------------------------------
# Golden equivalence (no amount changes)
# ---------------------------------------------------------------------------


@pytest.fixture
def golden_company(app):
    from datetime import datetime

    company = Company(name='Golden Caps Co', leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0))
    db.session.add(company)
    db.session.flush()
    seed_company_catalog(company.id, commit=True)
    return company.id


def _version_every_company_item(company_id):
    """Record label + deactivate/reactivate versions, effective FUTURE, on every company item."""
    for item in PayItemType.query.filter_by(company_id=company_id).all():
        svc.rename_item(
            item,
            None,
            name_en=f'{item.name_en} (renamed)',
            name_am=item.name_am,
            name_om=item.name_om,
            effective_from=FUTURE,
            today=FUTURE,
        )
        if item.is_active and item.key not in svc.IMPORT_MANAGED_KEYS:
            svc.deactivate_item(item, None, today=FUTURE)
            svc.reactivate_item(item, None, today=FUTURE)
    db.session.commit()


@pytest.mark.parametrize('section', ['elements', 'impact'])
def test_golden_matrix_unchanged_with_versions(golden_company, section):
    golden = _load(GOLDEN_TEST, 'golden_caps_for_pr4b')
    expected = json.loads(golden.GOLDEN.read_text())[section]
    _version_every_company_item(golden_company)
    assert PayItemType.query.filter_by(company_id=golden_company, key='transport').one().current_version_no == 4
    actual = golden.SECTIONS[section](golden_company)
    assert sorted(actual) == sorted(expected)
    mismatched = [k for k in expected if actual[k] != expected[k]]
    assert not mismatched, f'{len(mismatched)} {section} scenario(s) changed, first: {mismatched[:3]}'


_LABEL_KEYS = {'item_label', 'item_label_am', 'type_label', 'label'}


def _amounts(value):
    golden = _load(GOLDEN_TEST, 'golden_caps_amounts')
    plain = golden._plain(value)

    def strip(v):
        if isinstance(v, dict):
            return {k: strip(x) for k, x in v.items() if k not in _LABEL_KEYS}
        if isinstance(v, list):
            return [strip(x) for x in v]
        return v

    return strip(plain)


def test_amounts_identical_before_and_after_versions_on_covered_dates(golden_company):
    from payroll_engine.impact import _what_if_employee, virtual_assignment

    def run(for_date):
        out = {}
        for basic in ('1999.99', '8800', '10000', '18000'):
            for transport in ('0', '2200', '3000'):
                emp = _what_if_employee(Decimal(basic), golden_company)
                extras = [virtual_assignment(golden_company, 'basic_salary', Decimal(basic), for_date=for_date)]
                for key, amount in (('transport', transport), ('hardship', '700'), ('housing', '1500')):
                    if Decimal(amount) > 0:
                        extras.append(virtual_assignment(golden_company, key, Decimal(amount), for_date=for_date))
                result = calculate_payroll_from_assignments(
                    emp, golden_company, for_date, extra_items=extras, consume_balances=False
                )
                out[(basic, transport)] = _amounts(result)
        return out

    before = {d: run(d) for d in (TODAY, FUTURE)}
    _version_every_company_item(golden_company)
    after = {d: run(d) for d in (TODAY, FUTURE)}
    assert after == before


# ---------------------------------------------------------------------------
# Effective-dated resolution in the engine
# ---------------------------------------------------------------------------

D1 = date(2026, 9, 15)
D2 = date(2026, 10, 1)


def _backdate_v1(item, when):
    """Test-only: version 1 effective from ``when`` (bypassing the immutability guard)."""
    db.session.execute(
        sa.text('UPDATE pay_item_type_version SET effective_from = :d WHERE pay_item_type_id = :i AND version_no = 1'),
        {'d': when, 'i': item.id},
    )
    db.session.expire_all()


def test_engine_uses_tax_settings_effective_for_the_period(world):
    cid = world['a']
    emp = _employee(cid)
    transport = _item(cid, 'transport')
    _assign(cid, emp, transport, '2000')
    _backdate_v1(transport, date(2026, 1, 1))
    old = _calc(emp, cid, D1)
    assert old['exempt_allowances'] == Decimal('2000.00')

    transport = _item(cid, 'transport')
    transport.tax_treatment = 'taxable'
    record_version(transport, effective_from=D2, source='settings', changes={'tax_treatment': {}})
    db.session.commit()
    assert transport.current_version_no == 2

    before = _calc(emp, cid, D1)  # unlocked period before the change: version 1
    after = _calc(emp, cid, D2)  # on/after the change: version 2 (the row)
    assert before['exempt_allowances'] == Decimal('2000.00') and before == old
    assert after['exempt_allowances'] == Decimal('0.00')
    assert after['taxable'] == before['taxable'] + Decimal('2000.00')
    assert after['gross'] == before['gross']


def test_engine_uses_cap_and_active_flag_effective_for_the_period(world):
    cid = world['a']
    emp = _employee(cid)
    transport = _item(cid, 'transport')
    housing = _item(cid, 'housing')
    _assign(cid, emp, transport, '3000')
    _assign(cid, emp, housing, '1500')
    for it in (transport, housing):
        _backdate_v1(it, date(2026, 1, 1))
    base = _calc(emp, cid, D1)

    transport = _item(cid, 'transport')
    transport.exempt_cap_amount = Decimal('1000')
    record_version(transport, effective_from=D2, source='settings')
    housing = _item(cid, 'housing')
    housing.is_active = False
    record_version(housing, effective_from=D2, source='settings')
    db.session.commit()

    assert _calc(emp, cid, D1) == base
    later = _calc(emp, cid, D2)
    assert 'housing' in {li['item_key'] for li in base['line_items']}
    assert 'housing' not in {li['item_key'] for li in later['line_items']}
    assert later['gross'] == base['gross'] - Decimal('1500.00')
    assert later['exempt_allowances'] == Decimal('1000.00')


def test_resolution_skips_single_version_items_and_views_are_read_only(world):
    cid = world['a']
    items = PayItemType.query.filter_by(company_id=cid).all()
    assert resolve_item_types(items, D1) == {}
    assert resolve_rows(items, D1) == items
    transport = _item(cid, 'transport')
    _backdate_v1(transport, date(2026, 1, 1))
    transport = _item(cid, 'transport')
    transport.name_en = 'Fuel'
    record_version(transport, effective_from=D2, source='settings')
    db.session.commit()
    (view,) = resolve_rows([transport], D1)
    assert isinstance(view, ResolvedItemType) and view.version_no == 1
    assert view.name_en != 'Fuel' and transport.name_en == 'Fuel'
    assert view.key == 'transport' and view.id == transport.id
    with pytest.raises(AttributeError):
        view.name_en = 'x'
    assert resolve_rows([transport], D2) == [transport]


def test_approval_snapshot_records_version_effective_on_calculation_date(world):
    cid = world['a']
    transport = _item(cid, 'transport')
    _backdate_v1(transport, date(2026, 1, 1))
    transport = _item(cid, 'transport')
    transport.tax_treatment = 'taxable'
    record_version(transport, effective_from=D2, source='settings')
    db.session.commit()

    def snap(run_date, period):
        run = PayrollRun(company_id=cid, period=period, status='review', run_date=run_date)
        db.session.add(run)
        db.session.flush()
        row = capture_run_item_snapshot(run, cid, run_date)
        db.session.commit()
        return next(i for i in row.snapshot['items'] if i['key'] == 'transport' and i['company_id'] == cid)

    assert snap(D1, '2019-01')['tax_treatment'] == 'partial'
    assert snap(D2, '2019-02')['tax_treatment'] == 'taxable'


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------


def test_rename_creates_version_with_who_when_what(owner, world):
    item = _item(world['a'], 'housing')
    resp = owner.post(
        f'/settings/pay-items/{item.id}/edit',
        data={'name_en': 'Housing Allowance (new)', 'name_am': item.name_am or '', 'name_om': item.name_om or ''},
    )
    assert resp.status_code == 302
    item = _item(world['a'], 'housing')
    versions = _versions(item)
    assert [v.version_no for v in versions] == [1, 2] and item.current_version_no == 2
    v2 = versions[1]
    assert v2.source == 'settings' and v2.changed_by_user_id == world['owner_id']
    assert v2.effective_from == TODAY
    assert set(v2.changes) == {'name_en'} and v2.changes['name_en']['new'] == 'Housing Allowance (new)'
    assert settings_of(v2) == settings_of(item)
    audit = AuditLog.query.filter_by(company_id=world['a'], action='pay_item_renamed').one()
    assert audit.details['version_no'] == 2 and audit.details['effective_from'] == TODAY.isoformat()


@pytest.mark.parametrize(
    'value, message',
    [
        ((TODAY + timedelta(days=1)).isoformat(), 'cannot be in the future'),
        ((TODAY - timedelta(days=1)).isoformat(), 'cannot be before'),
        ('31/12/2026', 'must be a date'),
    ],
)
def test_rename_effective_date_validation(owner, world, value, message):
    item = _item(world['a'], 'housing')
    resp = owner.post(f'/settings/pay-items/{item.id}/edit', data={'name_en': 'Changed', 'effective_from': value})
    assert resp.status_code == 400 and message in resp.get_data(as_text=True)
    item = _item(world['a'], 'housing')
    assert item.name_en != 'Changed' and len(_versions(item)) == 1


def test_backdated_rename_within_current_version_is_allowed(world):
    item = _item(world['a'], 'housing')
    _backdate_v1(item, date(2026, 1, 1))
    item = _item(world['a'], 'housing')
    svc.rename_item(item, world['owner_id'], name_en='Housing (from Sept)', effective_from='2026-09-11')
    db.session.commit()
    assert _versions(item)[1].effective_from == date(2026, 9, 11)


def test_noop_rename_and_move_create_no_version(owner, world):
    item = _item(world['a'], 'housing')
    owner.post(
        f'/settings/pay-items/{item.id}/edit',
        data={'name_en': item.name_en, 'name_am': item.name_am or '', 'name_om': item.name_om or ''},
    )
    owner.post(f'/settings/pay-items/{item.id}/move', data={'direction': 'down'})
    assert len(_versions(_item(world['a'], 'housing'))) == 1


def test_deactivate_and_reactivate_create_versions(owner, world):
    item = _item(world['a'], 'hardship')
    assert owner.post(f'/settings/pay-items/{item.id}/deactivate').status_code == 302
    assert owner.post(f'/settings/pay-items/{item.id}/reactivate').status_code == 302
    versions = _versions(_item(world['a'], 'hardship'))
    assert [(v.version_no, v.is_active) for v in versions] == [(1, True), (2, False), (3, True)]
    assert versions[1].changes == {'is_active': {'old': True, 'new': False}}
    assert all(v.changed_by_user_id == world['owner_id'] for v in versions[1:])


def test_add_custom_item_records_version_one_with_owner(owner, world):
    resp = owner.post(
        '/settings/pay-items', data={'kind': 'earning', 'key': 'fuel_allowance', 'name_en': 'Fuel Allowance'}
    )
    assert resp.status_code == 302
    (v1,) = _versions(_item(world['a'], 'fuel_allowance'))
    assert v1.source == 'created' and v1.changed_by_user_id == world['owner_id'] and v1.tax_treatment == 'taxable'


def test_history_page_shows_versions(owner, world):
    item = _item(world['a'], 'housing')
    owner.post(f'/settings/pay-items/{item.id}/edit', data={'name_en': 'Housing Two'})
    resp = owner.get(f'/settings/pay-items/{item.id}/history')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'data-version="2"' in html and 'data-version="1"' in html
    assert html.index('data-version="2"') < html.index('data-version="1"')
    assert 'Synthetic Owner' in html and 'Changed on this settings page' in html
    assert 'English name' in html and 'Housing Two' in html and TODAY.isoformat() in html
    assert 'Version History' in html and 'Effective From' in html
    listing = owner.get('/settings/pay-items').get_data(as_text=True)
    assert f'/settings/pay-items/{item.id}/history' in listing


def test_history_access_rules(app, owner, world):
    foreign = _item(world['b'], 'housing')
    assert owner.get(f'/settings/pay-items/{foreign.id}/history').status_code == 404
    system = PayItemType.query.filter_by(company_id=None, key='basic_salary').one()
    resp = owner.get(f'/settings/pay-items/{system.id}/history')
    assert resp.status_code == 200 and 'data-version="1"' in resp.get_data(as_text=True)
    assert owner.post(f'/settings/pay-items/{system.id}/edit', data={'name_en': 'X'}).status_code == 403
    accountant = _login(app, world['accountant'])
    assert accountant.get(f'/settings/pay-items/{system.id}/history').status_code == 403


def test_history_strings_have_amharic_and_oromo_drafts():
    from payroll_engine.i18n import STRINGS
    from payroll_engine.i18n_om import STRINGS_OM

    for key in (
        'version',
        'version_history',
        'effective_from',
        'changed_by',
        'recorded_at',
        'what_changed',
        'current_version',
        'first_version',
    ):
        assert STRINGS.get(key) and STRINGS_OM.get(key), key
    source = (REPO / 'payroll_engine' / 'i18n.py').read_text() + (REPO / 'payroll_engine' / 'i18n_om.py').read_text()
    assert source.count('Catalog PR 4b (version history). DRAFT TRANSLATION, pending native-speaker review.') == 2


def test_delete_unused_custom_item_removes_its_versions(owner, world):
    owner.post('/settings/pay-items', data={'kind': 'earning', 'key': 'fuel_allowance', 'name_en': 'Fuel'})
    item = _item(world['a'], 'fuel_allowance')
    item_id = item.id
    owner.post(f'/settings/pay-items/{item_id}/edit', data={'name_en': 'Fuel 2'})
    assert owner.post(f'/settings/pay-items/{item_id}/delete').status_code == 302
    assert PayItemTypeVersion.query.filter_by(company_id=world['a'], pay_item_type_id=item_id).count() == 0


def test_used_item_still_cannot_be_deleted(owner, world):
    emp = _employee(world['a'])
    owner.post('/settings/pay-items', data={'kind': 'earning', 'key': 'fuel_allowance', 'name_en': 'Fuel'})
    item = _item(world['a'], 'fuel_allowance')
    _assign(world['a'], emp, item, '100')
    owner.post(f'/settings/pay-items/{item.id}/delete')
    assert len(_versions(_item(world['a'], 'fuel_allowance'))) == 1


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_versions_are_immutable(world):
    (v1,) = _versions(_item(world['a'], 'housing'))
    v1.name_en = 'Rewritten history'
    with pytest.raises(ImmutableVersionError):
        db.session.flush()
    db.session.rollback()


def test_version_must_belong_to_items_company(world):
    item = _item(world['a'], 'housing')
    db.session.add(
        PayItemTypeVersion(
            pay_item_type_id=item.id,
            company_id=world['b'],
            version_no=9,
            effective_from=TODAY,
            source='settings',
            **settings_of(item),
        )
    )
    with pytest.raises(ImmutableVersionError, match='belongs to company'):
        db.session.flush()
    db.session.rollback()


def test_unscoped_version_query_raises(world):
    with pytest.raises(RuntimeError, match='TENANT ISOLATION'):
        PayItemTypeVersion.query.all()


def test_direct_orm_change_is_versioned_with_overwrite_semantics(world):
    cid = world['a']
    emp = _employee(cid)
    transport = _item(cid, 'transport')
    _assign(cid, emp, transport, '2000')
    _backdate_v1(transport, date(2026, 1, 1))
    transport = _item(cid, 'transport')
    transport.tax_treatment = 'taxable'  # not through the settings page
    db.session.commit()
    versions = _versions(transport)
    assert [v.version_no for v in versions] == [1, 2] and transport.current_version_no == 2
    assert versions[1].source == 'direct' and versions[1].effective_from == date(2026, 1, 1)
    assert versions[1].changes == {'tax_treatment': {'old': 'partial', 'new': 'taxable'}}
    # Same as overwriting the row before versions existed: every covered date sees it.
    assert _calc(emp, cid, D1)['exempt_allowances'] == Decimal('0.00')
    # Touching a non-versioned column creates no version.
    transport.sort_order = transport.sort_order + 1
    db.session.commit()
    assert len(_versions(transport)) == 2
