"""Actual worksheet HTTP handlers against a real Alembic-migrated database."""

import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import config
from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, User
from payroll_engine.payroll import calculate_payroll

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


class Inputs(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and 'name' in attrs:
            self.values[attrs['name']] = attrs.get('value', '')


@pytest.fixture
def worksheet(monkeypatch, tmp_path):
    monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', PG_URL)
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    # Unrelated automatic retention/nudges are not part of this money slice.
    monkeypatch.setattr('payroll_engine.services.proactive.prepare_monthly_draft', lambda *args: None)
    monkeypatch.setattr('payroll_engine.services.proactive.send_compliance_nudges', lambda *args: None)
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    app.before_request_funcs[None] = [
        f for f in app.before_request_funcs.get(None, []) if f.__name__ != 'daily_retention_purge'
    ]
    cfg = Config(str(Path(__file__).resolve().parents[1] / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(Path(__file__).resolve().parents[1] / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', PG_URL)
    with app.app_context():
        command.upgrade(cfg, 'head')
        company = Company(name='Worksheet ' + uuid4().hex)
        foreign = Company(name='Foreign worksheet ' + uuid4().hex)
        db.session.add_all([company, foreign])
        db.session.flush()
        owner = User(company_id=company.id, email=uuid4().hex + '@example.invalid', role='owner')
        owner.set_password('Synthetic1!')
        employee = Employee(
            company_id=company.id,
            employee_id='SHEET1',
            name='Synthetic monthly',
            basic_salary=10000,
            allowances=2000,
            bank_or_telebirr='cbe:1000123456789',
            tin='1234567890',
        )
        other = Employee(
            company_id=foreign.id, employee_id='FOREIGN', name='Foreign private name', basic_salary=10000, allowances=0
        )
        db.session.add_all([owner, employee, other])
        db.session.commit()
        ids = dict(company=company.id, foreign=foreign.id, user=owner.id, employee=employee.id, other=other.id)
        engine = db.engine
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(ids['user'])
        session['_fresh'] = True
        session['active_company_id'] = ids['company']
    try:
        yield app, client, ids, engine, cfg
    finally:
        with app.app_context():
            db.session.rollback()
            db.session.remove()
            with engine.begin() as conn:
                # Delete only these two newly-created synthetic tenants.
                tables = [
                    'payslip_generation_job',
                    'payroll_preview',
                    'payroll_draft',
                    'payroll_validation_result',
                    'payslip',
                    'payroll_run',
                    'employee_deduction',
                    'spreadsheet_input',
                    'overtime_entry',
                    'leave',
                    'notification',
                    'audit_log',
                    'payroll_item_assignment',
                    'pay_item_type',
                    'user_company',
                    'employee',
                    'user',
                ]
                for table in tables:
                    if table == 'payroll_validation_result':
                        conn.execute(
                            text(
                                'DELETE FROM payroll_validation_result WHERE payroll_run_id IN (SELECT id FROM payroll_run WHERE company_id IN (:a, :b))'
                            ),
                            {'a': ids['company'], 'b': ids['foreign']},
                        )
                        continue
                    if conn.execute(text('SELECT to_regclass(:table)'), {'table': table}).scalar():
                        conn.execute(
                            text('DELETE FROM "' + table + '" WHERE company_id IN (:a, :b)'),
                            {'a': ids['company'], 'b': ids['foreign']},
                        )
                conn.execute(
                    text('DELETE FROM company WHERE id IN (:a, :b)'), {'a': ids['company'], 'b': ids['foreign']}
                )


def form(ids, **changes):
    prefix = f'emp_{ids["employee"]}_'
    data = {
        'emp_id': str(ids['employee']),
        'period_start': date.today().replace(day=1).isoformat(),
        'action': 'calculate',
    }
    data.update(
        {prefix + key: '0' for key in ('ot_day', 'ot_night', 'ot_holiday', 'ot_rest', 'absences', 'advance', 'bonus')}
    )
    data.update({prefix + key: value for key, value in changes.items()})
    return data


def test_save_recalculate_applies_bonus_absences_and_survives_reload(worksheet):
    _, client, ids, engine, _ = worksheet
    response = client.post('/payroll/spreadsheet', data=form(ids, bonus='900.50', absences='2'), follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    inputs = Inputs(html).values
    assert Decimal(inputs[f'emp_{ids["employee"]}_bonus']) == Decimal('900.50')
    assert Decimal(inputs[f'emp_{ids["employee"]}_absences']) == 2
    expected = calculate_payroll(10000, Decimal('2900.50'), sick_leave_reduction=Decimal('800'))
    row = next(row for row in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S) if 'Synthetic monthly' in row)
    for key in ('gross', 'tax', 'net'):
        assert f'{expected[key]:,.2f}' in row
    reloaded = Inputs(client.get('/payroll/spreadsheet').get_data(as_text=True)).values
    assert reloaded[f'emp_{ids["employee"]}_bonus'] == inputs[f'emp_{ids["employee"]}_bonus']
    with engine.connect() as conn:
        saved = conn.execute(
            text('SELECT bonus, absence_days FROM spreadsheet_input WHERE company_id=:c AND employee_id=:e'),
            {'c': ids['company'], 'e': ids['employee']},
        ).one()
        assert saved == (Decimal('900.50'), 2)


@pytest.mark.parametrize(
    'field,value', [('bonus', 'NaN'), ('bonus', '-1'), ('bonus', '1.001'), ('absences', '1.5'), ('absences', '31')]
)
def test_invalid_adjustment_rejects_entire_save(worksheet, field, value):
    _, client, ids, engine, _ = worksheet
    response = client.post('/payroll/spreadsheet', data=form(ids, **{field: value, 'ot_day': '4'}))
    assert response.status_code == 400
    assert 'SHEET1' in response.get_data(as_text=True)
    with engine.connect() as conn:
        assert (
            conn.execute(
                text('SELECT count(*) FROM overtime_entry WHERE company_id=:id'), {'id': ids['company']}
            ).scalar()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id=:id AND action LIKE 'payroll.%saved'"),
                {'id': ids['company']},
            ).scalar()
            == 0
        )


def test_foreign_employee_rejects_batch_without_writes(worksheet):
    _, client, ids, engine, _ = worksheet
    data = form(ids, bonus='900', ot_day='4')
    data['emp_id'] = [str(ids['employee']), str(ids['other'])]
    response = client.post('/payroll/spreadsheet', data=data)
    assert response.status_code == 404
    assert 'Foreign private name' not in response.get_data(as_text=True)
    with engine.connect() as conn:
        assert (
            conn.execute(
                text('SELECT count(*) FROM overtime_entry WHERE company_id IN (:a,:b)'),
                {'a': ids['company'], 'b': ids['foreign']},
            ).scalar()
            == 0
        )


def test_saved_advance_is_not_reset_by_unrelated_edit(worksheet):
    _, client, ids, engine, _ = worksheet
    assert client.post('/payroll/spreadsheet', data=form(ids, advance='500')).status_code == 302
    html = client.get('/payroll/spreadsheet').get_data(as_text=True)
    advance = Inputs(html).values[f'emp_{ids["employee"]}_advance']
    assert Decimal(advance) == 500
    assert client.post('/payroll/spreadsheet', data=form(ids, ot_day='4', advance=advance)).status_code == 302
    with engine.connect() as conn:
        assert (
            conn.execute(
                text('SELECT fixed_amount FROM payroll_item_assignment WHERE employee_id=:id AND is_active'),
                {'id': ids['employee']},
            ).scalar_one()
            == 500
        )


def test_repeated_and_concurrent_saves_have_one_input_and_change_audit(worksheet):
    app, client, ids, engine, _ = worksheet

    def save():
        request_client = app.test_client()
        with request_client.session_transaction() as session:
            session['_user_id'] = str(ids['user'])
            session['_fresh'] = True
            session['active_company_id'] = ids['company']
        return request_client.post('/payroll/spreadsheet', data=form(ids, bonus='500', absences='1')).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: save(), range(2))) == [302, 302]
    assert client.post('/payroll/spreadsheet', data=form(ids, bonus='500', absences='1')).status_code == 302
    with engine.connect() as conn:
        assert (
            conn.execute(
                text('SELECT count(*) FROM spreadsheet_input WHERE company_id=:id'), {'id': ids['company']}
            ).scalar()
            == 1
        )
        audits = conn.execute(
            text("SELECT details FROM audit_log WHERE company_id=:id AND action='payroll.worksheet_inputs_saved'"),
            {'id': ids['company']},
        ).all()
        assert len(audits) == 1
        assert Decimal(audits[0][0]['new']['bonus']) == 500
        assert audits[0][0]['new']['absence_days'] == 1


def test_audit_failure_rolls_back_inputs_and_overtime(worksheet, monkeypatch):
    _, client, ids, engine, _ = worksheet

    def reject(*args, **kwargs):
        raise RuntimeError('synthetic audit unavailable')

    monkeypatch.setattr('payroll_engine.services.worksheet.create_audit_log', reject)
    with pytest.raises(RuntimeError, match='synthetic audit unavailable'):
        client.post('/payroll/spreadsheet', data=form(ids, bonus='500', ot_day='4'))
    with engine.connect() as conn:
        for table in ('spreadsheet_input', 'overtime_entry'):
            assert (
                conn.execute(
                    text('SELECT count(*) FROM ' + table + ' WHERE company_id=:id'), {'id': ids['company']}
                ).scalar()
                == 0
            )


def test_stale_month_and_daily_worker_adjustments_are_rejected(worksheet):
    app, client, ids, engine, _ = worksheet
    data = form(ids, bonus='500')
    data['period_start'] = '2000-01-01'
    assert client.post('/payroll/spreadsheet', data=data).status_code == 400
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.employee_type = 'daily'
        employee.daily_rate = 500
        db.session.commit()
    response = client.post('/payroll/spreadsheet', data=form(ids, bonus='500'))
    assert response.status_code == 400
    assert 'monthly employees only' in response.get_data(as_text=True)
    with engine.connect() as conn:
        assert (
            conn.execute(
                text('SELECT count(*) FROM spreadsheet_input WHERE company_id=:id'), {'id': ids['company']}
            ).scalar()
            == 0
        )


def test_database_enforces_tenant_ownership_and_monthly_uniqueness(worksheet):
    _, _, ids, engine, _ = worksheet
    values = {'c': ids['company'], 'e': ids['other'], 'p': date.today().replace(day=1)}
    insert = text('INSERT INTO spreadsheet_input (company_id, employee_id, period_start) VALUES (:c,:e,:p)')
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert, values)
    values['e'] = ids['employee']
    with engine.begin() as conn:
        conn.execute(insert, values)
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert, values)


