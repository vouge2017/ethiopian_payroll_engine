# PRD-03: Approve & Lock Payroll
**Journey:** 3 — Approve & Lock Payroll
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md
**Catalogues:** STATE_MACHINE_CATALOGUE.md (SM-001), NOTIFICATION_CATALOGUE.md (N-001, N-004, N-005, N-007), ANALYTICS_CATALOGUE.md (AE-026 through AE-031), EVIDENCE_CATALOGUE.md (EV-013, EV-018)

---

## 1. Vision

Every Ethiopian business owner can approve payroll in under 2 minutes with complete confidence that every number is correct, cross-checked, and defensible — and once approved, the payroll is locked and immutable.

## 2. Customer Problem

Business owners currently approve payroll by receiving an Excel file via Telegram, eyeballing the total, saying "looks okay," and hoping it's right. There's no verification, no audit trail, no confidence score, and the Excel can still be modified after "approval." When errors are discovered (wrong tax, missing overtime, incorrect pension), there's no way to prove what was approved or fix it without starting over.

## 3. Business Objective

Enable the owner to approve payroll with a single tap, backed by a confidence report showing all crosschecks passed, and immediately lock the payroll so no further changes are possible. Create a permanent audit trail that defensible to ERCA, MOLSA, or any auditor.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Business Owner** | Reviews confidence report, taps approve | Monthly |
| **Supporting: Payroll Officer** | Presents draft, answers questions, handles warnings | Monthly |
| **Supporting: Accountant** | Reviews crosscheck results, signs off on compliance | Monthly |
| **Waiting: System** | Runs crosschecks, generates confidence score, locks run | During approval |
| **Handoff: Employees** | Receive payslips after approval (Journey 6) | Monthly |
| **Handoff: Finance** | Receives bank file after approval (Journey 4) | Monthly |

## 5. Entry Criteria

- PayrollRun exists with status `review` (from PRD-02)
- All validation BLOCKs resolved
- All validation FLAGs acknowledged (or none exist)
- Crosscheck results available
- Month-over-month comparison available
- Owner is authenticated

## 6. Exit Criteria

- PayrollRun status is `locked`
- All Payslip records frozen (no further modification possible)
- Calculation snapshot frozen on each Payslip
- Audit log entry created (payroll.approved, payroll.locked)
- Notifications sent to employees (N-005)
- Bank file generation triggered (Journey 4)
- ERCA report generation triggered (Journey 5)

## 7. User Journey

### Main Flow

```
Owner receives notification: "Payroll draft ready for review"
    ↓
Owner opens Payroll → sees Confidence Report
    ↓
System shows:
  Employees: 50
  Gross: ETB 2,145,330
  Tax: ETB 412,650
  Pension: ETB 148,173
  Net: ETB 1,584,507
    ↓
System shows crosscheck results:
  ✓ Attendance vs Payroll: PASSED
  ✓ ERCA totals match: PASSED
  ✓ Pension totals match: PASSED
  ✓ Bank file matches: PASSED
    ↓
System shows month-over-month comparison:
  "+ETB 68,330 (+3.2%) vs last month"
  Top drivers: +2 new hires, +overtime, -1 termination
    ↓
Owner drills into any number → ExplainPanel shows:
  Formula, inputs, law citation, timestamp, approver
    ↓
Owner acknowledges any remaining warnings
    ↓
Owner taps "Approve"
    ↓
System shows confirmation:
  "You are approving payroll PR-2018-10-042 for ETB 1,584,507.00.
   This action is permanent and recorded.
   IP: 196.188.x.x, Time: 2026-07-28 14:35"
    ↓
Owner confirms
    ↓
System:
  1. Sets PayrollRun.status = processing
  2. Freezes calculation snapshot on each Payslip
  3. Sets PayrollRun.status = completed
  4. Locks PayrollRun (status = locked, locked_at, locked_by)
  5. Triggers bank file generation (Journey 4)
  6. Triggers ERCA report generation (Journey 5)
  7. Triggers pension report generation
  8. Publishes payslips to employee portal
  9. Sends notifications (N-004, N-005)
  10. Logs audit events
    ↓
System shows:
  "Payroll locked. ERCA report generated. Bank file generated.
   Payslips published. 50 employees notified."
    ↓
Owner sees: "One tap and everything is done."
```

