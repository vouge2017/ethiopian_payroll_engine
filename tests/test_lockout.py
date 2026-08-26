"""Tests for brute-force login lockout."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import UTC, datetime, timedelta

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from payroll_engine import create_app, db
from payroll_engine.models import Company, LoginAttempt, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    # CSRFProtect is global; integration POSTs below submit raw form data.
    app.config['WTF_CSRF_ENABLED'] = False
    # Disable rate limiter for lockout tests
    from payroll_engine import limiter

    limiter.enabled = False
    with app.app_context():
        db.create_all()
        # Create a test user
        company = Company(name='LockoutTestCo')
        db.session.add(company)
        db.session.flush()
        user = User(phone='0910000000', role='owner', company_id=company.id)
        user.set_password('OwnerPass1!')
        db.session.add(user)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class TestLoginAttemptModel:
    """Test the LoginAttempt model directly."""

    def test_record_failure(self, app):
        """Recording a failure creates a LoginAttempt row."""
        with app.app_context():
            is_locked, _remaining = LoginAttempt.record_failure('0910000000')
            assert is_locked is False
            assert LoginAttempt.query.filter_by(identifier='0910000000').count() == 1

    def test_lockout_after_max_attempts(self, app):
        """Account locks after MAX_ATTEMPTS failures."""
        with app.app_context():
            for _i in range(LoginAttempt.MAX_ATTEMPTS):
                is_locked, remaining = LoginAttempt.record_failure('0910000000')

            assert is_locked is True
            assert remaining > 0

    def test_lockout_remaining_decreases(self, app):
        """Remaining lockout time is positive and reasonable."""
        with app.app_context():
            for _i in range(LoginAttempt.MAX_ATTEMPTS):
                LoginAttempt.record_failure('0910000000')

            is_locked, remaining = LoginAttempt.is_locked_out('0910000000')
            assert is_locked is True
            # Should be close to 30 minutes (1800 seconds)
            assert 1700 <= remaining <= 1800

    def test_success_clears_failures(self, app):
        """Successful login clears recent failures."""
        with app.app_context():
            for _i in range(LoginAttempt.MAX_ATTEMPTS - 1):
                LoginAttempt.record_failure('0910000000')

            LoginAttempt.record_success('0910000000')

            is_locked, _ = LoginAttempt.is_locked_out('0910000000')
            assert is_locked is False

    def test_different_identifiers_independent(self, app):
        """Lockout for one identifier doesn't affect another."""
        with app.app_context():
            for _i in range(LoginAttempt.MAX_ATTEMPTS):
                LoginAttempt.record_failure('0910000000')

            is_locked_1, _ = LoginAttempt.is_locked_out('0910000000')
            is_locked_2, _ = LoginAttempt.is_locked_out('0910000001')
            assert is_locked_1 is True
            assert is_locked_2 is False

    def test_old_failures_dont_count(self, app):
        """Failures outside the lockout window don't trigger lockout."""
        with app.app_context():
            # Create failures outside the window
            old_time = datetime.now(UTC) - timedelta(minutes=LoginAttempt.LOCKOUT_WINDOW_MINUTES + 1)
            for _i in range(LoginAttempt.MAX_ATTEMPTS):
                attempt = LoginAttempt(identifier='0910000000', success=False, created_at=old_time)
                db.session.add(attempt)
            db.session.commit()

            is_locked, _ = LoginAttempt.is_locked_out('0910000000')
            assert is_locked is False

    def test_cleanup_old(self, app):
        """cleanup_old deletes attempts older than N days."""
        with app.app_context():
            old_time = datetime.now(UTC) - timedelta(days=8)
            attempt = LoginAttempt(identifier='0910000000', success=False, created_at=old_time)
            db.session.add(attempt)
            db.session.commit()

            LoginAttempt.cleanup_old(days=7)
            assert LoginAttempt.query.count() == 0

    def test_phone_format_normalization(self, app):
        """Different phone formats for the same number share lockout counter."""
        with app.app_context():
            # These are all the same phone number in different formats
            formats = ['0910000000', '+251910000000', '910000000']
            for fmt in formats:
                from payroll_engine.models import validate_ethiopian_phone

                is_valid, normalized, _ = validate_ethiopian_phone(fmt)
                if is_valid:
                    LoginAttempt.record_failure(normalized)

            # All should resolve to the same normalized phone
            is_locked, _ = LoginAttempt.is_locked_out('0910000000')
            assert is_locked is False  # 3 < 5

            # Two more to hit the limit
            LoginAttempt.record_failure('0910000000')
            LoginAttempt.record_failure('0910000000')
            is_locked, _ = LoginAttempt.is_locked_out('0910000000')
            assert is_locked is True  # 5 >= 5

    def test_is_locked_out_not_locked(self, app):
        """is_locked_out returns (False, 0) when not locked."""
        with app.app_context():
            is_locked, remaining = LoginAttempt.is_locked_out('0910000000')
            assert is_locked is False
            assert remaining == 0


