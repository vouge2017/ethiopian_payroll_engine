# Developer Playbook
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** How to add, modify, and extend the system
**Audience:** New engineers, contributors

---

## How to Use This Document

Every "how to" question should be answered here. If you're adding something new, follow the relevant guide. If the guide doesn't cover your case, update it.

---

## How to Add a New Business Rule

1. **Define the rule** in `BUSINESS_RULE_CATALOGUE.md`
   - Use format: `BR-{PRD}-{seq}` (e.g., BR-02-13 for PRD-02, rule #13)
   - Include: rule text, source (law/convention), PRD reference

2. **Add to the relevant PRD** (section 10: Business Rules)
   - Reference the catalogue ID

3. **Implement in code**
   - If configurable: add to `TaxRule.rules_json` or `SystemSetting`
   - If hardcoded: add constant to relevant module

4. **Add validation** if needed
   - Define in `VALIDATION_CATALOGUE.md` (VL-{PRD}-{seq})
   - Add to PRD section 11

5. **Add test**
   - Test the rule in isolation
   - Test the rule in the payroll flow

6. **Add evidence** if it affects calculations
   - Define in `EVIDENCE_CATALOGUE.md` (EV-{seq})

---

## How to Add a New Validation Rule

1. **Define in** `VALIDATION_CATALOGUE.md`
   - ID: `VL-{PRD}-{seq}`
   - Rule, severity (BLOCK/FLAG/WARN), when it runs

2. **Add to PRD** section 11 (Validation Rules)

3. **Implement in code**
   - Add to `validation.py` or the relevant module
   - Return `PayrollValidationResult` with rule_code, severity, message

4. **Add test**
   - Test with valid data (should pass)
   - Test with invalid data (should block/warn)

---

## How to Add a New API Endpoint

1. **Define in** `API_CATALOGUE.md`
   - Method, path, description, auth, PRD reference

2. **Add to PRD** section 14 (API Contracts)
   - Request/response format, error codes

3. **Implement in code**
   - Add route to the relevant blueprint (`employees_bp.py`, `payroll_bp.py`, etc.)
   - Use `@login_required` and `@role_required` decorators
   - Use `TenantQuery` for all database queries
   - Return consistent error format: `{"error": "code", "message": "..."}`

4. **Add to** `ERROR_CATALOGUE.md`
   - Document any new error codes

5. **Add test**
   - Test with valid auth
   - Test with invalid auth
   - Test with missing data
   - Test tenant isolation

---

## How to Add a New State Machine

1. **Define in** `STATE_MACHINE_CATALOGUE.md`
   - ID: `SM-{seq}`
   - States, transitions, forbidden transitions, fields per state

2. **Add to PRD** section 13 (State Machine)

3. **Implement in code**
   - Add status field to model (if new entity)
   - Add transition validation (check current status before allowing change)
   - Add audit log entry on every transition

4. **Add test**
   - Test each valid transition
   - Test each forbidden transition (should reject)
   - Test concurrent transitions (race condition)

---

## How to Add a New Notification

1. **Define in** `NOTIFICATION_CATALOGUE.md`
   - ID: `N-{seq}` (main catalogue) or `N-{PRD}-{seq}` (PRD-specific)
   - Trigger, recipient, priority, channel, message template

2. **Add to PRD** section 16 (Notifications)

3. **Implement in code**
   - Use `create_notification()` from `shared.py`
   - Include link to relevant page

4. **Add test**
   - Test notification is created on trigger
   - Test notification is sent to correct recipient

---

## How to Add a New Analytics Event

1. **Define in** `ANALYTICS_CATALOGUE.md`
   - ID: `AE-{seq}` (main) or `PA-{seq}` (payment-specific)
   - Event name, trigger, key properties

2. **Add to PRD** section 25 (Analytics Events)

3. **Implement in code**
   - Track event at the relevant point in the code
   - Include: company_id, timestamp, relevant properties

---

## How to Add a New Audit Event

1. **Define in PRD** section 26 (Audit Events)
   - Event name, actor, data recorded

2. **Implement in code**
   - Use `create_audit_log()` from `shared.py`
   - Include: company_id, user_id, action, details (JSON)
   - Hash chain is computed automatically (before_insert event)

3. **Add test**
   - Test audit entry is created
   - Test hash chain is intact after entry

---

## How to Add a New Evidence Definition

1. **Define in** `EVIDENCE_CATALOGUE.md`
   - ID: `EV-{seq}`
   - Source, formula, inputs, output, law, timestamp, approver

2. **Add to PRD** section 18 (Evidence Requirements)

3. **Implement in code**
   - Include evidence in payslip PDF generation
   - Include in audit package generation

---

## How to Add a New Database Migration

1. **Create migration**
   ```bash
   flask db migrate -m "description of change"
   ```

2. **Review the generated migration**
   - Check it handles existing data
   - Check it has proper downgrade

3. **Test migration**
   ```bash
   flask db upgrade
   flask db downgrade
   flask db upgrade
   ```

4. **Update** `DATA_MODEL.md`
   - Add new columns/tables

---

## How to Add a New Configuration Setting

1. **Define in** `CONFIGURATION_CATALOGUE.md`
   - Category, key, default, allowed values, editable by, audit required

2. **Add to PRD** (if applicable)

3. **Implement in code**
   - Add to `SystemSetting` (system-wide) or `Company.settings` (per-company)
   - Add to `TaxRule.rules_json` (if payroll-related)

4. **Add validation**
   - Validate allowed values on save

5. **Add audit log**
   - Log changes to settings

---

## How to Add a New Report

1. **Define in** `API_CATALOGUE.md`
   - GET endpoint for report

2. **Add to PRD** section 8 (Screen Specifications)

3. **Implement in code**
   - Add to `reports.py` or create new module
   - Use configurable template (report_templates.py)
   - Generate as Excel (.xlsx) or PDF

4. **Add test**
   - Test report generation
   - Test report content matches expected values

---

## How to Add a New Leave Type

1. **Define in** `BUSINESS_RULE_CATALOGUE.md`
   - BR-LVE-{seq}: leave type, days, pay percentage

2. **Add to PRD-02** (Leave section)

3. **Implement in code**
   - Add to `leave.py`
   - Add balance tracking
   - Add payroll integration (paid/unpaid)

4. **Add validation**
   - Balance check before approval

5. **Add test**
   - Test accrual
   - Test usage
   - Test payroll impact

---

## How to Add a New Payment Method

1. **Define in** `PAYMENT_CATALOGUE.md`
   - PM-001-{code}: method, description, file format

2. **Add to PRD-04** (Payment Methods section)

3. **Implement in code**
   - Add to `bank_file.py` (if bank-based)
   - Add format validation
   - Add file generation

4. **Add test**
   - Test validation
   - Test file generation

---

## How to Write Tests

### Unit Tests
```python
def test_tax_calculation():
    """Test tax bracket calculation."""
    result = calculate_tax(13950)  # ETB 13,950 taxable
    assert result == 2685  # Expected tax after relief
```

### Integration Tests
```python
def test_payroll_flow(app):
    """Test complete payroll flow."""
    with app.app_context():
        # Create company, employees, payroll
        # Calculate, approve, lock
        # Verify all values
```

### E2E Tests
```python
def test_full_payroll_cycle(app, client):
    """Test from import to payslip generation."""
    # Import employees
    # Create payroll
    # Approve
    # Generate payslips
    # Verify PDFs exist
```

---

## How to Update Documentation

1. **PRDs** — update the relevant section in the PRD
2. **Catalogues** — update the canonical catalogue (Business Rule, Validation, etc.)
3. **ADRs** — add new ADR if architectural decision changed
4. **Operating Manual** — update if the change affects the document map
5. **Traceability Matrix** — add new trace if new feature

---

*Developer Playbook v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
