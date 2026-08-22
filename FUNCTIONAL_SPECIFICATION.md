# Functional Specification
### Ethiopian Workforce Operating System
**Version:** 1.0
**Date:** 2026-07-28
**Purpose:** Single functional reference — how the product behaves across all modules
**Audience:** Engineers, QA, architects, auditors, implementation partners

---

## How to Read This Document

This is not a PRD. It doesn't define what should be built — it defines **how the system works**.

Every module section follows this structure:

| Section | What It Answers |
|---------|----------------|
| **Purpose** | What this module does |
| **Inputs** | What data flows in |
| **Outputs** | What data flows out |
| **Dependencies** | What must exist before this works |
| **State Changes** | What changes when this runs |
| **Failure Modes** | What can go wrong |
| **APIs** | What endpoints support it |
| **Permissions** | Who can do what |
| **Evidence** | What proof is generated |
| **Notifications** | Who gets notified |

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACES                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Owner   │ │ Officer  │ │Accountant│ │ Employee │   │
│  │Dashboard │ │ Payroll  │ │ Filing   │ │  Portal  │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
│       │            │            │            │          │
│  ┌────┴────────────┴────────────┴────────────┴─────┐    │
│  │              AUTHENTICATION LAYER               │    │
│  │    Phone+OTP | Password | OAuth | MFA (TOTP)    │    │
│  └────────────────────┬────────────────────────────┘    │
│                       │                                 │
│  ┌────────────────────┴────────────────────────────┐    │
│  │              TENANT ISOLATION (TenantQuery)      │    │
│  │         company_id filter on every query         │    │
│  └────────────────────┬────────────────────────────┘    │
│                       │                                 │
│  ┌────────────────────┴────────────────────────────┐    │
│  │              BUSINESS LOGIC LAYER                │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐           │    │
│  │  │Company  │ │Employee │ │Payroll  │           │    │
│  │  │Setup    │ │Mgmt     │ │Engine   │           │    │
│  │  └────┬────┘ └────┬────┘ └────┬────┘           │    │
│  │       │           │           │                 │    │
│  │  ┌────┴────┐ ┌────┴────┐ ┌───┴────┐            │    │
│  │  │Approval │ │Payment  │ │Filing  │            │    │
│  │  │Engine   │ │Engine   │ │Engine  │            │    │
│  │  └────┬────┘ └────┬────┘ └───┬────┘            │    │
│  │       │           │          │                  │    │
│  │  ┌────┴───────────┴──────────┴────┐             │    │
│  │  │     EVIDENCE & AUDIT LAYER     │             │    │
│  │  │  Hash Chain | Calculation      │             │    │
│  │  │  Snapshots | Filing Records    │             │    │
│  │  └───────────────────────────────┘             │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │              DATA LAYER                         │    │
│  │  PostgreSQL (SQLite for dev)                    │    │
│  │  Encrypted fields: bank_account, tin            │    │
│  │  28 models, 295 columns                         │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Module 1: Company Setup

### Purpose
Create a company, configure policies, import employees from Excel.

### Inputs
- Company name, TIN, address, industry
- Excel/CSV file with employee data
- Policy settings (leave year start, overtime rates, pension eligibility)

### Outputs
- Company record with configured policies
- Imported employees (validated)
- Trust score (data quality assessment)

### Dependencies
- None (first module in the chain)

### State Changes
```
Company: (none) → draft → active
Employee: (none) → imported → active (or → rejected if validation fails)
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Missing TIN | Validation (VL-01-06) | User adds TIN before ERCA filing |
| Invalid phone format | Validation (VL-01-04) | User corrects phone |
| Duplicate employee_id | Validation (VL-01-03) | User resolves duplicate |
| Excel format wrong | Import validation | User downloads template, re-uploads |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/company` | Create company |
| PUT | `/api/company/settings` | Update policies |
| POST | `/api/employees/import` | Import from Excel/CSV |
| GET | `/api/employees/import/template` | Download template |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Create company | ✅ | ❌ | ❌ | ❌ |
| Configure policies | ✅ | ❌ | ❌ | ❌ |
| Import employees | ✅ | ✅ | ❌ | ❌ |

### Evidence
- EV-001: Gross Salary (basic + allowances)
- Import audit: file name, row count, success/failure count, timestamp

