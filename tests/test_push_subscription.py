import sys
from unittest.mock import patch, MagicMock

# Mock pywebpush and its WebPushException before any imports
mock_pywebpush = MagicMock()
class MockWebPushException(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response

mock_pywebpush.WebPushException = MockWebPushException
sys.modules['pywebpush'] = mock_pywebpush

import pytest
from payroll_engine import create_app, db
from payroll_engine.models import User, Company, PushSubscription, Notification
from payroll_engine.push import save_subscription, send_push_notification

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        # Seed company and user
        company = Company(name='Test Company')
        db.session.add(company)
        db.session.flush()

        user = User(phone='0911000000', email='test@example.com', company_id=company.id)
        user.set_password('Password123!')
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

def test_save_subscription_creates_new(app):
    with app.app_context():
        user = User.query.filter_by(phone='0911000000').first()
        sub_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/token123',
            'keys': {'auth': 'auth123', 'p256dh': 'p256dh123'}
        }

        # Save subscription
        res = save_subscription(user.id, sub_info)
        assert res is True

        # Verify stored in DB
        sub = PushSubscription.query.filter_by(user_id=user.id).first()
        assert sub is not None
        assert sub.endpoint == 'https://fcm.googleapis.com/fcm/send/token123'
        assert sub.subscription_json == sub_info

        # Verify in-app notification created
        notif = Notification.query.filter_by(user_id=user.id).first()
        assert notif is not None
        assert 'Push notifications enabled' in notif.message

def test_save_subscription_updates_existing(app):
    with app.app_context():
        user = User.query.filter_by(phone='0911000000').first()
        sub_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/token123',
            'keys': {'auth': 'auth123', 'p256dh': 'p256dh123'}
        }

        # Save initial
        save_subscription(user.id, sub_info)

        # Save again with same endpoint but updated keys or different user
        updated_sub_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/token123',
            'keys': {'auth': 'new_auth', 'p256dh': 'new_p256dh'}
        }
        res = save_subscription(user.id, updated_sub_info)
        assert res is True

        # Should NOT duplicate, only update
        subs = PushSubscription.query.filter_by(user_id=user.id).all()
        assert len(subs) == 1
        assert subs[0].subscription_json == updated_sub_info

@patch('payroll_engine.push.VAPID_PRIVATE_KEY', 'some-private-key')
def test_send_push_notification_success(app):
    # Reset mock
    mock_pywebpush.webpush.reset_mock()

    with app.app_context():
        user = User.query.filter_by(phone='0911000000').first()
        sub_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/token123',
            'keys': {'auth': 'auth123', 'p256dh': 'p256dh123'}
        }
        save_subscription(user.id, sub_info)

        # Send push
        res = send_push_notification(user.id, 'Test Title', 'Test Body')
        assert res is True

        # Verify webpush called with correct params
        mock_pywebpush.webpush.assert_called_once()
        kwargs = mock_pywebpush.webpush.call_args[1]
        assert kwargs['subscription_info'] == sub_info
        assert 'Test Title' in kwargs['data']

@patch('payroll_engine.push.VAPID_PRIVATE_KEY', 'some-private-key')
def test_send_push_notification_cleanup_on_gone(app):
    # Reset mock
    mock_pywebpush.webpush.reset_mock()

    # Configure webpush mock to raise WebPushException with 410 Gone response
    mock_response = MagicMock()
    mock_response.status_code = 410
    mock_pywebpush.webpush.side_effect = MockWebPushException('Subscription expired', response=mock_response)

    with app.app_context():
        user = User.query.filter_by(phone='0911000000').first()
        sub_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/token123',
            'keys': {'auth': 'auth123', 'p256dh': 'p256dh123'}
        }
        save_subscription(user.id, sub_info)

        # Ensure subscription is in DB
        assert PushSubscription.query.filter_by(user_id=user.id).count() == 1

        # Send push (should fail but handle gracefully)
        res = send_push_notification(user.id, 'Test Title', 'Test Body')
        assert res is False

        # Verify subscription was deleted from DB
        assert PushSubscription.query.filter_by(user_id=user.id).count() == 0
