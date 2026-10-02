"""Billing routes — tenant self-service and platform-operator reconciliation.

Tenant side:
    GET  /billing                     plan, status, history, payment instructions
    POST /billing/submit-payment      record a bank-transfer reference (pending)
    GET  /billing/blocked             landing page for suspended tenants

Platform side (User.is_platform_admin only):
    GET  /platform/payments           pending payments across all tenants
    POST /platform/payments/<id>/confirm   activate: status, paid_until, plan
    POST /platform/payments/<id>/reject    mark rejected with a note
"""

import calendar
from datetime import datetime, UTC

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, request,
    url_for,
)
from flask_login import current_user, login_required

from payroll_engine import db
from payroll_engine.billing import (
    BANK_DETAILS,
    PLANS,
    effective_billing_status,
    employee_count,
    get_plan,
)
from payroll_engine.models import BillingPayment, Company, User
from payroll_engine.shared import create_audit_log

billing_bp = Blueprint('billing', __name__)
platform_bp = Blueprint('platform', __name__, url_prefix='/platform')


def _require_platform_admin():
    if not current_user.is_authenticated or not getattr(current_user, 'is_platform_admin', False):
        abort(403)


def _period_end(period_month):
    """'YYYY-MM' -> date of that month's last day."""
    year, month = int(period_month[:4]), int(period_month[5:7])
    return datetime(year, month, calendar.monthrange(year, month)[1]).date()


@billing_bp.route('/billing', methods=['GET'])
@login_required
def view():
    company_id = getattr(current_user, 'company_id', None)
    company = db.session.get(Company, company_id) if company_id else None
    if company is None:
        flash('Create or join a company first.', 'info')
        return redirect(url_for('main.index'))

    payments = (
        BillingPayment.query.filter_by(company_id=company.id)
        .order_by(BillingPayment.submitted_at.desc())
        .limit(24)
        .all()
    )
    return render_template(
        'billing.html',
        company=company,
        plan=get_plan(company),
        plans=PLANS,
        status=effective_billing_status(company),
        employees_used=employee_count(company.id),
        payments=payments,
        bank=BANK_DETAILS,
        now=datetime.now(UTC),
    )


@billing_bp.route('/billing/submit-payment', methods=['POST'])
@login_required
def submit_payment():
    company_id = current_user.company_id
    company = db.session.get(Company, company_id) if company_id else None
    if company is None:
        abort(404)

    reference = (request.form.get('reference') or '').strip()
    period_month = (request.form.get('period_month') or '').strip()
    plan_code = (request.form.get('plan_code') or '').strip() or None
    amount_raw = (request.form.get('amount_etb') or '').strip()
    note = (request.form.get('note') or '').strip() or None

    # Validation
    if not reference:
        flash('Enter the transfer reference number from your bank/Telebirr receipt.', 'danger')
        return redirect(url_for('billing.view'))
    try:
        year, month = int(period_month[:4]), int(period_month[5:7])
        if not (1 <= month <= 12) or len(period_month) != 7 or period_month[4] != '-':
            raise ValueError
    except (ValueError, IndexError):
        flash('Period must be in YYYY-MM format (the month you are paying for).', 'danger')
        return redirect(url_for('billing.view'))
    if plan_code is not None and plan_code not in PLANS:
        flash('Unknown plan selected.', 'danger')
        return redirect(url_for('billing.view'))

    amount = None
    if amount_raw:
        try:
            amount = round(float(amount_raw), 2)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash('Amount must be a positive number.', 'danger')
            return redirect(url_for('billing.view'))
    if amount is None and plan_code:
        amount = float(PLANS[plan_code]['monthly_etb'])

    payment = BillingPayment(
        company_id=company.id,
        plan_code=plan_code,
        amount_etb=amount or 0,
        period_month=period_month,
        method=(request.form.get('method') or 'bank_transfer').strip(),
        reference=reference[:100],
        note=note,
        submitted_by=current_user.id,
    )
    db.session.add(payment)

    # First submission on a grandfathered/past-due account flips stored state
    # to keep the operator queue meaningful; enforcement stays derived.
    create_audit_log(
        company_id=company.id,
        user_id=current_user.id,
        action='billing_payment_submitted',
        details={
            'payment_reference': payment.reference,
            'period_month': period_month,
            'plan_code': plan_code,
            'amount_etb': float(amount or 0),
        },
    )
    db.session.commit()

    flash(
        'Payment submitted. Our team will confirm your transfer — usually within '
        'one business day.',
        'success',
    )
    return redirect(url_for('billing.view'))


@billing_bp.route('/billing/blocked')
@login_required
def blocked():
    company = db.session.get(Company, current_user.company_id) if current_user.company_id else None
    return render_template('billing_blocked.html', company=company)


# ---------------------------------------------------------------------------
# Platform operator reconciliation
# ---------------------------------------------------------------------------


@platform_bp.route('/payments')
@login_required
def payments():
    _require_platform_admin()
    pending = (
        BillingPayment.query.filter_by(status='pending')
        .order_by(BillingPayment.submitted_at.asc())
        .all()
    )
    recent = (
        BillingPayment.query.filter(BillingPayment.status != 'pending')
        .order_by(BillingPayment.reviewed_at.desc())
        .limit(50)
        .all()
    )

    def with_names(rows):
        out = []
        for p in rows:
            company = db.session.get(Company, p.company_id)
            out.append({'payment': p, 'company_name': company.name if company else f'#{p.company_id}'})
        return out

    return render_template(
        'platform_payments.html',
        pending=with_names(pending),
        recent=with_names(recent),
    )


@platform_bp.route('/payments/<int:payment_id>/confirm', methods=['POST'])
@login_required
def confirm_payment(payment_id):
    _require_platform_admin()
    payment = db.session.get(BillingPayment, payment_id)
    if payment is None:
        abort(404)
    if payment.status != 'pending':
        flash('That payment was already reviewed.', 'warning')
        return redirect(url_for('platform.payments'))

    company = db.session.get(Company, payment.company_id)
    if company is None:
        abort(404)

    payment.status = 'confirmed'
    payment.reviewed_by = current_user.id
    payment.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    payment.review_note = (request.form.get('review_note') or '').strip() or None

    company.billing_status = 'active'
    company.paid_until = _period_end(payment.period_month)
    if payment.plan_code in PLANS:
        company.plan_code = payment.plan_code

    create_audit_log(
        company_id=company.id,
        user_id=current_user.id,
        action='billing_payment_confirmed',
        details={
            'payment_id': payment.id,
            'company_id': company.id,
            'paid_until': str(company.paid_until),
            'plan_code': company.plan_code,
        },
    )
    db.session.commit()
    flash(f"Confirmed — {company.name} active through {company.paid_until}.", 'success')
    return redirect(url_for('platform.payments'))


@platform_bp.route('/payments/<int:payment_id>/reject', methods=['POST'])
@login_required
def reject_payment(payment_id):
    _require_platform_admin()
    payment = db.session.get(BillingPayment, payment_id)
    if payment is None:
        abort(404)
    if payment.status != 'pending':
        flash('That payment was already reviewed.', 'warning')
        return redirect(url_for('platform.payments'))

    payment.status = 'rejected'
    payment.reviewed_by = current_user.id
    payment.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    payment.review_note = (request.form.get('review_note') or '').strip() or 'Rejected.'

    create_audit_log(
        company_id=payment.company_id,
        user_id=current_user.id,
        action='billing_payment_rejected',
        details={'payment_id': payment.id, 'reference': payment.reference},
    )
    db.session.commit()
    flash('Payment rejected.', 'info')
    return redirect(url_for('platform.payments'))
