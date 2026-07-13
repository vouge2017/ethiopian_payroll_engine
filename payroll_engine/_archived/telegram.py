"""
Telegram Notification System

Sends notifications to employees and owners via Telegram Bot API.

Features:
- Payslip notifications
- Leave request status updates
- Deadline reminders (ERCA, pension)
- Salary credit notifications
- Custom messages

Setup:
1. Create a Telegram bot via @BotFather
2. Set TELEGRAM_BOT_TOKEN environment variable
3. Users link their Telegram account via /start command

Uses Telegram Bot API (no external dependencies beyond requests).
"""

import os
import json
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _get_bot_token():
    """Get Telegram bot token from environment."""
    return os.environ.get('TELEGRAM_BOT_TOKEN', '')


def _send_message(chat_id: str, text: str, parse_mode: str = 'HTML') -> dict:
    """Send a message via Telegram Bot API.

    Args:
        chat_id: Telegram chat ID
        text: Message text (HTML formatted)
        parse_mode: 'HTML' or 'Markdown'

    Returns:
        API response dict or error dict
    """
    import requests

    token = _get_bot_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Cannot send Telegram messages.")
        return {'ok': False, 'error': 'Telegram bot token not configured'}

    url = TELEGRAM_API.format(token=token, method='sendMessage')
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return {'ok': False, 'error': str(e)}


def notify_payslip_ready(chat_id: str, employee_name: str, period: str,
                          net_pay, bank_account: str = None):
    """Notify employee that their payslip is ready.

    Args:
        chat_id: Telegram chat ID
        employee_name: Employee name
        period: Pay period (e.g., "July 2026")
        net_pay: Net pay amount
        bank_account: Bank account (optional)
    """
    text = (
        f"💰 <b>Payslip Ready</b>\n\n"
        f"Dear {employee_name},\n\n"
        f"Your payslip for <b>{period}</b> is ready.\n\n"
        f"💵 Net Pay: <b>ETB {net_pay:,.2f}</b>\n"
    )
    if bank_account:
        text += f"🏦 Account: {bank_account}\n"

    text += (
        f"\n📋 Log in to view your full payslip details.\n"
        f"\n<i>EthioPayroll — Ethiopian Payroll Engine</i>"
    )

    return _send_message(chat_id, text)


def notify_salary_credited(chat_id: str, employee_name: str, amount,
                            bank_account: str, period: str):
    """Notify employee that salary has been credited.

    Args:
        chat_id: Telegram chat ID
        employee_name: Employee name
        amount: Amount credited
        bank_account: Bank account
        period: Pay period
    """
    text = (
        f"✅ <b>Salary Credited</b>\n\n"
        f"Dear {employee_name},\n\n"
        f"Your salary for <b>{period}</b> has been credited.\n\n"
        f"💵 Amount: <b>ETB {amount:,.2f}</b>\n"
        f"🏦 Account: {bank_account}\n"
        f"📅 Date: {datetime.now().strftime('%d %B %Y')}\n"
        f"\n<i>EthioPayroll</i>"
    )

    return _send_message(chat_id, text)


def notify_leave_status(chat_id: str, employee_name: str, leave_type: str,
                         status: str, start_date: str, end_date: str,
                         days: int, reason: str = None):
    """Notify employee about leave request status.

    Args:
        chat_id: Telegram chat ID
        employee_name: Employee name
        leave_type: Type of leave
        status: approved/rejected
        start_date: Start date string
        end_date: End date string
        days: Number of days
        reason: Rejection reason (if rejected)
    """
    if status == 'approved':
        emoji = "✅"
        status_text = "<b>Approved</b>"
    else:
        emoji = "❌"
        status_text = "<b>Rejected</b>"

    text = (
        f"{emoji} <b>Leave Request {status_text}</b>\n\n"
        f"Dear {employee_name},\n\n"
        f"Your {leave_type} leave request has been {status}.\n\n"
        f"📅 Period: {start_date} to {end_date}\n"
        f"📊 Days: {days}\n"
    )

    if reason:
        text += f"💬 Reason: {reason}\n"

    text += f"\n<i>EthioPayroll</i>"

    return _send_message(chat_id, text)


def notify_deadline_reminder(chat_id: str, company_name: str,
                              deadline_type: str, due_date: str,
                              days_remaining: int, details: str = None):
    """Notify owner about upcoming compliance deadline.

    Args:
        chat_id: Telegram chat ID
        company_name: Company name
        deadline_type: Type of deadline (ERCA Filing, Pension Remittance)
        due_date: Due date string
        days_remaining: Days until deadline
        details: Additional details
    """
    if days_remaining <= 1:
        urgency = "🚨 <b>URGENT</b>"
    elif days_remaining <= 3:
        urgency = "⚠️ <b>Due Soon</b>"
    else:
        urgency = "📅 <b>Reminder</b>"

    text = (
        f"{urgency}\n\n"
        f"<b>{deadline_type}</b>\n"
        f"Company: {company_name}\n"
        f"Due: <b>{due_date}</b> ({days_remaining} days)\n"
    )

    if details:
        text += f"\n{details}\n"

    text += f"\n<i>EthioPayroll Compliance</i>"

    return _send_message(chat_id, text)


def notify_payroll_completed(chat_id: str, company_name: str, period: str,
                              employee_count: int, total_net,
                              compliance_score: float):
    """Notify owner that payroll has been completed.

    Args:
        chat_id: Telegram chat ID
        company_name: Company name
        period: Pay period
        employee_count: Number of employees
        total_net: Total net pay
        compliance_score: Compliance score percentage
    """
    text = (
        f"✅ <b>Payroll Completed</b>\n\n"
        f"Company: {company_name}\n"
        f"Period: <b>{period}</b>\n\n"
        f"👥 Employees: {employee_count}\n"
        f"💵 Total Net Pay: <b>ETB {total_net:,.2f}</b>\n"
        f"📊 Compliance Score: {compliance_score}%\n"
        f"\n<i>EthioPayroll</i>"
    )

    return _send_message(chat_id, text)


def notify_custom(chat_id: str, message: str, company_name: str = None):
    """Send a custom notification.

    Args:
        chat_id: Telegram chat ID
        message: Message text
        company_name: Company name (optional)
    """
    text = f"📢 <b>Notification</b>\n\n{message}"
    if company_name:
        text += f"\n\nFrom: {company_name}"
    text += f"\n<i>EthioPayroll</i>"

    return _send_message(chat_id, text)


def broadcast_to_employees(chat_ids: list, message: str, company_name: str = None):
    """Broadcast a message to multiple employees.

    Args:
        chat_ids: List of Telegram chat IDs
        message: Message text
        company_name: Company name (optional)

    Returns:
        Dict with success/failure counts
    """
    results = {'success': 0, 'failed': 0, 'errors': []}

    for chat_id in chat_ids:
        result = notify_custom(chat_id, message, company_name)
        if result.get('ok'):
            results['success'] += 1
        else:
            results['failed'] += 1
            results['errors'].append({
                'chat_id': chat_id,
                'error': result.get('error', 'Unknown error'),
            })

    return results
