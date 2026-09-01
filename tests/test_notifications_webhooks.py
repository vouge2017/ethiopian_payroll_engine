"""
Tests for notifications.py and webhooks.py.

Covers:
- Notification created on leave request
- Notification is flush (not commit) inside payroll transaction
- Webhook fires on payroll approval
- Webhook handles missing company gracefully
- Webhook handles missing webhook_url gracefully
- WhatsApp send skipped when not configured
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    Leave,
    Notification,
    User,
    UserCompany,
)
from payroll_engine.notifications import (
    create_in_app_notification,
    notify,
    notify_leave_decision,
    notify_payroll_approved,
    send_whatsapp,
)
from payroll_engine.webhooks import _deliver, _sign_payload, fire_webhook


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


def _setup(app):
    """Create company, users, employee, and UserCompany records.

    The employee's phone must match emp_user's phone so
    notify_leave_decision can find the user via phone lookup.
    """
    with app.app_context():
        company = Company(
            name='NotifTestCo',
            webhook_url='https://example.com/hook',
            webhook_secret='testsecret',
        )
        db.session.add(company)
        db.session.flush()

        # Owner — linked via UserCompany
        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('OwnerPass1!')
        db.session.add(owner)
        db.session.flush()

        owner_uc = UserCompany(
            user_id=owner.id,
            company_id=company.id,
            role='owner',
        )
        db.session.add(owner_uc)

        # Employee user — phone must match the Employee record's phone
        emp_user = User(phone='0911111111', role='employee', company_id=company.id)
        emp_user.set_password('EmpPass1!')
        db.session.add(emp_user)
        db.session.flush()

        emp_uc = UserCompany(
            user_id=emp_user.id,
            company_id=company.id,
            role='employee',
        )
        db.session.add(emp_uc)

        emp = Employee(
            employee_id='EMP001',
            name='Tigist Haile',
            phone='0911111111',
            department='Finance',
            position='Accountant',
            basic_salary=10000,
            company_id=company.id,
            user_id=emp_user.id,
        )
        db.session.add(emp)
        db.session.commit()

        return company.id, owner.id, emp_user.id, emp.id


# ─── Notification tests ───


class TestCreateInAppNotification:
    """Tests for create_in_app_notification."""

    def test_creates_notification_in_db(self, app):
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            notif = create_in_app_notification(cid, owner_id, 'Test message', 'info', '/test')
            assert notif.id is not None
            assert notif.message == 'Test message'
            assert notif.type == 'info'
            assert notif.link == '/test'
            assert notif.is_read is False

    def test_flush_not_commit(self, app):
        """Notification should be flushed, not committed. Caller owns the transaction."""
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            notif = create_in_app_notification(cid, owner_id, 'Flush test')
            assert notif.id is not None
            # Rollback — the notification should disappear
            db.session.rollback()
            found = Notification.query.filter_by(message='Flush test', company_id=cid).first()
            assert found is None


class TestNotify:
    """Tests for the notify() dispatcher."""

    def test_creates_in_app_notification(self, app):
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            notify(cid, owner_id, 'Dispatch test', notif_type='warning')
            notif = Notification.query.filter_by(user_id=owner_id, company_id=cid).first()
            assert notif is not None
            assert notif.type == 'warning'

    @patch('payroll_engine.notifications.send_whatsapp')
    def test_calls_whatsapp_when_phone_provided(self, mock_wa, app):
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        mock_wa.return_value = True
        with app.app_context():
            notify(cid, owner_id, 'WA test', employee_phone='0911111111')
            mock_wa.assert_called_once_with('0911111111', 'WA test')

    @patch('payroll_engine.notifications.send_whatsapp')
    def test_skips_whatsapp_when_no_phone(self, mock_wa, app):
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            notify(cid, owner_id, 'No WA test')
            mock_wa.assert_not_called()


class TestWhatsApp:
    """Tests for send_whatsapp."""

    def test_skips_when_not_configured(self):
        import payroll_engine.notifications as notif_mod

        orig = notif_mod.WHATSAPP_ENABLED
        notif_mod.WHATSAPP_ENABLED = False
        result = send_whatsapp('0911111111', 'test')
        assert result is False
        notif_mod.WHATSAPP_ENABLED = orig

    def test_returns_false_when_no_phone(self):
        import payroll_engine.notifications as notif_mod

        orig = notif_mod.WHATSAPP_ENABLED
        notif_mod.WHATSAPP_ENABLED = True
        result = send_whatsapp('', 'test')
        assert result is False
        notif_mod.WHATSAPP_ENABLED = orig

    @patch('requests.post')
    def test_sends_to_normalized_phone(self, mock_post, app):
        import payroll_engine.notifications as notif_mod

        orig = notif_mod.WHATSAPP_ENABLED
        notif_mod.WHATSAPP_ENABLED = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = send_whatsapp('0911111111', 'Hello')
        assert result is True
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['to'] == '251911111111'
        notif_mod.WHATSAPP_ENABLED = orig

    @patch('requests.post')
    def test_returns_false_on_api_error(self, mock_post):
        import payroll_engine.notifications as notif_mod

        orig = notif_mod.WHATSAPP_ENABLED
        notif_mod.WHATSAPP_ENABLED = True

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = 'Bad request'
        mock_post.return_value = mock_resp

        result = send_whatsapp('0911111111', 'Hello')
        assert result is False
        notif_mod.WHATSAPP_ENABLED = orig

    @patch('requests.post')
    def test_returns_false_on_network_error(self, mock_post):
        import payroll_engine.notifications as notif_mod

        orig = notif_mod.WHATSAPP_ENABLED
        notif_mod.WHATSAPP_ENABLED = True

        mock_post.side_effect = Exception('Connection refused')
        result = send_whatsapp('0911111111', 'Hello')
        assert result is False
        notif_mod.WHATSAPP_ENABLED = orig


class TestNotifyPayrollApproved:
    """Tests for notify_payroll_approved."""

    def test_notifies_owners_and_accountants(self, app):
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            employees_data = [{'name': 'Tigist', 'phone': '0911111111', 'net': 8000}]
            notify_payroll_approved(cid, employees_data, 'PR-2026-07-001')

            notif = Notification.query.filter_by(user_id=owner_id, company_id=cid).first()
            assert notif is not None
            assert 'PR-2026-07-001' in notif.message
            assert notif.type == 'success'

    @patch('requests.post')
    def test_sends_whatsapp_to_employees(self, mock_post, app):
        import payroll_engine.notifications as notif_mod

        orig = notif_mod.WHATSAPP_ENABLED
        notif_mod.WHATSAPP_ENABLED = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        cid, _owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            employees_data = [{'name': 'Tigist', 'phone': '0911111111', 'net': 8000}]
            notify_payroll_approved(cid, employees_data, 'PR-2026-07-001')
            mock_post.assert_called()
            wa_body = mock_post.call_args[1]['json']['text']['body']
            assert '8,000' in wa_body

        notif_mod.WHATSAPP_ENABLED = orig


class TestNotifyLeaveDecision:
    """Tests for notify_leave_decision."""

    def test_notification_created_on_leave_approval(self, app):
        cid, owner_id, emp_uid, emp_id = _setup(app)
        with app.app_context():
            leave = Leave(
                company_id=cid,
                employee_id=emp_id,
                leave_type='annual',
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 5),
                days_requested=5,
                status='approved',
                approved_by=owner_id,
            )
            db.session.add(leave)
            db.session.commit()

            notify_leave_decision(leave, 'approved', manager_name='Admin')

            notif = Notification.query.filter_by(user_id=emp_uid, company_id=cid).first()
            assert notif is not None
            assert 'approved' in notif.message
            assert notif.type == 'success'

    def test_notification_created_on_leave_rejection(self, app):
        cid, _owner_id, emp_uid, emp_id = _setup(app)
        with app.app_context():
            leave = Leave(
                company_id=cid,
                employee_id=emp_id,
                leave_type='sick',
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 3),
                days_requested=3,
                status='rejected',
            )
            db.session.add(leave)
            db.session.commit()

            notify_leave_decision(leave, 'rejected')

            notif = Notification.query.filter_by(user_id=emp_uid, company_id=cid).first()
            assert notif is not None
            assert 'rejected' in notif.message
            assert notif.type == 'warning'

    @patch('requests.post')
    def test_whatsapp_sent_on_leave_decision(self, mock_post, app):
        import payroll_engine.notifications as notif_mod

        orig = notif_mod.WHATSAPP_ENABLED
        notif_mod.WHATSAPP_ENABLED = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        cid, _owner_id, _emp_uid, emp_id = _setup(app)
        with app.app_context():
            leave = Leave(
                company_id=cid,
                employee_id=emp_id,
                leave_type='annual',
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 5),
                days_requested=5,
                status='approved',
            )
            db.session.add(leave)
            db.session.commit()

            notify_leave_decision(leave, 'approved')
            mock_post.assert_called()
            wa_body = mock_post.call_args[1]['json']['text']['body']
            assert 'annual' in wa_body

        notif_mod.WHATSAPP_ENABLED = orig

    def test_no_notification_when_employee_not_found(self, app):
        """If employee is deleted, no crash, no notification."""
        cid, _owner_id, emp_uid, _emp_id = _setup(app)
        with app.app_context():
            leave = Leave(
                company_id=cid,
                employee_id=9999,
                leave_type='annual',
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 5),
                days_requested=5,
                status='approved',
            )
            db.session.add(leave)
            db.session.commit()

            notify_leave_decision(leave, 'approved')
            notif = Notification.query.filter_by(user_id=emp_uid, company_id=cid).first()
            assert notif is None


# ─── Webhook tests ───


class TestWebhookSigning:
    """Tests for HMAC signature generation."""

    def test_sign_payload_returns_hex(self):
        sig = _sign_payload(b'{"test": true}', 'mysecret')
        assert isinstance(sig, str)
        assert len(sig) == 64

    def test_sign_payload_deterministic(self):
        sig1 = _sign_payload(b'{"test": true}', 'mysecret')
        sig2 = _sign_payload(b'{"test": true}', 'mysecret')
        assert sig1 == sig2

    def test_sign_payload_different_secret(self):
        sig1 = _sign_payload(b'{"test": true}', 'secret1')
        sig2 = _sign_payload(b'{"test": true}', 'secret2')
        assert sig1 != sig2


class TestFireWebhook:
    """Tests for fire_webhook."""

    @patch('payroll_engine.webhooks.threading.Thread')
    def test_fires_webhook_for_configured_company(self, mock_thread, app):
        cid, _owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            fire_webhook(cid, 'payroll.approved', {'run_id': 1})
            mock_thread.assert_called_once()
            assert mock_thread.call_args[1]['daemon'] is True

    @patch('payroll_engine.webhooks.threading.Thread')
    def test_webhook_url_passed_to_thread(self, mock_thread, app):
        cid, _owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            fire_webhook(cid, 'payroll.approved', {'run_id': 1})
            args = mock_thread.call_args[1]['args']
            url, payload, secret = args
            assert url == 'https://example.com/hook'
            assert secret == 'testsecret'
            assert payload['event'] == 'payroll.approved'
            assert payload['data']['run_id'] == 1

    @patch('payroll_engine.webhooks.threading.Thread')
    def test_skips_when_company_has_no_webhook_url(self, mock_thread, app):
        with app.app_context():
            company = Company(name='NoHookCo')
            db.session.add(company)
            db.session.commit()

            fire_webhook(company.id, 'payroll.approved', {'run_id': 1})
            mock_thread.assert_not_called()

    @patch('payroll_engine.webhooks.threading.Thread')
    def test_skips_when_company_not_found(self, mock_thread, app):
        with app.app_context():
            fire_webhook(99999, 'payroll.approved', {'run_id': 1})
            mock_thread.assert_not_called()

    @patch('payroll_engine.webhooks.threading.Thread')
    def test_skips_when_webhooks_disabled(self, mock_thread, app):
        import payroll_engine.webhooks as wh_mod

        orig = wh_mod.WEBHOOKS_ENABLED
        wh_mod.WEBHOOKS_ENABLED = False
        cid, _owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            fire_webhook(cid, 'payroll.approved', {'run_id': 1})
            mock_thread.assert_not_called()
        wh_mod.WEBHOOKS_ENABLED = orig


class TestWebhookDelivery:
    """Tests for the _deliver function."""

    @patch('requests.post')
    def test_deliver_sends_post_request(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        payload = {
            'event': 'test',
            'timestamp': '2026-01-01T00:00:00',
            'company_id': 1,
            'data': {},
        }
        _deliver('https://example.com/hook', payload, 'secret')

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://example.com/hook'
        assert call_args[1]['timeout'] == 10
        assert 'X-Webhook-Signature' in call_args[1]['headers']
        assert call_args[1]['headers']['X-Webhook-Signature'].startswith('sha256=')

    @patch('requests.post')
    def test_deliver_without_secret(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        payload = {'event': 'test', 'timestamp': '', 'data': {}}
        _deliver('https://example.com/hook', payload, None)

        call_args = mock_post.call_args
        assert 'X-Webhook-Signature' not in call_args[1]['headers']

    @patch('requests.post')
    def test_deliver_handles_network_error(self, mock_post):
        """Network errors should be caught, not raised."""
        mock_post.side_effect = Exception('Connection refused')
        payload = {'event': 'test', 'timestamp': '', 'data': {}}
        # Should not raise
        _deliver('https://example.com/hook', payload, 'secret')


class TestNotificationInPayrollTransaction:
    """Verify notifications are flush-not-commit inside payroll flow."""

    def test_notification_visible_in_same_transaction(self, app):
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            create_in_app_notification(cid, owner_id, 'In-tx test')
            found = Notification.query.filter_by(message='In-tx test', company_id=cid).first()
            assert found is not None

    def test_notification_rolled_back_on_rollback(self, app):
        """If the caller rolls back, the notification should disappear."""
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            create_in_app_notification(cid, owner_id, 'Rollback test')
            db.session.rollback()
            found = Notification.query.filter_by(message='Rollback test', company_id=cid).first()
            assert found is None

    def test_notification_committed_with_payroll(self, app):
        """When payroll commits, notification should be committed too."""
        cid, owner_id, _emp_uid, _emp_id = _setup(app)
        with app.app_context():
            create_in_app_notification(cid, owner_id, 'Commit test')
            db.session.commit()
            db.session.expire_all()
            found = Notification.query.filter_by(message='Commit test', company_id=cid).first()
            assert found is not None
