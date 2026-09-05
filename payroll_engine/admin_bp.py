"""
Platform Admin Control Plane Blueprint & Support Operations Engine.

Provides platform-wide oversight, tenant management, support ticketing,
impersonation ("Assist as Tenant") support sessions, system health monitoring,
and immutable admin audit logging.
"""

from datetime import datetime, timezone
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user, login_user

from payroll_engine.models import (
    db, User, Company, UserCompany, PayrollRun, SupportTicket,
    SupportTicketMessage, PlatformAuditLog, ImpersonationSession,
    BillingPayment
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def platform_admin_required(f):
    """Decorator ensuring current user is an authenticated platform administrator."""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not getattr(current_user, 'is_platform_admin', False):
            flash('Access denied: Platform Administrator privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def _log_platform_action(action, target_company_id=None, target_user_id=None, details=None):
    """Records an entry in the immutable PlatformAuditLog."""
    try:
        log = PlatformAuditLog(
            admin_user_id=current_user.id,
            action=action,
            target_company_id=target_company_id,
            target_user_id=target_user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:255],
            details=details or {}
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


# =============================================================================
# 1. PLATFORM DASHBOARD & TENANT DIRECTORY
# =============================================================================

@admin_bp.route('/dashboard')
@platform_admin_required
def dashboard():
    """Platform Admin Control Plane overview dashboard."""
    total_companies = Company.query.count()
    total_users = User.query.count()

    open_tickets = SupportTicket.query.filter(
        SupportTicket.status.in_(['open', 'in_progress', 'waiting_on_customer'])
    ).count()

    active_impersonations = ImpersonationSession.query.filter_by(is_active=True).count()
    pending_payments = BillingPayment.query.filter_by(status='pending').count()

    recent_tickets = SupportTicket.query.order_by(SupportTicket.updated_at.desc()).limit(5).all()
    recent_logs = PlatformAuditLog.query.order_by(PlatformAuditLog.created_at.desc()).limit(10).all()

    return render_template(
        'admin/dashboard.html',
        total_companies=total_companies,
        total_users=total_users,
        open_tickets=open_tickets,
        active_impersonations=active_impersonations,
        pending_payments=pending_payments,
        recent_tickets=recent_tickets,
        recent_logs=recent_logs
    )


@admin_bp.route('/tenants')
@platform_admin_required
def tenants():
    """Directory list of all tenants across the platform."""
    search_q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Company.query
    if search_q:
        query = query.filter(Company.name.ilike(f'%{search_q}%') | Company.tin.ilike(f'%{search_q}%'))

    if status_filter:
        query = query.filter_by(billing_status=status_filter)

    companies = query.order_by(Company.created_at.desc()).all()
    return render_template('admin/tenants.html', companies=companies, search_q=search_q, status_filter=status_filter)


@admin_bp.route('/tenants/<int:company_id>')
@platform_admin_required
def tenant_detail(company_id):
    """Detailed operational overview of a single company tenant."""
    company = Company.query.get_or_404(company_id)
    user_links = UserCompany.query.filter_by(company_id=company.id).all()
    payroll_runs = PayrollRun.query.filter_by(company_id=company.id).order_by(PayrollRun.created_at.desc()).limit(10).all()
    tickets = SupportTicket.query.filter_by(company_id=company.id).order_by(SupportTicket.created_at.desc()).all()

    return render_template(
        'admin/tenant_detail.html',
        company=company,
        user_links=user_links,
        payroll_runs=payroll_runs,
        tickets=tickets
    )


@admin_bp.route('/tenants/<int:company_id>/toggle-status', methods=['POST'])
@platform_admin_required
def toggle_tenant_status(company_id):
    """Suspend or reactivate a tenant account."""
    company = Company.query.get_or_404(company_id)
    new_status = request.form.get('status', 'active')

    old_status = company.billing_status
    company.billing_status = new_status
    db.session.commit()

    _log_platform_action(
        action='tenant_status_change',
        target_company_id=company.id,
        details={'old_status': old_status, 'new_status': new_status}
    )

    flash(f"Company '{company.name}' billing status updated to {new_status}.", 'success')
    return redirect(url_for('admin.tenant_detail', company_id=company.id))


# =============================================================================
# 2. SUPPORT TICKET QUEUE & MESSAGING
# =============================================================================

@admin_bp.route('/tickets')
@platform_admin_required
def tickets():
    """Platform Admin support ticket management queue."""
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')

    query = SupportTicket.query
    if status != 'all':
        query = query.filter_by(status=status)
    if priority != 'all':
        query = query.filter_by(priority=priority)

    tickets_list = query.order_by(SupportTicket.updated_at.desc()).all()
    return render_template('admin/tickets.html', tickets=tickets_list, current_status=status, current_priority=priority)


@admin_bp.route('/tickets/<int:ticket_id>')
@platform_admin_required
def ticket_detail(ticket_id):
    """View ticket thread, context metadata, and send support responses."""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    messages = ticket.messages.order_by(SupportTicketMessage.created_at.asc()).all()
    return render_template('admin/ticket_detail.html', ticket=ticket, messages=messages)


@admin_bp.route('/tickets/<int:ticket_id>/reply', methods=['POST'])
@platform_admin_required
def ticket_reply(ticket_id):
    """Reply to a support ticket or post an internal note."""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    message_text = request.form.get('message_text', '').strip()
    is_internal_note = request.form.get('is_internal_note') == '1'

    if not message_text:
        flash('Reply text cannot be empty.', 'warning')
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket.id))

    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        company_id=ticket.company_id,
        sender_user_id=current_user.id,
        is_admin_reply=True,
        is_internal_note=is_internal_note,
        message_text=message_text
    )

    if not is_internal_note:
        ticket.status = 'waiting_on_customer'
        ticket.updated_at = datetime.now(timezone.utc)

    db.session.add(msg)
    db.session.commit()

    _log_platform_action(
        action='ticket_reply',
        target_company_id=ticket.company_id,
        details={'ticket_code': ticket.ticket_code, 'internal_note': is_internal_note}
    )

    flash('Reply sent successfully.', 'success')
    return redirect(url_for('admin.ticket_detail', ticket_id=ticket.id))


