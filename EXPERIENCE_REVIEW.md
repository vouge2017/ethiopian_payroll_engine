# EthioPayroll — Product Experience Review

**Date:** 2026-08-04
**Reviewer:** Head of Product Design
**Scope:** Every major workflow, every critical screen, every user journey
**Standard:** Would an Ethiopian accountant trust this enough to process real payroll?

---

# Part 1 — The Core Problem

The product works. The calculations are correct. The data is secure.

But the product is not designed around how accountants think.

It's designed around how engineers think: models, routes, templates, CRUD.

An accountant doesn't think in "routes." They think in tasks:

1. I need to pay my employees
2. I need to file taxes
3. I need to prove I did it right

Every screen should reduce the distance between "I need to..." and "Done."

Right now, the product adds distance. It makes the accountant think about the system instead of thinking about their work.

---

# Part 2 — Trust Scoring

Every critical page scored on four questions.

## Dashboard

| Question | Score | Why |
|----------|-------|-----|
| Do I understand what this page is for? | 7/10 | Shows metrics and recent runs. But the first thing I see is "Compliance Score 100%" — does that mean I'm done? What do I do next? |
| Do I trust the information shown? | 5/10 | The compliance score is a number with no context. What does 100% mean? What was checked? What wasn't? |
| Do I know what happens next? | 4/10 | No clear primary action. "Run Payroll" is one of 4 buttons in the header. "Quick Start" appears only when no payroll exists. |
| Can I safely recover from mistakes? | 6/10 | Recent runs table shows status. But no undo, no "what changed since last month." |

**Dashboard trust score: 5.5/10**

## Add Employee

| Question | Score | Why |
|----------|-------|-----|
| Do I understand what this page is for? | 9/10 | Clear title, clear form. Ethiopian naming is excellent. |
| Do I trust the information shown? | 7/10 | Phone validation is good. But "More details (optional)" hides TIN, bank account, department — these are NOT optional for payroll. |
| Do I know what happens next? | 6/10 | After saving, I'm dumped back to the employee list. No confirmation of what was saved. No "add another" option. |
| Can I safely recover from mistakes? | 5/10 | No inline edit from the list. Must click into detail page, then edit. No undo for "deactivate." |

**Add Employee trust score: 6.75/10**

## Payroll Upload (new wizard)

| Question | Score | Why |
|----------|-------|-----|
| Do I understand what this page is for? | 8/10 | Clear stepper: Upload → Review → Validate → Confirm. "Use Last Payroll" button is good. |
| Do I trust the information shown? | 8/10 | Inline preview shows parsed data. Validation shows blocks/flags/warnings with severity. Cash flow check on confirm page. |
| Do I know what happens next? | 7/10 | Stepper shows progress. But "Validate & Process" is ambiguous — does it process or just validate? |
| Can I safely recover from mistakes? | 7/10 | "Back" button exists. "Clear & Start Over" exists. But once approved, only 1-hour undo window. |

**Payroll Upload trust score: 7.5/10**

## Payroll Confirm

| Question | Score | Why |
|----------|-------|-----|
| Do I understand what this page is for? | 8/10 | Clear summary cards. "Confirm Payroll Processing" title. |
| Do I trust the information shown? | 7/10 | Shows gross, tax+pension, net. Employee breakdown is expandable. Tax brackets shown. But trust badges ("Tax calculated ✓") feel decorative, not informative. |
| Do I know what happens next? | 5/10 | "This cannot be undone" is scary. But there IS an undo (1-hour window). The message is misleading. |
| Can I safely recover from mistakes? | 4/10 | Undo exists but the page says "cannot be undone." If I believe the page, I won't try to undo. If I know about the undo, I don't trust the "cannot be undone" message. Contradictory. |

**Payroll Confirm trust score: 6/10**

## Reports

| Question | Score | Why |
|----------|-------|-----|
| Do I understand what this page is for? | 7/10 | "Reports & Compliance" title. Three download buttons. Quick links to history, audit, analytics. |
| Do I trust the information shown? | 6/10 | Compliance score is a number. No breakdown of what was checked. No "last verified" date. |
| Do I know what happens next? | 5/10 | I can download reports. But what about filing? Is there a filing workflow? No guidance on what to do with the downloaded files. |
| Can I safely recover from mistakes? | 6/10 | Filing history exists. Audit log exists. But no "re-generate report" if I made a mistake. |

