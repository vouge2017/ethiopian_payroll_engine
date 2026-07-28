# PRD-04: Pay Employees
**Journey:** 4 — Pay Employees
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 3
**Template:** PRD-TEMPLATE.md (32 sections)
**Foundation:** DATA_MODEL.md, BACKEND_ARCHITECTURE.md, FRONTEND_DESIGN_SYSTEM.md, ENGINEERING_QUALITY_STANDARDS.md
**Catalogues:** STATE_MACHINE_CATALOGUE.md (SM-001), PAYMENT_CATALOGUE.md (PB-001, PS-001, PM-001, RT-001, RV-001, BR-001), NOTIFICATION_CATALOGUE.md (PN-001 through PN-007), ANALYTICS_CATALOGUE.md (PA-001 through PA-010), EVIDENCE_CATALOGUE.md (EV-017)

---

## 1. Vision

Every Ethiopian business owner can pay their entire team with confidence — download a bank file, upload it to the bank portal, and track exactly who was paid, who failed, and why — without ever reopening payroll.

## 2. Customer Problem

After approving payroll, the business owner currently receives a bank file and uploads it to the bank portal. But the process ends there — there's no tracking of whether the bank actually processed the file, which employees received money, or what to do when payments fail. If 3 out of 200 employees' payments are rejected (wrong account number, frozen account), the owner has no systematic way to fix and retry those payments. They resort to manual WhatsApp messages and Excel tracking, which defeats the purpose of having a payroll system.

The bigger problem: when payments fail, owners are tempted to "just reopen payroll" — which breaks the audit trail, invalidates the approval, and creates compliance risk. Payment failures must be handled without touching the approved payroll.

## 3. Business Objective

Transform an approved payroll into successful employee payments. Provide a clear, auditable path from "payroll approved" to "all employees paid" — including handling partial failures, retries, and reversals — while keeping the approved payroll permanently locked.

## 4. Personas & Roles

| Role | Action | Frequency |
|------|--------|-----------|
| **Primary: Business Owner** | Confirms payment details, downloads bank file, marks payments as paid | Monthly |
| **Supporting: Payroll Officer** | Generates bank file, handles failed payments, manages retries | Monthly |
| **Supporting: Accountant** | Reviews payment totals against payroll, handles reversals | Monthly |
| **Waiting: System** | Creates payment batch, generates file, tracks statuses | During payment processing |
| **Handoff: Bank** | Processes bulk payment file, transfers funds | External |
| **Handoff: Employees** | Receive salary in bank account | Monthly |

## 5. Entry Criteria

- PayrollRun status is `locked` (from PRD-03)
- All Payslip records frozen with calculation snapshots
- At least one employee has a valid bank account number
- Owner has confirmed the payroll approval

## 6. Exit Criteria

- PaymentBatch status is `completed` or `closed`
- All Payslip payment statuses are resolved (`paid`, `failed_permanent`, `skipped`, or `reversed`)
- Bank file has been generated and downloaded
- Payment confirmation recorded in audit log
- Failed payments have retry history or manual resolution notes
- Employees with `paid` status can receive payslips (PRD-05)

## 7. User Journey

### Main Flow

```
Owner receives notification: "Payroll PR-2026-07-001 approved. Ready to pay."
    ↓
Owner opens Payroll → sees Payment Summary
    ↓
System shows:
  Employees: 50
  Total Net: ETB 1,584,507.00
  Payment Method: Bank Transfer (CBE)
  Bank Account Validation: 50/50 valid
    ↓
Owner taps "Generate Bank File"
    ↓
System:
  1. Creates PaymentBatch (status: draft → ready → file_generated)
  2. Generates CBE bulk upload CSV/XLSX
  3. Validates all account numbers (pre-check)
  4. Sets each Payslip.payment_status = 'file_generated'
    ↓
System shows:
  "Bank file ready: CBE_Transfer_July2026.xlsx
   50 employees, ETB 1,584,507.00
   Download file"
    ↓
Owner downloads file
    ↓
Owner uploads file to CBE portal (outside the system)
    ↓
Owner returns to system → taps "Mark as Submitted"
    ↓
System:
  1. Sets PaymentBatch.status = 'submitted'
  2. Sets each Payslip.payment_status = 'submitted'
  3. Records submitted_at, submitted_by
    ↓
(time passes — bank processes the file)
    ↓
Owner checks bank portal → sees 47 successful, 3 rejected
    ↓
Owner returns to system → marks individual payments:
  - 47 employees → "Mark as Paid"
  - 3 employees → "Mark as Failed" (with reason)
    ↓
System shows:
  "47 employees paid (ETB 1,491,207.00)
   3 employees failed (ETB 93,300.00) — require attention"
    ↓
Payment Batch status: partial
    ↓
[See Alternative Flow: Handle Failed Payments]
```

### Alternative Flow: Handle Failed Payments

