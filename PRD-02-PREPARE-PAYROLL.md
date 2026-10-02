# PRD-02: Prepare Monthly Payroll
**Journey:** 2 — Prepare Monthly Payroll
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md

---

## 1. Vision

Every Ethiopian business runs payroll correctly, on time, with zero manual calculations — and can explain every number to any authority.

## 2. Customer Problem

Ethiopian SMEs spend 6-10 hours per month preparing payroll in Excel. The process involves: collecting attendance from biometric devices, manually calculating overtime, checking leave records, applying deductions, calculating tax (often with outdated brackets), calculating pension (often on the wrong base), and cross-checking totals. Errors are discovered only on payday. The entire process is repeated from scratch every month.

## 3. Business Objective

Reduce payroll preparation from 6-10 hours to 15 minutes for a 50-employee company. Eliminate manual calculations. Catch errors before the payroll draft is shown. Enable the payroll officer to explain any variance to the owner without opening a spreadsheet.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Payroll Officer** | Imports attendance, reviews draft, runs validation, generates outputs | Monthly |
| **Supporting: HR** | Confirms leave records, flags discrepancies | Monthly |
| **Supporting: Department Manager** | Approves overtime entries for their team | Monthly |
| **Supporting: Finance Officer** | Reviews deduction accuracy | Monthly |
| **Supporting: Accountant** | Reviews draft, verifies crosscheck results | Monthly |
| **Handoff: Business Owner** | Receives draft for approval (Journey 3) | Monthly |
| **Waiting: System** | Auto-matches attendance, calculates payroll, runs crosschecks | During generation |
| **Waiting: Employees** | Receive payslips after approval (Journey 6) | Monthly |

## 5. Entry Criteria

- Company exists and is active (Journey 0 complete)
- At least one active employee exists
- TaxRule records exist (seeded via `seed_tax_rules.py`)
- Current month's attendance data is available (biometric export or manual entry)
- Leave records for current month are finalized

## 6. Exit Criteria

- PayrollRun status is `review` (ready for owner approval)
- All validation BLOCKs resolved (or overridden with reason)
- All validation WARNINGs acknowledged
- Month-over-month comparison available
- Crosscheck results available
- Draft summary available for owner review

## 7. User Journey

### Main Flow

```
Payroll Officer opens Payroll → "Prepare [Month] Payroll"
    ↓
System checks preconditions:
  ✓ Active employees exist
  ✓ TaxRule records exist
  ✓ Attendance data available (or skip with warning)
    ↓
System shows: "Import attendance or proceed without?"
    ↓
Payroll Officer uploads attendance CSV
    ↓
System auto-matches employees by name/ID
  → Shows: "48/50 matched. 2 unmatched rows."
  → Payroll Officer resolves mismatches
    ↓
System runs pre-processing validation:
  ✓ All employees have valid TINs
  ✓ All employees have valid bank accounts
  ✓ No duplicate employees
  ✓ Attendance data complete (or flagged)
  ✓ Leave records finalized
  ✓ Salary changes since last run (flagged)
  ✓ Deduction balances current
    ↓
System calculates payroll for all employees:
  For each employee:
    gross = basic_salary + allowances
    pension = basic_salary × 7%
    taxable = gross - pension
    tax = progressive_brackets(taxable) - personal_relief
    deductions = loans + cost_sharing + ...
    net = gross - pension - tax - deductions
    ↓
System runs crosschecks:
  ✓ Attendance total vs payroll (employees matched)
  ✓ ERCA tax total vs payroll tax total
  ✓ Pension total vs payroll pension total
  ✓ Bank file net total vs payroll net total
    ↓
System generates draft:
  ✓ PayrollRun created (status: review)
  ✓ Payslips created for all employees
  ✓ Month-over-month comparison generated
  ✓ Validation results stored
    ↓
Payroll Officer reviews draft summary
    ↓
System shows: "Payroll ready for owner approval"
  → Notifies owner (Journey 3)
```

### Alternative Flows

