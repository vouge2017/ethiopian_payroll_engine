# PRD-00: Company Setup & Excel Migration
**Journey:** 0 — Create Company & Migrate from Excel
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 1 → Level 3 (transition)

---

## Business Objective

Enable an Ethiopian business owner to go from Excel-based payroll to a live, payroll-ready company in under 15 minutes — with zero data re-entry and verified accuracy.

## Customer Problem

Ethiopian SMEs manage payroll in Excel. Migration to new software is so painful (re-entering all employees, verifying data, reconfiguring rules) that most businesses never switch. The effort to migrate exceeds the perceived benefit — until something goes wrong (ERCA penalty, wrong tax, employee complaint).

## Primary Actor

**Business Owner** — creates account, chooses industry, approves import, goes live.

## Supporting Actors

| Role | Action |
|------|--------|
| **Accountant** | Reviews imported data, verifies TINs, confirms tax/pension rules |
| **HR Officer** | Provides employee Excel file, fixes flagged data errors |
| **System** | Validates data, maps columns, detects duplicates, runs test payroll |

## Trigger

Business owner decides to switch from Excel. Reasons: ERCA penalty risk, employee complaints about payslips, time wasted on manual calculations, fear of errors.

## Preconditions

- Business owner has an Excel file with employee data (name, salary, TIN, bank account)
- Business owner has internet access and a phone number for registration
- Business has a valid TIN

---

## Main Flow

### Step 1: Create Account
1. Owner enters phone number + password
2. System sends verification code
3. Owner enters code → account created
4. Owner is assigned "Owner" role

### Step 2: Create Company
1. Owner enters: company name, TIN, address, phone, email
2. System validates TIN format
3. Owner selects industry from list
4. System loads industry template (pre-fills fields, labels, rules)
5. Owner selects jurisdiction (default: Ethiopia)
6. Company entity created

### Step 3: Import Employees from Excel
1. Owner clicks "Import from Excel"
2. System accepts `.xlsx` or `.csv` file
3. System reads headers, auto-maps columns:
   - `Name` / `Full Name` / `Employee Name` → `name`
   - `Salary` / `Basic` / `Monthly Salary` → `basic_salary`
   - `TIN` / `Tax ID` → `tin`
   - `Bank` / `Account` / `Bank Account` → `bank_account`
   - `Department` / `Dept` → `department`
4. System shows mapping preview: "I found 6 columns. 5 mapped, 1 unrecognized."
5. Owner confirms or adjusts mappings

### Step 4: Validate Data
1. System runs validation on all imported rows:
   - TIN format check (9-10 digits)
   - Bank account format check (per bank pattern)
   - Duplicate detection (same name + same bank)
   - Missing required fields
   - Salary anomaly check (>500,000 ETB or >10× average)
2. System shows validation report:
   ```
   IMPORT VALIDATION
   ✓ 47 employees ready
   ⚠ 2 invalid TINs (flagged for review)
   ⚠ 1 missing bank account
   ✗ 1 duplicate detected
   ```
3. Owner fixes flagged issues inline
4. Owner confirms import

### Step 5: Configure Policies
1. System shows configuration screen with defaults:
   - Payroll calendar (monthly, last working day)
   - Leave year start (Ethiopian new year or Gregorian)
   - Overtime rules (208 hours/month, rate multipliers)
   - Tax rules (current brackets loaded from TaxRule)
   - Pension rules (7% employee, 11% employer)
2. Owner reviews defaults (most are correct for Ethiopian law)
3. Owner saves configuration

### Step 6: First Payroll Test
1. System offers: "Run a test payroll with your imported data?"
2. Owner accepts
3. System calculates payroll for all imported employees
4. System shows total: "Platform result: ETB 1,847,220.50"
5. Owner enters their Excel total: "ETB 1,847,220.50"
6. System compares: "Difference: ETB 0.00 ✓ Numbers match."
7. If mismatch: system shows per-employee breakdown to identify discrepancy

### Step 7: Go Live
1. System shows: "Your company is ready. Next payroll date: [date]."
2. System generates first Trust Score: 85% (data quality issues reduce from 100%)
3. Owner sees dashboard with imported employees, pending actions, next payroll date

