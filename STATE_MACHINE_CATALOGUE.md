# State Machine Catalogue
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 13)
**Rule:** Every PRD references these state machines by ID. No PRD redefines them.

---

## SM-001: PayrollRun

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
  ↓ (archive after retention)
archived
```

### Transitions

| From | To | Trigger | Actor | Reversible? |
|------|-----|---------|-------|-------------|
| draft | review | Generate draft | Payroll Officer | Yes (delete draft) |
| review | pending_approval | Submit for approval | Payroll Officer | Yes (return to draft) |
| pending_approval | processing | Approve | Owner | No |
| processing | completed | All outputs generated | System | No |
| processing | failed | Calculation error | System | Yes (retry) |
| completed | locked | Lock | Owner | No |
| locked | archived | Retention period expired | System | No |
| failed | processing | Retry | Payroll Officer | Yes |

### Forbidden Transitions
- `locked` → any (immutable)
- `completed` → `draft` (must create correction run)
- `archived` → any (immutable)

### Fields That Change Per State

| State | Set Fields |
|-------|-----------|
| draft | created_at, created_by, period, source |
| review | validation_results, crosscheck_results, comparison |
| pending_approval | submitted_at, submitted_by |
| processing | approved_at, approved_by, approval_ip |
| completed | gross, tax, pension_employee, pension_employer, net |
| locked | locked_at, locked_by, disbursement_status |
| failed | error_message, failed_at |

---

## SM-002: Payslip

```
not_generated
  ↓ (generation starts)
generating
  ↓ (success)
generated
  ↓ (failure)
failed
```

### Payment Sub-State

```
pending_bank_clearance
  ↓ (bank rejects)
bank_rejected
  ↓ (corrected)
corrected
  ↓ (confirmed)
paid
```

### Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| not_generated | generating | PayrollRun enters processing | System |
| generating | generated | PDF generated successfully | System |
| generating | failed | PDF generation error | System |
| failed | generating | Retry | System |
| pending_bank_clearance | bank_rejected | Bank rejects payment | System/User |
| pending_bank_clearance | paid | Payment confirmed | User |
| bank_rejected | corrected | Account fixed, re-generated | User |
| corrected | paid | Payment confirmed | User |

---

## SM-003: Employee

```
draft
  ↓ (save)
active
  ↓ (deactivate)
suspended
  ↓ (reactivate)
active
  ↓ (terminate)
terminated
  ↓ (archive after retention)
archived
  ↓ (rehire)
active
```

### Transitions

| From | To | Trigger | Actor | Reversible? |
|------|-----|---------|-------|-------------|
| draft | active | Save employee | HR | Yes (delete) |
| active | suspended | Deactivate | HR/Admin | Yes (reactivate) |
| suspended | active | Reactivate | HR/Admin | Yes |
| active | terminated | Terminate | HR/Admin | Yes (rehire) |
| terminated | active | Rehire | HR/Admin | — |
| terminated | archived | Retention expired | System | No |
| archived | active | Rehire | HR/Admin | — |

### Forbidden Transitions
- `archived` → `draft` (must rehire to active)
- `draft` → `terminated` (must activate first)

---

## SM-004: Leave Request

```
draft
  ↓ (submit)
pending
  ↓ (approve)
approved
  ↓ (dates pass)
taken
  ↓ (close)
closed

pending
  ↓ (reject)
rejected

approved
  ↓ (cancel)
cancelled
```

### Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| draft | pending | Submit request | Employee |
| pending | approved | Approve | Manager/HR |
| pending | rejected | Reject | Manager/HR |
| approved | taken | Leave dates pass | System |
| approved | cancelled | Cancel | Employee |
| taken | closed | Period ends | System |
| rejected | pending | Resubmit | Employee |

---

## SM-005: Overtime Entry

```
draft
  ↓ (submit)
pending_approval
  ↓ (approve)
approved
  ↓ (included in payroll)
processed

pending_approval
  ↓ (reject)
rejected
```

### Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| draft | pending_approval | Submit | Employee/Manager |
| pending_approval | approved | Approve | Manager |
| pending_approval | rejected | Reject | Manager |
| approved | processed | Payroll calculated | System |
| rejected | pending_approval | Resubmit | Employee |

---

## SM-006: Final Settlement

```
draft
  ↓ (calculate)
calculated
  ↓ (approve)
approved
  ↓ (include in payroll)
paid
```

### Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| draft | calculated | Calculate settlement | HR/System |
| calculated | approved | Approve | Owner |
| approved | paid | Included in payroll run | System |

---

## SM-007: Filing Record

```
pending
  ↓ (file)
filed
  ↓ (confirm)
confirmed
```

### Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| pending | filed | Submit to ERCA/MOLSA | Accountant |
| filed | confirmed | Enter confirmation number | Accountant |

---

## SM-008: Profile Change Request

```
draft
  ↓ (submit)
pending
  ↓ (approve)
approved
  ↓ (apply)
applied

pending
  ↓ (reject)
rejected
```

### Transitions

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| draft | pending | Submit request | Employee |
| pending | approved | Approve | HR |
| pending | rejected | Reject | HR |
| approved | applied | Changes applied | System |

---

*State Machine Catalogue version: 1.0*
*8 state machines defined. Every PRD references by ID.*
