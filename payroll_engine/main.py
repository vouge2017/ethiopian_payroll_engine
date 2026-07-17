"""Main blueprint: dashboard, employees, payroll upload/results, reports."""
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file, abort, current_app, jsonify, session
)
from payroll_engine import limiter
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
import zipfile
import io
from datetime import date, datetime

from payroll_engine import db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip, PayrollDraft,
    AuditLog, PayrollValidationResult, OvertimeEntry, FinalSettlement,
    EmployeeAllowance, Leave, LeaveBalance
)
from payroll_engine.tax import calculate_tax, explain_tax_amharic
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.payroll import calculate_payroll
from payroll_engine.pdf import generate_payslip
from payroll_engine.compliance import compute_compliance_score, get_status_message
from payroll_engine.security import log_and_flash_error
from payroll_engine.services.payroll_workflow import (
    parse_and_calculate_payroll,
    check_csv_row_limit,
    build_period_string,
    get_previous_payslips,
    check_duplicate_period,
    create_payroll_run,
)


main = Blueprint('main', __name__)

# Import shared helpers (single source of truth — no duplicates)
from payroll_engine.shared import _company_id, role_required


# --- Company Setup Guard ---

@main.before_request
def require_company():
    """Redirect users without a company to the setup page."""
    if not current_user.is_authenticated:
        return None  # Let Flask-Login handle it
    if request.endpoint in ('main.setup_company', 'main.demo_mode', 'static', 'health', 'healthz', 'readyz'):
        return None
    if current_user.company_id is None:
        return redirect(url_for('main.setup_company'))
    return None


# --- Company Setup ---

@main.route('/setup-company', methods=['GET', 'POST'])
@login_required
def setup_company():
    """Create or join a company after registration."""
    if current_user.company_id:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'create':
            company_name = request.form.get('company_name', '').strip()
            if not company_name:
                flash('Company name is required.', 'danger')
                return redirect(url_for('main.setup_company'))

            existing = Company.query.filter_by(name=company_name).first()
            if existing:
                flash('A company with that name already exists. Choose a different name.', 'danger')
                return redirect(url_for('main.setup_company'))

            company = Company(name=company_name)
            db.session.add(company)
            db.session.commit()

            current_user.company_id = company.id
            current_user.role = 'owner'
            db.session.commit()

            flash(f'Company "{company_name}" created! Welcome to EthioPayroll.', 'success')
            return redirect(url_for('main.index'))

    return render_template('setup_company.html')


# --- Multi-Company Dashboard ---

@main.route('/companies')
@login_required
def companies_dashboard():
    """
    Multi-company dashboard for accountants managing multiple clients.
    Shows all companies with payroll status, deadlines, and quick actions.
    """
    from payroll_engine.compliance import get_upcoming_deadlines
    from payroll_engine.models import PayrollRun, Payslip

    user_companies = current_user.companies
    company_cards = []

    for company in user_companies:
        if company is None:
            continue

        # Latest payroll run
        latest_run = PayrollRun.query.filter_by(
            company_id=company.id
        ).order_by(PayrollRun.created_at.desc()).first()

        # Employee count
        emp_count = Employee.query.filter_by(
            company_id=company.id, is_deleted=False
        ).count()

        # Last payroll totals
        last_gross = Decimal('0')
        last_net = Decimal('0')
        last_status = 'No payroll'
        if latest_run:
            last_status = latest_run.status.replace('_', ' ').title()
            payslips = Payslip.query.filter_by(payroll_run_id=latest_run.id).all()
            last_gross = sum(p.gross_salary for p in payslips)
            last_net = sum(p.net_pay for p in payslips)

        # Upcoming deadlines
        payroll_date = latest_run.run_date.isoformat() if latest_run else date.today().isoformat()
        deadlines = get_upcoming_deadlines(payroll_date)

        # Role for this company
        role = current_user.get_role_for_company(company.id)

        company_cards.append({
            'company': company,
            'role': role,
            'emp_count': emp_count,
            'latest_run': latest_run,
            'last_status': last_status,
            'last_gross': last_gross,
            'last_net': last_net,
            'deadlines': deadlines,
        })

    return render_template(
        'companies_dashboard.html',
        company_cards=company_cards,
        year=date.today().year,
    )


@main.route('/companies/<int:company_id>/switch', methods=['GET', 'POST'])
@main.route('/switch-company/<int:company_id>', methods=['GET'])
@login_required
def switch_company(company_id):
    """Switch active company context."""
    if not current_user.can_access_company(company_id):
        abort(403)
    session['active_company_id'] = company_id
    company = Company.query.get(company_id)
    flash(f'Switched to {company.name}.', 'success')
    return redirect(url_for('main.index'))




# --- Demo Mode ---

