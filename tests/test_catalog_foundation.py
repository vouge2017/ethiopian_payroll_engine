"""Catalog foundation: every company has a pay-item catalog; the elements tables are tenant-isolated.

Covers PR 1 of the pay-item catalog plan:
  * seed_company_catalog is the single idempotent seeder, called at company creation;
  * the b7c1d2e3f4a5 data migration backfills existing companies and refuses
    to run over cross-company assignments;
  * routes re-seed a missing catalog on demand instead of asking for a CLI run;
  * PayItemType / PayrollItemAssignment queries go through TenantQuery;
  * an assignment can never link another company's employee or pay item.
"""

import importlib.util
import pathlib
from decimal import Decimal

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from helpers import register_company

from payroll_engine import create_app, db
from payroll_engine.catalog import (
    COMPANY_TEMPLATE_ITEMS,
    SYSTEM_ITEMS,
    migrate_pay_items,
    seed_company_catalog,
    seed_company_templates,
    seed_system_items,
)
from payroll_engine.models import Company, Employee, PayItemType, PayrollItemAssignment
from payroll_engine.models_payroll_elements import CrossTenantAssignmentError, check_assignment_tenancy

TEMPLATE_KEYS = {s['key'] for s in COMPANY_TEMPLATE_ITEMS}
SYSTEM_KEYS = {s['key'] for s in SYSTEM_ITEMS}
MIGRATION = (
    pathlib.Path(__file__).resolve().parents[1] / 'migrations' / 'versions' / 'b7c1d2e3f4a5_seed_pay_item_catalog.py'
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _company(name):
    co = Company(name=name)
    db.session.add(co)
    db.session.flush()
    return co


def _company_keys(company_id):
    return [k for (k,) in db.session.query(PayItemType.key).filter(PayItemType.company_id == company_id).all()]


def _system_keys():
    return [k for (k,) in db.session.query(PayItemType.key).filter(PayItemType.company_id.is_(None)).all()]


def _employee(company, code):
    emp = Employee(company_id=company.id, employee_id=code, name=f'Emp {code}', phone='0912345670', basic_salary=5000)
    db.session.add(emp)
    db.session.flush()
    return emp


def _load_migration():
    spec = importlib.util.spec_from_file_location('mig_b7c1d2e3f4a5', MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_upgrade(module):
    conn = db.session.connection()
    ctx = MigrationContext.configure(conn)
    with Operations.context(ctx):
        module.upgrade()


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def test_seed_company_catalog_gives_full_catalog(app):
    co = _company('Fresh PLC')
    result = seed_company_catalog(co.id)
    assert result['created'] == len(COMPANY_TEMPLATE_ITEMS)
    assert sorted(_company_keys(co.id)) == sorted(TEMPLATE_KEYS)
    assert sorted(_system_keys()) == sorted(SYSTEM_KEYS)


def test_seeding_is_idempotent_and_preserves_customisation(app):
    co = _company('Idem PLC')
    seed_company_catalog(co.id)
    transport = PayItemType.query.filter_by(company_id=co.id, key='transport').one()
    transport.name_en = 'Fuel Allowance'
    transport.rate = Decimal('321')
    db.session.commit()

    again = seed_company_catalog(co.id)
    assert again == {'system_created': 0, 'created': 0, 'skipped': len(COMPANY_TEMPLATE_ITEMS)}
    assert seed_system_items() == {'created': 0, 'skipped': len(SYSTEM_ITEMS)}
    assert seed_company_templates(co.id)['created'] == 0
    keys = _company_keys(co.id)
    assert len(keys) == len(set(keys)) == len(TEMPLATE_KEYS)
    assert len(_system_keys()) == len(SYSTEM_KEYS)
    transport = PayItemType.query.filter_by(company_id=co.id, key='transport').one()
    assert (transport.name_en, transport.rate) == ('Fuel Allowance', Decimal('321'))


def test_seeding_fills_only_missing_keys(app):
    co = _company('Partial PLC')
    seed_company_catalog(co.id)
    PayItemType.query.filter_by(company_id=co.id, key='housing').delete()
    db.session.commit()
    assert seed_company_catalog(co.id)['created'] == 1
    assert sorted(_company_keys(co.id)) == sorted(TEMPLATE_KEYS)


def test_migrate_pay_items_cli_function_uses_same_seeder(app):
    a, b = _company('A PLC'), _company('B PLC')
    seed_company_catalog(a.id)
    counts = migrate_pay_items()
    assert counts['companies'] == 2
    assert counts['items_created'] == len(TEMPLATE_KEYS)
    assert sorted(_company_keys(b.id)) == sorted(TEMPLATE_KEYS)


def test_signup_creates_company_with_catalog(app):
    client = app.test_client()
    register_company(
        client,
        data={
            'company_name': 'Signup Catalog PLC',
            'phone': '911555111',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
        },
    )
    co = Company.query.filter_by(name='Signup Catalog PLC').one()
    assert sorted(_company_keys(co.id)) == sorted(TEMPLATE_KEYS)
    assert sorted(_system_keys()) == sorted(SYSTEM_KEYS)


def test_demo_company_has_catalog(app):
    from payroll_engine.demo import create_demo_data

    company, *_ = create_demo_data()
    assert set(_company_keys(company.id)) >= TEMPLATE_KEYS


# ---------------------------------------------------------------------------
# On-demand fallback (replaces "Run flask migrate-pay-items")
# ---------------------------------------------------------------------------


def test_assignable_item_seeds_missing_catalog_on_demand(app, monkeypatch):
    from payroll_engine import employees_bp

    co = _company('Legacy PLC')
    db.session.commit()
    assert _company_keys(co.id) == []
    monkeypatch.setattr(employees_bp, '_company_id', lambda: co.id)
    with app.test_request_context('/'):
        item = employees_bp.assert_assignable_item('transport')
    assert item is not None and item.company_id == co.id and item.key == 'transport'
    assert sorted(_company_keys(co.id)) == sorted(TEMPLATE_KEYS)


def test_company_pay_items_seeds_empty_catalog(app, monkeypatch):
    from payroll_engine import employees_bp

    co = _company('Empty PLC')
    db.session.commit()
    monkeypatch.setattr(employees_bp, '_company_id', lambda: co.id)
    with app.test_request_context('/'):
        items = employees_bp.company_pay_items()
    assert {i.key for i in items} == TEMPLATE_KEYS


def test_unknown_key_flashes_without_cli_hint(app, monkeypatch):
    from flask import get_flashed_messages

    from payroll_engine import employees_bp

    co = _company('Unknown PLC')
    seed_company_catalog(co.id)
    monkeypatch.setattr(employees_bp, '_company_id', lambda: co.id)
    with app.test_request_context('/'):
        assert employees_bp.assert_assignable_item('no_such_item') is None
        messages = get_flashed_messages()
    assert messages and 'migrate-pay-items' not in messages[0]


# ---------------------------------------------------------------------------
# Data migration
# ---------------------------------------------------------------------------


def test_migration_seeds_existing_companies_idempotently(app):
    a, b = _company('Old A'), _company('Old B')
    seed_company_templates(a.id)  # a already has its catalog, b has none
    db.session.commit()
    mig = _load_migration()

    _run_upgrade(mig)
    db.session.commit()
    assert sorted(_company_keys(a.id)) == sorted(TEMPLATE_KEYS)
    assert sorted(_company_keys(b.id)) == sorted(TEMPLATE_KEYS)
    assert sorted(_system_keys()) == sorted(SYSTEM_KEYS)

    assert mig.seed_catalog(db.session.connection()) == 0  # second run: nothing new
    _run_upgrade(mig)
    assert len(_company_keys(b.id)) == len(TEMPLATE_KEYS)

    # Rows seeded by SQL load through the ORM with the right types.
    court = PayItemType.query.filter_by(company_id=b.id, key='court_order').one()
    spec = next(s for s in COMPANY_TEMPLATE_ITEMS if s['key'] == 'court_order')
    assert court.classification == spec['classification']
    assert court.max_percent_of_net == spec.get('max_percent_of_net')
    assert court.is_system is False and court.is_active is True


def test_migration_downgrade_is_noop(app):
    co = _company('Down PLC')
    seed_company_catalog(co.id)
    mig = _load_migration()
    conn = db.session.connection()
    with Operations.context(MigrationContext.configure(conn)):
        mig.downgrade()
    assert len(_company_keys(co.id)) == len(TEMPLATE_KEYS)


def test_migration_refuses_cross_company_assignments(app):
    a, b = _company('Mig A'), _company('Mig B')
    seed_company_catalog(a.id)
    seed_company_catalog(b.id)
    emp_a = _employee(a, 'A1')
    foreign_item = PayItemType.query.filter_by(company_id=b.id, key='transport').one()
    db.session.commit()
    # Simulate a pre-existing bad row written before the guard existed.
    db.session.execute(
        PayrollItemAssignment.__table__.insert().values(
            company_id=a.id, employee_id=emp_a.id, pay_item_type_id=foreign_item.id, is_active=True
        )
    )
    mig = _load_migration()
    bad = mig.find_cross_company_assignments(db.session.connection())
    assert len(bad) == 1 and bad[0][1:] == (a.id, b.id, 'pay_item_type')
    with pytest.raises(RuntimeError, match='Refusing to seed'):
        _run_upgrade(mig)


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


def test_tenant_query_rejects_unscoped_queries(app):
    co = _company('Scope PLC')
    seed_company_catalog(co.id)
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        PayItemType.query.all()
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        PayItemType.query.filter_by(key='transport').first()
    with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
        PayrollItemAssignment.query.filter_by(employee_id=1).all()


def test_tenant_query_allows_company_and_explicit_system_scope(app):
    co = _company('Scope2 PLC')
    seed_company_catalog(co.id)
    assert len(PayItemType.query.filter_by(company_id=co.id).all()) == len(TEMPLATE_KEYS)
    # System items: company_id IS NULL must be stated explicitly.
    assert len(PayItemType.query.filter(PayItemType.company_id.is_(None)).all()) == len(SYSTEM_KEYS)
    assert len(PayItemType.query.filter_by(company_id=None).all()) == len(SYSTEM_KEYS)
    assert PayrollItemAssignment.query.filter_by(company_id=co.id).count() == 0


def test_assignment_to_foreign_pay_item_rejected(app):
    a, b = _company('Iso A'), _company('Iso B')
    seed_company_catalog(a.id)
    seed_company_catalog(b.id)
    emp_a = _employee(a, 'A1')
    foreign = PayItemType.query.filter_by(company_id=b.id, key='transport').one()
    db.session.add(
        PayrollItemAssignment(company_id=a.id, employee_id=emp_a.id, pay_item_type_id=foreign.id, fixed_amount=1)
    )
    with pytest.raises(CrossTenantAssignmentError, match='pay item type'):
        db.session.flush()
    db.session.rollback()


def test_assignment_to_foreign_employee_rejected(app):
    a, b = _company('Iso C'), _company('Iso D')
    seed_company_catalog(a.id)
    emp_b = _employee(b, 'B1')
    own = PayItemType.query.filter_by(company_id=a.id, key='transport').one()
    db.session.add(
        PayrollItemAssignment(company_id=a.id, employee_id=emp_b.id, pay_item_type_id=own.id, fixed_amount=1)
    )
    with pytest.raises(CrossTenantAssignmentError, match='employee'):
        db.session.flush()
    db.session.rollback()


def test_update_repointing_to_foreign_item_rejected(app):
    a, b = _company('Iso E'), _company('Iso F')
    seed_company_catalog(a.id)
    seed_company_catalog(b.id)
    emp_a = _employee(a, 'A1')
    own = PayItemType.query.filter_by(company_id=a.id, key='transport').one()
    foreign = PayItemType.query.filter_by(company_id=b.id, key='housing').one()
    row = PayrollItemAssignment(company_id=a.id, employee_id=emp_a.id, pay_item_type_id=own.id, fixed_amount=1)
    db.session.add(row)
    db.session.commit()
    row.fixed_amount = 2  # unrelated change: no re-check needed, must succeed
    db.session.commit()
    row.pay_item_type_id = foreign.id
    with pytest.raises(CrossTenantAssignmentError):
        db.session.flush()
    db.session.rollback()


def test_own_and_system_items_are_assignable(app):
    co = _company('Iso G')
    seed_company_catalog(co.id)
    emp = _employee(co, 'G1')
    own = PayItemType.query.filter_by(company_id=co.id, key='transport').one()
    system_basic = PayItemType.query.filter_by(company_id=None, key='basic_salary').one()
    check_assignment_tenancy(co.id, emp.id, own.id)
    check_assignment_tenancy(co.id, emp.id, system_basic.id)
    db.session.add_all(
        [
            PayrollItemAssignment(company_id=co.id, employee_id=emp.id, pay_item_type_id=own.id, fixed_amount=1),
            PayrollItemAssignment(
                company_id=co.id, employee_id=emp.id, pay_item_type_id=system_basic.id, fixed_amount=5000
            ),
        ]
    )
    db.session.commit()
    assert PayrollItemAssignment.query.filter_by(company_id=co.id).count() == 2


def test_service_check_rejects_foreign_links(app):
    a, b = _company('Svc A'), _company('Svc B')
    seed_company_catalog(b.id)
    emp_b = _employee(b, 'B1')
    item_b = PayItemType.query.filter_by(company_id=b.id, key='transport').one()
    with pytest.raises(CrossTenantAssignmentError):
        check_assignment_tenancy(a.id, emp_b.id, None)
    with pytest.raises(CrossTenantAssignmentError):
        check_assignment_tenancy(a.id, None, item_b.id)
