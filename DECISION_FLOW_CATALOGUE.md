# Decision Flow Catalogue
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** How the engine thinks — system decision logic for every major workflow
**Audience:** Engineers, QA, auditors

---

## How to Read This Document

Every major workflow has a decision flow. These are not user flows — they are **system decision logic**. When the system needs to decide what to do, it follows these flows.

---

## DF-001: Payroll Approval Decision

```
Owner taps "Approve Payroll"
  ↓
Are all BLOCK-severity validations resolved?
  ├─ No → REJECT: "Cannot approve. {count} blocking issues remain."
  │         Show list of unresolved BLOCKs.
  └─ Yes ↓
Are all FLAG-severity validations acknowledged?
  ├─ No → SHOW: "Warning: {count} unacknowledged flags."
  │         Require acknowledgment with reason.
  └─ Yes ↓
Do all crosschecks pass?
  ├─ No → REJECT: "Crosscheck failed: {check} — expected {expected}, got {actual}"
  └─ Yes ↓
Is the confidence score ≥ 80%?
  ├─ No → WARN: "Confidence score is {score}%. Proceed with caution."
  │         Allow override with acknowledgment.
  └─ Yes ↓
Is the owner authenticated (password/MFA)?
  ├─ No → REQUIRE: Password confirmation.
  └─ Yes ↓
APPROVE:
  1. Set PayrollRun.status = processing
  2. Freeze calculation snapshot on each Payslip
  3. Set PayrollRun.status = completed
  4. Lock PayrollRun (status = locked, locked_at, locked_by)
  5. Create AuditLog entry
  6. Trigger: bank file generation, ERCA report, payslip generation
```

---

## DF-002: Payment Processing Decision

```
Payment batch created
  ↓
Validate all employee bank accounts
  ↓
For each employee:
  ↓
  Is bank account valid?
    ├─ No → BLOCK: "Invalid account: {account}. Expected: {format}"
    │         Employee excluded from batch.
    └─ Yes ↓
  Is net pay positive?
    ├─ No → BLOCK: "Negative net pay: {amount}"
    │         Employee excluded from batch.
    └─ Yes ↓
  Is account number duplicate?
    ├─ Yes → BLOCK: "Account {account} assigned to multiple employees"
    └─ No ↓
  Did account change from previous month?
    ├─ Yes → FLAG: "Account changed from {old} to {new}. Verify."
    └─ No ↓
  INCLUDE in batch.
  ↓
Generate bank file
  ↓
User uploads to bank portal
  ↓
User marks as "Submitted"
  ↓
For each employee (after bank processes):
  ↓
  Did payment succeed?
    ├─ Yes → Set payment_status = paid
    └─ No → Set payment_status = failed
             Record failure reason
             ↓
             Is retry_count < 3?
               ├─ Yes → Allow retry
               └─ No → Set status = failed_permanent
                        Notify owner: "Manual resolution required"
```

---

## DF-003: Termination Settlement Decision

```
HR initiates termination
  ↓
What is the termination reason?
  ├─ Resignation → Severance = 0
  ├─ Termination with cause → Severance = 0
  ├─ Redundancy → Calculate severance
  ├─ Retirement → Calculate severance
  └─ End of contract → Severance = 0
  ↓
Calculate settlement:
  ↓
  Outstanding salary = prorated to last working day
  ↓
  Severance eligible?
    ├─ Yes → Severance = years × 1 month salary
    │         Cap at 12 months maximum
    └─ No → Severance = 0
  ↓
  Leave encashment = unused annual leave × (monthly_salary / 26)
  ↓
  Total earnings = outstanding + severance + encashment
  ↓
  Pension deduction = outstanding_salary × 7% (NOT on severance)
  ↓
  Tax on settlement = progressive_brackets(total_earnings − pension)
  ↓
  Pending deductions = active loans + cost_sharing
  ↓
  Net settlement = total_earnings − pension − tax − pending_deductions
  ↓
  Is net settlement negative?
    ├─ Yes → WARN: "Settlement is negative. Review deductions."
    │         Owner must approve negative settlement.
    └─ No → Continue
  ↓
  Password confirmation required?
    ├─ Yes → Verify password
    └─ No → Error
  ↓
  CREATE settlement record
  SOFT-DELETE employee
  DEACTIVATE pending deductions
  CREATE audit log entry
```

---

## DF-004: Leave Request Decision

```
Employee submits leave request
  ↓
Is leave type valid?
  ├─ No → REJECT: "Invalid leave type"
  └─ Yes ↓
Is end date ≥ start date?
  ├─ No → REJECT: "End date must be after start date"
  └─ Yes ↓
Calculate requested days (excluding weekends and holidays)
  ↓
Is leave balance sufficient?
  ├─ No → REJECT: "Insufficient balance. Available: {available}, Requested: {requested}"
  └─ Yes ↓
Is this a special leave (≤3 days)?
  ├─ Yes → AUTO-APPROVE
  └─ No → Send to manager for approval
           ↓
           Manager approves?
             ├─ Yes → Set status = approved
             │         Deduct from balance
             │         Notify employee
             └─ No → Set status = rejected
                      Notify employee with reason
```

