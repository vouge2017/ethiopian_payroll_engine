# 🇪🇹 ACTION PLAN — Beyond the Audit

**Date:** July 13, 2026  
**Goal:** Build a real deal, not just a calculator

---

## 1. ERCA FILING — BEYOND THE DEADLINE

### What the law says
- Filing deadline: **25th of the following month**
- Monthly return required for all employees
- TIN (Taxpayer Identification Number) required for each employee
- Income tax withheld must be remitted with the return

### What we can build NOW (no API needed)

**A. Filing Preparation Wizard**
```
Step 1: System shows "ERCA filing due in 5 days"
Step 2: System pre-fills the return with:
        - All employees with TIN
        - Gross salary, pension, tax for each
        - Total tax to remit
Step 3: System flags missing TINs (BLOCK)
Step 4: System generates the return in ERCA's format (Excel/PDF)
Step 5: Owner downloads and uploads to ERCA portal manually
Step 6: Owner marks as "Filed" with confirmation number
Step 7: System records filing date in audit trail
```

**B. What-if ERCA adds an API later**
- Design the filing module as a **pluggable adapter**
- Current: `ERCAAdapter.generate_return()` → downloads Excel
- Future: `ERCAAdapter.submit_api()` → posts to ERCA endpoint
- The data preparation logic stays the same, only the submission method changes

**C. ERCA-related assistance we MUST build**

| Problem | Solution |
|---|---|
| "I don't know when to file" | Deadline reminders (7 days, 3 days, 1 day before) |
| "I don't know what format ERCA wants" | Pre-filled return in ERCA's exact format |
| "I don't know if I have all TINs" | Pre-filing validation catches missing TINs |
| "I filed but forgot to mark it" | System asks "Did you file?" on the deadline day |
| "I need to amend a previous filing" | Correction run workflow (unlock → correct → re-file) |
| "I don't know how much to pay" | System calculates exact remittance amount |
| "I need proof of filing" | System stores confirmation number + timestamp |

**D. Annual Tax Reconciliation**
- At year end, system should:
  - Sum all 12 months of tax withheld per employee
  - Compare with annual tax liability
  - Identify over/under withholding
  - Generate annual summary for each employee
  - Prepare annual reconciliation report for ERCA

---

## 2. LEAVE MANAGEMENT — CORRECT AND FLEXIBLE

### What the law says (Labor Proclamation 1156/2019)

| Leave Type | Legal Requirement | Can Company Add More? |
|---|---|---|
| Annual | 14 days (Year 1), +1 day per year | ✅ Yes, can offer more |
| Sick | Max 6 months in 12-month period | ❌ Cannot reduce below this |
| Maternity | 120 days (30 pre + 90 post) | ❌ Cannot reduce below this |
| Paternity | 3 working days | ✅ Yes, can offer more |
| Special | 3 days (marriage, death of spouse/child) | ✅ Yes, can offer more |
| Other types | Not specified in law | ✅ Company can create |

### What we should build

**A. System-Enforced Minimums (Cannot Go Below)**
```
ANNUAL_LEAVE:
  minimum_days: 14 (Year 1)
  accrual: +1 day per additional year of service
  max_carry_forward: company policy (system suggests 50% of entitlement)
  COMPANY CANNOT SET BELOW 14

SICK_LEAVE:
  max_period: 6 months in 12-month period
  payment_tiers:
    - Month 1 (day 1-30): 100% pay
    - Month 2-3 (day 31-90): 50% pay
    - Month 4-6 (day 91-180): 0% pay
  COMPANY CANNOT SHORTEN THE PERIOD
  COMPANY CAN OFFER HIGHER PAY PERCENTAGE

MATERNITY_LEAVE:
  total_days: 120
  prenatal: 30 days
  postnatal: 90 days
  payment: 100% (employer pays, no social insurance system yet)
  COMPANY CANNOT REDUCE BELOW 120

PATERNITY_LEAVE:
  minimum_days: 3
  COMPANY CAN OFFER MORE
```

