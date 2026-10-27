"""PostgreSQL proof for catalog PR 4a (migration e2f3a4b5c6d7, run item snapshots).

* On an isolated database: upgrade to the previous head, seed a company
  catalog (frozen b7c1d2e3f4a5 seeder plus a custom earning) and completed /
  locked / review runs, upgrade to head (table created, completed and locked
  runs backfilled with ``backfilled = true`` from the native-enum catalog),
  then prove the two triggers: a snapshot cannot be updated, and its
  company_id must equal its run's company_id. Dropping the triggers inside a
  rolled-back transaction makes the same statements succeed, so the triggers
  (not some other constraint) are what block them. Deleting a run removes its
  snapshot. Downgrade drops table, triggers and functions; upgrade again
  re-backfills. Single Alembic head.
* On the shared test database: a worksheet approval through the route writes
  the snapshot in the approval transaction, and a raw cross-tenant insert is
  rejected by the trigger.
Requires a disposable TEST_DATABASE_URL.
"""

import importlib.util
import os
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')

REPO = Path(__file__).resolve().parents[1]
PREVIOUS = 'd1e2f3a4b5c6'
REVISION = 'e2f3a4b5c6d7'
TABLE = 'payroll_run_item_snapshot'
TRIGGERS = {'trg_payroll_run_item_snapshot_tenancy', 'trg_payroll_run_item_snapshot_immutable'}
FUNCTIONS = {'payroll_run_item_snapshot_tenancy_guard', 'payroll_run_item_snapshot_immutable_guard'}


@pytest.fixture
def isolated():
    name = 'payroll_pr4a_snap_' + uuid4().hex
    url = sa.engine.make_url(PG_URL).set(database=name)
    control = sa.create_engine(PG_URL, isolation_level='AUTOCOMMIT')
    with control.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    engine = sa.create_engine(url)
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', url.render_as_string(hide_password=False).replace('%', '%%'))
    try:
        yield engine, cfg
    finally:
        engine.dispose()
        with control.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE "{name}"'))
        control.dispose()


def _seed_module():
    path = REPO / 'migrations' / 'versions' / 'b7c1d2e3f4a5_seed_pay_item_catalog.py'
    spec = importlib.util.spec_from_file_location('mig_b7c1_seed_pr4a', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _company(conn, name, now):
    return conn.execute(
        sa.text(
            'INSERT INTO company (name, created_at, billing_status, plan_code) '
            "VALUES (:n, :now, 'active', 'standard') RETURNING id"
        ),
        {'n': name, 'now': now},
    ).scalar_one()


def _run(conn, company_id, status, run_date, period):
    return conn.execute(
        sa.text(
            'INSERT INTO payroll_run (company_id, period, run_date, status, source, disbursement_status, '
            "version_id, created_at) VALUES (:c, :p, :d, :s, 'upload', 'pending', 1, :d) RETURNING id"
        ),
        {'c': company_id, 'p': period, 'd': run_date, 's': status},
    ).scalar_one()


def _objects(engine):
    with engine.connect() as conn:
        tables = set(sa.inspect(conn).get_table_names())
        triggers = {
            r[0]
            for r in conn.execute(
                sa.text(
                    'SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid '
                    'WHERE c.relname = :t AND NOT t.tgisinternal'
                ),
                {'t': TABLE},
            )
        }
        functions = {
            r[0] for r in conn.execute(sa.text('SELECT proname FROM pg_proc WHERE proname LIKE :p'), {'p': TABLE + '%'})
        }
    return tables, triggers, functions


def _snapshots(engine):
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(f'SELECT payroll_run_id, company_id, snapshot, calculation_date, backfilled FROM {TABLE}')
        ).all()
    return {r[0]: r for r in rows}


