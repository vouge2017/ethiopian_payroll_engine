"""Shared utilities used across all blueprints.

Extracted from main.py to enable blueprint split without circular imports.
"""
from flask import session, abort, flash, request
from flask_login import current_user
from functools import wraps
from payroll_engine import db
from payroll_engine.models import AuditLog


def _company_id():
    """Return the session-scoped active company ID, falling back to user default."""
    return session.get('active_company_id', current_user.company_id)


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
                    details={'route': request.endpoint, 'required_roles': list(roles),
                             'user_role': effective_role}
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
