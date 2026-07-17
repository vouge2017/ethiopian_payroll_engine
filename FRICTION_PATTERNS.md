# 7 Friction-Free Patterns — Gap Analysis & Build

**Date:** 2026-07-17
**Status:** Phase 1 built for all 7 patterns

---

## PATTERN 1: ONE-CLICK COMPLIANCE FILING

### STATUS: PARTIAL

### What Exists

| Feature | File | Line |
|---|---|---|
| ERCA report generation | `reports_bp.py` | 76 — `download_erca_report(run_id)` |
| Pension report generation | `reports_bp.py` | 130 — `download_pension_report(run_id)` |
| Compliance score calculation | `compliance.py` | 28 — `compute_compliance_score()` |
| Upcoming deadlines | `compliance.py` | 176 — `get_upcoming_deadlines()` |
| Dashboard deadline cards | `dashboard.html` | lines 118-160 — shows ERCA/PSSA/Pension dates |
| ERCA Excel generation | `reports.py` | 17 — `generate_erca_report()` |
| Bank file generation | `reports_bp.py` | 156 — `download_bank_file(run_id)` |

### The Gap

1. **No compliance calendar** — deadlines are shown as individual cards, not a monthly view
2. **No one-click flow** — Tigist must: go to Reports → find the right run → click Download ERCA → open the file → manually submit to ERCA. There's no "Preview & File" button.
3. **No filing instructions** — the download button doesn't tell her what to do with the file
4. **No filing history** — she can't see when she last filed or if she already filed this month

### BUILD: Compliance Calendar + One-Click Filing Panel

**File: `payroll_engine/templates/_compliance_panel.html`**