**Reports trust score: 6/10**

## Employee Detail

| Question | Score | Why |
|----------|-------|-----|
| Do I understand what this page is for? | 8/10 | Shows employee info, salary, actions. |
| Do I trust the information shown? | 7/10 | Four metric cards (basic, allowances, gross, payment). But no history — when did salary change? What was last month's payslip? |
| Do I know what happens next? | 5/10 | Many buttons: Edit, Terminate, Deactivate, Invite. No guidance on which to use when. |
| Can I safely recover from mistakes? | 4/10 | Terminate and Deactivate are both available. What's the difference? No explanation. Confirmation dialogs are generic ("Are you sure?"). |

**Employee Detail trust score: 6/10**

---

# Part 3 — Task-Based Usability Analysis

## Task 1: First Payroll Run (from empty database)

### Current flow:

| Step | Screen | Clicks | Decisions | Typing | Issue |
|------|--------|--------|-----------|--------|-------|
| 1 | Register | 1 | 4 fields | ~80 chars | OK |
| 2 | Dashboard | 0 | 0 | 0 | "Quick Start" card appears. Good. |
| 3 | Quick Start | 1 | 0 | Paste data | Only captures name, phone, salary. Missing TIN, bank, department. |
| 4 | Dashboard | 1 | 0 | 0 | "Open Payroll Spreadsheet" button. Good. |
| 5 | Spreadsheet | 1 | 0 | 0 | Shows all employees in editable table. But columns are limited. |
| 6 | Process | 1 | 0 | 0 | "Process Payroll" button. Where does it go? |
| 7 | Validation | 0 | 0 | 0 | Shows blocks/flags. Good. |
| 8 | Confirm | 1 | 1 | 1 | Enter password. Approve. |
| 9 | Results | 0 | 0 | 0 | Download payslips. Done. |

**Total: ~9 steps, ~10 clicks, ~80 characters typed, ~15 minutes estimated**

### Issues:

1. **Quick Start is a trap.** It captures only 3 fields. The accountant then has to go back and add TIN, bank account, department for every employee. The "quick" path creates more work later.

2. **No guidance between steps.** After Quick Start, the dashboard shows "Open Payroll Spreadsheet" — but why? What am I supposed to do there? The system doesn't explain.

3. **Spreadsheet → Process is unclear.** Where is the "Process" button? Is it on the spreadsheet page? On the dashboard? The accountant has to figure this out.

4. **No "what changed" summary.** After processing, the results page shows totals. But not "3 employees added, 1 salary changed from last month."

### Ideal flow:

| Step | Screen | What the accountant sees |
|------|--------|-------------------------|
| 1 | Register | 4 fields. Done. |
| 2 | Dashboard | "Welcome! Here's what to do next: 1. Add employees, 2. Run payroll, 3. File taxes." |
| 3 | Add Employees | Full form (not Quick Start). All fields. Bulk import available. |
| 4 | Dashboard | "You have 3 employees. Ready to run payroll?" → One button. |
| 5 | Payroll Review | Pre-filled from employee data. Show what changed from last month. |
| 6 | Validation | Clear: "3 issues found. Fix them." → Inline fixes. |
| 7 | Confirm | "Here's what will happen: 3 payslips, ETB X total, bank file ready." → Approve. |
| 8 | Done | "Payroll complete. Next: Download ERCA filing (due in 12 days)." |

**Target: 8 steps, ~8 clicks, ~5 minutes for repeat payroll**

---

## Task 2: Add a New Employee Mid-Month

### Current flow:

| Step | Screen | Issue |
|------|--------|-------|
| 1 | Navigate to Employees | 2 clicks from sidebar |
| 2 | Click "Add Employee" | 1 click |
| 3 | Fill form | 3 fields visible (name, phone, salary). 7 fields hidden in "More details" |
| 4 | Save | Redirected to employee list |
| 5 | Find the employee | Search or scroll |
| 6 | Click into detail | Verify everything is correct |

