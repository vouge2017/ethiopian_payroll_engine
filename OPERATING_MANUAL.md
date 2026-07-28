# Operating Manual
### Ethiopian Workforce Operating System
**Version:** 1.1
**Date:** 2026-07-28
**Audience:** Engineers, QA, Product, Sales, Customer Success, Implementation, Investors

---

## Vision

> **"From the day you hire an employee until the day you pass a government audit, every workforce event happens in one trusted system."**

We don't build payroll software. We build trust between employers, employees, accountants, banks, and government.

---

## Operating Principles

1. **Single source of truth** — no duplicate entry, ever
2. **Every calculation is explainable** — formula, inputs, law, timestamp
3. **Every workflow is auditable** — who, when, what changed
4. **Automation assists; humans approve** — the system proposes, the owner decides
5. **Compliance before convenience** — if it's not legally correct, don't do it
6. **Trust over speed when they conflict** — slower and right beats fast and wrong
7. **Configuration over customization** — change values, not code
8. **Every feature must remove Excel work** — if they still need Excel, we failed

---

## Journey Map

```
JOURNEY 0: Create Company & Migrate from Excel
JOURNEY 1: Hire an Employee
JOURNEY 2: Prepare Monthly Payroll
JOURNEY 3: Approve & Lock Payroll
JOURNEY 4: Pay Employees
JOURNEY 5: File with Government (ERCA/MOLSA)
JOURNEY 6: Employee Opens Payslip
JOURNEY 7: Employee Leaves the Company
JOURNEY 8: Government Audit
JOURNEY 9: Manager Approvals & HR Lifecycle
```

### The Operating System Loop

```
PLAN → HIRE → WORK → PAY → COMPLY → AUDIT → LEARN → IMPROVE → PLAN
```

---

## Trust Architecture

```
INPUT (Employee, Attendance, Leave, Salary)
  ↓
VALIDATION (TIN, Bank, Dates, Policies)
  ↓
CALCULATION (Payroll Engine)
  ↓
CROSSCHECK (Attendance ↔ Payroll ↔ Bank ↔ ERCA ↔ Pension)
  ↓
APPROVAL (Owner with confidence score)
  ↓
LOCK (Immutable snapshot, hash-chain protected)
  ↓
OUTPUT (Payslip, Bank File, ERCA Report, Audit Package)
  ↓
EVIDENCE (Formula, Law, Timestamp, Approver)
```

Every layer adds trust. By the time output reaches the employee, it has passed through validation, calculation, crosscheck, approval, and lock. Every layer is evidenced.

---

## How Payroll Works

### Monthly Cycle

```
Day 25: Attendance closes
Day 26: Overtime approved
Day 27: Leave finalized
Day 28: Payroll draft generated
Day 28: Validation runs (BLOCK/FLAG/WARN)
Day 28: Crosschecks run (attendance, ERCA, pension, bank)
Day 29: Owner approves
Day 29: Bank file generated
Day 30: Employees paid
Day 31: ERCA filed
Day 31: Pension filed
```

### Calculation Flow

```
gross = basic_salary + allowances
pension = basic_salary × 7%
taxable = gross - pension
tax = progressive_brackets(taxable) - personal_relief
deductions = loans + cost_sharing + ...
net = gross - pension - tax - deductions
```

### What's Frozen After Approval

- PayrollRun (status, totals, approval metadata)
- Each Payslip (all calculated values)
- Calculation snapshot (exact rules used)
- Audit log entry (who, when, IP)

---

## How Approvals Work

### Single-Level Approval (Current)

```
Payroll Officer prepares draft
  ↓
Owner reviews confidence report
  ↓
Owner taps "Approve"
  ↓
System locks run, generates outputs
```

### Confidence Report

```
PAYROLL CONFIDENCE REPORT
━━━━━━━━━━━━━━━━━━━━━━━
Employees:     50
Gross:         ETB 2,145,330
Tax:           ETB 412,650
Pension:       ETB 148,173
Net:           ETB 1,584,507
━━━━━━━━━━━━━━━━━━━━━━━
✓ Attendance vs Payroll: PASSED
✓ ERCA totals match:     PASSED
✓ Pension totals match:  PASSED
✓ Bank file matches:     PASSED
━━━━━━━━━━━━━━━━━━━━━━━
Confidence: 98%
```

### What Prevents Approval

- Any BLOCK-severity validation result
- Any unresolved crosscheck failure
- Missing owner authentication

### What Can Be Overridden

- FLAG-severity validation results (with reason)
- WARNING-severity results (acknowledge)

### What Cannot Be Overridden

- BLOCK-severity results (must fix)
- Crosscheck failures (must resolve)

---

## How Audit Works

### What's Logged

Every state change: who, when, what changed, from what IP.

### What's Immutable

- AuditLog records (never updated or deleted)
- Locked PayrollRun records
- Calculation snapshots
- Filing confirmations

### Hash Chain

Each AuditLog entry includes a SHA-256 hash of: previous_hash + company_id + user_id + action + details. This creates a tamper-evident chain.

### During an Audit

```
Auditor asks: "Prove your June 2026 tax calculation for employee X."
System shows:
  - Tax breakdown (bracket-by-bracket)
  - Law citation (Proclamation 1395/2025, Art. 36(1))
  - Calculation timestamp
  - Approval record (who, when, IP)
  - Lock hash
  - ERCA filing confirmation
```

---

## How Corrections Work

### Adjustment Payslip

```
Original payslip: net = ETB 11,265 (locked, immutable)
Correction needed: forgot overtime = ETB 500
  ↓
Create adjustment payslip:
  - type: 'adjustment'
  - original_payslip_id: points to original
  - reason: "Overtime omitted from original run"
  - net: ETB 500 (the delta)
  ↓
Include in next payroll run
```