### Notifications
- N-010: New employee added (→ Accountant)
- N-012: TIN missing (→ HR, after7 days)

### PRD Reference
PRD-00

---

## Module 2: Employee Management

### Purpose
Create, update, and manage employee records throughout their lifecycle.

### Inputs
- Employee data (name, salary, department, position, bank, TIN, phone)
- Profile change requests (from employee portal)
- Termination requests

### Outputs
- Active employee record
- Profile change audit trail
- Termination record with settlement

### Dependencies
- Company must exist (Module 1)

### State Changes
```
Employee: draft → active → suspended → terminated → archived
Profile Change: pending → approved → completed (or → rejected)
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Duplicate phone | Validation (VL-01-05) | User changes phone |
| Invalid bank account | Validation (VL-01-07) | User corrects account |
| Employee not linked to user | Portal check (VL-09-01) | HR links employee to user |
| Sensitive field change without approval | Profile change check | Change request created |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/employees` | Create employee |
| PUT | `/api/employees/{id}` | Update employee |
| GET | `/api/employees/{id}` | Get employee detail |
| DELETE | `/api/employees/{id}` | Soft-delete |
| POST | `/api/employees/{id}/terminate` | Terminate |
| GET | `/api/portal/profile` | Employee views own profile |
| PUT | `/api/portal/profile` | Employee updates profile |
| GET | `/api/portal/dashboard` | Employee dashboard |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Create employee | ✅ | ✅ | ❌ | ❌ |
| Edit employee | ✅ | ✅ | ❌ | ❌ |
| Terminate employee | ✅ | ❌ | ❌ | ❌ |
| View own profile | ❌ | ❌ | ❌ | ✅ |
| Edit own profile | ❌ | ❌ | ❌ | ✅ (non-sensitive) |
| Approve profile change | ✅ | ❌ | ❌ | ❌ |

### Evidence
- EV-001: Gross Salary
- EV-002: Employee Pension (7%)
- Profile change audit: field, old value, new value, approver, timestamp

### Notifications
- N-014: Employee welcome (→ Employee)
- N-015: Employee terminated (→ Accountant)

### PRD Reference
PRD-01, PRD-07

---

## Module 3: Payroll Calculation

### Purpose
Calculate payroll for all employees in a period — gross, pension, tax, net.

### Inputs
- Employee records (basic salary, allowances)
- Tax rules (TaxRule model — versioned)
- Pension rates (configurable)
- Overtime entries
- Leave records (unpaid leave deduction)
- Loan deductions

### Outputs
- PayrollRun with calculated totals
- Payslip per employee with full breakdown
- Calculation snapshot (frozen rules)

### Dependencies
- Active employees (Module 2)
- Tax rules configured (TaxRule model)
- Attendance/leave data (if applicable)

### State Changes
```
PayrollRun: draft → review → pending_approval → processing → completed → locked
Payslip: (created with payroll run, values frozen at lock)
```

### Calculation Flow
```
gross = basic_salary + SUM(allowances)
pension_employee = basic_salary × 7%
pension_employer = basic_salary × 11%
taxable = gross − pension_employee
tax = progressive_brackets(taxable) − personal_relief
deductions = loans + cost_sharing + unpaid_leave
net = gross − pension_employee − tax − deductions
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Missing employee data | Validation (VL-06-02) | User adds missing data |
| Duplicate period | Validation (VL-PAY-10) | User deletes existing run |
| Negative net pay | Validation (VL-PMT-03) | User reviews deductions |
| Tax rule not found | System error | Fall back to default rules |
| Calculation error | Exception handler | Log error, mark run as failed |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/payroll` | Create payroll draft |
| GET | `/api/payroll/{id}` | Get payroll detail |
| DELETE | `/api/payroll/{id}` | Delete draft |
| GET | `/api/payroll/{id}/confidence` | Confidence report |
| GET | `/api/payroll/{id}/comparison` | Month-over-month |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Create draft | ✅ | ✅ | ❌ | ❌ |
| Edit draft | ✅ | ✅ | ❌ | ❌ |
| Delete draft | ✅ | ✅ | ❌ | ❌ |
| View summary | ✅ | ✅ | ✅ | ❌ |

