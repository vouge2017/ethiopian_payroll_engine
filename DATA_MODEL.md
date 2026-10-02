# Data Model & Domain Dictionary
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 15)
**Source:** `models.py` (1,714 lines), 28 models, 295 columns

---

## Entity Relationship Overview

```
Company (1) ──── (N) Employee
Company (1) ──── (N) User
Company (1) ──── (N) PayrollRun
Company (1) ──── (N) TaxRule
Company (1) ──── (N) Holiday

PayrollRun (1) ──── (N) Payslip
PayrollRun (1) ──── (N) PayrollValidationResult

Employee (1) ──── (N) Payslip
Employee (1) ──── (N) Leave
Employee (1) ──── (N) LeaveBalance
Employee (1) ──── (N) OvertimeEntry
Employee (1) ──── (N) EmployeeAllowance
Employee (1) ──── (N) EmployeeDeduction
Employee (1) ──── (N) Attendance
Employee (1) ──── (N) FinalSettlement
Employee (1) ──── (N) ProfileChangeRequest
Employee (1) ──── (N) PayslipAcknowledgment

User (1) ──── (N) AuditLog
User (1) ──── (N) Notification
User (1) ──── (N) ApiKey
```

---

## Core Entities

### Company

| Field | Type | Required | Sensitivity | Description |
|-------|------|----------|-------------|-------------|
| id | Integer | PK | — | Auto-increment |
| name | String(200) | Yes | Public | Legal company name |
| tin | String(20) | Yes | Confidential | Tax Identification Number |
| address | Text | Yes | Internal | Physical address |
| phone | String(20) | Yes | Internal | Company phone |
| email | String(200) | Yes | Internal | Company email |
| jurisdiction_code | String(5) | Yes | Internal | ISO 3166-1 (default: 'ET') |
| industry_code | String(20) | No | Internal | Industry classification |
| report_templates | JSON | No | Internal | ERCA column configuration |
| logo_path | String(500) | No | Public | Company logo |
| primary_color | String(7) | No | Public | Brand color (hex) |
| is_demo | Boolean | No | Internal | Demo company flag |
| created_at | DateTime | Auto | Internal | Creation timestamp |
| updated_at | DateTime | Auto | Internal | Last update timestamp |

**Lifecycle:** Active → Inactive (no deletion — data retained per legal requirement)
**Indexes:** `ix_company_tin` (unique)

---

### Employee

| Field | Type | Required | Sensitivity | Description |
|-------|------|----------|-------------|-------------|
| id | Integer | PK | — | Auto-increment |
| company_id | Integer | FK → Company | Internal | Tenant isolation |
| employee_id | String(50) | Yes | Public | Company employee ID (e.g., EMP-001) |
| name | String(200) | Yes | Internal | Full name |
| phone | String(20) | No | Confidential | Phone (Ethiopian format) |
| email | String(200) | No | Confidential | Email address |
| date_of_birth | Date | No | Confidential | Date of birth |
| gender | String(10) | No | Confidential | Male/Female/Other |
| national_id | String(50) | No | Confidential | National ID or passport |
| department | String(100) | Yes | Public | Department name |
| position | String(100) | Yes | Public | Job title |
| employment_type | String(20) | Yes | Internal | Permanent/Contract/Daily |
| start_date | Date | Yes | Internal | Employment start date |
| end_date | Date | No | Internal | Contract end date (if applicable) |
| basic_salary | Numeric(12,2) | Yes | Confidential | Monthly basic salary (ETB) |
| allowances | Numeric(12,2) | Yes | Confidential | Total monthly allowances (ETB) |
| daily_rate | Numeric(12,2) | No | Confidential | For daily workers |
| bank_or_telebirr | String(100) | No | Confidential | Legacy: 'bank:account' or 'telebirr:phone' |
| bank_account | String(50) | Yes | Confidential | **AES encrypted** — bank account number |
| bank_name | String(50) | Yes | Internal | Bank identifier |
| tin | String(20) | Yes | Confidential | **AES encrypted** — Tax ID |
| metadata | JSON | No | Internal | Industry-specific fields |
| is_active | Boolean | Yes | Internal | Active employment status |
| is_deleted | Boolean | Yes | Internal | Soft delete flag |
| user_id | Integer | FK → User | Internal | Linked portal account |
| invite_token | String(100) | No | Confidential | Portal invite token |
| created_at | DateTime | Auto | Internal | Creation timestamp |
| updated_at | DateTime | Auto | Internal | Last update timestamp |

**Lifecycle:**
```
Draft (import pending)
  ↓
Active (employed)
  ↓
Suspended (if needed)
  ↓
Terminated (employment ended)
  ↓
Archived (after retention period)
  ↓
Rehired (if re-employed → back to Active)
```

