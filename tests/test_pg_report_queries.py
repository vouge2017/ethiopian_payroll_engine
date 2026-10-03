"""Report query growth, tenant boundaries and warning preservation on migrated PG."""

import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import event, text

from payroll_engine import db, models
from payroll_engine.evidence import FAIL, collect_evidence
from payroll_engine.exceptions import classify_exceptions
from payroll_engine.models import Company, Employee, PayrollRun, Payslip

pytest_plugins = ['test_pg_encrypted_employee']

pytestmark = pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URL', '').startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL'
)


@pytest.fixture
def report_db(encrypted_employee_db):
    app, company_id, engine, _ = encrypted_employee_db
    companies = [company_id]
    try:
        yield app, company_id, engine, companies
    finally:
        with app.app_context():
            db.session.rollback()
            db.session.remove()
            with engine.begin() as conn:
                for company in companies:
                    for table in ('payslip', 'payroll_run'):
                        conn.execute(text('DELETE FROM ' + table + ' WHERE company_id = :id'), {'id': company})
                    if company != company_id:
                        conn.execute(text('DELETE FROM employee WHERE company_id = :id'), {'id': company})
                        conn.execute(text('DELETE FROM company WHERE id = :id'), {'id': company})


def seed_run(company_id, count):
    run = PayrollRun(company_id=company_id, run_date=date(2026, 9, 1), period='2026-09', status='completed')
    db.session.add(run)
    db.session.flush()
    for index in range(count):
        employee = Employee(
            company_id=company_id,
            employee_id=str(index),
            name='Synthetic ' + str(index),
            basic_salary=10000,
            allowances=0,
            tin='1234567890',
            phone='+251911123456',
            bank_or_telebirr='1000123456789',
        )
        db.session.add(employee)
        db.session.flush()
        db.session.add(
            Payslip(
                company_id=company_id,
                payroll_run_id=run.id,
                employee_id=employee.id,
                gross_salary=10000,
                tax=1500,
                employee_pension=700,
                employer_pension=1100,
                net_pay=7800,
            )
        )
    run_id = run.id
    db.session.commit()
    db.session.remove()
    return run_id


@pytest.mark.parametrize('count', [5, 25])
def test_report_employee_query_count_is_bounded(report_db, count):
    app, company_id, engine, _ = report_db
    with app.app_context():
        run_id = seed_run(company_id, count)
        statements = []

        def record_sql(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, 'before_cursor_execute', record_sql)
        try:
            report = collect_evidence(run_id, company_id, db, models)
        finally:
            event.remove(engine, 'before_cursor_execute', record_sql)
        employee_reads = [
            sql for sql in statements if sql.lstrip().upper().startswith('SELECT') and 'FROM employee ' in sql
        ]
        assert len(employee_reads) <= 3, f'{len(employee_reads)} employee reads for {count} payslips'
        assert report.ready_for_approval
        assert report.total == 8
        assert not [sql for sql in statements if sql.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]


def test_report_warnings_keep_tenant_and_soft_delete_scope(report_db):
    app, company_id, _engine, companies = report_db
    with app.app_context():
        run_id = seed_run(company_id, 1)
        active = Employee.query.filter_by(company_id=company_id, employee_id='0').one()
        active_slip = Payslip.query.filter_by(company_id=company_id, payroll_run_id=run_id, employee_id=active.id).one()
        active_slip.net_pay = Decimal('-1')
        foreign = Company(name='Foreign private report tenant')
        db.session.add(foreign)
        db.session.flush()
        companies.append(foreign.id)
        former = Employee(
            company_id=company_id,
            employee_id='FORMER',
            name='Former local employee',
            basic_salary=10000,
            allowances=0,
            is_deleted=True,
        )
        private = Employee(
            company_id=foreign.id,
            employee_id='PRIVATE',
            name='Foreign private employee',
            basic_salary=10000,
            allowances=0,
        )
        db.session.add_all([former, private])
        db.session.flush()
        # A malformed cross-company FK must not expose the foreign employee's
        # name, even though the current schema permits that relation.
        for employee in (former, private):
            db.session.add(
                Payslip(
                    company_id=company_id,
                    payroll_run_id=run_id,
                    employee_id=employee.id,
                    gross_salary=10000,
                    tax=1500,
                    employee_pension=700,
                    employer_pension=1100,
                    net_pay=Decimal('-1'),
                )
            )
        db.session.commit()
        db.session.remove()
        report = collect_evidence(run_id, company_id, db, models)
        validation = next(signal for signal in report.signals if signal.name == 'No validation errors')
        assert validation.status == FAIL
        assert 'Synthetic 0' in validation.detail
        assert 'Former local employee' not in validation.detail
        assert 'Foreign private employee' not in repr(report)
        exceptions = classify_exceptions(run_id, company_id, db, models)
        negatives = [issue for issue in exceptions.issues if issue.code == 'NEGATIVE_NET_PAY']
        assert len(negatives) == 1
        assert negatives[0].employee_name == 'Synthetic 0'
        # Preserve the current soft-delete policy in this performance slice.
        # Missing historical warnings need their own money-safety repair.
        assert 'Former local employee' not in repr(exceptions)
        assert 'Foreign private employee' not in repr(exceptions)
        assert collect_evidence(run_id, companies[1], db, models).total == 0
