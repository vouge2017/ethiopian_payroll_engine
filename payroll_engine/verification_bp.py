"""
Accountant Verification Blueprint — self-guided verification flow.

Walks accountants through verifying the system's calculations step by step.
Includes feedback form for flagging issues.
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from . import db
from .models import Company, User
import json
from datetime import datetime, timezone

verification_bp = Blueprint('verification', __name__)


# Verification steps — each maps to a section in VERIFICATION_PACKAGE.md
VERIFICATION_STEPS = [
    {
        'id': 'tax_brackets',
        'title': 'Income Tax Brackets',
        'section': 1,
        'description': 'Verify the tax brackets match Proclamation No. 1395/2025, Article 11',
        'what_to_check': 'Compare our brackets against the actual proclamation text',
        'impact': 'HIGH — wrong brackets = wrong tax for every employee',
        'fields': [
            '0 – 2,000 ETB: 0%',
            '2,001 – 4,000 ETB: 15%',
            '4,001 – 7,000 ETB: 20%',
            '7,001 – 10,000 ETB: 25%',
            '10,001 – 14,000 ETB: 30%',
            '14,001+ ETB: 35%',
        ],
    },
    {
        'id': 'paye_method',
        'title': 'PAYE Calculation Method',
        'section': 2,
        'description': 'Verify the order of deductions from gross salary',
        'what_to_check': 'Is pension deducted before tax? Are there other pre-tax deductions?',
        'impact': 'HIGH — wrong order = wrong tax for every employee',
        'fields': [
            '1. Start with gross salary',
            '2. Subtract pension (7% of basic) → taxable income',
            '3. Apply tax brackets → PAYE tax',
            '4. Net = gross − pension − PAYE',
        ],
    },
    {
        'id': 'pension',
        'title': 'Pension Contributions',
        'section': 4,
        'description': 'Verify pension rates and ceiling',
        'what_to_check': 'Are the rates correct? Is there a salary ceiling?',
        'impact': 'HIGH — wrong pension = wrong deductions for every employee',
        'fields': [
            'Employee: 7% of basic salary',
            'Employer: 11% of basic salary',
            'Ceiling: None (no statutory cap)',
        ],
    },
    {
        'id': 'overtime',
        'title': 'Overtime Rates',
        'section': 5,
        'description': 'Verify overtime multipliers',
        'what_to_check': 'Are the rates correct? Is the hourly rate formula correct?',
        'impact': 'MEDIUM — affects employees with overtime',
        'fields': [
            'Day overtime: 1.5× hourly rate',
            'Night overtime: 1.75× hourly rate',
            'Holiday overtime: 2.0× hourly rate',
            'Rest day + holiday: 2.5× hourly rate',
            'Hourly rate = basic salary ÷ 26 ÷ 8',
        ],
    },
    {
        'id': 'leave',
        'title': 'Leave & Sick Pay',
        'section': 6,
        'description': 'Verify leave entitlements',
        'what_to_check': 'Are the leave days and sick pay rates correct?',
        'impact': 'MEDIUM — affects employee benefits',
        'fields': [
            'Annual leave: 16 days (year 1), +1 day every 2 years',
            'Sick leave: 180 days total',
            'Sick pay: 100% (days 1-30), 50% (days 31-90), 0% (days 91-180)',
            'Maternity: 120 days',
            'Paternity: 3 days',
        ],
    },
    {
        'id': 'severance',
        'title': 'Severance Pay',
        'section': 7,
        'description': 'Verify severance formula',
        'what_to_check': 'Is the formula correct? Is the maximum cap correct?',
        'impact': 'MEDIUM — affects terminated employees',
        'fields': [
            'Year 1: 30 days basic salary',
            'Each additional year: +10 days',
            'Maximum: 12 months basic salary',
        ],
    },
    {
        'id': 'allowances',
        'title': 'Allowances (Taxable vs Exempt)',
        'section': 8,
        'description': 'Verify which allowances are taxable',
        'what_to_check': 'Are transport, housing, meal allowances correctly classified?',
        'impact': 'HIGH — wrong classification = wrong tax for every employee',
        'fields': [
            'Transport: taxable (no exempt limit)',
            'Housing: taxable',
            'Meal: taxable',
            'Medical: taxable',
            'Overtime: taxable (already in Section 5)',
        ],
    },
    {
        'id': 'erca_filing',
        'title': 'ERCA Filing Format',
        'section': 12,
        'description': 'Verify the ERCA filing columns match the portal',
        'what_to_check': 'Do the columns match what the ERCA portal expects?',
        'impact': 'HIGH — wrong format = filing rejected',
        'fields': [
            'Employee Full Name',
            'Start Date / End Date',
            'Basic Salary',
            'Transport Allowance',
            'Taxable Transport Allowance',
            'Over Time',
            'Other Taxable Benefit',
            'Total Taxable',
            'Tax Withheld',
        ],
    },
    {
        'id': 'deadlines',
        'title': 'Compliance Deadlines',
        'section': 14,
        'description': 'Verify filing deadlines',
        'what_to_check': 'Are the default deadlines correct?',
        'impact': 'MEDIUM — wrong deadlines = late filing penalties',
        'fields': [
            'ERCA tax filing: 25th of following month',
            'Pension remittance: 10th of following month',
            'PSSA contribution: 10th of following month',
            'Salary disbursement: 5 days after month end',
        ],
    },
    {
        'id': 'record_keeping',
        'title': 'Record Keeping',
        'section': 15,
        'description': 'Verify data retention period',
        'what_to_check': 'Is 10 years the correct retention period?',
        'impact': 'LOW — affects compliance, not calculations',
        'fields': [
            'Payroll records: 10 years (3,650 days)',
        ],
    },
]


@verification_bp.route('/verification')
@login_required
def verification_home():
    """Verification home — shows all steps with progress."""
    from payroll_engine.models import SystemSetting

    # Load saved progress
    progress_json = SystemSetting.get(f'verification_progress_{current_user.id}')
    progress = json.loads(progress_json) if progress_json else {}

    completed = sum(1 for s in VERIFICATION_STEPS if progress.get(s['id'], {}).get('verified'))
    total = len(VERIFICATION_STEPS)

    return render_template(
        'verification.html',
        steps=VERIFICATION_STEPS,
        progress=progress,
        completed=completed,
        total=total,
    )


@verification_bp.route('/verification/<step_id>', methods=['GET', 'POST'])
@login_required
def verification_step(step_id):
    """Single verification step — show details and collect response."""
    step = next((s for s in VERIFICATION_STEPS if s['id'] == step_id), None)
    if not step:
        flash('Verification step not found.', 'danger')
        return redirect(url_for('verification.verification_home'))

    from payroll_engine.models import SystemSetting

    if request.method == 'POST':
        verified = request.form.get('verified') == 'on'
        correct = request.form.get('correct') == 'on'
        correction = request.form.get('correction', '').strip()
        notes = request.form.get('notes', '').strip()

        # Save progress
        progress_json = SystemSetting.get(f'verification_progress_{current_user.id}')
        progress = json.loads(progress_json) if progress_json else {}
        progress[step_id] = {
            'verified': verified,
            'correct': correct,
            'correction': correction,
            'notes': notes,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        SystemSetting.set(f'verification_progress_{current_user.id}', json.dumps(progress))

        if verified and correct:
            flash(f'✓ {step["title"]} confirmed as correct.', 'success')
        elif verified and not correct:
            flash(f'⚠ {step["title"]} flagged with correction. Thank you!', 'warning')
        else:
            flash(f'Step saved as draft.', 'info')

        # Go to next step
        current_idx = next(i for i, s in enumerate(VERIFICATION_STEPS) if s['id'] == step_id)
        if current_idx + 1 < len(VERIFICATION_STEPS):
            next_step = VERIFICATION_STEPS[current_idx + 1]
            return redirect(url_for('verification.verification_step', step_id=next_step['id']))
        else:
            return redirect(url_for('verification.verification_summary'))

    # Load existing progress
    progress_json = SystemSetting.get(f'verification_progress_{current_user.id}')
    progress = json.loads(progress_json) if progress_json else {}
    step_progress = progress.get(step_id, {})

    current_idx = next(i for i, s in enumerate(VERIFICATION_STEPS) if s['id'] == step_id)

    return render_template(
        'verification_step.html',
        step=step,
        progress=step_progress,
        current_idx=current_idx,
        total=len(VERIFICATION_STEPS),
    )


@verification_bp.route('/verification/summary')
@login_required
def verification_summary():
    """Summary of all verification responses."""
    from payroll_engine.models import SystemSetting

    progress_json = SystemSetting.get(f'verification_progress_{current_user.id}')
    progress = json.loads(progress_json) if progress_json else {}

    results = []
    for step in VERIFICATION_STEPS:
        p = progress.get(step['id'], {})
        results.append({
            'step': step,
            'verified': p.get('verified', False),
            'correct': p.get('correct', False),
            'correction': p.get('correction', ''),
            'notes': p.get('notes', ''),
        })

    verified_count = sum(1 for r in results if r['verified'])
    correct_count = sum(1 for r in results if r['verified'] and r['correct'])
    flagged_count = sum(1 for r in results if r['verified'] and not r['correct'])

    return render_template(
        'verification_summary.html',
        results=results,
        verified_count=verified_count,
        correct_count=correct_count,
        flagged_count=flagged_count,
        total=len(VERIFICATION_STEPS),
    )


@verification_bp.route('/verification/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submit general feedback about the system."""
    data = request.get_json() or request.form
    feedback_text = data.get('feedback', '').strip()
    category = data.get('category', 'general')

    if not feedback_text:
        return jsonify({'error': 'Feedback text is required'}), 400

    from payroll_engine.models import SystemSetting

    # Store feedback
    feedback_json = SystemSetting.get('accountant_feedback')
    feedback_list = json.loads(feedback_json) if feedback_json else []
    feedback_list.append({
        'user_id': current_user.id,
        'category': category,
        'feedback': feedback_text,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })
    SystemSetting.set('accountant_feedback', json.dumps(feedback_list))

    return jsonify({'status': 'received', 'message': 'Thank you for your feedback!'})