### Evidence
- EV-001 through EV-008: All calculation evidence
- Calculation snapshot on each Payslip (frozen rules)

### Notifications
- N-002: Validation BLOCK (→ Officer)
- N-003: Validation FLAG (→ Officer)
- N-008: Payroll variance alert (→ Officer, if >20% change)

### PRD Reference
PRD-02, PRD-03

---

## Module 4: Approval & Locking

### Purpose
Owner reviews confidence report, approves payroll, locks it permanently.

### Inputs
- PayrollRun in `review` status
- Confidence report (crosscheck results)
- Month-over-month comparison
- Validation results (BLOCK/FLAG)

### Outputs
- Locked PayrollRun (immutable)
- Frozen Payslips (all values locked)
- Audit log entry (approval with IP, timestamp)

### Dependencies
- PayrollRun in `review` status (Module 3)
- All BLOCK-severity validations resolved
- All FLAG-severity validations acknowledged

### State Changes
```
PayrollRun: review → pending_approval → processing → completed → locked
```
**Forward only.** No rollback from locked.

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| BLOCK unresolved | Validation check | Cannot approve — must fix first |
| Crosscheck failed | Crosscheck engine | Cannot approve — must resolve |
| Concurrent approval | Optimistic locking | Second request gets409 |
| Wrong payroll approved | Password confirmation | Password required for approval |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/payroll/{id}/submit` | Submit for approval |
| POST | `/api/payroll/{id}/approve` | Approve payroll |
| POST | `/api/payroll/{id}/reject` | Reject payroll |
| GET | `/api/payroll/{id}/confidence` | Confidence report |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Submit for approval | ✅ | ✅ | ❌ | ❌ |
| Approve payroll | ✅ | ❌ | ❌ | ❌ |
| Reject payroll | ✅ | ❌ | ❌ | ❌ |

### Evidence
- Approval record: who, when, IP, confidence score
- Lock timestamp
- Hash chain entry

### Notifications
- N-001: Payroll draft ready (→ Owner)
- N-004: Payroll approved (→ Officer)
- N-007: Approval overdue (→ Owner, after2 days)

### PRD Reference
PRD-03

---

## Module 5: Payment Processing

### Purpose
Transform approved payroll into successful employee payments.

### Inputs
- Locked PayrollRun
- Employee bank accounts
- Payment method (bank, cash, cheque)

### Outputs
- PaymentBatch with status tracking
- Bank file (CSV/XLSX)
- Per-employee payment status
- Retry history for failed payments

### Dependencies
- PayrollRun locked (Module 4)
- Employees have valid bank accounts

### State Changes
```
PaymentBatch: draft → ready → file_generated → submitted → completed / partial
Payslip.payment_status: pending → file_generated → submitted → paid / failed → retry
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Invalid bank account | Validation (VL-PMT-02) | User corrects account |
| Bank rejects payment | User marks as failed | Retry (max3 times) |
| Duplicate bank account | Validation (VL-PMT-04) | User resolves |
| Account changed from previous month | Validation (VL-PMT-05) | User verifies |
| Retry limit exceeded | Validation (VL-PMT-08) | Manual resolution |
| Payment reversal needed | Reversal workflow | Creates adjustment payslip |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/payroll/{id}/payment-batch` | Create batch |
| POST | `/api/payment-batch/{id}/generate` | Generate bank file |
| GET | `/api/payment-batch/{id}/download` | Download file |
| POST | `/api/payment-batch/{id}/submit` | Mark submitted |
| POST | `/api/payment-batch/{id}/mark-paid` | Bulk mark paid |
| POST | `/api/payment-batch/{id}/mark-failed` | Mark failed |
| POST | `/api/payslip/{id}/retry` | Retry payment |
| POST | `/api/payslip/{id}/reverse` | Reverse payment |
| GET | `/api/payroll/{id}/payments` | Payment summary |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Generate bank file | ✅ | ✅ | ❌ | ❌ |
| Download bank file | ✅ | ✅ | ❌ | ❌ |
| Mark as submitted | ✅ | ✅ | ❌ | ❌ |
| Mark as paid (bulk) | ✅ | ❌ | ❌ | ❌ |
| Retry payment | ✅ | ✅ | ❌ | ❌ |
| Reverse payment | ✅ | ❌ | ❌ | ❌ |

### Evidence
- EV-017: Net Pay (payment evidence)
- Payment batch: total, paid count, failed count, file reference
- Retry history: correction reason, timestamp, user

### Notifications
- PN-001: Payment batch created (→ Owner)
- PN-002: Bank file generated (→ Owner)
- PN-003: Payment confirmation needed (→ Owner)
- PN-005: Payment failed (→ Officer)
- PN-006: Retry limit reached (→ Owner)

### PRD Reference
PRD-04

---

## Module 6: Government Filing

### Purpose
Generate ERCA tax reports, pension reports, and track filing status.

### Inputs
- Locked PayrollRun with paid payslips
- Company TIN
- Configurable report templates

### Outputs
- ERCA report (.xlsx)
- Pension report (.xlsx)
- FilingRecord per filing type per period
- Deadline tracking with notifications

### Dependencies
- PayrollRun locked (Module 4)
- Employees have TINs
- Company has TIN

### State Changes
```
FilingRecord: (none) → filed → amended (if correction needed)
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Missing TIN | Validation (VL-FL-01) | User adds TIN |
| Company TIN missing | Validation (VL-FL-07) | User adds company TIN |
| Report totals mismatch | Validation (VL-FL-03) | Investigate discrepancy |
| Already filed | Validation (VL-FL-08) | Use amendment flow |
| Deadline approaching | Scheduled check | Send notification |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/filing/{period}/status` | Filing status |
| GET | `/api/filing/{period}/{type}/download` | Download report |
| POST | `/api/filing/{period}/{type}/mark-filed` | Mark as filed |
| GET | `/api/filing/history` | Filing history |
| POST | `/api/filing/{period}/{type}/validate` | Validate data |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| View filing center | ✅ | ✅ | ✅ | ❌ |
| Download report | ✅ | ✅ | ✅ | ❌ |
| Mark as filed | ✅ | ❌ | ✅ | ❌ |
| Amend filing | ✅ | ❌ | ✅ | ❌ |

### Evidence
- FilingRecord: filing_type, period, filed_at, filed_by, confirmation_number
- ERCA report evidence: total gross, tax, pension, net per employee

### Notifications
- N-06-01: Report ready (→ Accountant)
- N-06-02: ERCA deadline in7 days (→ Owner)
- N-06-04: ERCA deadline in2 days (→ Owner)
- N-06-06: Deadline today (→ Owner)
- N-06-07: Filing completed (→ Owner)

### PRD Reference
PRD-05

---

## Module 7: Payslip Generation

### Purpose
Generate professional, bilingual payslips for every employee.

### Inputs
- Locked PayrollRun
- Employee data (name, department, position)
- Company data (name, logo)
- Calculation snapshot (frozen rules)

### Outputs
- PDF payslips (one per employee)
- Batch ZIP download
- Acknowledgment tracking

### Dependencies
- PayrollRun locked (Module 4)
- Employee data complete
- NotoSansEthiopic font installed

### State Changes
```
Payslip.pdf_status: not_generated → generating → generated / failed
PayslipAcknowledgment: (none) → acknowledged
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Font missing | File check (VL-PSL-05) | Install font |
| PDF generation error | Exception handler | Retry (auto, up to2 times) |
| Race condition | Atomic claim | Second request reads result |
| Disk full | Disk check (VL-PSL-06) | Free space |
| Employee not linked | Portal check | Employee can't view — HR links account |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/payroll/{id}/generate-payslips` | Generate all |
| GET | `/api/payroll/{id}/generate-payslips/status` | Progress |
| GET | `/api/payslips/{id}/download` | Download PDF |
| GET | `/api/payroll/{id}/payslips/download-all` | Download ZIP |
| POST | `/api/payslips/{id}/acknowledge` | Acknowledge receipt |
| POST | `/api/payslips/{id}/regenerate` | Regenerate (display fields) |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Generate payslips | ✅ | ✅ | ❌ | ❌ |
| Download own | ❌ | ❌ | ❌ | ✅ |
| Download all | ✅ | ✅ | ❌ | ❌ |
| Acknowledge | ❌ | ❌ | ❌ | ✅ (own) |