---

## DF-005: Correction Run Decision

```
User initiates correction
  ↓
Is the original payslip locked?
  ├─ No → REJECT: "Original payslip must be locked"
  └─ Yes ↓
Is the correction reason ≥20 characters?
  ├─ No → REJECT: "Reason too short"
  └─ Yes ↓
Is the adjustment amount non-zero?
  ├─ No → REJECT: "Adjustment must be non-zero"
  └─ Yes ↓
Is the adjustment amount ≤ original amount?
  ├─ No → REJECT: "Cannot exceed original"
  └─ Yes ↓
CREATE adjustment payslip:
  - type = 'adjustment'
  - original_payslip_id = original
  - amount = adjustment (positive or negative)
  - reason = correction reason
  ↓
CREATE audit log entry
  ↓
Include in next payroll run as line item
```

---

## DF-006: ERCA Filing Decision

```
User requests ERCA report
  ↓
Is the payroll locked?
  ├─ No → REJECT: "Payroll must be locked"
  └─ Yes ↓
Do all employees have TIN?
  ├─ No → BLOCK: "{count} employees missing TIN"
  │         List employees without TIN.
  └─ Yes ↓
Is company TIN present?
  ├─ No → BLOCK: "Company TIN required"
  └─ Yes ↓
Are report totals consistent?
  ├─ No → BLOCK: "Totals mismatch"
  └─ Yes ↓
Is this period already filed?
  ├─ Yes → WARN: "Already filed on {date}. Use amendment flow."
  └─ No ↓
GENERATE report using configured template
  ↓
User downloads report
  ↓
User uploads to ERCA portal (external)
  ↓
User enters confirmation number
  ↓
CREATE FilingRecord:
  - filing_type = erca
  - period = {period}
  - filed_at = now
  - confirmation_number = {number}
```

---

## DF-007: Hash Chain Verification Decision

```
Verify chain requested
  ↓
Load all AuditLog entries for company (ordered by id)
  ↓
For each entry:
  ↓
  Is this the first entry?
    ├─ Yes → Is previous_hash null?
    │         ├─ Yes → OK
    │         └─ No → FAIL: "First entry has non-null previous_hash"
    └─ No → Does previous_hash match previous entry's hash?
              ├─ Yes → OK
              └─ No → FAIL: "previous_hash mismatch with entry {id}"
  ↓
  Does computed hash match stored hash?
    ├─ Yes → OK
    └─ No → FAIL: "hash does not match computed value"
  ↓
Report:
  - Total entries: {count}
  - Verified: {count}
  - Broken: {count}
  - Status: intact / compromised
```

---

## DF-008: Profile Change Decision

```
Employee submits profile change
  ↓
Which fields are being changed?
  ├─ Non-sensitive (phone, email, address) → Save directly
  └─ Sensitive (bank account, salary, department) → Create change request
  ↓
For sensitive fields:
  ↓
  Is there already a pending request for this field?
    ├─ Yes → REJECT: "Change for {field} already pending"
    └─ No ↓
  CREATE ProfileChangeRequest (status = pending)
  NOTIFY HR officer
  ↓
HR reviews:
  ├─ Approve → Apply change to Employee record
  │            Set request status = completed
  │            Notify employee
  └─ Reject → Set request status = rejected
              Notify employee with reason
```

---

## DF-009: Compliance Deadline Decision

```
Daily scheduled task runs
  ↓
For each filing type (ERCA, Pension, PSSA):
  ↓
  Is there an unfiled period?
    ├─ No → Skip
    └─ Yes ↓
  Calculate days until deadline
  ↓
  Days remaining:
    ├─ >7 days → No notification
    ├─ 7 days → Send N-06-02 (reminder)
    ├─ 2 days → Send N-06-04 (urgent)
    ├─ 0 days → Send N-06-06 (critical)
    └─ <0 days → Mark as OVERDUE
                   Send critical notification
```

---

## DF-010: PDF Generation Decision

```
Generate payslip PDF requested
  ↓
Is the payroll locked?
  ├─ No → REJECT: "Payroll must be locked"
  └─ Yes ↓
Does the payslip have all required values?
  ├─ No → REJECT: "Missing values: {fields}"
  └─ Yes ↓
Is the font file installed?
  ├─ No → REJECT: "NotoSansEthiopic font missing"
  └─ Yes ↓
Is there sufficient disk space?
  ├─ No → WARN: "Low disk space"
  └─ Yes ↓
Claim 'generating' status (atomic)
  ↓
Did we win the claim?
  ├─ No → Wait for other generation (poll up to5s)
  └─ Yes ↓
Generate PDF with ReportLab
  ↓
Success?
  ├─ Yes → Save file, set status = generated
  └─ No → Set status = failed, retry up to2 times
```

---

*Decision Flow Catalogue v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