```
Owner opens failed payments panel
    ↓
System shows:
  EMP023 — Abebe Kebede — ETB 11,265.00
    Reason: Account number invalid (CBE rejected)
    Original: 100012345678X
    Retry count: 0/3

  EMP041 — Fatuma Hassan — ETB 5,830.00
    Reason: Account frozen
    Retry count: 0/3

  EMP050 — Yonas Daniel — ETB 13,051.00
    Reason: Insufficient bank funds (company account)
    Retry count: 0/3
    ↓
Owner fixes EMP023's account number (corrects last digit)
    ↓
Owner taps "Retry" on EMP023
    ↓
System:
  1. Sets EMP023 payment_status = 'retry'
  2. Increments retry_count
  3. Records correction reason
    ↓
Owner taps "Generate Bank File" again
    ↓
System generates file containing ONLY retried payments (1 employee)
    ↓
Owner uploads to bank, marks as submitted, marks as paid
    ↓
EMP023 payment_status = 'paid'
    ↓
For EMP041 (account frozen) and EMP050 (insufficient funds):
  - Owner resolves externally (employee provides new account / company deposits funds)
  - Owner retries when resolved
  - If not resolved after 3 retries → status = 'failed_permanent'
    ↓
When all employees resolved (paid, failed_permanent, or skipped):
  PaymentBatch.status = 'completed'
```

### Alternative Flow: Cash Payment

```
Owner selects "Cash" as payment method for specific employees
    ↓
System creates PaymentBatch with payment_method = 'cash'
    ↓
No bank file generated — instead, system generates:
  1. Cash payment register (PDF) — employee name, amount, signature line
  2. Individual cash receipts
    ↓
Owner pays employees physically, collects signatures
    ↓
Owner returns to system → marks each as "Paid"
    ↓
System records: paid_at, paid_by, payment_method = 'cash'
    ↓
Cash payments follow same status lifecycle as bank payments
```

### Alternative Flow: Reversal

```
Owner discovers EMP003 was paid ETB 15,000 but should have been ETB 12,000
    ↓
Owner opens EMP003's payment → taps "Reverse"
    ↓
System shows confirmation:
  "You are reversing payment to Gebrehiwot Tesfaye.
   Original amount: ETB 15,000.00
   This will create an adjustment payslip.
   This action is permanent and recorded.
   IP: 196.188.x.x, Time: 2026-07-28 16:45"
    ↓
Owner enters reason: "Overpayment — allowances entered incorrectly"
    ↓
System:
  1. Sets original payslip.payment_status = 'reversed'
  2. Creates ReversalRecord with original payment details
  3. Creates adjustment payslip for the correction
  4. Records in audit log
    ↓
Owner processes correction through normal payroll flow
```

## 8. Screen Specifications

### Screen 1: Payment Summary (Post-Approval)

| Element | Description |
|---------|-------------|
| **Header** | "Pay Employees — {period}" |
| **Summary Card** | Total employees, total net pay, payment method, bank validation status |
| **Payment Method Selector** | Bank Transfer / Cash / Cheque (if mixed, show breakdown) |
| **Bank Validation Status** | "50/50 valid" or "47/50 valid — 3 need attention" with link to fix |
| **Action Button** | "Generate Bank File" (primary) or "Generate Cash Register" |
| **Previous Batches** | List of existing payment batches for this payroll (if any) |

### Screen 2: Payment Batch Detail

| Element | Description |
|---------|-------------|
| **Header** | "Payment Batch {batch_ref}" |
| **Status Banner** | Color-coded: green (completed), yellow (partial), blue (submitted), grey (file_generated) |
| **Progress Bar** | Visual: paid / failed / pending / skipped |
| **Summary Stats** | Paid: 47 (ETB 1,491,207) · Failed: 3 (ETB 93,300) · Pending: 0 |
| **Employee Table** | Name, employee ID, amount, status, bank, account number (masked), actions |
| **Action Buttons** | "Mark All as Paid" (bulk), "Download Bank File" (re-download), "Generate Retry File" (if failures) |
| **Filter Tabs** | All / Paid / Failed / Pending / Skipped |

### Screen 3: Failed Payments Panel

| Element | Description |
|---------|-------------|
| **Header** | "3 Payments Require Attention" |
| **Failed Payment Cards** | Each card shows: employee name, amount, failure reason, retry count, original account, correction field |
| **Action per Card** | "Edit Account & Retry" or "Skip Payment" or "Mark as Paid (manual)" |
| **Retry Counter** | Visual: 0/3, 1/3, 2/3, 3/3 (red at 3/3) |
| **Batch Retry Button** | "Generate Retry File" — generates file for all retried payments |

### Screen 4: Reversal Confirmation Dialog

| Element | Description |
|---------|-------------|
| **Title** | "Reverse Payment" |
| **Employee Info** | Name, ID, original amount |
| **Amount Field** | Pre-filled with original amount (can be partial) |
| **Reason Field** | Required, minimum 10 characters |
| **Warning** | "This creates an adjustment payslip. The original payment record is preserved." |
| **Confirmation** | IP address, timestamp, "I understand this is permanent" checkbox |
| **Buttons** | "Reverse Payment" (destructive red) / "Cancel" |

## 9. Component Specifications

### PaymentSummary Component

