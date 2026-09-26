"""Consumer-1 tests: employees_bp allowance/deduction routes on the elements model.

These lock in the migration away from the hardcoded class enums:
  - the routes resolve against the per-company PayItemType catalog
  - they write PayrollItemAssignment, never EmployeeAllowance / EmployeeDeduction
  - the transport / hardship / court_order regulatory rules come from the
    catalog row, not from `if allowance_type == 'transport'` style branches
  - system items (income_tax, pensions) are rejected (AC5)
  - the max_percent_of_net ceiling is enforced in the ENGINE, not only the route
"""

import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.catalog import migrate_pay_items, seed_system_items
from payroll_engine.models import (
    Company,
    Employee,
    EmployeeAllowance,
    EmployeeDeduction,
    User,
)
from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    import tempfile

    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    with app.app_context():
        db.create_all()
        seed_system_items()
        co = Company(name='ElementsCo', tin='999')
        db.session.add(co)
        db.session.flush()
        migrate_pay_items()
        emp = Employee(
            employee_id='EMP001', name='Smoke Tester',
            basic_salary=Decimal('10000'), company_id=co.id,
        )
        db.session.add(emp)
        u = User(phone='0911111111', role='owner', company_id=co.id)
        u.set_password('password')
        db.session.add(u)
        db.session.commit()
        app.extensions['test_co'] = co
        app.extensions['test_emp'] = emp
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def ctx(app):
    class C:
        pass

    c = C()
    c.co = app.extensions['test_co']
    c.emp = app.extensions['test_emp']
    c.client = app.test_client()
    c.client.post(
        '/auth/login',
        data={'login_id': '0911111111', 'password': 'password'},
        follow_redirects=True,
    )
    return c


# --------------------------------------------------------------------------
# Catalog carries the regulatory rules (previously hardcoded in the route)
# --------------------------------------------------------------------------


def test_transport_rule_lives_in_catalog(app):
    t = PayItemType.query.filter_by(company_id=app.extensions['test_co'].id, key='transport').one()
    assert t.tax_treatment == 'partial'
    assert t.exempt_cap_amount == Decimal('2200')
    assert t.exempt_cap_percent == Decimal('25')
    assert t.exempt_cap_basis == 'basic_salary'
    assert t.regulation_reference


def test_hardship_rule_lives_in_catalog(app):
    h = PayItemType.query.filter_by(company_id=app.extensions['test_co'].id, key='hardship').one()
    assert h.tax_treatment == 'partial'
    assert h.regulation_reference


def test_court_order_ceiling_lives_in_catalog(app):
    c = PayItemType.query.filter_by(company_id=app.extensions['test_co'].id, key='court_order').one()
    assert c.max_percent_of_net == Decimal('50')


# --------------------------------------------------------------------------
# add_allowance
# --------------------------------------------------------------------------


def test_add_allowance_creates_assignment(app, ctx):
    r = ctx.client.post(
        f'/employees/{ctx.emp.id}/allowances/add',
        data={'allowance_type': 'transport', 'amount': '1500'},
        follow_redirects=True,
    )
    assert r.status_code == 200
    a = PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id).one()
    assert a.item_type.key == 'transport'
    assert a.fixed_amount == Decimal('1500')
    assert a.is_active is True


def test_add_allowance_writes_no_legacy_row(app, ctx):
    """Guard: the new path must never write EmployeeAllowance."""
    ctx.client.post(
        f'/employees/{ctx.emp.id}/allowances/add',
        data={'allowance_type': 'transport', 'amount': '1500'},
        follow_redirects=True,
    )
    assert EmployeeAllowance.query.filter_by(company_id=ctx.co.id).count() == 0


def test_add_allowance_rejects_unknown_key(app, ctx):
    ctx.client.post(
        f'/employees/{ctx.emp.id}/allowances/add',
        data={'allowance_type': 'not_a_real_item', 'amount': '500'},
        follow_redirects=True,
    )
    assert PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id).count() == 0


def test_add_allowance_rejects_deduction_item(app, ctx):
    """A deduction key must not be accepted on the allowance route."""
    ctx.client.post(
        f'/employees/{ctx.emp.id}/allowances/add',
        data={'allowance_type': 'court_order', 'amount': '500'},
        follow_redirects=True,
    )
    assert PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id).count() == 0


# --------------------------------------------------------------------------
# add_deduction
# --------------------------------------------------------------------------


def test_add_deduction_percentage_creates_assignment(app, ctx):
    ctx.client.post(
        f'/employees/{ctx.emp.id}/deductions/add',
        data={
            'deduction_type': 'court_order', 'label': 'Case 42',
            'amount_mode': 'percentage', 'amount': '60',
            'tracking_mode': 'declining', 'total_to_recover': '1000',
            'start_date': date.today().isoformat(),
        },
        follow_redirects=True,
    )
    d = PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id, custom_label='Case 42').one()
    assert d.item_type.key == 'court_order'
    assert d.percent_of_net == Decimal('60')
    assert d.fixed_amount is None
    assert d.tracking_mode == 'declining'
    assert d.total_to_recover == Decimal('1000')