**B. Company-Created Leave Types**
The company admin can add custom leave types:
```
Examples:
  - Compassionate leave (company-specific)
  - Religious leave (beyond statutory)
  - Study/exam leave
  - Sabbatical (for long-tenured employees)
```

System behavior:
- Company creates new type → system asks "Is this paid or unpaid?"
- Company sets days → system asks "Per year? Per occurrence? Career total?"
- System validates: "This is above the statutory minimum. OK to proceed."

**C. What-if Scenarios for Leave**
```
Scenario: Employee wants 5 days sick leave
System shows:
  ✅ Sick leave balance: 6 months remaining
  ✅ Payment: 100% (within first 30 days)
  📋 Days used this period: 0
  📋 Medical certificate required after: 3 days (company policy)

Scenario: Employee requests maternity leave
System shows:
  ✅ Maternity leave: 120 days entitlement
  📋 Start date: March 1, 2026
  📋 Expected return: June 29, 2026
  💰 Full pay for 120 days
  ⚠️ System will auto-adjust payroll during leave period

Scenario: Company tries to approve only 10 days annual leave
System shows:
  ❌ BLOCK: Ethiopian law requires minimum 14 days annual leave
     (Labor Proclamation 1156/2019, Article 48)
     You cannot approve less than 14 days.
```

**D. Leave Accrual Engine**
```
Join date: July 1, 2025
Year 1 (Jul 2025 - Jun 2026): 14 days entitled
Year 2 (Jul 2026 - Jun 2026): 15 days entitled
Year 3 (Jul 2027 - Jun 2028): 16 days entitled
...and so on

System auto-calculates:
- Current entitlement based on years of service
- Days taken this year
- Remaining balance
- Carry-forward amount (if company policy allows)
```

---

## 3. ALLOWANCES — FLEXIBLE WITH LEGAL GUARDRAILS

### What the law says

The Ethiopian tax law does NOT restrict:
- What TYPE of allowance a company can create
- How MUCH a company can pay as allowance

The law DOES restrict:
- What is TAX-EXEMPT (and the caps)
- What is PENSIONABLE (basic salary only, not allowances)

### System Design: Allowance Types

**A. Pre-Built Types (System Knows the Rules)**

| Type | Tax Treatment | Pension Treatment | System Behavior |
|---|---|---|---|
| Transport | Exempt up to ETB 2,200 or 25% of salary | Not pensionable | Auto-calculate exempt amount |
| Hardship | Exempt based on zone | Not pensionable | Auto-apply zone rules |
| Per Diem | Exempt up to ETB 255/day or 4% of salary | Not pensionable | Auto-calculate with distance check |
| Housing | Fully taxable | Not pensionable | No exemption |
| Communication | Fully taxable | Not pensionable | No exemption |
| Medical | Fully exempt (actual cost) | Not pensionable | Requires documentation |
| Food & Beverage | Partial exempt (sector-specific) | Not pensionable | Auto-check sector |
| 13th Month | Fully taxable | Not pensionable | Not required by law |

**B. Company-Created Allowance Types**

The owner can create custom types:
```
Examples:
  - "Remote work allowance"
  - "Education allowance"
  - "Transport fuel allowance"
  - "Uniform allowance"
```

System behavior when creating a new type:
```
┌─────────────────────────────────────────────────────┐
│  Create New Allowance Type                          │
│                                                     │
│  Name: [Remote work allowance    ]                  │
│                                                     │
│  Tax treatment:                                     │
│  ○ Taxable (added to income)                        │
│  ○ Tax-exempt (with cap)                            │
│  ○ Partially exempt                                 │
│                                                     │
│  If tax-exempt:                                     │
│  Max exempt amount: [ETB 1,000    ] per month       │
│                                                     │
│  ⚖️ Ethiopian tax law reference:                    │
│  Transport allowance is exempt up to ETB 2,200      │
│  or 25% of salary (whichever is lower).             │
│  Custom allowances are fully taxable unless          │
│  specifically exempted by ERCA directive.            │
│                                                     │
│  ⚠️ If this allowance is not in ERCA's list of      │
│  exempt allowances, it will be treated as taxable.  │
│                                                     │
│  [Create Allowance]                                 │
└─────────────────────────────────────────────────────┘
```

