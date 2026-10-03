"""Retained-period taxable additions: draft, owner approval, immutable delta."""

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from payroll_engine.services.correction_context import frozen_tax, money


@dataclass
class AdjustmentResult:
    success: bool
    adjustment_id: int | None = None
    employee_name: str = ''
    adjustment_net: Decimal = Decimal('0')
    error: str = ''


@dataclass
class AdjustmentSummary:
    run_id: int
    period: str
    total_adjustments: int = 0
    total_positive_net: Decimal = Decimal('0')
    total_negative_net: Decimal = Decimal('0')
    net_adjustment: Decimal = Decimal('0')
    adjustments: list = field(default_factory=list)
    employees_affected: int = 0
    pending_count: int = 0
    legacy_count: int = 0


def calculate_adjustment(
    original_gross,
    original_tax,
    original_pension,
    original_net,
    adjustment_amount,
    adjustment_type='addition',
    basic_salary=Decimal('0'),
    *,
    taxable_income=None,
    tax_context=None,
):
    if adjustment_type != 'addition':
        raise ValueError(
            'Only additional taxable overtime or bonus is supported. Other corrections require policy review.'
        )
    amount = money(adjustment_amount, positive=True)
    taxable = money(taxable_income)
    tax_before = money(original_tax)
    if frozen_tax(taxable, tax_context) != tax_before:
        raise ValueError('Retained tax rules do not reconcile to approved payroll. Historical review is required.')
    money(money(original_gross) + amount)
    tax_delta = frozen_tax(taxable + amount, tax_context) - tax_before
    net_delta = money(amount - tax_delta, positive=True)
    return {
        'adjustment_gross': amount,
        'adjustment_tax': tax_delta,
        'adjustment_pension': Decimal('0.00'),
        'adjustment_net': net_delta,
        'new_total_net': money(money(original_net) + net_delta),
        'mode': 'retained_period_delta',
    }