### Alternative Flows

**A1: Owner wants to review individual employees**
1. Owner clicks "View Employee Details" on confidence report
2. System shows employee list (sortable by name, department, net pay)
3. Owner clicks any employee → full calculation breakdown with evidence
4. Owner returns to confidence report
5. Continues with approval

**A2: Owner finds an error after reviewing**
1. Owner clicks "Return to Payroll Officer"
2. System changes PayrollRun.status back to `review`
3. Payroll Officer corrects the data
4. Payroll Officer re-generates draft
5. Owner receives new notification (N-001)
6. Reviews again

**A3: Owner rejects the payroll**
1. Owner clicks "Reject"
2. System asks for reason
3. Owner enters: "Overtime for department X not included"
4. System sets PayrollRun.status back to `draft`
5. Payroll Officer receives notification
6. Payroll Officer adds overtime, re-generates

**A4: Approval delayed (overdue)**
1. Payroll is in `pending_approval` for > 2 days
2. System sends N-007: "Payroll for [month] still not approved. Employees expect payment on [date]."
3. Owner receives escalation
4. Owner approves or rejects

**A5: Concurrent approval attempt**
1. Two users try to approve simultaneously
2. System uses `SELECT ... FOR UPDATE` (row-level lock)
3. First user succeeds, second gets: "Payroll already approved by [user] at [time]"

**A6: Owner wants to see evidence for a specific number**
1. Owner clicks ⓘ next to any number
2. ExplainPanel slides in showing:
   - Value
   - Formula
   - Inputs
   - Law citation
   - Calculation timestamp
   - Approver
   - Evidence hash
3. Owner closes panel, returns to confidence report

## 8. Screen Specifications

### Screen: Approval Confidence Report

```
Screen: Payroll Approval
URL: /payroll/{id}/approve
Purpose: Show confidence report for owner review and approval
Auth: Owner, Admin

Layout:
  Header: "Payroll Approval — PR-2018-10-042"
  Main:
    Summary card: employees, gross, tax, pension, net
    Crosscheck results card
    Month-over-month comparison card
    Warning acknowledgment section (if any)
    Employee list (expandable, drill-down)
    Approval button (disabled if BLOCKs exist)
    Reject button

States:
  Loading: Skeleton screens
  Ready: Full confidence report
  Has warnings: Yellow banner, acknowledge required
  Has blocks: Red banner, approval disabled
  Approving: Spinner + "Processing approval..."
  Approved: Success message + next steps

Actions:
  Primary: "Approve Payroll" (only if no BLOCKs, all warnings acknowledged)
  Secondary: "View Employee Details", "Return to Payroll Officer"
  Destructive: "Reject Payroll" (requires reason)

Keyboard shortcuts:
  Ctrl+Enter: Approve (with confirmation)
  Escape: Cancel/Back
```

### Screen: Approval Confirmation Dialog

```
Screen: Approval Confirmation
URL: Modal (overlay)
Purpose: Final confirmation before locking
Auth: Owner, Admin

Layout:
  Header: "Confirm Approval"
  Main:
    Payroll reference: PR-2018-10-042
    Total: ETB 1,584,507.00
    Employees: 50
    Warning: "This action is permanent and recorded."
    IP: 196.188.x.x
    Time: 2026-07-28 14:35
  Footer:
    "Approve" button (primary)
    "Cancel" button

States:
  Normal: Show confirmation details
  Processing: Spinner + "Locking payroll..."
  Success: "Payroll locked." + auto-close
  Error: "Approval failed. [reason]" + retry
```