```
Props:
  payrollRunId: int
  employees: list
  totalNet: decimal
  paymentMethod: string
  bankValidation: { valid: int, invalid: int, warnings: list }

Renders:
  - Summary card with totals
  - Payment method selector
  - Bank validation status with drill-down
  - Primary action button

Events:
  - onGenerateFile(batchId) → triggers file generation
  - onChangeMethod(method) → updates payment method
  - onViewValidation() → opens validation detail panel
```

### PaymentBatchTable Component

```
Props:
  batchId: int
  payments: list [{ id, name, empId, amount, status, bank, account, actions }]
  filters: { status: 'all'|'paid'|'failed'|'pending'|'skipped' }

Renders:
  - Sortable table with status column (color-coded badges)
  - Bulk selection checkboxes
  - Per-row action buttons (Mark Paid, Mark Failed, Retry, Skip)
  - Masked account number (last 4 digits visible)

Events:
  - onMarkPaid(payslipIds) → bulk status update
  - onMarkFailed(payslipId, reason) → individual failure
  - onRetry(payslipId, correction) → initiate retry
  - onSkip(payslipId, reason) → skip payment
```

### FailedPaymentCard Component

```
Props:
  payslipId: int
  employeeName: string
  employeeId: string
  amount: decimal
  failureReason: string
  retryCount: int (0-3)
  originalAccount: string
  bank: string

Renders:
  - Card with employee info and failure details
  - Retry counter (0/3 → 3/3, color-coded)
  - Account correction field (editable when retrying)
  - Action buttons: "Edit & Retry", "Skip", "Mark Paid"

Events:
  - onRetry(correctedAccount, reason) → submit retry
  - onSkip(reason) → skip payment
  - onMarkPaid(confirmationNumber) → manual confirmation
```

### ReversalDialog Component

```
Props:
  payslipId: int
  employeeName: string
  originalAmount: decimal
  maxReversalAmount: decimal

Renders:
  - Modal dialog with employee info
  - Amount field (pre-filled, editable for partial reversal)
  - Reason field (required, min 10 chars)
  - Warning text about adjustment payslip
  - Confirmation checkbox
  - IP + timestamp display

Events:
  - onConfirm(amount, reason) → execute reversal
  - onCancel → close dialog
```

## 10. Business Rules

| ID | Rule | Source |
|----|------|--------|
| BR-04-01 | A payment batch can only be created from a `locked` payroll run | PAYMENT_CATALOGUE.md PB-001 |
| BR-04-02 | Each employee has exactly one payment method per payroll run | PAYMENT_CATALOGUE.md PM-001 |
| BR-04-03 | Bank file generation requires all included employees to have valid account numbers | bank_file.py validation |
| BR-04-04 | Payment status changes are one-way (forward only) except for `failed` → `retry` | PAYMENT_CATALOGUE.md PS-001 |
| BR-04-05 | A payment can be retried up to 3 times before becoming `failed_permanent` | PAYMENT_CATALOGUE.md RT-001 |
| BR-04-06 | Reversals create adjustment payslips — original payslip is never modified | PAYMENT_CATALOGUE.md RV-001 |
| BR-04-07 | Reversal amount cannot exceed the original payment amount | PAYMENT_CATALOGUE.md RV-001-E |
| BR-04-08 | Bank file narrative uses configurable template (default: "{period} salary - {id} {name}") | bank_file.py |
| BR-04-09 | Account numbers must be stored and transmitted as TEXT (never numeric) to prevent scientific notation | bank_file.py |
| BR-04-10 | Payment batch totals must match the approved payroll net total (no rounding differences) | Cross-check |
| BR-04-11 | Cash payments require a signed receipt (PDF with signature line) | Ethiopian labor practice |
| BR-04-12 | Re-opening payroll for payment failures is forbidden — use retry/reversal instead | Core principle |

## 11. Validation Rules

| ID | Validation | Severity | When |
|----|-----------|----------|------|
| VL-04-01 | All employees must have a payment method assigned | BLOCK | Before batch creation |
| VL-04-02 | Bank account numbers must pass format validation | BLOCK | Before file generation |
| VL-04-03 | Net pay must be positive for all employees | BLOCK | Before file generation |
| VL-04-04 | No duplicate account numbers within same batch | BLOCK | Before file generation |
| VL-04-05 | Account number changed from previous month | FLAG | Before file generation (warning, not block) |
| VL-04-06 | Total batch amount must equal payroll net total | BLOCK | Before file generation |
| VL-04-07 | Bank file must be non-empty | BLOCK | At generation time |
| VL-04-08 | Retry count must be < 3 to allow retry | BLOCK | At retry time |
| VL-04-09 | Reversal reason must be ≥ 10 characters | BLOCK | At reversal time |
| VL-04-10 | Reversal amount must be > 0 and ≤ original amount | BLOCK | At reversal time |

## 12. Permissions