def _fingerprint(original):
    values = {
        key: getattr(original, key)
        for key in (
            'id',
            'company_id',
            'employee_id',
            'payroll_run_id',
            'gross_salary',
            'tax',
            'employee_pension',
            'employer_pension',
            'net_pay',
            'taxable_income',
            'exempt_allowances',
            'sick_leave_reduction',
            'unpaid_leave_reduction',
            'deduction_details',
            'line_items',
            'calculation_context',
        )
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()


def _actor(db, models, company_id, user_id, roles):
    actor = db.session.get(models.User, user_id)
    membership = models.UserCompany.query.filter_by(user_id=user_id, company_id=company_id).with_for_update().first()
    if actor is None or membership is None or membership.role not in roles:
        raise ValueError('You do not have permission for this company or action.')


def _original(models, run_id, company_id, employee_id):
    run = (
        models.PayrollRun.query.filter_by(id=run_id, company_id=company_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if run is None or run.status not in ('completed', 'locked') or not run.approved_at:
        raise ValueError('Can only correct approved completed or locked payroll runs.')
    original = (
        models.Payslip.query.filter_by(
            company_id=company_id, payroll_run_id=run_id, employee_id=employee_id, payslip_type='regular'
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if original is None:
        raise ValueError('Original approved payslip not found for this company and employee.')
    return run, original


def _approved(models, company_id, original_id):
    return (
        models.PayrollCorrection.query.filter_by(
            company_id=company_id, original_payslip_id=original_id, status='approved'
        )
        .order_by(models.PayrollCorrection.id)
        .all()
    )


def _audit(db, models, correction, user_id, action):
    db.session.add(
        models.AuditLog(
            company_id=correction.company_id,
            user_id=user_id,
            action=action,
            details={
                'correction_id': correction.id,
                'run_id': correction.payroll_run_id,
                'original_payslip_id': correction.original_payslip_id,
                'source': correction.source,
                'source_reference': correction.source_reference,
                'effective_date': correction.effective_date.isoformat(),
                'reason': correction.reason,
                'amount': str(correction.amount),
                'tax_delta': str(correction.tax_delta),
                'net_delta': str(correction.net_delta),
                'period': correction.snapshot['period'],
                'original_fingerprint': correction.snapshot['original_fingerprint'],
                'approved_payslip_id': correction.approved_payslip_id,
            },
        )
    )


def create_adjustment(
    db,
    models,
    run_id,
    company_id,
    employee_id,
    adjustment_amount,
    adjustment_type,
    reason,
    user_id,
    basic_salary=Decimal('0'),
    *,
    source='',
    source_reference='',
    effective_date=None,
):
    """Persist an auditable draft; no payslip, bank amount or balance mutation."""
    try:
        _actor(db, models, company_id, user_id, ('owner', 'accountant'))
        amount = money(adjustment_amount, positive=True)
        if adjustment_type != 'addition' or source not in ('approved_overtime', 'approved_bonus'):
            raise ValueError('Only approved additional taxable overtime or bonus is supported.')
        reason, source_reference = reason.strip(), source_reference.strip()
        if not reason or len(reason) > 255 or not source_reference or len(source_reference) > 128:
            raise ValueError('Reason and supporting source reference are required and must fit their field limits.')
        effective = date.fromisoformat(effective_date) if isinstance(effective_date, str) else effective_date
        if not isinstance(effective, date):
            raise ValueError('The effective date of the correction is required.')
        run, original = _original(models, run_id, company_id, employee_id)
        correction = models.PayrollCorrection.query.filter_by(
            company_id=company_id, original_payslip_id=original.id, source_reference=source_reference
        ).first()
        if correction:
            if (correction.amount, correction.reason, correction.effective_date, correction.source) != (
                amount,
                reason,
                effective,
                source,
            ):
                raise ValueError('This source reference was already used with different correction details.')
            if correction.status == 'rejected':
                raise ValueError(
                    'This source correction was rejected. A revised request needs a new supporting reference.'
                )
            return AdjustmentResult(True, correction.id, correction.snapshot['employee']['name'], correction.net_delta)
        if models.PayrollCorrection.query.filter_by(
            company_id=company_id, original_payslip_id=original.id, status='draft'
        ).first():
            raise ValueError('Approve or reject the pending correction for this employee first.')
        context = copy.deepcopy(original.calculation_context)
        frozen_tax(original.taxable_income, context)
        calculation_date = date.fromisoformat(context['calculation_date'])
        period_start = date.fromisoformat(context['period_start'])
        if not period_start <= effective <= calculation_date:
            raise ValueError('The effective date must fall inside the retained payroll period.')
        prior = _approved(models, company_id, original.id)
        approved_ids = {c.approved_payslip_id for c in prior}
        old = models.Payslip.query.filter_by(
            company_id=company_id, original_payslip_id=original.id, payslip_type='adjustment'
        ).all()
        if any(ps.id not in approved_ids for ps in old):
            raise ValueError('A legacy adjustment needs historical review before further corrections.')
        gross = original.gross_salary + sum((c.amount for c in prior), Decimal('0'))
        tax = original.tax + sum((c.tax_delta for c in prior), Decimal('0'))
        net = original.net_pay + sum((c.net_delta for c in prior), Decimal('0'))
        taxable = original.taxable_income + sum((c.amount for c in prior), Decimal('0'))
        calc = calculate_adjustment(
            gross, tax, original.employee_pension, net, amount, taxable_income=taxable, tax_context=context
        )
        correction = models.PayrollCorrection(
            company_id=company_id,
            payroll_run_id=run.id,
            employee_id=employee_id,
            original_payslip_id=original.id,
            source=source,
            source_reference=source_reference,
            effective_date=effective,
            reason=reason,
            amount=amount,
            tax_delta=calc['adjustment_tax'],
            net_delta=calc['adjustment_net'],
            created_by=user_id,
            status='draft',
            snapshot={
                'period': run.period,
                'run_date': run.run_date.isoformat(),
                'original_fingerprint': _fingerprint(original),
                'prior_correction_ids': [c.id for c in prior],
                'context': context,
                'employee': context['employee'],
                'baseline_taxable': str(taxable),
                'baseline_tax': str(tax),
                'baseline_gross': str(gross),
                'baseline_net': str(net),
                'new_total_net': str(calc['new_total_net']),
            },
        )
        db.session.add(correction)
        db.session.flush()
        _audit(db, models, correction, user_id, 'payroll_correction_drafted')
        db.session.commit()
        return AdjustmentResult(True, correction.id, context['employee']['name'], correction.net_delta)
    except (ValueError, TypeError, KeyError) as exc:
        db.session.rollback()
        return AdjustmentResult(False, error=str(exc))
    except Exception:
        db.session.rollback()
        raise


def decide_adjustment(db, models, run_id, company_id, correction_id, user_id, *, approve=True):
    try:
        _actor(db, models, company_id, user_id, ('owner',))
        correction = models.PayrollCorrection.query.filter_by(
            id=correction_id, company_id=company_id, payroll_run_id=run_id
        ).first()
        if correction is None:
            raise ValueError('Correction not found.')
        run, original = _original(models, run_id, company_id, correction.employee_id)
        correction = (
            models.PayrollCorrection.query.filter_by(id=correction_id, company_id=company_id, payroll_run_id=run_id)
            .with_for_update()
            .populate_existing()
            .one()
        )
        if correction.status == ('approved' if approve else 'rejected'):
            return AdjustmentResult(True, correction.id, correction.snapshot['employee']['name'], correction.net_delta)
        if correction.status != 'draft':
            raise ValueError('This correction is already decided.')
        snapshot = correction.snapshot
        if approve:
            prior = _approved(models, company_id, original.id)
            actual = {
                'baseline_gross': original.gross_salary + sum((c.amount for c in prior), Decimal('0')),
                'baseline_tax': original.tax + sum((c.tax_delta for c in prior), Decimal('0')),
                'baseline_net': original.net_pay + sum((c.net_delta for c in prior), Decimal('0')),
                'baseline_taxable': original.taxable_income + sum((c.amount for c in prior), Decimal('0')),
            }
            if (
                any(Decimal(snapshot[key]) != value for key, value in actual.items())
                or snapshot['context'] != original.calculation_context
            ):
                raise ValueError('The retained correction basis changed. Reject and review this draft again.')
            if (
                _fingerprint(original) != snapshot['original_fingerprint']
                or run.period != snapshot['period']
                or run.run_date.isoformat() != snapshot['run_date']
                or [c.id for c in _approved(models, company_id, original.id)] != snapshot['prior_correction_ids']
            ):
                raise ValueError('Approved payroll context changed. Reject this draft and review the correction again.')
            calc = calculate_adjustment(
                snapshot['baseline_gross'],
                snapshot['baseline_tax'],
                original.employee_pension,
                snapshot['baseline_net'],
                correction.amount,
                taxable_income=snapshot['baseline_taxable'],
                tax_context=snapshot['context'],
            )
            if (calc['adjustment_tax'], calc['adjustment_net']) != (correction.tax_delta, correction.net_delta):
                raise ValueError('Correction amounts changed after review.')
            payslip = models.Payslip(
                company_id=company_id,
                payroll_run_id=run_id,
                employee_id=correction.employee_id,
                original_payslip_id=original.id,
                payslip_type='adjustment',
                reason=correction.reason,
                gross_salary=correction.amount,
                tax=correction.tax_delta,
                employee_pension=0,
                employer_pension=0,
                net_pay=correction.net_delta,
                taxable_income=correction.amount,
                exempt_allowances=0,
                line_items=[
                    {
                        'item_key': correction.source,
                        'item_label': correction.reason,
                        'classification': 'earning',
                        'earned_amount': str(correction.amount),
                        'is_deduction': False,
                    }
                ],
                calculation_context=copy.deepcopy(snapshot['context']),
            )
            db.session.add(payslip)
            db.session.flush()
            correction.approved_payslip_id = payslip.id
            correction.approved_by = user_id
            correction.approved_at = datetime.now(UTC).replace(tzinfo=None)
            correction.status = 'approved'
        else:
            correction.status = 'rejected'
        _audit(
            db, models, correction, user_id, 'payroll_correction_approved' if approve else 'payroll_correction_rejected'
        )
        db.session.commit()
        return AdjustmentResult(True, correction.id, snapshot['employee']['name'], correction.net_delta)
    except (ValueError, KeyError, TypeError) as exc:
        db.session.rollback()
        return AdjustmentResult(False, error=str(exc))
    except Exception:
        db.session.rollback()
        raise


def correction_output(correction, payslip):
    identity = correction.snapshot['employee']
    return {
        'id': identity['id'],
        'employee_pk': correction.employee_id,
        'name': identity['name'],
        'bank': identity['bank'],
        'tin': identity.get('tin', ''),
        'department': identity.get('department', ''),
        'position': identity.get('position', ''),
        'basic': 0,
        'allowances': 0,
        'gross': payslip.gross_salary,
        'taxable': payslip.taxable_income,
        'tax': payslip.tax,
        'pension_employee': payslip.employee_pension,
        'pension_employer': payslip.employer_pension,
        'net': payslip.net_pay,
        'exempt_allowances': 0,
        'total_deductions': 0,
        'sick_leave_reduction': 0,
        'unpaid_leave_reduction': 0,
        'deduction_details': [],
        'line_items': [
            dict(item, earned_amount=Decimal(str(item['earned_amount']))) for item in (payslip.line_items or [])
        ],
        'worksheet_period_start': correction.snapshot['context']['period_start'],
        'calculation_date': correction.snapshot['context']['calculation_date'],
        'correction_note': f'Approved correction to payslip {correction.original_payslip_id}; source {correction.source_reference}. Tax for the corrected period minus retained tax: {Decimal(correction.snapshot["baseline_tax"]) + correction.tax_delta:,.2f} - {Decimal(correction.snapshot["baseline_tax"]):,.2f} = {correction.tax_delta:,.2f} ETB. Original payslip is unchanged.',
    }


def get_adjustment_summary(db, models, run_id, company_id):
    run = models.PayrollRun.query.filter_by(id=run_id, company_id=company_id).first()
    summary = AdjustmentSummary(run_id, run.period if run else '')
    if not run:
        return summary
    corrections = (
        models.PayrollCorrection.query.filter_by(company_id=company_id, payroll_run_id=run_id)
        .order_by(models.PayrollCorrection.id)
        .all()
    )
    for c in corrections:
        summary.adjustments.append(
            {
                'id': c.id,
                'employee_id': c.snapshot['employee']['id'],
                'employee_name': c.snapshot['employee']['name'],
                'type': 'addition',
                'gross': c.amount,
                'tax': c.tax_delta,
                'pension': Decimal('0'),
                'net': c.net_delta,
                'original_net': Decimal(c.snapshot['baseline_net']),
                'new_total': Decimal(c.snapshot['new_total_net']),
                'reason': c.reason,
                'source': c.source,
                'source_reference': c.source_reference,
                'status': c.status,
                'effective_date': c.effective_date.isoformat(),
                'created_at': c.created_at.isoformat(),
            }
        )
        summary.pending_count += c.status == 'draft'
        if c.status == 'approved':
            summary.total_adjustments += 1
            summary.total_positive_net += c.net_delta
    linked = {c.approved_payslip_id for c in corrections if c.approved_payslip_id}
    legacy = models.Payslip.query.filter_by(
        company_id=company_id, payroll_run_id=run_id, payslip_type='adjustment'
    ).all()
    summary.legacy_count = sum(ps.id not in linked for ps in legacy)
    summary.net_adjustment = summary.total_positive_net
    summary.employees_affected = len({c.employee_id for c in corrections if c.status == 'approved'})
    return summary


def generate_adjustment_bank_file(db, models, run_id, company_id):
    from payroll_engine.bank_file import generate_csv, validate_account_number

    run = models.PayrollRun.query.filter_by(id=run_id, company_id=company_id).first()
    if not run:
        return None
    corrections = (
        models.PayrollCorrection.query.filter_by(company_id=company_id, payroll_run_id=run_id, status='approved')
        .order_by(models.PayrollCorrection.id)
        .all()
    )
    rows = {}
    for c in corrections:
        ps = models.Payslip.query.filter_by(
            id=c.approved_payslip_id, company_id=company_id, payroll_run_id=run_id
        ).first()
        if ps is None or ps.net_pay != c.net_delta:
            raise ValueError('Approved correction and payable output do not reconcile.')
        if ps.payment_status == 'paid':
            continue
        row = correction_output(c, ps)
        bank = row['bank'].strip()
        prefix, account = bank.split(':', 1) if ':' in bank else ('cbe', bank)
        valid, _error = validate_account_number(account.strip(), 'cbe')
        if prefix.lower() != 'cbe' or not valid:
            raise ValueError('Retained payment instructions are not valid for CBE. Review them before exporting.')
        key = (row['id'], bank)
        if key not in rows:
            rows[key] = {'id': row['id'], 'name': row['name'], 'bank': bank, 'net': Decimal('0')}
        rows[key]['net'] += ps.net_pay
    return (
        generate_csv(list(rows.values()), bank='cbe', company_name='', period=f'{run.period} (Approved corrections)')
        if rows
        else None
    )