### Screen: Post-Approval Success

```
Screen: Approval Complete
URL: /payroll/{id}/approved
Purpose: Show approval result and next steps
Auth: Owner, Admin

Layout:
  Header: "Payroll Approved ✓"
  Main:
    Success message: "Payroll PR-2018-10-042 locked."
    Summary: 50 employees, ETB 1,584,507.00
    Next steps:
      ✓ ERCA report generated → Download
      ✓ Bank file generated → Download
      ✓ Pension report generated → Download
      ✓ Payslips published → 50 employees notified
    Trust Score update: "Trust Score: 94 → 96 (+2)"

Actions:
  Primary: "Download Bank File"
  Secondary: "Download ERCA Report", "View Payslips"
```

## 9. Component Specifications

### ConfidenceReport
```
Properties:
  employees: number
  gross: Decimal
  tax: Decimal
  pension: Decimal
  net: Decimal
  crosschecks: array of {name, status, expected, actual, difference}
  warnings: array of {rule, message, acknowledged}
  confidence: number (0-100)
  comparison: {gross_change, net_change, headcount_change, top_drivers}

Display:
  Summary block (5 numbers, large, formatted)
  Crosscheck grid (green/red/yellow)
  Warnings list (yellow, checkbox to acknowledge)
  Comparison card (delta, percentage, top 3 drivers)
  Confidence percentage (large, color-coded: green >90, yellow 70-90, red <70)

Events:
  onDrillDown(field) → opens ExplainPanel
  onAcknowledgeWarning(rule) → marks acknowledged
  onViewEmployees() → expands employee list
  onApprove() → opens confirmation dialog
  onReject() → opens rejection dialog
```

### ExplainPanel
```
Properties:
  title: string
  value: Decimal
  formula: string
  inputs: array of {name, value, source}
  lawReference: string
  calculatedAt: DateTime
  calculatedBy: string
  approvedBy: string
  snapshotHash: string

Display:
  Slide-over panel from right (400px)
  Value at top (large, formatted)
  Formula in plain language
  Inputs listed with sources
  Law citation (clickable if URL available)
  Timestamp and approver
  Evidence hash (truncated)

Triggered by:
  Click/tap on any number with ⓘ icon

Events:
  onClose() → returns to previous view
```

### ApprovalButton
```
Properties:
  enabled: boolean (false if BLOCKs exist)
  loading: boolean
  employeeCount: number
  total: Decimal

Display:
  Large primary button: "Approve Payroll — ETB {total}"
  Disabled state: gray, "Cannot approve — {count} blocking issue(s)"
  Loading state: spinner + "Processing..."

Events:
  onClick() → opens ApprovalConfirmationDialog
```

### ApprovalConfirmationDialog
```
Properties:
  reference: string
  total: Decimal
  employees: number
  ip: string
  timestamp: DateTime

Display:
  Modal overlay
  Confirmation details
  Warning: "This action is permanent"
  Two buttons: Approve (primary), Cancel (secondary)

Events:
  onConfirm() → triggers approval
  onCancel() → closes dialog
```

## 10. Business Rules

| Rule | Source | Enforcement |
|------|--------|-------------|
| Cannot approve with BLOCKs | Validation engine | Button disabled |
| Cannot approve without acknowledging all FLAGs | Validation engine | Button disabled until all acknowledged |
| Approval creates permanent audit trail | AuditLog | Logged with IP, timestamp, hash |
| Approval freezes calculation snapshot | ADR-007 | Each Payslip gets snapshot |
| Approval locks PayrollRun | SM-001 | Status → locked, immutable |
| Approval triggers output generation | System | Bank file, ERCA, pension, payslips |
| One approval per PayrollRun | SM-001 | Cannot re-approve locked run |
| Concurrent approval prevented | Database | SELECT ... FOR UPDATE |
| Rejection returns to draft | SM-001 | Status → draft |
| Return to officer returns to review | SM-001 | Status → review |