**A1: No attendance data**
1. Payroll Officer selects "Proceed without attendance"
2. System calculates based on full-month salaries (no absence deduction)
3. System shows warning: "No attendance imported — all employees assumed present"
4. Payroll Officer acknowledges

**A2: Attendance mismatch**
1. System shows unmatched rows: "Row 15: 'Kebede A' — no matching employee found"
2. Payroll Officer can: map to existing employee, skip row, or create new employee
3. System re-matches after resolution

**A3: Validation BLOCK found**
1. System prevents draft generation
2. Shows: "BLOCK: Employee #37 has no bank account. Fix before proceeding."
3. Payroll Officer fixes in employee record
4. System re-validates

**A4: Validation FLAG found**
1. System allows draft generation with warnings
2. Shows: "FLAG: Employee #37 salary increased 45% (ETB 8,000 → ETB 12,000). Acknowledge?"
3. Payroll Officer acknowledges with reason: "Promotion approved by owner on 2026-07-15"
4. System records acknowledgment in audit trail

**A5: Correction run (re-calculation)**
1. Payroll Officer modifies an employee's data (e.g., forgot overtime)
2. System shows: "Re-calculate payroll? This will replace the current draft."
3. Payroll Officer confirms
4. System re-runs calculation, updates draft

## 8. Screen Specifications

### Screen: Prepare Payroll

```
Screen: Prepare Payroll
URL: /payroll/new
Purpose: Configure and generate monthly payroll draft
Auth: Owner, Admin, Payroll Officer

Layout:
  Header: "Prepare [Month] Payroll" + period selector
  Sidebar: Steps (1. Attendance → 2. Validation → 3. Calculate → 4. Review)
  Main Content: Current step content
  Footer: Back / Next / Cancel buttons

States:
  Empty: "No active employees. Add employees first."
  Loading: Progress bar with step labels
  Error: Validation errors with fix instructions
  Success: Draft summary with comparison

Actions:
  Primary: "Generate Draft" (only if no BLOCKs)
  Secondary: "Import Attendance", "Run Validation", "Re-calculate"
  Destructive: "Cancel Payroll" (with confirmation)
```

### Screen: Attendance Import

```
Screen: Import Attendance
URL: /payroll/attendance/import
Purpose: Upload biometric device CSV and match to employees
Auth: Owner, Admin, Payroll Officer

Layout:
  Header: "Import Attendance — [Month]"
  Main:
    Upload zone (drag & drop)
    Recent imports list
    Import history

  After upload:
    Mapping preview (system matched columns)
    Unmatched rows (red, require resolution)
    Match summary: "48/50 matched"

States:
  Empty: "No attendance imported yet. Upload CSV from biometric device."
  Uploading: Progress bar
  Processing: Spinner + "Matching employees..."
  Complete: Summary with match count
  Error: Unmatched rows with fix options

Actions:
  Primary: "Confirm Import"
  Secondary: "Download Template", "Skip Attendance"
  Destructive: "Clear Import"
```

### Screen: Validation Summary

```
Screen: Validation Results
URL: /payroll/validation
Purpose: Show all pre-processing validation results
Auth: Owner, Admin, Payroll Officer

Layout:
  Header: "Validation Results"
  Main:
    Summary bar: "47 passed, 2 warnings, 1 block"
    BLOCK section (red) — must fix
    FLAG section (yellow) — can override
    WARN section (blue) — informational

States:
  Empty: "No validation issues found. ✓ Ready to calculate."
  Loading: Spinner + "Running validation..."
  All pass: Green checkmark + "All checks passed"
  Has blocks: Red banner + fix instructions

Actions:
  Primary: "Fix Issues" (links to fix location)
  Secondary: "Override" (requires reason), "Acknowledge"
  Destructive: None
```

### Screen: Payroll Draft Review

