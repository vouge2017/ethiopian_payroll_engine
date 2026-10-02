# PRD-01: Hire Employee
**Journey:** 1 — Hire an Employee
**Status:** Draft
**Date:** 2026-07-28
**Maturity Required:** Level 2+

---

## Business Objective

Enable an HR officer to add a new employee to the system in under 3 minutes, with real-time validation of TIN and bank account, automatic payroll impact preview, and zero communication gaps with accounting.

## Customer Problem

Ethiopian businesses hire employees by collecting documents (paper, WhatsApp photos), entering data in Excel, manually verifying TINs and bank accounts, and then emailing/calling the accountant. This takes 3+ hours, has an 8-12% error rate, and errors are discovered only on payday.

## Primary Actor

**HR Officer** — enters employee data, assigns salary, uploads documents.

## Supporting Actors

| Role | Action |
|------|--------|
| **Business Owner** | Approves salary, reviews payroll impact preview |
| **Accountant** | Receives notification, verifies TIN, reviews tax implications |
| **Employee** | Receives welcome notification, creates portal account |
| **System** | Validates TIN, validates bank, calculates payroll impact |

## Trigger

Business owner or HR officer decides to hire someone. Reasons: new position, replacement, business growth.

## Preconditions

- Company exists and is active (Journey 0 complete)
- HR officer has employee information (name, salary, TIN, bank account)
- Department exists in system (or can be created)

---

## Main Flow

### Step 1: Open Add Employee Form
1. HR officer navigates to Employees → Add Employee
2. System shows form with fields grouped into sections:
   - **Personal:** Name, phone, email, date of birth, gender, national ID
   - **Employment:** Employee ID (auto-generated), department, position, employment type, start date
   - **Compensation:** Basic salary, allowances
   - **Banking:** Bank (dropdown), account number
   - **Tax:** TIN

### Step 2: Enter Personal Information
1. HR enters full name
2. System auto-generates Employee ID (e.g., EMP-051)
3. HR enters phone → system validates Ethiopian format (09/07 + 8 digits)
4. HR enters remaining personal fields

### Step 3: Enter Employment Information
1. HR selects department from dropdown (or creates new)
2. HR enters position/title
3. HR selects employment type: Permanent / Contract / Daily
4. HR enters start date
5. If Contract: HR enters contract end date → system calculates contract duration

### Step 4: Enter Compensation
1. HR enters basic salary
2. System immediately shows:
   ```
   PAYROLL IMPACT
   This employee adds:
   Gross:     ETB 12,000/month
   Pension:   ETB    840/month (7% of basic)
   Taxable:   ETB 11,160/month
   Est. Tax:  ETB  2,004/month
   Est. Net:  ETB  9,156/month
   ```
3. HR adds allowances (if any): housing, transport, meal, other
4. System recalculates impact with allowances

### Step 5: Enter Banking Information
1. HR selects bank from dropdown (CBE, Dashen, Awash, etc.)
2. HR enters account number
3. System validates account format against selected bank pattern
4. System shows: ✓ Valid CBE account" or ✗ Invalid: CBE requires 13 digits starting with 1"

### Step 6: Enter Tax Information
1. HR enters TIN
2. System validates format (9-10 digits)
3. System shows: ✓ Valid TIN format" or ✗ Invalid: TIN must be 9-10 digits"

### Step 7: Review & Save
1. System shows summary:
   ```
   NEW EMPLOYEE SUMMARY
   ━━━━━━━━━━━━━━━━━━━━━━━━━
   Name:           Kebede Alemu
   Employee ID:    EMP-051
   Department:     Sales
   Position:       Officer
   Type:           Permanent
   Start Date:     2026-08-01
   Basic Salary:   ETB 12,000
   Allowances:     ETB 3,000
   Gross:          ETB 15,000
   Bank:           CBE (1000123456789)
   TIN:            1234567890
   ━━━━━━━━━━━━━━━━━━━━━━━━━
   ```
2. HR confirms → employee saved
3. System shows: ✓ Employee added. Appears in next payroll run."

### Step 8: Automatic Post-Save Actions
1. System adds employee to next payroll draft
2. System sends notification to accountant: "New employee: Kebede Alemu (EMP-051), ETB 15,000 gross. Review."
3. System logs action in audit trail
4. System updates Trust Score (if TIN/bank valid, score maintains; if issues, score decreases)

---

## Alternative Flows

