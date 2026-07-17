"""Proactive payroll service — monthly draft preparation and compliance nudges.

This service runs automatically (via before_request hooks) to:
1. Prepare draft payroll on the 28th of each month
2. Send compliance deadline nudges when deadlines are within 3 days

No external scheduler needed — uses the same pattern as daily_retention_purge.
"""
import logging
from datetime import date, datetime, timezone

from payroll_engine import db

logger = logging.getLogger('payroll_engine.proactive')


def prepare_monthly_draft(company_id):
    """Pre-calculate a draft payroll for the current period.

    Called on the 28th of each month (or first request after that).
    Creates a draft payroll run with calculated values.
    Skips if a run already exists for this period.

    Args:
        company_id: Company ID to prepare draft for

    Returns:
        dict with 'status' and 'message', or None if skipped
    """
    from payroll_engine.models import (
        Company, Employee, PayrollRun, PayrollDraft, User, UserCompany,
    )
    from payroll_engine.payroll import calculate_payroll
    from payroll_engine.notifications import notify
    from payroll_engine.ethiopian_calendar import gregorian_to_ethiopian

    today = date.today()
    eth_year, eth_month, _ = gregorian_to_ethiopian(today)
    period_str = f'{eth_year}-{eth_month:02d}'

    # Check if a run already exists for this period
    existing = PayrollRun.query.filter_by(
        company_id=company_id, period=period_str
    ).filter(
        PayrollRun.status.notin_(['failed', 'rejected'])
    ).first()
    if existing:
        return None  # Already has a run for this period

    # Get active employees
    employees = Employee.query.filter_by(
        company_id=company_id, is_deleted=False
    ).all()
    if not employees:
        return None

    # Calculate payroll for each employee
    employees_data = []
    issues = []

    for emp in employees:
        try:
            result = calculate_payroll(
                basic_salary=emp.basic_salary,
                allowances=emp.allowances,
                allowance_records=emp.allowance_records if hasattr(emp, 'allowance_records') else None,
            )
            emp_data = {
                'id': emp.employee_id,
                'name': emp.name,
                'phone': emp.phone or '',
                'department': emp.department or '',
                'position': emp.position or '',
                'basic': float(emp.basic_salary),
                'allowances': float(emp.allowances),
                'gross': float(result['gross']),
                'taxable': float(result['taxable']),
                'tax': float(result['tax']),
                'pension_employee': float(result['pension_employee']),
                'pension_employer': float(result['pension_employer']),
                'net': float(result['net']),
                'bank_account': emp.bank_account or '',
                'bank': emp.bank_account or emp.bank_or_telebirr or '',
                'tin': emp.tin or '',
            }
            employees_data.append(emp_data)

            # Collect issues
            if not emp_data['bank']:
                issues.append(f"{emp.name}: no bank account")
            if not emp_data['tin']:
                issues.append(f"{emp.name}: no TIN")

        except Exception as e:
            logger.error('Failed to calculate payroll for %s: %s', emp.name, e)
            issues.append(f"{emp.name}: calculation error")

    if not employees_data:
        return None

    # Create draft payroll run
    try:
        run = PayrollRun(
            company_id=company_id,
            run_date=today,
            status='draft',
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

        # Notify owners
        owners = User.query.join(UserCompany).filter(
            UserCompany.company_id == company_id,
            User.role.in_(['owner', 'accountant'])
        ).all()

        total_net = sum(e['net'] for e in employees_data)
        issue_text = f" ({len(issues)} issues)" if issues else ""
        message = (
            f'Draft payroll for {period_str} is ready! '
            f'{len(employees_data)} employees{issue_text}. '
            f'Total: ETB {total_net:,.0f}. '
            f'Review and approve.'
        )

        for owner in owners:
            try:
                notify(
                    company_id=company_id,
                    user_id=owner.id,
                    message=message,
                    notif_type='info',
                    link=f'/payroll/{run.id}/confirm',
                )
            except Exception as e:
                logger.error('Failed to notify owner %s: %s', owner.id, e)

        db.session.commit()

        logger.info(
            'Prepared draft payroll for company %s: %s (%d employees, ETB %s)',
            company_id, period_str, len(employees_data), f'{total_net:,.0f}'
        )

        return {
            'status': 'ok',
            'period': period_str,
            'employee_count': len(employees_data),
            'total_net': total_net,
            'issues': issues,
        }

    except Exception as e:
        db.session.rollback()
        logger.error('Failed to prepare draft for company %s: %s', company_id, e)
        return None


def send_compliance_nudges(company_id):
    """Send compliance deadline notifications when deadlines are within 3 days.

    Called daily. Only sends once per day per company (tracked in session or DB).

    Args:
        company_id: Company ID to check

    Returns:
        list of notification messages sent, or empty list
    """
    from payroll_engine.models import PayrollRun, User, UserCompany
    from payroll_engine.compliance import get_upcoming_deadlines
    from payroll_engine.notifications import notify

    today = date.today()

    # Find the latest completed run for compliance dates
    last_run = PayrollRun.query.filter_by(
        company_id=company_id, status='completed'
    ).order_by(PayrollRun.run_date.desc()).first()

    payroll_date = last_run.run_date.isoformat() if last_run else today.isoformat()
    deadlines = get_upcoming_deadlines(payroll_date)

    alerts = []

    erca_days = deadlines.get('erca_days_left', 999)
    if 0 <= erca_days <= 3:
        alerts.append(f'ERCA filing due in {erca_days} days')
    elif erca_days < 0:
        alerts.append(f'ERCA filing overdue by {abs(erca_days)} days')

    pension_days = deadlines.get('pension_days_left', 999)
    if 0 <= pension_days <= 3:
        alerts.append(f'Pension remittance due in {pension_days} days')
    elif pension_days < 0:
        alerts.append(f'Pension remittance overdue by {abs(pension_days)} days')

    if not alerts:
        return []

    # Send to owners
    owners = User.query.join(UserCompany).filter(
        UserCompany.company_id == company_id,
        User.role.in_(['owner', 'accountant'])
    ).all()

    message = '⚠️ ' + ' · '.join(alerts) + '. Open dashboard to download and file.'

    for owner in owners:
        try:
            notify(
                company_id=company_id,
                user_id=owner.id,
                message=message,
                notif_type='warning',
                link='/reports',
            )
        except Exception as e:
            logger.error('Failed to send compliance nudge to %s: %s', owner.id, e)

    db.session.commit()

    logger.info('Compliance nudges sent for company %s: %s', company_id, alerts)
    return alerts


def should_prepare_draft():
    """Check if today is the 28th (or later) and draft hasn't been prepared yet.

    Returns True if we should run prepare_monthly_draft for each company.
    """
    today = date.today()
    return today.day >= 28