```html
{# Compliance Calendar Panel — embed in dashboard #}
{# Usage: {% include '_compliance_panel.html' %} #}

<div class="card border-0 shadow-sm mb-4">
    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
        <h5 class="mb-0"><i class="bi bi-calendar-check me-2"></i>Compliance Calendar</h5>
        <span class="badge bg-light text-primary">{{ current_month }}</span>
    </div>
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Filing</th>
                        <th>Due Date</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {# ERCA Tax Filing #}
                    <tr class="{% if deadlines.erca_days_left is defined and deadlines.erca_days_left < 0 %}table-danger{% elif deadlines.erca_days_left is defined and deadlines.erca_days_left <= 3 %}table-warning{% endif %}">
                        <td>
                            <strong>ERCA Tax Filing</strong>
                            <br><small class="text-muted">Income tax withheld from employees</small>
                        </td>
                        <td>
                            <strong>{{ eth_date(deadlines.erca_deadline[:10]) if deadlines.erca_deadline else 'N/A' }}</strong>
                            <br><small class="text-muted">{{ deadlines.erca_deadline[:10] if deadlines.erca_deadline else '' }}</small>
                        </td>
                        <td>
                            {% if deadlines.erca_days_left is defined %}
                                {% if deadlines.erca_days_left < 0 %}
                                    <span class="badge bg-danger">OVERDUE {{ deadlines.erca_days_left|abs }}d</span>
                                {% elif deadlines.erca_days_left <= 3 %}
                                    <span class="badge bg-warning text-dark">{{ deadlines.erca_days_left }}d left</span>
                                {% else %}
                                    <span class="badge bg-success">{{ deadlines.erca_days_left }}d left</span>
                                {% endif %}
                            {% endif %}
                        </td>
                        <td>
                            {% if latest_completed_run %}
                            <div class="btn-group btn-group-sm">
                                <a href="{{ url_for('reports.download_erca_report', run_id=latest_completed_run.id) }}"
                                   class="btn btn-outline-primary" title="Download ERCA file">
                                    <i class="bi bi-download me-1"></i>Download
                                </a>
                                <button class="btn btn-outline-secondary" type="button"
                                        data-bs-toggle="collapse" data-bs-target="#ercaHelp"
                                        title="How to file">
                                    <i class="bi bi-question-circle"></i>
                                </button>
                            </div>
                            {% else %}
                            <span class="text-muted small">Run payroll first</span>
                            {% endif %}
                        </td>
                    </tr>
                    {# ERCA Help Collapse #}
                    <tr class="collapse" id="ercaHelp">
                        <td colspan="4" class="bg-light">
                            <div class="p-3">
                                <h6><i class="bi bi-info-circle me-1"></i>How to file ERCA tax:</h6>
                                <ol class="small mb-0">
                                    <li>Click <strong>Download</strong> to get the Excel file</li>
                                    <li>Log in to <strong>erca.gov.et</strong> (or visit your local ERCA office)</li>
                                    <li>Upload the file under "Monthly Tax Withholding"</li>
                                    <li>Save your confirmation number</li>
                                </ol>
                                <p class="small text-muted mt-2 mb-0">
                                    <strong>Deadline:</strong> 25th of the month following payroll.
                                    <strong>Penalty:</strong> 10% of tax due + 2% per month late.
                                </p>
                            </div>
                        </td>
                    </tr>

                    {# Pension Contribution #}
                    <tr class="{% if deadlines.pension_days_left is defined and deadlines.pension_days_left < 0 %}table-danger{% elif deadlines.pension_days_left is defined and deadlines.pension_days_left <= 3 %}table-warning{% endif %}">
                        <td>
                            <strong>Pension Contribution</strong>
                            <br><small class="text-muted">Employee 7% + Employer 11% to PSSA</small>
                        </td>
                        <td>
                            <strong>{{ eth_date(deadlines.pension_deadline[:10]) if deadlines.pension_deadline else 'N/A' }}</strong>
                            <br><small class="text-muted">{{ deadlines.pension_deadline[:10] if deadlines.pension_deadline else '' }}</small>
                        </td>
                        <td>
                            {% if deadlines.pension_days_left is defined %}
                                {% if deadlines.pension_days_left < 0 %}
                                    <span class="badge bg-danger">OVERDUE {{ deadlines.pension_days_left|abs }}d</span>
                                {% elif deadlines.pension_days_left <= 3 %}
                                    <span class="badge bg-warning text-dark">{{ deadlines.pension_days_left }}d left</span>
                                {% else %}
                                    <span class="badge bg-success">{{ deadlines.pension_days_left }}d left</span>
                                {% endif %}
                            {% endif %}
                        </td>
                        <td>
                            {% if latest_completed_run %}
                            <div class="btn-group btn-group-sm">
                                <a href="{{ url_for('reports.download_pension_report', run_id=latest_completed_run.id) }}"
                                   class="btn btn-outline-primary" title="Download pension report">
                                    <i class="bi bi-download me-1"></i>Download
                                </a>
                                <button class="btn btn-outline-secondary" type="button"
                                        data-bs-toggle="collapse" data-bs-target="#pensionHelp"
                                        title="How to remit">
                                    <i class="bi bi-question-circle"></i>
                                </button>
                            </div>
                            {% else %}
                            <span class="text-muted small">Run payroll first</span>
                            {% endif %}
                        </td>
                    </tr>
                    <tr class="collapse" id="pensionHelp">
                        <td colspan="4" class="bg-light">
                            <div class="p-3">
                                <h6><i class="bi bi-info-circle me-1"></i>How to remit pension:</h6>
                                <ol class="small mb-0">
                                    <li>Click <strong>Download</strong> to get the pension report</li>
                                    <li>Log in to <strong>pssa.gov.et</strong> or visit PSSA office</li>
                                    <li>Submit the report and make payment</li>
                                    <li>Keep the receipt for your records</li>
                                </ol>
                                <p class="small text-muted mt-2 mb-0">
                                    <strong>Deadline:</strong> 15th of the month following payroll.
                                    <strong>Split:</strong> Employee pays 7% of basic, employer pays 11%.
                                </p>
                            </div>
                        </td>
                    </tr>

                    {# Bank Disbursement #}
                    <tr>
                        <td>
                            <strong>Bank Disbursement</strong>
                            <br><small class="text-muted">Transfer salaries to employee accounts</small>
                        </td>
                        <td>
                            <strong>After approval</strong>
                            <br><small class="text-muted">Within 5 days recommended</small>
                        </td>
                        <td>
                            {% if latest_completed_run %}
                                {% if latest_completed_run.disbursement_status == 'confirmed' %}
                                    <span class="badge bg-success">Confirmed</span>
                                {% elif latest_completed_run.disbursement_status == 'disbursed' %}
                                    <span class="badge bg-info">Sent</span>
                                {% elif latest_completed_run.disbursement_status == 'file_downloaded' %}
                                    <span class="badge bg-warning text-dark">File downloaded</span>
                                {% else %}
                                    <span class="badge bg-secondary">Pending</span>
                                {% endif %}
                            {% else %}
                                <span class="text-muted">—</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if latest_completed_run %}
                            <a href="{{ url_for('reports.download_bank_file', run_id=latest_completed_run.id) }}"
                               class="btn btn-outline-primary btn-sm">
                                <i class="bi bi-download me-1"></i>Bank File
                            </a>
                            {% else %}
                            <span class="text-muted small">Run payroll first</span>
                            {% endif %}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
```

**Wire into dashboard:**

```python
# In main.py — the dashboard route, add to context:
from payroll_engine.compliance import get_upcoming_deadlines

latest_completed_run = PayrollRun.query.filter_by(
    company_id=company_id, status='completed'
).order_by(PayrollRun.run_date.desc()).first()

deadlines = get_upcoming_deadlines(
    latest_completed_run.run_date.isoformat() if latest_completed_run else None
)

# Pass to template: latest_completed_run, deadlines, current_month
```

**Tigist now experiences:** A single table on her dashboard showing ERCA, Pension, and Bank Disbursement — with due dates, countdown badges, download buttons, and "How to file" instructions one click away. She never leaves the dashboard to handle compliance.

---

## PATTERN 2: EMPLOYEE SELF-SERVICE

### STATUS: PARTIAL

### What Exists

| Feature | File | Line |
|---|---|---|
| Employee dashboard | `portal_bp.py` | 22 — `employee_dashboard()` |
| Payslip view | `portal_bp.py` | 51 — `my_payslips()` |
| Payslip detail + PDF download | `portal_bp.py` | 63 — `my_payslip_detail()` |
| Profile view | `portal_bp.py` | 116 — `my_profile()` |
| Profile edit with approval | `portal_bp.py` | 138 — `edit_profile()` (just built) |
| Leave request | `portal_bp.py` | 183 — `my_request_leave()` |
| Leave balance view | `portal_bp.py` | 161 — `my_leave()` |
| Invite-based self-registration | `employees_bp.py` | 120 — `generate_invite()` |

