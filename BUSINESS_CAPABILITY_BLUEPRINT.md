# Business Capability Blueprint
### Ethiopian Workforce Platform
**Version:** 1.0
**Date:** 2026-07-28
**Status:** Draft — Pending Product Steering Committee Approval

---

## Purpose

This document defines **what the platform does as a business**, not how it is built.

Every capability described here answers: *What business outcome does this produce for a real person in a real Ethiopian company?*

Once approved, all engineering work must trace back to a capability in this blueprint. If a feature cannot be mapped to a capability, it should not be built.

---

## How to Read This Document

Each capability is defined with:

| Field | Meaning |
|-------|---------|
| **Business Outcome** | What changes in the real world when this capability works |
| **Personas** | Who uses it, who benefits |
| **Workflows** | Step-by-step business processes |
| **Required Data** | What information flows through this capability |
| **Dependencies** | What must exist before this capability can function |
| **Success Metrics** | How we know it's working |
| **Maturity Level** | Where we are today |
| **Current Gaps** | What's missing to reach full maturity |

### Maturity Levels

| Level | Meaning |
|-------|---------|
| **L0 — Not Started** | Does not exist. No workflow, no data model. |
| **L1 — Conceptual** | Design exists. Some code. Not usable by real customers. |
| **L2 — Functional** | Works for a single company in a controlled pilot. Manual workarounds needed. |
| **L3 — Reliable** | Works consistently. Minimal manual intervention. Ready for production. |
| **L4 — Optimized** | Measurable business impact. Customers report time saved. Benchmarked. |
| **L5 — Industry-Leading** | Best-in-class for Ethiopian market. Self-improving. Customers advocate for it. |

---

## Business Capability Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ETHIOPIAN WORKFORCE PLATFORM                      │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   1. PARTY   │  │  2. WORKFORCE │  │  3. COMPENSATION│            │
│  │  MANAGEMENT  │  │  OPERATIONS   │  │  & PAYROLL      │            │
│  │              │  │               │  │                  │            │
│  │ Employers    │  │ Attendance    │  │ Salary Structure │            │
│  │ Employees    │  │ Leave         │  │ Payroll Engine   │            │
│  │ Users/Roles  │  │ Overtime      │  │ Tax & Pension    │            │
│  │ Contacts     │  │ Holidays      │  │ Deductions       │            │
│  └──────────────┘  └──────────────┘  │ Settlements      │            │
│                                       └──────────────┘              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 4. COMPLIANCE│  │ 5. FINANCIAL │  │ 6. EMPLOYEE    │              │
│  │ & REGULATORY │  │ OPERATIONS   │  │    EXPERIENCE  │              │
│  │              │  │              │  │                  │            │
│  │ ERCA Filing  │  │ Bank Files   │  │ Self-Service     │            │
│  │ Pension Remit│  │ Disbursement │  │ Payslips         │            │
│  │ Audit Trail  │  │ Reconciliation│ │ Leave Requests   │            │
│  │ Labor Law    │  │ Accounting   │  │ Notifications    │            │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │ 7. BUSINESS  │  │ 8. PLATFORM  │                                │
│  │ INTELLIGENCE │  │ CAPABILITIES │                                │
│  │              │  │              │                                │
│  │ Dashboards   │  │ Multi-Tenant │                                │
│  │ Reports      │  │ Security     │                                │
│  │ Analytics    │  │ Integration  │                                │
│  │ Forecasting  │  │ i18n         │                                │
│  └──────────────┘  └──────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 1. PARTY MANAGEMENT

**Business outcome:** Every person and organization that participates in the employment relationship is identified, verified, and linked correctly.

---

## 1.1 Employer (Company) Management

**Business outcome:** A business entity exists in the system with all information needed to operate payroll, file taxes, and employ people.

**Personas:** Business Owner, HR Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Company Registration | New customer signs up | 1. Enter company name, TIN, address, phone → 2. Select jurisdiction (region) → 3. Select industry → 4. Configure payroll calendar → 5. System creates company entity |
| 2 | Company Profile Update | Business details change | 1. Edit fields → 2. System logs change in audit trail → 3. Updated info propagates to payslips, reports, filings |
| 3 | Company Deactivation | Business closes | 1. Final payroll run → 2. All filings submitted → 3. Data archived (retained per legal requirement) → 4. Company marked inactive |
| 4 | Multi-Branch Setup | Business opens new location | 1. Add branch (name, address, manager) → 2. Assign employees to branches → 3. Branch-level reporting enabled |

### Required Data

| Data Point | Required | Source | Sensitivity |
|-----------|----------|--------|-------------|
| Company legal name | Yes | User input | Public |
| TIN (Tax Identification Number) | Yes | User input | Confidential |
| Physical address | Yes | User input | Internal |
| Phone number | Yes | User input | Internal |
| Email | Yes | User input | Internal |
| Industry code | Yes | User selection | Internal |
| Jurisdiction (region/country) | Yes | User selection | Internal |
| Fiscal year start | Yes | Configuration | Internal |
| Payroll calendar (monthly/bi-weekly) | Yes | Configuration | Internal |
| ERCA registration number | Conditional | User input | Confidential |
| MOLSA registration number | Conditional | User input | Confidential |
| Bank accounts (for disbursement) | Yes | User input | Confidential |
| Logo/branding | No | File upload | Public |

### Dependencies

- Jurisdiction must be defined (tax rules, labor law, filing requirements)
- Industry classification must exist

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Time to register a company | < 10 minutes | Unknown |
| % of companies with complete profiles | 100% | Unknown |
| Profile update propagation time | Instant | Instant |

### Maturity: **L3 — Reliable**
Registration works. Profile updates work. Multi-branch does not exist.

### Current Gaps
- No multi-branch support
- No industry-specific configuration
- No guided onboarding wizard with progress persistence

---

## 1.2 Employee Management

**Business outcome:** Every person employed by a company has a verified, complete, and current record that serves as the single source of truth for payroll, HR, and compliance.

