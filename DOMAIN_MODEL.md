# Domain Model
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** Business concepts and their relationships — UML for accountants
**Audience:** Everyone — engineers, product, sales, accountants, auditors

---

## What Is This Document?

This is not a database schema. It's a **business concept map**. It shows how the system's core entities relate to each other in business terms.

If you understand this document, you understand the system.

---

## Core Concepts

```
┌─────────────────────────────────────────────────────────────┐
│                        COMPANY                               │
│  The employer. Everything belongs to a company.              │
│  Has: name, TIN, policies, employees                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ employs
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        EMPLOYEE                              │
│  A person who works for the company.                         │
│  Has: name, salary, department, bank account, TIN            │
│  Lifecycle: active → suspended → terminated → archived       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ appears in
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      PAYROLL RUN                             │
│  A monthly calculation of what everyone is owed.             │
│  Contains: many payslips, one per employee                   │
│  Lifecycle: draft → review → approved → locked               │
│  Once locked: IMMUTABLE                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ contains
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        PAYSLIP                               │
│  One employee's pay for one month.                           │
│  Shows: gross, pension, tax, net, evidence                   │
│  Has: PDF, acknowledgment status, payment status             │
│  Can be: regular or adjustment (correction)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ triggers
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     PAYMENT BATCH                            │
│  A group of payments to be processed together.               │
│  Contains: many payment lines, one per employee              │
│  Lifecycle: draft → file_generated → submitted → completed   │
│  Can have: partial failures (some paid, some failed)         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ produces
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      BANK FILE                               │
│  A file uploaded to the bank portal for bulk payment.        │
│  Contains: account numbers, amounts, narratives              │
│  Format: CSV or XLSX, bank-specific                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Relationship Diagram

```
COMPANY
  │
  ├── has many → EMPLOYEE
  │                 │
  │                 ├── has many → PAYSLIP
  │                 │                │
  │                 │                ├── belongs to → PAYROLL RUN
  │                 │                │
  │                 │                ├── has → PAYMENT STATUS
  │                 │                │
  │                 │                ├── has → PDF
  │                 │                │
  │                 │                └── has → ACKNOWLEDGMENT
  │                 │
  │                 ├── has many → LEAVE
  │                 │
  │                 ├── has many → OVERTIME ENTRY
  │                 │
  │                 ├── has → LEAVE BALANCE
  │                 │
  │                 ├── has → BANK ACCOUNT (encrypted)
  │                 │
  │                 ├── has → TIN (encrypted)
  │                 │
  │                 └── has → PROFILE CHANGE REQUEST
  │
  ├── has many → PAYROLL RUN
  │                 │
  │                 ├── contains many → PAYSLIP
  │                 │
  │                 ├── has → VALIDATION RESULTS
  │                 │
  │                 ├── has → PAYMENT BATCH
  │                 │
  │                 └── has → FILING RECORDS
  │
  ├── has → TAX RULES (configurable, versioned)
  │
  ├── has → REPORT TEMPLATES (configurable)
  │
  ├── has → SETTINGS (policies, deadlines)
  │
  └── has → AUDIT LOG (every action recorded)
```

---

## Key Relationships in Plain English

### A Company has Employees
The company hires employees. Each employee belongs to exactly one company. When the company is deleted, employees are preserved (soft-delete).

### An Employee has Payslips
Every month, the employee gets a payslip showing how much they earned and how much was deducted. The payslip is created when payroll is calculated and frozen when payroll is approved.

### A Payroll Run contains Payslips
A payroll run is a monthly calculation for all employees. It creates one payslip per employee. Once approved and locked, no payslip can be changed.

### A Payslip has Evidence
Every number on the payslip (gross, pension, tax, net) has evidence: the formula, the inputs, the law citation, and the timestamp. This is what makes the system trustworthy.

### A Payment Batch processes Payslips
After payroll is locked, a payment batch is created to actually pay the employees. The batch generates a bank file and tracks which payments succeeded and which failed.

### A Filing Record tracks Government Reports
After payroll is locked, ERCA and pension reports are generated. The filing record tracks when each report was filed and with what confirmation number.

### A Correction creates an Adjustment Payslip
If an error is discovered after payroll is locked, a correction creates an adjustment payslip. The original payslip is never modified. The adjustment appears in the next payroll run.

### An Employee can Request Leave
Leave requests go through a manager approval workflow. Approved leave affects payroll (unpaid leave reduces salary).

### An Employee can View their own Portal
The employee portal shows payslips, leave balance, profile, and tax certificates. The employee can only see their own data.

---

## Business Concepts Explained

### What is "Gross Salary"?
The total amount the employee earns before any deductions.
```
Gross = Basic Salary + Allowances
```

### What is "Pension"?
A mandatory retirement contribution.
```
Employee Pension = Basic Salary × 7% (deducted from pay)
Employer Pension = Basic Salary × 11% (paid by employer, not deducted)
```

### What is "Taxable Income"?
The amount on which income tax is calculated.
```
Taxable Income = Gross Salary − Employee Pension
```

### What is "Income Tax"?
A progressive tax on taxable income. Higher income = higher rate.
```
0–2,000 ETB: 0%
2,001–4,000: 15%
4,001–7,000: 20%
7,001–10,000: 25%
10,001–14,000: 30%
14,001+: 35%
Minus personal relief: ETB 150/month
```

### What is "Net Pay"?
The amount the employee actually receives.
```
Net Pay = Gross − Pension − Tax − Other Deductions
```

### What is a "Payroll Run"?
A monthly calculation that produces payslips for all employees. It goes through states:
1. **Draft** — being prepared
2. **Review** — ready for validation
3. **Pending Approval** — submitted to owner
4. **Processing** — approved, generating outputs
5. **Completed** — all outputs generated
6. **Locked** — IMMUTABLE, cannot be changed

### What is a "Payment Batch"?
A group of payments processed together. Created from a locked payroll run. Can have partial failures (some employees paid, some failed).

### What is an "Adjustment Payslip"?
A correction to a locked payroll. Instead of modifying the original (which is immutable), the system creates an adjustment that records the difference. The adjustment appears in the next payroll run.

### What is "Evidence"?
Proof that a number is correct. Every financial number in the system has:
- **Source**: where the inputs came from
- **Formula**: how it was calculated
- **Law**: what legal rule applies
- **Timestamp**: when it was calculated
- **Approver**: who verified it

### What is a "Filing Record"?
A record that a government report was filed. Contains: filing type (ERCA/Pension), period, filed date, filed by, confirmation number.

### What is the "Hash Chain"?
A tamper-evident audit trail. Each audit log entry includes a hash of the previous entry. If any entry is modified, the chain breaks and the system detects it.

---

## Entity Summary

| Entity | Purpose | Key Fields | Lifecycle |
|--------|---------|------------|-----------|
| Company | The employer | name, TIN, settings | active |
| Employee | A worker | name, salary, bank, TIN | active → terminated |
| PayrollRun | Monthly calculation | period, status, totals | draft → locked |
| Payslip | One employee's pay | gross, pension, tax, net | created → locked |
| PaymentBatch | Payment processing | method, status, counts | draft → completed |
| FilingRecord | Government filing | type, period, confirmation | filed → amended |
| Leave | Leave request | type, dates, status | pending → approved |
| OvertimeEntry | Overtime hours | date, hours, type | pending → approved |
| FinalSettlement | Termination pay | earnings, deductions, net | pending → paid |
| AuditLog | Action record | action, user, hash | immutable |
| TaxRule | Configurable rules | rules_json, effective dates | versioned |
| Notification | User alert | message, type, read status | created → read |

---

*Domain Model v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