**C. What-if Scenarios for Allowances**

```
Scenario: Owner wants to set transport allowance at ETB 3,000
System shows:
  ℹ️ Transport allowance: ETB 3,000
  📊 Tax-exempt cap: ETB 2,200 (or 25% of salary)
  📊 Employee's cap: ETB 2,200 (25% of ETB 10,000 = ETB 2,500, but ETB 2,200 is lower)
  💰 Taxable excess: ETB 800 (3,000 - 2,200)
  💡 Employee will pay tax on the ETB 800 excess

  This is LEGAL. You can pay more than the exempt cap.
  The excess just becomes taxable income.

  [Proceed] [Adjust to ETB 2,200 for full exemption]

Scenario: Owner creates "Hardship allowance" of ETB 200 for Asosa
System shows:
  ❌ BLOCK: Minimum hardship allowance for Asosa is ETB 500
     (Directive No. 21/2001)
     You cannot set it below the legal minimum.

  Minimum: ETB 500
  Your amount: ETB 200
  Please increase to at least ETB 500.

Scenario: Law changes transport cap from ETB 2,200 to ETB 3,000
System shows:
  📢 TAX LAW UPDATE
  Transport allowance exempt cap changed from ETB 2,200 to ETB 3,000
  Effective: January 1, 2027

  Affected employees: 12
  Previous exempt amount: ETB 2,200
  New exempt amount: ETB 3,000

  Impact: Employees with transport allowance between ETB 2,200-3,000
  will no longer pay tax on the excess.

  [View affected employees] [Acknowledge]
```

**D. Allowance Change Impact Preview**

When owner changes any allowance:
```
┌─────────────────────────────────────────────────────┐
│  Change Preview: Transport Allowance                 │
│                                                     │
│  Employee: Dawit Mekonnen (EMP001)                  │
│  Current transport: ETB 1,500                       │
│  New transport: ETB 2,500                           │
│                                                     │
│  BEFORE CHANGE:                                     │
│  Gross: ETB 12,000 | Tax: ETB 1,245 | Net: ETB 10,110│
│                                                     │
│  AFTER CHANGE:                                      │
│  Gross: ETB 13,000 | Tax: ETB 1,395 | Net: ETB 10,960│
│                                                     │
│  Net increase: ETB 850/month                        │
│  Annual impact: ETB 10,200                          │
│  Employer cost increase: ETB 1,000/month            │
│                                                     │
│  Tax-exempt portion: ETB 2,200 (cap)                │
│  Taxable excess: ETB 300                            │
│                                                     │
│  [Confirm Change] [Cancel]                          │
└─────────────────────────────────────────────────────┘
```

---

## 4. SEVERANCE — WIRE IT IN

### What needs to happen

**A. Termination Flow with Severance**

```
Step 1: Owner clicks "Terminate Employee"
Step 2: System shows termination form
        - End date
        - Reason (dropdown: resignation, for cause, redundancy, mutual agreement)
Step 3: System calculates severance IN REAL-TIME
        - Shows years of service
        - Shows formula
        - Shows amount
        - Shows cap if applicable
Step 4: Owner confirms with password
Step 5: System soft-deletes employee
Step 6: System creates final settlement record:
        - Outstanding salary
        - Severance pay
        - Unused leave encashment
        - Any pending deductions
        - Net final payment
Step 7: System generates settlement document
Step 8: System logs everything in audit trail
```

**B. Severance Calculation Display**

```
┌─────────────────────────────────────────────────────┐
│  Severance Calculation: Dawit Mekonnen              │
│                                                     │
│  Start date: July 1, 2020                           │
│  End date: July 15, 2026                            │
│  Years of service: 6.04 years                       │
│  Monthly salary: ETB 15,000                         │
│                                                     │
│  Reason: Redundancy                                 │
│  Eligible: ✅ Yes                                   │
│                                                     │
│  Formula: ETB 15,000 × 6.04 = ETB 90,600           │
│  Cap: 12 months × ETB 15,000 = ETB 180,000         │
│  Capped: No (ETB 90,600 < ETB 180,000)             │
│                                                     │
│  Severance payable: ETB 90,600                      │
│                                                     │
│  Reference: Labor Proclamation 1156/2019, Art. 40-42│
│                                                     │
│  [Confirm Termination] [Cancel]                     │
└─────────────────────────────────────────────────────┘
```

