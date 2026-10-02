"""Approved worksheet accounting stays reconciled on migrated PostgreSQL."""

import csv
import io
from decimal import Decimal

import pytest
from sqlalchemy import text
from test_pg_spreadsheet_inputs import PG_URL
from test_pg_worksheet_journey import saved_review

from payroll_engine import db
from payroll_engine.accounting_bp import _generate_journal_entries
from payroll_engine.models import Employee, PayrollRun, Payslip, UserCompany

pytest_plugins = ('test_pg_spreadsheet_inputs',)
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def test_approved_accounting_reconciles_and_preserves_employee_facts(worksheet, monkeypatch):
    app, client, ids, engine, rid = saved_review(worksheet, monkeypatch, bonus='900.50', absences='2', advance='500')
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        employee = db.session.get(Employee, ids['employee'])
        employee.name = 'Changed after approval'
        employee.department = 'Changed department'
        employee.basic_salary = Decimal('30000')
        db.session.commit()
        journal = _generate_journal_entries(rid, ids['company'])
        assert journal['balanced']
        assert journal['total_debits'] == journal['total_credits'] == Decimal('13200.50')
        assert journal['entries'][0]['employee_name'] == 'Synthetic monthly'
        assert journal['totals']['gross'] == Decimal('12900.50')
        assert journal['totals']['net'] == Decimal('8590.35')
        lines = {line['account']: line for line in journal['journal_lines']}
        assert lines['5100']['debit'] == Decimal('12100.50')
        assert lines['1300']['credit'] == Decimal('500.00')
    response = client.get(f'/accounting/export/{rid}?format=generic')
    assert response.status_code == 200 and 'attachment' in response.headers['Content-Disposition']
    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
    journal_rows = rows[1 : rows.index([])]
    debits = sum((Decimal(row[5] or '0') for row in journal_rows), Decimal('0'))
    credits = sum((Decimal(row[6] or '0') for row in journal_rows), Decimal('0'))
    assert debits == credits == Decimal('13200.50')
    assert '8590.35' in response.get_data(as_text=True)
    assert 'Changed after approval' not in response.get_data(as_text=True)
    preview = client.get(f'/accounting/preview/{rid}')
    assert preview.status_code == 200
    assert f'/accounting/export/{rid}?format=generic'.encode() in preview.data
    assert client.get(f'/accounting/export/{rid + 100000}').status_code == 404
    with engine.connect() as conn:
        assert conn.execute(
            text('SELECT net_pay FROM payslip WHERE payroll_run_id=:id'), {'id': rid}
        ).scalar_one() == Decimal('8590.35')


@pytest.mark.parametrize('fmt', ['generic', 'quickbooks', 'peachtree', 'xero'])
def test_inconsistent_saved_payroll_cannot_be_exported(worksheet, monkeypatch, fmt):
    _app, client, _ids, engine, rid = saved_review(worksheet, monkeypatch)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with engine.begin() as conn:
        conn.execute(text('UPDATE payslip SET net_pay=net_pay-1 WHERE payroll_run_id=:id'), {'id': rid})
    response = client.get(f'/accounting/export/{rid}?format={fmt}')
    assert response.status_code == 302
    assert response.location.endswith(f'/accounting/preview/{rid}')
    assert 'Content-Disposition' not in response.headers
    preview = client.get(response.location)
    assert b'Accounting export blocked' in preview.data
    assert f'/accounting/export/{rid}?'.encode() not in preview.data


def test_accounting_switches_authorized_company_and_denies_foreign_runs(worksheet, monkeypatch):
    app, client, ids, _engine, rid = saved_review(worksheet, monkeypatch)
    assert client.post('/payroll/approve', data={'run_id': rid, 'password': 'Synthetic1!'}).status_code == 302
    with app.app_context():
        original = db.session.get(PayrollRun, rid)
        foreign = PayrollRun(
            company_id=ids['foreign'],
            run_date=original.run_date,
            period=original.period,
            status='locked',
            source='upload',
        )
        db.session.add(foreign)
        db.session.flush()
        foreign_id = foreign.id
        db.session.add(
            Payslip(
                company_id=ids['foreign'],
                payroll_run_id=foreign_id,
                employee_id=ids['other'],
                gross_salary=10000,
                tax=1500,
                employee_pension=700,
                employer_pension=1100,
                net_pay=7800,
            )
        )
        db.session.commit()
    assert client.get(f'/accounting/export/{foreign_id}').status_code == 404
    assert app.test_client().get(f'/accounting/export/{rid}').status_code == 302
    with app.app_context():
        db.session.add(UserCompany(user_id=ids['user'], company_id=ids['foreign'], role='accountant'))
        db.session.commit()
    with client.session_transaction() as session:
        session['active_company_id'] = ids['foreign']
    foreign_output = client.get(f'/accounting/export/{foreign_id}')
    assert foreign_output.status_code == 200
    assert b'Foreign private name' in foreign_output.data
    assert b'Synthetic monthly' not in foreign_output.data
    assert client.get(f'/accounting/export/{rid}').status_code == 404
    with app.app_context():
        UserCompany.query.filter_by(user_id=ids['user'], company_id=ids['foreign']).delete()
        db.session.commit()
    removed = client.get(f'/accounting/export/{foreign_id}')
    assert removed.status_code == 403 and 'Content-Disposition' not in removed.headers
