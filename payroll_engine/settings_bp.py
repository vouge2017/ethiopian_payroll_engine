"""Settings & team management blueprint."""

from datetime import UTC, datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from payroll_engine import db
from payroll_engine.models import Company, Employee, User
from payroll_engine.shared import _company_id, create_audit_log, role_required

settings_bp = Blueprint('settings', __name__)


@settings_bp.before_request
@login_required
def _require_company():
    """Ensure user has a company."""
    if current_user.company_id is None:
        return redirect(url_for('main.setup_company'))


@settings_bp.route('/settings/company', methods=['GET', 'POST'])
@role_required('owner')
def company_profile():
    """Edit company branding: name, address, TIN, logo."""
    import os

    from werkzeug.utils import secure_filename

    company = db.session.get(Company, _company_id())

    if request.method == 'POST':
        company.name = request.form.get('name', company.name).strip()
        company.address = request.form.get('address', '').strip() or None

        # Validate company phone
        from payroll_engine.models import validate_ethiopian_phone

        phone_raw = request.form.get('phone', '').strip()
        if phone_raw:
            is_valid, normalized_phone, phone_error = validate_ethiopian_phone(phone_raw)
            if not is_valid:
                flash(f'Company phone: {phone_error}', 'danger')
                return redirect(url_for('settings.company_profile'))
            company.phone = normalized_phone
        else:
            company.phone = None

        company.tin = request.form.get('tin', '').strip() or None

        # Leave encashment daily-rate setting (only when the form sends it).
        from payroll_engine.services.settlement_service import validate_leave_rate_settings

        leave_rate_change = None
        leave_rate_confirmation = None
        if 'leave_rate_basis' in request.form or 'leave_rate_divisor' in request.form:
            try:
                basis, divisor = validate_leave_rate_settings(
                    request.form.get('leave_rate_basis', company.leave_rate_basis).strip(),
                    request.form.get('leave_rate_divisor', str(company.leave_rate_divisor)).strip(),
                )
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), 'danger')
                return redirect(url_for('settings.company_profile'))
            changed = (basis, divisor) != (company.leave_rate_basis, company.leave_rate_divisor)
            # The checkbox mirrors the confirmed state: ticked = this basis and
            # divisor are confirmed by the company; unticked = not confirmed.
            confirm = request.form.get('leave_rate_confirm') == '1'
            was_confirmed = company.leave_rate_confirmed_at is not None
            if changed:
                leave_rate_change = {
                    'leave_rate_basis': {'old': company.leave_rate_basis, 'new': basis},
                    'leave_rate_divisor': {'old': company.leave_rate_divisor, 'new': divisor},
                }
            company.leave_rate_basis = basis
            company.leave_rate_divisor = divisor
            if confirm and (changed or not was_confirmed):
                company.leave_rate_confirmed_at = datetime.now(UTC).replace(tzinfo=None)
                company.leave_rate_confirmed_by = current_user.id
                leave_rate_confirmation = {'confirmed': True, 'leave_rate_basis': basis, 'leave_rate_divisor': divisor}
            elif not confirm and was_confirmed:
                company.leave_rate_confirmed_at = None
                company.leave_rate_confirmed_by = None
                leave_rate_confirmation = {'confirmed': False, 'leave_rate_basis': basis, 'leave_rate_divisor': divisor}

        company.webhook_url = request.form.get('webhook_url', '').strip() or None
        company.webhook_secret = request.form.get('webhook_secret', '').strip() or None

        # Handle logo upload
        logo = request.files.get('logo')
        if logo and logo.filename:
            filename = secure_filename(logo.filename)
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                flash('Logo must be a PNG or JPG image.', 'danger')
                return redirect(url_for('settings.company_profile'))
            upload_dir = os.path.join('payroll_engine', 'static', 'uploads', 'logos')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, f'logo_{company.id}_{filename}')
            logo.save(filepath)
            company.logo_path = f'uploads/logos/logo_{company.id}_{filename}'

        # Audit: company settings change
        create_audit_log(
            company_id=company.id,
            user_id=current_user.id,
            action='company_settings_change',
            details={'fields_updated': ['name', 'address', 'phone', 'tin', 'webhook_url', 'webhook_secret']},
        )
        if leave_rate_change:
            create_audit_log(
                company_id=company.id,
                user_id=current_user.id,
                action='leave_rate_setting_change',
                details=leave_rate_change,
            )
        if leave_rate_confirmation:
            create_audit_log(
                company_id=company.id,
                user_id=current_user.id,
                action='leave_rate_confirmation_change',
                details=leave_rate_confirmation,
            )
        db.session.commit()
        flash('Company profile updated.', 'success')
        return redirect(url_for('settings.company_profile'))

    from payroll_engine import constants

    return render_template(
        'company_profile.html',
        company=company,
        leave_rate_basis_choices=[(b, constants.LEAVE_RATE_BASIS_LABELS[b]) for b in constants.LEAVE_RATE_BASES],
        default_leave_rate_basis=constants.DEFAULT_LEAVE_RATE_BASIS,
        default_leave_rate_divisor=constants.DEFAULT_LEAVE_RATE_DIVISOR,
        leave_rate_divisor_min=constants.LEAVE_RATE_DIVISOR_MIN,
        leave_rate_divisor_max=constants.LEAVE_RATE_DIVISOR_MAX,
    )