## 11. Validation Rules

These are checked BEFORE the approval screen is shown (from PRD-02):

| Check | Severity | Blocks Approval? |
|-------|----------|-----------------|
| Missing TIN | BLOCK | Yes |
| Missing bank account | BLOCK | Yes |
| Negative net pay | BLOCK | Yes |
| Duplicate employee | BLOCK | Yes |
| Salary anomaly | FLAG | No (must acknowledge) |
| Salary change >30% | FLAG | No (must acknowledge) |
| Payroll variance >20% | FLAG | No (must acknowledge) |
| Overtime >20 hours | FLAG | No (must acknowledge) |
| Crosscheck failure | BLOCK | Yes |

## 12. Permissions

| Action | Owner | Admin | Manager | Employee | Accountant |
|--------|-------|-------|---------|----------|------------|
| View confidence report | ✅ | ✅ | ❌ | ❌ | ✅ |
| View employee details | ✅ | ✅ | ❌ | ❌ | ✅ |
| View evidence/explain | ✅ | ✅ | ❌ | ❌ | ✅ |
| Acknowledge warnings | ✅ | ✅ | ❌ | ❌ | ❌ |
| Approve payroll | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reject payroll | ✅ | ✅ | ❌ | ❌ | ❌ |
| Return to officer | ✅ | ✅ | ❌ | ❌ | ❌ |
| Lock payroll | ✅ | ✅ | ❌ | ❌ | ❌ |

## 13. State Machine

References SM-001 (PayrollRun).

### Approval Flow States

```
review (from PRD-02)
  ↓ (owner opens approval screen)
pending_approval
  ↓ (owner approves)
processing
  ↓ (system generates outputs)
completed
  ↓ (system locks)
locked

review
  ↓ (owner returns to officer)
review (stays review)

pending_approval
  ↓ (owner rejects)
draft
```

### Transition Details

| From | To | Trigger | Actor | Fields Set |
|------|-----|---------|-------|-----------|
| review | pending_approval | Owner opens approval | Owner | — |
| pending_approval | processing | Owner confirms approval | Owner | approved_at, approved_by, approval_ip |
| processing | completed | All outputs generated | System | gross, tax, pension, net |
| completed | locked | System locks | System | locked_at, locked_by |
| pending_approval | draft | Owner rejects | Owner | rejection_reason |
| pending_approval | review | Owner returns to officer | Owner | — |

### Forbidden Transitions

- `locked` → any (immutable)
- `completed` → `review` (must create correction run)

## 14. API Contracts

### POST /payroll-runs/{id}/submit
Submit draft for owner approval.

