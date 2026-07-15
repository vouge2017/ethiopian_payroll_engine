"""
Employee phone field tests.

The employee phone field is a general contact field — it must accept
any phone format (Ethiopian, Kenyan, US, etc.) without restriction.

The Ethiopian format validation (validate_ethiopian_phone) applies ONLY
to User.phone for login/auth, NOT to Employee.phone for contact info.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from decimal import Decimal

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User, Employee, validate_ethiopian_phone


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _login(client, app):
    """Login as owner."""
    with app.app_context():
        company = Company(name='TestCo')
        db.session.add(company)
        db.session.flush()
        user = User(email='owner@test.com', role='owner', company_id=company.id)
        user.set_password('TestPass1!')
        db.session.add(user)
        db.session.commit()
        company_id = company.id
        user_id = user.id

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True

    return company_id


def test_employee_accepts_non_ethiopian_phone(app):
    """Employee phone field must accept non-Ethiopian numbers."""
    test_phones = [
        '+254712345678',    # Kenya
        '+12025551234',     # US
        '+447911123456',    # UK
        '+491701234567',    # Germany
        '+8613812345678',   # China
        '0712345678',       # Kenya local format
        '+251911234567',    # Ethiopian (should also work)
    ]

    with app.test_client() as client:
        company_id = _login(client, app)

        for i, phone in enumerate(test_phones):
            resp = client.post('/employees/add', data={
                'employee_id': f'EMP-{i+1:03d}',
                'name': f'Worker {i+1}',
                'phone': phone,
                'basic_salary': '10000',
                'allowances': '0',
            }, follow_redirects=True)

            # Should NOT get a phone validation error
            assert b'Invalid Ethiopian phone' not in resp.data, \
                f"Non-Ethiopian phone {phone} was rejected by employee form"

    # Verify all employees were saved (must filter by company_id for TenantQuery)
    with app.app_context():
        employees = Employee.query.filter_by(company_id=company_id).all()
        assert len(employees) == len(test_phones), \
            f"Expected {len(test_phones)} employees, got {len(employees)}"


def test_employee_phone_stored_as_is(app):
    """Employee phone should be stored exactly as entered (no normalization)."""
    with app.test_client() as client:
        company_id = _login(client, app)

        resp = client.post('/employees/add', data={
            'employee_id': 'EMP001',
            'name': 'Kenyan Worker',
            'phone': '+254712345678',
            'basic_salary': '10000',
            'allowances': '0',
        }, follow_redirects=True)

    with app.app_context():
        emp = Employee.query.filter_by(employee_id='EMP001', company_id=company_id).first()
        assert emp is not None
        assert emp.phone == '+254712345678', \
            f"Phone was normalized from '+254712345678' to '{emp.phone}'"


def test_ethiopian_phone_still_works_for_employees(app):
    """Ethiopian phone numbers should still be accepted in the employee field."""
    with app.test_client() as client:
        company_id = _login(client, app)

        resp = client.post('/employees/add', data={
            'employee_id': 'EMP001',
            'name': 'Ethiopian Worker',
            'phone': '+251911234567',
            'basic_salary': '10000',
            'allowances': '0',
        }, follow_redirects=True)

    with app.app_context():
        emp = Employee.query.filter_by(employee_id='EMP001', company_id=company_id).first()
        assert emp is not None
        # Stored as-is (not normalized to 0XXXXXXXXX)
        assert emp.phone == '+251911234567'


def test_validate_ethiopian_phone_only_for_auth():
    """validate_ethiopian_phone should correctly validate Ethiopian format."""
    # Valid Ethiopian
    is_valid, normalized, _ = validate_ethiopian_phone('+251911234567')
    assert is_valid
    assert normalized == '0911234567'

    # Invalid (not Ethiopian) — this is what auth uses, NOT the employee field
    is_valid, _, error = validate_ethiopian_phone('+254712345678')
    assert not is_valid
    assert 'Invalid' in error or 'Ethiopian' in error

    # This proves the validator correctly rejects non-Ethiopian for auth,
    # while the employee field (tested above) correctly accepts them.
