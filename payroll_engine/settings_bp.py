"""Settings & team management blueprint."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from payroll_engine import db
from payroll_engine.models import User, Company, Employee
from payroll_engine.shared import _company_id, role_required

settings_bp = Blueprint('settings', __name__)


@settings_bp.before_request
@login_required
def _require_company():
    """Ensure user has a company."""
    if current_user.company_id is None:
        return redirect(url_for('main.setup_company'))


@settings_bp.route('/settings/team')
@role_required('owner')
def team_settings():
    """Show team members and invite form."""
    from payroll_engine.models import UserCompany
    members = User.query.filter_by(company_id=_company_id()).all()
    linked = UserCompany.query.filter_by(company_id=_company_id()).all()
    return render_template('team_settings.html', members=members, linked=linked,
                           year=date.today().year)


@settings_bp.route('/settings/team/invite', methods=['POST'])
@role_required('owner')
def invite_team_member():
    """Invite a team member by phone. Creates user with temporary password."""
    from payroll_engine.models import validate_ethiopian_phone, UserCompany
    import secrets as _secrets
    phone = request.form.get('phone', '').strip()
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'employee').strip()
    if role not in ('owner', 'accountant', 'employee'):
        role = 'employee'
    if not phone or not name:
        flash('Phone number and name are required.', 'danger')
        return redirect(url_for('settings.team_settings'))
    is_valid, normalized, error = validate_ethiopian_phone(phone)
    if not is_valid:
        flash(error, 'danger')
        return redirect(url_for('settings.team_settings'))
    existing = User.query.filter_by(phone=normalized).first()
    if existing:
        if existing.company_id == _company_id():
            flash('This user is already a member of your company.', 'warning')
            return redirect(url_for('settings.team_settings'))
        link = UserCompany.query.filter_by(user_id=existing.id, company_id=_company_id()).first()
        if link:
            flash('This user already has access to your company.', 'warning')
            return redirect(url_for('settings.team_settings'))
        link = UserCompany(user_id=existing.id, company_id=_company_id(), role=role)
        db.session.add(link)
        db.session.commit()
        flash(f'{name} ({normalized}) linked to your company as {role}.', 'success')
        return redirect(url_for('settings.team_settings'))
    # Cryptographically random temp password — shown only in this response body.
    # Never flash it, never put it in the session cookie, never log it.
    temp_password = _secrets.token_urlsafe(16)
    user = User(phone=normalized, company_id=_company_id(), role=role, must_change_password=True)
    user.set_password(temp_password)
    db.session.add(user)
    db.session.commit()
    from payroll_engine.models import AuditLog
    log = AuditLog(
        company_id=_company_id(), user_id=current_user.id,
        action='team_member_invited',
        details={'phone': normalized, 'name': name, 'role': role}
    )
    db.session.add(log)
    db.session.commit()
    # One-shot display — password shown only in this rendered page.
    return render_template('team_invite_credentials.html', invited_user=user,
                           temp_password=temp_password, invitee_name=name)


@settings_bp.route('/settings/team/remove/<int:user_id>', methods=['POST'])
@role_required('owner')
def remove_team_member(user_id):
    """Remove a team member by unlinking them from the company."""
    from payroll_engine.models import UserCompany
    target = User.query.get_or_404(user_id)
    if target.id == current_user.id:
        flash('You cannot remove yourself.', 'danger')
        return redirect(url_for('settings.team_settings'))
    if target.company_id == _company_id():
        target.company_id = None
        db.session.commit()
    uc = UserCompany.query.filter_by(user_id=user_id, company_id=_company_id()).first()
    if uc:
        db.session.delete(uc)
        db.session.commit()
    from payroll_engine.models import AuditLog
    log = AuditLog(
        company_id=_company_id(), user_id=current_user.id,
        action='team_member_removed',
        details={'removed_user_id': user_id}
    )
    db.session.add(log)
    db.session.commit()
    flash('Team member removed.', 'success')
    return redirect(url_for('settings.team_settings'))


@settings_bp.route('/settings/link-employee', methods=['GET', 'POST'])
@role_required('owner', 'accountant')
def link_employee_user():
    """Link an employee record to a user account for portal access."""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        user_id = request.form.get('user_id', type=int)
        emp = Employee.query.filter_by(id=employee_id, company_id=_company_id()).first_or_404()
        user = User.query.get_or_404(user_id)
        if emp.user_id:
            flash('This employee is already linked to a user account.', 'danger')
            return redirect(url_for('settings.link_employee_user'))
        existing_link = Employee.query.filter_by(user_id=user_id, company_id=_company_id()).first()
        if existing_link:
            flash('This user is already linked to another employee.', 'danger')
            return redirect(url_for('settings.link_employee_user'))
        emp.user_id = user_id
        user.company_id = _company_id()
        user.role = 'employee'
        db.session.commit()
        from payroll_engine.models import AuditLog
        log = AuditLog(
            company_id=_company_id(), user_id=current_user.id,
            action='employee_user_linked',
            details={'employee_id': emp.employee_id, 'user_id': user_id}
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Linked {emp.name} to user account.', 'success')
        return redirect(url_for('settings.team_settings'))
    employees = Employee.query.filter_by(company_id=_company_id(), is_deleted=False, user_id=None).all()
    users = User.query.filter_by(company_id=_company_id()).all()
    return render_template('link_employee_user.html', employees=employees, users=users)


# Need to import date for team_settings
from datetime import date