**Request:**
```json
{}
```

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "status": "pending_approval",
    "submitted_at": "2026-07-28T10:30:00Z",
    "submitted_by": 15
  }
}
```

**Errors:**
- 409: "Payroll is not in review status"
- 422: "Cannot submit — 1 blocking issue unresolved"

### GET /payroll-runs/{id}/confidence
Get confidence report for approval.

**Response (200):**
```json
{
  "data": {
    "employees": 50,
    "gross": "2145330.00",
    "tax": "412650.00",
    "pension_employee": "148173.00",
    "pension_employer": "231231.00",
    "net": "1584507.00",
    "confidence": 98,
    "crosschecks": [
      {"name": "attendance_vs_payroll", "status": "pass", "expected": 50, "actual": 50, "difference": 0},
      {"name": "erca_totals", "status": "pass", "expected": "412650.00", "actual": "412650.00", "difference": "0.00"},
      {"name": "pension_totals", "status": "pass", "expected": "148173.00", "actual": "148173.00", "difference": "0.00"},
      {"name": "bank_file_total", "status": "pass", "expected": "1584507.00", "actual": "1584507.00", "difference": "0.00"}
    ],
    "warnings": [
      {"rule": "SALARY_CHANGE_30PCT", "employee_id": 37, "employee_name": "Kebede Alemu", "message": "Salary increased 45%", "acknowledged": true, "acknowledged_by": 15, "acknowledged_at": "2026-07-28T14:20:00Z"}
    ],
    "comparison": {
      "gross_change": "68330.00",
      "gross_change_pct": 3.2,
      "net_change": "45220.00",
      "net_change_pct": 2.8,
      "headcount_change": 2,
      "top_drivers": [
        {"description": "+2 new hires", "impact": "24000.00"},
        {"description": "+overtime", "impact": "18000.00"},
        {"description": "-1 termination", "impact": "-12000.00"}
      ]
    }
  }
}
```

### POST /payroll-runs/{id}/approve
Approve and lock payroll.

**Request:**
```json
{
  "acknowledgments": [
    {"rule": "SALARY_CHANGE_30PCT", "employee_id": 37, "reason": "Promotion approved by owner on 2026-07-15"}
  ]
}
```

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "status": "locked",
    "approved_at": "2026-07-28T14:35:00Z",
    "approved_by": 1,
    "approval_ip": "196.188.x.x",
    "locked_at": "2026-07-28T14:35:05Z",
    "locked_by": 1,
    "outputs": {
      "bank_file": {"status": "generated", "url": "/payroll/42/bank-file"},
      "erca_report": {"status": "generated", "url": "/payroll/42/erca"},
      "pension_report": {"status": "generated", "url": "/payroll/42/pension"},
      "payslips": {"status": "published", "count": 50}
    }
  }
}
```

**Errors:**
- 409: "Payroll is not in pending_approval status"
- 422: "Cannot approve — 1 blocking issue unresolved"
- 422: "Cannot approve — 2 warnings not acknowledged"
- 409: "Payroll already approved by [user] at [time]"

### POST /payroll-runs/{id}/reject
Reject payroll.