```
Screen: Payroll Draft
URL: /payroll/{id}/review
Purpose: Review calculated payroll before owner approval
Auth: Owner, Admin, Payroll Officer, Accountant

Layout:
  Header: "Payroll Draft — [Month] PR-2018-10-001"
  Main:
    Summary card: employees, gross, tax, pension, net
    Month-over-month comparison card
    Crosscheck results card
    Employee list (sortable, filterable)
    Validation warnings (if any)

States:
  Empty: "No payroll draft. Generate one first."
  Loading: Skeleton screens
  Ready: Full summary with all data
  Has warnings: Yellow banner + acknowledgment required

Actions:
  Primary: "Submit for Approval" (sends to owner)
  Secondary: "Re-calculate", "Export Summary", "View Employee Details"
  Destructive: "Delete Draft"
```

### Screen: Employee Payroll Detail

```
Screen: Employee Payroll Detail
URL: /payroll/{id}/employee/{emp_id}
Purpose: Show full calculation breakdown for one employee
Auth: Owner, Admin, Payroll Officer, Accountant

Layout:
  Header: "Payroll — [Employee Name]"
  Main:
    Salary breakdown (basic, allowances, gross)
    Pension calculation (7% of basic, with formula)
    Tax calculation (bracket-by-bracket, with law citation)
    Deductions (loan, cost-sharing, with balances)
    Net pay
    Comparison with last month
    Evidence panel (ⓘ on each line)

States:
  Loading: Skeleton
  Ready: Full breakdown
  Adjusted: Shows adjustment reason and original values

Actions:
  Primary: None (read-only)
  Secondary: "View Evidence", "Compare with Last Month"
  Destructive: None
```

## 9. Component Specifications

### AttendanceUpload
```
Properties:
  accept: '.csv,.xlsx'
  maxSize: 10MB
  month: string (period)

States:
  empty → dragover → uploading → matching → complete → error

Events:
  onUpload(file)
  onMatch(results) → {matched: 48, unmatched: 2, rows: [...]}
  onError(message)
```

### ValidationSummary
```
Properties:
  results: array of {rule, severity, message, employee?, fix?}
  counts: {block, flag, warn}

Display:
  Block: red card, must fix before proceeding
  Flag: yellow card, can override with reason
  Warn: blue card, informational

Events:
  onFix(rule) → navigates to fix location
  onOverride(rule, reason) → records override
  onAcknowledge(rule) → marks as acknowledged
```

### PayrollSummaryCard
```
Properties:
  employees: number
  gross: Decimal
  tax: Decimal
  pension: Decimal
  net: Decimal
  comparison: {gross_change, tax_change, net_change, headcount_change}

Display:
  Large numbers with commas
  Change indicators (green/red arrows)
  Click any number → ExplainPanel

Events:
  onDrillDown(field) → opens ExplainPanel
```

### MonthComparisonCard
```
Properties:
  current: {employees, gross, tax, pension, net}
  previous: {employees, gross, tax, pension, net}
  changes: array of {employee, field, old, new, reason}

Display:
  Side-by-side totals
  Top 3 changes sorted by impact
  "Why did payroll change?" summary

Events:
  onViewDetails() → full comparison view
```

### CrosscheckResults
```
Properties:
  checks: array of {name, status, expected, actual, difference}

Display:
  Green checkmark for PASS
  Red X for BLOCK
  Yellow warning for WARNING
  Each check expandable for details

Events:
  onDrillDown(check) → shows evidence
```

## 10. Business Rules

| Rule | Source | Enforcement |
|------|--------|-------------|
| Tax brackets from current TaxRule | Proclamation 1395/2025 | System loads active version |
| Pension 7% of basic salary | Proclamation 1268/2022 | Calculated per employee |
| Pension employer 11% of basic | Proclamation 1268/2022 | Recorded, not deducted |
| Personal relief ETB 150/month | Proclamation 1395/2025 | Deducted from gross tax |
| Overtime rates: 1.25×/1.5×/2×/2.5× | Proclamation 1156/2019, Art. 68 | Applied per overtime type |
| Overtime monthly limit: 20 hours | Proclamation 1156/2019, Art. 89 | FLAG if exceeded |
| Leave deduction: daily rate × unpaid days | Business logic | Applied for unpaid leave |
| Loan deduction: from EmployeeDeduction balance | Business logic | Auto-applied, balance tracked |
| Salary rounding: 2 decimal places, HALF_UP | Business precision | `Decimal('0.01')` quantize |
| Payroll period: Ethiopian calendar month | System | Auto-generated from run date |

