# Payment Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** PRD-04, PRD-05, PRD-06, PRD-08
**Rule:** Every PRD that touches money movement references these definitions by ID. No PRD redefines payment concepts.

---

## What This Catalogue Covers

This catalogue defines the payment domain — the lifecycle from "payroll approved" to "employee received money." It is deliberately separated from payroll calculation (PRD-02) and payroll approval (PRD-03) because payment failures must never reopen payroll.

**Core principle:** Payroll is a calculation. Payment is an action. They live in different domains.

---

## PM-001: Payment Methods

| ID | Method | Code | Description | Status |
|----|--------|------|-------------|--------|
| PM-001-A | Bank Transfer | `bank` | Bulk file uploaded to bank portal (CBE, Dashen, Awash, etc.) | Active |
| PM-001-B | Cash | `cash` | Physical cash disbursement with signed receipt | Active |
| PM-001-C | Cheque | `cheque` | Company cheque issued to employee | Active |
| PM-001-D | Mobile Money | `mobile` | Telebirr, M-Pesa, CBE Birr | Future |
| PM-001-E | Mixed | `mixed` | Employee receives via multiple methods in same period | Future |

### Rules

- Each employee has exactly one payment method per payroll run.
- Payment method is stored on the `Payslip` record (snapshot at time of payroll generation), not on `Employee`. If an employee changes banks between months, the payslip reflects the method at payroll time.
- Cash and cheque payments still require a payslip record — they are not exempt from the payment lifecycle.
- The bank file generator (`bank_file.py`) handles `bank` and `mobile` methods. Cash and cheque methods skip file generation but still follow the payment status lifecycle.

---

## PS-001: Payment Statuses (Per Employee)

Each `Payslip` record has an independent payment status. Employees within the same payroll run can be at different payment stages.

```
pending
  ↓ (bank file generated)
file_generated
  ↓ (file uploaded to bank portal)
submitted
  ↓ (bank processes payment)
paid
  ↓ (reversal requested)
reversed

Alternative paths:

pending → skipped        (employee excluded from this run)
file_generated → failed  (bank rejected this line)
failed → retry           (corrected and re-submitted)
retry → paid             (successful on retry)
retry → failed           (failed again, needs manual intervention)
```

### Status Definitions

| Status | Code | Meaning | Who Sets It |
|--------|------|---------|-------------|
| Pending | `pending` | Payslip created, payment not yet initiated | System (on payroll approval) |
| File Generated | `file_generated` | Included in a bank file download | System (on file generation) |
| Submitted | `submitted` | File uploaded to bank portal (manual confirmation) | User (marks as submitted) |
| Paid | `paid` | Employee received funds | User (marks as paid) or Bank confirmation import |
| Failed | `failed` | Bank rejected this payment line | User (marks as failed) or Bank confirmation import |
| Retry | `retry` | Corrected and queued for re-submission | System (on correction) |
| Reversed | `reversed` | Payment was made but needs to be reversed | User (initiates reversal) |
| Skipped | `skipped` | Employee intentionally excluded from this run | User (marks as skipped) |

### Forbidden Transitions

- `paid` → `pending` (cannot un-pay; must create adjustment payslip)
- `reversed` → `paid` (must create new payment)
- `skipped` → `paid` (must create adjustment payslip)

### Fields That Change Per Status

| Status | Fields Set |
|--------|-----------|
| pending | `payment_status='pending'`, `payment_status_at=now()` |
| file_generated | `payment_status='file_generated'`, `bank_file_id`, `payment_status_at=now()` |
| submitted | `payment_status='submitted'`, `bank_reference`, `submitted_by`, `submitted_at` |
| paid | `payment_status='paid'`, `paid_at`, `paid_by`, `confirmation_number` |
| failed | `payment_status='failed'`, `failure_reason`, `failed_at` |
| retry | `payment_status='retry'`, `retry_count += 1`, `retry_from_id` |
| reversed | `payment_status='reversed'`, `reversed_at`, `reversed_by`, `reversal_reason` |
| skipped | `payment_status='skipped'`, `skipped_reason` |

---

## PB-001: Payment Batch Lifecycle

A Payment Batch groups multiple payment lines into a single file or action. One payroll run produces one or more payment batches (e.g., one batch per bank).

```
draft
  ↓ (owner confirms payment details)
ready
  ↓ (file generated)
file_generated
  ↓ (user uploads to bank portal and marks as submitted)
submitted
  ↓ (bank processes)
completed
  ↓ (all lines resolved)
closed

Alternative paths:

draft → cancelled         (abandoned before generation)
file_generated → partial  (some lines paid, some failed)
partial → completed       (all failures resolved via retry or skip)
partial → closed          (remaining failures accepted as-is)
```

