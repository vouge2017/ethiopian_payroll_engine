"""
Tests for error boundaries — trust component failure isolation.

Verifies:
- Page still loads when one component fails
- API returns partial data when one component fails
- Approval is blocked when exceptions can't be computed
- Other components still work when one fails
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'

from datetime import date
from decimal import Decimal

from payroll_engine import create_app, db, trust_cache
from payroll_engine.models import Company, Employee, PayrollRun, Payslip, User


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
    """Register company and create payroll via the actual flow."""
    with app.app_context():
        # Register company + owner (creates UserCompany link)
        client.post(
            '/auth/register',
            data={
                'company_name': 'Test PLC',
                'phone': '0911123456',
                'password': 'TestPass123!',
                'password2': 'TestPass123!',
            },
            follow_redirects=True,
        )

        company = Company.query.filter_by(name='Test PLC').first()
        user = User.query.filter_by(phone='0911123456').first()

        # Add employee
        emp = Employee(
            employee_id='EMP-001',
            name='Dawit Kebede',
            basic_salary=Decimal('15000'),
            allowances=Decimal('0'),
            bank_or_telebirr='1000123456789',
            tin='TIN001',
            phone='+251911000001',
            company_id=company.id,
        )
        db.session.add(emp)
        db.session.commit()

        # Create completed payroll run
        run = PayrollRun(
            company_id=company.id,
            run_date=date(2026, 8, 1),
            status='completed',
            period='2018-10',
            reference='PR-2018-10-001',
        )
        db.session.add(run)
        db.session.flush()

        ps = Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            gross_salary=Decimal('15000'),
            tax=Decimal('2250'),
            employee_pension=Decimal('1050'),
            employer_pension=Decimal('1050'),
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
    """Log in the test user."""
    return client.post(
        '/auth/login',
        data={
            'login_id': '0911123456',
            'password': 'TestPass123!',
        },
        follow_redirects=True,
    )


class TestReviewWorkspaceErrorBoundaries:
    """Test error boundaries in the payroll review workspace."""

    def test_page_loads_normally(self, app, client, seed_data):
        """Baseline: page loads without errors."""
        with app.app_context():
            login(client)
            resp = client.get(f'/payroll/runs/{seed_data["run_id"]}/review')
            assert resp.status_code == 200

    def test_page_loads_when_change_summary_fails(self, app, client, seed_data):
        """Page should still load if compute_change_summary throws."""
        with app.app_context():
            login(client)
            with patch(
                'payroll_engine.payroll_bp.compute_change_summary', side_effect=RuntimeError('DB connection lost')
            ):
                resp = client.get(f'/payroll/runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200
                assert b'Unable to load' in resp.data or b'Review' in resp.data

    def test_page_loads_when_evidence_fails(self, app, client, seed_data):
        """Page should still load if collect_evidence throws."""
        with app.app_context():
            login(client)
            with patch('payroll_engine.payroll_bp.collect_evidence', side_effect=RuntimeError('Timeout')):
                resp = client.get(f'/payroll/runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200

    def test_page_loads_when_exceptions_fails(self, app, client, seed_data):
        """Page should still load if classify_exceptions throws."""
        with app.app_context():
            login(client)
            with patch('payroll_engine.payroll_bp.classify_exceptions', side_effect=RuntimeError('Error')):
                resp = client.get(f'/payroll/runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200

    def test_approval_blocked_when_exceptions_fails(self, app, client, seed_data):
        """Approval button should be disabled if exceptions can't be computed."""
        with app.app_context():
            login(client)
            with patch('payroll_engine.payroll_bp.classify_exceptions', side_effect=RuntimeError('Error')):
                resp = client.get(f'/payroll/runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200
                # Should NOT have an active approve button
                assert b'disabled' in resp.data or b'Cannot' in resp.data or b'Unable' in resp.data

    def test_page_loads_when_all_fail(self, app, client, seed_data):
        """Page should still load even if ALL components fail."""
        with app.app_context():
            login(client)
            with (
                patch('payroll_engine.payroll_bp.compute_change_summary', side_effect=RuntimeError('E1')),
                patch('payroll_engine.payroll_bp.collect_evidence', side_effect=RuntimeError('E2')),
                patch('payroll_engine.payroll_bp.classify_exceptions', side_effect=RuntimeError('E3')),
            ):
                resp = client.get(f'/payroll/runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200


class TestCockpitErrorBoundaries:
    """Test error boundaries in the cockpit."""

    def test_cockpit_loads_normally(self, app, client, seed_data):
        """Baseline: cockpit loads without errors."""
        with app.app_context():
            login(client)
            resp = client.get('/payroll/cockpit')
            assert resp.status_code in (200, 302)

    def test_cockpit_loads_when_change_summary_fails(self, app, client, seed_data):
        """Cockpit should still load if change summary fails."""
        with app.app_context():
            login(client)
            with patch('payroll_engine.cockpit.compute_change_summary', side_effect=RuntimeError('Error')):
                resp = client.get('/payroll/cockpit')
                assert resp.status_code in (200, 302)

    def test_cockpit_loads_when_filing_fails(self, app, client, seed_data):
        """Cockpit should still load if filing workspace fails."""
        with app.app_context():
            login(client)
            with patch('payroll_engine.cockpit.build_filing_workspace', side_effect=RuntimeError('Error')):
                resp = client.get('/payroll/cockpit')
                assert resp.status_code in (200, 302)

    def test_cockpit_loads_when_exceptions_fails(self, app, client, seed_data):
        """Cockpit should still load if exceptions fail."""
        with app.app_context():
            login(client)
            with patch('payroll_engine.cockpit.classify_exceptions', side_effect=RuntimeError('Error')):
                resp = client.get('/payroll/cockpit')
                assert resp.status_code in (200, 302)


class TestAPIErrorBoundaries:
    """Test error boundaries in API endpoints."""

    def test_review_api_returns_partial_on_change_summary_failure(self, app, client, seed_data):
        """API should return partial data if change summary fails."""
        with app.app_context():
            trust_cache.invalidate_trust_cache()
            login(client)
            with patch('payroll_engine.api.compute_change_summary', side_effect=RuntimeError('Error')):
                resp = client.get(f'/api/v1/payroll-runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200
                data = resp.get_json()
                assert 'errors' in data
                assert 'change_summary' in data['errors']

    def test_review_api_returns_partial_on_evidence_failure(self, app, client, seed_data):
        """API should return partial data if evidence fails."""
        with app.app_context():
            trust_cache.invalidate_trust_cache()
            login(client)
            with patch('payroll_engine.api.collect_evidence', side_effect=RuntimeError('Error')):
                resp = client.get(f'/api/v1/payroll-runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200
                data = resp.get_json()
                assert 'errors' in data
                assert 'evidence' in data['errors']

    def test_review_api_returns_partial_on_exceptions_failure(self, app, client, seed_data):
        """API should return partial data if exceptions fail."""
        with app.app_context():
            trust_cache.invalidate_trust_cache()
            login(client)
            with patch('payroll_engine.api.classify_exceptions', side_effect=RuntimeError('Error')):
                resp = client.get(f'/api/v1/payroll-runs/{seed_data["run_id"]}/review')
                assert resp.status_code == 200
                data = resp.get_json()
                assert 'errors' in data
                assert 'exceptions' in data['errors']
                assert data['can_approve'] is False  # Conservative

    def test_review_api_can_approve_false_on_exceptions_failure(self, app, client, seed_data):
        """API should return can_approve=False if exceptions can't be computed."""
        with app.app_context():
            trust_cache.invalidate_trust_cache()
            login(client)
            with patch('payroll_engine.api.classify_exceptions', side_effect=RuntimeError('Error')):
                resp = client.get(f'/api/v1/payroll-runs/{seed_data["run_id"]}/review')
                data = resp.get_json()
                assert data['can_approve'] is False