## 11. Validation Rules

| Check | Severity | Behavior |
|-------|----------|----------|
| Empty employee list | BLOCK | Cannot generate draft |
| Missing TIN (active employee) | BLOCK | Cannot generate draft |
| Missing bank account (active employee) | BLOCK | Cannot generate draft |
| Negative net pay | BLOCK | Cannot generate draft |
| Duplicate employee (name + bank) | BLOCK | Cannot generate draft |
| Salary > 500,000 ETB | FLAG | Generate with warning, require acknowledgment |
| Salary changed > 30% from last month | FLAG | Generate with warning, require acknowledgment |
| Payroll total changed > 20% from last month | FLAG | Generate with warning, require acknowledgment |
| Overtime > 20 hours this month | FLAG | Generate with warning |
| Employee on unpaid leave with full salary | FLAG | Generate with warning |
| Pension doesn't match 7% of basic | FLAG | Generate with warning |
| Tax doesn't match bracket calculation | FLAG | Generate with warning |
| Missing attendance data | WARN | Generate, show in summary |
| Missing department | WARN | Generate, show in summary |

## 12. Permissions

| Action | Owner | Admin | Manager | Employee | Accountant |
|--------|-------|-------|---------|----------|------------|
| Import attendance | ✅ | ✅ | ❌ | ❌ | ❌ |
| Run validation | ✅ | ✅ | ❌ | ❌ | ❌ |
| Generate draft | ✅ | ✅ | ❌ | ❌ | ❌ |
| View draft summary | ✅ | ✅ | ❌ | ❌ | ✅ |
| View employee detail | ✅ | ✅ | ❌ | ❌ | ✅ |
| Re-calculate | ✅ | ✅ | ❌ | ❌ | ❌ |
| Submit for approval | ✅ | ✅ | ❌ | ❌ | ❌ |
| Override validation FLAG | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete draft | ✅ | ✅ | ❌ | ❌ | ❌ |
| Approve overtime | ✅ | ✅ | ✅ (own dept) | ❌ | ❌ |

## 13. State Machine

### PayrollRun Lifecycle

```
draft
  ↓ (generate)
review
  ↓ (submit for approval)
pending_approval
  ↓ (owner approves)
processing
  ↓ (all outputs generated)
completed
  ↓ (lock)
locked
```

### Error States

```
processing → failed (if calculation error)
  ↓ (fix and retry)
processing → completed
```

### Forbidden Transitions

- `locked` → any (immutable)
- `completed` → `draft` (must create correction run)
- `review` → `locked` (must go through approval)

### Allowed Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| draft | review | Generate draft | Payroll Officer |
| review | pending_approval | Submit for approval | Payroll Officer |
| pending_approval | processing | Approve | Owner |
| processing | completed | All outputs generated | System |
| processing | failed | Calculation error | System |
| completed | locked | Lock | Owner |
| failed | processing | Retry | Payroll Officer |

## 14. API Contracts

### POST /payroll-runs
Create a new payroll draft.

**Request:**
```json
{
  "period": "2018-10",
  "source": "manual"
}
```

**Response (201):**
```json
{
  "data": {
    "id": 42,
    "reference": "PR-2018-10-042",
    "period": "2018-10",
    "status": "draft",
    "employee_count": 50,
    "created_at": "2026-07-28T10:00:00Z"
  }
}
```

### POST /payroll-runs/{id}/attendance
Import attendance data.

**Request:** Multipart form with CSV file

**Response (200):**
```json
{
  "data": {
    "matched": 48,
    "unmatched": 2,
    "unmatched_rows": [
      {"row": 15, "name": "Kebede A", "reason": "No matching employee"},
      {"row": 33, "name": "Unknown", "reason": "Empty name"}
    ]
  }
}
```