**Issues:**
- TIN is hidden in "More details" — but it's required for ERCA filing
- Bank account is hidden — but it's required for disbursement
- No "Add another" button — must navigate back to list, then back to form
- No confirmation of what was saved
- No guidance on "you also need to add overtime/attendance for this employee before running payroll"

---

## Task 3: Fix an Error After CSV Upload

### Current flow:

| Step | Screen | Issue |
|------|--------|-------|
| 1 | Validation results | Shows blocks with hints |
| 2 | "Back to Upload" | Must re-upload entire CSV |
| 3 | Fix CSV in Excel | External tool |
| 4 | Re-upload | All validation runs again |

**Issues:**
- No inline editing after upload
- Must fix errors in Excel, then re-upload
- No "fix this one employee" option
- The spreadsheet editor exists but it's a separate entry point, not integrated into the validation flow

---

## Task 4: Prepare ERCA Filing

### Current flow:

| Step | Screen | Issue |
|------|--------|-------|
| 1 | Navigate to Reports | 2 clicks |
| 2 | Select period | Dropdown |
| 3 | Download ERCA report | .xlsx file |
| 4 | Open in Excel | External tool |
| 5 | Review | What am I looking for? |
| 6 | Upload to ERCA portal | External process |

**Issues:**
- No guidance on what to do with the downloaded file
- No checklist: "Is this complete? Are all employees included? Are TINs correct?"
- No preview before download
- No filing status tracking (did I file? when?)
- No reminder that filing is due

---

## Task 5: Approve Payroll

### Current flow:

| Step | Screen | Issue |
|------|--------|-------|
| 1 | Navigate to payroll run | From results page or runs list |
| 2 | Review summary | 4 metric cards |
| 3 | Expand employee details | Click each employee to see breakdown |
| 4 | Cash flow check | Enter bank balance manually |
| 5 | Enter password | Security step |
| 6 | Check confirmation checkbox | |
| 7 | Click approve | |

**Issues:**
- Must expand each employee individually to see details — no summary table
- Cash flow check requires manual bank balance entry — why doesn't it remember?
- "This cannot be undone" is misleading — there IS a 1-hour undo
- Trust badges ("Tax calculated ✓") are decorative — they don't show WHAT was verified
- No comparison with last month — "is this right?" requires memory

---

# Part 4 — Screen-by-Screen Analysis

## Screens That Are Overloaded

### 1. Payroll Confirm Page
**What's on it:** Summary cards + employee breakdown (expandable per employee) + tax bracket details + cash flow check + trust badges + password + MFA + confirmation checkbox + approve button + cancel button

**Problem:** This page tries to be everything: review tool, confidence builder, and approval gate. It's too much.

**Fix:** Split into two sub-steps:
- **Review:** Summary table + comparison with last month + "looks good" button
- **Approve:** Password + checkbox + approve. Clean, focused, one decision.

### 2. Employee Detail Page
**What's on it:** 4 metric cards + employee info + edit/terminate/deactivate/invite buttons + overtime + allowances + deductions + leave + payslips + profile changes

**Problem:** 480+ lines of template. Too many actions visible at once. Terminate and Deactivate are both available — what's the difference?

**Fix:** Organize into tabs: Overview | Payroll | Leave | Actions. Hide destructive actions behind a "More" menu.

### 3. Dashboard
**What's on it:** 4 metric cards + compliance badges + action needed section + charts + compliance deadlines + overtime alert + recent runs table + first-run wizard

**Problem:** Everything is the same visual weight. No priority. No clear "do this next."

**Fix:** Hero section with ONE primary action. Secondary content below the fold.

---

## Screens That Need More Emphasis

### 1. Validation Results
**Current:** Shows blocks/flags/warnings in tables. Action buttons at the bottom.