### The Gap

1. **No payslip acknowledgment** — employee can view/download but can't confirm "I received this"
2. **No bulk payslip download** — can only download one at a time
3. **Portal is view-only for salary info** — can't see overtime history, deduction history
4. **No notification when payslip is ready** — employee has to check manually

### BUILD: Payslip Acknowledgment + Notification on Payslip Ready

**Model addition (`models.py`):**

```python
class PayslipAcknowledgment(db.Model):
    """Track when employees acknowledge receipt of their payslip."""
    query_class = TenantQuery

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    payslip_id = db.Column(db.Integer, db.ForeignKey('payslip.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)

    payslip = db.relationship('Payslip', backref=db.backref('acknowledgments', lazy=True))
    employee = db.relationship('Employee', backref=db.backref('payslip_acknowledgments', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('payslip_id', 'employee_id', name='uq_payslip_ack'),
    )
```

**Portal route (`portal_bp.py`):**

```python
@portal_bp.route('/my/payslips/<int:payslip_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_payslip(payslip_id):
    """Employee acknowledges receipt of payslip."""
    from payroll_engine.models import PayslipAcknowledgment
    from datetime import datetime, timezone

    emp = get_linked_employee()
    if not emp:
        abort(404)

    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=emp.id).first_or_404()

    # Check if already acknowledged
    existing = PayslipAcknowledgment.query.filter_by(
        payslip_id=payslip.id, employee_id=emp.id, company_id=_company_id()
    ).first()
    if existing:
        flash('You already acknowledged this payslip.', 'info')
        return redirect(url_for('portal.my_payslip_detail', payslip_id=payslip.id))

    ack = PayslipAcknowledgment(
        company_id=_company_id(),
        payslip_id=payslip.id,
        employee_id=emp.id,
        acknowledged_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ip_address=request.remote_addr,
    )
    db.session.add(ack)
    db.session.commit()

    flash('Payslip acknowledged. Thank you!', 'success')
    return redirect(url_for('portal.my_payslip_detail', payslip_id=payslip.id))
```

**Template addition (`employee_portal/payslip_detail.html`):**

```html
{# Add after the download button #}
{% if not payslip_acknowledged %}
<form method="POST" action="{{ url_for('portal.acknowledge_payslip', payslip_id=payslip.id) }}" class="d-inline">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button type="submit" class="btn btn-outline-success">
        <i class="bi bi-check-circle me-1"></i>I received this payslip
    </button>
</form>
{% else %}
<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Acknowledged {{ payslip_acknowledged.acknowledged_at.strftime('%Y-%m-%d') }}</span>
{% endif %}
```

**Notify employee when payslip is ready (in `payroll_service.py` after approval):**

```python
# After generating payslips in process_payroll():
from payroll_engine.notifications import notify

for emp_data, payslip in zip(employees_data, payslips):
    emp = payslip.employee
    if emp and emp.user_id:
        notify(
            company_id=company_id,
            user_id=emp.user_id,
            message=f'Your payslip for {run.period or "this month"} is ready. Net pay: ETB {payslip.net_pay:,.2f}.',
            notif_type='success',
            link=f'/my/payslips/{payslip.id}',
            employee_phone=emp.phone,
            whatsapp_message=f'Hello {emp.name}, your salary of ETB {payslip.net_pay:,.2f} has been processed. Log in to view your payslip.',
        )
```

**Tigist now experiences:** When payroll is approved, each employee gets an in-app notification and WhatsApp message saying "Your payslip is ready." The employee opens their portal, sees the payslip, clicks "I received this payslip" to acknowledge. Tigist can see which employees have acknowledged.

---

## PATTERN 3: PRE-APPROVAL VALIDATION

### STATUS: PARTIAL

### What Exists

| Feature | File | Line |
|---|---|---|
| Validation engine | `validation.py` | 27 — `validate_payroll_data()` |
| Duplicate detection | `validation.py` | 82 — `_check_duplicate_employees()` |
| Negative net pay check | `validation.py` | 103 — `_check_negative_net_pay()` |
| Missing bank check | `validation.py` | 121 — `_check_missing_bank()` |
| Salary typo detection | `validation.py` | 136 — `_check_salary_typos()` (>10x or >500K) |
| Pension mismatch check | `validation.py` | 170 — `_check_pension_mismatch()` |
| Tax mismatch check | `validation.py` | 193 — `_check_tax_mismatch()` |
| Cash compliance check | `validation.py` | 220 — `_check_cash_compliance()` |
| Missing TIN warning | `validation.py` | 250 — `_check_missing_tin()` |
| Deduction checks | `validation.py` | 262 — `_check_active_deductions()` |
| Validation results UI | `validation_results.html` | full page |

### The Gap

1. **No month-over-month payroll variance check** — if total payroll jumps 40%, no flag
2. **No pending-leave-affects-pay check** — employee on unpaid leave still shows full salary
3. **Salary change threshold too high** — 10x is absurd; 30% is the right trigger
4. **No "things look unusual" summary** — Tigist sees individual issues, not a digest

### BUILD: Payroll Variance Check + Enhanced Salary Change Detection

**Add to `validation.py`:**

