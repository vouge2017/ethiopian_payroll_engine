"""Shared utilities used across all blueprints.

Extracted from main.py to enable blueprint split without circular imports.
"""

from functools import wraps

from flask import abort, flash, request, session
from flask_login import current_user

from payroll_engine import db
from payroll_engine.models import AuditLog


def _company_id():
    """Return the session-scoped active company ID, falling back to user default."""
    return session.get('active_company_id', current_user.company_id)


def get_tenant_or_404(model, record_id, company_id=None):
    """Fetch a tenant-scoped record by ID, enforcing company ownership.

    Use this INSTEAD of Model.query.get() / db.session.get() / get_or_404()
    whenever the ID comes from a route parameter on a model that carries
    company_id. Returns 404 (not 403) so IDs are not enumerable across tenants.

    Args:
        model: Model class with a company_id column.
        record_id: Primary key from the request.
        company_id: Defaults to the session's active company.
    """
    return (
        model.query.filter_by(id=record_id, company_id=company_id or _company_id()).first_or_404()
    )


def tenant_get(model, record_id, company_id):
    """Fetch a tenant-scoped record by ID, returning None instead of aborting.

    Internal/service-safe counterpart to get_tenant_or_404(): use inside
    service functions, loops, and background tasks where a 404 abort is
    wrong and the caller handles missing rows. Replaces raw
    db.session.get(Model, pk) which bypasses TenantQuery isolation.
    """
    if record_id is None or company_id is None:
        return None
    return model.query.filter_by(id=record_id, company_id=company_id).first()


def role_required(*roles):
    """Restrict access to users with specific roles.

    Roles: owner, accountant, employee
    Also checks UserCompany for multi-company accountants.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            effective_role = current_user.get_role_for_company(_company_id())
            if effective_role not in roles:
                flash('You do not have permission for this action.', 'danger')
                log = AuditLog(
                    company_id=_company_id(),
                    user_id=current_user.id,
                    action='permission_denied',
                    details={'route': request.endpoint, 'required_roles': list(roles), 'user_role': effective_role},
                )
                db.session.add(log)
                db.session.commit()
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_linked_employee():
    """Get the employee record linked to the current user, or None."""
    from payroll_engine.models import Employee

    return Employee.query.filter_by(
        user_id=current_user.id,
        company_id=_company_id(),
        is_deleted=False,
    ).first()


def create_audit_log(company_id, user_id, action, details=None):
    """Create an AuditLog with request_id automatically injected."""
    from flask import g

    from payroll_engine.models import AuditLog

    merged_details = dict(details or {})
    request_id = getattr(g, 'request_id', None)
    if request_id:
        merged_details['request_id'] = request_id
    log = AuditLog(
        company_id=company_id,
        user_id=user_id,
        action=action,
        details=merged_details,
    )
    db.session.add(log)
    return log


def create_notification(company_id, user_id, message, type='info', link=None):
    """Create an in-app notification for a user."""
    from payroll_engine.models import Notification

    notif = Notification(
        company_id=company_id,
        user_id=user_id,
        message=message,
        type=type,
        link=link,
    )
    db.session.add(notif)
    return notif
