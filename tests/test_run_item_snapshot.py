"""Catalog PR 4a: approval-time pay-item settings snapshots (SQLite).

* Both approval paths (draft/CSV ``process_payroll`` and the worksheet review)
  write one ``PayrollRunItemSnapshot`` in the approval transaction.
* The ERCA ``_pay_item:<key>:taxable`` column of an approved month reads the
  frozen tax treatment, so a later settings edit changes neither that column
  nor the stored payslip. Runs without a snapshot do not use live settings.
* Snapshots are tenant-scoped (TenantQuery), cannot link another company's
  run and are immutable (ORM guard; PostgreSQL triggers in
  test_pg_run_item_snapshot.py).
* Migration e2f3a4b5c6d7: its frozen serialiser equals the app's, it
  backfills completed/locked runs only (``backfilled=True``), and
  downgrade/upgrade round-trips on SQLite.
"""

import importlib.util
import pathlib
from datetime import date
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from payroll_engine import create_app, db
from payroll_engine.catalog import seed_company_catalog
from payroll_engine.item_snapshot import (
    ITEM_COLUMNS,
    build_snapshot,
    run_item_snapshot,
    serialize_item,
    snapshot_item,
)
from payroll_engine.models import (
    Company,
    Employee,
    PayItemType,
    PayrollDraft,
    PayrollItemAssignment,
    PayrollRun,
    PayrollRunItemSnapshot,
    Payslip,
    User,
)
from payroll_engine.models_payroll_elements import ImmutableSnapshotError
from payroll_engine.report_templates import _pay_item_amount

REPO = pathlib.Path(__file__).resolve().parents[1]
MIGRATION = REPO / 'migrations' / 'versions' / 'e2f3a4b5c6d7_payroll_run_item_snapshot.py'
RUN_DATE = date(2026, 9, 1)


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _company(name, phone):
    company = Company(name=name)
    db.session.add(company)
    db.session.flush()
    seed_company_catalog(company.id, commit=False)
    user = User(phone=phone, company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    emp = Employee(employee_id='E1', name='Abebe Kebede', basic_salary=10000, allowances=0, company_id=company.id)
    db.session.add(emp)
    db.session.flush()
    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    housing.tax_treatment = 'taxable'
    db.session.add(
        PayrollItemAssignment(
            company_id=company.id, employee_id=emp.id, pay_item_type_id=housing.id, fixed_amount=Decimal('3000')
        )
    )
    db.session.commit()
    return company, user, emp


@pytest.fixture
def setup(app, monkeypatch):
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args, **kwargs: None)
    return _company('Snapshot PLC', '0911000101')


def _approve_draft(company, user, emp, run_date=RUN_DATE, period='2018-13'):
    from payroll_engine.services.payroll_service import process_payroll

    run = PayrollRun(company_id=company.id, period=period, status='review', run_date=run_date)
    db.session.add(run)
    db.session.flush()
    db.session.add(
        PayrollDraft(
            payroll_run_id=run.id,
            company_id=company.id,
            employee_data=[
                {
                    'id': emp.employee_id,
                    'name': emp.name,
                    'basic': 10000.0,
                    'allowances': 0.0,
                    'gross': 10000.0,
                    'tax': 0.0,
                    'pension_employee': 0.0,
                    'pension_employer': 0.0,
                    'net': 10000.0,
                }
            ],
        )
    )
    db.session.commit()
    result = process_payroll(run, company.id, user.id, 'owner@test.example', '127.0.0.1')
    assert result.success, result.message or result.error
    return run


def _approve_worksheet(company, user):
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.services.worksheet_review import create_review

    run = create_review(company.id, user.id, RUN_DATE)
    db.session.commit()
    result = process_payroll(run, company.id, user.id, 'owner@test.example', '127.0.0.1')
    assert result.success, result.message or result.error
    return run


def _snapshot(company_id, run_id):
    return PayrollRunItemSnapshot.query.filter_by(company_id=company_id, payroll_run_id=run_id).one()


def _payslip(company_id, run_id):
    return Payslip.query.filter_by(company_id=company_id, payroll_run_id=run_id).one()


def _stored(ps):
    return (ps.gross_salary, ps.tax, ps.taxable_income, ps.exempt_allowances, ps.net_pay, ps.line_items)


# ---------------------------------------------------------------------------
# Written at approval (both paths)
# ---------------------------------------------------------------------------