### Evidence
- EV-001 through EV-017: All calculation evidence in PDF
- PDF generation timestamp
- Acknowledgment timestamp + IP

### Notifications
- N-06-02: Payslip ready (→ Employee)
- N-06-05: Payslip updated (→ Employee, after regeneration)

### PRD Reference
PRD-06

---

## Module 8: Employee Self-Service

### Purpose
Employee portal for payslips, leave, profile, tax certificates.

### Inputs
- Employee linked to user account
- Leave requests
- Profile updates
- Tax certificate requests

### Outputs
- Payslip views and downloads
- Leave requests → manager approval
- Profile change requests → HR approval
- Tax certificate PDFs
- Year-to-date summaries

### Dependencies
- Employee linked to User account
- At least one payroll run completed (for payslips)
- Leave policy configured

### State Changes
```
Leave: pending → approved / rejected
Profile Change: pending → approved / completed (or → rejected)
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Employee not linked | Auth check (VL-09-01) | HR links account |
| Insufficient leave balance | Balance check (VL-09-02) | Employee reduces request |
| Sensitive field without approval | Profile change check | Request created for HR |
| Duplicate change request | Status check (VL-PRF-05) | Wait for existing request |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/portal/dashboard` | Dashboard |
| GET | `/api/portal/payslips` | Payslip list |
| GET | `/api/portal/payslips/{id}` | Payslip detail |
| POST | `/api/portal/leave/request` | Request leave |
| GET | `/api/portal/leave` | Leave history |
| PUT | `/api/portal/profile` | Update profile |
| GET | `/api/portal/tax-certificate` | Tax certificate |
| GET | `/api/portal/ytd` | Year-to-date |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| View own dashboard | ❌ | ❌ | ❌ | ✅ |
| View own payslips | ❌ | ❌ | ❌ | ✅ |
| Request leave | ❌ | ❌ | ❌ | ✅ |
| Edit own profile | ❌ | ❌ | ❌ | ✅ |
| Approve leave | ✅ | ✅ | ❌ | ❌ |
| Approve profile change | ✅ | ❌ | ❌ | ❌ |

