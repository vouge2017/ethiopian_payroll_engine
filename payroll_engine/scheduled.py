"""
Scheduled Reports Module

Auto-generates reports on schedule:
- ERCA report on 20th of each month
- Pension report on 10th of each month
- Compliance deadline reminders

Uses APScheduler or can be triggered via cron/heartbeat.
"""

import logging
from datetime import date, datetime

logger = logging.getLogger('payroll_engine.scheduled')


def check_deadlines_and_notify():
    """Check compliance deadlines and send notifications.

    Run this daily via heartbeat or cron.
    """
    from payroll_engine import db
    from payroll_engine.compliance import get_upcoming_deadlines
    from payroll_engine.models import Company, PayrollRun, User
    from payroll_engine.push import notify_deadline_approaching

    date.today()
    companies = Company.query.all()

    for company in companies:
        # Get latest payroll run
        latest_run = (
            PayrollRun.query.filter_by(company_id=company.id, status='completed')
            .order_by(PayrollRun.run_date.desc())
            .first()
        )

        if not latest_run:
            continue

        payroll_date = latest_run.run_date.isoformat()
        deadlines = get_upcoming_deadlines(company=company, payroll_date=payroll_date)

        # Get company owners
        owners = (
            db.session.query(User)
            .join(User.companies)
            .filter(User.companies.any(company_id=company.id), User.role == 'owner')
            .all()
        )

        # Use company-configurable reminder window
        from payroll_engine.compliance import get_company_deadlines

        company_deadlines = get_company_deadlines(company)
        reminder_days = company_deadlines.get('_reminder_days_before', 3)

        # Check each deadline
        deadline_checks = []
        for key, value in deadlines.items():
            if key.endswith('_days_left'):
                ftype = key.replace('_days_left', '')
                label = company_deadlines.get(ftype, {}).get('label', ftype.upper())
                deadline_checks.append((label, value))

        for deadline_name, days_left in deadline_checks:
            if 0 < days_left <= reminder_days:  # Due within reminder window
                for owner in owners:
                    notify_deadline_approaching(user_id=owner.id, deadline_name=deadline_name, days_left=days_left)
                    logger.info(f'Notified {owner.email} about {deadline_name} ({days_left}d)')


def generate_monthly_erca_reminder():
    """Generate ERCA filing reminder on 20th of each month.

    Called by cron or heartbeat on the 20th.
    """
    from payroll_engine import db
    from payroll_engine.models import Company, PayrollRun, User
    from payroll_engine.push import send_push_notification

    today = date.today()
    if today.day != 20:
        return  # Only run on 20th

    companies = Company.query.all()

    for company in companies:
        # Check if current month payroll is completed
        current_month_run = PayrollRun.query.filter(
            PayrollRun.company_id == company.id,
            PayrollRun.status == 'completed',
            db.extract('year', PayrollRun.run_date) == today.year,
            db.extract('month', PayrollRun.run_date) == today.month,
        ).first()

        if not current_month_run:
            # No payroll run this month — remind owner
            owners = (
                db.session.query(User)
                .join(User.companies)
                .filter(User.companies.any(company_id=company.id), User.role == 'owner')
                .all()
            )

            for owner in owners:
                send_push_notification(
                    user_id=owner.id,
                    title='ERCA Filing Due',
                    body=f'Run payroll for {today.strftime("%B %Y")} — ERCA filing due on the 25th.',
                    url='/payroll/upload',
                    notif_type='deadline',
                )


def generate_payroll_summary_email(company_id, run_id):
    """Generate a plain-text payroll summary for email.

    Can be sent via email service or WhatsApp.
    """
    from payroll_engine.models import Company, Employee, PayrollRun, Payslip

    run = PayrollRun.query.filter_by(id=run_id, company_id=company_id).first()
    company = Company.query.get(company_id)

    if not run or not company:
        return None

    payslips = Payslip.query.filter_by(payroll_run_id=run_id, company_id=run.company_id).all()

    total_gross = sum(ps.gross_salary or 0 for ps in payslips)
    total_tax = sum(ps.tax or 0 for ps in payslips)
    total_pension = sum(ps.employee_pension or 0 for ps in payslips)
    total_net = sum(ps.net_pay or 0 for ps in payslips)

    period = run.period or run.run_date.strftime('%B %Y')

    lines = [
        f'Payroll Summary — {company.name}',
        f'Period: {period}',
        f'Employees: {len(payslips)}',
        '',
        f'Total Gross: ETB {total_gross:,.2f}',
        f'Total Tax: ETB {total_tax:,.2f}',
        f'Total Pension: ETB {total_pension:,.2f}',
        f'Total Net Pay: ETB {total_net:,.2f}',
        '',
        'Per Employee:',
    ]

    for ps in payslips:
        emp = Employee.query.filter_by(id=ps.employee_id, company_id=company_id).first()
        if emp:
            lines.append(f'  {emp.name}: ETB {ps.net_pay:,.2f}')

    lines.append('')
    lines.append(f'Generated by EthioPayroll — {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    return '\n'.join(lines)