def test_draft_approval_writes_snapshot(setup):
    company, user, emp = setup
    run = _approve_draft(company, user, emp)
    snap = _snapshot(company.id, run.id)
    assert snap.backfilled is False
    assert snap.calculation_date == RUN_DATE  # approval's for_date (run.run_date), unchanged
    assert snap.captured_at is not None
    doc = snap.snapshot
    assert doc['version'] == 1
    visible = PayItemType.query.filter(
        db.or_(PayItemType.company_id == company.id, PayItemType.company_id.is_(None))
    ).all()
    assert {i['id'] for i in doc['items']} == {i.id for i in visible}
    housing = snapshot_item(snap, company.id, 'housing')
    assert housing['tax_treatment'] == 'taxable'
    assert set(housing) >= {
        'id',
        'key',
        'labels',
        'tax_treatment',
        'exempt_cap_amount',
        'exempt_cap_percent',
        'exempt_cap_basis',
        'calculation_method',
        'rate',
        'max_percent_of_net',
        'pensionable',
        'counts_as_art53_wage',
        'is_active',
    }
    assert set(housing['labels']) == {'en', 'am', 'om'}
    transport = snapshot_item(snap, company.id, 'transport')
    assert transport['tax_treatment'] == 'partial' and transport['exempt_cap_amount'] == '2200.00'
    # System rows are recorded but never returned for a company lookup.
    assert any(i['company_id'] is None and i['key'] == 'basic_salary' for i in doc['items'])
    assert snapshot_item(snap, company.id, 'basic_salary') is None
    # The approval did not bump the payslip calculation_context version.
    assert _payslip(company.id, run.id).calculation_context['version'] == 1


def test_worksheet_approval_writes_snapshot(setup):
    company, user, _emp = setup
    run = _approve_worksheet(company, user)
    assert run.status == 'completed'
    snap = _snapshot(company.id, run.id)
    assert snap.backfilled is False
    assert snap.calculation_date == date(2026, 9, 30)  # worksheet rows are calculated for the month end
    assert snapshot_item(snap, company.id, 'housing')['tax_treatment'] == 'taxable'
    assert _payslip(company.id, run.id).calculation_context['version'] == 1


def test_failed_approval_leaves_no_snapshot(setup, monkeypatch):
    company, user, emp = setup

    def boom(*args, **kwargs):
        raise RuntimeError('audit store down')

    monkeypatch.setattr('payroll_engine.services.payroll_service.create_audit_log', boom)
    from payroll_engine.services.payroll_service import process_payroll

    run = PayrollRun(company_id=company.id, period='2018-13', status='review', run_date=RUN_DATE)
    db.session.add(run)
    db.session.flush()
    db.session.add(
        PayrollDraft(
            payroll_run_id=run.id,
            company_id=company.id,
            employee_data=[
                {
                    'id': emp.employee_id,
                    'name': emp.name,
                    'basic': 10000.0,
                    'allowances': 0.0,
                    'gross': 10000.0,
                    'tax': 0.0,
                    'pension_employee': 0.0,
                    'pension_employer': 0.0,
                    'net': 10000.0,
                }
            ],
        )
    )
    db.session.commit()
    run_id = run.id
    result = process_payroll(run, company.id, user.id, 'owner@test.example', '127.0.0.1')
    assert not result.success
    assert PayrollRunItemSnapshot.query.filter_by(company_id=company.id, payroll_run_id=run_id).first() is None
    assert Payslip.query.filter_by(company_id=company.id, payroll_run_id=run_id).first() is None


# ---------------------------------------------------------------------------
# Reports read the frozen tax treatment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('path', ['draft', 'worksheet'])
def test_settings_edit_after_approval_changes_nothing(setup, path):
    company, user, emp = setup
    run = _approve_draft(company, user, emp) if path == 'draft' else _approve_worksheet(company, user)
    ps = _payslip(company.id, run.id)
    before_amount = _pay_item_amount(ps, 'housing', 'taxable')
    before_stored = _stored(ps)
    assert before_amount == Decimal('3000.00')

    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    housing.tax_treatment = 'exempt'
    db.session.commit()
    db.session.expire_all()

    ps = _payslip(company.id, run.id)
    assert _pay_item_amount(ps, 'housing', 'taxable') == before_amount
    assert _stored(ps) == before_stored