@admin_bp.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@platform_admin_required
def ticket_update_status(ticket_id):
    """Update status or priority of a support ticket."""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    new_status = request.form.get('status', ticket.status)
    new_priority = request.form.get('priority', ticket.priority)

    ticket.status = new_status
    ticket.priority = new_priority
    ticket.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    _log_platform_action(
        action='ticket_status_update',
        target_company_id=ticket.company_id,
        details={'ticket_code': ticket.ticket_code, 'status': new_status, 'priority': new_priority}
    )

    flash('Ticket status updated.', 'success')
    return redirect(url_for('admin.ticket_detail', ticket_id=ticket.id))


# =============================================================================
# 3. SUPPORT ASSIST / IMPERSONATION MODE
# =============================================================================

@admin_bp.route('/impersonate/start', methods=['POST'])
@platform_admin_required
def impersonate_start():
    """Initiate a time-bounded Support Assist session to view/assist as a tenant user."""
    target_user_id = request.form.get('target_user_id', type=int)
    target_company_id = request.form.get('target_company_id', type=int)
    reason = request.form.get('reason', '').strip()

    if not target_user_id or not target_company_id or not reason:
        flash('User, Company, and explicit Support Reason are required for impersonation.', 'danger')
        return redirect(url_for('admin.dashboard'))

    target_user = User.query.get_or_404(target_user_id)
    target_company = Company.query.get_or_404(target_company_id)

    token = uuid.uuid4().hex
    impersonation = ImpersonationSession(
        session_token=token,
        admin_user_id=current_user.id,
        target_user_id=target_user.id,
        target_company_id=target_company.id,
        reason=reason,
        is_active=True
    )
    db.session.add(impersonation)
    db.session.commit()

    admin_id = current_user.id
    # Switch current_user session to target_user
    login_user(target_user)

    # Save original admin identity in Flask session after login_user
    session['impersonator_admin_id'] = admin_id
    session['impersonation_token'] = token
    session['impersonation_company_name'] = target_company.name
    session['company_id'] = target_company.id
    session.modified = True

    _log_platform_action(
        action='impersonate_start',
        target_company_id=target_company.id,
        target_user_id=target_user.id,
        details={'reason': reason, 'token': token}
    )

    flash(f"Support Assist Active: Now viewing platform as '{target_user.email}' at '{target_company.name}'. All actions are logged.", 'warning')
    return redirect(url_for('main.index'))