### Batch Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `payroll_run_id` | Integer | FK to PayrollRun |
| `company_id` | Integer | FK to Company (tenant isolation) |
| `batch_reference` | String | Human-readable (e.g., PB-2026-07-001) |
| `payment_method` | String | `bank`, `cash`, `cheque`, `mobile` |
| `bank_code` | String | `cbe`, `dashen`, `awash`, etc. (null for cash/cheque) |
| `status` | String | `draft`, `ready`, `file_generated`, `submitted`, `completed`, `partial`, `closed`, `cancelled` |
| `total_employees` | Integer | Count of payment lines |
| `total_amount` | Decimal | Sum of net pay for all lines |
| `paid_count` | Integer | Employees confirmed paid |
| `failed_count` | Integer | Employees whose payment failed |
| `pending_count` | Integer | Employees still pending |
| `file_path` | String | Path to generated bank file |
| `file_format` | String | `csv`, `xlsx` |
| `generated_at` | DateTime | When file was generated |
| `generated_by` | Integer | FK to User |
| `submitted_at` | DateTime | When user marked as submitted |
| `submitted_by` | Integer | FK to User |
| `completed_at` | DateTime | When all lines resolved |
| `notes` | Text | Free-text notes |

---

## BR-001: Bank Acknowledgement Lifecycle

The system distinguishes between four events that are often confused:

| Event | Code | Meaning | How It Happens |
|-------|------|---------|----------------|
| File Generated | `file_generated` | Bank file created and downloaded | System generates file |
| File Uploaded | `file_uploaded` | User uploaded file to bank portal | Manual (user action outside system) |
| Bank Accepted | `bank_accepted` | Bank acknowledged receipt of file | Manual confirmation or API |
| Money Transferred | `money_transferred` | Bank executed the payments | Bank confirmation import or manual |
| Employee Received | `employee_received` | Employee confirmed receipt | Employee confirmation or bank statement |

**The system tracks:** `file_generated`, `submitted` (file_uploaded), `paid` (money_transferred/employee_received).

**The system does NOT track:** `bank_accepted` separately from `submitted` — this would require bank API integration (future).

---

## RT-001: Retry Rules

When a payment fails, the system follows these rules:

| Rule | Description |
|------|-------------|
| RT-001-A | A failed payment can be retried up to **3 times** before requiring manual intervention |
| RT-001-B | Each retry creates a new entry in `PaymentRetryHistory` with reason, timestamp, and user |
| RT-001-C | Retried payments are included in the next bank file generation for the same batch |
| RT-001-D | After 3 failures, payment status becomes `failed_permanent` — requires manual resolution |
| RT-001-E | A retry can only happen from `failed` status — not from `paid` or `reversed` |
| RT-001-F | The correction that triggers a retry must be recorded (e.g., "account number corrected") |

### Retry Workflow

```
Payment failed (bank rejected line 47)
  ↓
User corrects the issue (fixes account number)
  ↓
User clicks "Retry" on the failed payment
  ↓
System sets payment_status = 'retry', retry_count += 1
  ↓
Next bank file generation includes this payment
  ↓
If paid → payment_status = 'paid'
If failed again → retry_count check:
  - retry_count < 3 → back to 'failed', user can retry again
  - retry_count >= 3 → 'failed_permanent', needs manual resolution
```

---

## RV-001: Reversal Rules

Reversals handle cases where a payment was made but needs to be undone (e.g., wrong amount, terminated employee).

| Rule | Description |
|------|-------------|
| RV-001-A | Only `paid` payments can be reversed |
| RV-001-B | Reversal requires a reason (minimum 10 characters) |
| RV-001-C | Reversal creates a `ReversalRecord` with original payment details |
| RV-001-D | Reversal does NOT modify the original payslip — it creates an adjustment payslip |
| RV-001-E | Reversal amount can be partial (e.g., overpayment correction) |
| RV-001-F | Reversal is recorded in audit log with actor, timestamp, IP, and reason |

### Reversal vs. Correction

| Scenario | Action | Creates Adjustment? |
|----------|--------|-------------------|
| Wrong amount paid | Reversal + new payment | Yes |
| Wrong account (money went to wrong person) | Reversal only | Yes |
| Employee terminated after payment | Reversal + final settlement | Yes |
| Duplicate payment | Reversal of duplicate | Yes |
| Calculation error discovered after payment | Correction run (PRD-08) | Yes, via correction run |

---

## PE-001: Payment Events