**C. Final Settlement Document**

```
┌─────────────────────────────────────────────────────┐
│  FINAL SETTLEMENT — Dawit Mekonnen (EMP001)         │
│  Date: July 15, 2026                                │
│                                                     │
│  EARNINGS:                                          │
│  Outstanding salary (Jul 1-15): ETB 7,500           │
│  Severance pay: ETB 90,600                          │
│  Unused leave (3 days): ETB 2,143                   │
│  Total earnings: ETB 100,243                        │
│                                                     │
│  DEDUCTIONS:                                        │
│  Pension (7% of salary): ETB 525                    │
│  Tax on salary portion: ETB 845                     │
│  Outstanding loan: ETB 3,000                        │
│  Total deductions: ETB 4,370                        │
│                                                     │
│  NET FINAL PAYMENT: ETB 95,873                      │
│                                                     │
│  Payment method: CBE Transfer                       │
│  Account: 1000123456789                             │
│                                                     │
│  [Generate PDF] [Process Payment]                   │
└─────────────────────────────────────────────────────┘
```

---

## 5. BANK ACCOUNTS — TRUST AND VERIFICATION

### The Problem
- Ethiopian banks don't have public APIs for account verification
- Manual CSV upload to bank portals is the norm
- Wrong account numbers = failed transfers = angry employees
- Same account assigned to two employees = fraud risk

### What We Can Build

**A. Account Verification Workflow**

```
Step 1: Owner enters employee's bank account
Step 2: System validates format (13 digits for CBE, etc.)
Step 3: System flags suspicious patterns:
        - Account number is same as another employee → BLOCK
        - Account number changed from last month → FLAG
        - Account number doesn't match bank prefix → WARN
Step 4: System asks owner to verify:
        "Please confirm this account belongs to [Employee Name]"
        Options:
        - "I verified with the employee" (owner attestation)
        - "I have a bank statement" (upload proof)
Step 5: System records verification in audit trail
```

**B. Bank File Integrity Checks**

Before generating bank file:
```
✅ All account numbers valid format
✅ No duplicate accounts
✅ No duplicate employees
✅ All net pays positive
✅ Account changes flagged
✅ Total matches sum of individual amounts
✅ File generates with checksum

If any check fails → BLOCK with clear message
```

**C. Post-Payment Reconciliation**

After bank processes the file:
```
Step 1: Owner uploads bank's response file (reconciliation)
Step 2: System matches each payment:
        - Successful: marks as "paid"
        - Failed: marks as "bank_rejected" with reason
Step 3: For rejected payments:
        - System shows which employees weren't paid
        - System asks for corrected account numbers
        - System generates correction file
Step 4: System tracks payment status per employee
```

**D. Multi-Bank Support**

Expand bank support beyond current 3:
```
Currently supported: CBE, Dashen, Awash, Telebirr
Should add: Bank of Abyssinia, Wegagen, NIB, Bunna, Zemen, Lion

Each bank has different:
- Account number format
- File format requirements
- Upload portal interface

System should:
- Store bank-specific validation rules
- Generate bank-specific file formats
- Allow owner to set default bank
- Support employees at different banks in same run
```

---

## 6. TRANSLATION — MAKE IT WORK

### Approach: Owner-Driven Translation

**A. Extract All English Strings**

I'll create a file with every English string in the system. You translate them. I'll integrate.

**B. Translation File Format**

```json
{
  "meta": {
    "language": "am",
    "language_name": "አማርኛ",
    "version": "1.0",
    "last_updated": "2026-07-13"
  },
  "strings": {
    "dashboard.title": "Dashboard",
    "dashboard.title_translated": "",
    "employees.title": "Employees",
    "employees.title_translated": "",
    "payroll.title": "Payroll",
    "payroll.title_translated": "",
    "common.save": "Save",
    "common.save_translated": "",
    "common.cancel": "Cancel",
    "common.cancel_translated": ""
  }
}
```