**Allowed transitions:** Draft→Active, Active→Suspended, Active→Terminated, Suspended→Active, Suspended→Terminated, Terminated→Rehired(Active)
**Forbidden transitions:** Terminated→Active (must go through Rehired), Archived→any (immutable)
**Indexes:** `ix_employee_company_id`, `ix_employee_tin` (unique per company), `ix_employee_user_id`
**Encryption:** `bank_account` and `tin` use AES encryption via `sqlalchemy-utils`

---

### PayrollRun

| Field | Type | Required | Sensitivity | Description |
|-------|------|----------|-------------|-------------|
| id | Integer | PK | — | Auto-increment |
| company_id | Integer | FK → Company | Internal | Tenant isolation |
| reference | String(20) | No | Public | Human-readable (PR-2018-10-001) |
| period | String(7) | No | Internal | Ethiopian period (2018-10) |
| run_date | Date | Yes | Internal | Payroll date |
| status | String(20) | Yes | Internal | Lifecycle status |
| source | String(20) | Yes | Internal | upload/spreadsheet/import/api |
| approved_by | Integer | FK → User | Internal | Approver |
| approved_at | DateTime | No | Internal | Approval timestamp |
| approval_ip | String(45) | No | Confidential | Approver IP |
| locked_at | DateTime | No | Internal | Lock timestamp |
| locked_by | Integer | FK → User | Internal | Locker |
| disbursement_status | String(20) | Yes | Internal | Payment status |
| disbursed_at | DateTime | No | Internal | Disbursement timestamp |
| disbursed_by | Integer | FK → User | Internal | Disburser |
| disbursement_notes | Text | No | Internal | Notes |
| created_at | DateTime | Auto | Internal | Creation timestamp |

**Lifecycle:**
```
draft → review → pending_approval → processing → completed → locked
                                                      ↓
                                                    failed
```

**Allowed transitions:** draft→review, review→pending_approval, pending_approval→processing, processing→completed, processing→failed, completed→locked
**Forbidden transitions:** locked→any (immutable), completed→draft (must create correction run)
**Indexes:** `ix_payrollrun_company_status`

---

### Payslip

| Field | Type | Required | Sensitivity | Description |
|-------|------|----------|-------------|-------------|
| id | Integer | PK | — | Auto-increment |
| payroll_run_id | Integer | FK → PayrollRun | Internal | Parent run |
| employee_id | Integer | FK → Employee | Internal | Employee |
| pdf_file_path | String(500) | No | Internal | Generated PDF path |
| pdf_status | String(20) | Yes | Internal | not_generated/generating/generated/failed |
| gross_salary | Numeric(12,2) | Yes | Confidential | Monthly gross |
| tax | Numeric(12,2) | Yes | Confidential | Income tax withheld |
| employee_pension | Numeric(12,2) | Yes | Confidential | Employee pension (7%) |
| employer_pension | Numeric(12,2) | Yes | Confidential | Employer pension (11%) |
| net_pay | Numeric(12,2) | Yes | Confidential | Take-home pay |
| payment_status | String(30) | Yes | Internal | Bank clearance status |
| payment_rejection_reason | Text | No | Internal | Why rejected |
| payslip_type | String(20) | Yes | Internal | regular/adjustment |
| reason | String(255) | No | Internal | Adjustment reason |
| original_payslip_id | Integer | FK → Payslip | Internal | If adjustment |
| calculation_snapshot | JSON | No | Internal | **Frozen rules at calculation time** |
| generated_at | DateTime | Auto | Internal | Generation timestamp |

**Lifecycle:**
```
not_generated → generating → generated → failed
payment: pending_bank_clearance → bank_rejected → corrected → paid
```

**Indexes:** `ix_payslip_run_employee`

**Critical:** `calculation_snapshot` stores the exact tax brackets, pension rates, and rules used. This makes historical payslips verifiable even if rules change later.

---

### TaxRule

| Field | Type | Required | Sensitivity | Description |
|-------|------|----------|-------------|-------------|
| id | Integer | PK | — | Auto-increment |
| company_id | Integer | FK → Company | Internal | Tenant isolation |
| rule_type | String(50) | Yes | Internal | tax_brackets/pension/overtime/leave/severance |
| version_name | String(50) | Yes | Internal | e.g., '2025-v1' |
| status | String(20) | Yes | Internal | draft/active/archived |
| rules_json | JSON | Yes | Internal | Rule values |
| description | Text | No | Internal | Legal citation |
| effective_from | Date | No | Internal | When this version takes effect |
| effective_to | Date | No | Internal | When this version expires |
| created_at | DateTime | Auto | Internal | Creation timestamp |