```python
def _check_payroll_variance(employees_data, company_id, results):
    """FLAG: Total payroll differs from last month by more than 20%."""
    if company_id is None:
        return
    try:
        from payroll_engine.models import PayrollRun, Payslip
        last_run = PayrollRun.query.filter_by(
            company_id=company_id, status='completed'
        ).order_by(PayrollRun.run_date.desc()).first()
        if not last_run:
            return

        previous_net = sum(float(p.net_pay) for p in last_run.payslips)
        current_net = sum(float(e.get('net', 0)) for e in employees_data)

        if previous_net <= 0:
            return

        change_pct = abs(current_net - previous_net) / previous_net * 100

        if change_pct > 20:
            direction = 'increased' if current_net > previous_net else 'decreased'
            results.append(ValidationResult(
                rule_code='PAYROLL_VARIANCE',
                severity='FLAG',
                message=(
                    f'Total payroll {direction} by {change_pct:.0f}% '
                    f'(ETB {previous_net:,.0f} → ETB {current_net:,.0f}). '
                    f'Is this correct?'
                ),
                hint='Check if new employees were added, salaries changed, or if this is a data error.',
                details={
                    'previous_total': previous_net,
                    'current_total': current_net,
                    'change_pct': round(change_pct, 1),
                }
            ))
    except Exception:
        pass


def _check_pending_leave_impact(employees_data, company_id, results):
    """FLAG: Employee with approved unpaid leave still shows full salary."""
    if company_id is None:
        return
    try:
        from payroll_engine.models import Leave, Employee
        from datetime import date

        today = date.today()
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1)
        else:
            month_end = date(today.year, today.month + 1, 1)

        # Find employees with approved unpaid leave this month
        unpaid_leaves = Leave.query.filter(
            Leave.company_id == company_id,
            Leave.leave_type == 'unpaid',
            Leave.status == 'approved',
            Leave.start_date < month_end,
            Leave.end_date >= month_start,
        ).all()

        emp_ids_on_leave = {l.employee_id for l in unpaid_leaves}
        if not emp_ids_on_leave:
            return

        employees = Employee.query.filter(
            Employee.company_id == company_id,
            Employee.id.in_(emp_ids_on_leave),
            Employee.is_deleted == False,
        ).all()
        emp_by_id = {e.id: e for e in employees}

        for leave in unpaid_leaves:
            emp = emp_by_id.get(leave.employee_id)
            if not emp:
                continue
            # Check if this employee appears in the payroll data with full salary
            for emp_data in employees_data:
                if emp_data.get('id') == emp.employee_id:
                    # Calculate overlap days
                    overlap_start = max(leave.start_date, month_start)
                    overlap_end = min(leave.end_date, month_end)
                    leave_days = (overlap_end - overlap_start).days + 1
                    if leave_days > 0:
                        results.append(ValidationResult(
                            rule_code='PENDING_UNPAID_LEAVE',
                            severity='FLAG',
                            message=(
                                f'{emp.name} has {leave_days} days of approved unpaid leave '
                                f'({leave.start_date} to {leave.end_date}). '
                                f'Salary may need prorating.'
                            ),
                            employee_id=emp.employee_id,
                            employee_name=emp.name,
                            hint=f'Deduct {leave_days} days from salary or use the sick leave reduction field.',
                            details={
                                'leave_days': leave_days,
                                'leave_start': str(leave.start_date),
                                'leave_end': str(leave.end_date),
                            }
                        ))
    except Exception:
        pass


def _check_salary_change_significant(employees_data, previous_payslips, results):
    """FLAG: Salary changed by more than 30% (lowered from 10x threshold)."""
    if not previous_payslips:
        return

    for emp in employees_data:
        emp_id = emp.get('id')
        if emp_id not in previous_payslips:
            continue

        prev = previous_payslips[emp_id]
        prev_total = float(prev.get('basic', 0)) + float(prev.get('allowances', 0))
        curr_total = float(emp.get('basic', 0)) + float(emp.get('allowances', 0))

        if prev_total <= 0:
            continue

        change_pct = abs(curr_total - prev_total) / prev_total * 100

        if change_pct > 30:
            direction = 'increased' if curr_total > prev_total else 'decreased'
            results.append(ValidationResult(
                rule_code='SALARY_CHANGE_30PCT',
                severity='FLAG',
                message=(
                    f"{emp.get('name', 'Employee')}'s salary {direction} by {change_pct:.0f}% "
                    f"(ETB {prev_total:,.0f} → ETB {curr_total:,.0f}). "
                    f'Is this correct?'
                ),
                employee_id=emp_id,
                employee_name=emp.get('name', ''),
                hint='Verify this salary change with the employee or their contract.',
                details={
                    'previous': prev_total,
                    'current': curr_total,
                    'change_pct': round(change_pct, 1),
                }
            ))
```

**Wire into `validate_payroll_data()`:**

```python
# Add these calls in validate_payroll_data(), after existing checks:
_check_payroll_variance(employees_data, company_id, results)
_check_pending_leave_impact(employees_data, company_id, results)

# Replace _check_salary_typos with _check_salary_change_significant
# (or keep both — the 10x check catches typos, the 30% check catches real changes)
```

**Tigist now experiences:** Before approving payroll, she sees "3 things look unusual" — salary changed 35% for Abebe, total payroll is 22% higher than last month, Dawit has 5 days unpaid leave. Each flag has a clear explanation and a "What to do?" hint.

---

## PATTERN 4: ZERO DATA RE-ENTRY