| Action | Owner | Payroll Officer | Accountant | Employee |
|--------|-------|----------------|------------|----------|
| View payment summary | ✅ | ✅ | ✅ | ❌ |
| Generate bank file | ✅ | ✅ | ❌ | ❌ |
| Download bank file | ✅ | ✅ | ❌ | ❌ |
| Mark as submitted | ✅ | ✅ | ❌ | ❌ |
| Mark as paid (individual) | ✅ | ✅ | ❌ | ❌ |
| Mark as paid (bulk) | ✅ | ❌ | ❌ | ❌ |
| Mark as failed | ✅ | ✅ | ❌ | ❌ |
| Retry payment | ✅ | ✅ | ❌ | ❌ |
| Skip payment | ✅ | ❌ | ❌ | ❌ |
| Reverse payment | ✅ | ❌ | ❌ | ❌ |
| View reversal history | ✅ | ✅ | ✅ | ❌ |
| Generate cash register | ✅ | ✅ | ❌ | ❌ |

## 13. State Machine

### SM-PB-01: PaymentBatch (new — see PAYMENT_CATALOGUE.md PB-001)

```
draft
  ↓ (confirm details)
ready
  ↓ (generate file)
file_generated
  ↓ (user uploads and confirms)
submitted
  ↓ (all lines resolved)
completed
  ↓ (archive)
closed

Alternative:
draft → cancelled
file_generated → partial (some failures)
partial → completed (all resolved)
partial → closed (remaining accepted as-is)
```

### SM-PS-01: Payslip Payment Status (new — see PAYMENT_CATALOGUE.md PS-001)

```
pending
  ↓ (included in bank file)
file_generated
  ↓ (file uploaded to bank)
submitted
  ↓ (bank processes)
paid / failed
  ↓ (retry from failed)
retry → paid / failed / failed_permanent
  ↓ (reversal from paid)
reversed
```

### SM-001: PayrollRun (existing — no changes)

PRD-04 does NOT change the PayrollRun state machine. Once locked, the payroll stays locked. Payment is a separate domain.

## 14. API Contracts

### POST /api/payroll/{run_id}/payment-batch

Create a payment batch from a locked payroll.

```
Request:
{
  "payment_method": "bank",           // required: bank, cash, cheque
  "bank_code": "cbe",                 // required if method=bank
  "narrative_template": "id_name",    // optional: id_name, name_only, id_only, period_name, custom
  "custom_narrative": null,           // optional: custom template string
  "employee_ids": null                // optional: null=all, or list of specific employee IDs
}

Response (201):
{
  "batch_id": 42,
  "batch_reference": "PB-2026-07-001",
  "payment_method": "bank",
  "bank_code": "cbe",
  "total_employees": 50,
  "total_amount": 1584507.00,
  "status": "ready",
  "validation": {
    "valid": 50,
    "invalid": 0,
    "warnings": []
  }
}

Error (400):
{
  "error": "validation_failed",
  "details": [
    {
      "employee_id": "EMP023",
      "field": "bank_or_telebirr",
      "error": "Invalid CBE account: '100012345678X'. Expected: 13 digits starting with 1",
      "severity": "BLOCK"
    }
  ]
}
```

### POST /api/payment-batch/{batch_id}/generate

Generate the bank file for a payment batch.

```
Request:
{
  "format": "xlsx"    // optional: csv, xlsx (default: xlsx)
}

Response (200):
{
  "batch_id": 42,
  "status": "file_generated",
  "file_url": "/api/payment-batch/42/download",
  "file_format": "xlsx",
  "line_count": 50,
  "total_amount": 1584507.00,
  "generated_at": "2026-07-28T14:30:00Z"
}
```

### GET /api/payment-batch/{batch_id}/download

Download the generated bank file.

```
Response: Binary file (CSV or XLSX)
Content-Disposition: attachment; filename="CBE_Transfer_2026-07.xlsx"
```

### POST /api/payment-batch/{batch_id}/submit

Mark the batch as submitted (user uploaded file to bank).

```
Request:
{
  "notes": "Uploaded to CBE portal at 14:35"    // optional
}

Response (200):
{
  "batch_id": 42,
  "status": "submitted",
  "submitted_at": "2026-07-28T14:35:00Z",
  "submitted_by": 1
}
```

### POST /api/payment-batch/{batch_id}/mark-paid

Bulk mark payments as paid.

```
Request:
{
  "payslip_ids": [101, 102, 103, 104],    // required: list of payslip IDs
  "confirmation_number": "CBE-2026-07-28-001",    // optional
  "notes": "Confirmed via CBE portal"    // optional
}

Response (200):
{
  "updated": 4,
  "batch_status": "partial",    // or "completed" if all resolved
  "paid_count": 47,
  "failed_count": 3,
  "pending_count": 0
}
```

### POST /api/payment-batch/{batch_id}/mark-failed

Mark individual payment as failed.

```
Request:
{
  "payslip_id": 123,    // required
  "failure_reason": "Account number invalid — CBE rejected",    // required
  "notes": null    // optional
}

Response (200):
{
  "payslip_id": 123,
  "payment_status": "failed",
  "retry_count": 0,
  "batch_status": "partial"
}
```

### POST /api/payslip/{payslip_id}/retry

Initiate a payment retry.

```
Request:
{
  "correction": "Account number corrected: 1000123456789 → 1000123456780",    // required
  "new_account": "1000123456780"    // optional: if account was corrected
}

Response (200):
{
  "payslip_id": 123,
  "payment_status": "retry",
  "retry_count": 1,
  "retry_history": [
    {
      "retry_number": 1,
      "reason": "Account number corrected",
      "timestamp": "2026-07-28T15:00:00Z",
      "user_id": 1
    }
  ]
}
```