**rules_json structure (tax_brackets):**
```json
{
  "brackets": [
    {"min": 0, "max": 2000, "rate": 0.00},
    {"min": 2001, "max": 4000, "rate": 0.15},
    {"min": 4001, "max": 7000, "rate": 0.20},
    {"min": 7001, "max": 10000, "rate": 0.25},
    {"min": 10001, "max": 14000, "rate": 0.30},
    {"min": 14001, "max": null, "rate": 0.35}
  ],
  "personal_relief": 150,
  "pension": {
    "employee_rate": 0.07,
    "employer_rate": 0.11,
    "deduction_order": "before_tax",
    "ceiling": null
  }
}
```

---

### AuditLog

| Field | Type | Required | Sensitivity | Description |
|-------|------|----------|-------------|-------------|
| id | Integer | PK | — | Auto-increment |
| company_id | Integer | FK → Company | Internal | Tenant isolation |
| user_id | Integer | FK → User | Internal | Who performed action |
| action | String(50) | Yes | Internal | Action type |
| entity_type | String(50) | Yes | Internal | Entity type (Employee, PayrollRun, etc.) |
| entity_id | Integer | Yes | Internal | Entity ID |
| details | JSON | No | Internal | Change details (old/new values) |
| ip_address | String(45) | No | Confidential | Requester IP |
| hash | String(64) | Yes | Internal | SHA-256 hash (tamper-evident) |
| previous_hash | String(64) | No | Internal | Previous log hash (chain) |
| created_at | DateTime | Auto | Internal | Action timestamp |

**Immutability:** AuditLog records are never updated or deleted. The hash chain ensures tamper-evident integrity.

**Hash calculation:** `SHA-256(previous_hash + company_id + user_id + action + sorted_json(details))`

---

## Supporting Entities

### EmployeeAllowance
Links employees to their allowance components (housing, transport, meal, etc.)

### EmployeeDeduction
Tracks loans, cost-sharing, and other deductions with remaining balance.

### Leave / LeaveBalance
Tracks leave requests (type, dates, status) and remaining balances per type per year.

### OvertimeEntry
Records overtime hours by type (day/night/holiday/rest_holiday) with approval status.

### Attendance
Daily attendance records (check-in, check-out, hours worked). Imported from biometric devices.

### FinalSettlement
Complete settlement calculation for terminated employees (salary, severance, leave, deductions).

### ProfileChangeRequest
Employee-requested changes to their own profile (phone, bank account). Requires HR approval.

### PayslipAcknowledgment
Records when employee views/acknowledges their payslip.

### Notification
In-app notifications with type, link, read status.

### FilingRecord
Tracks ERCA/MOLSA filings (period, filed_by, filed_at, confirmation_number).

### ValidationRule
Configurable validation rules (rule_code, severity, enabled, config_json).

### PayrollValidationResult
Results of validation checks for a payroll run (rule, severity, employee, message, override).

### LoginAttempt
Failed login tracking for brute-force protection (identifier, ip, timestamp).

### SystemSetting
Key-value store for company-level settings.

---

## Naming Conventions

| Convention | Rule | Example |
|-----------|------|---------|
| Table names | snake_case, plural | `employees`, `payroll_runs` |
| Column names | snake_case | `basic_salary`, `employee_id` |
| Foreign keys | `{table}_id` | `company_id`, `employee_id` |
| Boolean columns | `is_` prefix | `is_active`, `is_deleted` |
| Timestamp columns | `_at` suffix | `created_at`, `approved_at` |
| JSON columns | `_json` suffix | `rules_json`, `details_json` |
| Encrypted columns | No suffix (documented) | `bank_account`, `tin` |

---

## Audit Requirements

Every entity must log:
- **Create:** Who created, when, initial values
- **Update:** Who updated, when, old values → new values
- **Delete:** Who soft-deleted, when (hard delete forbidden for payroll data)

Exceptions:
- AuditLog itself (immutable)
- LoginAttempt (append-only)
- Notification (read status update doesn't need audit)

---

## Evidence Model

Every calculation that touches money must produce an evidence record:

```json
{
  "calculation_id": "CALC-2026-07-28-001",
  "entity_type": "Payslip",
  "entity_id": 42,
  "formula": "tax = progressive_brackets(taxable_income) - personal_relief",
  "inputs": {
    "taxable_income": 13950.00,
    "brackets": [...],
    "personal_relief": 150.00
  },
  "output": 2685.00,
  "law_reference": "Proclamation No. 1395/2025, Article 36(1)",
  "calculated_at": "2026-07-28T10:35:12Z",
  "calculated_by": "system",
  "approved_by": "user:15",
  "approved_at": "2026-07-28T14:22:05Z",
  "snapshot_hash": "a7f3b2c1d4e5..."
}
```

---

## Multi-Tenancy

All tenant-scoped entities use `TenantQuery` (application-level enforcement).

**Required:** Every query on tenant-scoped entities must include `company_id` filter. `TenantQuery` raises `RuntimeError` if missing.

**Planned (ADR-003):** Database-level constraints (CHECK, row-level security) for defense in depth.

---

*Data Model version: 1.0*
*Source: models.py analysis, 2026-07-28*
