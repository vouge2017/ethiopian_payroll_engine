"""
Employee phone field tests.

The employee phone field is a general contact field — it must accept
any phone format (Ethiopian, Kenyan, US, etc.) without restriction.

The Ethiopian format validation (validate_ethiopian_phone) applies ONLY
to User.phone for login/auth, NOT to Employee.phone for contact info.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, User, validate_ethiopian_phone


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


def _login(client, app, plan='standard'):
    """Login as owner. Uses standard plan to allow enough employees."""
    with app.app_context():
        company = Company(name='TestCo', plan_code=plan)
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


def test_employee_accepts_ethiopian_phone(app):
    """Employee phone field accepts all Ethiopian formats."""
    test_phones = [
        '+251911234567',  # Ethiopian +251 format
        '0911234567',  # Ethiopian local format
        '911234567',  # Ethiopian without leading 0
        '+251711234567',  # Ethiopian Safaricom
        '0711234567',  # Ethiopian Safaricom local
        '711234567',  # Ethiopian Safaricom without leading 0
    ]

    with app.test_client() as client:
        company_id = _login(client, app)

        for i, phone in enumerate(test_phones):
            resp = client.post(
                '/employees/add',
                data={
                    'employee_id': f'EMP-{i + 1:03d}',
                    'name': f'Worker {i + 1}',
                    'phone': phone,
                    'basic_salary': '10000',
                    'allowances': '0',
                },
                follow_redirects=True,
            )
            assert b'Invalid' not in resp.data, f'Ethiopian phone {phone} was rejected'

    with app.app_context():
        employees = Employee.query.filter_by(company_id=company_id).all()
        assert len(employees) == len(test_phones)


def test_employee_accepts_international_phone(app):
    """Employee phone field accepts non-Ethiopian phone numbers."""
    test_phones = [
        ('+254712345678', '+254712345678'),     # Kenya
        ('+1 555 123 4567', '+15551234567'),    # US (spaces stripped)
        ('+44 20 7946 0958', '+442079460958'),  # UK
        ('+971501234567', '+971501234567'),     # UAE
        ('+86 138 0013 8000', '+8613800138000'), # China
    ]

    with app.test_client() as client:
        company_id = _login(client, app)

        for i, (phone_input, _) in enumerate(test_phones):
            resp = client.post(
                '/employees/add',
                data={
                    'employee_id': f'INT-{i + 1:03d}',
                    'name': f'International {i + 1}',
                    'phone': phone_input,
                    'basic_salary': '10000',
                    'allowances': '0',
                },
                follow_redirects=True,
            )
            assert b'Invalid' not in resp.data, f'International phone {phone_input} was rejected'

    with app.app_context():
        employees = Employee.query.filter_by(company_id=company_id).all()
        assert len(employees) == len(test_phones)
        # Verify normalized (spaces stripped)
        phones = sorted([e.phone for e in employees])
        expected = sorted([exp for _, exp in test_phones])
        assert phones == expected, f'Phones: {phones} != Expected: {expected}'


def test_employee_phone_stored_as_is(app):
    """Ethiopian phone normalized to 0XXXXXXXXX; international stored as-is."""
    with app.test_client() as client:
        company_id = _login(client, app)

        # Ethiopian — should normalize
        client.post(
            '/employees/add',
            data={
                'employee_id': 'EMP001',
                'name': 'Ethiopian Worker',
                'phone': '+251911234567',
                'basic_salary': '10000',
                'allowances': '0',
            },
            follow_redirects=True,
        )

        # International — should store cleaned
        client.post(
            '/employees/add',
            data={
                'employee_id': 'EMP002',
                'name': 'Kenyan Worker',
                'phone': '+254712345678',
                'basic_salary': '10000',
                'allowances': '0',
            },
            follow_redirects=True,
        )

    with app.app_context():
        eth = Employee.query.filter_by(employee_id='EMP001', company_id=company_id).first()
        assert eth is not None
        assert eth.phone == '0911234567', f"Ethiopian phone: '{eth.phone}'"

        ken = Employee.query.filter_by(employee_id='EMP002', company_id=company_id).first()
        assert ken is not None
        assert ken.phone == '+254712345678', f"Kenyan phone: '{ken.phone}'"


def test_validate_ethiopian_phone_only_for_auth():
    """validate_ethiopian_phone correctly validates Ethiopian format (used for auth only)."""
    # Valid Ethiopian
    is_valid, normalized, _ = validate_ethiopian_phone('+251911234567')
    assert is_valid
    assert normalized == '0911234567'

    # Invalid (not Ethiopian) — this is what auth uses, NOT the employee field
    is_valid, _, error = validate_ethiopian_phone('+254712345678')
    assert not is_valid
    assert 'Invalid' in error or 'Ethiopian' in error