### POST /payroll-runs/{id}/validate
Run pre-processing validation.

**Response (200):**
```json
{
  "data": {
    "block_count": 0,
    "flag_count": 2,
    "warn_count": 1,
    "results": [
      {
        "rule": "SALARY_CHANGE_30PCT",
        "severity": "flag",
        "employee_id": 37,
        "employee_name": "Kebede Alemu",
        "message": "Salary increased 45% (ETB 8,000 → ETB 12,000)",
        "fix": "Verify promotion was approved"
      }
    ]
  }
}
```

### POST /payroll-runs/{id}/calculate
Generate payroll draft.

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "status": "review",
    "employee_count": 50,
    "gross": "2145330.00",
    "tax": "412650.00",
    "pension_employee": "148173.00",
    "pension_employer": "231231.00",
    "net": "1584507.00",
    "comparison": {
      "gross_change": "3.2%",
      "net_change": "2.8%",
      "headcount_change": 2,
      "top_changes": [
        {"employee": "Kebede Alemu", "field": "salary", "old": "8000", "new": "12000", "reason": "Promotion"}
      ]
    },
    "crosschecks": [
      {"name": "attendance_vs_payroll", "status": "pass", "expected": 50, "actual": 50},
      {"name": "erca_totals", "status": "pass", "expected": "412650.00", "actual": "412650.00"},
      {"name": "pension_totals", "status": "pass", "expected": "148173.00", "actual": "148173.00"},
      {"name": "bank_file_total", "status": "pass", "expected": "1584507.00", "actual": "1584507.00"}
    ]
  }
}
```

### GET /payroll-runs/{id}
Get payroll draft details.

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "reference": "PR-2018-10-042",
    "period": "2018-10",
    "status": "review",
    "employee_count": 50,
    "gross": "2145330.00",
    "tax": "412650.00",
    "net": "1584507.00",
    "created_at": "2026-07-28T10:00:00Z"
  }
}
```

### GET /payroll-runs/{id}/employees
Get per-employee payroll details.

**Response (200):**
```json
{
  "data": [
    {
      "employee_id": 1,
      "employee_code": "EMP001",
      "name": "Abebe Kebede",
      "gross": "15000.00",
      "pension": "1050.00",
      "taxable": "13950.00",
      "tax": "2685.00",
      "deductions": "2000.00",
      "net": "11265.00"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 50}
}
```