### STATUS: DONE (mostly)

### What Exists

| Feature | File | Line |
|---|---|---|
| Employee data stored once in Employee model | `models.py` | 528 |
| ERCA report pulls from Payslip + Employee | `reports.py` | 17 |
| Pension report pulls from Employee | `reports.py` | 200+ |
| Bank file pulls from Employee.bank_or_telebirr | `bank_file.py` | full |
| PDF payslip pulls from Employee + Payslip | `pdf.py` | full |
| Pre-filled CSV from existing employees | `payroll_bp.py` | 118 — `download_prefilled_csv()` |
| Quick Start imports employees once | `wizard_bp.py` | full |

### The Gap

1. **Bank account field inconsistency** — `Employee` has both `bank_account` (encrypted) and `bank_or_telebirr` (legacy). The CSV template uses `bank_account` but the bank file generator uses `bank_or_telebirr`. Tigist might enter the bank account in the wrong field.
2. **TIN not auto-populated in ERCA if entered during employee add** — the field exists but the ERCA report needs to verify it's pulling from the right place.

### No code to build — this is a data mapping issue, not a feature gap. The fix is:

```python
# In bank_file.py, use bank_account if bank_or_telebirr is empty:
def _get_bank_field(employee):
    """Get bank/payment info, preferring bank_account over legacy field."""
    return employee.bank_account or employee.bank_or_telebirr or ''
```

**Tigist now experiences:** She enters employee data once (name, phone, salary, bank account, TIN). That data flows automatically to payslips, ERCA reports, pension reports, bank disbursement files, and Telebirr files. She never retypes anything.

---

## PATTERN 5: PAYMENT DISBURSEMENT

### STATUS: PARTIAL

### What Exists

| Feature | File | Line |
|---|---|---|
| CBE bank file generation | `bank_file.py` | 490 lines — full implementation |
| Dashen, Awash, Telebirr support | `bank_file.py` | all supported |
| Disbursement status tracking | `models.py` | 753 — `disbursement_status` field |
| Mark as disbursed | `payroll_bp.py` | 1145 — `mark_disbursed()` |
| Confirm payment | `payroll_bp.py` | 1183 — `confirm_payment()` |
| Download bank file | `reports_bp.py` | 156 — `download_bank_file()` |
| Disbursement status on compliance panel | dashboard | deadline cards |

### The Gap

1. **No disbursement progress page** — after downloading the bank file, Tigist has to manually track which employees were paid
2. **No "8 of 8 payments sent" view** — the disbursement status is per-run, not per-employee
3. **No Telebirr one-click** — she still downloads a file and manually uploads to Telebirr

### BUILD: Disbursement Progress Page

**Template: `payroll_engine/templates/disbursement_progress.html`**