### A1: Add Employee from Employee Portal Invite
1. HR enters employee email → system sends invite link
2. Employee clicks link → creates account → enters own bank/TIN
3. HR reviews and approves employee-submitted data
4. Employee is linked to user account for portal access

### A2: Bulk Import (Multiple Employees)
1. HR clicks "Import from Excel" (Journey 0 flow)
2. System uses same validation and mapping
3. All employees imported in one operation

### A3: Salary Impact Causes Owner Concern
1. HR enters salary → system shows payroll impact
2. Owner sees impact and wants to negotiate salary
3. Owner adjusts salary → system recalculates
4. Owner approves final salary

### A4: Employee Already Exists (Rehire)
1. HR enters name → system detects match with deactivated employee
2. System shows: "This person was previously employed (deactivated 2025-12-15). Reactivate?"
3. HR chooses: Reactivate (preserves history) or Create New (fresh record)
4. If rehire: previous salary, department, TIN, bank pre-filled

---

## Business Rules

| Rule | Source | Enforcement |
|------|--------|-------------|
| TIN must be 9-10 digits | ERCA | BLOCK — cannot save without valid TIN |
| Bank account must match bank pattern | Bank specifications | BLOCK — cannot save without valid account |
| Basic salary must be > 0 | Business logic | BLOCK — zero/negative salary rejected |
| Pension calculated on basic salary | Proclamation 1268/2022 | System uses basic_salary, not gross |
| Employee ID auto-generated | System | Unique, sequential per company |
| Start date must be in the past or today | Business logic | WARN if future date (probation tracking) |
| One active employee per TIN | Data integrity | BLOCK — duplicate TIN rejected |

## Validation Rules

| Check | Severity | Behavior |
|-------|----------|----------|
| Empty name | BLOCK | Cannot save |
| Invalid TIN format | BLOCK | Cannot save |
| Invalid bank account | BLOCK | Cannot save |
| Duplicate TIN (active employee) | BLOCK | Cannot save |
| Salary = 0 or negative | BLOCK | Cannot save |
| Salary > 500,000 ETB | FLAG | Save with warning, require acknowledgment |
| Missing phone | WARN | Save, show reminder |
| Missing email | WARN | Save, show reminder |
| Future start date | WARN | Save, note for probation tracking |

---

## Trust Moments

| Moment | What Happens | What Customer Thinks |
|--------|-------------|---------------------|
| TIN validated | Green checkmark after TIN entry | "I used to find out on payday that TIN was wrong" |
| Bank validated | Green checkmark after bank entry | "Last month 3 employees had wrong bank accounts" |
| Payroll impact preview | Shows gross, tax, pension, net before saving | "I can see what this hire costs me" |
| Accountant notification | Accountant sees new employee instantly | "No phone call needed" |
| Employee in next payroll | Employee automatically included | "No copy-paste into Excel" |

---

## Evidence Requirements

| Data Point | Evidence |
|-----------|----------|
| TIN validation | System shows: format check result, match against existing TINs |
| Bank validation | System shows: bank pattern, account format check |
| Payroll impact | System shows: calculation breakdown (basic → pension → taxable → tax → net) |
| Salary impact | System shows: comparison with department average, company average |

---

## Notifications

| Event | Recipient | Channel | Message |
|-------|-----------|---------|---------|
| Employee added | Accountant | In-app | "New employee: [name] ([ID]), ETB [gross]/month. Review." |
| Employee added | Owner | In-app | "New hire: [name] adds ETB [gross] to monthly payroll." |
| TIN missing (7 days) | HR | In-app | "[name] has no TIN — ERCA filing will fail." |
| Bank missing (7 days) | HR | In-app | "[name] has no bank account — cannot process payroll." |
| Welcome | Employee | In-app + WhatsApp | "Welcome to [company]. Your employee ID is [ID]. Access your portal at [link]." |

---

## Automation Rules

| Event | Automatic Action |
|-------|-----------------|
| Employee saved | Add to next payroll draft |
| Employee saved | Notify accountant |
| Employee saved | Log audit trail entry |
| TIN entered | Validate format, check for duplicates |
| Bank entered | Validate against bank pattern |
| Salary entered | Calculate and display payroll impact |
| Employee has portal invite email | Send welcome notification |
| TIN missing after 7 days | Remind HR |
| Bank missing after 7 days | Remind HR, block from payroll |
| Probation ending in 7 days | Notify HR: "Confirm permanent appointment" |

---

## Permissions