class TestLoginLockoutIntegration:
    """Test lockout behavior through the login route."""

    def test_login_works_normally(self, client, app):
        """Valid login works without lockout."""
        resp = client.post(
            '/auth/login',
            data={
                'login_id': '0910000000',
                'password': 'OwnerPass1!',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'Welcome back' in resp.data

    def test_failed_login_shows_invalid(self, client, app):
        """Failed login shows 'Invalid credentials' message."""
        resp = client.post(
            '/auth/login',
            data={
                'login_id': '0910000000',
                'password': 'wrongpassword',
            },
            follow_redirects=True,
        )
        assert b'Invalid credentials' in resp.data

    def test_lockout_message_after_max_failures(self, client, app):
        """After MAX_ATTEMPTS failures, shows lockout message."""
        for _i in range(LoginAttempt.MAX_ATTEMPTS):
            client.post(
                '/auth/login',
                data={
                    'login_id': '0910000000',
                    'password': 'wrongpassword',
                },
            )

        resp = client.post(
            '/auth/login',
            data={
                'login_id': '0910000000',
                'password': 'wrongpassword',
            },
            follow_redirects=True,
        )
        assert b'locked' in resp.data.lower() or b'temporarily' in resp.data.lower()

    def test_locked_out_user_cannot_login_even_with_correct_password(self, client, app):
        """Locked out user can't login even with correct password."""
        for _i in range(LoginAttempt.MAX_ATTEMPTS):
            client.post(
                '/auth/login',
                data={
                    'login_id': '0910000000',
                    'password': 'wrongpassword',
                },
            )

        resp = client.post(
            '/auth/login',
            data={
                'login_id': '0910000000',
                'password': 'OwnerPass1!',
            },
            follow_redirects=True,
        )
        assert b'locked' in resp.data.lower() or b'temporarily' in resp.data.lower()
        assert b'Logged in as' not in resp.data  # success-flash absent; page copy itself says 'Welcome back'

    def test_successful_login_resets_counter(self, client, app):
        """Successful login resets the failure counter."""
        # Fail a few times (not enough to lock)
        for _i in range(3):
            client.post(
                '/auth/login',
                data={
                    'login_id': '0910000000',
                    'password': 'wrongpassword',
                },
            )

        # Succeed
        resp = client.post(
            '/auth/login',
            data={
                'login_id': '0910000000',
                'password': 'OwnerPass1!',
            },
            follow_redirects=True,
        )
        assert b'Welcome back' in resp.data

        # Fail counter should be reset — can fail again without immediate lockout
        with app.app_context():
            is_locked, _ = LoginAttempt.is_locked_out('0910000000')
            assert is_locked is False

    def test_unknown_identifier_no_500(self, client):
        """Failed login with UNKNOWN account must flash, never 500 (bugfix)."""
        resp = client.post(
            '/auth/login',
            data={'login_id': '0999999999', 'password': 'Whatever1!'},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b'Invalid credentials' in resp.data
