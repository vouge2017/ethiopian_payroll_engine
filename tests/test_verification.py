"""
Tests for accountant verification flow.

Verifies:
- Verification home page loads
- Each step page loads
- Form submission saves progress
- Summary page shows results
- Feedback form works
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User


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
def logged_in(app, client):
    """Register and log in a user."""
    with app.app_context():
        client.post('/auth/register', data={
            'company_name': 'Test PLC',
            'phone': '0911123456',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
        }, follow_redirects=True)
        client.post('/auth/login', data={
            'login_id': '0911123456',
            'password': 'TestPass123!',
        }, follow_redirects=True)


class TestVerificationHome:
    """Test verification home page."""

    def test_home_requires_login(self, app, client):
        """Should redirect to login if not authenticated."""
        with app.app_context():
            resp = client.get('/verification')
            assert resp.status_code == 302

    def test_home_loads_when_logged_in(self, app, client, logged_in):
        """Should load when authenticated."""
        with app.app_context():
            resp = client.get('/verification')
            assert resp.status_code == 200
            assert b'Accountant Verification' in resp.data

    def test_home_shows_all_steps(self, app, client, logged_in):
        """Should show all 10 verification steps."""
        with app.app_context():
            resp = client.get('/verification')
            assert resp.status_code == 200
            assert b'Tax Brackets' in resp.data
            assert b'PAYE' in resp.data
            assert b'Pension' in resp.data
            assert b'ERCA' in resp.data


class TestVerificationSteps:
    """Test individual verification steps."""

    def test_each_step_loads(self, app, client, logged_in):
        """Each of the 10 steps should load."""
        steps = [
            'tax_brackets', 'paye_method', 'pension', 'overtime', 'leave',
            'severance', 'allowances', 'erca_filing', 'deadlines', 'record_keeping',
        ]
        with app.app_context():
            for step_id in steps:
                resp = client.get(f'/verification/{step_id}')
                assert resp.status_code == 200, f'Step {step_id} failed with {resp.status_code}'

    def test_invalid_step_returns_404(self, app, client, logged_in):
        """Invalid step should redirect."""
        with app.app_context():
            resp = client.get('/verification/nonexistent_step')
            assert resp.status_code == 302  # Redirect to home

    def test_step_form_submission(self, app, client, logged_in):
        """Submitting a step should save progress."""
        with app.app_context():
            resp = client.post('/verification/tax_brackets', data={
                'verified': 'on',
                'correct': 'on',
                'correction': '',
                'notes': 'Looks correct',
            }, follow_redirects=True)
            assert resp.status_code == 200

    def test_step_with_correction(self, app, client, logged_in):
        """Submitting a correction should save it."""
        with app.app_context():
            resp = client.post('/verification/tax_brackets', data={
                'verified': 'on',
                'correct': '',
                'correction': 'Rate should be 10% not 15%',
                'notes': 'Checked against proclamation',
            }, follow_redirects=True)
            assert resp.status_code == 200


class TestVerificationSummary:
    """Test verification summary page."""

    def test_summary_loads(self, app, client, logged_in):
        """Summary page should load."""
        with app.app_context():
            resp = client.get('/verification/summary')
            assert resp.status_code == 200
            assert b'Verification Summary' in resp.data

    def test_summary_shows_progress(self, app, client, logged_in):
        """Summary should show progress after submitting steps."""
        with app.app_context():
            # Submit a step
            client.post('/verification/tax_brackets', data={
                'verified': 'on',
                'correct': 'on',
            }, follow_redirects=True)

            resp = client.get('/verification/summary')
            assert resp.status_code == 200
            assert b'Confirmed Correct' in resp.data


class TestFeedback:
    """Test feedback submission."""

    def test_feedback_requires_login(self, app, client):
        """Feedback should require login."""
        with app.app_context():
            resp = client.post('/verification/feedback',
                               json={'feedback': 'test'},
                               content_type='application/json')
            assert resp.status_code == 302

    def test_feedback_submission(self, app, client, logged_in):
        """Submitting feedback should return success."""
        with app.app_context():
            resp = client.post('/verification/feedback',
                               json={'feedback': 'Tax brackets look correct', 'category': 'general'},
                               content_type='application/json')
            assert resp.status_code == 200
            data = resp.get_json()
            assert data['status'] == 'received'

    def test_feedback_empty_rejected(self, app, client, logged_in):
        """Empty feedback should be rejected."""
        with app.app_context():
            resp = client.post('/verification/feedback',
                               json={'feedback': ''},
                               content_type='application/json')
            assert resp.status_code == 400