def test_item_exempt_at_approval_stays_exempt(setup):
    company, user, emp = setup
    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    housing.tax_treatment = 'exempt'
    db.session.commit()
    run = _approve_draft(company, user, emp)
    housing.tax_treatment = 'taxable'
    db.session.commit()
    assert _pay_item_amount(_payslip(company.id, run.id), 'housing', 'taxable') == 0


def test_run_without_snapshot_does_not_fall_back_to_live_settings(setup):
    company, user, emp = setup
    run = _approve_draft(company, user, emp)
    # A run approved before this PR (and not backfilled) has no snapshot row.
    db.session.delete(_snapshot(company.id, run.id))
    db.session.commit()
    ps = _payslip(company.id, run.id)
    assert run_item_snapshot(company.id, run.id) is None
    assert _pay_item_amount(ps, 'housing', 'taxable') == ''
    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    housing.tax_treatment = 'exempt'
    db.session.commit()
    assert _pay_item_amount(_payslip(company.id, run.id), 'housing', 'taxable') == ''


@pytest.mark.parametrize(('percent', 'expected'), [(None, Decimal('800.00')), (Decimal('25'), '')])
def test_partial_taxable_item_uses_only_reconstructible_snapshot_values(setup, percent, expected):
    company, user, emp = setup
    housing = PayItemType.query.filter_by(company_id=company.id, key='housing').one()
    housing.tax_treatment = 'partial'
    housing.exempt_cap_amount = Decimal('2200')
    housing.exempt_cap_percent = percent
    db.session.commit()
    run = _approve_draft(company, user, emp)
    assert _pay_item_amount(_payslip(company.id, run.id), 'housing', 'taxable') == expected


def test_backfilled_report_discloses_settings_were_not_captured_at_approval(setup):
    import io

    import openpyxl

    from payroll_engine.reports import generate_erca_report

    company, user, emp = setup
    run = _approve_draft(company, user, emp)
    db.session.execute(
        sa.text('UPDATE payroll_run_item_snapshot SET backfilled = true WHERE payroll_run_id = :id'), {'id': run.id}
    )
    db.session.commit()
    db.session.expire_all()
    workbook = openpyxl.load_workbook(io.BytesIO(generate_erca_report([_payslip(company.id, run.id)], company.name)))
    text_cells = [str(cell.value) for row in workbook.active for cell in row if cell.value is not None]
    assert any('backfilled from settings at migration time' in cell for cell in text_cells)


# ---------------------------------------------------------------------------
# Tenancy and immutability (ORM guards)
# ---------------------------------------------------------------------------


def test_snapshot_queries_are_tenant_scoped(setup):
    company, user, emp = setup
    run = _approve_draft(company, user, emp)
    other, _ou, _oe = _company('Other PLC', '0911000102')
    with pytest.raises(RuntimeError, match='TENANT ISOLATION'):
        PayrollRunItemSnapshot.query.all()
    assert run_item_snapshot(other.id, run.id) is None
    assert run_item_snapshot(company.id, run.id) is not None
    # Each company's snapshot lists only its own items plus the system rows.
    doc = _snapshot(company.id, run.id).snapshot
    assert {i['company_id'] for i in doc['items']} == {None, company.id}


def test_snapshot_cannot_point_at_another_companys_run(setup):
    company, user, emp = setup
    run = _approve_draft(company, user, emp)
    other, _ou, _oe = _company('Other PLC', '0911000103')
    db.session.delete(_snapshot(company.id, run.id))
    db.session.commit()
    db.session.add(
        PayrollRunItemSnapshot(
            company_id=other.id, payroll_run_id=run.id, snapshot={'version': 1, 'items': []}, calculation_date=RUN_DATE
        )
    )
    with pytest.raises(ImmutableSnapshotError, match='belongs to company'):
        db.session.flush()
    db.session.rollback()


def test_snapshot_is_immutable(setup):
    company, user, emp = setup
    run = _approve_draft(company, user, emp)
    snap = _snapshot(company.id, run.id)
    snap.snapshot = {'version': 1, 'items': []}
    with pytest.raises(ImmutableSnapshotError, match='immutable'):
        db.session.flush()
    db.session.rollback()
    snap = _snapshot(company.id, run.id)
    snap.backfilled = True
    with pytest.raises(ImmutableSnapshotError):
        db.session.commit()
    db.session.rollback()