def test_single_head():
    cfg = Config(str(REPO / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(REPO / 'migrations'))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    # Later migrations build on this one (catalog PR 4b: f3a4b5c6d7e8).
    assert REVISION in {rev.revision for rev in script.walk_revisions(base='base', head=heads[0])}


def test_upgrade_backfills_triggers_guard_and_downgrade_round_trips(isolated):
    engine, cfg = isolated
    command.upgrade(cfg, PREVIOUS)
    assert TABLE not in _objects(engine)[0]
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.begin() as conn:
        company_id = _company(conn, 'PG PR4a Co', now)
        other_id = _company(conn, 'PG PR4a Other', now)
        _seed_module().seed_catalog(conn)
        conn.execute(
            sa.text(
                'INSERT INTO pay_item_type (company_id, key, name_en, classification, calculation_method, '
                'tax_treatment, exempt_cap_amount, sort_order, is_system, is_active, created_at) '
                "VALUES (:c, 'risk_pg', 'Risk', 'earning', 'fixed', 'partial', 600, 200, false, true, :now)"
            ),
            {'c': company_id, 'now': now},
        )
        completed = _run(conn, company_id, 'completed', date(2026, 7, 1), '2018-11')
        locked = _run(conn, company_id, 'locked', date(2026, 8, 1), '2018-12')
        review = _run(conn, company_id, 'review', date(2026, 9, 1), '2018-13')
        foreign = _run(conn, other_id, 'completed', date(2026, 7, 1), '2018-11')

    command.upgrade(cfg, REVISION)
    tables, triggers, functions = _objects(engine)
    assert TABLE in tables and triggers == TRIGGERS and functions == FUNCTIONS
    snaps = _snapshots(engine)
    assert set(snaps) == {completed, locked, foreign}
    assert review not in snaps
    assert all(r.backfilled is True for r in snaps.values())
    assert snaps[locked].calculation_date == date(2026, 8, 1)
    assert snaps[foreign].company_id == other_id
    items = {i['key']: i for i in snaps[completed].snapshot['items'] if i['company_id'] == company_id}
    assert items['risk_pg']['tax_treatment'] == 'partial' and items['risk_pg']['exempt_cap_amount'] == '600.00'
    assert items['transport']['tax_treatment'] == 'partial'
    assert any(i['company_id'] is None and i['key'] == 'basic_salary' for i in snaps[completed].snapshot['items'])
    assert {i['company_id'] for i in snaps[foreign].snapshot['items']} == {None, other_id}
    assert 'risk_pg' not in {i['key'] for i in snaps[foreign].snapshot['items']}

    # Immutable: UPDATE is rejected by the trigger ...
    with pytest.raises(sa.exc.IntegrityError, match='immutable'), engine.begin() as conn:
        conn.execute(sa.text(f'UPDATE {TABLE} SET backfilled = false WHERE payroll_run_id = :r'), {'r': completed})
    # ... and the trigger is what blocks it: without it the same UPDATE succeeds.
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(sa.text(f'DROP TRIGGER trg_payroll_run_item_snapshot_immutable ON {TABLE}'))
        updated = conn.execute(
            sa.text(f'UPDATE {TABLE} SET backfilled = false WHERE payroll_run_id = :r'), {'r': completed}
        ).rowcount
        assert updated == 1
        tx.rollback()

    # Tenancy: a snapshot cannot point at another company's run.
    insert = sa.text(
        f'INSERT INTO {TABLE} (company_id, payroll_run_id, snapshot, calculation_date, backfilled, captured_at) '
        'VALUES (:c, :r, \'{"version": 1, "items": []}\', \'2026-09-01\', false, now())'
    )
    with pytest.raises(sa.exc.IntegrityError, match='belongs to company'), engine.begin() as conn:
        conn.execute(insert, {'c': other_id, 'r': review})
    with engine.connect() as conn:
        tx = conn.begin()
        conn.execute(sa.text(f'DROP TRIGGER trg_payroll_run_item_snapshot_tenancy ON {TABLE}'))
        assert conn.execute(insert, {'c': other_id, 'r': review}).rowcount == 1
        tx.rollback()
    # A matching company is accepted, and the row is unique per run.
    with engine.begin() as conn:
        conn.execute(insert, {'c': company_id, 'r': review})
    with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
        conn.execute(insert, {'c': company_id, 'r': review})
    assert _objects(engine)[1] == TRIGGERS  # rolled-back drops left the triggers in place

    # The snapshot goes with its run.
    with engine.begin() as conn:
        conn.execute(sa.text('DELETE FROM payroll_run WHERE id = :r'), {'r': review})
    assert review not in _snapshots(engine)

    command.downgrade(cfg, PREVIOUS)
    tables, triggers, functions = _objects(engine)
    assert TABLE not in tables and not triggers and not functions

    command.upgrade(cfg, REVISION)
    again = _snapshots(engine)
    assert set(again) == {completed, locked, foreign}
    assert again[completed].snapshot == snaps[completed].snapshot
    assert _objects(engine)[1] == TRIGGERS
    with engine.connect() as conn:
        assert conn.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one() == REVISION


# ---------------------------------------------------------------------------
# Shared database: approval writes the snapshot; raw cross-tenant insert fails
# ---------------------------------------------------------------------------

from test_pg_spreadsheet_inputs import form

pytest_plugins = ('test_pg_spreadsheet_inputs',)


def test_worksheet_approval_writes_snapshot_on_pg(worksheet, monkeypatch):
    _app, client, ids, engine, _cfg = worksheet
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args: None)
    monkeypatch.setattr('payroll_engine.webhooks.fire_webhook', lambda *args, **kwargs: None)
    assert client.post('/payroll/spreadsheet', data=form(ids, bonus='100')).status_code == 302
    response = client.post(
        '/payroll/spreadsheet/review', data={'period_start': date.today().replace(day=1).isoformat()}
    )
    assert response.status_code == 302
    rid = int(response.location.split('/')[-2])
    with engine.connect() as conn:
        assert (
            conn.execute(sa.text(f'SELECT count(*) FROM {TABLE} WHERE payroll_run_id = :r'), {'r': rid}).scalar() == 0
        )
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.connect() as conn:
        status = conn.execute(sa.text('SELECT status FROM payroll_run WHERE id = :r'), {'r': rid}).scalar_one()
        row = conn.execute(
            sa.text(
                f'SELECT company_id, snapshot, calculation_date, backfilled FROM {TABLE} WHERE payroll_run_id = :r'
            ),
            {'r': rid},
        ).one()
    assert status == 'completed'
    assert row.company_id == ids['company'] and row.backfilled is False
    import calendar

    first = date.today().replace(day=1)
    assert row.calculation_date == first.replace(day=calendar.monthrange(first.year, first.month)[1])
    assert row.snapshot['version'] == 1 and row.snapshot['items']
    assert {i['company_id'] for i in row.snapshot['items']} <= {None, ids['company']}

    with pytest.raises(sa.exc.IntegrityError, match='belongs to company'), engine.begin() as conn:
        conn.execute(
            sa.text(
                f'INSERT INTO {TABLE} (company_id, payroll_run_id, snapshot, calculation_date, backfilled, captured_at) '
                "VALUES (:c, :r, '{}', '2026-09-01', false, now())"
            ),
            {'c': ids['foreign'], 'r': rid},
        )
    with pytest.raises(sa.exc.IntegrityError, match='immutable'), engine.begin() as conn:
        conn.execute(sa.text(f"UPDATE {TABLE} SET snapshot = '{{}}' WHERE payroll_run_id = :r"), {'r': rid})