### POST /payroll-runs/{id}/submit
Submit draft for owner approval.

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "status": "pending_approval",
    "submitted_at": "2026-07-28T10:30:00Z"
  }
}
```

## 15. Data Model Changes

### Tables Created
- `PayrollRun` — payroll draft (see DATA_MODEL.md)
- `Payslip` — per-employee calculation (see DATA_MODEL.md)
- `PayrollValidationResult` — validation findings (see DATA_MODEL.md)

### Tables Modified
- `Attendance` — linked to payroll run via period matching
- `OvertimeEntry` — linked to payroll run via period matching
- `Leave` — applied to payroll calculation

### Indexes
- `ix_payrollrun_company_status` (existing)
- `ix_payslip_run_employee` (existing)

### Audit Events
- `payroll.created` — new draft created
- `payroll.attendance_imported` — attendance data imported
- `payroll.validated` — validation run completed
- `payroll.calculated` — draft generated
- `payroll.submitted` — submitted for approval
- `payroll.deleted` — draft deleted

## 16. Notifications

| Event | Recipient | Channel | Message |
|-------|-----------|---------|---------|
| Draft generated | Payroll Officer | In-app | "Payroll draft PR-2018-10-042 ready for review. 50 employees, ETB 1,584,507 net." |
| Draft generated | Owner | In-app | "Payroll draft ready for your approval. ETB 1,584,507 for 50 employees." |
| Validation BLOCK | Payroll Officer | In-app | "Payroll has 1 blocking issue. Fix before proceeding." |
| Validation FLAG | Payroll Officer | In-app | "Payroll has 2 warnings. Review and acknowledge." |
| Comparison alert | Payroll Officer | In-app | "Payroll changed +3.2% vs last month. Review drivers." |
| Attendance imported | Payroll Officer | In-app | "Attendance imported: 48/50 matched. 2 need resolution." |

## 17. Automation Rules

| Event | Automatic Action |
|-------|-----------------|
| 25th of month | Notify payroll officer: "Payroll period ending in 5 days. Import attendance?" |
| Attendance imported | Auto-match employees by name/ID, flag mismatches |
| Missing attendance (3+ days) | Alert: "Employee [name] has no attendance for [days] days" |
| Validation run complete | Auto-notify payroll officer with summary |
| Validation BLOCK found | Prevent draft generation, show fix instructions |
| Validation FLAG found | Allow draft, require acknowledgment before submission |
| Draft generated | Auto-compare with last month, flag >20% variance |
| Draft generated | Auto-run crosschecks |
| Draft ready | Notify owner for approval |
| Approval delayed >2 days | Escalation: "Payroll still not approved. Employees expect payment [date]." |
| Post-calculation | Freeze calculation snapshot on each Payslip |

## 18. Evidence Requirements

| Data Point | Evidence |
|-----------|----------|
| Tax calculation | Bracket-by-bracket breakdown with Proclamation 1395/2025, Art. 36(1) |
| Pension calculation | Rate (7%) × base (basic_salary) with Proclamation 1268/2022 |
| Overtime calculation | Hours × hourly_rate × multiplier with type and date |
| Leave deduction | Days × daily_rate with leave request reference |
| Loan deduction | Amount from EmployeeDeduction with remaining balance |
| Crosscheck: attendance | Expected count vs actual count |
| Crosscheck: ERCA | Sum of tax from payslips vs ERCA report total |
| Crosscheck: pension | Sum of pension from payslips vs pension report total |
| Crosscheck: bank file | Sum of net from payslips vs bank file total |

## 19. Trust Moments

| Moment | What Happens | What Customer Thinks |
|--------|-------------|---------------------|
| Validation summary | "47 passed, 2 warnings, 1 block" | "The system caught errors I would have missed" |
| Crosscheck results | "✓ All 4 crosschecks passed" | "Every number is verified against another source" |
| Month comparison | "Payroll +3.2%, mainly +2 new hires" | "I can explain this to the owner without Excel" |
| Draft ready | "50 employees, ETB 1,584,507. Ready for approval." | "15 minutes instead of 6 hours" |
| Tax breakdown | Bracket-by-bracket with law citation | "I can defend this to ERCA" |

## 20. Error Handling

| Error | Handling |
|-------|----------|
| Attendance CSV malformed | Show error: "File format not recognized. Download template." |
| Employee not found in attendance | Show unmatched rows, allow manual mapping |
| Calculation error (division by zero) | Log error, show generic message, alert engineering |
| Database timeout during calculation | Retry once, then show error: "Payroll generation took too long. Try with fewer employees or contact support." |
| Concurrent modification | Show error: "Payroll was modified by another user. Refresh and try again." |
| Missing TaxRule | Show error: "Tax rules not configured. Contact support." |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| 0 employees active | Show: "No active employees. Add employees first." |
| 1 employee | Allow — single-employee payroll |
| 1000+ employees | Background processing with progress bar |
| Employee terminated mid-month | Pro-rate salary to termination date |
| Employee hired mid-month | Pro-rate salary from start date |
| Employee on full-month unpaid leave | Zero gross, zero tax, zero net |
| Employee with multiple overtime types | Sum each type separately, apply different rates |
| Negative allowances (deductions from gross) | Treat as deduction, not allowance |
| Same employee in multiple departments | Not allowed — one department per employee |
| Payroll for previous month (backfill) | Allow, use historical TaxRule version |
| Ethiopian month boundary (different from Gregorian) | Use Ethiopian calendar for period |

## 22. Security

- Attendance data contains employee names → treat as PII (redact in logs)
- Salary data is confidential → AES encryption at rest
- Payroll totals are confidential → restrict to authorized roles
- Validation overrides require reason → audit trail
- Calculation snapshot frozen at generation → tamper-evident

## 23. Performance

| Operation | Target | Max |
|-----------|--------|-----|
| Attendance import (50 employees) | < 5s | 15s |
| Attendance import (500 employees) | < 15s | 30s |
| Validation (50 employees) | < 2s | 5s |
| Calculation (50 employees) | < 5s | 15s |
| Calculation (500 employees) | < 30s | 60s |
| Calculation (1000+ employees) | Background | — |
| Draft summary generation | < 2s | 5s |

## 24. Accessibility

- Validation results: color + icon + text (never color-only)
- Progress bar: aria-valuenow, aria-valuemin, aria-valuemax
- Error messages: linked to inputs via aria-describedby
- Tab order: follows visual flow (upload → match → validate → review)
- Screen reader: announces validation summary counts

## 25. Analytics Events

| Event | Properties |
|-------|-----------|
| `payroll.preparation_started` | period, employee_count |
| `payroll.attendance_uploaded` | file_type, row_count, matched_count |
| `payroll.validation_run` | block_count, flag_count, warn_count, duration |
| `payroll.calculated` | employee_count, gross, net, duration |
| `payroll.comparison_viewed` | gross_change_pct, net_change_pct |
| `payroll.crosscheck_viewed` | check_name, status |
| `payroll.submitted` | employee_count, total, warnings_acknowledged |

## 26. Audit Events

| Action | Entity | Details |
|--------|--------|---------|
| `payroll.created` | PayrollRun | {period, source, employee_count} |
| `payroll.attendance_imported` | PayrollRun | {file_name, row_count, matched_count, unmatched_count} |
| `payroll.validated` | PayrollRun | {block_count, flag_count, warn_count} |
| `payroll.calculated` | PayrollRun | {employee_count, gross, tax, pension, net} |
| `payroll.flag_overridden` | PayrollValidationResult | {rule, employee_id, reason, overridden_by} |
| `payroll.submitted` | PayrollRun | {submitted_by, submitted_at} |
| `payroll.deleted` | PayrollRun | {deleted_by, deleted_at} |

## 27. Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| Customer | Payroll completed in | < 15 minutes |
| Customer | Payroll corrections after approval | < 1% |
| Customer | Payrolls approved before payday | > 95% |
| Business | Payroll preparation time | Reduced by 97% |
| Business | HR support requests | Reduced by 80% |
| Business | Customer renewals | > 95% |
| Platform | Validation completion rate | 100% |
| Platform | Crosscheck pass rate | > 99% |
| Platform | Payroll variance alerts resolved | 100% |

## 28. Acceptance Tests

```
Scenario: Generate payroll draft successfully
Given   50 active employees with valid TINs and bank accounts
And     Attendance imported for all 50 employees
And     No overtime or leave adjustments
When    Payroll Officer clicks "Generate Draft"
Then    PayrollRun created with status "review"
And     50 Payslips created
And     Tax calculated using current TaxRule brackets
And     Pension calculated as 7% of basic salary
And     Net pay = gross - pension - tax - deductions
And     Crosscheck: attendance vs payroll = 50/50 (PASS)
And     Crosscheck: ERCA totals match (PASS)
And     Month-over-month comparison available
And     Audit log: payroll.calculated