**C. Notification via Telegram (Instead of SMS)**

Telegram is free, widely used in Ethiopia, and doesn't require SMS gateway integration.

What to build:
```
1. Company links Telegram bot to their account
2. Employee links their Telegram to their employee profile
3. System sends notifications via Telegram:
   - "Your payslip for July 2026 is ready"
   - "ERCA filing due in 3 days"
   - "Your leave request was approved"
   - "Salary credited to CBE account"
4. Owner can broadcast to all employees:
   - "Payroll has been processed"
   - "Office closed on [holiday]"
```

**D. Notification Preferences**

Each user (owner/employee) can choose:
```
Notification preferences:
  ☑ Telegram notifications
  ☐ Email notifications
  ☐ SMS notifications (if available)

Notify me about:
  ☑ Payslip generated
  ☑ Salary credited
  ☑ Leave request status
  ☑ Deadline reminders (owner only)
  ☐ System updates
```

---

## 7. WHAT-IF SCENARIOS — SHOW THE IMPACT

### A. Salary Change Impact

```
┌─────────────────────────────────────────────────────┐
│  Salary Change Preview                              │
│                                                     │
│  Employee: Hana Tesfaye (EMP002)                    │
│                                                     │
│  CURRENT:                                           │
│  Basic: ETB 8,000 | Allowances: ETB 1,000          │
│  Pension: ETB 560 | Tax: ETB 645                    │
│  Net: ETB 7,795                                     │
│                                                     │
│  PROPOSED:                                          │
│  Basic: ETB 12,000 | Allowances: ETB 1,500         │
│  Pension: ETB 840 | Tax: ETB 1,245                  │
│  Net: ETB 11,415                                    │
│                                                     │
│  IMPACT:                                            │
│  Net increase: ETB 3,620/month (46% increase)       │
│  Annual increase: ETB 43,440                        │
│  Employer cost increase: ETB 4,280/month            │
│  (includes employer pension increase)               │
│                                                     │
│  Tax bracket change: 20% → 25% bracket              │
│                                                     │
│  [Apply Change] [Adjust] [Cancel]                   │
└─────────────────────────────────────────────────────┘
```

### B. New Employee Impact

```
┌─────────────────────────────────────────────────────┐
│  New Employee Impact                                │
│                                                     │
│  Adding: Abebe Kebede (EMP015)                      │
│  Basic: ETB 20,000 | Allowances: ETB 3,000         │
│                                                     │
│  MONTHLY COST TO COMPANY:                           │
│  Gross salary: ETB 23,000                           │
│  Employer pension (11%): ETB 2,200                  │
│  Total employer cost: ETB 25,200                    │
│                                                     │
│  EMPLOYEE RECEIVES:                                 │
│  Pension deduction: ETB 1,400                       │
│  Tax: ETB 2,445                                     │
│  Net pay: ETB 19,155                                │
│                                                     │
│  ANNUAL IMPACT:                                     │
│  Total employer cost: ETB 302,400                   │
│  ERCA filing: +1 employee                           │
│  POEPA filing: +1 employee                          │
│                                                     │
│  [Add Employee] [Cancel]                            │
└─────────────────────────────────────────────────────┘
```

### C. Medical Expense Sharing

```
┌─────────────────────────────────────────────────────┐
│  Medical Expense Configuration                      │
│                                                     │
│  Employee: Dawit Mekonnen (EMP001)                  │
│  Medical bill: ETB 5,000                            │
│                                                     │
│  SHARING OPTIONS:                                   │
│  ○ Company pays 100% (fully exempt from tax)        │
│  ○ Company pays 80%, Employee pays 20%              │
│  ○ Company pays fixed amount: [ETB 3,000]           │
│  ○ Employee pays 100% (not relevant for payroll)    │
│                                                     │
│  TAX TREATMENT:                                     │
│  Medical expenses paid by employer are FULLY EXEMPT │
│  from income tax (ERCA directive).                  │
│                                                     │
│  If company pays ETB 4,000:                         │
│  - Employee taxable income: unchanged               │
│  - Employee saves: ETB 4,000 × marginal tax rate    │
│  - Company records: medical expense (deductible)    │
│                                                     │
│  [Apply] [Cancel]                                   │
└─────────────────────────────────────────────────────┘
```

