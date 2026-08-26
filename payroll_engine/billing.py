"""Billing spine v0 — tiers, derived billing state, employee-slot cap.

Philosophy (matches the disbursement philosophy): the engine records money
movement; humans move the money. Payment = manual bank transfer by the
tenant, confirmed by the platform operator. No payment-gateway integration
in v0.

Enforcement model (derived, stateless):
    stored status   | condition                          | effective
    ----------------+------------------------------------+-----------
    trialing        | no trial_end OR now <= trial_end   | trialing
    trialing        | trial expired                      | past_due
    active          | paid_until >= today                | active
    active          | today-grace <= paid_until < today  | past_due
    active          | paid_until < today - grace         | suspended
    suspended       | operator override                  | suspended

The request gate (see enforce_billing_gate) turns these into:
    active/trialing -> full access
    past_due        -> read-only (writes redirect; API gets HTTP 402)
    suspended       -> everything except /billing redirects to blocked page
"""

import os
from datetime import date, datetime, timedelta

from flask import flash, g, jsonify, redirect, request, url_for
from flask_login import current_user

from payroll_engine import db
from payroll_engine.models import Company

Q = None  # placeholder to keep Decimal import local where used

# ---------------------------------------------------------------------------
# Plans — matches the pricing strategy: Free 1-5, ETB 500/mo 6-25, 1500/mo 26+
# ---------------------------------------------------------------------------

PLANS = {
    'free': {'name': 'Free', 'max_employees': 5, 'monthly_etb': 0},
    'standard': {'name': 'Standard', 'max_employees': 25, 'monthly_etb': 500},
    'pro': {'name': 'Pro', 'max_employees': 100, 'monthly_etb': 1500},
}
DEFAULT_PLAN = 'free'
TRIAL_DAYS = 30
BILLING_GRACE_DAYS = 7

# Where tenants send money. Operator: replace via env vars or edit here.
BANK_DETAILS = {
    'bank_name': os.environ.get('BILLING_BANK_NAME', 'Commercial Bank of Ethiopia'),
    'account_name': os.environ.get('BILLING_ACCOUNT_NAME', 'EthioPayroll PLC'),
    'account_number': os.environ.get('BILLING_ACCOUNT_NUMBER', '1000123456789'),
    'telebirr': os.environ.get('BILLING_TELEBIRR', ''),
}

WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

# Endpoints reachable regardless of billing state.
ALWAYS_EXEMPT = {
    'static',
    'health',
    # auth
    'auth.login', 'auth.logout', 'auth.register',
    'auth.forgot_password', 'auth.reset_password',
    'auth.google_login', 'auth.google_callback', 'auth.google_register',
    'auth.set_language',
    # billing self-service
    'billing.view', 'billing.submit_payment', 'billing.blocked',
}


def get_plan(company):
    """Return the plan dict for a company (falling back safely)."""
    return PLANS.get(getattr(company, 'plan_code', None) or DEFAULT_PLAN, PLANS[DEFAULT_PLAN])


def _as_date(value):
    """Coerce datetime/date to date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def effective_billing_status(company, today=None):
    """Compute the enforceable billing state (see module docstring table)."""
    stored = getattr(company, 'billing_status', None) or 'trialing'
    today = today or date.today()

    if stored == 'suspended':
        return 'suspended'

    if stored == 'active':
        paid_until = _as_date(getattr(company, 'paid_until', None))
        if paid_until is None:
            return 'past_due'
        if paid_until >= today:
            return 'active'
        if paid_until < today - timedelta(days=BILLING_GRACE_DAYS):
            return 'suspended'
        return 'past_due'

    # trialing
    trial_end = _as_date(getattr(company, 'trial_ends_at', None))
    if trial_end is None:
        # Grandfathered companies (column added with NULL): unlimited trial
        # until the operator activates billing for them explicitly.
        return 'trialing'
    if today <= trial_end:
        return 'trialing'
    return 'past_due'


def employee_count(company_id):
    """Count active (non-deleted) employees for tier capping."""
    from payroll_engine.models import Employee

    return (
        Employee.query.filter_by(company_id=company_id, is_deleted=False).count()
    )


def check_employee_slot(company):
    """Return (ok, error_message) for adding one more employee under the plan cap."""
    plan = get_plan(company)
    used = employee_count(company.id)
    if used >= plan['max_employees']:
        return False, (
            f"Your {plan['name']} plan allows up to {plan['max_employees']} employees "
            f"(you have {used}). Upgrade your plan on the Billing page to add more."
        )
    return True, None


def company_for_request():
    """Resolve + cache the active Company for this request (None if unresolvable)."""
    if getattr(g, '_billing_company', None) is not None:
        return g._billing_company
    company_id = getattr(current_user, 'company_id', None)
    from flask import session

    company_id = session.get('active_company_id', company_id)
    company = db.session.get(Company, company_id) if company_id else None
    g._billing_company = company
    return company


def enforce_billing_gate():
    """Flask before_request hook: turn billing state into access control."""
    if request.endpoint in ALWAYS_EXEMPT or request.endpoint is None:
        return None
    if not current_user.is_authenticated:
        return None
    if getattr(current_user, 'is_platform_admin', False):
        return None  # operator account manages all tenants

    company = company_for_request()
    if company is None:
        return None  # pre-setup accounts have nothing to bill yet

    status = effective_billing_status(company)
    g.billing_status = status
    g.billing_plan = get_plan(company)

    endpoint_is_platform = (request.endpoint or '').startswith('platform.')
    billing_allowed = request.endpoint in ALWAYS_EXEMPT or endpoint_is_platform

    if status == 'suspended' and not billing_allowed:
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Account suspended. Contact support.'}), 402
        return redirect(url_for('billing.blocked'))

    if status == 'past_due' and request.method in WRITE_METHODS and not billing_allowed:
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Payment overdue — read-only mode.', 'billing_status': status}), 402
        flash(
            'Your payment is overdue. The account is read-only until you settle '
            'the invoice on the Billing page.',
            'warning',
        )
        return redirect(url_for('billing.view'))

    return None