### Evidence
- Tax certificate: YTD totals from all payslips
- Leave balance: accrual, usage, remaining

### Notifications
- N-07-01: Payslip ready (→ Employee)
- N-07-02: Leave approved (→ Employee)
- N-07-03: Leave rejected (→ Employee)
- N-07-06: Leave request received (→ Manager)

### PRD Reference
PRD-09

---

## Module 9: Corrections & Audit

### Purpose
Handle post-approval corrections and maintain tamper-proof audit trail.

### Inputs
- Correction requests (type, amount, reason)
- Original locked payslips
- Hash chain verification requests

### Outputs
- Adjustment payslips (linked to originals)
- Correction history
- Audit packages (8-document ZIP)
- Hash chain verification reports

### Dependencies
- Locked PayrollRun (Module 4)
- Original Payslip records

### State Changes
```
Adjustment Payslip: created → included in next payroll → processed
Hash Chain: intact → compromised (if break detected) → resolved
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Hash chain break | Daily verification | Critical alert, investigation |
| Correction on unlocked payslip | Status check (VL-AUD-05) | Must lock payroll first |
| Short correction reason | Length check (VL-AUD-03) | User extends reason |
| Zero adjustment | Value check (VL-AUD-04) | User provides non-zero amount |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/audit/corrections` | Create correction |
| GET | `/api/audit/corrections` | List corrections |
| POST | `/api/audit/verify-chain` | Verify hash chain |
| POST | `/api/audit/generate-package` | Generate audit package |
| GET | `/api/audit/packages/{id}/download` | Download package |
| GET | `/api/audit/log/export` | Export audit log |
| GET | `/api/audit/dashboard` | Compliance dashboard |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Create correction | ✅ | ✅ | ❌ | ❌ |
| View corrections | ✅ | ✅ | ✅ | ❌ |
| Verify hash chain | ✅ | ✅ | ✅ | ❌ |
| Generate audit package | ✅ | ❌ | ✅ | ❌ |
| Export audit log | ✅ | ❌ | ✅ | ❌ |