**Personas:** HR Officer, Payroll Officer, Employee (self-service)

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Add Employee | New hire | 1. Enter personal info (name, DOB, gender, phone, email) → 2. Enter employment info (ID, department, position, type, start date) → 3. Enter compensation (basic salary, allowances) → 4. Enter banking (account number, bank) → 5. Enter tax info (TIN) → 6. System validates all fields → 7. Employee record created |
| 2 | Bulk Import | Many hires at once | 1. Upload spreadsheet (.xlsx/.csv) → 2. System maps columns → 3. Preview with validation errors highlighted → 4. Confirm import → 5. System creates records, reports errors |
| 3 | Edit Employee | Info changes | 1. Modify field → 2. System logs change (who, when, what) → 3. If salary changes: trigger impact analysis |
| 4 | Deactivate Employee | End of employment | 1. Enter termination date and reason → 2. System calculates final settlement → 3. Employee marked inactive → 4. Payroll stops |
| 5 | Reactivate Employee | Rehire | 1. Search deactivated employees → 2. Reactivate with new start date → 3. Previous history preserved |
| 6 | Employee Self-Update | Employee changes own info | 1. Employee requests change (phone, bank account) → 2. HR approves → 3. Record updated |
| 7 | Employee Search/Filter | Find employee | 1. Search by name, ID, department, status → 2. Filter by active/inactive/terminated → 3. View list with key info |

### Required Data

| Data Point | Required | Source | Sensitivity | Change Frequency |
|-----------|----------|--------|-------------|-----------------|
| Full name | Yes | User input | Public | Rare |
| Employee ID | Yes | System/user | Public | Never |
| Date of birth | Yes | User input | Confidential | Never |
| Gender | Yes | User input | Confidential | Never |
| Phone number | Yes | User/input | Internal | Occasional |
| Email | No | User input | Internal | Occasional |
| National ID / Passport | Yes | User input | Confidential | Rare |
| Department | Yes | User selection | Public | Occasional |
| Position/Title | Yes | User input | Public | Occasional |
| Employment type | Yes | Selection | Internal | Rare |
| Start date | Yes | User input | Internal | Never |
| Basic salary | Yes | User input | Confidential | Annual |
| Allowances | Conditional | User input | Confidential | Annual |
| Bank account | Yes | User input | Confidential | Rare |
| Bank name | Yes | Selection | Internal | Rare |
| TIN | Yes | User input | Confidential | Never |
| Emergency contact | No | User input | Confidential | Rare |
| Photo | No | Upload | Internal | Rare |

### Dependencies

- Company must exist
- Department must be configured
- Bank must be in supported list

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Time to add one employee | < 3 minutes | ~4 min |
| Time to import 50 employees | < 5 minutes | ~3 min |
| Import error rate (clean spreadsheet) | < 2% | ~5% |
| Employee data completeness | 100% required fields | ~95% |
| Search response time | < 1 second | ~0.3s |

### Maturity: **L3 — Reliable**
Core CRUD works. Bulk import works. Self-service updates exist. Missing: document management, contract tracking, probation tracking.

### Current Gaps
- No document/contract management
- No probation period tracking
- No employee timeline/history view
- No bulk salary update workflow
- Import doesn't handle truly messy spreadsheets well
- No employee ID auto-generation strategy

---

## 1.3 User & Access Management

**Business outcome:** Every person who interacts with the system has appropriate access — no more, no less. All access is auditable.

**Personas:** Business Owner, System Administrator

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | User Registration | New user signs up | 1. Enter phone + password → 2. Verify phone → 3. Create company or accept invite → 4. Assign role |
| 2 | Role Assignment | Admin grants access | 1. Select user → 2. Assign role (Owner/Admin/Manager/Employee) → 3. System applies permissions |
| 3 | Employee Invite | HR links employee to portal | 1. HR enters employee email → 2. System sends invite link → 3. Employee creates account → 4. Account linked to employee record |
| 4 | Password Reset | User forgets password | 1. Enter phone → 2. System sends reset code → 3. Enter code + new password → 4. Account unlocked |
| 5 | Account Lockout | Too many failed logins | 1. 5 failed attempts → 2. Account locked 30 minutes → 3. User notified → 4. Auto-unlock or admin override |
| 6 | Access Revocation | User leaves company | 1. Admin deactivates user → 2. All sessions terminated → 3. API keys revoked |

### Roles & Permissions

| Capability | Owner | Admin | Manager | Employee |
|-----------|-------|-------|---------|----------|
| Manage company settings | ✅ | ✅ | ❌ | ❌ |
| Manage users/roles | ✅ | ✅ | ❌ | ❌ |
| Add/edit employees | ✅ | ✅ | ✅ | ❌ |
| Run payroll | ✅ | ✅ | ✅ (initiate) | ❌ |
| Approve payroll | ✅ | ✅ | ❌ | ❌ |
| Generate reports | ✅ | ✅ | ✅ | ❌ |
| View all employees | ✅ | ✅ | ✅ | ❌ |
| View own payslips | ✅ | ✅ | ✅ | ✅ |
| Request leave | ✅ | ✅ | ✅ | ✅ |
| Approve leave | ✅ | ✅ | ✅ | ❌ |
| View audit log | ✅ | ✅ | ❌ | ❌ |

### Dependencies

- Company must exist
- Employee record must exist (for employee role)

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Time to invite employee to portal | < 1 minute | ~2 min |
| Invite acceptance rate | > 80% | Unknown |
| Password reset completion rate | > 90% | Unknown |
| Unauthorized access incidents | 0 | 0 |

### Maturity: **L3 — Reliable**
Roles work. Invite flow works. Password reset works. Missing: fine-grained permissions, SSO.

### Current Gaps
- No fine-grained permission customization
- No SSO/SAML (enterprise feature — deferred)
- No multi-company user (one user, multiple companies)
- No access review/audit workflow

---

# 2. WORKFORCE OPERATIONS

**Business outcome:** HR officers can manage daily workforce activities — attendance, leave, overtime — and this data flows accurately into payroll.

---

## 2.1 Attendance Management

**Business outcome:** Every working day, every hour, and every absence is recorded. This data feeds into payroll calculations (especially overtime and leave deductions).