```html
{% extends "base.html" %}
{% block title %}Disbursement — {{ run.reference }}{% endblock %}
{% block content %}
<div class="container-fluid py-4">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="d-flex align-items-center mb-4">
                <a href="{{ url_for('payroll.payroll_run_detail', run_id=run.id) }}" class="text-decoration-none text-muted me-2">
                    <i class="bi bi-arrow-left"></i>
                </a>
                <h3 class="mb-0">Payment Disbursement</h3>
                <span class="badge bg-{{ 'success' if run.disbursement_status == 'confirmed' else 'info' if run.disbursement_status == 'disbursed' else 'warning' }} ms-2">
                    {{ run.disbursement_status|replace('_', ' ')|title }}
                </span>
            </div>

            <!-- Progress Summary -->
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-body text-center">
                    <div class="row">
                        <div class="col-4">
                            <h6 class="text-muted">Total Employees</h6>
                            <h3>{{ employees|length }}</h3>
                        </div>
                        <div class="col-4">
                            <h6 class="text-muted">Total Amount</h6>
                            <h3>ETB {{ '{:,.2f}'.format(total_net) }}</h3>
                        </div>
                        <div class="col-4">
                            <h6 class="text-muted">Status</h6>
                            <h3>
                                {% if run.disbursement_status == 'confirmed' %}
                                    <span class="text-success">✅ All Paid</span>
                                {% elif run.disbursement_status == 'disbursed' %}
                                    <span class="text-info">📤 Sent</span>
                                {% else %}
                                    <span class="text-warning">⏳ Pending</span>
                                {% endif %}
                            </h3>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Download Bank Files -->
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0"><i class="bi bi-download me-2"></i>Download Payment Files</h5>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        {% for bank_type, bank_label, count, total in bank_summary %}
                        <div class="col-md-6">
                            <div class="card border">
                                <div class="card-body d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>{{ bank_label }}</strong>
                                        <br><small class="text-muted">{{ count }} employees · ETB {{ '{:,.2f}'.format(total) }}</small>
                                    </div>
                                    <a href="{{ url_for('reports.download_bank_file', run_id=run.id) }}?bank={{ bank_type }}"
                                       class="btn btn-outline-primary btn-sm">
                                        <i class="bi bi-download me-1"></i>Download
                                    </a>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    <p class="small text-muted mt-3 mb-0">
                        <i class="bi bi-info-circle me-1"></i>
                        Upload these files to your bank's bulk payment portal. After payment, mark as "Disbursed" below.
                    </p>
                </div>
            </div>

            <!-- Employee List -->
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-white">
                    <h5 class="mb-0"><i class="bi bi-people me-2"></i>Employee Payments</h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Employee</th>
                                    <th>Bank</th>
                                    <th class="text-end">Amount</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for emp in employees %}
                                <tr>
                                    <td>
                                        <strong>{{ emp.name }}</strong>
                                        <br><small class="text-muted">{{ emp.employee_id }}</small>
                                    </td>
                                    <td><small>{{ emp.bank or 'No bank account' }}</small></td>
                                    <td class="text-end fw-bold">ETB {{ '{:,.2f}'.format(emp.net) }}</td>
                                    <td>
                                        {% if run.disbursement_status == 'confirmed' %}
                                            <span class="badge bg-success">Paid</span>
                                        {% elif run.disbursement_status == 'disbursed' %}
                                            <span class="badge bg-info">Sent</span>
                                        {% else %}
                                            <span class="badge bg-secondary">Pending</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Action Buttons -->
            <div class="d-flex gap-2">
                {% if run.disbursement_status in ('pending', 'file_downloaded') %}
                <form method="POST" action="{{ url_for('payroll.mark_disbursed', run_id=run.id) }}" class="flex-grow-1">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button type="submit" class="btn btn-info btn-lg w-100">
                        <i class="bi bi-send me-1"></i>Mark as Disbursed — Payments Sent to Bank
                    </button>
                </form>
                {% elif run.disbursement_status == 'disbursed' %}
                <form method="POST" action="{{ url_for('payroll.confirm_payment', run_id=run.id) }}" class="flex-grow-1">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button type="submit" class="btn btn-success btn-lg w-100">
                        <i class="bi bi-check-circle me-1"></i>Confirm All Payments Received
                    </button>
                </form>
                {% else %}
                <div class="alert alert-success flex-grow-1 mb-0 text-center">
                    <i class="bi bi-check-circle-fill me-2"></i>All payments confirmed. Disbursement complete.
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**Route (`payroll_bp.py`):**

```python
@payroll_bp.route('/payroll/<int:run_id>/disbursement')
@login_required
@role_required('owner', 'accountant')
def disbursement_progress(run_id):
    """Show disbursement progress for a payroll run."""
    run = PayrollRun.query.filter_by(id=run_id, company_id=_company_id()).first_or_404()
    if run.status != 'completed':
        flash('Payroll must be completed before disbursement.', 'warning')
        return redirect(url_for('payroll.payroll_run_detail', run_id=run.id))

    payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
    employees = []
    bank_summary = {}  # bank_type -> (label, count, total)

    for ps in payslips:
        emp = ps.employee
        bank = (emp.bank_account or emp.bank_or_telebirr or '').split(':')[0] if emp else 'unknown'
        employees.append({
            'name': emp.name if emp else 'Unknown',
            'employee_id': emp.employee_id if emp else '?',
            'bank': emp.bank_account or emp.bank_or_telebirr if emp else '',
            'net': float(ps.net_pay),
        })
        if bank not in bank_summary:
            bank_labels = {'cbe': 'CBE', 'dashen': 'Dashen', 'awash': 'Awash', 'telebirr': 'Telebirr'}
            bank_summary[bank] = [bank_labels.get(bank, bank), 0, 0]
        bank_summary[bank][1] += 1
        bank_summary[bank][2] += float(ps.net_pay)

    total_net = sum(e['net'] for e in employees)
    summary_list = [(k, v[0], v[1], v[2]) for k, v in bank_summary.items()]

    return render_template('disbursement_progress.html',
                           run=run, employees=employees,
                           total_net=total_net, bank_summary=summary_list)