---

## Alternative Flows

### A1: No Excel File
1. Owner selects "Add employees manually"
2. System shows add-employee form (same as Journey 1)
3. Owner adds employees one by one

### A2: Messy Excel File
1. System detects inconsistent headers
2. System shows: "I found columns that don't match standard fields. Would you like to map them?"
3. Owner maps unrecognized columns to fields
4. System re-validates

### A3: Test Payroll Mismatch
1. System shows: "Difference: ETB 12,450.00"
2. System shows per-employee comparison:
   ```
   EMPLOYEE DIFFERENCES
   Kebede Alemu: Platform ETB 12,000 vs Excel ETB 15,000 (salary mismatch)
   Hana Tesfaye: Platform ETB 8,400 vs Excel ETB 8,400 (match)
   ```
3. Owner corrects data
4. Re-runs test

### A4: Abandoned Setup
1. Owner closes browser mid-setup
2. System saves progress (company created, partial import)
3. On next login: "Continue where you left off? You were importing employees."
4. Owner resumes from Step 3

---

## Business Rules

| Rule | Source | Enforcement |
|------|--------|-------------|
| TIN must be 9-10 digits | ERCA | BLOCK — cannot import without valid TIN |
| Bank account must match bank pattern | Bank specifications | BLOCK — cannot import without valid account |
| Salary must be > 0 | Business logic | BLOCK — zero/negative salary rejected |
| Basic salary is pension base | Proclamation 1268/2022 | System uses basic_salary for pension calculation |
| Tax brackets from TaxRule table | Proclamation 1395/2025 | System loads current version |
| Pension 7%/11% | Proclamation 1268/2022 | System applies rates from TaxRule |

## Validation Rules

| Check | Severity | Behavior |
|-------|----------|----------|
| Empty name | BLOCK | Cannot import row |
| Invalid TIN format | BLOCK | Cannot import row |
| Invalid bank account | BLOCK | Cannot import row |
| Duplicate (name + bank) | BLOCK | Cannot import row |
| Missing salary | BLOCK | Cannot import row |
| Salary > 500,000 ETB | FLAG | Import with warning, require acknowledgment |
| Salary > 10× average | FLAG | Import with warning, require acknowledgment |
| Missing department | WARN | Import, show in validation report |
| Missing phone | WARN | Import, show in validation report |

---

## Trust Moments

| Moment | What Happens | What Customer Thinks |
|--------|-------------|---------------------|
| Column auto-mapping | System matches Excel headers to fields | "It understood my spreadsheet" |
| Validation report | System flags errors before import | "Excel never told me about these errors" |
| Test payroll match | Platform total matches Excel total | "The numbers match — I can trust this" |
| First Trust Score | System shows 85% with improvement suggestions | "I can see exactly what to fix" |

---

## Evidence Requirements

| Data Point | Evidence |
|-----------|----------|
| Column mapping | System shows which Excel header mapped to which field |
| Validation results | Per-row pass/fail with specific error messages |
| Test payroll comparison | Side-by-side totals with per-employee breakdown |
| Trust Score | Sub-scores with specific deductions explained |

---

## Notifications

| Event | Recipient | Channel | Message |
|-------|-----------|---------|---------|
| Import complete | Owner | In-app | "47 employees imported. 4 issues to fix." |
| TIN invalid | Owner | In-app | "2 employees have invalid TINs. Fix before first payroll." |
| Bank invalid | Owner | In-app | "1 employee has no bank account. Fix before first payroll." |
| Migration complete | Accountant | In-app | "Company [name] has been set up. Review employee data." |
| Test payroll complete | Owner | In-app | "Test payroll: ETB X. Compare with your Excel." |

---

## Automation Rules

| Event | Automatic Action |
|-------|-----------------|
| Excel uploaded | Auto-detect column headers, map to fields |
| Import complete | Validate all TINs, bank accounts, detect duplicates |
| First payroll test | Auto-compare with uploaded Excel totals |
| Migration complete | Generate Migration Report with data quality summary |
| TIN invalid | Flag employee, block from ERCA filing |
| Bank account invalid | Flag employee, block from payroll |
| Duplicate detected | Block import, show both rows for owner decision |