**Personas:** HR Officer, Payroll Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Import Attendance | Daily/weekly | 1. Export from biometric device → 2. Upload CSV → 3. System matches employees → 4. Creates attendance records → 5. Reports mismatches |
| 2 | Manual Attendance Entry | Missing record | 1. Select employee + date → 2. Enter hours worked → 3. Save with reason |
| 3 | Attendance Review | End of month | 1. View attendance summary → 2. Identify missing days → 3. Verify overtime hours → 4. Approve for payroll |

### Required Data

| Data Point | Required | Source |
|-----------|----------|--------|
| Employee ID | Yes | Biometric/Manual |
| Date | Yes | Biometric/Manual |
| Check-in time | Yes | Biometric/Manual |
| Check-out time | Yes | Biometric/Manual |
| Hours worked | Calculated | System |
| Overtime hours | Calculated | System |
| Status (present/absent/leave/holiday) | Calculated | System |

### Dependencies

- Employee records must exist
- Holiday calendar must be populated
- Leave records must be current

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Import success rate (clean CSV) | > 98% | ~95% |
| Time to import 100 employees' attendance | < 2 minutes | ~3 min |
| Missing attendance detection | Automatic | Manual |
| Attendance-to-payroll data flow | Zero manual steps | 1 manual step (approval) |

### Maturity: **L2 — Functional**
CSV import works. Manual entry works. No biometric device integration. No automatic missing-attendance detection.

### Current Gaps
- No biometric device direct integration
- No automatic missing-attendance alerts
- No attendance pattern analysis (late trends, absence patterns)
- No shift-based attendance

---

## 2.2 Leave Management

**Business outcome:** Every employee's leave entitlement, usage, and balance is tracked accurately. Leave data directly affects payroll (paid leave, unpaid leave, leave encashment).

**Personas:** Employee, HR Officer, Manager

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Leave Request | Employee requests leave | 1. Select leave type → 2. Select dates → 3. Add reason → 4. Submit → 5. Manager notified |
| 2 | Leave Approval | Manager reviews | 1. View request → 2. Check balance → 3. Check team coverage → 4. Approve/reject → 5. Employee notified |
| 3 | Leave Balance Calculation | System | 1. Start with annual entitlement → 2. Add carried forward → 3. Subtract used → 4. Add approved future → 5. Show remaining |
| 4 | Sick Leave Processing | Employee on sick leave | 1. Employee reports sick → 2. HR records sick leave → 3. System applies tiered pay (100%/50%/0%) based on duration → 4. Payroll adjusts |
| 5 | Maternity/Paternity Leave | Employee requests | 1. Employee submits request → 2. HR approves → 3. System tracks 120 days (maternity) or 3 days (paternity) → 4. Payroll handles pay |
| 6 | Leave Encashment | Termination | 1. Calculate unused annual leave → 2. Multiply by daily rate → 3. Include in final settlement |

### Leave Types & Rules

| Type | Entitlement | Carry Forward | Pay Impact |
|------|------------|---------------|------------|
| Annual Leave | 14 days (year 1), +1/year, max 30 | Yes (limited) | Full pay |
| Sick Leave | 180 days max | No | 100% (days 1-30), 50% (31-90), 0% (91-180) |
| Maternity Leave | 120 days | No | Full pay |
| Paternity Leave | 3 days | No | Full pay |
| Special Leave | 3 days | No | Full pay |
| Unpaid Leave | Unlimited | N/A | No pay (reduces gross) |

### Required Data

| Data Point | Required | Source |
|-----------|----------|--------|
| Leave type | Yes | Employee selection |
| Start date | Yes | Employee selection |
| End date | Yes | Employee selection |
| Reason | Conditional | Employee input |
| Medical certificate | Conditional (sick > 3 days) | Upload |
| Approval status | Yes | Manager action |
| Balance impact | Calculated | System |

### Dependencies

- Employee must be active
- Manager must be linked
- Holiday calendar must be current
- Leave rules must be configured

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Time to request leave | < 1 minute | ~1 min |
| Time to approve leave | < 2 minutes | ~1 min |
| Balance accuracy | 100% | ~98% |
| Payroll impact accuracy (unpaid leave) | 100% | ~95% |
| Employee self-service adoption | > 70% | Unknown |

### Maturity: **L3 — Reliable**
Leave types, request/approval workflow, balance tracking, payroll integration all work. Missing: leave calendar team view, carry-forward automation.