**Request:**
```json
{
  "reason": "Overtime for Sales department not included"
}
```

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "status": "draft",
    "rejected_at": "2026-07-28T14:40:00Z",
    "rejected_by": 1,
    "rejection_reason": "Overtime for Sales department not included"
  }
}
```

### POST /payroll-runs/{id}/return
Return to payroll officer (back to review).

**Request:**
```json
{
  "reason": "Need to verify overtime entries"
}
```

**Response (200):**
```json
{
  "data": {
    "id": 42,
    "status": "review",
    "returned_at": "2026-07-28T14:40:00Z",
    "returned_by": 1
  }
}
```

## 15. Data Model Changes

### Tables Modified
- `PayrollRun`: approved_at, approved_by, approval_ip, locked_at, locked_by
- `Payslip`: calculation_snapshot (JSON frozen at lock time)

### Tables Created
- None (uses existing models)

### Indexes
- `ix_payrollrun_company_status` (existing)

### Audit Events
- `payroll.submitted` — submitted for approval
- `payroll.approved` — owner approved
- `payroll.locked` — payroll locked
- `payroll.rejected` — owner rejected
- `payroll.returned` — returned to officer
- `payslip.snapshot_frozen` — calculation snapshot frozen

## 16. Notifications

| ID | Event | Recipient | Channel | Message |
|----|-------|-----------|---------|---------|
| N-001 | Draft ready | Owner | In-app, WhatsApp | "Payroll draft PR-{ref} ready for review. {count} employees, ETB {net} net." |
| N-004 | Payroll approved | Payroll Officer | In-app, WhatsApp | "Payroll PR-{ref} approved by {approver}. Generating outputs." |
| N-005 | Payslip ready | Employee | In-app, WhatsApp | "Your payslip for {month} is ready. Net pay: ETB {net}." |
| N-007 | Approval overdue | Owner | In-app, WhatsApp | "Payroll for {month} still not approved. Employees expect payment on {date}." |

## 17. Automation Rules

| Event | Automatic Action |
|-------|-----------------|
| PayrollRun → pending_approval | Notify owner (N-001) |
| PayrollRun → pending_approval > 2 days | Escalation notification (N-007) |
| Owner approves | Lock run, freeze snapshots, generate outputs |
| Owner approves | Generate bank file (Journey 4) |
| Owner approves | Generate ERCA report (Journey 5) |
| Owner approves | Generate pension report |
| Owner approves | Publish payslips to portal |
| Owner approves | Notify employees (N-005) |
| Owner approves | Notify payroll officer (N-004) |
| Owner approves | Log audit events |
| Owner approves | Update Trust Score |
| Owner rejects | Return to draft, notify payroll officer |
| Owner returns to officer | Return to review, notify payroll officer |

## 18. Evidence Requirements

| Data Point | Evidence ID | Shown In |
|-----------|------------|----------|
| Gross total | EV-001 (sum) | Confidence report |
| Tax total | EV-005 (sum) | Confidence report |
| Pension total | EV-002 (sum) | Confidence report |
| Net total | EV-006 (sum) | Confidence report |
| Crosscheck: attendance | EV-013 | Crosscheck card |
| Crosscheck: ERCA | EV-014 | Crosscheck card |
| Crosscheck: pension | EV-015 | Crosscheck card |
| Crosscheck: bank file | EV-016 | Crosscheck card |
| Month comparison | EV-018 | Comparison card |
| Individual employee | EV-001 through EV-009 | ExplainPanel |

## 19. Trust Moments

| Moment | What Happens | What Customer Thinks |
|--------|-------------|---------------------|
| Confidence report loads | All numbers + crosschecks displayed | "Every number is checked against another source" |
| Crosscheck: all PASSED | Green checkmarks on all 4 checks | "I can trust these numbers" |
| ExplainPanel opens | Formula, inputs, law, timestamp shown | "I can defend this to any auditor" |
| Approval confirmation | IP, time, "permanent and recorded" | "This is documented and defensible" |
| Post-approval lock | "Payroll locked. No further changes." | "No one can modify this after I approved" |
| Trust Score increase | Score goes from 94 to 96 | "The longer I use this, the stronger my track record" |

## 20. Error Handling

| Error | Handling |
|-------|----------|
| BLOCK exists when owner tries to approve | Show error: "Cannot approve — {count} blocking issue(s). Fix or override first." |
| Warning not acknowledged | Show error: "Acknowledge all warnings before approving." |
| Concurrent approval | Show error: "Payroll already approved by {user} at {time}." |
| Database error during lock | Retry once, then show error: "Approval failed. Try again or contact support." |
| Output generation fails | Partial success: "Payroll locked but {component} generation failed. Retry from payroll details." |
| Network timeout | Show: "Approval submitted. Check status in a moment." Poll for completion. |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| Owner approves but internet drops | Approval is transactional — either fully committed or rolled back |
| Owner approves from mobile | Confirmation dialog sized for mobile, same flow |
| 1000+ employees | Confidence report loads summary first, employee list paginated |
| No crosschecks available | Show warning: "Crosschecks not run. Run validation first." |
| Crosscheck BLOCK exists | Approval button disabled, red banner shows issue |
| Owner is also payroll officer | Same flow — owner reviews own draft (audit trail still records) |
| Approval after hours | Allowed — no time restriction |
| Re-approval after rejection | Full flow restarts from review |

## 22. Security

- Approval requires authenticated owner/admin session
- Approval IP recorded for audit
- Approval action logged with hash chain
- Cannot approve without CSRF token (form submission)
- Cannot approve via API without valid Bearer token
- Rate limit: 5 approvals per hour per company

## 23. Performance

| Operation | Target | Max |
|-----------|--------|-----|
| Confidence report load | < 2s | 5s |
| Approval + lock | < 5s | 15s |
| Output generation trigger | < 1s | 3s |
| Notification dispatch | < 2s | 5s |
| Post-approval page load | < 2s | 5s |

## 24. Accessibility

- Approval button: aria-label="Approve payroll for ETB {total}"
- Confirmation dialog: focus trap, Escape to close
- Crosscheck results: color + icon + text (never color-only)
- Confidence percentage: aria-valuenow, aria-valuemin=0, aria-valuemax=100
- Tab order: summary → crosschecks → warnings → approve button

## 25. Analytics Events

| ID | Event | Properties |
|----|-------|-----------|
| AE-026 | payroll.submitted | company_id, run_id, employee_count, total, warnings_acknowledged |
| AE-027 | payroll.approved | company_id, run_id, employee_count, total, confidence, duration_ms |
| AE-028 | payroll.rejected | company_id, run_id, reason |
| AE-029 | payroll.locked | company_id, run_id |
| AE-031 | payroll.flag_overridden | company_id, run_id, rule, employee_id, reason |
| AE-103 | crosscheck.run | company_id, run_id, check_name, status, duration_ms |
| AE-045 | payslip.explained | company_id, payslip_id, field |

## 26. Audit Events

| Action | Entity | Details |
|--------|--------|---------|
| payroll.submitted | PayrollRun | {submitted_by, submitted_at} |
| payroll.approved | PayrollRun | {approved_by, approved_at, approval_ip, employee_count, total} |
| payroll.locked | PayrollRun | {locked_by, locked_at} |
| payroll.rejected | PayrollRun | {rejected_by, rejected_at, reason} |
| payroll.returned | PayrollRun | {returned_by, returned_at, reason} |
| payroll.flag_overridden | PayrollValidationResult | {rule, employee_id, reason, overridden_by} |
| payslip.snapshot_frozen | Payslip | {payslip_id, snapshot_hash} |

## 27. Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| Customer | Owner approval time | < 2 minutes |
| Customer | Approval confidence | > 95% |
| Business | Payroll corrections after approval | < 0.5% |
| Business | Audit findings from approval process | 0 |
| Platform | Crosscheck completion rate | 100% |
| Platform | Post-approval modifications | 0 (locked) |
| Platform | Approval-to-lock time | < 10 seconds |

## 28. Acceptance Tests

```
Scenario: Owner approves payroll successfully
Given   PayrollRun status is "review"
And     All crosschecks PASSED
And     No BLOCK-severity warnings
When    Owner opens approval screen
Then    Confidence report shows: 50 employees, ETB 1,584,507 net, 98% confidence
When    Owner taps "Approve"
Then    Confirmation dialog shows: reference, total, employees, IP, time
When    Owner confirms
Then    PayrollRun status changes: review → pending_approval → processing → completed → locked
And     Calculation snapshot frozen on all 50 Payslips
And     Audit log: payroll.approved (with IP, timestamp)
And     Audit log: payroll.locked
And     Bank file generation triggered
And     ERCA report generation triggered
And     Pension report generation triggered
And     50 payslips published to portal
And     Notification N-005 sent to all 50 employees
And     Notification N-004 sent to payroll officer
And     Trust Score updated

