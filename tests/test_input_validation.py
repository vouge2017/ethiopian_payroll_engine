"""
Tests for input validation on API endpoints.

Verifies:
- Company existence is checked (not just session/company_id)
- Run_id ownership is enforced (can't access another company's runs)
- Invalid inputs return 400/404 with clear messages
- Valid requests still work normally
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User, Employee, PayrollRun, Payslip
from decimal import Decimal
from datetime import date


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


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_data(app, client):
    """Register company and create payroll."""
    with app.app_context():
        client.post('/auth/register', data={
            'company_name': 'Test PLC',
            'phone': '0911123456',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
        }, follow_redirects=True)

        company = Company.query.filter_by(name='Test PLC').first()
        user = User.query.filter_by(phone='0911123456').first()

        emp = Employee(
            employee_id='EMP-001', name='Dawit Kebede',
            basic_salary=Decimal('15000'), allowances=Decimal('0'),
            bank_or_telebirr='1000123456789', tin='TIN001',
            phone='+251911000001', company_id=company.id,
        )
        db.session.add(emp)
        db.session.commit()

        run = PayrollRun(
            company_id=company.id, run_date=date(2026, 8, 1),
            status='completed', period='2018-10',
            reference='PR-2018-10-001',
        )
        db.session.add(run)
        db.session.flush()

        ps = Payslip(
            payroll_run_id=run.id, employee_id=emp.id,
            gross_salary=Decimal('15000'), tax=Decimal('2250'),
            employee_pension=Decimal('1050'), employer_pension=Decimal('1050'),
            net_pay=Decimal('11700'),
        )
        db.session.add(ps)
        db.session.commit()

        return {
            'company_id': company.id,
            'user_id': user.id,
            'run_id': run.id,
            'emp_id': emp.id,
        }


def login(client):
    return client.post('/auth/login', data={
        'login_id': '0911123456',
        'password': 'TestPass123!',
    }, follow_redirects=True)


class TestCompanyValidation:
    """Test that company existence is verified."""

    def test_api_returns_401_without_login(self, app, client, seed_data):
        """API should return 401 if not logged in."""
        with app.app_context():
            resp = client.get('/api/v1/employees')
            assert resp.status_code == 401

    def test_api_returns_200_with_valid_company(self, app, client, seed_data):
        """API should return 200 when company exists and user is logged in."""
        with app.app_context():
            login(client)
            resp = client.get('/api/v1/employees')
            assert resp.status_code == 200

    def test_api_returns_404_when_company_deleted(self, app, client, seed_data):
        """API should return 404 if the company_id in session doesn't exist."""
        with app.app_context():
            login(client)
            # Simulate stale session: set active_company_id to non-existent company
            with client.session_transaction() as sess:
                sess['active_company_id'] = 99999

            resp = client.get('/api/v1/employees')
            assert resp.status_code == 404
            data = resp.get_json()
            assert 'Company not found' in data.get('error', '')


class TestRunIdOwnership:
    """Test that run_id ownership is enforced."""

    def test_review_returns_404_for_nonexistent_run(self, app, client, seed_data):
        """Should return 404 for a run that doesn't exist."""
        with app.app_context():
            login(client)
            resp = client.get('/api/v1/payroll-runs/99999/review')
            assert resp.status_code == 404

    def test_review_returns_200_for_own_run(self, app, client, seed_data):
        """Should return 200 for a run that belongs to the company."""
        with app.app_context():
            login(client)
            resp = client.get(f'/api/v1/payroll-runs/{seed_data["run_id"]}/review')
            assert resp.status_code == 200

    def test_review_returns_404_for_other_company_run(self, app, client, seed_data):
        """Should return 404 for a run that belongs to another company."""
        with app.app_context():
            # Create another company with a run
            other = Company(name='Other PLC', tin='9999999999')
            db.session.add(other)
            db.session.flush()

            other_run = PayrollRun(
                company_id=other.id, run_date=date(2026, 8, 1),
                status='completed', period='2018-10',
            )
            db.session.add(other_run)
            db.session.commit()

            login(client)
            resp = client.get(f'/api/v1/payroll-runs/{other_run.id}/review')
            assert resp.status_code == 404

    def test_employee_returns_404_for_other_company(self, app, client, seed_data):
        """Should return 404 for an employee that belongs to another company."""
        with app.app_context():
            other = Company(name='Other PLC', tin='9999999999')
            db.session.add(other)
            db.session.flush()

            other_emp = Employee(
                employee_id='EMP-999', name='Other Employee',
                basic_salary=Decimal('10000'), allowances=Decimal('0'),
                bank_or_telebirr='1000999999999', tin='TIN999',
                phone='+251911999999', company_id=other.id,
            )
            db.session.add(other_emp)
            db.session.commit()

            login(client)
            resp = client.get(f'/api/v1/employees/{other_emp.id}')
            assert resp.status_code == 404