### POST /api/payslip/{payslip_id}/reverse

Reverse a paid payment.

```
Request:
{
  "amount": 15000.00,    // required: can be partial
  "reason": "Overpayment — allowances entered incorrectly for July"    // required, min 10 chars
}

Response (200):
{
  "original_payslip_id": 123,
  "original_amount": 15000.00,
  "reversal_amount": 15000.00,
  "adjustment_payslip_id": 456,
  "reversed_at": "2026-07-28T16:45:00Z",
  "reversed_by": 1
}
```

### GET /api/payroll/{run_id}/payments

Get payment status summary for a payroll run.

```
Response (200):
{
  "payroll_run_id": 42,
  "reference": "PR-2026-07-001",
  "period": "2018-10",
  "total_employees": 50,
  "total_net": 1584507.00,
  "payment_summary": {
    "paid": { "count": 47, "amount": 1491207.00 },
    "failed": { "count": 3, "amount": 93300.00 },
    "pending": { "count": 0, "amount": 0 },
    "skipped": { "count": 0, "amount": 0 },
    "reversed": { "count": 0, "amount": 0 }
  },
  "batches": [
    {
      "batch_id": 42,
      "reference": "PB-2026-07-001",
      "method": "bank",
      "bank": "cbe",
      "status": "partial",
      "file_url": "/api/payment-batch/42/download"
    }
  ]
}
```

## 15. Data Model Changes

### New Table: PaymentBatch

```sql
CREATE TABLE payment_batch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES company(id),
    payroll_run_id INTEGER NOT NULL REFERENCES payroll_run(id),
    batch_reference VARCHAR(20) UNIQUE,    -- PB-2026-07-001
    payment_method VARCHAR(20) NOT NULL DEFAULT 'bank',
    bank_code VARCHAR(20),                 -- cbe, dashen, awash, etc.
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    total_employees INTEGER NOT NULL DEFAULT 0,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    paid_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    pending_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    file_path VARCHAR(255),
    file_format VARCHAR(10),               -- csv, xlsx
    narrative_template VARCHAR(50) DEFAULT 'id_name',
    custom_narrative VARCHAR(255),
    generated_at TIMESTAMP,
    generated_by INTEGER REFERENCES user(id),
    submitted_at TIMESTAMP,
    submitted_by INTEGER REFERENCES user(id),
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES user(id)
);

CREATE INDEX ix_payment_batch_company ON payment_batch(company_id);
CREATE INDEX ix_payment_batch_run ON payment_batch(payroll_run_id);
CREATE INDEX ix_payment_batch_status ON payment_batch(company_id, status);
```

### Modified Table: Payslip (add columns)

```sql
ALTER TABLE payslip ADD COLUMN bank_file_id INTEGER REFERENCES payment_batch(id);
ALTER TABLE payslip ADD COLUMN payment_status_at TIMESTAMP;
ALTER TABLE payslip ADD COLUMN bank_reference VARCHAR(100);
ALTER TABLE payslip ADD COLUMN submitted_by INTEGER REFERENCES user(id);
ALTER TABLE payslip ADD COLUMN submitted_at TIMESTAMP;
ALTER TABLE payslip ADD COLUMN paid_at TIMESTAMP;
ALTER TABLE payslip ADD COLUMN paid_by INTEGER REFERENCES user(id);
ALTER TABLE payslip ADD COLUMN confirmation_number VARCHAR(100);
ALTER TABLE payslip ADD COLUMN failure_reason TEXT;
ALTER TABLE payslip ADD COLUMN failed_at TIMESTAMP;
ALTER TABLE payslip ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE payslip ADD COLUMN retry_from_id INTEGER REFERENCES payslip(id);
ALTER TABLE payslip ADD COLUMN reversed_at TIMESTAMP;
ALTER TABLE payslip ADD COLUMN reversed_by INTEGER REFERENCES user(id);
ALTER TABLE payslip ADD COLUMN reversal_reason TEXT;
ALTER TABLE payslip ADD COLUMN skipped_reason TEXT;
```

### New Table: PaymentRetryHistory

```sql
CREATE TABLE payment_retry_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payslip_id INTEGER NOT NULL REFERENCES payslip(id),
    retry_number INTEGER NOT NULL,
    correction TEXT NOT NULL,
    old_account VARCHAR(50),
    new_account VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES user(id)
);

CREATE INDEX ix_retry_history_payslip ON payment_retry_history(payslip_id);
```

### New Table: ReversalRecord

```sql
CREATE TABLE reversal_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_payslip_id INTEGER NOT NULL REFERENCES payslip(id),
    adjustment_payslip_id INTEGER REFERENCES payslip(id),
    amount DECIMAL(12,2) NOT NULL,
    reason TEXT NOT NULL,
    reversed_by INTEGER NOT NULL REFERENCES user(id),
    reversed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

CREATE INDEX ix_reversal_original ON reversal_record(original_payslip_id);
```

## 16. Notifications