def test_one_snapshot_per_run(setup):
    company, user, emp = setup
    run = _approve_draft(company, user, emp)
    db.session.add(
        PayrollRunItemSnapshot(
            company_id=company.id,
            payroll_run_id=run.id,
            snapshot={'version': 1, 'items': []},
            calculation_date=RUN_DATE,
        )
    )
    with pytest.raises(sa.exc.IntegrityError):
        db.session.flush()
    db.session.rollback()


# ---------------------------------------------------------------------------
# Migration e2f3a4b5c6d7 (SQLite; PostgreSQL in test_pg_run_item_snapshot.py)
# ---------------------------------------------------------------------------


def _load_migration():
    spec = importlib.util.spec_from_file_location('mig_e2f3a4b5c6d7', MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ops(fn):
    conn = db.session.connection()
    with Operations.context(MigrationContext.configure(conn)):
        fn()


def test_migration_serialiser_equals_app_serialiser(setup):
    company, _user, _emp = setup
    mig = _load_migration()
    assert mig.down_revision == 'd1e2f3a4b5c6'
    assert mig.ITEM_COLUMNS == ITEM_COLUMNS
    item = PayItemType.query.filter_by(company_id=company.id, key='transport').one()
    item.rate = Decimal('1.5')
    item.effective_date = date(2026, 1, 1)
    db.session.commit()
    orm_rows = PayItemType.query.filter(
        db.or_(PayItemType.company_id == company.id, PayItemType.company_id.is_(None))
    ).all()
    cols = ', '.join(ITEM_COLUMNS)
    raw_rows = [
        dict(r._mapping)
        for r in db.session.execute(
            sa.text(f'SELECT {cols} FROM pay_item_type WHERE company_id = :c OR company_id IS NULL'), {'c': company.id}
        )
    ]
    app_doc = build_snapshot(orm_rows)
    assert mig.build_snapshot(raw_rows) == app_doc
    assert build_snapshot(raw_rows) == app_doc
    assert [mig.serialize_item(r) for r in raw_rows] == [serialize_item(r) for r in raw_rows]
    transport = next(i for i in app_doc['items'] if i['key'] == 'transport')
    assert transport['rate'] == '1.5000' and transport['effective_date'] == '2026-01-01'


def test_migration_downgrade_upgrade_backfills_completed_and_locked_only(setup):
    company, user, emp = setup
    approved = _approve_draft(company, user, emp)
    locked = PayrollRun(company_id=company.id, period='2018-11', status='locked', run_date=date(2026, 7, 1))
    draft = PayrollRun(company_id=company.id, period='2018-12', status='review', run_date=date(2026, 8, 1))
    other, _ou, _oe = _company('Backfill Other PLC', '0911000104')
    other_run = PayrollRun(company_id=other.id, period='2018-11', status='completed', run_date=date(2026, 7, 1))
    db.session.add_all([locked, draft, other_run])
    db.session.commit()
    ids = {'approved': approved.id, 'locked': locked.id, 'draft': draft.id, 'other': other_run.id}
    original = _snapshot(company.id, approved.id).snapshot

    mig = _load_migration()
    _ops(mig.downgrade)
    assert 'payroll_run_item_snapshot' not in sa.inspect(db.session.connection()).get_table_names()

    _ops(mig.upgrade)
    db.session.commit()
    db.session.expire_all()
    rows = {
        r.payroll_run_id: r
        for r in db.session.query(PayrollRunItemSnapshot).filter(PayrollRunItemSnapshot.company_id.isnot(None))
    }
    assert set(rows) == {ids['approved'], ids['locked'], ids['other']}
    assert all(r.backfilled for r in rows.values())
    assert rows[ids['locked']].calculation_date == date(2026, 7, 1)
    assert rows[ids['locked']].company_id == company.id and rows[ids['other']].company_id == other.id
    # Built from the settings current at migration time (unchanged here).
    assert rows[ids['approved']].snapshot == original
    assert {i['company_id'] for i in rows[ids['other']].snapshot['items']} == {None, other.id}
    # Re-running the backfill writes nothing new.
    assert mig.backfill(db.session.connection()) == 0
    # down / up again
    _ops(mig.downgrade)
    _ops(mig.upgrade)
    db.session.commit()
    count = db.session.query(PayrollRunItemSnapshot).filter(PayrollRunItemSnapshot.company_id.isnot(None)).count()
    assert count == 3
    # The report reads the backfilled snapshot.
    assert _pay_item_amount(_payslip(company.id, ids['approved']), 'housing', 'taxable') == Decimal('3000.00')