def test_real_revision_rollback_preserves_employees_and_refuses_saved_inputs(worksheet):
    app, client, ids, engine, cfg = worksheet
    with app.app_context():
        db.session.remove()
        command.downgrade(cfg, 'f4a5b6c7d8ef')
        with engine.connect() as conn:
            assert (
                conn.execute(text('SELECT count(*) FROM employee WHERE id=:id'), {'id': ids['employee']}).scalar() == 1
            )
        command.upgrade(cfg, 'head')
    assert client.post('/payroll/spreadsheet', data=form(ids, bonus='500')).status_code == 302
    with app.app_context():
        db.session.remove()
        with pytest.raises(RuntimeError, match='saved worksheet inputs must be preserved'):
            command.downgrade(cfg, 'f4a5b6c7d8ef')
    with engine.connect() as conn:
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'f4a5b6c7d8f0'
        assert (
            conn.execute(
                text('SELECT bonus FROM spreadsheet_input WHERE company_id=:id'), {'id': ids['company']}
            ).scalar_one()
            == 500
        )


def test_autosave_preserves_saved_manual_adjustments_and_advance(worksheet):
    _, client, ids, engine, _ = worksheet
    assert (
        client.post('/payroll/spreadsheet', data=form(ids, bonus='500', absences='2', advance='300')).status_code == 302
    )
    # Unsaved bonus/days must not be committed by the OT-only autosave.
    response = client.post(
        '/payroll/spreadsheet/autosave', data=form(ids, bonus='900', absences='4', advance='300', ot_day='4')
    )
    assert response.status_code == 200
    with engine.connect() as conn:
        assert conn.execute(
            text('SELECT bonus, absence_days FROM spreadsheet_input WHERE company_id=:id'), {'id': ids['company']}
        ).one() == (Decimal('500'), 2)
        assert (
            conn.execute(
                text('SELECT hours FROM overtime_entry WHERE company_id=:id'), {'id': ids['company']}
            ).scalar_one()
            == 4
        )
        assert (
            conn.execute(
                text('SELECT fixed_amount FROM payroll_item_assignment WHERE employee_id=:id AND is_active'),
                {'id': ids['employee']},
            ).scalar_one()
            == 300
        )


@pytest.mark.parametrize('anonymous', [True, False])
def test_anonymous_and_employee_roles_cannot_save_money_inputs(worksheet, anonymous):
    app, client, ids, engine, _ = worksheet
    if anonymous:
        client = app.test_client()
    else:
        with app.app_context():
            db.session.get(User, ids['user']).role = 'employee'
            db.session.commit()
    response = client.post('/payroll/spreadsheet', data=form(ids, bonus='500'))
    assert response.status_code == (302 if anonymous else 403)
    with engine.connect() as conn:
        assert (
            conn.execute(
                text('SELECT count(*) FROM spreadsheet_input WHERE company_id=:id'), {'id': ids['company']}
            ).scalar()
            == 0
        )
