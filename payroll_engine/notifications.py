"""Notification service — in-app + WhatsApp delivery.

Usage:
    from payroll_engine.notifications import notify
    notify(company_id, user_id, "Payroll approved", employee_phone="+251911234567")
"""
import os
import logging
from payroll_engine import db
from payroll_engine.models import Notification

logger = logging.getLogger('payroll_engine.notifications')

# WhatsApp Business API configuration (set env vars to enable)
WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', '')
WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN', '')
WHATSAPP_ENABLED = bool(WHATSAPP_API_URL and WHATSAPP_API_TOKEN)


def create_in_app_notification(company_id, user_id, message, notif_type='info', link=None):
    """Create an in-app notification."""
    notif = Notification(
        company_id=company_id,
        user_id=user_id,
        message=message,
        type=notif_type,
        link=link,
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def send_whatsapp(phone, message):
    """Send a WhatsApp message via the Business API.

    Returns True if sent, False if skipped (not configured) or failed.
    """
    if not WHATSAPP_ENABLED:
        logger.debug('WhatsApp not configured, skipping')
        return False

    if not phone:
        logger.warning('No phone number provided for WhatsApp')
        return False

    # Normalize phone
    phone = phone.replace(' ', '').replace('+', '')
    if phone.startswith('0'):
        phone = '251' + phone[1:]

    try:
        import requests
        resp = requests.post(
            WHATSAPP_API_URL,
            headers={
                'Authorization': f'Bearer {WHATSAPP_API_TOKEN}',
                'Content-Type': 'application/json',
            },
            json={
                'messaging_product': 'whatsapp',
                'to': phone,
                'type': 'text',
                'text': {'body': message},
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            logger.info(f'WhatsApp sent to {phone}')
            return True
        else:
            logger.error(f'WhatsApp API error {resp.status_code}: {resp.text}')
            return False
    except Exception as e:
        logger.error(f'WhatsApp send failed: {e}')
        return False


def notify(company_id, user_id, message, notif_type='info', link=None,
           employee_phone=None, whatsapp_message=None):
    """Send notification via all channels: in-app + WhatsApp (if configured).

    Args:
        company_id: Company ID
        user_id: User ID for in-app notification
        message: In-app notification message
        notif_type: Notification type (info, success, warning)
        link: Optional link for the notification
        employee_phone: Employee phone for WhatsApp delivery
        whatsapp_message: WhatsApp message (defaults to in-app message)
    """
    # Always create in-app notification
    create_in_app_notification(company_id, user_id, message, notif_type, link)

    # Send WhatsApp if phone provided
    if employee_phone:
        wa_msg = whatsapp_message or message
        send_whatsapp(employee_phone, wa_msg)


def notify_payroll_approved(company_id, employees_data, run_reference):
    """Send notifications when payroll is approved.

    Args:
        company_id: Company ID
        employees_data: List of dicts with employee info and payslip data
        run_reference: Payroll run reference (e.g., "PR-2026-07-001")
    """
    from payroll_engine.models import User, UserCompany

    # Notify all owners/accountants in the company
    users = User.query.join(UserCompany).filter(
        UserCompany.company_id == company_id,
        User.role.in_(['owner', 'accountant'])
    ).all()

    for user in users:
        notify(
            company_id=company_id,
            user_id=user.id,
            message=f'Payroll {run_reference} has been approved. {len(employees_data)} payslips generated.',
            notif_type='success',
            link=f'/payroll/runs',  # Will be resolved by the template
        )

    # Send WhatsApp to each employee
    for emp_data in employees_data:
        phone = emp_data.get('phone')
        name = emp_data.get('name', 'Employee')
        net_pay = emp_data.get('net', 0)

        if phone:
            wa_msg = (
                f'Hello {name},\n\n'
                f'Your salary of ETB {net_pay:,.2f} has been processed.\n'
                f'Payslip: {run_reference}\n\n'
                f'Log in to view your detailed payslip.'
            )
            send_whatsapp(phone, wa_msg)


def notify_leave_decision(leave, decision, manager_name=None):
    """Send notification when a leave request is approved or rejected.

    Args:
        leave: Leave object
        decision: 'approved' or 'rejected'
        manager_name: Name of the manager who made the decision
    """
    from payroll_engine.models import Employee, User, UserCompany

    emp = Employee.query.get(leave.employee_id)
    if not emp:
        return

    # Find the user linked to this employee
    user = User.query.filter_by(phone=emp.phone).first()
    if user:
        msg = (
            f'Your {leave.leave_type} leave request '
            f'({leave.start_date} to {leave.end_date}) has been {decision}.'
        )
        if manager_name:
            msg += f' by {manager_name}.'

        notify(
            company_id=leave.company_id,
            user_id=user.id,
            message=msg,
            notif_type='success' if decision == 'approved' else 'warning',
        )

    # WhatsApp to employee
    if emp.phone:
        wa_msg = (
            f'Hello {emp.name},\n\n'
            f'Your {leave.leave_type} leave request '
            f'({leave.start_date} to {leave.end_date}) has been {decision}.\n\n'
            f'Log in for details.'
        )
        send_whatsapp(emp.phone, wa_msg)