---

## Permissions

| Action | Owner | Admin | Manager | Employee |
|--------|-------|-------|---------|----------|
| Create company | ✅ | ❌ | ❌ | ❌ |
| Import employees | ✅ | ✅ | ❌ | ❌ |
| Configure policies | ✅ | ✅ | ❌ | ❌ |
| Run test payroll | ✅ | ✅ | ❌ | ❌ |
| Go live | ✅ | ❌ | ❌ | ❌ |

---

## Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| Customer | Time to go live | < 15 minutes |
| Customer | Data import accuracy | > 99% |
| Customer | First payroll matches Excel | 100% match |
| Business | Migration completion rate | > 90% |
| Business | Customer activation (first payroll within 7 days) | > 80% |
| Platform | Column auto-mapping accuracy | > 95% |
| Platform | Validation error detection rate | > 99% |

---

## Acceptance Criteria

```
Scenario: Successful migration from Excel
Given   Owner has Excel with 50 employees (name, salary, TIN, bank, department)
And     TINs are valid, bank accounts are valid, no duplicates
When    Owner uploads Excel, confirms mapping, runs test payroll
Then    50 employees imported
And     Validation report shows 0 errors
And     Test payroll total matches Excel total
And     Trust Score > 85%
And     Company status is "Live"

Scenario: Excel with errors
Given   Owner has Excel with 50 employees
And     2 TINs are invalid, 1 bank account is missing, 1 duplicate exists
When    Owner uploads Excel
Then    Validation report shows 4 errors
And     Import is blocked until errors are fixed
And     Owner can fix errors inline
When    Owner fixes all errors and re-validates
Then    50 employees imported with 0 errors

Scenario: Abandoned setup
Given   Owner creates company and starts import
And     Owner closes browser after importing 30 of 50 employees
When    Owner logs in again
Then    System shows "Continue where you left off?"
And     Import resumes from row 31
And     Previous 30 employees are preserved

Scenario: Test payroll mismatch
Given   Owner imports employees and runs test payroll
And     Platform total is ETB 1,847,220
And     Owner enters Excel total as ETB 1,860,000
When    System compares
Then    System shows difference: ETB 12,780
And     System shows per-employee breakdown identifying discrepancies
And     Owner can correct data and re-run test
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| Excel with 0 rows | Show error: "No employees found in file" |
| Excel with 1,000+ rows | Allow import, show progress bar, warn about performance |
| Excel with merged cells | Ignore merged cells, read data rows |
| Excel with multiple sheets | Read first sheet, offer sheet selection |
| TIN already exists in system | Block: "This TIN is registered to another company" |
| Same employee in multiple rows | Detect as duplicate, block import |
| Salary in text format ("ETB 15,000") | Parse: remove "ETB", remove commas, convert to number |
| Date in Ethiopian calendar | Convert to Gregorian for storage |
| Phone in various formats | Normalize to Ethiopian format (09xxxxxxxx) |

---

## Out of Scope

- Multi-company import (one company per migration)
- Historical payroll data import (only current employees)
- Attendance/leave history import (separate journey)
- Contract/document upload (Journey 1 extension)
- API-based migration (file upload only for v1)

---

## Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Excel import module | ✅ Exists | `excel_import.py` — reads .xlsx with column mapping |
| TIN validation | ✅ Exists | Format check in validation engine |
| Bank validation | ✅ Exists | Pattern matching in `bank_file.py` |
| TaxRule configuration | ✅ Exists | Seeded via `seed_tax_rules.py` |
| Industry templates | 🟡 Partial | Framework exists, templates need pilot industries |
| Trust Score | ❌ New | Needs to be built |
| Test payroll comparison | ❌ New | Needs to be built |
| Setup progress persistence | ❌ New | Needs `OnboardingProgress` model |

---

## Related ADRs

- ADR-001: Trust Architecture (Trust Score foundation)
- ADR-002: Evidence Layer (validation evidence display)
- ADR-008: Industry Template Engine (industry selection)

---

*PRD-00 | Part of CUSTOMER_JOURNEY_BLUEPRINT v2.0*