def test_add_deduction_fixed_uses_fixed_amount(app, ctx):
    ctx.client.post(
        f'/employees/{ctx.emp.id}/deductions/add',
        data={
            'deduction_type': 'court_order', 'label': 'Case 43',
            'amount_mode': 'fixed', 'amount': '500',
            'tracking_mode': 'declining', 'total_to_recover': '1000',
            'start_date': date.today().isoformat(),
        },
        follow_redirects=True,
    )
    d = PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id, custom_label='Case 43').one()
    assert d.fixed_amount == Decimal('500')
    assert d.percent_of_net is None


def test_add_deduction_persists_document_trail(app, ctx):
    """Regression: reference_number/document_path were silently dropped."""
    ctx.client.post(
        f'/employees/{ctx.emp.id}/deductions/add',
        data={
            'deduction_type': 'court_order', 'label': 'Case 44',
            'amount_mode': 'fixed', 'amount': '500',
            'tracking_mode': 'declining', 'total_to_recover': '1000',
            'start_date': date.today().isoformat(),
            'reference_number': 'SC-2026-99',
        },
        follow_redirects=True,
    )
    d = PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id, custom_label='Case 44').one()
    assert d.reference_number == 'SC-2026-99'
    # document_path stays None when no file was uploaded
    assert d.document_path is None


def test_add_deduction_writes_no_legacy_row(app, ctx):
    ctx.client.post(
        f'/employees/{ctx.emp.id}/deductions/add',
        data={
            'deduction_type': 'court_order', 'label': 'Case 45',
            'amount_mode': 'fixed', 'amount': '500',
            'tracking_mode': 'declining', 'start_date': date.today().isoformat(),
        },
        follow_redirects=True,
    )
    assert EmployeeDeduction.query.filter_by(company_id=ctx.co.id).count() == 0


# --------------------------------------------------------------------------
# AC5 — system items are engine-managed
# --------------------------------------------------------------------------


@pytest.mark.parametrize('key', ['employee_pension', 'employer_pension', 'income_tax'])
def test_ac5_rejects_system_item_assignment(app, ctx, key):
    before = PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id).count()
    ctx.client.post(
        f'/employees/{ctx.emp.id}/allowances/add',
        data={'allowance_type': key, 'amount': '500'},
        follow_redirects=True,
    )
    after = PayrollItemAssignment.query.filter_by(employee_id=ctx.emp.id).count()
    assert after == before


# --------------------------------------------------------------------------
# Engine-side ceiling enforcement
# --------------------------------------------------------------------------


def _make_assignment(app, item, pct):
    """A real PayrollItemAssignment row so the engine sees the true column set.

    The seeded court_order/loan templates default to calculation_method='fixed'.
    A percentage deduction is expressed by switching the company item to
    percent_of_net, which is what the admin does in pay item settings.
    """
    co = app.extensions['test_co']
    emp = app.extensions['test_emp']
    item.calculation_method = 'percent_of_net'
    db.session.flush()
    a = PayrollItemAssignment(
        company_id=co.id,
        employee_id=emp.id,
        pay_item_type_id=item.id,
        percent_of_net=Decimal(pct),
        is_active=True,
    )
    db.session.add(a)
    db.session.commit()
    return a


def test_engine_clamps_percent_of_net_to_ceiling(app, ctx):
    """The cap must be enforced at calculation time, not just warned about.

    A row created before the ceiling existed (or written by any path that
    bypasses the route) still must not deduct more than the catalog allows.
    """
    from payroll_engine.payroll_elements import _calculate_item_amount

    item = PayItemType.query.filter_by(company_id=ctx.co.id, key='court_order').one()
    assert item.max_percent_of_net == Decimal('50')

    a = _make_assignment(app, item, '90')
    amount = _calculate_item_amount(
        a, ctx.emp, date.today(), None, Decimal('1000')
    )
    # 90% would be 900; the 50% ceiling caps it at 500.
    assert amount == Decimal('500.00')


def test_engine_does_not_clamp_below_ceiling(app, ctx):
    from payroll_engine.payroll_elements import _calculate_item_amount

    item = PayItemType.query.filter_by(company_id=ctx.co.id, key='court_order').one()
    a = _make_assignment(app, item, '20')
    amount = _calculate_item_amount(
        a, ctx.emp, date.today(), None, Decimal('1000')
    )
    assert amount == Decimal('200.00')


def test_engine_ignores_ceiling_when_null(app, ctx):
    """NULL ceiling means no documented limit -- pass the value through."""
    from payroll_engine.payroll_elements import _calculate_item_amount

    item = PayItemType.query.filter_by(company_id=ctx.co.id, key='loan').one()
    assert item.max_percent_of_net is None

    a = _make_assignment(app, item, '90')
    amount = _calculate_item_amount(
        a, ctx.emp, date.today(), None, Decimal('1000')
    )
    assert amount == Decimal('900.00')
