"""
Push Notification Service

Web Push notifications for EthioPayroll.
Uses the Web Push Protocol (VAPID) for PWA push notifications.

Setup:
    1. Generate VAPID keys: python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.private_pem()); print(v.public_pem())"
    2. Set VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY env vars
    3. Set VAPID_CLAIMS_EMAIL to your admin email

Usage:
    from payroll_engine.push import send_push_notification
    send_push_notification(user_id, "Payslip Ready", "Your July payslip is ready to view.", url="/portal/payslips")
"""

import json
import logging
import os

logger = logging.getLogger('payroll_engine.push')

# VAPID keys (set via env vars)
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_CLAIMS_EMAIL = os.environ.get('VAPID_CLAIMS_EMAIL', 'mailto:admin@ethiopayroll.com')


def get_vapid_public_key():
    """Get VAPID public key for client-side subscription."""
    return VAPID_PUBLIC_KEY


def save_subscription(user_id, subscription_info):
    """Save a push subscription for a user to the database."""
    from payroll_engine import db
    from payroll_engine.models import Notification, PushSubscription, User

    endpoint = subscription_info.get('endpoint')
    if not endpoint:
        return False

    # Look up existing subscription by endpoint
    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.user_id = user_id
        existing.subscription_json = subscription_info
    else:
        sub = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            subscription_json=subscription_info
        )
        db.session.add(sub)

    # Fetch user to get company_id
    user = db.session.get(User, user_id)
    company_id = user.company_id if user else None


    # Also store in-app notification
    notif = Notification(company_id=company_id, user_id=user_id, message='Push notifications enabled', type='system', is_read=True)
    db.session.add(notif)
    db.session.commit()

    return True


def send_push_notification(user_id, title, body, url='/', notif_type='info'):
    """Send a push notification to all user's registered devices.

    Also creates an in-app notification as fallback.
    """
    from payroll_engine import db
    from payroll_engine.models import Notification, PushSubscription, User

    # Fetch user to get company_id
    user = db.session.get(User, user_id)
    company_id = user.company_id if user else None

    # Always create in-app notification
    notif = Notification(
        company_id=company_id, user_id=user_id, message=f"{title}: {body}" if body else title, type=notif_type, link=url
    )
    db.session.add(notif)
    db.session.commit()

    # Get all active subscriptions for the user
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions or not VAPID_PRIVATE_KEY:
        return False

    success = False
    for sub in subscriptions:
        try:
            from pywebpush import WebPushException, webpush

            payload = json.dumps(
                {
                    'title': title,
                    'body': body,
                    'url': url,
                }
            )

            webpush(
                subscription_info=sub.subscription_json,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    'sub': VAPID_CLAIMS_EMAIL,
                },
            )
            success = True

        except ImportError:
            logger.warning('pywebpush not installed — push notifications disabled')
            return False
        except WebPushException as e:
            # Handle stale/expired subscription (410 Gone / 404 Not Found)
            # Delete stale subscription from database
            if e.response is not None and e.response.status_code in (410, 404):
                try:
                    db.session.delete(sub)
                    db.session.commit()
                    logger.info(f'Deleted stale push subscription for user {user_id}')
                except Exception as db_err:
                    db.session.rollback()
                    logger.error(f'Failed to delete stale push subscription: {db_err}')
            else:
                logger.error(f'Push notification WebPushException for user {user_id}: {e}')
        except Exception as e:
            logger.error(f'Push notification failed for user {user_id}: {e}')

    return success


def notify_payslip_ready(user_id, employee_name, period, payslip_id):
    """Notify user that their payslip is ready."""
    send_push_notification(
        user_id=user_id,
        title='Payslip Ready',
        body=f'{employee_name} — {period} payslip is ready to view.',
        url=f'/portal/payslips/{payslip_id}',
        notif_type='payslip',
    )


def notify_payroll_approved(user_id, period, employee_count):
    """Notify owner that payroll was approved."""
    send_push_notification(
        user_id=user_id,
        title='Payroll Approved',
        body=f'{period} payroll approved for {employee_count} employees.',
        url='/payroll/runs',
        notif_type='payroll',
    )


def notify_leave_request(user_id, employee_name, leave_type, days):
    """Notify owner of a new leave request."""
    send_push_notification(
        user_id=user_id,
        title='Leave Request',
        body=f'{employee_name} requested {days} days of {leave_type} leave.',
        url='/employees/leave',
        notif_type='leave',
    )


def notify_deadline_approaching(user_id, deadline_name, days_left):
    """Notify user of approaching compliance deadline."""
    send_push_notification(
        user_id=user_id,
        title='Deadline Approaching',
        body=f'{deadline_name} is due in {days_left} days.',
        url='/reports',
        notif_type='deadline',
    )