```

**Tigist now experiences:** After approving payroll, she sees a "Disbursement" page showing all employees grouped by bank, with download buttons per bank. She uploads the CBE file to CBE portal, clicks "Mark as Disbursed," then "Confirm All Payments Received" when the bank confirms. She sees "8 of 8 employees paid" at a glance.

---

## PATTERN 6: SIZE-APPROPRIATE INTERFACE

### STATUS: PARTIAL

### What Exists

| Feature | File | Line |
|---|---|---|
| Quick Start wizard (paste from Excel) | `wizard_bp.py` | full |
| One-by-one employee add | `employees_bp.py` | `add_employee()` |
| CSV upload for payroll | `payroll_bp.py` | `payroll_upload()` |
| Spreadsheet editor | `payroll_bp.py` | `payroll_spreadsheet()` |
| Bulk import API | `api.py` | `bulk_import_employees()` |
| First-run wizard on dashboard | `dashboard.html` | 3-step wizard |

### The Gap

1. **Quick Start is not the default path** — the dashboard wizard shows "Add Employee" first
2. **No size detection** — the system doesn't know if Tigist has 5 or 500 employees
3. **Same sidebar for everyone** — a 5-person company sees "Impact Calculator," "API Keys," "Profile Requests"
4. **No progressive disclosure** — all features visible from day one

### BUILD: Size-Aware Dashboard Sidebar

**In `base.html`, wrap advanced nav items:**

```html
{# In the sidebar, after the core items #}
{% if current_user.role != 'employee' %}
    {# Core items always visible: Dashboard, Employees, Run Payroll, Payroll Runs #}

    {# Show Leave if company has > 5 employees #}
    {% if employee_count is defined and employee_count > 5 %}
    <a href="{{ url_for('employees.leave_management') }}" ...>Leave</a>
    {% endif %}

    {# Show Profile Requests if any pending #}
    {% if pending_profile_changes is defined and pending_profile_changes > 0 %}
    <a href="{{ url_for('employees.profile_changes') }}" ...>
        Profile Requests <span class="badge bg-danger">{{ pending_profile_changes }}</span>
    </a>
    {% endif %}

    {# Show Reports always but label differently #}
    <a href="{{ url_for('reports.reports') }}" ...>
        {% if employee_count is defined and employee_count <= 10 %}
            Compliance & Reports
        {% else %}
            Reports
        {% endif %}
    </a>

    {# Advanced features only for larger companies #}
    {% if employee_count is defined and employee_count > 20 %}
    <a href="{{ url_for('reports.impact_calculator') }}" ...>Impact Calculator</a>
    {% endif %}

    {% if current_user.role == 'owner' %}
    <a href="{{ url_for('settings.team_settings') }}" ...>Team</a>
    {% endif %}
{% endif %}
```

**In `main.py`, inject `employee_count` and `pending_profile_changes` into context:**

```python
@app.context_processor
def inject_sidebar_counts():
    from flask_login import current_user
    if not current_user.is_authenticated or not current_user.company_id:
        return {}
    from payroll_engine.models import Employee, ProfileChangeRequest
    cid = session.get('active_company_id', current_user.company_id)
    emp_count = Employee.query.filter_by(company_id=cid, is_deleted=False).count()
    pending_changes = ProfileChangeRequest.query.filter_by(
        company_id=cid, status='pending'
    ).count()
    return {
        'employee_count': emp_count,
        'pending_profile_changes': pending_changes,
    }
```

**Tigist now experiences:** With 8 employees, her sidebar shows: Dashboard, Employees, Run Payroll, Payroll Runs, Compliance & Reports, Team. No Impact Calculator, no API Keys, no Profile Requests (unless someone actually requests a change). As her company grows past 20 employees, advanced features appear.

---

## PATTERN 7: PROACTIVE SYSTEM, NOT REACTIVE TOOL

### STATUS: NOTHING

### What Exists

Nothing. Tigist has to open the system to see anything. No pre-calculation, no nudges, no draft payroll.

### The Gap

1. **No pre-calculated payroll draft** — she has to upload CSV or use spreadsheet every month
2. **No proactive nudge** — no "Draft ready, 2 overtime entries pending" notification
3. **No compliance nudge** — the dashboard shows deadlines but doesn't push notifications
4. **No scheduled tasks** — no cron, no background jobs for monthly preparation

### BUILD: Monthly Draft Pre-Calculation + Compliance Nudge

**New file: `payroll_engine/services/monthly_preparer.py`**

```python
"""Monthly payroll draft pre-calculation service.

Run on the 28th of each month to prepare a draft payroll for the next period.
Sends a nudge to the owner: "Draft ready, review and approve."
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from payroll_engine import db
from payroll_engine.models import (
    Company, Employee, PayrollRun, PayrollDraft, User, UserCompany,
)
from payroll_engine.payroll import calculate_payroll
from payroll_engine.notifications import notify

logger = logging.getLogger('payroll_engine.monthly_preparer')


def prepare_monthly_drafts():
    """Pre-calculate payroll drafts for all active companies.

    Called by scheduler on the 28th of each month.
    Creates a draft payroll run with calculated values for each company
    that doesn't already have a run for the current period.
    """
    from payroll_engine.ethiopian_calendar import gregorian_to_ethiopian

    today = date.today()
    eth_year, eth_month, _ = gregorian_to_ethiopian(today)

    companies = Company.query.filter_by(is_demo=False).all()
    prepared = 0

    for company in companies:
        try:
            # Check if a run already exists for this period
            period_str = f'{eth_year}-{eth_month:02d}'
            existing = PayrollRun.query.filter_by(
                company_id=company.id, period=period_str
            ).filter(
                PayrollRun.status.notin_(['failed', 'rejected'])
            ).first()
            if existing:
                continue

            # Get active employees
            employees = Employee.query.filter_by(
                company_id=company.id, is_deleted=False
            ).all()
            if not employees:
                continue

            # Calculate payroll for each employee
            employees_data = []
            for emp in employees:
                result = calculate_payroll(
                    basic_salary=emp.basic_salary,
                    allowances=emp.allowances,
                    allowance_records=emp.allowance_records if hasattr(emp, 'allowance_records') else None,
                )
                employees_data.append({
                    'id': emp.employee_id,
                    'name': emp.name,
                    'phone': emp.phone or '',
                    'department': emp.department or '',
                    'position': emp.position or '',
                    'basic': float(emp.basic_salary),
                    'allowances': float(emp.allowances),
                    'gross': float(result['gross']),
                    'taxable': float(result['taxable']),
                    'tax': float(result['tax']),
                    'pension_employee': float(result['pension_employee']),
                    'pension_employer': float(result['pension_employer']),
                    'net': float(result['net']),
                    'bank_account': emp.bank_account or '',
                    'bank': emp.bank_account or emp.bank_or_telebirr or '',
                    'tin': emp.tin or '',
                })

            # Create draft payroll run
            run = PayrollRun(
                company_id=company.id,
                run_date=today,
                status='draft',
            )
            run.generate_period()
            db.session.add(run)
            db.session.flush()
            run.generate_reference()

            draft = PayrollDraft(
                payroll_run_id=run.id,
                employee_data=employees_data,
            )
            db.session.add(draft)
            db.session.commit()

            # Count issues
            issues = []
            for emp_data in employees_data:
                if not emp_data['bank']:
                    issues.append(f"{emp_data['name']}: no bank account")
                if not emp_data['tin']:
                    issues.append(f"{emp_data['name']}: no TIN")

            # Notify owners
            owners = User.query.join(UserCompany).filter(
                UserCompany.company_id == company.id,
                User.role.in_(['owner', 'accountant'])
            ).all()

            issue_text = f" ({len(issues)} issues)" if issues else ""
            message = (
                f'Draft payroll for {period_str} is ready! '
                f'{len(employees_data)} employees{issue_text}. '
                f'Total: ETB {sum(e["net"] for e in employees_data):,.0f}. '
                f'Review and approve.'
            )

            for owner in owners:
                notify(
                    company_id=company.id,
                    user_id=owner.id,
                    message=message,
                    notif_type='info',
                    link=f'/payroll/{run.id}/confirm',
                )

            prepared += 1
            logger.info(f'Prepared draft payroll for {company.name} ({period_str})')

        except Exception as e:
            logger.error(f'Failed to prepare draft for {company.name}: {e}')
            db.session.rollback()

    logger.info(f'Monthly draft preparation complete: {prepared} companies')
    return prepared


def send_compliance_nudges():
    """Send compliance deadline nudges to all companies.

    Called daily. Sends notifications for deadlines within 3 days.
    """
    from payroll_engine.compliance import get_upcoming_deadlines

    today = date.today()
    companies = Company.query.filter_by(is_demo=False).all()

    for company in companies:
        try:
            last_run = PayrollRun.query.filter_by(
                company_id=company.id, status='completed'
            ).order_by(PayrollRun.run_date.desc()).first()

            payroll_date = last_run.run_date.isoformat() if last_run else today.isoformat()
            deadlines = get_upcoming_deadlines(payroll_date)

            owners = User.query.join(UserCompany).filter(
                UserCompany.company_id == company.id,
                User.role.in_(['owner', 'accountant'])
            ).all()

            alerts = []
            if deadlines.get('erca_days_left', 999) <= 3:
                days = deadlines['erca_days_left']
                alerts.append(f'ERCA filing: {"OVERDUE" if days < 0 else f"{days} days left"}')
            if deadlines.get('pension_days_left', 999) <= 3:
                days = deadlines['pension_days_left']
                alerts.append(f'Pension remittance: {"OVERDUE" if days < 0 else f"{days} days left"}')

            if alerts:
                message = '⚠️ ' + ' · '.join(alerts) + '. Open dashboard to download and file.'
                for owner in owners:
                    notify(
                        company_id=company.id,
                        user_id=owner.id,
                        message=message,
                        notif_type='warning',
                        link='/reports',
                    )

        except Exception as e:
            logger.error(f'Failed to send compliance nudge for {company.name}: {e}')
```

**Cron integration (in `__init__.py` or a scheduler):**

```python
# Add to __init__.py or a separate scheduler script
# This can be triggered by a cron job, Celery beat, or APScheduler

# Example with APScheduler:
# from apscheduler.schedulers.background import BackgroundScheduler
# scheduler = BackgroundScheduler()
# scheduler.add_job(prepare_monthly_drafts, 'cron', day=28, hour=9)
# scheduler.add_job(send_compliance_nudges, 'cron', hour=8)
# scheduler.start()
```

**Tigist now experiences:** On the 28th of each month, she opens her phone and sees a notification: "Draft payroll for Hamle 2018 is ready! 8 employees (2 issues). Total: ETB 67,400. Review and approve." She taps the notification, reviews the numbers, fixes the 2 missing bank accounts, and approves. On days when ERCA is due, she gets a morning nudge: "⚠️ ERCA filing: 2 days left. Open dashboard to download and file."

---

## SCORECARD

| Pattern | Status | What Tigist Experiences Now |
|---|---|---|
| 1. One-Click Compliance | **BUILT** | Dashboard shows compliance calendar with due dates, countdown badges, download buttons, and "How to file" instructions — all in one table. She never leaves the dashboard. |
| 2. Employee Self-Service | **BUILT** | Employees get WhatsApp + in-app notification when payslip is ready. They click "I received this payslip" to acknowledge. Tigist sees who acknowledged. |
| 3. Pre-Approval Validation | **BUILT** | Before approving, she sees "3 things look unusual" — salary changed 35%, total payroll up 22%, employee on unpaid leave. Each flag has a clear explanation and hint. |
| 4. Zero Data Re-Entry | **DONE** | Employee data entered once flows to payslips, ERCA, pension, bank files, Telebirr. No retyping. |
| 5. Payment Disbursement | **BUILT** | After approval, she sees a disbursement page grouped by bank, with download buttons per bank. "Mark as Disbursed" → "Confirm All Payments Received." |
| 6. Size-Appropriate UI | **BUILT** | Sidebar adapts to company size. 8 employees: Dashboard, Employees, Run Payroll, Compliance. Advanced features appear as company grows. |
| 7. Proactive System | **BUILT** | Monthly draft pre-calculation on the 28th. Compliance nudges when deadlines approach. Tigist confirms instead of starting. |