class TestEmployeeInputValidation:
    """Test employee data validation."""

    def test_create_employee_missing_fields(self, app, client, seed_data):
        """Should return 422 if required fields are missing."""
        with app.app_context():
            login(client)
            resp = client.post('/api/v1/employees', json={})
            assert resp.status_code == 422
            data = resp.get_json()
            assert 'error' in data

    def test_create_employee_negative_salary(self, app, client, seed_data):
        """Should return 422 if salary is negative."""
        with app.app_context():
            login(client)
            resp = client.post('/api/v1/employees', json={
                'employee_id': 'EMP-002',
                'name': 'Test Employee',
                'basic_salary': -1000,
            })
            assert resp.status_code == 422

    def test_create_employee_valid_data(self, app, client, seed_data):
        """Should return 201 if data is valid."""
        with app.app_context():
            login(client)
            resp = client.post('/api/v1/employees', json={
                'employee_id': 'EMP-002',
                'name': 'Valid Employee',
                'basic_salary': 10000,
                'bank_or_telebirr': '1000123456789',
            })
            assert resp.status_code == 201

    def test_create_employee_duplicate_id(self, app, client, seed_data):
        """Should return 409 if employee_id already exists."""
        with app.app_context():
            login(client)
            resp = client.post('/api/v1/employees', json={
                'employee_id': 'EMP-001',  # Already exists
                'name': 'Duplicate',
                'basic_salary': 10000,
            })
            assert resp.status_code == 409


class TestRoleValidation:
    """Test that role-based access control works."""

    def test_owner_can_access_all_endpoints(self, app, client, seed_data):
        """Owner should have access to all endpoints."""
        with app.app_context():
            login(client)
            # Employee list
            resp = client.get('/api/v1/employees')
            assert resp.status_code == 200
            # Payroll review
            resp = client.get(f'/api/v1/payroll-runs/{seed_data["run_id"]}/review')
            assert resp.status_code == 200


class TestInputSanitization:
    """Test that dangerous inputs are handled."""

    def test_long_employee_id_rejected(self, app, client, seed_data):
        """Should reject employee_id longer than 20 chars."""
        with app.app_context():
            login(client)
            resp = client.post('/api/v1/employees', json={
                'employee_id': 'A' * 21,
                'name': 'Test',
                'basic_salary': 10000,
            })
            assert resp.status_code == 422

    def test_long_name_rejected(self, app, client, seed_data):
        """Should reject name longer than 100 chars."""
        with app.app_context():
            login(client)
            resp = client.post('/api/v1/employees', json={
                'employee_id': 'EMP-NEW',
                'name': 'A' * 101,
                'basic_salary': 10000,
            })
            assert resp.status_code == 422

    def test_empty_body_rejected(self, app, client, seed_data):
        """Should reject empty request body."""
        with app.app_context():
            login(client)
            resp = client.post('/api/v1/employees',
                              data='',
                              content_type='application/json')
            assert resp.status_code in (400, 422)
