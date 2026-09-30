"""ORM writes against Alembic-created native enum columns; no create_all."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import text

from payroll_engine import db
from payroll_engine.models import Company
from payroll_engine.models_payroll_elements import PayItemType

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


def test_bulk_catalog_write_matches_native_enum_schema():
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=PG_URL)
    db.init_app(app)
    Migrate(app, db)
    with app.app_context():
        repo = Path(__file__).resolve().parents[1]
        cfg = Config(str(repo / 'migrations/alembic.ini'))
        cfg.set_main_option('script_location', str(repo / 'migrations'))
        cfg.set_main_option('sqlalchemy.url', PG_URL)
        command.upgrade(cfg, 'head')
        company = Company(name='PG bulk catalog ' + uuid4().hex)
        db.session.add(company)
        db.session.flush()
        company_id = company.id
        try:
            db.session.add_all(
                [
                    PayItemType(
                        company_id=company_id,
                        key='bulk_salary',
                        name_en='Salary',
                        classification='earning',
                        calculation_method='fixed',
                        tax_treatment='taxable',
                    ),
                    PayItemType(
                        company_id=company_id,
                        key='bulk_loan',
                        name_en='Loan',
                        classification='deduction',
                        calculation_method='percent_of_net',
                        tax_treatment='exempt',
                    ),
                    PayItemType(
                        company_id=company_id,
                        key='bulk_units',
                        name_en='Units',
                        classification='earning',
                        calculation_method='rate_x_units',
                        tax_treatment='partial',
                    ),
                ]
            )
            db.session.commit()
            with db.engine.connect() as conn:
                rows = conn.execute(
                    text(
                        'SELECT key, classification, calculation_method, tax_treatment '
                        'FROM pay_item_type WHERE company_id=:id ORDER BY key'
                    ),
                    {'id': company_id},
                ).all()
                assert rows == [
                    ('bulk_loan', 'deduction', 'percent_of_net', 'exempt'),
                    ('bulk_salary', 'earning', 'fixed', 'taxable'),
                    ('bulk_units', 'earning', 'rate_x_units', 'partial'),
                ]
        finally:
            db.session.rollback()
            with db.engine.begin() as conn:
                conn.execute(text('DELETE FROM pay_item_type WHERE company_id=:id'), {'id': company_id})
                conn.execute(text('DELETE FROM company WHERE id=:id'), {'id': company_id})