References: PAYMENT_CATALOGUE.md PN-001 through PN-007

| Notification | Trigger | Recipient | Channel | Priority |
|-------------|---------|-----------|---------|----------|
| PN-001: Payment Batch Created | PaymentBatch created | Owner | In-app | High |
| PN-002: Bank File Generated | File generated | Owner | In-app | High |
| PN-003: Payment Confirmation Needed | Batch has failures | Owner | In-app, WhatsApp | High |
| PN-004: All Payments Completed | All resolved | Owner | In-app, WhatsApp | Medium |
| PN-005: Payment Failed | Individual failure | Payroll Officer | In-app | High |
| PN-006: Retry Limit Reached | 3rd failure | Owner | In-app, WhatsApp | Critical |
| PN-007: Payment Reversed | Reversal created | Owner | In-app, WhatsApp | High |

## 17. Automation Rules

| ID | Rule | Trigger | Action |
|----|------|---------|--------|
| AR-04-01 | Auto-create payment batch | PayrollRun locked | Create PaymentBatch with status `ready` for each payment method group |
| AR-04-02 | Auto-validate accounts | PaymentBatch created | Run bank_file.validate_payroll_for_bank on all employees |
| AR-04-03 | Auto-update batch status | All payslips resolved | Set PaymentBatch.status = `completed` |
| AR-04-04 | Auto-update batch status | Some payslips failed | Set PaymentBatch.status = `partial` |
| AR-04-05 | Auto-include retries | Bank file generated | Include all `retry` payslips in new bank file |
| AR-04-06 | Auto-set payment timestamp | Status → `paid` | Set `paid_at = now()`, `paid_by = current_user` |
| AR-04-07 | Create adjustment on reversal | Reversal confirmed | Create adjustment Payslip with `payslip_type = 'adjustment'` |

## 18. Evidence Requirements

References: EVIDENCE_CATALOGUE.md EV-017

### EV-017: Net Pay (Payment Evidence)

```
Evidence:
  Source: Payroll calculation (frozen at approval)
  Formula: net = gross − pension_employee − tax
  Inputs:
    - gross: ETB {value} (from Payslip.gross_salary)
    - pension_employee: ETB {value} (from Payslip.employee_pension)
    - tax: ETB {value} (from Payslip.tax)
  Output: ETB {net_pay}
  Law: Proclamation No. 1395/2025, Art. 36(1)
  Frozen: {approval_timestamp} by {approver}
  Payment: {payment_method} via {bank_code} on {paid_at}
  Bank Reference: {bank_reference}
  Confirmation: {confirmation_number}
  Hash: {hash}
```

### EV-017-A: Payment Batch Evidence

```
Evidence:
  Source: PaymentBatch record
  Batch: {batch_reference}
  Method: {payment_method}
  Bank: {bank_code}
  Employees: {total_employees}
  Total Amount: ETB {total_amount}
  File: {file_path}
  Generated: {generated_at} by {generated_by}
  Submitted: {submitted_at} by {submitted_by}
  Status: {status}
  Paid: {paid_count} employees (ETB {paid_amount})
  Failed: {failed_count} employees (ETB {failed_amount})
```

## 19. Trust Moments

| Moment | What the User Sees | Why It Matters |
|--------|-------------------|----------------|
| **Bank file ready** | "50 employees, ETB 1,584,507.00 — Download file" | Confirms the file matches the approved payroll exactly |
| **All accounts valid** | "50/50 valid — no issues found" | Confidence that bank won't reject any lines |
| **Payment confirmation** | "47 employees paid. 3 require attention." | Clear status — not "file uploaded" but actual results |
| **Failure with reason** | "Account frozen — employee must visit bank" | Actionable, not just "failed" |
| **Retry success** | "EMP023 paid on retry #1 — account corrected" | Problem → fix → resolution, all tracked |
| **Batch complete** | "All 50 employees paid. Total: ETB 1,584,507.00" | Closure — payment cycle done |
| **Reversal recorded** | "ETB 15,000 reversed. Adjustment payslip #456 created." | Reversal is traceable, not a silent edit |

## 20. Error Handling

| Error | HTTP Code | Response | Recovery |
|-------|-----------|----------|----------|
| Payroll not locked | 400 | `{"error": "payroll_not_locked", "message": "Payroll must be approved and locked before payment"}` | Approve payroll first |
| No employees with bank accounts | 400 | `{"error": "no_payment_method", "message": "No employees have bank accounts assigned"}` | Add bank accounts |
| Account validation failed | 400 | `{"error": "validation_failed", "details": [...]}` | Fix account numbers |
| Batch already exists | 409 | `{"error": "batch_exists", "batch_id": 42, "message": "Payment batch already exists for this payroll"}` | Use existing batch or delete it |
| File generation failed | 500 | `{"error": "generation_failed", "message": "..."}` | Retry generation |
| Payslip not in correct status | 400 | `{"error": "invalid_status", "current": "paid", "required": "failed"}` | Check current status |
| Retry limit exceeded | 400 | `{"error": "retry_limit", "retry_count": 3, "message": "Maximum retries reached"}` | Manual resolution |
| Reversal amount exceeds original | 400 | `{"error": "amount_exceeded", "max": 15000.00}` | Reduce reversal amount |
| Concurrent modification | 409 | `{"error": "conflict", "message": "Payment status changed by another user"}` | Refresh and retry |