### Current Gaps
- No team leave calendar (see who's off when)
- No automatic carry-forward processing
- No leave conflict detection (too many people off at once)
- No leave encashment automation (manual calculation)

---

## 2.3 Overtime Management

**Business outcome:** Extra hours worked are tracked, calculated at the correct rate, and included in payroll. Compliance with labor law overtime limits is enforced.

**Personas:** Employee, Manager, Payroll Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Overtime Request | Employee/Manager | 1. Enter date, hours, type → 2. System checks monthly limit (20 hrs) → 3. Manager approves |
| 2 | Overtime Calculation | Payroll run | 1. Sum approved overtime hours per type → 2. Calculate hourly rate (basic/208) → 3. Apply multiplier → 4. Add to payslip |
| 3 | Limit Enforcement | System | 1. Check monthly total against 20-hour limit → 2. Check yearly total against 100-hour limit → 3. Flag violations |

### Overtime Types & Rates

| Type | Multiplier | When |
|------|-----------|------|
| Day overtime | 1.25× | Regular working hours extension |
| Night overtime | 1.50× | Between 10 PM and 6 AM |
| Holiday overtime | 2.00× | On public holidays |
| Rest + Holiday | 2.50× | On rest day that is also a holiday |

### Required Data

| Data Point | Required | Source |
|-----------|----------|--------|
| Employee | Yes | Selection |
| Date | Yes | User input |
| Hours | Yes | User input |
| Overtime type | Yes | Selection |
| Approval status | Yes | Manager action |

### Dependencies

- Employee must be active
- Basic salary must be set
- Working hours configuration must be correct

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Overtime calculation accuracy | 100% | ~100% |
| Limit violation detection | Automatic | Automatic |
| Time to record overtime | < 30 seconds | ~30 sec |
| Payroll integration | Zero manual steps | Zero (automatic) |

### Maturity: **L3 — Reliable**
Calculation works. Types and rates are configurable. Limits enforced. Missing: approval workflow, attendance integration.

### Current Gaps
- No overtime approval workflow (recorded directly)
- No automatic overtime from attendance data
- No overtime cost forecasting
- No department-level overtime budget

---

## 2.4 Holiday Calendar

**Business outcome:** Public holidays are defined and affect payroll (holiday pay, overtime rates) and leave calculations.

**Personas:** HR Officer, System

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Add Holiday | Annual planning | 1. Enter name, date, type → 2. System marks as public holiday → 3. Affects attendance, overtime, leave |
| 2 | Holiday Import | System | 1. Load Ethiopian public holidays → 2. Company can add custom holidays |

### Dependencies

- Ethiopian holiday data must be current
- Company-specific holidays may need to be added

### Maturity: **L2 — Functional**
Holiday model exists. Ethiopian holidays can be loaded. Missing: automatic yearly import, holiday pay calculation rules.

### Current Gaps
- No automatic holiday import for new year
- No holiday-specific pay rules (some industries pay double on holidays)
- No holiday conflict with leave detection

---

# 3. COMPENSATION & PAYROLL

**Business outcome:** Every employee is paid correctly, on time, with full compliance with Ethiopian tax and labor law. Every payroll run is auditable and defensible.

---

## 3.1 Salary Structure

**Business outcome:** Employee compensation is defined, structured, and changes are tracked with approval and audit trail.

**Personas:** HR Officer, Business Owner

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Set Initial Salary | New hire | 1. Enter basic salary → 2. Add allowances → 3. System calculates gross → 4. Record effective date |
| 2 | Salary Adjustment | Annual review / promotion | 1. Enter new salary → 2. Enter reason → 3. Set effective date → 4. System logs change → 5. Next payroll uses new salary |
| 3 | Impact Analysis | Before salary change | 1. System shows: old gross, new gross, tax impact, pension impact, net pay change → 2. Decision maker reviews → 3. Approves |

### Salary Components

| Component | Description | Taxable | Pensionable |
|-----------|-------------|---------|-------------|
| Basic Salary | Fixed monthly amount | Yes | Yes |
| Housing Allowance | Monthly housing support | Yes | Varies |
| Transport Allowance | Monthly transport support | Yes | Varies |
| Meal Allowance | Monthly meal support | Yes | Varies |
| Other Allowances | Free-text, configurable | Configurable | Configurable |

### Dependencies

- Employee must exist
- Tax rules must be current
- Allowance types must be defined

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Time to process salary change | < 2 minutes | ~2 min |
| Salary change audit trail | 100% logged | 100% |
| Impact analysis accuracy | 100% | ~100% |

### Maturity: **L3 — Reliable**
Basic salary and allowances work. Changes are logged. Impact analysis exists. Missing: salary grades, salary bands, annual increment automation.

### Current Gaps
- No salary grade/band structure
- No automatic annual increment workflow
- No salary benchmarking against market data
- No promotion workflow with salary adjustment

---

## 3.2 Payroll Engine

**Business outcome:** A complete payroll run processes all employees correctly, produces payslips, and generates all required outputs — in one operation.

**Personas:** Payroll Officer, Business Owner (approver)

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Prepare Payroll | Monthly cycle | 1. Verify all employees have current data → 2. Import/verify attendance → 3. Process overtime → 4. Process leave impacts → 5. Process deductions → 6. Run pre-processing validation |
| 2 | Run Payroll | Payroll Officer | 1. Select pay period → 2. System calculates all employees → 3. Generate draft → 4. Show validation results → 5. Show summary (total gross, tax, pension, net) |
| 3 | Review Payroll | Payroll Officer | 1. Compare with previous month → 2. Investigate variances → 3. Review flagged items → 4. Override flags with reasons if needed |
| 4 | Approve Payroll | Business Owner | 1. Review summary → 2. Review comparison → 3. Approve → 4. System locks run → 5. Generates outputs |
| 5 | Generate Outputs | System (post-approval) | 1. Generate payslips (PDF) → 2. Generate ERCA report → 3. Generate pension report → 4. Generate bank file → 5. Generate accounting entries |
| 6 | Distribute | System | 1. Publish payslips to employee portal → 2. Send notifications → 3. Bank file ready for download |
| 7 | Correction Run | Error discovered | 1. Create adjustment payslip → 2. Enter correction amount and reason → 3. Generate delta report → 4. Include in next ERCA filing |

### Calculation Pipeline

```
Employee Data
    ↓
Gross Salary = Basic + All Allowances
    ↓
Pension (7% of Basic) → deducted
    ↓
Taxable Income = Gross − Pension
    ↓
Income Tax = Progressive Brackets (0%→15%→20%→25%→30%→35%)
    ↓
Tax After Relief = Tax − Personal Relief (ETB 150)
    ↓
Other Deductions = Loans + Cost-Sharing + ...
    ↓
Net Pay = Gross − Pension − Tax − Other Deductions
```

### Pre-Processing Validation

| Check | Severity | Description |
|-------|----------|-------------|
| Missing salary | BLOCK | Employee with no salary cannot be processed |
| Negative net pay | BLOCK | Net pay cannot go below zero |
| Duplicate employee | BLOCK | Same name + same bank account detected |
| Missing bank details | BLOCK | No payment method specified |
| Salary anomaly (>500k or >10×) | FLAG | Unusually large salary, likely data error |
| Salary change >30% | FLAG | Significant change, verify intentional |
| Payroll variance >20% | FLAG | Total payroll changed significantly |
| Unpaid leave conflict | FLAG | Employee on unpaid leave but full salary |
| Pension mismatch | FLAG | Calculated pension doesn't match 7% of basic |
| Tax mismatch | FLAG | Calculated tax doesn't match bracket computation |

### Required Data

| Data Point | Source | Timing |
|-----------|--------|--------|
| Employee master data | Employee Management | Current |
| Attendance records | Attendance Import | Monthly |
| Overtime entries | Overtime Module | Monthly |
| Leave records | Leave Module | Monthly |
| Deductions (loans, etc.) | Deduction Module | Current |
| Tax rules | TaxRule Configuration | Current version |
| Pension rules | TaxRule Configuration | Current version |

### Dependencies

- All employee data must be current
- Attendance must be imported
- Overtime and leave must be processed
- Deductions must be configured
- Tax rules must be verified

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Payroll calculation accuracy | 100% | ~99% (unverified) |
| Time to run payroll (50 employees) | < 5 minutes | ~3 min |
| Time to run payroll (500 employees) | < 15 minutes | ~10 min |
| Pre-processing validation catches errors | > 95% | ~85% |
| Payroll-to-payslip generation | < 1 minute | ~30 sec |
| Correction run turnaround | < 1 hour | ~30 min |
| Month-over-month comparison | Instant | Instant |

### Maturity: **L3 — Reliable**
Core calculation works. Validation exists. Comparison report works. Missing: async processing for large companies, calculation snapshot for audit, scheduled payroll.

### Current Gaps
- No calculation snapshot on payslip (ADR-007)
- No async processing for 500+ employees (ADR-005)
- No scheduled/auto payroll
- No payroll run checklist (guided workflow)
- No bulk correction workflow

---

## 3.3 Final Settlement

**Business outcome:** When an employee leaves, all financial obligations are calculated correctly and paid in full — salary, severance, leave encashment, minus deductions.

**Personas:** HR Officer, Payroll Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Terminate Employee | End of employment | 1. Enter termination date + reason → 2. System calculates final settlement → 3. Shows breakdown → 4. HR reviews → 5. Approve → 6. Generate settlement document |
| 2 | Settlement Calculation | System | 1. Outstanding salary (prorated) → 2. Severance pay (years × salary) → 3. Leave encashment (unused days × daily rate) → 4. Minus pending deductions → 5. Minus tax/pension → 6. Net final payment |
| 3 | Settlement Payment | Payroll Officer | 1. Include in next payroll run → 2. Or process as separate payment → 3. Record payment method and reference |

### Termination Types & Severance

| Reason | Severance | Notice Period |
|--------|-----------|--------------|
| Resignation | None (if voluntary) | Per contract |
| Termination (with cause) | None | Per law |
| Layoff / Redundancy | 1 month per year (max 12) | 30 days |
| End of contract | 1 month per year (max 12) | Per contract |
| Retirement | 1 month per year (max 12) | N/A |
| Mutual agreement | Negotiated | Negotiated |

### Required Data

| Data Point | Source |
|-----------|--------|
| Termination reason | HR input |
| Last working day | HR input |
| Employment start date | Employee record |
| Years of service | Calculated |
| Unused leave days | Leave balance |
| Pending deductions | Deduction records |
| Basic salary | Employee record |

### Dependencies

- Employee record must be complete
- Leave balance must be current
- Deduction records must be current
- Severance rules must be configured

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Settlement calculation accuracy | 100% | ~98% |
| Time to calculate settlement | < 5 minutes | ~3 min |
| Settlement document generation | Automatic | Automatic |
| Payment method support | Bank + Telebirr + Cash | All three |

### Maturity: **L3 — Reliable**
Calculation works for all termination types. PDF generation works. Missing: clearance checklist, exit interview workflow.

### Current Gaps
- No exit clearance checklist
- No exit interview workflow
- No automated notification to IT/Finance on termination

---

# 4. COMPLIANCE & REGULATORY

**Business outcome:** Every filing, every report, every legal requirement is met correctly and on time. The business can defend every number to any authority.

---

## 4.1 ERCA Tax Filing

**Business outcome:** Monthly income tax withholding report is generated in the exact format ERCA requires, ready for submission.

**Personas:** Accountant, Payroll Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Generate ERCA Report | Monthly (after payroll) | 1. Select payroll run → 2. System generates .xlsx with 9 columns → 3. Accountant reviews → 4. Download |
| 2 | Submit to ERCA | Monthly deadline | 1. Download report → 2. Upload to ERCA portal → 3. Record filing in system (date, confirmation #) |
| 3 | Track Filing Status | Ongoing | 1. Record filed date → 2. Record confirmation number → 3. Track which periods are filed |

### Report Format (Current)

| Column | Header | Content |
|--------|--------|---------|
| A | No. | Sequential number |
| B | Employee ID | Company employee identifier |
| C | Employee Name | Full name |
| D | TIN | Tax Identification Number |
| E | Gross Salary | Monthly gross in ETB |
| F | Pension 7% | Employee pension contribution |
| G | Taxable Income | Gross − Pension |
| H | Tax Withheld | Monthly income tax |
| I | Net Pay | Take-home pay |

### Required Data

- Completed payroll run
- Employee TINs (all must be valid)
- Company TIN

### Dependencies

- Payroll must be completed and approved
- All employees must have valid TINs
- ERCA report template must be configured

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Report generation time | < 1 minute | ~30 sec |
| ERCA portal acceptance rate | 100% | Unknown (never tested) |
| Filing deadline compliance | 100% | Unknown |
| Column header accuracy | 100% match | Unverified |

### Maturity: **L2 — Functional**
Report generates. Format is assumed. Never test-uploaded to ERCA portal.

### Current Gaps
- **ERCA format unverified by accountant** — #1 compliance risk
- No direct ERCA portal integration
- No filing deadline reminders
- No automatic filing status tracking

---

## 4.2 Pension Remittance Reporting

**Business outcome:** Monthly pension contributions (employee 7% + employer 11%) are reported correctly for MOLSA submission.

**Personas:** Accountant, Payroll Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Generate Pension Report | Monthly | 1. Select payroll run → 2. System generates report with employee + employer contributions → 3. Download |
| 2 | Submit to MOLSA | Monthly deadline | 1. Download report → 2. Submit to pension authority → 3. Record filing |

### Required Data

- Completed payroll run
- Employee basic salaries (pension base)
- Pension rates (7% employee, 11% employer)

### Dependencies

- Payroll must be completed
- Pension rules must be current

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Calculation accuracy | 100% | ~100% |
| Report generation | Automatic | Automatic |

### Maturity: **L3 — Reliable**
Pension calculation is correct (7%/11% of basic). Report generates. Missing: MOLSA format verification.

### Current Gaps
- MOLSA report format unverified
- No direct MOLSA submission integration

---

## 4.3 Audit Trail

**Business outcome:** Every action in the system is recorded with who, what, when, and from where. The audit trail is tamper-evident and can defend the business in any inspection.

**Personas:** Auditor, Business Owner, Compliance Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Automatic Logging | Any state change | 1. Action occurs → 2. System records: timestamp, user, action, entity, old value, new value, IP address → 3. Hash chain updated |
| 2 | Audit Review | Investigation | 1. Filter by date, user, action type → 2. View chronological log → 3. Export for external review |
| 3 | Hash Chain Verification | Compliance check | 1. System computes hash chain → 2. Verifies no records altered → 3. Reports integrity status |

### Logged Action Types (18 currently)

- Login, logout, failed login
- Employee create, edit, deactivate, reactivate
- Payroll run create, approve, process, lock
- Company settings change
- Report template change
- Leave request, approval
- Settlement creation

### Dependencies

- All modules must log their actions
- Hash chain must be maintained

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Action coverage | 100% of state changes | ~85% |
| Hash chain integrity | Always valid | Always valid |
| Audit query response time | < 2 seconds | ~1 sec |
| Retention period | 10 years (3,650 days) | 10 years |

### Maturity: **L3 — Reliable**
18 action types logged. Hash chain intact. Missing: some state changes not logged (allowance/deduction CRUD).

### Current Gaps
- Not all CRUD operations logged
- No audit report export (PDF/Excel)
- No anomaly detection on audit log

---

## 4.4 Labor Law Compliance

**Business outcome:** Employment practices comply with Ethiopian labor law (Proclamation No. 1156/2019). Overtime limits, leave entitlements, severance calculations, and termination procedures are enforced.

**Personas:** HR Officer, Auditor

### Compliance Rules Enforced

| Rule | Law | System Enforcement |
|------|-----|-------------------|
| Overtime daily limit (20 hrs/month) | Art. 89 | Automatic flag |
| Overtime yearly limit (100 hrs/year) | Art. 89 | Automatic flag |
| Annual leave (14 days minimum) | Art. 61 | Configured |
| Sick leave (180 days max) | Art. 63 | Enforced |
| Maternity leave (120 days) | Art. 65 | Configured |
| Severance (1 month/year, max 12) | Art. 40-42 | Calculated |
| Working hours (48 hrs/week max) | Art. 57 | Configured |

### Maturity: **L3 — Reliable**
Core labor law rules are configured and enforced. Missing: contract compliance checking, working condition tracking.

### Current Gaps
- No employment contract template management
- No contract expiry tracking
- No labor law change notification system

---

# 5. FINANCIAL OPERATIONS

**Business outcome:** Money moves from business to employee correctly, on time, through the right channel. Every transaction is tracked.

---

## 5.1 Bank File Generation

**Business outcome:** A file is generated that can be uploaded to a bank portal to disburse salaries to all employees in one batch.

**Personas:** Payroll Officer, Finance Officer

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Generate Bank File | After payroll approval | 1. Select payroll run → 2. Select bank → 3. System validates all account numbers → 4. Generate file → 5. Download |
| 2 | Generate Mobile Money File | After payroll approval | 1. Select employees with Telebirr/M-Pesa → 2. Validate phone numbers → 3. Generate file → 4. Download |
| 3 | Mixed Disbursement | After payroll approval | 1. System groups by payment method → 2. Generate bank file for bank employees → 3. Generate mobile money file for mobile employees → 4. Download both |

### Supported Banks (Current)

| Bank | Account Format | Status |
|------|---------------|--------|
| CBE (Commercial Bank of Ethiopia) | 13 digits starting with 1 | ✅ |
| Dashen Bank | 13 digits | ✅ |
| Awash Bank | 13 digits | ✅ |
| Bank of Abyssinia | 13 digits | ✅ |
| Wegagen Bank | 13 digits | ✅ |
| NIB International | 13 digits | ✅ |
| Bunna Bank | 13 digits | ✅ |
| Zemen Bank | 13 digits | ✅ |
| Lion International | 13 digits | ✅ |
| Telebirr | 9 digits (09/07) | ✅ |
| M-Pesa | 9 digits (07) | ✅ |

### Required Data

- Approved payroll run
- Employee bank accounts (validated)
- Employee phone numbers (for mobile money)

### Dependencies

- Payroll must be approved
- All account numbers must be validated
- Bank format must be correct

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Account validation accuracy | 100% | ~99% |
| Bank file first-try acceptance | 100% | Unknown (never tested) |
| File generation time (50 employees) | < 10 seconds | ~5 sec |
| Supported banks | All major Ethiopian banks | 10 banks + 2 mobile |

### Maturity: **L2 — Functional**
Files generate. Formats are assumed. Never test-uploaded to actual bank portals.

### Current Gaps
- Bank file format unverified against actual portal requirements
- No retry workflow for failed payments
- No payment status tracking (sent/confirmed/failed)
- No real-time bank API integration

---

## 5.2 Disbursement Tracking

**Business outcome:** The business knows exactly which employees have been paid, which haven't, and why.

**Personas:** Payroll Officer, Finance Officer, Business Owner

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Mark as Disbursed | After bank upload | 1. Upload confirmation from bank → 2. Mark payroll run as disbursed → 3. Record date and user |
| 2 | Handle Failures | Bank rejects payments | 1. Record failed employees → 2. Enter rejection reason → 3. Generate retry file for failed employees only |
| 3 | Confirm Payment | After bank confirms | 1. Mark individual payslips as confirmed → 2. Notify employees |

### Current Status Flow

```
PayrollRun: pending → file_downloaded → disbursed → confirmed → failed
Payslip: pending_bank_clearance → bank_rejected → corrected → paid
```

### Maturity: **L2 — Functional**
Status fields exist. Manual updates work. Missing: automatic bank feedback, retry workflow, employee notification.

### Current Gaps
- No automatic bank feedback integration
- No one-click retry for failed payments
- No real-time payment status (sent/confirmed/failed)
- No employee notification on payment

---

## 5.3 Accounting Export

**Business outcome:** Payroll data is exported in a format that can be imported into accounting software, eliminating manual journal entries.

**Personas:** Accountant

### Workflows

| # | Workflow | Trigger | Steps |
|---|---------|---------|-------|
| 1 | Generate Journal Entries | After payroll | 1. Select payroll run → 2. System generates debit/credit entries → 3. Preview → 4. Export as .xlsx |
| 2 | Preview Entries | Before export | 1. View all journal entries → 2. Verify amounts → 3. Adjust if needed |

### Entry Structure

| Account | Debit | Credit |
|---------|-------|--------|
| Salary Expense | Gross salary | |
| Pension Payable (Employee) | | Employee pension |
| Pension Payable (Employer) | | Employer pension |
| Tax Payable | | Income tax |
| Net Payable | | Net pay |
| Bank/Cash | Net pay | |

### Maturity: **L2 — Functional**
Export generates. Format is basic. Missing: configurable chart of accounts, multi-currency.

### Current Gaps
- No configurable chart of accounts
- No direct accounting software integration (QuickBooks, etc.)
- No cost center allocation

---

# 6. EMPLOYEE EXPERIENCE

**Business outcome:** Employees can access their own information, request leave, view payslips, and track their requests — without calling HR.

---

## 6.1 Employee Self-Service Portal

**Business outcome:** Employees serve themselves for routine requests, reducing HR workload and improving employee satisfaction.

**Personas:** Employee

### Capabilities

| Capability | Status | Description |
|-----------|--------|-------------|
| View payslips | ✅ | Current and historical payslips with full breakdown |
| Download payslip PDF | ✅ | Individual payslip download |
| View tax certificate | ✅ | YTD tax summary |
| View leave balance | ✅ | Current balance by type |
| Request leave | ✅ | Submit leave request with dates and reason |
| View overtime | ✅ | Current month overtime hours and pay |
| Update profile | ✅ | Edit phone, email, bank account |
| View loan balance | ❌ | Not implemented |
| Dispute payslip | ❌ | Not implemented |
| View announcements | ❌ | Not implemented |
| Download employment letter | ❌ | Not implemented |

### Required Data

- Employee must be linked to user account
- Employee must have portal access

### Dependencies

- User account must exist
- Employee record must be linked
- Portal must be enabled for company

### Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Portal adoption rate | > 70% of employees | Unknown |
| Self-service resolution rate | > 80% of requests | ~60% |
| Time to view payslip | < 10 seconds | ~5 sec |
| Time to request leave | < 1 minute | ~1 min |
| Support ticket reduction | 50% vs. no portal | Unknown |

### Maturity: **L3 — Reliable**
Core self-service works. Mobile-friendly. Missing: disputes, announcements, employment letters.

### Current Gaps
- No loan balance view
- No payslip dispute workflow
- No company announcements
- No employment letter generation
- No document download center

---

## 6.2 Notifications

**Business outcome:** Employees and managers are informed of relevant events in real-time.

**Personas:** Employee, Manager, HR Officer

### Notification Types

| Event | Recipient | Channel | Status |
|-------|-----------|---------|--------|
| Payslip published | Employee | In-app + WhatsApp | ✅ |
| Leave request submitted | Manager | In-app | ✅ |
| Leave approved/rejected | Employee | In-app | ✅ |
| Payroll approved | Employee | In-app | ✅ |
| Payment confirmed | Employee | ❌ Not implemented | ❌ |
| Filing deadline approaching | HR/Accountant | ❌ Not implemented | ❌ |
| Contract expiring | HR | ❌ Not implemented | ❌ |

### Maturity: **L2 — Functional**
In-app notifications work. WhatsApp integration exists (optional). Missing: payment notifications, deadline reminders, contract alerts.

### Current Gaps
- No payment confirmation notifications
- No filing deadline reminders
- No contract expiry alerts
- No notification preferences (user chooses channels)

---

# 7. BUSINESS INTELLIGENCE

**Business outcome:** Business owners and managers understand what's happening with their workforce and payroll — trends, costs, risks — without manually analyzing spreadsheets.

---

## 7.1 Dashboards

**Business outcome:** At a glance, the business owner knows: how much payroll costs, how it changed, and what's coming.

**Personas:** Business Owner, HR Officer, Accountant

### Dashboard Widgets

| Widget | Description | Status |
|--------|-------------|--------|
| Total payroll this month | Sum of net pay | ✅ |
| Payroll by department | Breakdown | ✅ |
| Employee headcount | Active employees | ✅ |
| Recent payroll runs | Last 5 runs | ✅ |
| Pending actions | Approvals, leave requests | ✅ |
| Payroll trend (6 months) | Line chart | 🟡 Basic |
| Overtime cost this month | Sum of overtime | ✅ |
| Leave summary | Who's on leave today | ❌ |
| Upcoming events | Contract expirations, filings | ❌ |
| Cost per employee | Average cost | ❌ |

### Maturity: **L2 — Functional**
Basic dashboard exists. Missing: trend analysis, forecasting, customizable widgets.

### Current Gaps
- No payroll trend chart (6+ months)
- No cost-per-employee analysis
- No headcount growth chart
- No upcoming events widget
- No customizable dashboard

---

## 7.2 Reports

**Business outcome:** Accountants, auditors, and business owners can get the data they need in the format they need.

### Report Inventory

| Report | Audience | Format | Status |
|--------|----------|--------|--------|
| ERCA Tax Filing | Accountant | .xlsx, .csv | ✅ |
| Pension Report | Accountant | .xlsx, .csv | ✅ |
| Payroll Comparison | Accountant, Owner | HTML | ✅ |
| Payslip Details | Accountant | .csv | ✅ |
| Accounting Export | Accountant | .xlsx, .csv | ✅ |
| Employee List | HR | .csv | ✅ |
| Bank File | Finance | .csv | ✅ |
| Filing History | Accountant | HTML | ✅ |
| Attendance Summary | HR | ❌ | ❌ |
| Leave Balance Report | HR | ❌ | ❌ |
| Overtime Summary | Manager | ❌ | ❌ |
| Headcount Trend | Owner | ❌ | ❌ |
| Turnover Report | HR, Owner | ❌ | ❌ |
| Salary Benchmark | HR | ❌ | ❌ |
| Department Cost | Owner | ❌ | ❌ |
| Loan Exposure | Finance | ❌ | ❌ |
| Contract Expiry | HR | ❌ | ❌ |

### Maturity: **L2 — Functional**
Core compliance reports exist. Missing: many standard HR and business reports.

### Current Gaps
- 10 of 17 reports not implemented
- No report scheduling
- No report sharing
- No custom report builder

---

## 7.3 Analytics & Forecasting

**Business outcome:** The platform predicts and explains, not just records.

### Potential Capabilities

| Capability | Description | Status |
|-----------|-------------|--------|
| Payroll anomaly detection | Flag unusual changes automatically | 🟡 Rule-based |
| Cost forecasting | Predict next 3 months payroll | ❌ |
| Turnover prediction | Identify at-risk employees | ❌ |
| Overtime trend analysis | Track overtime cost trends | ❌ |
| Budget vs. actual | Compare planned vs. actual payroll | ❌ |

### Maturity: **L1 — Conceptual**
Rule-based anomaly detection exists (validation engine). No ML-based prediction. No forecasting.

---

# 8. PLATFORM CAPABILITIES

**Business outcome:** The platform is secure, scalable, and supports multiple companies without data leakage.

---

## 8.1 Multi-Tenancy

**Business outcome:** Multiple companies use the same platform with complete data isolation. Company A cannot see Company B's data. Ever.

**Maturity: **L3 — Reliable****
Structural ORM-level isolation (TenantQuery). Database-level constraints needed (ADR-003).

---

## 8.2 Security

**Business outcome:** All data is protected. Access is controlled. Actions are auditable.

| Capability | Status |
|-----------|--------|
| Password policy | ✅ Strong |
| Brute-force protection | ✅ 5 attempts / 15 min lockout |
| MFA (TOTP) | ✅ |
| Encrypted sensitive fields (AES) | ✅ |
| CSRF protection | ✅ |
| XSS prevention | ✅ |
| Audit log with hash chain | ✅ |
| Role-based access control | ✅ |
| API key authentication | ✅ |

**Maturity: **L3 — Reliable****

---

## 8.3 Internationalization

**Business outcome:** Users interact with the platform in their preferred language.

| Language | Status | Coverage |
|----------|--------|----------|
| English | ✅ | 100% |
| Amharic | ✅ | ~80% (needs native review) |
| Afaan Oromoo | ✅ | ~70% (needs native review) |

**Maturity: **L2 — Functional****
Translations exist. Native speaker review needed.

---

## 8.4 Integration

**Business outcome:** The platform connects with the tools businesses already use.

| Integration | Type | Status |
|-----------|------|--------|
| Excel/CSV | Import/Export | ✅ |
| Bank files | File generation | ✅ |
| ERCA reports | File generation | ✅ |
| WhatsApp | Notifications | ✅ (optional) |
| REST API | Programmatic | ✅ |
| Biometric devices | File import | ✅ (CSV) |
| Accounting software | File export | ✅ (CSV) |
| Bank APIs | Real-time | ❌ |
| SMS | Notifications | ❌ |
| Email | Notifications | ✅ (password reset) |

**Maturity: **L2 — Functional****
File-based integrations work. No real-time integrations.

---

# MATURITY SUMMARY

| Capability | Current Level | Target (12 months) | Gap |
|-----------|--------------|-------------------|-----|
| 1.1 Employer Management | L3 | L4 | Multi-branch, onboarding wizard |
| 1.2 Employee Management | L3 | L4 | Documents, timeline, bulk ops |
| 1.3 User & Access | L3 | L3 | Fine-grained permissions |
| 2.1 Attendance | L2 | L3 | Biometric integration, alerts |
| 2.2 Leave | L3 | L4 | Team calendar, carry-forward |
| 2.3 Overtime | L3 | L3 | Approval workflow |
| 2.4 Holidays | L2 | L3 | Auto-import, pay rules |
| 3.1 Salary Structure | L3 | L4 | Grades, bands, increments |
| 3.2 Payroll Engine | L3 | L4 | Snapshots, async, scheduling |
| 3.3 Final Settlement | L3 | L3 | Clearance checklist |
| 4.1 ERCA Filing | L2 | L4 | **Accountant verification** |
| 4.2 Pension Reporting | L3 | L3 | MOLSA format verification |
| 4.3 Audit Trail | L3 | L4 | Full coverage, export |
| 4.4 Labor Law | L3 | L3 | Contract compliance |
| 5.1 Bank Files | L2 | L4 | **Bank portal verification** |
| 5.2 Disbursement | L2 | L3 | Retry, status tracking |
| 5.3 Accounting Export | L2 | L3 | Chart of accounts |
| 6.1 Employee Portal | L3 | L4 | Disputes, announcements |
| 6.2 Notifications | L2 | L3 | Payment alerts, deadlines |
| 7.1 Dashboards | L2 | L3 | Trends, forecasting |
| 7.2 Reports | L2 | L4 | 10 missing reports |
| 7.3 Analytics | L1 | L2 | Forecasting |
| 8.1 Multi-Tenancy | L3 | L3 | DB-level constraints |
| 8.2 Security | L3 | L3 | Maintain |
| 8.3 i18n | L2 | L3 | Native speaker review |
| 8.4 Integration | L2 | L3 | Real-time integrations |

---

# CRITICAL PATH TO PRODUCTION

The capabilities that **must** reach L3 before any public launch:

1. **ERCA Filing** (L2→L4): Accountant verification of format
2. **Bank Files** (L2→L4): Bank portal verification of format
3. **Payroll Engine** (L3→L4): Calculation snapshot, async processing
4. **Audit Trail** (L3→L4): Full action coverage
5. **Employee Portal** (L3→L4): Dispute workflow

Everything else can launch at L3 and improve based on pilot feedback.

---

# ENGINEERING TRACEABILITY

Every engineering task must map to a capability in this blueprint.

**Template:**

```
Engineering Task: [Description]
Capability: [X.Y — Name]
Business Outcome: [What this achieves for the customer]
Maturity Impact: [L_current → L_target]
```

**Example:**

```
Engineering Task: Add calculation_snapshot JSON column to Payslip
Capability: 3.2 — Payroll Engine
Business Outcome: Every payroll calculation is frozen and verifiable by auditors
Maturity Impact: L3 → L4
```

If a task cannot fill in this template, it should not be built.

---

*Blueprint version: 1.0*
*Approved by: [Pending Product Steering Committee]*
*Next review: After first pilot completion*
*All engineering work must trace back to this document.*