@settings_bp.route('/settings/team')
@role_required('owner')
def team_settings():
    """Show team members and invite form."""
    from payroll_engine.models import UserCompany

    members = User.query.filter_by(company_id=_company_id()).all()
    linked = UserCompany.query.filter_by(company_id=_company_id()).all()
    return render_template('team_settings.html', members=members, linked=linked, year=date.today().year)


@settings_bp.route('/settings/team/invite', methods=['POST'])
@role_required('owner')
def invite_team_member():
    """Invite a team member by phone. Creates user with temporary password."""
    import secrets as _secrets

    from payroll_engine.models import UserCompany, validate_ethiopian_phone

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
        company_id=_company_id(),
        user_id=current_user.id,
        action='team_member_invited',
        details={'phone': normalized, 'name': name, 'role': role},
    )
    db.session.add(log)
    db.session.commit()
    # One-shot display — password shown only in this rendered page.
    return render_template(
        'team_invite_credentials.html', invited_user=user, temp_password=temp_password, invitee_name=name
    )


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
        company_id=_company_id(),
        user_id=current_user.id,
        action='team_member_removed',
        details={'removed_user_id': user_id},
    )
    db.session.add(log)
    db.session.commit()
    flash('Team member removed.', 'success')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Team member removed.', 'user_id': user_id})
    return redirect(url_for('settings.team_settings'))