### Evidence
- Adjustment payslip: original reference, correction type, amount, reason
- Hash chain: SHA-256 of previous_hash + company_id + user_id + action + details
- Audit package: executive summary, payroll detail, tax calculations, pension, ERCA, audit log, evidence, corrections

### Notifications
- N-08-01: Hash chain break (→ Owner, critical)
- N-08-02: Correction created (→ Owner)

### PRD Reference
PRD-08

---

## Module 10: Termination & Settlement

### Purpose
Process employee departures with legally compliant settlement calculations.

### Inputs
- Termination reason (resignation, redundancy, cause, retirement, contract end)
- Last working day
- Employee salary, years of service, leave balance, pending deductions

### Outputs
- FinalSettlement record
- Settlement letter PDF
- Experience certificate PDF
- Adjusted employee status (terminated)

### Dependencies
- Active employee (Module 2)
- Current salary data
- Leave balance

### State Changes
```
Employee: active → terminated → archived
FinalSettlement: pending → approved → paid
```

### Failure Modes
| Failure | Detection | Recovery |
|---------|-----------|----------|
| Invalid reason | Validation (VL-TRM-02) | User selects valid reason |
| Wrong password | Validation (VL-TRM-03) | User re-enters password |
| Already terminated | Validation (VL-TRM-04) | Check employee status |
| Negative settlement | Calculation check | Review deductions |
| Pending deductions | Balance check (VL-TRM-07) | Settle or write off |

### APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/employees/{id}/terminate` | Terminate |
| GET | `/api/settlements/{id}` | Settlement detail |
| POST | `/api/settlements/{id}/approve` | Approve payment |
| GET | `/api/settlements/{id}/letter` | Settlement letter |
| GET | `/api/settlements/{id}/certificate` | Experience cert |
| POST | `/api/settlements/{id}/preview` | Preview calculation |

### Permissions
| Action | Owner | Officer | Accountant | Employee |
|--------|-------|---------|------------|----------|
| Initiate termination | ✅ | ✅ | ❌ | ❌ |
| View settlement | ✅ | ✅ | ✅ | ❌ |
| Approve payment | ✅ | ❌ | ❌ | ❌ |
| Generate letter | ✅ | ✅ | ❌ | ❌ |

### Evidence
- Settlement: earnings breakdown, deductions breakdown, net payment, legal references
- Severance formula: years × 1 month salary (per Proclamation 1156/2019)
- Settlement letter: employer certification

### Notifications
- N-09-01: Employee terminated (→ Owner)
- N-09-02: Settlement needs approval (→ Owner)

### PRD Reference
PRD-07

---

## Cross-Module Dependencies

```
Module 1 (Company Setup)
  ↓
Module 2 (Employee Management)
  ↓
Module 3 (Payroll Calculation)
  ↓
Module 4 (Approval & Locking)
  ↓
  ├──→ Module 5 (Payment Processing)
  │      ↓
  │      Module 6 (Government Filing)
  │
  ├──→ Module 7 (Payslip Generation)
  │      ↓
  │      Module 8 (Employee Self-Service)
  │
  └──→ Module 9 (Corrections & Audit)
         ↓
         Module 10 (Termination & Settlement)
```

**Key invariant:** Modules 5, 6, 7, 8 can only run after Module 4 (lock). Module 9 creates adjustment payslips that feed back into Module 3 (next payroll).

---

## Global Behaviors

### Tenant Isolation
Every query includes `company_id` filter via `TenantQuery`. One ORM bug = cross-tenant data leak. Database-level constraints are the safety net (Phase 2).

### Evidence
Every number displayed to a user is traceable to: source data, formula, law, timestamp, approver, hash. See `EVIDENCE_CATALOGUE.md`.

### Audit Trail
Every state change is recorded: who, when, what changed, from what IP. SHA-256 hash chain for tamper detection. See `ARCHITECTURE_DECISIONS.md` ADR-006.

### Notifications
All notifications defined in `NOTIFICATION_CATALOGUE.md` and `PAYMENT_CATALOGUE.md`. In-app (always on), WhatsApp (future), email (future).

### Configuration
All configurable values defined in `BUSINESS_RULE_CATALOGUE.md`. Values stored in `TaxRule`, `SystemSetting`, and `Company` models. See Configuration Catalogue (to be built).

---

*Functional Specification v1.0*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