**Problem:** The most important information (what's blocking me) is in the middle of the page. The action buttons are below the fold.

**Fix:** Large status banner at top: "❌ 3 issues must be fixed." Issues listed with inline fix buttons. "Continue" button sticky at bottom.

### 2. ERCA Filing Preparation
**Current:** Download button on Reports page. That's it.

**Problem:** Filing is the most important compliance task. It gets one button.

**Fix:** Dedicated filing workflow: Preview → Verify → Download → Track filing status → Reminder

---

## Information That Should Be Hidden Until Needed

1. **Tax bracket breakdown** — Don't show by default. Show only when user clicks "Show calculation."
2. **Employer pension** — Employee doesn't need to see this. Show only on employer-facing reports.
3. **Audit log details** — Show summary by default. Details on click.
4. **API keys** — Hidden in team settings. Should be in a dedicated "Integrations" section.

---

## Information That's Missing From Critical Screens

### Dashboard:
- No "what changed since last month" summary
- No upcoming deadline with specific action needed
- No "last payroll was on X, next payroll due by Y"

### Employee List:
- No salary change indicator
- No "new this month" badge
- No quick actions (edit, view payslip) without clicking into detail

### Payroll Results:
- No comparison with previous month
- No "X employees added, Y salary changes" summary
- No link to "what to do next" (download reports, file ERCA)

### Reports:
- No filing status (filed/not filed/overdue)
- No preview before download
- No guidance on what to do with downloaded files

---

# Part 5 — Benchmarking Against Market Leaders

## Company Onboarding

| Aspect | EthioPayroll | Rippling | Gusto | Deel |
|--------|-------------|----------|-------|------|
| Time to first value | ~15 min (Quick Start) | ~5 min (guided wizard) | ~10 min (step-by-step) | ~3 min (invite link) |
| Guided setup | No. Dashboard shows "Quick Start" card. | Yes. Multi-step wizard with progress. | Yes. Checklist with progress bar. | Yes. Minimal — just invite. |
| What's captured | Name, phone, salary (Quick Start misses TIN, bank, dept) | Company info, tax IDs, bank accounts, employees | Company info, bank, tax setup, employees | Company info, employees |
| Confidence level | Low. "Did I do this right?" | High. Each step validates before moving on. | High. Progress bar shows completion. | High. Minimal steps. |

**Gap:** No guided onboarding wizard. Quick Start is a shortcut that creates data quality problems.

## Employee Import

| Aspect | EthioPayroll | Deel | Gusto | Rippling |
|--------|-------------|------|-------|----------|
| Bulk import | CSV upload or Quick Start paste | CSV upload with column mapping | CSV upload with preview | CSV upload with auto-mapping |
| Column mapping | No. Fixed CSV format. | Yes. Auto-detects columns. | Yes. Shows preview with mapping. | Yes. AI-powered mapping. |
| Preview before import | Yes (Quick Start) / No (CSV upload) | Yes | Yes | Yes |
| Validation on import | Yes (missing TIN, bank, etc.) | Yes | Yes | Yes |
| Error recovery | Must fix CSV and re-upload | Inline editing before import | Inline editing | Inline editing |

**Gap:** No column mapping. No inline editing after import. Must use exact CSV format.

## Payroll Review

| Aspect | EthioPayroll | Gusto | Deel | Rippling |
|--------|-------------|-------|------|----------|
| Summary view | 4 metric cards + expandable per-employee | Dashboard with totals + drill-down | Clean summary + employee list | Summary + comparison |
| Comparison with last month | No | Yes (visual diff) | Yes | Yes |
| Validation | BLOCK/FLAG/WARN with hints | Real-time validation | Real-time validation | Real-time validation |
| Confidence before approval | Trust badges (decorative) | "All checks passed" + specific items | Clear status indicators | Verification checklist |
| Approval flow | Password + checkbox + MFA | One-click with confirmation | One-click with confirmation | Multi-step with review |

**Gap:** No month-over-month comparison. Trust badges are decorative, not informative.

## Payslip Generation

| Aspect | EthioPayroll | Gusto | Deel | BambooHR |
|--------|-------------|-------|------|----------|
| Format | PDF with Ethiopian font | PDF, clean design | PDF, multi-language | PDF |
| Delivery | Download (manual) | Auto-email to employees | Auto-email + portal | Auto-email + portal |
| Employee access | Self-service portal | Self-service portal | Self-service portal | Self-service portal |
| Batch download | ZIP file | Individual or batch | Individual or batch | Individual |
| Customization | Logo, company info | Full branding | Full branding | Limited |

**Gap:** No auto-email to employees. No branding customization beyond logo.

## Reports

| Aspect | EthioPayroll | Xero | Sage | Odoo |
|--------|-------------|------|------|------|
| Report types | 6 (ERCA, pension, bank, yearly, register, analytics) | 40+ | 50+ | 30+ |
| Custom reports | No (column config only) | Yes (report builder) | Yes | Yes |
| Filing workflow | Download only | Download + e-filing (some countries) | Download + e-filing | Download + e-filing |
| Filing status tracking | No | Yes | Yes | Yes |
| Preview before download | No | Yes | Yes | Yes |

**Gap:** No filing workflow. No status tracking. No preview. No custom reports.

---

# Part 6 — Redesign Proposals

## Proposal 1: Dashboard Redesign

### Current issues:
- Everything has the same visual weight
- No clear primary action
- No "what changed" summary
- Compliance score is meaningless without context

### Proposed hierarchy:

```
┌─────────────────────────────────────────────────────────┐
│  Good morning, Tigist. Here's your payroll status.      │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  NEXT ACTION: Run payroll for Sene 2018         │   │
│  │  3 employees · Due by July 25                   │   │
│  │  [Run Payroll →]                                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Last payroll: May 2018 · ETB 35,500 total · ✅ Filed  │
│  [View Details] [Download Reports]                      │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Quick Actions:                                         │
│  [+ Add Employee]  [📊 Reports]  [⏰ Attendance]       │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Compliance Checklist:                                  │
│  ✅ Payroll processed (May 25)                          │
│  ✅ ERCA filed (May 28)                                 │
│  ✅ Pension remitted (May 12)                           │
│  ⬜ Payroll for June — due in 12 days                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Changes:**
1. Hero section with ONE primary action
2. Last payroll summary (not metric cards)
3. Compliance as a checklist (not a score)
4. Quick actions as buttons (not buried in sidebar)

---

## Proposal 2: Payroll Flow Redesign

### Current:
Upload → Validation → Confirm → Done (4 pages, ~10 clicks)

### Proposed:
Single page with progressive disclosure

```
┌─────────────────────────────────────────────────────────┐
│  Run Payroll — Sene 2018                                │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Source: [Use Last Month ▼] [Upload CSV] [Paste]│   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  3 employees · ETB 35,500 total                  │   │
│  │                                                  │   │
│  │  Name          Basic    Allow.   Gross    Net    │   │
│  │  Dawit M.      10,000   2,000    12,000   9,260 │   │
│  │  Hana T.        5,000     500     5,500   4,620 │   │
│  │  Kebede A.     15,000   3,000    18,000  13,068 │   │
│  │                                                  │   │
│  │  [✏️ Edit] [↩️ Use Last Month]                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ✅ All checks passed                            │   │
│  │  ✅ No duplicates found                          │   │
│  │  ✅ All bank accounts valid                      │   │
│  │  ⚠️ Dawit's salary changed +20% (verify)        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Cash flow check:                                │   │
│  │  Your balance: [150,000    ]                     │   │
│  │  Payroll total: ETB 26,948                       │   │
│  │  Remaining: ETB 123,052 ✅                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel]                              [Approve Payroll]│
│                                                         │
│  By approving: payslips will be generated, bank file    │
│  will be created, employees will be notified.           │
│  You can undo within 1 hour.                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Changes:**
1. One page instead of four
2. Inline editing without re-uploading
3. Validation results inline, not on separate page
4. Cash flow remembers last balance
5. Clear "what happens next" message
6. Honest undo messaging