Scenario: Validation blocks on missing TIN
Given   1 employee has no TIN
When    Payroll Officer runs validation
Then    BLOCK: "Employee [name] has no TIN"
And     Draft generation is prevented
And     Payroll Officer can click "Fix" to navigate to employee record

Scenario: Validation flags salary change
Given   Employee #37 salary changed from ETB 8,000 to ETB 12,000
When    Payroll Officer runs validation
Then    FLAG: "Salary increased 50% (ETB 8,000 → ETB 12,000)"
And     Draft can be generated
And     Payroll Officer must acknowledge with reason before submission

Scenario: Crosscheck detects ERCA mismatch
Given   Payroll tax total is ETB 412,650
And     ERCA report total is ETB 412,700 (ETB 50 difference)
When    Crosscheck runs
Then    BLOCK: "ERCA total mismatch: payroll ETB 412,650 vs ERCA ETB 412,700"
And     Payroll Officer must resolve before submission

Scenario: Month-over-month comparison
Given   Last month payroll was ETB 2,000,000
And     This month payroll is ETB 2,100,000 (+5%)
When    Draft is generated
Then    Comparison shows: "+ETB 100,000 (+5.0%)"
And     Top 3 changes identified with reasons
And     No FLAG (within 20% threshold)

Scenario: Large payroll variance flag
Given   Last month payroll was ETB 2,000,000
And     This month payroll is ETB 2,500,000 (+25%)
When    Draft is generated
Then    FLAG: "Payroll changed +25% vs last month"
And     Payroll Officer must acknowledge before submission