## 21. Edge Cases

| Case | Handling |
|------|----------|
| Employee has no bank account | Block from bank file, allow skip or cash payment |
| Employee has multiple bank accounts | Use primary account (first one, or marked as primary) |
| Same account number for two employees | Block — duplicate account detection in bank_file.py |
| Bank file is empty (all employees skipped) | Block — cannot generate empty file |
| Owner marks all as paid at once | Bulk operation, single transaction, audit log per employee |
| Payment made but payroll was for wrong period | Reversal + correction run (PRD-08), not reopening payroll |
| Employee terminated after approval but before payment | Allow skip with reason, or pay and handle via final settlement |
| Bank file generated but never uploaded | File stays in `file_generated`, user can re-download |
| Partial bank file (some lines rejected by bank portal) | System tracks per-employee, not per-file — portal rejection is handled via mark-failed |
| Double payment (file uploaded twice) | Reversal of duplicate, tracked in audit log |
| Payment amount doesn't match payslip | Reversal of incorrect amount + adjustment payslip |

## 22. Security

| Control | Implementation |
|---------|---------------|
| **Tenant isolation** | PaymentBatch.company_id enforced via TenantQuery on all queries |
| **Authorization** | Only Owner can mark as paid (bulk), reverse, or skip. Payroll Officer can generate file and mark individual payments |
| **Audit trail** | Every status change recorded: actor, timestamp, IP, old value, new value |
| **Account number masking** | API responses show only last 4 digits: `****56789` |
| **Bank file encryption** | Generated files stored with restricted access (signed URLs, 24h expiry) |
| **Reversal protection** | Reversal requires reason (min 10 chars), creates immutable ReversalRecord |
| **Concurrent access** | Optimistic locking on PaymentBatch — prevents two users from generating files simultaneously |
| **CSRF protection** | All mutation endpoints require CSRF token |
| **Rate limiting** | Mark-paid and retry endpoints rate-limited to 10/minute per user |

## 23. Performance

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Bank file generation (100 employees) | < 1s | ~0.3s | CSV generation is fast |
| Bank file generation (1000 employees) | < 5s | ~2.8s | XLSX slightly slower |
| Mark-paid bulk (100 employees) | < 2s | N/A | Single transaction, batch update |
| Payment summary API | < 500ms | N/A | Single query with aggregation |
| Account validation (1000 employees) | < 1s | N/A | Regex matching, no DB calls |