---

## Proposal 3: Reports Page Redesign

### Current:
Metric cards + download buttons + quick links

### Proposed:
Filing workflow with status tracking

```
┌─────────────────────────────────────────────────────────┐
│  Compliance — Sene 2018                                 │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  FILING STATUS                                   │   │
│  │                                                  │   │
│  │  ✅ Payroll processed     May 25                 │   │
│  │  ✅ Payslips distributed  May 25                 │   │
│  │  ✅ Bank file sent        May 26                 │   │
│  │  ⬜ ERCA filing           Due June 25 (21 days)  │   │
│  │  ⬜ Pension remittance    Due June 10 (6 days)   │   │
│  │                                                  │   │
│  │  [Download ERCA File] [Download Pension File]    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  WHAT TO DO WITH THESE FILES                     │   │
│  │                                                  │   │
│  │  1. Download the ERCA file (.xlsx)               │   │
│  │  2. Log in to the ERCA portal                    │   │
│  │  3. Upload the file                              │   │
│  │  4. Mark as filed below                          │   │
│  │                                                  │   │
│  │  [Mark ERCA as Filed ✓]                          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  HISTORY                                         │   │
│  │  May 2018 — Filed on May 28 ✅                   │   │
│  │  April 2018 — Filed on April 30 ✅               │   │
│  │  March 2018 — Filed on March 29 ✅               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Changes:**
1. Filing workflow instead of download buttons
2. Status tracking (filed/not filed/overdue)
3. Instructions on what to do with downloaded files
4. Filing history with dates

---

## Proposal 4: Employee List Redesign

### Current:
Standard table with search/filter

### Proposed:
Smart list with context

```
┌─────────────────────────────────────────────────────────┐
│  Employees (3 active)                    [+ Add Employee]│
│                                                         │
│  [🔍 Search...]  [Department ▼]  [Sort: Name ▼]        │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  👤 Dawit Mekonnen          Sales Manager       │   │
│  │     EMP001 · ETB 12,000/mo · CBE ****6789       │   │
│  │     📈 Salary +20% this month                   │   │
│  │     [View] [Edit] [Payslip]                     │   │
│  │─────────────────────────────────────────────────│   │
│  │  👤 Hana Tesfaye           Factory Worker       │   │
│  │     EMP002 · ETB 5,500/mo · Dashen ****4321     │   │
│  │     [View] [Edit] [Payslip]                     │   │
│  │─────────────────────────────────────────────────│   │
│  │  👤 Kebede Alemu           Accountant           │   │
│  │     EMP003 · ETB 18,000/mo · Awash ****3445     │   │
│  │     [View] [Edit] [Payslip]                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Changes:**
1. Card-based layout instead of table (better for mobile)
2. Salary change indicator
3. Quick actions without clicking into detail
4. Bank account partially masked for security

