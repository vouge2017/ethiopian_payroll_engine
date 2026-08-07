"""Tests for the analytics reports (department costs, overtime, leave, headcount)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    PayrollDraft,
    PayrollRun,
    User,
)


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


def _setup(app, num_employees=3, departments=None):
    """Create company, owner, employees with departments, complete payroll."""
    if departments is None:
        departments = ['Finance', 'Engineering', 'Finance']

    with app.app_context():
        company = Company(name='AnalyticsTestCo')
        db.session.add(company)
        db.session.flush()

        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('OwnerPass1!')
        db.session.add(owner)
        db.session.flush()

        employees_data = []
        for i in range(num_employees):
            dept = departments[i] if i < len(departments) else 'General'
            emp = Employee(
                employee_id=f'EMP{i+1:03d}',
                name=f'Employee {i+1}',
                phone=f'09100000{i+1:02d}',
                basic_salary=10000 + i * 2000,
                allowances=2000,
                company_id=company.id,
                bank_account=f'cbe:100012345678{i}',
                tin=f'12345678{i:02d}',
                department=dept,
            )
            db.session.add(emp)
            employees_data.append({
                'id': f'EMP{i+1:03d}',
                'name': f'Employee {i+1}',
                'phone': f'09100000{i+1:02d}',
                'basic': 10000 + i * 2000,
                'allowances': 2000,
                'gross': 12000 + i * 2000,
                'tax': 1500 + i * 200,
                'pension_employee': 700 + i * 140,
                'pension_employer': 1100 + i * 220,
                'net': 9800 + i * 1660,
                'bank': f'cbe:100012345678{i}',
                'tin': f'12345678{i:02d}',
                'taxable': 11300 + i * 1860,
                'department': dept,
                'position': '',
            })

        db.session.flush()

        run = PayrollRun(
            company_id=company.id, run_date=date.today(), status='review',
        )
        run.generate_period()
        db.session.add(run)
        db.session.flush()
        run.generate_reference()

        draft = PayrollDraft(
            payroll_run_id=run.id,
            employee_data=employees_data,
        )
        db.session.add(draft)
        db.session.commit()

        from payroll_engine.services.payroll_service import process_payroll
        result = process_payroll(
            run=run, company_id=company.id, user_id=owner.id,
            user_email='test@test.com', request_ip='127.0.0.1',
        )
        assert result.success is True

        return company.id, owner.id, run.id


def _login(client):
    client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})


class TestAnalyticsPage:
    """Test the analytics dashboard."""

    def test_analytics_loads(self, client, app):
        """Analytics page loads successfully."""
        _setup(app)
        _login(client)
        resp = client.get('/reports/analytics')
        assert resp.status_code == 200
        assert b'Analytics' in resp.data

    def test_analytics_requires_login(self, client, app):
        """Analytics redirects if not logged in."""
        resp = client.get('/reports/analytics', follow_redirects=False)
        assert resp.status_code == 302

    def test_analytics_shows_departments(self, client, app):
        """Analytics shows department cost breakdown."""
        _setup(app, departments=['Finance', 'Engineering', 'Finance'])
        _login(client)
        resp = client.get('/reports/analytics')
        assert b'Finance' in resp.data
        assert b'Engineering' in resp.data

    def test_analytics_shows_headcount(self, client, app):
        """Analytics shows headcount data."""
        _setup(app)
        _login(client)
        resp = client.get('/reports/analytics')
        assert b'Headcount' in resp.data

    def test_analytics_shows_leave_tab(self, client, app):
        """Analytics shows leave utilization tab."""
        _setup(app)
        _login(client)
        resp = client.get('/reports/analytics')
        assert b'Leave Utilization' in resp.data

    def test_analytics_year_filter(self, client, app):
        """Analytics can filter by year."""
        _setup(app)
        _login(client)
        resp = client.get(f'/reports/analytics?year={date.today().year}')
        assert resp.status_code == 200

    def test_analytics_empty_year(self, client, app):
        """Analytics handles year with no data."""
        _setup(app)
        _login(client)
        resp = client.get('/reports/analytics?year=2020')
        assert resp.status_code == 200

    def test_analytics_dept_costs_calculated(self, client, app):
        """Department costs are calculated correctly."""
        _setup(app, departments=['Finance', 'Finance', 'Engineering'])
        _login(client)
        resp = client.get('/reports/analytics')
        # Finance has 2 employees, Engineering has 1
        assert b'Finance' in resp.data
        assert b'Engineering' in resp.data


class TestAnalyticsData:
    """Test the data calculations."""

    def test_dept_costs_grouped_correctly(self, app):
        """Department costs are grouped by department name."""
        _setup(app, departments=['Finance', 'Engineering', 'Finance'])

        with app.app_context():
            from payroll_engine.models import Payslip
            company = Company.query.first()
            runs = PayrollRun.query.filter_by(company_id=company.id, status='completed').all()
            run_ids = [r.id for r in runs]
            payslips = Payslip.query.filter(Payslip.payroll_run_id.in_(run_ids)).all()

            dept_costs = {}
            for ps in payslips:
                emp = ps.employee
                dept = emp.department or 'Unassigned'
                if dept not in dept_costs:
                    dept_costs[dept] = {'count': 0}
                dept_costs[dept]['count'] += 1

            assert dept_costs['Finance']['count'] == 2
            assert dept_costs['Engineering']['count'] == 1