Scenario: Owner cannot approve with BLOCKs
Given   PayrollRun has 1 BLOCK: "Employee #37 has no bank account"
When    Owner opens approval screen
Then    Approval button is disabled
And     Red banner shows: "Cannot approve — 1 blocking issue"
And     Issue details shown with "Fix" link

Scenario: Owner must acknowledge warnings before approval
Given   PayrollRun has 2 FLAGs not acknowledged
When    Owner opens approval screen
Then    Approval button is disabled
And     Yellow banner shows: "Acknowledge 2 warnings before approving"
When    Owner acknowledges both warnings with reasons
Then    Approval button becomes enabled

Scenario: Owner rejects payroll
Given   PayrollRun status is "pending_approval"
When    Owner taps "Reject"
Then    System asks for reason
When    Owner enters: "Overtime not included"
Then    PayrollRun status changes to "draft"
And     Payroll officer receives rejection notification
And     Audit log: payroll.rejected

Scenario: Owner returns to payroll officer
Given   PayrollRun status is "pending_approval"
When    Owner taps "Return to Payroll Officer"
Then    PayrollRun status changes to "review"
And     Payroll officer receives notification

Scenario: Concurrent approval prevented
Given   PayrollRun status is "pending_approval"
And     Owner A and Owner B both open approval screen
When    Owner A taps "Approve" at 14:35:00
And     Owner B taps "Approve" at 14:35:01
Then    Owner A's approval succeeds
And     Owner B sees: "Payroll already approved by Owner A at 14:35:00"