---

## Proposal 5: Add Employee Redesign

### Current:
3 visible fields + 7 hidden in "More details"

### Proposed:
All fields visible, organized in logical groups

```
┌─────────────────────────────────────────────────────────┐
│  Add Employee                                           │
│                                                         │
│  PERSONAL INFORMATION                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ስም / First Name    የአባት ስም / Father    የአያት ስም│   │
│  │  [________]          [________]          [______]│   │
│  │                                                  │   │
│  │  Phone               TIN (for ERCA filing)      │   │
│  │  [+251] [9XXXXXXXX]  [____________]             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  COMPENSATION                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Basic Salary (ETB)    Allowances (ETB)          │   │
│  │  [10,000      ]       [2,000       ]            │   │
│  │                                                  │   │
│  │  → Gross: ETB 12,000                             │   │
│  │  → Pension: ETB 700 (7%)                         │   │
│  │  → Tax: ETB 2,040                                │   │
│  │  → Net: ETB 9,260                                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  PAYMENT                                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Bank/Telebirr    Account Number                 │   │
│  │  [CBE        ▼]  [1000123456789      ]          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  WORK DETAILS (optional)                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Employee ID    Department    Position    Start  │   │
│  │  [auto     ]   [Sales    ]   [Manager]  [date]  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel]                               [Save Employee] │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Changes:**
1. All fields visible (no hidden sections)
2. Live payroll preview as you type salary
3. Bank account with dropdown for common banks
4. Logical grouping: Personal → Compensation → Payment → Work
5. TIN prominently placed (required for ERCA)

---

# Part 7 — The Accountant's Journey

## What an Ethiopian accountant actually does each month:

| Day | Task | Current System | Gap |
|-----|------|---------------|-----|
| 1st | Collect attendance data | Attendance import exists | No integration with biometric devices (manual export) |
| 1st-5th | Calculate overtime | Spreadsheet editor has OT columns | No automatic OT calculation from attendance |
| 5th-10th | Run payroll | CSV upload or spreadsheet | Works. But no "what changed" summary. |
| 10th-15th | Fix errors | Re-upload CSV | No inline editing |
| 15th-20th | Approve payroll | Password + MFA | Works. But confusing undo messaging. |
| 20th-25th | Generate reports | Download buttons | No filing workflow |
| 25th | File ERCA | Manual upload to portal | No guidance, no tracking |
| 25th-30th | Remit pension | Manual payment | No bank integration |

**The accountant touches 6 different screens to complete one payroll cycle.** A well-designed system would have 2-3.

---

# Part 8 — Where Accountants Would Hesitate

1. **"Is this the right number?"** — No comparison with last month. No explanation of what changed. The accountant has to remember.

2. **"Did I file this?"** — No filing status tracking. The accountant has to check their email or the ERCA portal.

3. **"Can I undo this?"** — The confirm page says "cannot be undone" but there IS an undo. Contradictory messaging destroys trust.

4. **"What do I do with this file?"** — Reports download as .xlsx with no instructions. The accountant has to know the ERCA portal workflow.

5. **"Is this employee's data complete?"** — TIN is hidden in "More details." Bank account is hidden. The accountant discovers missing data only when validation blocks them.

6. **"Why is the compliance score 100%?"** — The score is meaningless without context. What was checked? What wasn't? A perfect score feels suspicious.

7. **"Which button do I click?"** — Employee detail has Edit, Terminate, Deactivate, Invite, Archive. Too many destructive actions visible at once.

---

# Part 9 — Prioritized UX Improvements

| # | Improvement | Impact | Effort | Why |
|---|-------------|--------|--------|-----|
| 1 | **Dashboard hero section** with ONE primary action | Critical | 1 day | First impression. If the dashboard is confusing, the user leaves. |
| 2 | **Month-over-month comparison** on payroll review | Critical | 2 days | "Is this right?" is the #1 question accountants ask. Without comparison, they can't answer it. |
| 3 | **Filing workflow** with status tracking | Critical | 3 days | Filing is the highest-stakes task. Download-only is insufficient. |
| 4 | **Inline editing** after CSV upload | High | 2 days | Re-uploading CSVs is the biggest friction point. |
| 5 | **All fields visible** on Add Employee form | High | 1 day | Hidden fields cause validation failures. |
| 6 | **Honest undo messaging** on Confirm page | High | 0.5 days | Contradictory messaging destroys trust. |
| 7 | **Compliance checklist** instead of score | High | 1 day | A checklist is actionable. A score is not. |
| 8 | **Live payroll preview** on Add Employee | Medium | 1 day | Shows the accountant what the numbers will be before saving. |
| 9 | **Quick actions** on employee list | Medium | 1 day | Reduces clicks for common tasks. |
| 10 | **Report preview** before download | Medium | 1 day | Accountant can verify before committing. |
| 11 | **Guided onboarding** wizard | Medium | 3 days | First-time users need direction. |
| 12 | **Auto-email payslips** to employees | Low | 2 days | Reduces manual distribution. |

---

# Part 10 — The Single Most Important Insight

The product is built for the happy path.

An accountant using Excel has one advantage: they can see everything at once, they can change anything, and they don't have to trust a system they don't understand.

EthioPayroll needs to earn that trust by:

1. **Showing what changed** — not just what is
2. **Explaining what will happen** — not just asking for confirmation
3. **Allowing recovery** — not just saying "this cannot be undone"
4. **Guiding the workflow** — not just providing tools

The calculations are correct. The security is solid. The architecture is good.

The product needs to feel like it was designed by someone who has sat next to an Ethiopian accountant during payroll processing and understood their anxiety, their questions, and their need for control.

That's the gap between "a payroll system" and "the payroll system Ethiopian businesses trust."

---

*Report generated: 2026-08-04 22:45 GMT+8*
*Every observation based on actual template inspection, not assumptions.*