## 24. Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Keyboard navigation | All status buttons reachable via Tab, activatable via Enter/Space |
| Screen reader | Status badges use aria-label (e.g., "Payment status: paid") |
| Color contrast | Status colors meet WCAG AA: paid (green #155724), failed (red #721c24), pending (blue #0c5464) |
| Touch targets | All action buttons minimum 44px |
| Mobile | Payment summary uses responsive-card layout (inherited from FRONTEND_DESIGN_SYSTEM.md) |

## 25. Analytics Events

References: PAYMENT_CATALOGUE.md PA-001 through PA-010

| Event | When | Key Properties |
|-------|------|---------------|
| PA-001: `payment_batch_created` | Batch created | method, bank, employee_count, total_amount |
| PA-002: `payment_file_generated` | File generated | format, file_size_bytes, line_count, generation_time_ms |
| PA-003: `payment_file_downloaded` | File downloaded | batch_id, downloaded_by |
| PA-004: `payment_marked_submitted` | User marks submitted | batch_id, time_since_generation_hours |
| PA-005: `payment_employee_paid` | Individual paid | method, amount_tier, time_since_submission_hours |
| PA-006: `payment_employee_failed` | Individual failed | failure_reason_category, bank, amount |
| PA-007: `payment_retry_initiated` | Retry started | retry_count, correction_type |
| PA-008: `payment_reversal_initiated` | Reversal started | amount, reason_category, time_since_payment_hours |
| PA-009: `payment_batch_completed` | Batch completed | total_time_hours, success_rate, total_amount |
| PA-010: `payment_batch_partial` | Batch partial | failed_count, failed_amount, failure_categories |

## 26. Audit Events

| Event | Actor | Data Recorded |
|-------|-------|--------------|
| `payment.batch.created` | Owner/Officer | batch_id, method, bank, employee_count, total_amount, IP |
| `payment.file.generated` | Owner/Officer | batch_id, format, file_path, line_count, IP |
| `payment.file.downloaded` | Owner/Officer | batch_id, file_path, IP |
| `payment.batch.submitted` | Owner/Officer | batch_id, notes, IP |
| `payment.employee.paid` | Owner/Officer | payslip_id, amount, confirmation_number, IP |
| `payment.employee.failed` | Owner/Officer | payslip_id, failure_reason, IP |
| `payment.retry.initiated` | Owner/Officer | payslip_id, retry_count, correction, old_account, new_account, IP |
| `payment.reversal.initiated` | Owner | payslip_id, amount, reason, adjustment_payslip_id, IP |
| `payment.batch.completed` | System | batch_id, paid_count, failed_count, skipped_count |

All audit events use the existing hash chain (AuditLog model) with `entity_type='payment'`.

## 27. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Time from approval to bank file | < 5 minutes | Analytics: time between payroll.locked and file.generated |
| Payment success rate | > 95% | PA-009: success_rate in batch completion event |
| Retry success rate | > 80% | PA-007: retry outcomes (paid vs. failed again) |
| Time to resolve failures | < 48 hours | Analytics: time between first failure and resolution |
| Reversal rate | < 1% | PA-008: reversals / total payments |
| Bank file re-generation rate | < 5% | PA-002: file generations per batch (should be 1) |

## 28. Acceptance Tests

| # | Test | Steps | Expected Result |
|---|------|-------|----------------|
| AT-04-01 | Generate bank file from locked payroll | Lock payroll → generate bank file | File contains all employees, amounts match payslips, status = file_generated |
| AT-04-02 | Mark payments as paid | Generate file → mark 3 employees as paid | 3 payslips show payment_status = paid, batch shows paid_count = 3 |
| AT-04-03 | Handle partial failure | Mark 2 as paid, 1 as failed | Batch status = partial, failed employee shows failure reason |
| AT-04-04 | Retry failed payment | Mark as failed → correct account → retry | payment_status = retry, retry_count = 1, included in next file |
| AT-04-05 | Retry limit enforcement | Fail payment 3 times, attempt 4th retry | Error: "Maximum retries reached", status = failed_permanent |
| AT-04-06 | Reversal creates adjustment | Reverse a paid payment | Original stays as reversed, new adjustment payslip created, audit log records both |
| AT-04-07 | Cash payment flow | Select cash → generate register → mark paid | Cash register PDF generated, no bank file, status lifecycle works |
| AT-04-08 | Cannot reopen payroll | Attempt to modify locked payroll via payment | Error: "Payroll is locked. Use retry or reversal for corrections." |
| AT-04-09 | Bank file validation blocks bad accounts | Employee with invalid account number | Validation error before file generation, file not created |
| AT-04-10 | Tenant isolation | Company A cannot see Company B's payments | API returns 404 for cross-tenant batch access |
| AT-04-11 | Concurrent file generation | Two users try to generate file simultaneously | Second request gets 409 conflict |
| AT-04-12 | Batch completion detection | All employees paid or resolved | Batch status auto-updates to completed |

## 29. Rollout Strategy

| Phase | Scope | Duration |
|-------|-------|----------|
| Phase 1 | Bank file generation + download + mark paid/failed | 1 week |
| Phase 2 | Retry workflow + validation improvements | 3 days |
| Phase 3 | Cash payment flow + register PDF | 2 days |
| Phase 4 | Reversal workflow + adjustment payslips | 3 days |
| Phase 5 | Reconciliation (bank statement import) | 1 week (future) |

Phase 1 is the MVP — it replaces the current "download bank file and hope" workflow with proper status tracking.

## 30. Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| PRD-03 (Approve & Lock) | ✅ Complete | Entry criteria: payroll must be locked |
| PAYMENT_CATALOGUE.md | ✅ Complete | All definitions referenced by ID |
| bank_file.py | ✅ Exists | Bank file generation already works |
| Payslip.payment_status | ✅ Exists | Column already in DB (migration d2e3f4a5b6c7) |
| PayrollRun.disbursement_status | ✅ Exists | Column already in DB (migration o4p5q6r7s8t9) |
| PRD-05 (Generate Payslips) | ⏳ Pending | Payslip release gated on payment status |
| PRD-06 (ERCA Filing) | ⏳ Pending | ERCA report includes only paid employees |

## 31. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Bank file format varies by bank | File rejected by bank portal | bank_file.py already supports 10 banks, but formats may change — validation should be configurable |
| Owner forgets to mark payments | Status stuck in "submitted" | PN-003 reminder after 48 hours, auto-escalation after 7 days |
| Double upload (file uploaded twice) | Duplicate payments | Bank-side protection (bank rejects duplicate transactions), system-side: track bank_reference |
| Reversal abuse | Silent money movement | Reversal requires reason, audit log, IP tracking, owner-only permission |
| Account number errors | Failed payments, employee dissatisfaction | Pre-validation in bank_file.py, account change detection from previous month |
| Partial bank processing | Some lines succeed, some fail | Per-employee status tracking, not per-file |

## 32. Future Extensions

| Extension | Description | Priority |
|-----------|-------------|----------|
| Bank API integration | Direct submission to bank portal (no manual upload) | Medium |
| Auto-reconciliation | Import bank statement CSV, auto-match payments | Medium |
| Payment scheduling | Schedule payment for specific date | Low |
| Multi-currency support | USD payments for expat employees | Low |
| Payment approval workflow | Separate approval for payment (vs. payroll approval) | Low |
| Employee notification on payment | WhatsApp/SMS when salary is deposited | Medium |
| Payment dashboard | Analytics: success rates, failure patterns, bank performance | Medium |
| Mobile money integration | Telebirr, M-Pesa bulk payments | High (for Ethiopian market) |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