@main.route('/demo')
def demo_mode():
    """Create demo data and log in automatically."""
    if not current_app.config.get('ENABLE_DEMO_MODE', False):
        abort(404)
    from payroll_engine.demo import create_demo_data
    company, user, employees, run = create_demo_data()
    # Log in as demo user
    from flask_login import login_user
    login_user(user)
    flash('Welcome to the demo! You\'re exploring with sample data. No real data is stored.', 'info')
    return redirect(url_for('main.index'))


# --- Dashboard ---

@main.route('/')
@login_required
def index():
    """Dashboard home."""
    company = current_user.company
    employee_count = Employee.query.filter_by(company_id=company.id, is_deleted=False).count()
    recent_runs = PayrollRun.query.filter_by(company_id=company.id) \
        .order_by(PayrollRun.created_at.desc()) \
        .limit(5).all()
    # Use the most recent payroll run date for compliance scoring
    # Falls back to today if no runs exist
    last_run = recent_runs[0] if recent_runs else None
    payroll_date_str = last_run.run_date.isoformat() if last_run else date.today().isoformat()
    score, status = compute_compliance_score(
        payroll_date=payroll_date_str
    )
    status_msg = get_status_message(status)

    # Get upcoming deadlines
    from payroll_engine.compliance import get_upcoming_deadlines
    deadlines = get_upcoming_deadlines(payroll_date_str)

    # Overtime summary for current month (eager-load employee to avoid N+1)
    from payroll_engine.models import OvertimeEntry
    from payroll_engine.overtime import MAX_OVERTIME_HOURS_MONTH
    from sqlalchemy.orm import joinedload
    month_start = date.today().replace(day=1)
    ot_entries = OvertimeEntry.query.options(
        joinedload(OvertimeEntry.employee)
    ).filter_by(company_id=company.id) \
        .filter(OvertimeEntry.date >= month_start).all()
    ot_by_employee = {}
    for entry in ot_entries:
        if entry.employee_id not in ot_by_employee:
            ot_by_employee[entry.employee_id] = {'name': entry.employee.name if entry.employee else '?', 'hours': 0}
        ot_by_employee[entry.employee_id]['hours'] += entry.hours
    ot_total_hours = sum(v['hours'] for v in ot_by_employee.values())
    ot_employee_count = len(ot_by_employee)
    ot_over_limit = [{'name': v['name'], 'hours': round(v['hours'], 1)}
                     for v in ot_by_employee.values() if v['hours'] > MAX_OVERTIME_HOURS_MONTH]

    # Count completed payroll runs for first-run wizard
    completed_runs_count = PayrollRun.query.filter_by(
        company_id=company.id, status='completed'
    ).count()

    # "What happened last month" summary
    last_month_summary = None
    last_completed = PayrollRun.query.filter_by(
        company_id=company.id, status='completed'
    ).order_by(PayrollRun.created_at.desc()).first()
    if last_completed:
        from payroll_engine.models import Payslip
        payslips = Payslip.query.filter_by(payroll_run_id=last_completed.id).all()
        if payslips:
            total_net = sum(p.net_pay for p in payslips)
            total_gross = sum(p.gross_salary for p in payslips)
            total_tax = sum(p.tax for p in payslips)
            avg_salary = total_net / len(payslips) if payslips else 0
            last_month_summary = {
                'period': last_completed.reference or last_completed.run_date.strftime('%B %Y'),
                'employee_count': len(payslips),
                'total_net': total_net,
                'total_gross': total_gross,
                'total_tax': total_tax,
                'avg_salary': avg_salary,
            }

    return render_template(
        'dashboard.html',
        company=company,
        employee_count=employee_count,
        recent_runs=recent_runs,
        completed_runs_count=completed_runs_count,
        compliance_score=score,
        compliance_status=status,
        status_message=status_msg,
        deadlines=deadlines,
        year=date.today().year,
        ot_total_hours=round(ot_total_hours, 1),
        ot_employee_count=ot_employee_count,
        ot_over_limit=ot_over_limit,
        last_month_summary=last_month_summary,
    )


# --- Employees ---


# --- Referral Program ---

@main.route('/referral')
@login_required
def my_referral():
    """Show referral code and stats."""
    import secrets

    # Generate referral code if not exists
    if not current_user.referral_code:
        current_user.referral_code = f'EP{secrets.token_hex(4).upper()}'
        db.session.commit()

    # Count referrals
    from payroll_engine.models import User
    referral_count = User.query.filter_by(referred_by=current_user.id).count()

    return render_template('referral.html',
                           referral_code=current_user.referral_code,
                           referral_count=referral_count)


@main.route('/referral/<code>')
def apply_referral(code):
    """Apply a referral code during registration."""
    from payroll_engine.models import User
    referrer = User.query.filter_by(referral_code=code).first()
    if not referrer:
        flash('Invalid referral code.', 'danger')
        return redirect(url_for('auth.register'))

    # Store in session for use during registration
    from flask import session
    session['referral_code'] = code
    flash(f'You were referred! Sign up to get started.', 'info')
    return redirect(url_for('auth.register'))