Scenario: Approval overdue escalation
Given   PayrollRun status is "pending_approval"
And     2 days have passed since submission
When    System checks overdue approvals
Then    N-007 sent to owner: "Payroll for July still not approved. Employees expect payment on Friday."

Scenario: ExplainPanel shows evidence
Given   Owner is viewing confidence report
When    Owner clicks ⓘ next to "Tax: ETB 412,650"
Then    ExplainPanel opens showing:
        - Value: ETB 412,650.00
        - Formula: SUM of all employee taxes
        - Inputs: 50 employee tax amounts
        - Law: Proclamation No. 1395/2025, Art. 36(1)
        - Calculated: 2026-07-28 10:35:12
        - Crosscheck: ERCA total matches ✓
```

## 29. Rollout Strategy

| Phase | Scope | Feature Flags |
|-------|-------|--------------|
| Internal testing | Demo company | All features ON |
| Pilot (10 companies) | Real data | Crosscheck ON, Evidence ON |
| Limited availability | 50 companies | All features ON |
| General availability | Open | All features ON |

## 30. Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| PayrollRun (review status) | ✅ Exists | From PRD-02 |
| Payslip records | ✅ Exists | From PRD-02 |
| Validation results | ✅ Exists | From PRD-02 |
| Crosscheck engine | ❌ New | Needs build (ADR-003) |
| Calculation snapshot | ❌ New | Needs build (ADR-007) |
| Confidence report API | ❌ New | Needs build |
| ExplainPanel component | ❌ New | Needs build (ADR-005) |
| Trust Score | ❌ New | Needs build (ADR-006) |
| Bank file generation | ✅ Exists | `bank_file.py` |
| ERCA report generation | ✅ Exists | `reports.py` |
| Pension report generation | ✅ Exists | `reports.py` |
| Notification system | ✅ Exists | `notifications.py` |
| Audit log | ✅ Exists | `models.py` |
| SELECT FOR UPDATE | ✅ Exists | `payroll_bp.py` line 371 |

## 31. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Owner approves without reviewing | Medium | High | Require scroll through confidence report before approve button activates |
| Crosscheck not run before approval | Low | High | Block approval if crosschecks not completed |
| Snapshot too large (1000+ employees) | Low | Medium | Compress JSON, store hash instead of full snapshot if needed |
| Approval timeout (slow database) | Low | High | Transaction timeout + retry |
| Owner confused by confidence score | Medium | Medium | Tooltip explains score calculation |
| Mobile approval UX | Medium | Medium | Responsive confirmation dialog |

## 32. Future Extensions

- Multi-level approval (manager → owner)
- Approval delegation (owner approves someone else to approve)
- Scheduled auto-approval (if no issues, auto-approve on date)
- Approval comments (owner adds note before approving)
- Bulk approval (approve multiple periods at once)
- Approval history view (all past approvals with details)

---

*PRD-03 | Part of CUSTOMER_JOURNEY_BLUEPRINT v2.0*
*References: SM-001, N-001/N-004/N-005/N-007, AE-026 through AE-031, EV-013/EV-018*