### What's Preserved

- Original payslip (immutable)
- Adjustment payslip (linked to original)
- Both in audit trail
- Both in ERCA filing (as adjustment)

---

## How Rollbacks Work

### Draft Payroll

- Can be deleted (returns to no payroll)
- Can be re-calculated (replaces draft)

### Approved Payroll

- Cannot be rolled back
- Must create correction/adjustment

### Failed Payroll

- Can be retried (re-processes)
- Error logged for investigation

---

## State Machines

See `STATE_MACHINE_CATALOGUE.md` for all 8 state machines.

Key states:

| Entity | States |
|--------|--------|
| PayrollRun | draft → review → pending_approval → processing → completed → locked |
| Employee | draft → active → suspended → terminated → archived |
| Leave | draft → pending → approved → taken → closed |
| Payslip | not_generated → generating → generated / failed |

---

## Evidence Model

See `EVIDENCE_CATALOGUE.md` for all 18 evidence definitions.

Every number displayed to a user is traceable to:
1. Source data
2. Formula
3. Law
4. Timestamp
5. Approver
6. Hash

---

## Notifications

See `NOTIFICATION_CATALOGUE.md` for all 37 notifications.

Key notifications:
- N-001: Payroll draft ready (→ Owner)
- N-005: Payslip ready (→ Employee)
- N-040: Probation ending (→ HR)
- N-060: ERCA deadline (→ Accountant)

---

## Analytics

See `ANALYTICS_CATALOGUE.md` for all 52 events.

Key events:
- AE-023: payroll.calculated
- AE-027: payroll.approved
- AE-041: payslip.viewed
- AE-100: trust_score.viewed

---

## Glossary

| Term | Definition |
|------|-----------|
| **BLOCK** | Validation severity. Must fix before proceeding. Cannot override. |
| **FLAG** | Validation severity. Can override with reason. Requires acknowledgment. |
| **WARN** | Validation severity. Informational only. |
| **Crosscheck** | Comparison of two independently-sourced numbers that should agree. |
| **Confidence Score** | Percentage based on crosscheck pass rate. |
| **Trust Score** | Company-level score based on data quality, compliance, accuracy, audit readiness. |
| **Evidence** | Proof that a number is correct: formula, inputs, law, timestamp, approver. |
| **Calculation Snapshot** | Frozen copy of rules used at calculation time. Ensures historical accuracy. |
| **Hash Chain** | Tamper-evident chain of audit log entries using SHA-256. |
| **TenantQuery** | ORM-level enforcement that every query includes company_id filter. |
| **ERCA** | Ethiopian Revenue and Customs Authority. Tax filing authority. |
| **MOLSA** | Ministry of Labor and Social Affairs. Pension authority. |
| **TIN** | Tax Identification Number. 9-10 digits. |
| **Pension (Employee)** | 7% of basic salary, deducted from gross. |
| **Pension (Employer)** | 11% of basic salary, paid by employer (not deducted). |
| **Personal Relief** | ETB 150/month, deducted from gross tax. |
| **Progressive Tax** | Tax increases with income, applied in brackets. |
| **Adjustment Payslip** | Correction to a locked payroll. Delta amount only. |

---

## Document Map

### Foundation

| Document | Purpose | Audience |
|----------|---------|----------|
| EXECUTIVE_DIRECTIVE.md | Strategic direction | Leadership |
| PRODUCT_GOVERNANCE.md | Decision-making structure | All |
| COMPANY_OPERATING_SYSTEM.md | Operating model | All |
| OPERATING_PRINCIPLES.md | Standing rules | All |
| CUSTOMER_JOURNEY_BLUEPRINT.md | Product vision (frozen) | All |
| WORKFORCE_OPERATING_SYSTEM_PRINCIPLES.md | 10 core principles (frozen) | All |

### Architecture

| Document | Purpose | Audience |
|----------|---------|----------|
| ARCHITECTURE_DECISIONS.md | 22 ADRs across 5 domains | Engineering |
| DATA_MODEL.md | Entity definitions | Engineering |
| BACKEND_ARCHITECTURE.md | API standards | Engineering |
| FRONTEND_DESIGN_SYSTEM.md | UI components | Design, Frontend |
| ENGINEERING_QUALITY_STANDARDS.md | Quality bar | Engineering, QA |

### Catalogues

| Document | Purpose | Audience |
|----------|---------|----------|
| STATE_MACHINE_CATALOGUE.md | 8 lifecycle states | Engineering, QA |
| NOTIFICATION_CATALOGUE.md | 37 notifications | Engineering, Product |
| ANALYTICS_CATALOGUE.md | 52 analytics events | Engineering, Product |
| EVIDENCE_CATALOGUE.md | 18 evidence definitions | Engineering, Compliance |
| PAYMENT_CATALOGUE.md | Payment methods, statuses, batch lifecycle | Engineering, Product |
| VALIDATION_CATALOGUE.md | 68 validation rules | Engineering, QA |
| BUSINESS_RULE_CATALOGUE.md | 115 business rules | Engineering, Product |
| PERMISSION_CATALOGUE.md | RBAC matrix (4 roles × 9 areas) | Engineering, Product |
| API_CATALOGUE.md | 45+ endpoints | Engineering |
| ERROR_CATALOGUE.md | 50+ error codes | Engineering, QA |

### Specifications

| Document | Purpose | Audience |
|----------|---------|----------|
| PRD-TEMPLATE.md | PRD structure (32 sections) | Product, Engineering |
| PRD-00 through PRD-09 | 10 journey specifications | Engineering, QA |
| EXECUTION_ROADMAP.md | Build order | All |

---

*Operating Manual version: 1.1 (updated2026-07-28)*
*This is the handbook for everyone working on the Ethiopian Workforce Operating System.*