@settings_bp.route('/settings/link-employee', methods=['GET', 'POST'])
@role_required('owner', 'accountant')
def link_employee_user():
    """Link an employee record to a user account for portal access."""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        user_id = request.form.get('user_id', type=int)
        emp = Employee.query.filter_by(id=employee_id, company_id=_company_id(), is_deleted=False).first_or_404()
        user = User.query.get_or_404(user_id)
        if emp.user_id:
            flash('This employee is already linked to a user account.', 'danger')
            return redirect(url_for('settings.link_employee_user'))
        existing_link = Employee.query.filter_by(user_id=user_id, company_id=_company_id(), is_deleted=False).first()
        if existing_link:
            flash('This user is already linked to another employee.', 'danger')
            return redirect(url_for('settings.link_employee_user'))
        emp.user_id = user_id
        user.company_id = _company_id()
        user.role = 'employee'
        db.session.commit()
        from payroll_engine.models import AuditLog

        log = AuditLog(
            company_id=_company_id(),
            user_id=current_user.id,
            action='employee_user_linked',
            details={'employee_id': emp.employee_id, 'user_id': user_id},
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Linked {emp.name} to user account.', 'success')
        return redirect(url_for('settings.team_settings'))
    employees = Employee.query.filter_by(company_id=_company_id(), is_deleted=False, user_id=None).all()
    users = User.query.filter_by(company_id=_company_id()).all()
    return render_template('link_employee_user.html', employees=employees, users=users)


# ---------------------------------------------------------------------------
# Compliance Deadline Settings
# ---------------------------------------------------------------------------


@settings_bp.route('/settings/compliance', methods=['GET', 'POST'])
@role_required('owner', 'accountant')
def compliance_deadlines():
    """Configure compliance deadlines and reminder settings."""
    from payroll_engine.compliance import FILING_TYPE_DEFAULTS, get_company_deadlines

    company = current_user.company

    if request.method == 'POST':
        deadlines = {}

        # Built-in filing types
        for ftype in FILING_TYPE_DEFAULTS:
            day_key = f'day_{ftype}'
            enabled_key = f'enabled_{ftype}'
            day = request.form.get(day_key, type=int)
            enabled = request.form.get(enabled_key) == 'on'
            if day and 1 <= day <= 28:  # 28 to be safe for all months
                deadlines[ftype] = {
                    'day': day,
                    'enabled': enabled,
                    'label': FILING_TYPE_DEFAULTS[ftype]['label'],
                    'label_am': FILING_TYPE_DEFAULTS[ftype]['label_am'],
                }

        # Disbursement days
        disb_days = request.form.get('disbursement_days', type=int)
        if disb_days and 1 <= disb_days <= 30:
            deadlines['disbursement_days'] = disb_days

        # Reminder window
        reminder_days = request.form.get('reminder_days_before', type=int)
        if reminder_days and 1 <= reminder_days <= 14:
            deadlines['reminder_days_before'] = reminder_days

        # Custom filing types
        custom = []
        i = 0
        while True:
            name = request.form.get(f'custom_name_{i}', '').strip()
            day = request.form.get(f'custom_day_{i}', type=int)
            enabled = request.form.get(f'custom_enabled_{i}') == 'on'
            if not name:
                break
            if day and 1 <= day <= 28:
                custom.append({'name': name, 'day': day, 'enabled': enabled})
            i += 1
        if custom:
            deadlines['custom_deadlines'] = custom

        company.compliance_deadlines = deadlines
        create_audit_log(
            company_id=company.id,
            user_id=current_user.id,
            action='compliance_deadlines_change',
            details={'deadlines': deadlines},
        )
        db.session.commit()
        flash('Compliance deadlines updated.', 'success')
        return redirect(url_for('settings.compliance_deadlines'))

    # GET
    current = get_company_deadlines(company)
    return render_template(
        'settings/compliance_deadlines.html', company=company, current=current, defaults=FILING_TYPE_DEFAULTS
    )


# Need to import date for team_settings
from datetime import date

# ---------------------------------------------------------------------------
# Report Template Settings
# ---------------------------------------------------------------------------


@settings_bp.route('/settings/reports', methods=['GET', 'POST'])
@role_required('owner', 'accountant')
def report_templates():
    """Configure report column layouts."""
    from payroll_engine.report_templates import (
        get_all_available_columns,
        get_default_template,
        get_report_template,
        save_report_template,
    )

    company = current_user.company

    if request.method == 'POST':
        report_type = request.form.get('report_type', 'erca')
        all_cols = get_all_available_columns(report_type)

        # Build column config from form
        columns = []
        for i, col in enumerate(all_cols):
            key = col['key']
            enabled = request.form.get(f'enabled_{key}') == 'on'
            label = request.form.get(f'label_{key}', col['label']).strip() or col['label']
            order = int(request.form.get(f'order_{key}', i))
            columns.append(
                {
                    'key': key,
                    'label': label,
                    'enabled': enabled,
                    'order': order,
                }
            )

        # Sort by order
        columns.sort(key=lambda c: c['order'])

        save_report_template(company, report_type, columns)
        # Audit: report template change
        create_audit_log(
            company_id=company.id,
            user_id=current_user.id,
            action='report_template_change',
            details={'report_type': report_type, 'column_count': len(columns)},
        )
        db.session.commit()
        flash('Report template updated.', 'success')
        return redirect(url_for('settings.report_templates'))

    # GET: show current templates
    report_type = request.args.get('type', 'erca')
    template = get_report_template(company, report_type)
    available = get_all_available_columns(report_type)
    default = get_default_template(report_type)

    return render_template(
        'settings/report_templates.html',
        template=template,
        available=available,
        default=default,
        report_type=report_type,
    )


# ---------------------------------------------------------------------------
# Pay items (company catalog settings)
#
# Owner-only, like the other company-configuration pages (company profile,
# team). Every route resolves the item through the company scope: another
# company's id is a 404; a shared statutory item (company_id IS NULL) is
# visible but locked, and any change to it is refused with 403. Rules and
# audit logging live in services.pay_item_settings.
# ---------------------------------------------------------------------------

_PAY_ITEM_FORM_FIELDS = ('kind', 'key', 'name_en', 'name_am', 'name_om')


def _pay_item_or_404(item_id):
    from payroll_engine.services import pay_item_settings as svc

    item = svc.get_visible_item(_company_id(), item_id)
    if item is None:
        abort(404)
    return item


def _company_pay_item_or_403(item_id):
    """The company's own item; 404 if not visible, 403 if it is a locked system item."""
    item = _pay_item_or_404(item_id)
    if item.company_id is None:
        abort(403)
    return item


def _render_pay_items(form=None, status=200):
    from payroll_engine.services import pay_item_settings as svc

    return (
        render_template(
            'settings/pay_items.html',
            groups=svc.catalog_view(_company_id()),
            legal_view=svc.legal_view,
            form=form or {},
        ),
        status,
    )


@settings_bp.route('/settings/pay-items', methods=['GET'])
@role_required('owner')
def pay_items():
    """List the company's pay items (system + own) grouped by kind."""
    body, status = _render_pay_items()
    return body, status


@settings_bp.route('/settings/pay-items', methods=['POST'])
@role_required('owner')
def pay_item_create():
    from payroll_engine.services import pay_item_settings as svc

    form = {f: request.form.get(f, '') for f in _PAY_ITEM_FORM_FIELDS}
    try:
        item = svc.create_item(
            _company_id(),
            current_user.id,
            key=form['key'],
            kind=form['kind'],
            name_en=form['name_en'],
            name_am=form['name_am'],
            name_om=form['name_om'],
        )
    except svc.PayItemSettingsError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
        return _render_pay_items(form=form, status=400)
    db.session.commit()
    flash(f'{item.name_en} added.', 'success')
    return redirect(url_for('settings.pay_items', _anchor=f'item-{item.id}'))


@settings_bp.route('/settings/pay-items/<int:item_id>/edit', methods=['GET', 'POST'])
@role_required('owner')
def pay_item_edit(item_id):
    """Rename an item (labels only; the key is immutable)."""
    from payroll_engine.services import pay_item_settings as svc

    item = _pay_item_or_404(item_id)
    locked = item.company_id is None
    reason = svc.permissions(item, svc.Usage())['reason'] if locked else None

    def page(form, status=200):
        earliest = svc.earliest_effective_from(item)
        return (
            render_template(
                'settings/pay_item_edit.html',
                item=item,
                locked=locked,
                reason=reason,
                form=form,
                today=date.today(),
                earliest_effective_from=earliest,
            ),
            status,
        )

    if request.method == 'GET':
        return page({})

    if locked:
        abort(403)
    form = {f: request.form.get(f, '') for f in ('name_en', 'name_am', 'name_om', 'effective_from')}
    try:
        changed = svc.rename_item(item, current_user.id, **form)
    except svc.PayItemSettingsError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
        return page(form, 400)
    db.session.commit()
    flash(
        'Names saved as a new version.' if changed else 'Nothing changed.',
        'success' if changed else 'info',
    )
    return redirect(url_for('settings.pay_items', _anchor=f'item-{item.id}'))


@settings_bp.route('/settings/pay-items/<int:item_id>/default-amount', methods=['POST'])
@role_required('owner')
def pay_item_default_amount(item_id):
    """Set or clear the company default monthly amount (pre-fills employee assignments only)."""
    from payroll_engine.services import employee_assignments as ea

    item = _company_pay_item_or_403(item_id)
    try:
        changed = ea.set_default_amount(item, current_user.id, request.form.get('default_amount', ''))
    except ea.AssignmentError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
        return redirect(url_for('settings.pay_item_edit', item_id=item.id))
    db.session.commit()
    flash('Default amount saved.' if changed else 'Nothing changed.', 'success' if changed else 'info')
    return redirect(url_for('settings.pay_item_edit', item_id=item.id))


@settings_bp.route('/settings/pay-items/<int:item_id>/history', methods=['GET'])
@role_required('owner')
def pay_item_history(item_id):
    """Version history of one item (own or shared system item), newest first."""
    from payroll_engine.item_versions import history

    item = _pay_item_or_404(item_id)
    return render_template('settings/pay_item_history.html', item=item, versions=history(item))


def _pay_item_action(item_id, action, success_message):
    from payroll_engine.services import pay_item_settings as svc

    item = _company_pay_item_or_403(item_id)
    anchor = f'item-{item.id}'
    try:
        result = action(svc, item)
    except svc.PayItemSettingsError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
        return redirect(url_for('settings.pay_items', _anchor=anchor))
    db.session.commit()
    if result is not False:
        flash(success_message.format(name=item.name_en), 'success')
    return redirect(url_for('settings.pay_items', _anchor=anchor))


@settings_bp.route('/settings/pay-items/<int:item_id>/move', methods=['POST'])
@role_required('owner')
def pay_item_move(item_id):
    direction = request.form.get('direction', '')
    return _pay_item_action(
        item_id, lambda svc, item: svc.move_item(item, current_user.id, direction), 'Order of {name} updated.'
    )


@settings_bp.route('/settings/pay-items/<int:item_id>/deactivate', methods=['POST'])
@role_required('owner')
def pay_item_deactivate(item_id):
    return _pay_item_action(
        item_id,
        lambda svc, item: svc.deactivate_item(item, current_user.id),
        '{name} deactivated. It is hidden from new assignments and kept for history.',
    )


@settings_bp.route('/settings/pay-items/<int:item_id>/reactivate', methods=['POST'])
@role_required('owner')
def pay_item_reactivate(item_id):
    return _pay_item_action(
        item_id, lambda svc, item: svc.reactivate_item(item, current_user.id), '{name} reactivated.'
    )


@settings_bp.route('/settings/pay-items/<int:item_id>/delete', methods=['POST'])
@role_required('owner')
def pay_item_delete(item_id):
    from payroll_engine.services import pay_item_settings as svc

    item = _company_pay_item_or_403(item_id)
    name = item.name_en
    try:
        svc.delete_item(item, current_user.id)
    except svc.PayItemSettingsError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
        return redirect(url_for('settings.pay_items', _anchor=f'item-{item_id}'))
    except IntegrityError:
        # An assignment referencing it was created concurrently (FK RESTRICT).
        db.session.rollback()
        flash('This item is now in use, so it is kept for history. Deactivate it instead.', 'danger')
        return redirect(url_for('settings.pay_items', _anchor=f'item-{item_id}'))
    db.session.commit()
    flash(f'{name} deleted.', 'success')
    return redirect(url_for('settings.pay_items'))