@admin_bp.route('/impersonate/stop', methods=['POST'])
def impersonate_stop():
    """Terminate active support assist session and return to Super Admin context."""
    admin_id = session.get('impersonator_admin_id')
    token = session.get('impersonation_token')

    if not admin_id or not token:
        flash('No active support assist session found.', 'info')
        return redirect(url_for('main.index'))

    impersonation = ImpersonationSession.query.filter_by(session_token=token, is_active=True).first()
    if impersonation:
        impersonation.is_active = False
        impersonation.ended_at = datetime.now(timezone.utc)
        db.session.commit()

    admin_user = db.session.get(User, admin_id)
    if admin_user:
        login_user(admin_user)

    # Clean up session keys
    session.pop('impersonator_admin_id', None)
    session.pop('impersonation_token', None)
    session.pop('impersonation_company_name', None)
    session.modified = True

    flash('Support Assist session terminated. Returned to Platform Admin account.', 'success')
    return redirect(url_for('admin.dashboard'))


# =============================================================================
# 4. SYSTEM HEALTH & AUDIT LOGS
# =============================================================================

@admin_bp.route('/audit-logs')
@platform_admin_required
def audit_logs():
    """View platform admin audit log ledger."""
    logs = PlatformAuditLog.query.order_by(PlatformAuditLog.created_at.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)


@admin_bp.route('/system-health')
@platform_admin_required
def system_health():
    """Inspect system operations, database metrics, and background worker queues."""
    from payroll_engine.worker_health import get_worker_health
    worker_status = get_worker_health()
    return render_template('admin/system_health.html', worker_status=worker_status)


# =============================================================================
# 5. TENANT-FACING SUPPORT ROUTES
# =============================================================================

support_bp = Blueprint('support', __name__, url_prefix='/support')


@support_bp.route('/tickets')
@login_required
def my_tickets():
    """Tenant view of their support tickets."""
    company_id = session.get('company_id') or getattr(current_user, 'company_id', None)
    if not company_id:
        flash('Please select a company first.', 'warning')
        return redirect(url_for('main.index'))

    tickets_list = SupportTicket.query.filter_by(company_id=company_id).order_by(SupportTicket.updated_at.desc()).all()
    return render_template('support/my_tickets.html', tickets=tickets_list)


@support_bp.route('/tickets/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create a new support ticket with automatic technical context capture."""
    company_id = session.get('company_id') or getattr(current_user, 'company_id', None)
    if not company_id:
        flash('Please select a company first.', 'warning')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        category = request.form.get('category', 'general')
        priority = request.form.get('priority', 'medium')
        message_text = request.form.get('message_text', '').strip()

        if not subject or not message_text:
            flash('Subject and Description are required.', 'danger')
            return render_template('support/create_ticket.html')

        ticket_code = f"TICK-{uuid.uuid4().hex[:8].upper()}"

        context_data = {
            'user_agent': request.headers.get('User-Agent', ''),
            'referrer': request.referrer or '',
            'ip_address': request.remote_addr,
            'company_id': company_id
        }

        ticket = SupportTicket(
            ticket_code=ticket_code,
            company_id=company_id,
            user_id=current_user.id,
            subject=subject,
            category=category,
            priority=priority,
            status='open',
            context_data=context_data
        )
        db.session.add(ticket)
        db.session.flush()

        msg = SupportTicketMessage(
            ticket_id=ticket.id,
            company_id=company_id,
            sender_user_id=current_user.id,
            is_admin_reply=False,
            message_text=message_text
        )
        db.session.add(msg)
        db.session.commit()

        flash(f"Support ticket {ticket.ticket_code} created successfully. Our team will respond shortly.", 'success')
        return redirect(url_for('support.ticket_detail', ticket_id=ticket.id))

    return render_template('support/create_ticket.html')


@support_bp.route('/tickets/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_detail(ticket_id):
    """Tenant detailed view of a support ticket thread."""
    company_id = session.get('company_id') or getattr(current_user, 'company_id', None)
    ticket = SupportTicket.query.filter_by(id=ticket_id, company_id=company_id).first_or_404()

    if request.method == 'POST':
        message_text = request.form.get('message_text', '').strip()
        if message_text:
            msg = SupportTicketMessage(
                ticket_id=ticket.id,
                company_id=company_id,
                sender_user_id=current_user.id,
                is_admin_reply=False,
                message_text=message_text
            )
            ticket.status = 'open'
            ticket.updated_at = datetime.now(timezone.utc)
            db.session.add(msg)
            db.session.commit()
            flash('Response added to ticket.', 'success')
            return redirect(url_for('support.ticket_detail', ticket_id=ticket.id))

    messages = ticket.messages.filter_by(is_internal_note=False).order_by(SupportTicketMessage.created_at.asc()).all()
    return render_template('support/ticket_detail.html', ticket=ticket, messages=messages)