### D. Law Change Notification

```
┌─────────────────────────────────────────────────────┐
│  ⚖️ TAX LAW UPDATE — Action Required               │
│                                                     │
│  Change: Personal relief increased from ETB 150     │
│  to ETB 300 per month                               │
│                                                     │
│  Effective: January 1, 2027                         │
│  Source: Proclamation No. XXXX/2026                 │
│                                                     │
│  IMPACT ON YOUR EMPLOYEES:                          │
│  All employees: Tax decreases by ETB 150/month      │
│  Average savings per employee: ETB 150/month        │
│  Total company savings: ETB 0 (employee benefit)    │
│                                                     │
│  WHAT YOU NEED TO DO:                               │
│  Nothing. The system will automatically apply       │
│  the new relief starting January 2027 payroll.      │
│                                                     │
│  [View Details] [Acknowledge]                       │
└─────────────────────────────────────────────────────┘
```

---

## 8. KEEPING IT SIMPLE — EASY STEPS

### Design Principle: Maximum 3 Clicks to Anything

```
Add employee:     Dashboard → Add Employee → Fill form → Done
Run payroll:      Dashboard → Run Payroll → Upload CSV → Review → Approve → Done
View payslip:     Dashboard → Employee → Payslips → Download
Generate report:  Dashboard → Reports → Select type → Download
File ERCA:        Dashboard → Filing → Review → Download → Done
```

### The "One Screen" Payroll Run

For a company with 10 employees, the entire payroll should be visible on ONE screen:

```
┌─────────────────────────────────────────────────────────────────┐
│  PAYROLL — July 2026 (Sene 2018)                               │
│                                                                  │
│  ⚠️ 2 employees missing TIN  │  ✅ ERCA filing: 12 days left    │
│                                                                  │
│  ┌─────┬──────────┬────────┬───────┬───────┬───────┬──────────┐ │
│  │ ID  │ Name     │ Gross  │ Tax   │Pension│ Net   │ Status   │ │
│  ├─────┼──────────┼────────┼───────┼───────┼───────┼──────────┤ │
│  │E001 │ Dawit    │12,000  │1,245  │ 840   │9,915  │ ✅       │ │
│  │E002 │ Hana     │ 8,500  │ 645   │ 560   │7,295  │ ✅       │ │
│  │E003 │ Kebede   │15,000  │1,845  │1,050  │12,105 │ ✅       │ │
│  │E004 │ Sara     │ 6,000  │ 345   │ 420   │5,235  │ ⚠️ No TIN│ │
│  │E005 │ Yonas    │20,000  │2,945  │1,400  │15,655 │ ✅       │ │
│  └─────┴──────────┴────────┴───────┴───────┴───────┴──────────┘ │
│                                                                  │
│  TOTALS: Gross: 61,500 │ Tax: 7,025 │ Pension: 4,270 │ Net: 50,205│
│                                                                  │
│  [Generate Bank File] [Download ERCA Report] [Approve Payroll]  │
└─────────────────────────────────────────────────────────────────┘
```

No wizards. No multiple pages. Everything visible. Everything actionable.

---

## NEXT STEPS

### Immediate (This Week)
1. Extract all English strings → you translate → I integrate
2. Wire severance into termination route
3. Fix ERCA deadline (8 → 25)
4. Add allowance breakdown to Employee model

### Next 2 Weeks
5. Tax exemption layer (transport, hardship, per diem)
6. Leave accrual engine
7. What-if scenario previews
8. Telegram notification system

### Next Month
9. Three-layer allowance config UI
10. Bank account verification workflow
11. ERCA filing preparation wizard
12. Full Amharic/Afaan Oromoo UI

---

*This is beyond what Kimi suggested. This is building the real deal.*