| Action | Owner | Admin | Manager | Employee |
|--------|-------|-------|---------|----------|
| Add employee | ✅ | ✅ | ✅ | ❌ |
| Edit employee | ✅ | ✅ | ✅ (own dept) | ❌ |
| View employee list | ✅ | ✅ | ✅ (own dept) | ❌ |
| View employee salary | ✅ | ✅ | ❌ | ❌ |
| Approve salary | ✅ | ✅ | ❌ | ❌ |
| Deactivate employee | ✅ | ✅ | ❌ | ❌ |
| Invite to portal | ✅ | ✅ | ✅ | ❌ |

---

## Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| Customer | Time to add employee | < 3 minutes |
| Customer | Data entry errors | < 0.5% |
| Customer | Time to payroll-ready | Instant |
| Business | HR support requests for hiring | Reduced by 80% |
| Platform | TIN validation accuracy | 100% |
| Platform | Bank account validation accuracy | 100% |

---

## Acceptance Criteria

```
Scenario: Add new employee successfully
Given   HR officer has employee info: name, salary ETB 12,000, valid TIN, valid CBE account
When    HR enters all fields and saves
Then    Employee is created with status "Active"
And     Employee appears in next payroll draft
And     Accountant receives notification
And     Audit log records creation
And     Trust Score maintains (no deductions)

Scenario: Invalid TIN
Given   HR enters TIN "12345" (too short)
When    HR attempts to save
Then    System shows error: "TIN must be 9-10 digits"
And     Employee is not saved
And     HR can correct TIN and retry

Scenario: Invalid bank account
Given   HR selects CBE and enters account "12345" (too short)
When    HR attempts to save
Then    System shows error: "CBE requires 13 digits starting with 1"
And     Employee is not saved

Scenario: Payroll impact preview
Given   HR enters basic salary ETB 12,000 and allowance ETB 3,000
When    Salary field loses focus
Then    System shows:
        Gross: ETB 15,000
        Pension: ETB 840 (7% of 12,000)
        Taxable: ETB 14,160
        Est. Tax: ETB 2,004
        Est. Net: ETB 12,156

Scenario: Duplicate TIN
Given   Employee with TIN 1234567890 already exists (active)
When    HR enters same TIN for new employee
Then    System shows error: "This TIN is already registered to [existing employee name]"
And     Employee is not saved

Scenario: High salary flag
Given   HR enters salary ETB 600,000
When    HR saves
Then    System shows warning: "Salary ETB 600,000 is unusually high. Confirm this is correct."
And     HR must acknowledge before save completes
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| Employee name has special characters (Amharic) | Accept UTF-8 names |
| Same name, different people | Allow — system uses Employee ID to distinguish |
| Bank not in supported list | Show: "Bank not supported. Supported banks: [list]" |
| Employee has no phone | Allow (WARN), but cannot send portal invite |
| Employee has no email | Allow (WARN), but cannot send email notifications |
| Start date in the past (backfill) | Allow, note for payroll pro-ration |
| Multiple allowances with same name | Allow — system tracks by amount, not name |
| Employee type = Daily | Show daily rate field instead of monthly salary |

---

## Out of Scope

- Document/contract upload (future: document management)
- Probation tracking automation (future: Journey 9)
- Performance review setup (future: Journey 9)
- Background check integration (future: ecosystem)
- Recruitment pipeline (future: ecosystem)

---

## Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Employee model | ✅ Exists | `models.py` — Employee class |
| TIN validation | ✅ Exists | Format check in validation engine |
| Bank validation | ✅ Exists | Pattern matching in `bank_file.py` |
| Tax calculation | ✅ Exists | `tax.py` — `calculate_tax_breakdown()` |
| Pension calculation | ✅ Exists | `pension.py` — `employee_pension()` |
| Notification system | ✅ Exists | `notifications.py` — in-app + WhatsApp |
| Audit log | ✅ Exists | `models.py` — AuditLog with hash chain |
| Employee portal invite | ✅ Exists | `employees_bp.py` — invite flow |
| Payroll impact preview | 🟡 Partial | Calculation exists, UI preview needs build |
| Trust Score | ❌ New | Needs to be built |

---

## Related ADRs

- ADR-001: Trust Architecture (validation as trust layer)
- ADR-002: Evidence Layer (TIN/bank validation evidence)
- ADR-003: Crosscheck Engine (payroll impact calculation)

---

*PRD-01 | Part of CUSTOMER_JOURNEY_BLUEPRINT v2.0*
