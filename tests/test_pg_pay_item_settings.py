"""PostgreSQL proof for the pay-item settings service (catalog PR 2).

Runs the service against an Alembic-built schema (native enum columns, the
name_om migration, the tenancy triggers): create with all three labels, the
grouped usage query (SUM(CASE ...)), the payslip JSON scan, reorder, and the
delete / deactivate rules. Requires a disposable TEST_DATABASE_URL.
"""

import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from flask import Flask
from flask_migrate import Migrate

from payroll_engine import db
from payroll_engine.catalog import seed_company_catalog
from payroll_engine.models import Company, Employee, PayItemType, PayrollItemAssignment, PayrollRun, Payslip

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


@pytest.fixture
def pg():
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=PG_URL)
    db.init_app(app)
    Migrate(app, db)
    repo = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(repo / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', PG_URL)
    with app.test_request_context('/'):
        command.upgrade(cfg, 'head')
        company = Company(name='PG pay item settings ' + uuid4().hex)
        db.session.add(company)
        db.session.flush()
        seed_company_catalog(company.id, commit=False)
        db.session.commit()
        company_id = company.id
        try:
            yield company_id
        finally:
            db.session.rollback()
            db.session.remove()
            with db.engine.begin() as conn:
                params = {'id': company_id}
                for sql in (
                    'DELETE FROM audit_log WHERE company_id = :id',
                    'DELETE FROM payslip WHERE company_id = :id',
                    'DELETE FROM payroll_run WHERE company_id = :id',
                    'DELETE FROM payroll_item_assignment WHERE company_id = :id',
                    'DELETE FROM employee WHERE company_id = :id',
                    'DELETE FROM pay_item_type WHERE company_id = :id',
                    'DELETE FROM company WHERE id = :id',
                ):
                    conn.execute(sa.text(sql), params)


def test_settings_service_on_postgres(pg):
    from payroll_engine.services import pay_item_settings as svc

    company_id = pg
    item = svc.create_item(
        company_id, None, key='fuel_allowance', kind='earning', name_en='Fuel', name_am='የነዳጅ አበል', name_om='Boba’aa'
    )
    db.session.commit()
    with db.engine.connect() as conn:
        row = conn.execute(
            sa.text(
                'SELECT classification::text, calculation_method::text, tax_treatment::text, name_am, name_om '
                'FROM pay_item_type WHERE id = :id'
            ),
            {'id': item.id},
        ).one()
    assert tuple(row) == ('earning', 'fixed', 'taxable', 'የነዳጅ አበል', 'Boba’aa')

    with pytest.raises(svc.PayItemSettingsError, match='already has an item'):
        svc.create_item(company_id, None, key='fuel_allowance', kind='earning', name_en='Again')
    db.session.rollback()

    emp = Employee(company_id=company_id, employee_id=uuid4().hex[:15], name='PG emp', basic_salary=10000, allowances=0)
    db.session.add(emp)
    db.session.flush()
    housing = PayItemType.query.filter_by(company_id=company_id, key='housing').one()
    db.session.add_all(
        [
            PayrollItemAssignment(
                company_id=company_id, employee_id=emp.id, pay_item_type_id=housing.id, fixed_amount=1
            ),
            PayrollItemAssignment(
                company_id=company_id,
                employee_id=emp.id,
                pay_item_type_id=housing.id,
                fixed_amount=1,
                end_date=date.today() - timedelta(days=3),
            ),
        ]
    )
    db.session.commit()
    usage = svc.usage_by_item(company_id)
    assert usage[housing.id] == svc.Usage(active_assignments=1, total_assignments=2)
    assert item.id not in usage

    with pytest.raises(svc.PayItemSettingsError, match='still running'):
        svc.deactivate_item(housing, None)
    db.session.rollback()

    # Payslip JSON snapshot scan on PostgreSQL.
    run = PayrollRun(company_id=company_id, status='approved', period='2019-02')
    db.session.add(run)
    db.session.flush()
    db.session.add(
        Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            company_id=company_id,
            gross_salary=10000,
            tax=1000,
            employee_pension=700,
            employer_pension=1100,
            net_pay=8300,
            generated_at=datetime.now(UTC),
            line_items=[{'item_key': 'fuel_allowance', 'item_id': item.id, 'earned_amount': '10'}],
        )
    )
    db.session.commit()
    assert svc.item_in_payslips(company_id, item) is True
    with pytest.raises(svc.PayItemSettingsError, match='appears on payslips'):
        svc.delete_item(item, None)
    db.session.rollback()

    # Reorder and deactivate/reactivate persist on PostgreSQL.
    assert svc.move_item(item, None, 'up') is True
    svc.deactivate_item(item, None)
    db.session.commit()
    db.session.expire_all()
    assert PayItemType.query.filter_by(company_id=company_id, key='fuel_allowance').one().is_active is False

    # An unused custom item can be deleted.
    spare = svc.create_item(company_id, None, key='spare_item', kind='deduction', name_en='Spare')
    db.session.commit()
    svc.delete_item(spare, None)
    db.session.commit()
    assert PayItemType.query.filter_by(company_id=company_id, key='spare_item').first() is None