| ID | Event | Trigger | Payload |
|----|-------|---------|---------|
| PE-001 | `payment.batch.created` | PaymentBatch created | batch_id, payroll_run_id, method, bank, total_employees, total_amount |
| PE-002 | `payment.batch.file_generated` | Bank file generated | batch_id, file_path, file_format, line_count |
| PE-003 | `payment.batch.submitted` | User marks batch as submitted | batch_id, submitted_by, submitted_at |
| PE-004 | `payment.batch.completed` | All lines in batch resolved | batch_id, paid_count, failed_count, total_amount |
| PE-005 | `payment.batch.partial` | Some lines failed, batch still open | batch_id, paid_count, failed_count |
| PE-006 | `payment.employee.paid` | Individual payment confirmed | payslip_id, employee_id, amount, confirmation_number |
| PE-007 | `payment.employee.failed` | Individual payment failed | payslip_id, employee_id, amount, failure_reason |
| PE-008 | `payment.employee.retry` | Payment retry initiated | payslip_id, employee_id, retry_count, correction_reason |
| PE-009 | `payment.employee.reversed` | Payment reversed | payslip_id, employee_id, amount, reversal_reason, reversed_by |
| PE-010 | `payment.reconciliation.matched` | Bank statement matches system record | batch_id, payslip_id, bank_reference |
| PE-011 | `payment.reconciliation.mismatch` | Bank statement does not match | batch_id, expected_amount, actual_amount, bank_reference |

---

## PN-001: Payment Notifications

| ID | Name | Recipient | Trigger | Priority | Channels | Message Template |
|----|------|-----------|---------|----------|----------|-----------------|
| PN-001 | Payment Batch Created | Owner | PE-001 | High | In-app | "Payment batch {batch_ref} created for {count} employees, ETB {total}. Ready to generate bank file." |
| PN-002 | Bank File Generated | Owner | PE-002 | High | In-app | "Bank file for {batch_ref} ready to download. {count} employees, ETB {total}." |
| PN-003 | Payment Confirmation Needed | Owner | PE-005 | High | In-app, WhatsApp | "Payment batch {batch_ref}: {paid_count} paid, {failed_count} require attention." |
| PN-004 | All Payments Completed | Owner | PE-004 | Medium | In-app, WhatsApp | "All {count} employees paid for {period}. Total: ETB {total}." |
| PN-005 | Payment Failed | Payroll Officer | PE-007 | High | In-app | "Payment to {name} ({emp_id}) failed: {reason}. Retry or resolve." |
| PN-006 | Retry Limit Reached | Owner | RT-001-D | Critical | In-app, WhatsApp | "Payment to {name} failed {retry_count} times. Manual resolution required." |
| PN-007 | Payment Reversed | Owner | PE-009 | High | In-app, WhatsApp | "Payment to {name} reversed: {reason}. Amount: ETB {amount}." |

---

## PA-001: Payment Analytics Events

| ID | Event Name | Trigger | Key Properties |
|----|------------|---------|---------------|
| PA-001 | `payment_batch_created` | Batch created | method, bank, employee_count, total_amount |
| PA-002 | `payment_file_generated` | File generated | format, file_size_bytes, line_count, generation_time_ms |
| PA-003 | `payment_file_downloaded` | File downloaded | batch_id, downloaded_by |
| PA-004 | `payment_marked_submitted` | User marks submitted | batch_id, time_since_generation_hours |
| PA-005 | `payment_employee_paid` | Individual paid | method, amount_tier, time_since_submission_hours |
| PA-006 | `payment_employee_failed` | Individual failed | failure_reason_category, bank, amount |
| PA-007 | `payment_retry_initiated` | Retry started | retry_count, correction_type |
| PA-008 | `payment_reversal_initiated` | Reversal started | amount, reason_category, time_since_payment_hours |
| PA-009 | `payment_batch_completed` | Batch completed | total_time_hours, success_rate, total_amount |
| PA-010 | `payment_batch_partial` | Batch partial | failed_count, failed_amount, failure_categories |

---

## RE-001: Reconciliation Rules

Reconciliation matches bank statements against system records.

| Rule | Description |
|------|-------------|
| RE-001-A | Reconciliation is optional — system works without it |
| RE-001-B | Bank statement import supports CSV format (account, amount, reference, date) |
| RE-001-C | Matching is by account number + amount (exact match) |
| RE-001-D | Unmatched bank entries are flagged as `reconciliation_mismatch` |
| RE-001-E | Unmatched system payments are flagged as `pending_reconciliation` |
| RE-001-F | Reconciliation does not change payment status — it creates a `ReconciliationRecord` |
| RE-001-G | Manual override: user can mark a mismatch as resolved with explanation |

---

## Cross-Reference: How PRDs Use This Catalogue

| PRD | Sections That Reference This Catalogue |
|-----|---------------------------------------|
| PRD-04 | Payment Batch (PB-001), Payment Status (PS-001), Retry Rules (RT-001), Events (PE-001 through PE-009), Notifications (PN-001 through PN-007) |
| PRD-05 | Payslip release gated on PS-001 status `paid` |
| PRD-06 | ERCA filing includes only `paid` payslips |
| PRD-08 | Reversals (RV-001), Correction runs reference original batch |

---

*This document is part of the EthioPayroll product specification.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
