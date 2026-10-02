# Audit Logging — Priority #7 (High-Risk Fields First)

Covers: employee edits (especially salary), company settings changes, tax rule
changes, and login/logout + failed logins. Built to reuse your existing
`AuditLog` model and hash chain — same pattern already proven in
`payroll_service.py:create_audit_log` for payroll approval.

If your actual helper signature differs, adjust the calls below to match —
the important part is the *shape* of what gets logged, not the exact function name.

---

## 1. Generic audit helper (add to `models.py` or a new `audit.py` if not already centralized)

```python
def log_audit_event(user_id, action, details=None, ip_address=None):
    """
    Central audit logging call. Reuses the existing AuditLog hash-chain model.
    `details` should be a dict — will be stored as JSON with before/after where relevant.
    """
    from .models import AuditLog, db

    last_entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    previous_hash = last_entry.hash if last_entry else None

    entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
        previous_hash=previous_hash,
    )
    entry.hash = entry.compute_hash()  # existing method per the diagnostic report
    db.session.add(entry)
    # NOTE: do not commit here — let it ride in the same transaction as the
    # actual change, so a failed save never produces an orphaned audit log.
    return entry
```

## 2. Employee edit — salary changes especially

In `employees_bp.py`, wherever the edit route commits changes:

```python
@employees_bp.route('/employees/<int:employee_id>/edit', methods=['POST'])
@login_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    # Capture before-state for the fields that matter most
    before = {
        'salary': str(employee.salary),
        'department': employee.department,
        'bank_account': '[redacted]',  # never log actual bank account numbers
        'status': employee.status,
    }

    # ... existing form handling / field updates ...
    employee.salary = new_salary
    employee.department = new_department
    # etc.

    after = {
        'salary': str(employee.salary),
        'department': employee.department,
        'bank_account': '[redacted]',
        'status': employee.status,
    }

    changed_fields = {k: {'before': before[k], 'after': after[k]}
                       for k in before if before[k] != after[k]}

    if changed_fields:
        log_audit_event(
            user_id=current_user.id,
            action='employee_edit',
            details={'employee_id': employee_id, 'changes': changed_fields},
            ip_address=request.remote_addr,
        )

    db.session.commit()
    return redirect(url_for('employees.view_employee', employee_id=employee_id))
```

**Key decisions baked in here:**
- Only logs an entry if something actually changed (no noise from no-op saves).
- Salary is logged as before/after, not just "salary changed" — this is the field most likely to be disputed later.
- Bank account is explicitly redacted — audit logs shouldn't become a second place sensitive data leaks from.
- Audit write and the actual DB change share one `db.session.commit()` — so you never get an audit entry for a change that didn't actually save (or vice versa).

## 3. Company settings change

Same pattern in `settings_bp.py`:

```python
@settings_bp.route('/settings/company', methods=['POST'])
@login_required
@require_role('owner')  # adjust to your actual decorator
def update_company_settings():
    company = current_user.company

    before = {'name': company.name, 'tin': company.tin, 'webhook_secret': '[redacted]'}
    # ... apply form updates to company ...
    after = {'name': company.name, 'tin': company.tin, 'webhook_secret': '[redacted]'}

    changed = {k: {'before': before[k], 'after': after[k]} for k in before if before[k] != after[k]}
    if changed:
        log_audit_event(
            user_id=current_user.id,
            action='company_settings_change',
            details={'changes': changed},
            ip_address=request.remote_addr,
        )

    db.session.commit()
    return redirect(url_for('settings.company_profile'))
```

## 4. Tax rule changes

Wherever `TaxRule` records are created/activated (likely `settings_bp.py` or an admin route):

```python
log_audit_event(
    user_id=current_user.id,
    action='tax_rule_change',
    details={
        'tax_rule_id': new_rule.id,
        'version_name': new_rule.version_name,
        'effective_date': str(new_rule.effective_date),
        'status': new_rule.status,
    },
    ip_address=request.remote_addr,
)
```

This one matters most — it's the direct fix for the root-cause gap called out in section 6 of the diagnostic (the pension ceiling error): every future rule change now has a named person and timestamp attached, not just a silent DB write.

## 5. Login / logout / failed login

In `auth.py`:

```python
@auth_bp.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(email=request.form['email']).first()

    if user and user.check_password(request.form['password']):
        login_user(user)
        log_audit_event(
            user_id=user.id,
            action='login_success',
            ip_address=request.remote_addr,
        )
        db.session.commit()
        return redirect(url_for('dashboard.index'))

    # Failed login — log even though we don't have a user_id in some cases
    log_audit_event(
        user_id=user.id if user else None,
        action='login_failed',
        details={'attempted_email': request.form.get('email', '')[:120]},
        ip_address=request.remote_addr,
    )
    db.session.commit()
    flash('Invalid credentials')
    return redirect(url_for('auth.login'))
```

```python
@auth_bp.route('/logout')
@login_required
def logout():
    log_audit_event(user_id=current_user.id, action='logout', ip_address=request.remote_addr)
    db.session.commit()
    logout_user()
    return redirect(url_for('auth.login'))
```

This directly closes two gaps the diagnostic flagged: no audit of failed logins, no way to detect brute-force patterns after the fact.

---

## What this deliberately leaves out (next tier, not today)

- Leave approval/rejection, overtime entry, deduction/allowance changes — lower financial risk than salary edits, do these once the high-risk set is proven in production.
- Password change / MFA enable-disable — security-relevant but lower urgency than login tracking.
- `session_id` and `user_agent` on audit entries — nice-to-have for forensics, not blocking.

## Test checklist before calling this done

- [ ] Edit an employee's salary → confirm one audit entry with correct before/after, hash chain still verifies (`AuditLog.verify_chain()`)
- [ ] Edit something unrelated (e.g. just resaving the form with no changes) → confirm NO audit entry is created
- [ ] Change a company setting → entry logged, secrets redacted
- [ ] Create/activate a new tax rule → entry logged with version and effective date
- [ ] Successful login → entry logged
- [ ] Failed login (wrong password) → entry logged, no user_id leak beyond what's expected
- [ ] Logout → entry logged
- [ ] Run `AuditLog.verify_chain()` after all the above — chain must still be intact