Scenario: Attendance import with mismatches
Given   CSV has 52 rows
And     2 rows don't match any employee
When    Payroll Officer imports
Then    System shows: "48/50 matched. 2 unmatched rows."
And     Unmatched rows displayed with resolution options
Payroll Officer can map, skip, or create new employee

Scenario: Re-calculate after data fix
Given   Payroll draft exists
And     Payroll Officer forgot to add overtime for employee #12
When    Payroll Officer adds overtime and clicks "Re-calculate"
Then    System shows: "Re-calculate payroll? This will replace the current draft."
When    Payroll Officer confirms
Then    Draft updated with new overtime amount
And     All totals recalculated
And     Crosschecks re-run
```

## 29. Rollout Strategy

| Phase | Scope | Feature Flags |
|-------|-------|--------------|
| Internal testing | Demo company, 10 employees | All features ON |
| Pilot (10 companies) | Real data, 50-200 employees | Crosscheck ON, Trust Score ON |
| Limited availability (50 companies) | Self-service | Crosscheck ON, Trust Score ON |
| General availability | Open | All features ON |

## 30. Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Employee management | ✅ Exists | Journey 1 |
| Attendance import | ✅ Exists | `attendance_bp.py` |
| Tax calculation | ✅ Exists | `tax.py` |
| Pension calculation | ✅ Exists | `pension.py` |
| Overtime calculation | ✅ Exists | `overtime.py` |
| Leave management | ✅ Exists | `leave.py` |
| Validation engine | ✅ Exists | `validation.py` |
| Payroll model | ✅ Exists | `models.py` |
| TaxRule model | ✅ Exists | `models.py` |
| Crosscheck engine | ❌ New | Needs build |
| Month comparison | 🟡 Partial | Logic exists in `reports_bp.py`, needs integration |
| Calculation snapshot | ❌ New | ADR-007 |
| Trust Score | ❌ New | Needs build |

## 31. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Wrong tax brackets | Low | High | TaxRule versioning + calculation snapshot |
| Pension calculated on wrong base | Low | High | Crosscheck: pension = 7% of basic (not gross) |
| Attendance import mismatch | Medium | Medium | Auto-match + manual resolution UI |
| Calculation timeout (1000+ employees) | Medium | High | Background processing via RQ |
| Concurrent draft modification | Low | Medium | Optimistic locking or "last write wins" with audit |
| Ethiopian calendar edge cases | Low | Medium | Test with boundary dates (Pagume, New Year) |

## 32. Future Extensions

- Attendance device direct integration (not just CSV)
- Scheduled payroll (auto-generate on configured date)
- Multi-period payroll (bi-weekly)
- Payroll approval workflow (multi-level)
- Correction run wizard (Journey 3 extension)
- Bulk salary adjustment
- Payroll budgeting (set budget, track actual vs budget)

---

*PRD-02 | Part of CUSTOMER_JOURNEY_BLUEPRINT v2.0*
*Foundation: DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md*
