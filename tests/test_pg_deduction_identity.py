"""PG service regressions: migrated schema, real commits, real row locks.

External PDF/webhook delivery is stubbed; calculation, persistence, audit and
approval guards are real. This does not prove HTTP authorization or every race.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import text

from payroll_engine import _json_serializer, db
from payroll_engine.models import (
    Company,
    Employee,
    EmployeeDeduction,
    PayrollDraft,
    PayrollRun,
    User,
)
from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment
from payroll_engine.services import payroll_service

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(
    not PG_URL.startswith('postgresql'), reason='Requires explicit disposable TEST_DATABASE_URL'
)


@pytest.fixture
def dataset(monkeypatch):
    # The caller supplies an identified disposable DB. Never use DATABASE_URL.
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY='synthetic-only',
        SQLALCHEMY_DATABASE_URI=PG_URL,
        SQLALCHEMY_ENGINE_OPTIONS={
            'json_serializer': lambda value: json.dumps(value, default=_json_serializer),
            'connect_args': {'options': '-c lock_timeout=10000 -c statement_timeout=15000'},
        },
    )
    db.init_app(app)
    Migrate(app, db)
    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args: None)
    monkeypatch.setattr('payroll_engine.webhooks.fire_webhook', lambda *args, **kwargs: None)
    companies = []
    with app.app_context():
        repo = Path(__file__).resolve().parents[1]
        cfg = Config(str(repo / 'migrations/alembic.ini'))
        cfg.set_main_option('script_location', str(repo / 'migrations'))
        cfg.set_main_option('sqlalchemy.url', PG_URL)
        command.upgrade(cfg, 'head')
        company = Company(name='PG identity ' + uuid4().hex)
        foreign = Company(name='PG foreign ' + uuid4().hex)
        db.session.add_all([company, foreign])
        db.session.flush()
        companies.extend([company.id, foreign.id])
        owner = User(email=uuid4().hex + '@example.invalid', role='owner', company_id=company.id)
        owner.set_password('Synthetic1!')
        employee = Employee(
            company_id=company.id, employee_id='IDENTITY', name='Synthetic employee', basic_salary=10000, allowances=0
        )
        foreign_employee = Employee(
            company_id=foreign.id, employee_id='IDENTITY', name='Foreign employee', basic_salary=10000, allowances=0
        )
        db.session.add_all([owner, employee, foreign_employee])
        db.session.flush()
        basic = PayItemType(
            company_id=company.id,
            key='basic_salary',
            name_en='Salary',
            classification='earning',
            calculation_method='fixed',
        )
        loan = PayItemType(
            company_id=company.id, key='loan', name_en='Loan', classification='deduction', calculation_method='fixed'
        )
        db.session.add_all([basic, loan])
        db.session.flush()
        assignment = PayrollItemAssignment(
            company_id=company.id,
            employee_id=employee.id,
            pay_item_type_id=loan.id,
            fixed_amount=100,
            tracking_mode='declining',
            remaining_balance=1000,
            total_to_recover=1000,
            effective_date=date(2026, 1, 1),
        )
        db.session.add(assignment)
        db.session.flush()
        legacy = EmployeeDeduction(
            id=assignment.id,
            company_id=company.id,
            employee_id=employee.id,
            deduction_type='other',
            label='Separate legacy debt',
            amount=20,
            remaining_balance=500,
            total_to_recover=500,
            start_date=date(2026, 1, 1),
        )
        run = PayrollRun(company_id=company.id, run_date=date.today(), period='2026-09', status='review')
        db.session.add_all([legacy, run])
        db.session.flush()
        draft = PayrollDraft(
            company_id=company.id,
            payroll_run_id=run.id,
            employee_data=[
                {
                    'id': 'IDENTITY',
                    'name': 'Synthetic employee',
                    'basic': 10000,
                    'allowances': 0,
                    'gross': 10000,
                    'tax': 0,
                    'pension_employee': 0,
                    'pension_employer': 0,
                    'net': 10000,
                }
            ],
        )
        db.session.add(draft)
        db.session.commit()
        ids = dict(
            company=company.id,
            foreign=foreign.id,
            employee=employee.id,
            foreign_employee=foreign_employee.id,
            user=owner.id,
            run=run.id,
            assignment=assignment.id,
            legacy=legacy.id,
        )
        engine = db.engine
    try:
        yield app, ids, engine
    finally:
        # Delete only this fixture's synthetic tenants, in FK order.
        with app.app_context():
            db.session.rollback()
            db.session.remove()
            with engine.begin() as conn:
                for table in (
                    'payslip_generation_job',
                    'payroll_draft',
                    'notification',
                    'audit_log',
                    'payslip',
                    'payroll_run',
                    'payroll_item_assignment',
                    'employee_deduction',
                    'employee',
                    'pay_item_type',
                    'user_company',
                    'user',
                ):
                    conn.execute(
                        text('DELETE FROM "' + table + '" WHERE company_id IN (:a, :b)'),
                        dict(a=companies[0], b=companies[1]),
                    )
                conn.execute(text('DELETE FROM company WHERE id IN (:a, :b)'), dict(a=companies[0], b=companies[1]))


def approve(app, ids):
    with app.app_context():
        # Same lock contract as the approval route; no mocked Query/session.
        run = PayrollRun.query.filter_by(id=ids['run'], company_id=ids['company']).with_for_update().one()
        return payroll_service.process_payroll(
            run, ids['company'], ids['user'], 'synthetic@example.invalid', '127.0.0.1'
        )


def persisted(engine, ids):
    # Independent connection proves committed DB state, not an ORM identity map.
    with engine.connect() as conn:
        return dict(
            assignment=conn.execute(
                text('SELECT remaining_balance FROM payroll_item_assignment WHERE id=:id'), dict(id=ids['assignment'])
            ).scalar_one(),
            legacy=conn.execute(
                text('SELECT remaining_balance FROM employee_deduction WHERE id=:id'), dict(id=ids['legacy'])
            ).scalar_one(),
            slips=conn.execute(
                text('SELECT count(*) FROM payslip WHERE payroll_run_id=:id'), dict(id=ids['run'])
            ).scalar_one(),
            audits=conn.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id=:id AND action='payroll_run_completed'"),
                dict(id=ids['company']),
            ).scalar_one(),
        )


def assert_approved_once(engine, ids):
    assert persisted(engine, ids) == dict(assignment=Decimal('900'), legacy=Decimal('480'), slips=1, audits=1)


def test_equal_ids_in_different_ledgers_preserve_their_own_amounts(dataset):
    app, ids, engine = dataset
    assert approve(app, ids).success
    assert_approved_once(engine, ids)


def test_repeated_approval_cannot_consume_again(dataset):
    app, ids, engine = dataset
    assert approve(app, ids).success
    assert not approve(app, ids).success
    assert_approved_once(engine, ids)


def test_two_competing_locked_approvals_commit_one_payroll(dataset):
    app, ids, engine = dataset
    barrier = Barrier(2)

    def concurrent_approval():
        barrier.wait(timeout=10)
        return approve(app, ids).success

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(concurrent_approval) for _ in range(2)]
        outcomes = [future.result(timeout=30) for future in futures]
    assert sorted(outcomes) == [False, True]
    assert_approved_once(engine, ids)


def test_failure_before_commit_restores_both_balances(dataset, monkeypatch):
    app, ids, engine = dataset

    def fail(*args, **kwargs):
        raise RuntimeError('synthetic failure before commit')

    monkeypatch.setattr(payroll_service, 'compute_compliance_score', fail)
    assert not approve(app, ids).success
    assert persisted(engine, ids) == dict(assignment=Decimal('1000'), legacy=Decimal('500'), slips=0, audits=0)


def test_assignment_id_without_legacy_flag_cannot_consume_legacy_debt(dataset):
    app, ids, engine = dataset
    with app.app_context():
        payroll_service._decline_balances(
            ids['employee'],
            ids['company'],
            [
                {'id': ids['assignment'], 'assignment_id': ids['assignment'], 'amount': 100},
            ],
        )
        db.session.commit()
    assert persisted(engine, ids)['legacy'] == Decimal('500')


def test_older_legacy_payload_without_identity_flag_still_consumes_its_amount(dataset):
    app, ids, engine = dataset
    with app.app_context():
        payroll_service._decline_balances(
            ids['employee'],
            ids['company'],
            [
                {'id': ids['legacy'], 'amount': 20},
            ],
        )
        db.session.commit()
    assert persisted(engine, ids)['legacy'] == Decimal('480')


@pytest.mark.parametrize('foreign_scope', ['company', 'employee'])
def test_legacy_balance_cannot_be_reached_with_foreign_scope(dataset, foreign_scope):
    app, ids, engine = dataset
    with app.app_context():
        company = ids['foreign'] if foreign_scope == 'company' else ids['company']
        employee = ids['employee'] if foreign_scope == 'company' else ids['foreign_employee']
        payroll_service._decline_balances(employee, company, [{'id': ids['legacy'], 'legacy': True, 'amount': 100}])
        db.session.commit()
    assert persisted(engine, ids)['legacy'] == Decimal('500')
