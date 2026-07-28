# Customer Journey Blueprint
### Ethiopian Workforce Operating System
**Version:** 2.0 (Production-Grade)
**Date:** 2026-07-28
**Status:** Draft — Pending Product Director Approval
**Supersedes:** BUSINESS_CAPABILITY_BLUEPRINT.md (this document reorganizes all capabilities around customer journeys, not feature modules)

---

## Disclaimer

All Before/After time and error-rate figures in this document are **projected estimates** based on engineering analysis of current workflows, not measured pilot data. They will be replaced with actual measured data from pilot companies once the Customer Advisory Board validates them. Until then, they represent expected improvements, not proven outcomes.

---

---

## Why This Document Exists

The previous blueprint answered: *"What capabilities exist?"*

This document answers: *"Why will an Ethiopian business stop using Excel tomorrow and pay for us?"*

Every capability is now organized around **8 customer journeys** — the actual sequences of events that happen in an Ethiopian business. Each journey documents the before/during/after, the moments of trust, the automation opportunities, and the measurable business impact.

If a feature doesn't appear in a journey, it doesn't get built.

---

## Customer Maturity Levels

Not every Ethiopian company is ready for the same features. Maturity levels define where a company is and what they're ready for.

```
LEVEL 1 — Paper Payroll
  Uses: Paper records, handwritten payslips
  Ready for: Basic employee management, simple payroll

LEVEL 2 — Excel Payroll
  Uses: Excel spreadsheets, manual calculations
  Ready for: Full payroll engine, ERCA filing, bank files

LEVEL 3 — Payroll OS
  Uses: Platform for payroll only
  Ready for: Crosschecks, approval workflow, disbursement tracking

LEVEL 4 — Workforce OS
  Uses: Platform for all workforce operations
  Ready for: Manager approvals, HR lifecycle, accountant workspace

LEVEL 5 — Autonomous Workforce Intelligence
  Uses: Platform as operating system with proactive insights
  Ready for: Operational memory, proactive alerts, cash forecasting
```

Each journey and feature is tagged with the minimum maturity level required. Onboarding starts by assessing the customer's level and unlocking only what they're ready for.

---

## The First 30 Days

Customers buy outcomes. This is what the first month looks like.

```
DAY 1    Create account. Choose industry. Import employees from Excel.
DAY 2    Validate TINs and bank accounts. Fix flagged errors.
DAY 3    Import attendance history. Configure payroll calendar.
DAY 5    Run first payroll draft. Compare with Excel results.
DAY 7    Owner approves first payroll. Generate bank file.
DAY 10   Employees receive first payslips via portal.
DAY 14   ERCA report generated. Filed with confirmation.
DAY 21   First month complete. All crosschecks passed.
DAY 30   Trust Score: 92%. Company is live.
```

**This is the onboarding journey.** Every step has a measurable outcome. Every step builds trust.

---

## The Operating System Loop

Every workforce event fits into this continuous cycle:

```
    PLAN
    ↓
    HIRE
    ↓
    WORK
    ↓
    PAY
    ↓
    COMPLY
    ↓
    AUDIT
    ↓
    LEARN
    ↓
    IMPROVE
    ↓
    PLAN
```

The platform serves every stage. No Excel needed at any point.

---

## Product Principles

These are the rules that guide every decision. Engineering, product, sales, and implementation all follow these.

1. **Single source of truth** — no duplicate entry, ever
2. **Every calculation is explainable** — formula, inputs, law, timestamp
3. **Every workflow is auditable** — who, when, what changed
4. **Automation assists; humans approve** — the system proposes, the owner decides
5. **Compliance before convenience** — if it's not legally correct, don't do it
6. **Trust over speed when they conflict** — slower and right beats fast and wrong
7. **Configuration over customization** — change values, not code
8. **Every feature must remove Excel work** — if they still need Excel, we failed

---

## Architecture of Trust

This is how trust is built, one layer at a time:

```
    INPUT
    Employee · Attendance · Leave · Salary
    ↓
    VALIDATION
    TIN · Bank · Dates · Policies
    ↓
    CALCULATION
    Payroll Engine (tax, pension, deductions)
    ↓
    CROSSCHECK
    Attendance ↔ Payroll ↔ Bank ↔ ERCA ↔ Pension
    ↓
    APPROVAL
    Owner (with confidence score)
    ↓
    LOCK
    Immutable Snapshot (hash-chain protected)
    ↓
    OUTPUT
    Payslip · Bank File · ERCA Report · Audit Package
    ↓
    EVIDENCE
    Formula · Law · Timestamp · Approver
```

Every layer adds trust. By the time output reaches the employee, it has passed through validation, calculation, crosscheck, approval, and lock. Every layer is evidenced.

---

## The 10 Journeys

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

Every feature in the platform exists to serve one of these journeys.

---

# JOURNEY 0: Create Company & Migrate from Excel

**Trigger:** Business owner decides to switch from Excel.
**Outcome:** Company is live, employees imported, ready for first payroll — in one session.
**Maturity Required:** Level 1 → Level 3 (transition)

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Business Owner** | Creates account, chooses industry, approves import | Start |
| **Supporting: Accountant** | Reviews imported data, verifies TINs | Day 1 |
| **Supporting: HR** | Provides employee Excel, fixes flagged errors | Day 1 |
| **Waiting: System** | Validates data, maps columns, detects duplicates | During import |

### Business Value

- ✔ Migrate from Excel in 15 minutes, not 3 days
- ✔ Zero data re-entry — upload existing spreadsheet
- ✔ Invalid TINs and bank accounts caught before first payroll
- ✔ First payroll matches Excel results — verified, not hoped

---

## Before (Excel)

| Step | How it happens | Time | Pain |
|------|---------------|------|------|
| 1. Research options | Ask friends, Google, Telegram groups | Days/weeks | Decision paralysis |
| 2. Try software | Download, install, configure | Hours | Often abandoned |
| 3. Re-enter employees | Copy-paste from Excel | Hours | Double entry |
| 4. Verify data | Check TINs, banks, salaries | Hours | Error-prone |
| 5. First payroll | "Does this match my Excel?" | Hours | Uncertainty |

**Pain points:** Migration is so painful that most businesses never switch. The effort to re-enter everything exceeds the perceived benefit.

---

## During (Using the Platform)

| Step | How it happens | Time |
|------|---------------|------|
| 1. Create account | Phone + password | 1 min |
| 2. Choose industry | Select from list → template loads | 30 sec |
| 3. Import Excel | Upload existing spreadsheet | 2 min |
| 4. Auto-map columns | System matches headers to fields | Instant |
| 5. Validate data | System flags: invalid TINs, missing banks, duplicates | 30 sec |
| 6. Preview & fix | Review errors, fix inline | 5 min |
| 7. Configure policies | Payroll calendar, leave year, overtime rules | 3 min |
| 8. First payroll test | Run "test payroll" — compare with Excel results | 5 min |
| **Total** | | **15 minutes** |

---

## After (Measurable Impact)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Time to go live | Days/weeks | 15 minutes | **99% reduction** |
| Data re-entry | Full re-entry | Zero (import) | **Eliminated** |
| Migration errors | 10-15% | <1% (auto-validation) | **93% reduction** |
| First payroll confidence | "Hope it matches" | Side-by-side comparison | **Verified** |

---

## Moments of Trust

**Moment 1: Column Auto-Mapping**
> Upload Excel → System shows: "I found: Name ✓, Salary ✓, TIN ✓, Bank ✓, Department ✓. 3 columns unrecognized — ignore or map?"
>
> *Owner thinks: "It understood my spreadsheet. I don't have to reformat anything."*

**Moment 2: Validation Report**
> ```
> IMPORT VALIDATION
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> ✓ 47 employees ready
> ⚠ 2 invalid TINs (flagged for review)
> ⚠ 1 missing bank account
> ✗ 1 duplicate detected (same name + same bank)
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> Fix the 4 issues above, then import.
> ```
>
> *Owner thinks: "Excel never told me about these errors. I would have found out on payday."*

**Moment 3: First Payroll Comparison**
> ```
> FIRST PAYROLL TEST
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> Platform result:  ETB 1,847,220.50
> Your Excel:       ETB 1,847,220.50
> Difference:       ETB 0.00
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> ✓ Numbers match. You're ready to go live.
> ```
>
> *Owner thinks: "The numbers match my Excel. I can trust this."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Time to go live | < 15 minutes |
| **Customer** | Data import accuracy | > 99% |
| **Customer** | First payroll matches Excel | 100% match |
| **Business** | Migration completion rate | > 90% |
| **Business** | Customer activation (first payroll within 7 days) | > 80% |
| **Platform** | Column auto-mapping accuracy | > 95% |
| **Platform** | Validation error detection rate | > 99% |


## Automation Opportunities

| Event | Automatic Action |
|-------|------------------|
| Excel uploaded | Auto-detect column headers, map to fields |
| Import complete | Validate all TINs, bank accounts, detect duplicates |
| First payroll test | Auto-compare with uploaded Excel totals |
| Migration complete | Generate "Migration Report" with data quality summary |
| TIN invalid | Flag employee, block from ERCA filing |
| Bank account invalid | Flag employee, block from payroll |

---

# JOURNEY 1: Hire an Employee

**Trigger:** Business owner or HR officer decides to hire someone.
**Outcome:** Employee is in the system, payroll-ready, with zero data entry errors.
**Maturity Required:** Level 2+

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: HR Officer** | Enters employee data, assigns salary, uploads documents | Day 1 |
| **Supporting: Business Owner** | Approves salary, reviews impact preview | Day 1 |
| **Supporting: Accountant** | Receives notification, verifies TIN | Day 1 |
| **Waiting: System** | Validates TIN, validates bank, calculates payroll impact | Instant |
| **Waiting: Employee** | Receives welcome notification, creates portal account | Day 1-7 |

### Business Value

- ✔ Hire an employee in 3 minutes, not 3 hours
- ✔ TIN and bank errors caught immediately, not on payday
- ✔ Accountant sees new employee instantly — no phone call needed
- ✔ Employee is payroll-ready the moment they're added

---

## Before (Excel/Manual)

| Step | How it happens | Time | Error rate |
|------|---------------|------|-----------|
| 1. Collect documents | Paper, WhatsApp photos, email | 1-3 days | Lost documents |
| 2. Enter in Excel | Manual typing of name, salary, TIN, bank | 15-30 min | 8-12% typo rate |
| 3. Verify TIN | Manually check format | 5 min | Often skipped |
| 4. Verify bank account | Manually check digits | 5 min | Often skipped |
| 5. Inform accountant | Email/Telegram/phone call | 1 day delay | Miscommunication |
| 6. Add to payroll Excel | Copy-paste into next month's sheet | 10 min | Double entry errors |
| 7. File contract | Paper folder | 5 min | Lost contracts |
| **Total** | | **3+ hours** | **8-12% error rate** |

**Pain points:**
- Data entered 2-3 times (Excel, contract, notification to accountant)
- TIN and bank errors discovered only on payday
- No single source of truth — Excel, paper, WhatsApp all have different versions

---

## During (Using the Platform)

| Step | How it happens | Time | Error rate |
|------|---------------|------|-----------|
| 1. Add employee | Single form: name, salary, TIN, bank, department | 3 min | Real-time validation |
| 2. TIN validation | System checks format automatically | Instant | 0% format errors |
| 3. Bank validation | System checks account pattern per bank | Instant | 0% format errors |
| 4. Impact preview | System shows: "This employee adds ETB X to monthly payroll" | Instant | — |
| 5. Notify accountant | Automatic — accountant sees new employee immediately | Instant | 0% |
| 6. Included in payroll | Automatic — appears in next payroll run | Instant | 0% |
| **Total** | | **3 minutes** | **<0.5% error rate** |

**What changes:**
- Single entry, single source of truth
- Validation catches errors before they reach payroll
- Accountant sees the change in real-time
- No copy-paste, no email, no phone call

---

## After (Measurable Impact)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Time to hire (data entry) | 3+ hours | 3 minutes | **98% reduction** |
| Data entry errors | 8-12% | <0.5% | **95% reduction** |
| Time to payroll-ready | 1-3 days | Instant | **Eliminated** |
| Communication gaps | Frequent | Zero | **Eliminated** |

---

## Moments of Trust

**Moment 1: TIN Validation**
> Employee TIN entered → System validates → Green checkmark appears
>
> *HR officer thinks: "I used to find out on payday that the TIN was wrong. Now I know immediately."*

**Moment 2: Impact Preview**
> Salary entered → System shows: "Monthly payroll increases by ETB 12,000. Tax impact: +ETB 1,800. Net: ETB 10,200."
>
> *Business owner thinks: "I can see exactly what this hire costs me before I commit."*

**Moment 3: Bank Account Validation**
> Bank account entered → System validates against CBE pattern → "Valid CBE account"
>
> *HR officer thinks: "Last month we had 3 employees whose bank accounts were wrong. This catches it."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Time to add employee | < 3 minutes |
| **Customer** | Data entry errors | < 0.5% |
| **Customer** | Time to payroll-ready | Instant |
| **Business** | HR support requests for hiring | Reduced by 80% |
| **Platform** | TIN validation accuracy | 100% |
| **Platform** | Bank account validation accuracy | 100% |


## Automation Opportunities

| Event | Automatic Action |
|-------|-----------------|
| Employee added | Notify accountant via in-app notification |
| Employee added | Add to next payroll draft |
| TIN missing after 7 days | Remind HR: "Employee [name] has no TIN — ERCA filing will fail" |
| Bank account missing after 7 days | Block from payroll: "Cannot process without payment method" |
| Probation period ending in 7 days | Notify HR: "Probation ending — confirm permanent appointment" |
| Contract expiring in 30 days | Notify owner: "Contract for [name] expires [date]" |

---

## Industry Variations

| Industry | Special Requirement | How Platform Adapts |
|----------|-------------------|-------------------|
| Construction | Site assignment, hazard level | Employee metadata: `site`, `hazard_level` |
| Schools | Academic rank, campus | Employee metadata: `rank`, `campus` |
| Hotels | Department (FO/Housekeeping/F&B), tip group | Employee metadata: `service_department`, `tip_group` |
| NGOs | Donor code, project code, grant period | Employee metadata: `donor`, `project`, `grant_end` |
| Security | Shift pattern, weapon license | Employee metadata: `shift_pattern`, `license_expiry` |

**No code changes needed.** Industry template pre-fills the metadata fields and labels.

---

# JOURNEY 2: Prepare Monthly Payroll

**Trigger:** End of month approaches. Payroll officer needs to process salaries.
**Outcome:** All data is verified, all validations pass, payroll draft is ready for review.
**Maturity Required:** Level 3

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Payroll Officer** | Imports attendance, reviews draft, runs validation | Day 26-28 |
| **Supporting: HR** | Confirms leave records, flags discrepancies | Day 25-27 |
| **Supporting: Manager** | Approves overtime entries for their team | Day 25-27 |
| **Supporting: Finance** | Reviews deduction accuracy | Day 27 |
| **Waiting: System** | Auto-matches attendance, calculates payroll, runs crosschecks | During generation |
| **Handoff → Owner** | Draft ready for approval notification | Day 28 |

### Business Value

- ✔ Save 2 payroll staff days every month
- ✔ Prevent tax penalties from outdated Excel brackets
- ✔ Reduce employee complaints about payslip errors
- ✔ Enable owner approval in under 2 minutes
- ✔ Remove Excel dependency for payroll calculations

---

## Before (Excel/Manual)

| Step | How it happens | Time | Error rate |
|------|---------------|------|-----------|
| 1. Collect attendance | Biometric device export → manually match to employees | 2-4 hours | Matching errors |
| 2. Calculate overtime | Manual formula in Excel per employee | 1-2 hours | Formula errors |
| 3. Check leave | Ask HR who was on leave, manually adjust | 30-60 min | Forgotten adjustments |
| 4. Update salaries | Check for any salary changes, copy new values | 30 min | Missed changes |
| 5. Apply deductions | Check loan balances, manually deduct | 30 min | Wrong amounts |
| 6. Calculate tax | Excel formula (often outdated brackets) | 1 hour | Bracket errors |
| 7. Calculate pension | Excel formula | 30 min | Wrong base (gross vs basic) |
| 8. Calculate net pay | Final formula | 30 min | Rounding errors |
| 9. Cross-check totals | Compare with last month, eyeball for errors | 1 hour | Often skipped |
| 10. Send to accountant | Email/Telegram the Excel file | 30 min | Version confusion |
| **Total** | | **6-10 hours** | **15-25% error rate** |

**Pain points:**
- Entire process repeated every month from scratch
- Attendance-to-payroll matching is manual and error-prone
- Tax brackets in Excel may be outdated
- Pension calculated on wrong base (gross instead of basic)
- No validation before "sending" — errors discovered on payday

---

## During (Using the Platform)

| Step | How it happens | Time | Error rate |
|------|---------------|------|-----------|
| 1. Import attendance | Upload CSV from biometric → auto-matches employees | 2 min | Auto-match |
| 2. Process overtime | Overtime entries already recorded and approved | 0 min | Pre-validated |
| 3. Check leave | System automatically adjusts for approved leave | 0 min | Automatic |
| 4. Apply salary changes | System uses current salary (changes auto-propagated) | 0 min | Automatic |
| 5. Apply deductions | System applies active deductions with balances | 0 min | Automatic |
| 6. Run validation | System runs 10+ pre-processing checks | 30 sec | Comprehensive |
| 7. Review draft | Payroll officer reviews summary + comparison with last month | 10 min | — |
| 8. Generate outputs | ERCA, pension, bank file all generated together | 1 min | Automatic |
| **Total** | | **15 minutes** | **<1% error rate** |

**What changes:**
- No manual calculations — the engine handles everything
- Validation catches errors before the draft is even shown
- Comparison with last month is automatic
- Accountant can see the draft in real-time (no file transfer)

---

## After (Measurable Impact)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Time to prepare payroll (50 employees) | 6-10 hours | 15 minutes | **97% reduction** |
| Calculation errors | 15-25% | <1% | **95% reduction** |
| Month-end stress | Extreme | Low | **Transformed** |
| Accountant involvement | Manual file transfer | Real-time visibility | **Eliminated handoff** |

---

## Moments of Trust

**Moment 1: Validation Summary (Pre-Draft)**
> System displays:
>
> ```
> ✓ 50 employees ready
> ✓ All TINs valid
> ✓ All bank accounts valid
> ✓ Attendance imported (1,200 records)
> ✓ 3 overtime entries processed
> ✓ 2 leave adjustments applied
> ⚠ 1 warning: Employee #37 — salary increased 45% (flag for review)
> ✓ Ready to generate draft
> ```
>
> *Payroll officer thinks: "I used to spend 2 hours cross-checking. The system just did it in 30 seconds."*

**Moment 2: Month-over-Month Comparison**
> System shows: "Payroll: ETB 2,145,330 (+3.2% vs last month). Main drivers: +2 new hires (ETB 24,000), +overtime (ETB 18,000), −1 termination (−ETB 12,000)."
>
> *Payroll officer thinks: "I can explain this to the owner without opening a single spreadsheet."*

**Moment 3: Crosscheck Results (from TRUST_CROSSCHECK_BUILD_SPEC.md)**
> System shows:
>
> ```
> CROSSCHECK RESULTS
> ✓ Attendance vs Payroll: 50/50 employees matched
> ✓ ERCA totals match payroll totals
> ✓ Pension totals match payroll totals
> ✓ Bank file total matches net pay total (ETB 1,847,220.50)
> ✓ No unresolved BLOCKs
> ```
>
> *Accountant thinks: "Every number is cross-checked against another source. I can sign off on this."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Payroll completed in | < 15 minutes |
| **Customer** | Payroll corrections after approval | < 1% |
| **Customer** | Payrolls approved before payday | > 95% |
| **Business** | Payroll preparation time | Reduced by 97% |
| **Business** | HR support requests | Reduced by 80% |
| **Business** | Customer renewals | > 95% |
| **Platform** | Validation completion rate | 100% |
| **Platform** | Crosscheck pass rate | > 99% |
| **Platform** | Payroll variance alerts resolved | 100% |


## Automation Opportunities

| Event | Automatic Action |
|-------|-----------------|
| 25th of month | Notify payroll officer: "Payroll period ending in 5 days. Attendance import ready?" |
| Attendance imported | Auto-match employees, flag mismatches |
| Missing attendance (3+ days) | Alert: "Employee [name] has no attendance records for [days]" |
| Payroll draft generated | Auto-compare with last month, flag >20% variance |
| Validation BLOCK found | Prevent draft generation, show fix instructions |
| Validation WARNING found | Allow draft, require acknowledgment before approval |
| Payroll ready | Notify owner: "Payroll draft ready for review" |

---

# JOURNEY 3: Approve & Lock Payroll

**Trigger:** Payroll officer has prepared the draft. Owner needs to approve.
**Outcome:** Owner approves with confidence. Payroll is locked. No changes possible.
**Maturity Required:** Level 3

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Business Owner** | Reviews confidence report, taps approve | Day 28-29 |
| **Supporting: Payroll Officer** | Presents draft, answers questions, handles warnings | Day 28 |
| **Supporting: Accountant** | Reviews crosscheck results, signs off on compliance | Day 28 |
| **Waiting: System** | Runs crosschecks, generates confidence score | Before approval |
| **Handoff → Employees** | Payslips published, notifications sent | Post-approval |
| **Handoff → Finance** | Bank file generated, ready for download | Post-approval |

### Business Value

- ✔ Owner approves payroll in under 2 minutes, not 30-60 minutes
- ✔ Every number is cross-checked and explainable — no "I hope it's right"
- ✔ Approval creates permanent audit trail — defensible to authorities
- ✔ Payroll locked after approval — no accidental post-approval edits



---

## Before (Excel/Manual)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Receive Excel | Email/Telegram from payroll officer | Hours delay | Version confusion |
| 2. Review totals | Eyeball the bottom line | 5 min | No drill-down |
| 3. Ask questions | "Why is this higher?" → back-and-forth | 30-60 min | Miscommunication |
| 4. Trust the numbers | "I hope it's right" | — | No verification |
| 5. Approve verbally | "Looks okay" via Telegram | Instant | No audit trail |
| 6. No lock mechanism | Excel can still be edited after "approval" | — | No protection |

**Pain points:**
- Owner can't verify without an accountant present
- No way to know if numbers are correct
- "Approval" is informal — no audit trail
- Excel can be modified after approval
- No confidence score — just hope

---

## During (Using the Platform)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Open payroll run | Dashboard shows "Pending Approval" badge | Instant | — |
| 2. Review confidence summary | 3 lines: crosscheck results, warnings, bank total | 30 sec | Comprehensive |
| 3. Drill into any number | Click any number → ExplainPanel shows formula, inputs, citation | As needed | Full transparency |
| 4. Review comparison | Side-by-side with last month, top 3 changes explained | 1 min | Automatic |
| 5. Approve | Single tap with confirmation | 2 sec | Audit trail + IP logged |
| 6. Lock | System locks run — no further edits possible | Instant | Protected |
| **Total** | | **< 2 minutes** | **Audit-trail backed** |

**What changes:**
- Owner can verify without an accountant present
- Every number is explainable
- Crosschecks are automatic
- Approval creates a permanent audit record
- Payroll is locked — no post-approval edits

---

## After (Measurable Impact)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Approval time | 30-60 minutes | < 2 minutes | **97% reduction** |
| Confidence in numbers | "Hope it's right" | Crosscheck-verified | **Trust transformation** |
| Post-approval changes | Possible (Excel editable) | Impossible (locked) | **Eliminated** |
| Audit trail | None | Full (who, when, IP) | **Complete** |

---

## Moments of Trust

**Moment 1: Approval Confidence Summary**
> ```
> PAYROLL CONFIDENCE REPORT
> ━━━━━━━━━━━━━━━━━━━━━━━━
> Employees processed:     50
> Gross payroll:           ETB 2,145,330.00
> Tax withheld:            ETB 412,650.00
> Pension (employee):      ETB 148,173.00
> Net pay:                 ETB 1,584,507.00
> ━━━━━━━━━━━━━━━━━━━━━━━━
> CROSSCHECKS
> ✓ Attendance vs Payroll:     PASSED
> ✓ ERCA totals match:         PASSED
> ✓ Pension totals match:      PASSED
> ✓ Bank file total matches:   PASSED
> ⚠ Salary variance >30%:      1 employee (flagged, acknowledged)
> ━━━━━━━━━━━━━━━━━━━━━━━━
> Confidence: 98%
> Status: READY TO APPROVE
> ```
>
> *Business owner thinks: "I've never been this confident about payroll. I can see every number is checked."*

**Moment 2: One-Tap Approval with Audit Trail**
> Tap "Approve" → Confirmation: "You are approving payroll PR-2018-10-001 for ETB 1,584,507.00. This action is permanent and recorded. IP: 196.188.x.x, Time: 2026-07-28 14:35"
>
> *Business owner thinks: "This is serious. This is documented. This is defensible."*

**Moment 3: Post-Approval Lock**
> "Payroll locked. ERCA report generated. Bank file generated. Payslips published to employee portal. 50 employees notified."
>
> *Business owner thinks: "One tap and everything is done. I used to spend all day on this."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Owner approval time | < 2 minutes |
| **Customer** | Approval confidence | > 95% |
| **Business** | Payroll corrections after approval | < 0.5% |
| **Business** | Audit findings from approval process | 0 |
| **Platform** | Crosscheck completion rate | 100% |
| **Platform** | Post-approval modifications | 0 (locked) |


## Automation Opportunities

| Event | Automatic Action |
|-------|-----------------|
| Draft ready | Notify owner with summary (WhatsApp + in-app) |
| Owner opens draft | Show confidence report immediately |
| Approval granted | Lock run, generate all outputs, notify employees |
| Approval delayed >2 days | Escalation: "Payroll for [month] still not approved. Employees expect payment on [date]" |
| Crosscheck BLOCK | Prevent approval, show fix instructions |
| Post-approval | Freeze calculation snapshot for audit |

---

# JOURNEY 4: Pay Employees

**Trigger:** Payroll is approved. Money needs to reach employees.
**Outcome:** Every employee is paid correctly through their preferred method. Payment status is tracked.
**Maturity Required:** Level 3

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Finance Officer** | Downloads bank file, uploads to portal, confirms payment | Day 29-30 |
| **Supporting: Payroll Officer** | Generates files, tracks status, handles failures | Day 29 |
| **Supporting: Business Owner** | Monitors disbursement status | Day 29-30 |
| **Waiting: System** | Validates accounts, generates files, tracks status | During generation |
| **Waiting: Employees** | Receive notification when paid | Day 30 |
| **Handoff → Employees** | "You have been paid" notification | Post-payment |

### Business Value

- ✔ Bank file generated in 30 seconds, not 1-2 hours
- ✔ Account numbers validated before file generation — zero bank rejections
- ✔ Mixed payment methods (bank + mobile money) in one workflow
- ✔ Every employee notified when paid — zero "was I paid?" calls



---

## Before (Excel/Manual)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Prepare bank file | Copy-paste from Excel to bank template | 1-2 hours | Copy errors |
| 2. Upload to bank | Login to bank portal, upload file | 30 min | Wrong file format |
| 3. Some rejected | Bank rejects bad account numbers | Hours/days | Lost track of who |
| 4. Manual correction | Fix accounts, re-upload | 1-2 hours | Re-processing |
| 5. Mobile money | Manually send Telebirr to unbanked employees | 30-60 min | Manual tracking |
| 6. Confirm payment | No systematic confirmation | — | "I think everyone got paid" |
| 7. Notify employees | WhatsApp: "Salary sent" | 15 min | Not everyone notified |

**Pain points:**
- Bank file creation is manual and error-prone
- Rejected payments are hard to track
- Mixed payment methods (bank + mobile money) require separate manual processes
- No systematic confirmation that money arrived
- "I think everyone got paid" is not good enough

---

## During (Using the Platform)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Generate bank file | One click — system generates validated file | 30 sec | Pre-validated |
| 2. Generate mobile money file | Automatic — Telebirr/M-Pesa employees separated | 30 sec | Pre-validated |
| 3. Upload to bank | Download file, upload to portal | 5 min | — |
| 4. Handle failures | System tracks which payments failed, why | Instant | Automatic |
| 5. Retry failed | One-click retry for failed payments only | 1 min | Automatic |
| 6. Mark as paid | Bulk "mark as confirmed" | 10 sec | Audit trail |
| 7. Notify employees | Automatic — in-app + WhatsApp when confirmed | Instant | Automatic |
| **Total** | | **10 minutes** | **<0.5% failure rate** |

---

## After (Measurable Impact)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Bank file preparation | 1-2 hours | 30 seconds | **99% reduction** |
| Payment errors | 3-5% | <0.5% | **90% reduction** |
| Failed payment tracking | Manual, error-prone | Automatic | **Eliminated** |
| Employee notification | Manual WhatsApp | Automatic | **Eliminated** |
| Mixed payment methods | Separate manual process | Single workflow | **Unified** |

---

## Moments of Trust

**Moment 1: Bank File Validation**
> ```
> BANK FILE READY
> Bank: CBE
> Employees: 42
> Total: ETB 1,423,560.00
> ✓ All 42 account numbers validated
> ✓ File format matches CBE specification
> Ready to download
> ```
>
> *Finance officer thinks: "Last month I had 5 rejections because of wrong account numbers. This won't happen again."*

**Moment 2: Payment Status Dashboard**
> ```
> DISBURSEMENT STATUS
> ━━━━━━━━━━━━━━━━━━━
> Bank (CBE):    42 employees  ✓ File downloaded
> Telebirr:       5 employees  ✓ File downloaded
> Cash:           3 employees  ✓ Marked as paid
> ━━━━━━━━━━━━━━━━━━━
> Confirmed:     47/50 (94%)
> Pending:        3/50 (6%)
> Failed:         0/50 (0%)
> ```
>
> *Business owner thinks: "I can see exactly who's been paid and who hasn't. No more guessing."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Bank file generation time | < 30 seconds |
| **Customer** | Bank rejections | < 0.5% |
| **Customer** | "Was I paid?" calls | Zero |
| **Business** | Disbursement errors | < 0.5% |
| **Business** | Payment confirmation rate | > 98% |
| **Platform** | Account validation accuracy | 100% |
| **Platform** | Mixed payment method support | Bank + Telebirr + Cash |


---

# JOURNEY 5: File with Government (ERCA/MOLSA)

**Trigger:** Monthly deadline approaching. Tax and pension reports must be submitted.
**Outcome:** Reports are generated, verified, and filed on time. Filing is recorded for audit.
**Maturity Required:** Level 3

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Accountant** | Generates reports, reviews totals, submits to ERCA/MOLSA | Day 30-31 |
| **Supporting: Payroll Officer** | Verifies report totals match payroll | Day 30 |
| **Waiting: System** | Generates ERCA and pension reports, crosschecks totals | During generation |
| **Handoff → Accountant** | Reports ready for download | Post-generation |
| **Waiting: Government** | Receives filing | Day 31 |

### Business Value

- ✔ ERCA report generated in 30 seconds, not 2-3 hours
- ✔ Report totals automatically verified against payroll — zero manual cross-check
- ✔ Filing tracked with confirmation numbers — complete audit trail
- ✔ Never miss a deadline — system alerts 5 days before due



---

## Before (Excel/Manual)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Prepare ERCA report | Manually format Excel to match ERCA template | 2-3 hours | Format errors |
| 2. Verify totals | Cross-check with payroll Excel | 30 min | Often skipped |
| 3. Submit to ERCA | Upload to portal | 30 min | Format rejection |
| 4. Prepare pension report | Separate Excel for MOLSA | 1-2 hours | Different format |
| 5. Submit to MOLSA | Upload/submit | 30 min | — |
| 6. Record filing | Paper folder or Excel log | 15 min | Often forgotten |
| 7. Track deadlines | Calendar reminder (if set) | — | Missed deadlines |

**Pain points:**
- Two separate reports, two separate formats
- Manual formatting is error-prone
- No verification that totals match payroll
- Filing records are scattered
- Deadline tracking is manual

---

## During (Using the Platform)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Generate ERCA report | One click — from approved payroll run | 30 sec | Auto-formatted |
| 2. Generate pension report | One click — from same payroll run | 30 sec | Auto-formatted |
| 3. Crosscheck | System verifies ERCA/pension totals match payroll | Instant | Automatic |
| 4. Download | Download both reports | 10 sec | — |
| 5. Submit to ERCA | Upload to ERCA portal | 5 min | — |
| 6. Record filing | Enter confirmation number → filing recorded | 30 sec | Audit trail |
| 7. Track deadlines | System tracks filed/pending per period | Automatic | Automatic |
| **Total** | | **10 minutes** | **<0.5% error rate** |

---

## After (Measurable Impact)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| ERCA report preparation | 2-3 hours | 30 seconds | **99% reduction** |
| Pension report preparation | 1-2 hours | 30 seconds | **99% reduction** |
| Format errors | Common | Zero (pre-formatted) | **Eliminated** |
| Total verification | Manual, often skipped | Automatic, always | **100% coverage** |
| Filing tracking | Paper/Excel | Systematic | **Complete** |
| Missed deadlines | Occasional | Never (alerts) | **Eliminated** |

---

## Moments of Trust

**Moment 1: Filing Reconciliation**
> ```
> ERCA FILING RECONCILIATION
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> Payroll total tax:     ETB 412,650.00
> ERCA report total:     ETB 412,650.00
> Match:                 ✓ EXACT
>
> Payroll total pension: ETB 148,173.00
> MOLSA report total:    ETB 148,173.00
> Match:                 ✓ EXACT
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> Ready to submit
> ```
>
> *Accountant thinks: "I used to spend 2 hours cross-checking these totals. The system does it instantly."*

**Moment 2: Filing History**
> ```
> FILING HISTORY
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> Period      ERCA    MOLSA   Filed By    Date         Confirmation
> 2018-10     ✓       ✓       Abebe       2026-07-28   ERCA-2026-07-0042
> 2018-09     ✓       ✓       Abebe       2026-06-27   ERCA-2026-06-0038
> 2018-08     ✓       ✓       Abebe       2026-05-29   ERCA-2026-05-0035
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> All periods filed. No gaps.
> ```
>
> *Auditor thinks: "Every filing is tracked with confirmation numbers. This is defensible."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | ERCA report generation time | < 30 seconds |
| **Customer** | Filing deadline compliance | 100% |
| **Customer** | Manual cross-checking time | Zero (automated) |
| **Business** | Government filing rejections caused by system | 0 |
| **Business** | Filing tracking completeness | 100% |
| **Platform** | Report total vs payroll total match | 100% |


---

# JOURNEY 6: Employee Opens Payslip

**Trigger:** Employee receives notification that payslip is ready.
**Outcome:** Employee understands every line. Zero calls to HR.
**Maturity Required:** Level 3

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Employee** | Opens payslip, understands every line, compares with last month | Day 30-31 |
| **Supporting: HR** | Receives dispute if employee disagrees (rare) | If disputed |
| **Waiting: System** | Generates payslips, sends notifications | Post-approval |
| **No involvement: Accountant** | Employee self-serves — no HR call needed | — |

### Business Value

- ✔ 90% reduction in "why is my pay different?" calls to HR
- ✔ Employee understands every deduction — self-service, not phone call
- ✔ Professional payslip builds trust — not a WhatsApp photo of Excel
- ✔ One-tap comparison explains month-over-month changes in plain language



---

## Before (Excel/Manual)

| Step | How it happens | Time | Result |
|------|---------------|------|--------|
| 1. Receive payslip | Photo of Excel printout via WhatsApp | — | Low quality, hard to read |
| 2. Try to understand | Look at net pay, confused by deductions | 5 min | Doesn't understand |
| 3. Call HR | "Why is my salary lower this month?" | 10-30 min | HR doesn't know either |
| 4. HR investigates | Check Excel, check leave records, check with accountant | 30-60 min | Delayed answer |
| 5. Employee unsatisfied | "I'll check again next month" | — | Trust eroded |

**Pain points:**
- Payslip is a photo of an Excel cell — no breakdown
- Employee can't understand deductions
- Every question requires HR involvement
- HR often can't answer immediately
- Trust erodes with every unanswered question

---

## During (Using the Platform)

| Step | How it happens | Time | Result |
|------|---------------|------|--------|
| 1. Receive notification | In-app + WhatsApp: "Your payslip for [month] is ready" | Instant | Professional |
| 2. Open payslip | Full breakdown with every line explained | 2 min | Self-service |
| 3. Understand deductions | Click any line → ExplainPanel shows formula, inputs, citation | 1 min | Self-explanatory |
| 4. Compare with last month | One-tap comparison: "Why different?" answered automatically | 1 min | Self-service |
| 5. Dispute if needed | One-tap: "I disagree with [line]" → HR notified with context | 30 sec | Structured |
| **Total** | | **5 minutes** | **Zero HR calls** |

---

## After (Measurable Impact)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| "Why is my pay different?" calls | 15-20/month | 0-2/month | **90% reduction** |
| Time for HR to answer | 30-60 min | Self-service | **Eliminated** |
| Employee trust in payslip | Low | High | **Transformed** |
| Payslip format | WhatsApp photo | Professional PDF | **Professional** |

---

## Moments of Trust

**Moment 1: Payslip with Explanations**
> ```
> PAYSLIP — July 2026
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> Basic Salary                    ETB 12,000.00
> Housing Allowance               ETB  3,000.00
> Transport Allowance             ETB  1,500.00
> ─────────────────────────────────────────
> Gross Salary                    ETB 16,500.00
>
> Pension (7% of basic)          −ETB    840.00  ⓘ
> Taxable Income                  ETB 15,660.00
>
> Income Tax                     −ETB  2,859.00  ⓘ
>   Bracket 1:  0–2,000 @ 0%     = ETB      0.00
>   Bracket 2:  2,001–4,000 @ 15% = ETB    300.00
>   Bracket 3:  4,001–7,000 @ 20% = ETB    600.00
>   Bracket 4:  7,001–10,000 @ 25% = ETB   750.00
>   Bracket 5:  10,001–14,000 @ 30% = ETB 1,200.00
>   Bracket 6:  14,001–15,660 @ 35% = ETB   581.00
>   Gross Tax:  ETB 3,431.00
>   Relief:    −ETB   150.00
>   Tax Due:    ETB 2,859.00
>
> Loan Deduction (Salary Advance) −ETB  2,000.00  ⓘ
> ─────────────────────────────────────────
> Net Pay                         ETB 10,801.00
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ⓘ = Tap for full explanation
> ```
>
> *Employee thinks: "I can see exactly why my tax is this amount. I don't need to call anyone."*

**Moment 2: "Why Different This Month?"**
> Employee taps comparison:
> ```
> July vs June
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> Net pay changed: −ETB 2,412.00
>
> WHY:
> 1. 3 unpaid leave days    −ETB 1,650.00
> 2. Tax decreased          +ETB   412.00  (lower taxable income)
> 3. Loan deduction         −ETB 2,000.00  (monthly installment)
> 4. Overtime decreased     −ETB 1,174.00  (8 hrs → 2 hrs)
> ━━━━━━━━━━━━━━━━━━━━━━━━━
> ```
>
> *Employee thinks: "This makes sense. I took leave and I have a loan. Now I understand."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | "Why is my pay different?" calls to HR | Reduced by 90% |
| **Customer** | Employee portal adoption | > 70% |
| **Customer** | Employee understands payslip | > 90% |
| **Business** | HR time spent on payslip queries | Reduced by 80% |
| **Platform** | Payslip explanation completeness | 100% of lines |


---

# JOURNEY 7: Employee Leaves the Company

**Trigger:** Employee resigns, is terminated, or contract ends.
**Outcome:** Final settlement is calculated correctly. Employee is paid everything owed. All records are preserved.
**Maturity Required:** Level 3

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: HR Officer** | Enters termination, reviews settlement, approves | When triggered |
| **Supporting: Payroll Officer** | Includes settlement in next payroll | Next cycle |
| **Supporting: Business Owner** | Approves final settlement amount | When triggered |
| **Waiting: System** | Calculates settlement: salary, severance, leave, deductions | Instant |
| **Waiting: Employee** | Receives final payment | Next payroll |

### Business Value

- ✔ Final settlement calculated in 10 minutes, not 3-4 hours
- ✔ Severance, leave encashment, and deductions all correct — no manual formulas
- ✔ Settlement document generated automatically — professional and defensible
- ✔ Employee paid everything they're owed — zero disputes



---

## Before (Excel/Manual)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Calculate final salary | Manual pro-rata in Excel | 30 min | Pro-rata errors |
| 2. Calculate severance | "How many years? What's the formula?" | 30 min | Formula confusion |
| 3. Calculate leave encashment | "How many days unused?" → check leave Excel | 30 min | Wrong balance |
| 4. Deduct loans | Check loan balance | 15 min | Wrong balance |
| 5. Calculate tax on settlement | Complex — is severance taxable? | 1 hour | Uncertainty |
| 6. Prepare settlement letter | Word document | 30 min | — |
| 7. Pay employee | Separate from payroll | 30 min | — |
| **Total** | | **3-4 hours** | **20-30% error rate** |

---

## During (Using the Platform)

| Step | How it happens | Time | Error risk |
|------|---------------|------|-----------|
| 1. Enter termination | Date + reason | 1 min | — |
| 2. System calculates | Outstanding salary, severance, leave encashment, deductions | Instant | Automatic |
| 3. Review breakdown | Full breakdown with explanations | 5 min | Transparent |
| 4. Approve settlement | Single action | 10 sec | Audit trail |
| 5. Generate settlement PDF | Automatic | 10 sec | Professional |
| 6. Include in payroll | Automatic inclusion in next run | Instant | — |
| **Total** | | **10 minutes** | **<1% error rate** |

---

## Moments of Trust

**Moment: Settlement Breakdown**
> ```
> FINAL SETTLEMENT — Kebede Alemu
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> Reason: Resignation
> Last working day: 2026-07-15
> Years of service: 3.4
>
> EARNINGS
> Outstanding salary (15 days)    ETB  7,500.00
> Leave encashment (8 days)       ETB  4,000.00
> Severance (not applicable)      ETB      0.00
> ─────────────────────────────────────────────
> Total earnings                  ETB 11,500.00
>
> DEDUCTIONS
> Pension (7% of basic)          −ETB    525.00
> Tax                            −ETB  1,245.00
> Outstanding loan               −ETB  4,000.00
> ─────────────────────────────────────────────
> Total deductions                −ETB  5,770.00
>
> NET FINAL PAYMENT               ETB  5,730.00
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ```
>
> *HR officer thinks: "I used to spend half a day on this and still get it wrong. The system did it in seconds."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Settlement calculation time | < 10 minutes |
| **Customer** | Settlement disputes | Zero |
| **Business** | Severance calculation errors | 0 |
| **Business** | Final payment accuracy | 100% |
| **Platform** | Leave encashment accuracy | 100% |


---

# JOURNEY 8: Government Audit

**Trigger:** ERCA, MOLSA, or labor inspector requests payroll records.
**Outcome:** Business produces complete, verified, tamper-evident records within minutes.
**Maturity Required:** Level 3

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Accountant** | Retrieves records, shows calculations, exports evidence | When audited |
| **Supporting: Business Owner** | Presents trust score and filing history | When audited |
| **Supporting: HR** | Provides employee records if requested | When audited |
| **Waiting: System** | Provides: audit log, calculation snapshots, filing confirmations | On demand |
| **Waiting: Auditor** | Reviews evidence | During audit |

### Business Value

- ✔ Audit completed in 5 minutes of system time, not hours of digging through files
- ✔ Every calculation explained with legal citation — defensible to any authority
- ✔ Hash-chain audit trail proves no records were altered
- ✔ Trust Score demonstrates compliance track record — not just claims



---

## Before (Excel/Manual)

| Step | How it happens | Time | Risk |
|------|---------------|------|------|
| 1. Find the Excel file | "Which version? Where is it saved?" | 30-60 min | Lost files |
| 2. Print records | Print payroll sheets | 30 min | — |
| 3. Verify accuracy | "Are these the right numbers?" | Hours | Can't verify |
| 4. Explain calculations | "How did you calculate this tax?" | Hours | Can't explain |
| 5. Prove compliance | "Show me the proclamation reference" | — | No citations |
| 6. Show audit trail | "Who approved this? When?" | — | No trail |

**Pain points:**
- Records may be lost or modified
- Can't prove calculations were correct at the time
- Can't show audit trail
- Can't cite legal basis for calculations
- Entire audit is stressful and time-consuming

---

## During (Using the Platform)

| Step | How it happens | Time | Risk |
|------|---------------|------|------|
| 1. Open audit log | Filter by period, action type | 30 sec | Complete |
| 2. Show payroll run | Full details with locked status | 1 min | Frozen |
| 3. Explain any calculation | ExplainPanel → formula, inputs, legal citation | 30 sec | Self-documenting |
| 4. Show approval trail | Who approved, when, from what IP | 10 sec | Hash-chain verified |
| 5. Show ERCA filing | Confirmation number, filed date, matched totals | 30 sec | Verified |
| 6. Export records | Download complete package | 1 min | Professional |
| **Total** | | **5 minutes** | **Fully defensible** |

---

## Moments of Trust

**Moment: Audit-Ready Response**
> Auditor asks: "Prove your June 2026 tax calculation for employee Abebe Kebede."
>
> System shows:
> ```
> EMPLOYEE: Abebe Kebede (EMP001)
> PERIOD: June 2026 (2018-10 Ethiopian)
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> Gross salary:           ETB 15,000.00
> Pension (7% of basic): −ETB  1,050.00
> Taxable income:         ETB 13,950.00
>
> Tax calculation:
>   Proclamation No. 1395/2025, Article 36(1)
>   Bracket 1:  0–2,000 @ 0%      = ETB      0.00
>   Bracket 2:  2,001–4,000 @ 15%  = ETB    300.00
>   Bracket 3:  4,001–7,000 @ 20%  = ETB    600.00
>   Bracket 4:  7,001–10,000 @ 25% = ETB    750.00
>   Bracket 5:  10,001–13,950 @ 30% = ETB  1,185.00
>   Gross tax:  ETB 2,835.00
>   Relief:    −ETB    150.00
>   Tax due:    ETB 2,685.00
>
> Calculated: 2026-06-28 10:35:12 UTC
> Approved by: Owner (Dawit Mekonnen)
> Approved:   2026-06-28 14:22:05 UTC
> IP:         196.188.x.x
> Lock hash:  a7f3b2c1d4e5...
> ERCA filed: 2026-06-29, Confirmation: ERCA-2026-06-0038
> ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
> ```
>
> *Auditor thinks: "Every number is explained, every action is traced, every filing is confirmed. This is exactly what we need."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Audit response time | < 5 minutes |
| **Customer** | Audit findings from system errors | 0 |
| **Business** | Trust Score at audit time | > 95% |
| **Business** | Evidence completeness | 100% |
| **Platform** | Hash chain integrity | Always valid |
| **Platform** | Calculation snapshot availability | 100% |


---

# JOURNEY 9: Manager Approvals & HR Lifecycle

**Trigger:** Department manager needs to approve team actions. HR manages employee lifecycle events.
**Outcome:** Every workforce decision flows through the right person, with the right context, at the right time.
**Maturity Required:** Level 4

### Who Experiences This

| Role | Action | When |
|------|--------|------|
| **Primary: Department Manager** | Approves overtime, leave, attendance for their team | Daily/weekly |
| **Supporting: HR** | Manages lifecycle events: probation, promotion, transfer | Ongoing |
| **Supporting: Business Owner** | Reviews department costs, approves promotions | Monthly |
| **Waiting: System** | Routes approvals to right manager, tracks status | Ongoing |
| **Handoff → Payroll** | Approved overtime/leave flows into payroll automatically | Monthly |

### Business Value

- ✔ Managers approve team actions in seconds — not via Telegram
- ✔ Every approval has audit trail — who approved, when, why
- ✔ Probation alerts prevent missed deadlines — no more forgotten confirmations
- ✔ Promotion impact preview shows exact payroll cost before approval



---

## Manager Approval Journey

**Before:** Manager approves overtime/leave via Telegram message. No record. No context.

**During:**

| Step | How it happens | Time |
|------|---------------|------|
| 1. Employee requests leave/overtime | Employee submits via portal | 30 sec |
| 2. Manager notified | In-app notification: "Kebede requests 3 days annual leave, Aug 5-7" | Instant |
| 3. Manager reviews | Sees: employee balance, team coverage, impact on payroll | 1 min |
| 4. Manager approves/rejects | One tap with optional note | 5 sec |
| 5. Employee notified | In-app + WhatsApp | Instant |
| 6. Payroll updated | Leave deduction or overtime pay auto-applied | Automatic |

**After:** Zero Telegram approvals. Full audit trail. Payroll impact automatic.

---

## HR Lifecycle Journey

**Before:** Promotions, salary changes, transfers tracked in Excel or not at all.

**During:**

| Lifecycle Event | System Action |
|----------------|---------------|
| Probation ending (7 days) | Alert HR: "Confirm permanent appointment for [name]" |
| Promotion | Record new position + salary → audit trail → payroll impact preview |
| Salary increase | Record change + reason + effective date → impact analysis → approval workflow |
| Transfer | Update department → notify new manager → no payroll disruption |
| Contract renewal | Alert 30 days before expiry → renew or terminate workflow |
| Contract expiry | If not renewed: auto-flag for termination or renewal |

**After:** Every lifecycle event is recorded, approved, and auditable. No Excel tracking.

---

## Moments of Trust

**Moment: Probation Alert**
> "Employee Hana Tesfaye's 90-day probation ends in 7 days. Confirm permanent appointment?"
>
> *HR thinks: "I would have forgotten this. Now it's impossible to miss."*

**Moment: Promotion Impact Preview**
> "Promoting Kebede from Officer to Manager: Salary ETB 8,000 → ETB 12,000. Monthly payroll impact: +ETB 4,000. Tax impact: +ETB 680. Net increase: ETB 3,320."
>
> *HR thinks: "I can see exactly what this promotion costs before I submit it."*

---

### Success Metrics

| Category | Metric | Target |
|----------|--------|--------|
| **Customer** | Manager approval time | < 30 seconds |
| **Customer** | Missed probation deadlines | Zero |
| **Customer** | Telegram/WhatsApp approvals | Zero (all in system) |
| **Business** | Manager adoption rate | > 80% |
| **Business** | HR lifecycle tracking completeness | 100% |
| **Platform** | Approval routing accuracy | 100% |


---

# PAYROLL CALENDAR

Companies think in months. The platform should show the full month at a glance.

```
JULY 2026 — PAYROLL CALENDAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sun  Mon  Tue  Wed  Thu  Fri  Sat
              1    2    3    4    5
 6    7    8    9   10   11   12
13   14   15   16   17   18   19
20   21   22   23   24   25   26
27   28   29   30   31
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVENTS
20  📋 Attendance closes
24  ⏰ Overtime approval deadline
26  📊 Payroll draft generated
27  👀 Review period
28  ✅ Owner approval
29  🏦 Bank file uploaded
30  💰 Employees paid
31  📄 ERCA filing deadline
31  📄 Pension filing deadline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**This replaces:** "When is payroll due?" emails. "Did we file?" phone calls.
**This gives:** The company's operating calendar, visible to everyone.

---

# DECISION DASHBOARD

Current dashboards show facts. Executives need decisions.

## Before (Facts Only)
```
Payroll increased 18%
```
*Owner thinks: "Why? What should I do?"*

## After (Facts + Reasons — No Recommendations)

The dashboard states facts and explains why. It does **not** tell the owner what to do. That's their decision.

```
PAYROLL CHANGE ALERT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Payroll increased 18% (+ETB 325,000)

WHY:
• 7 new hires                    +ETB 84,000
• Holiday overtime (Eid)         +ETB 182,000
• 2 promotions                   +ETB  24,000
• Annual increment (3 employees) +ETB  35,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
*Owner thinks: "Now I understand why. I can decide what to do."*

**Why no recommendation:** The platform states facts and explains causes. It does not advise the owner to change policy, reduce headcount, or take any specific action. That crosses from data into advice — and advice carries liability the platform shouldn't hold.

---

# CASH FLOW INTELLIGENCE

Owners care about cash, not payroll.

```
CASH FORECAST — NEXT 7 DAYS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Friday (Payday)
  Payroll disbursement    ETB 2,400,000
  Tax remittance (ERCA)   ETB   410,000
  Pension (MOLSA)          ETB   355,000
  ─────────────────────────────────────
  Total cash required      ETB 3,165,000

Available cash             ETB 4,200,000
Surplus after payroll      ETB 1,035,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: ✓ SUFFICIENT
```

*Owner thinks: "I know exactly how much cash I need on Friday. No surprises."*

---

# ACCOUNTANT TASK CENTER

Accountants don't browse menus. They work from a task list.

```
ACCOUNTANT WORKSPACE — July 28, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TODAY'S TASKS
  □ Payroll draft ready for review        [Due: Today]
  □ ERCA filing deadline in 3 days        [Due: Jul 31]
  □ Pension discrepancy: 1 employee       [Action: Review]
  □ 2 employees missing TIN               [Action: Collect]
  □ Loan balance mismatch: Kebede         [Action: Verify]
  □ Audit request from MOLSA              [Due: Aug 5]

RECENTLY COMPLETED
  ✓ June payroll processed (Jul 28)
  ✓ June ERCA filed (Jun 29)
  ✓ 3 overtime entries approved (Jul 27)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

*Accountant thinks: "I open the system and I know exactly what needs to be done today."*

---

# TRUST EVOLUTION

Trust should accumulate visibly over time.

```
COMPANY TRUST SCORE — July 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Payroll cycles completed:     6
  All calculations correct:   ✓
  All ERCA filings accepted:  ✓
  All pension filings accepted: ✓
  All employees paid on time: ✓
  Audit findings:             0
  Compliance issues:          0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRUST SCORE: 99%

This company has built a track record.
Auditors and regulators can reference this score.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**The longer you use the platform correctly, the stronger your trust score becomes.** This is a unique differentiator that Excel can never provide.

---

# COMPANY TRUST SCORE

Every company gets a real-time trust score. Not a feature — the product's core differentiator.

## Trust Score Dashboard

```
COMPANY TRUST SCORE: 94/100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Quality              100
  TINs valid              ✓ All 50
  Bank accounts valid     ✓ All 50
  Employee records complete ✓ 100%

Compliance                 98
  Tax accuracy            ✓ 100%
  Pension accuracy        ✓ 100%
  ERCA filings current    ✓ Through 2018-10
  Labor law compliance    ✓ All rules enforced

Payroll Accuracy           99
  Calculations verified   ✓ Crosschecked
  Month-over-month variance 3.2% (normal)
  Correction runs         0 this quarter

Audit Readiness           100
  Audit trail intact      ✓ Hash chain verified
  Calculation snapshots   ✓ All frozen
  Filing confirmations    ✓ All recorded

Employee Confidence        87
  Portal adoption         43/50 (86%)
  Disputes this month     0
  "Why different?" calls  2 (down from 15)

Automation                 73
  Manual steps remaining  4 of 15
  Auto-notifications      ✓ Active
  Auto-validations        ✓ Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLIANCE RISK:  LOW
AUDIT RISK:       LOW
CASH NEEDED:      ETB 2,400,000 (Friday)
EXPECTED TAX:     ETB 410,000
EXPECTED PENSION: ETB 355,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Trust Score becomes the product.** The longer you use the platform correctly, the higher your score. Auditors and regulators can reference it. Competitors can't copy a track record.

---

# EVIDENCE LAYER

Every screen answers: **"How do you know?"**

Every calculation, every alert, every dashboard number exposes its evidence.

## Evidence Format

```
Expected Tax: ETB 420,220
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Evidence:
  ✔ Payroll Run PR-2018-10-042
  ✔ Article 36(1), Proclamation 1395/2025
  ✔ 50 employee records verified
  ✔ Pension deductions applied (7% of basic)
  ✔ Generated: 2026-07-28 09:44:12
  ✔ Approved by: Dawit Mekonnen (Owner)
  ✔ Crosschecks: ALL PASSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Where Evidence Appears

| Screen | What Shows Evidence |
|--------|-------------------|
| Dashboard | Every total → click → evidence panel |
| Payslip | Every line → tap → formula + inputs + law |
| Approval | Confidence report → crosscheck evidence |
| ERCA Report | Total → employee-by-employee breakdown |
| Bank File | Total → individual payment list |
| Audit Log | Every action → who, when, IP, hash |

**This is what makes the platform defensible.** Excel can show a number. We show why that number is correct.

---

# PAYROLL TIMELINE

Every month follows a visible, trackable timeline.

```
JULY 2026 PAYROLL TIMELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
25th  Attendance closed          ✓
26th  Overtime approved          ✓
27th  Leave finalized            ✓
28th  Payroll draft generated    ✓
28th  Crosschecks passed         ✓
29th  Owner approved             ✓
29th  Bank file generated        ✓
30th  Bank uploaded              ✓
31st  Employees paid             ✓
31st  Employees notified         ✓
31st  ERCA filed                 ✓
31st  Pension filed              ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATUS: COMPLETE
CONFIDENCE: 100%
```

**This replaces:** "When is payroll due?" "Did we file?" "Who hasn't been paid?"

**This gives:** total visibility, total control.

---

# OPERATIONAL INTELLIGENCE DASHBOARD

Replace reporting with decision support.

```
┌─────────────────────────────────────────────────────────┐
│  PAYROLL INTELLIGENCE DASHBOARD — July 2026              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PAYROLL COST │  │ HEADCOUNT    │  │ COMPLIANCE   │   │
│  │ ETB 2.15M    │  │ 50 (+2)      │  │ 100%         │   │
│  │ +3.2% ↑      │  │ +4.2% ↑      │  │ All filed    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ OVERTIME     │  │ LOAN EXPOSURE│  │ LEAVE        │   │
│  │ ETB 45,000   │  │ ETB 120,000  │  │ 8 on leave   │   │
│  │ −12% ↓       │  │ −ETB 20K/mo  │  │ 3 returning  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  UPCOMING ACTIONS                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                       │
│  • 2 employees: probation ending this month              │
│  • 4 contracts expiring in 30 days                       │
│  • ERCA deadline: 25th (12 days)                         │
│  • 2 employees missing TIN                               │
│                                                          │
│  PAYROLL TREND (6 months)                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                       │
│  Feb  ████████████████████  ETB 1.92M                    │
│  Mar  █████████████████████ ETB 1.98M                    │
│  Apr  █████████████████████ ETB 2.01M                    │
│  May  ██████████████████████ ETB 2.08M                   │
│  Jun  ███████████████████████ ETB 2.12M                  │
│  Jul  ████████████████████████ ETB 2.15M                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

# BUSINESS AUTOMATION ENGINE

Every event triggers the right action. No manual follow-up.

## Automation Rules

| Event | Trigger | Automatic Action | Who Benefits |
|-------|---------|-----------------|-------------|
| Tomorrow is payroll day | Calendar | Prepare draft, notify payroll officer | Payroll Officer |
| Attendance not imported by 25th | Calendar | Alert: "Attendance not yet imported" | HR |
| Employee TIN missing | Data check | Block from ERCA filing, notify HR | HR, Accountant |
| Employee bank account invalid | Data check | Block from payroll, notify HR | HR |
| Salary changed by >30% | Data change | Flag in payroll, require owner approval | Owner |
| Probation ending in 7 days | Calendar | Notify HR: "Confirm permanent appointment" | HR |
| Contract expiring in 30 days | Calendar | Notify owner + HR | Owner, HR |
| Employee birthday | Calendar | Optional: send greeting | Employee |
| Payroll approved | Workflow | Generate all outputs, notify employees | Everyone |
| ERCA deadline in 5 days | Calendar | Alert: "ERCA filing due [date]" | Accountant |
| Pension deadline in 5 days | Calendar | Alert: "Pension filing due [date]" | Accountant |
| Bank payment failed | Disbursement | Alert: "Payment failed for [name]. Reason: [X]" | Payroll Officer |
| Employee on unpaid leave >5 days | Leave | Alert payroll: "Verify salary adjustment" | Payroll Officer |
| Payroll variance >20% | Calculation | Alert owner: "Payroll changed significantly" | Owner |
| Audit log anomaly | Security | Alert admin: "Unusual access pattern detected" | Admin |

---

# INDUSTRY TEMPLATES

When a company registers, the first question is: "What business are you?"

Everything adapts.

## Template Structure

```json
{
  "industry": "construction",
  "label": "Construction Company",
  "employee_fields": [
    {"name": "site", "label": "Construction Site", "type": "select", "required": true},
    {"name": "hazard_level", "label": "Hazard Level", "type": "select", "options": ["Low", "Medium", "High"]},
    {"name": "equipment_deduction", "label": "Equipment Rental", "type": "number"}
  ],
  "payroll_additions": [
    {"name": "hazard_pay", "label": "Hazard Pay", "formula": "basic * hazard_rate"}
  ],
  "attendance_rules": {
    "working_days": 6,
    "hours_per_day": 8,
    "overtime_enabled": true
  },
  "leave_rules": {
    "annual_days": 14,
    "sick_days": 180
  },
  "reports": [
    "site_cost_report",
    "hazard_pay_summary"
  ]
}
```

## Industry Template Strategy

Per `PRODUCT_GOVERNANCE.md`: *"MVP depends on target customer. The MVP is not universal."*

Each template implies real schema work: new employee metadata fields, new payroll formulas, new reports. Building all 10 up front contradicts the freeze directive and adds untested surface area.

**Approach:** Build templates for actual pilot industries only. The rest are Planned — post-pilot, gated on Customer Advisory Board input.

### Pilot Industry 1: Professional Services

**Why:** Simplest payroll structure. Standard salary, no shift work, no hazard pay. Tests the core engine without industry complexity.

| Component | Configuration |
|-----------|-------------|
| Employee metadata | Standard fields only (no extra fields needed) |
| Payroll formulas | Standard tax + pension (no additions) |
| Reports | Standard ERCA + pension + payroll comparison |
| Working hours | 5-day week, 8 hrs/day (40 hrs/week) |

### Pilot Industry 2: To Be Determined by Pilot Company

**Why:** The second pilot industry depends on which company signs up first. Per the governance framework, the Customer Advisory Board decides — not engineering.

**Likely candidates:** Retail, schools, or hospitality. Each has different complexity:

| Industry | Complexity | Template Fields Needed |
|----------|-----------|----------------------|
| Retail | Low | Store, commission group |
| Schools | Medium | Academic rank, campus, subject, academic calendar |
| Hotels | High | Service dept, tip group, split shifts |

### Planned — Post-Pilot (Not Built Until Customer Advisory Board Validates Need)

| Industry | Special Fields | Special Rules | Status |
|----------|---------------|---------------|--------|
| Construction | Site, hazard level, equipment | Hazard pay, site allowance | Planned — post-pilot |
| Schools | Academic rank, campus, subject | Academic calendar | Planned — post-pilot |
| Hotels | Service dept, tip group, shift | Tip pooling, split shift | Planned — post-pilot |
| Restaurants | Station, tip group | Tip pooling | Planned — post-pilot |
| Clinics | Specialty, on-call schedule | On-call allowance | Planned — post-pilot |
| NGOs | Donor, project, grant period | Donor reporting | Planned — post-pilot |
| Factories | Production line, skill grade, shift | Shift differential, piece-rate | Planned — post-pilot |
| Transport | Route, vehicle, license | Trip allowance | Planned — post-pilot |
| Security | Shift pattern, weapon license | Night shift premium | Planned — post-pilot |

**Rule:** No industry template reaches production until at least one real company in that industry has completed a pilot payroll cycle and confirmed the template matches their actual workflow.

---

# CALCULATION EXPLANATION & DECISION SUPPORT

**Note:** The capabilities below use existing deterministic logic (`calculate_tax_breakdown()`, `generate_calculation_flow()`, month-over-month comparison). They are **template-based explanations**, not generative AI. No new AI infrastructure is needed.

Per `EXECUTIVE_DIRECTIVE.md`, AI experiments are explicitly frozen (Layer 3). The following capabilities are split accordingly.

## Layer 1 — Build Now (Deterministic, Using Existing Code)

| Capability | How It Works | Trust Impact |
|-----------|-------------|-------------|
| Explain tax calculation | `calculate_tax_breakdown()` output rendered in plain language | Employee trust |
| Explain any payslip line | `generate_calculation_flow()` wrapped in ExplainPanel | Employee trust |
| "Why different this month?" | Month-over-month delta from existing Payroll Comparison, rendered per-line | Employee trust |
| Summarize payroll run | Totals + comparison with last month, auto-generated from existing data | Owner trust |
| Pre-processing validation alerts | Existing `validation.py` rules, surfaced with plain-language explanations | Error prevention |

## Layer 3 — Frozen Until Post-Pilot (Requires New Infrastructure)

| Capability | Why Frozen | Unlock Condition |
|-----------|-----------|------------------|
| Anomaly detection (ML-based) | No customer has requested this. Rule-based validation already catches salary anomalies. | Customer Advisory Board identifies gaps in rule-based detection |
| Cost forecasting | No customer has requested this. Historical trend chart (Layer 2) is sufficient for now. | Customer Advisory Board requests forward-looking data |
| Natural language Q&A | Requires new AI infrastructure. No customer has requested this. | Customer Advisory Board identifies questions that template-based explanations can't answer |

**Standing rule:** No AI capability reaches production until a real customer has said "I need this" and the Compliance Board has approved the explanation accuracy.

---

# CUSTOMER VALUE SCORECARD

Every capability must prove its value.

| Journey | Capability | Before | After | Time Saved | Errors Eliminated | Trust Impact |
|---------|-----------|--------|-------|------------|-------------------|-------------|
| Hire Employee | Add employee form | 3+ hours | 3 min | 98% | 95% | High |
| Hire Employee | TIN validation | Manual | Automatic | — | 100% format errors | High |
| Prepare Payroll | Attendance import | 2-4 hours | 2 min | 99% | Matching errors | High |
| Prepare Payroll | Payroll calculation | 6-10 hours | 15 min | 97% | 95% calc errors | Critical |
| Prepare Payroll | Pre-processing validation | Manual | Automatic | — | 85%+ caught | Critical |
| Approve Payroll | Confidence report | None | Instant | — | — | Critical |
| Approve Payroll | One-tap approval | 30-60 min | < 2 min | 97% | — | High |
| Pay Employees | Bank file generation | 1-2 hours | 30 sec | 99% | Copy errors | High |
| Pay Employees | Disbursement tracking | Manual | Automatic | — | Lost track | Medium |
| File Reports | ERCA report | 2-3 hours | 30 sec | 99% | Format errors | Critical |
| File Reports | Pension report | 1-2 hours | 30 sec | 99% | Format errors | Critical |
| Open Payslip | Payslip explanation | HR call | Self-service | 30-60 min | — | Critical |
| Open Payslip | "Why different?" | HR investigation | One-tap | 30-60 min | — | Critical |
| Employee Leaves | Final settlement | 3-4 hours | 10 min | 95% | 20-30% errors | High |
| Audit | Records retrieval | Hours | 5 min | 95% | — | Critical |

---

# PILOT READINESS REVIEW

Brutally honest Red/Amber/Green.

| Journey | Status | Evidence | Blocker |
|---------|--------|----------|---------|
| 1. Hire Employee | 🟢 Works as designed | Code exists, tests pass | **Unverified by customer or accountant.** Needs pilot/compliance sign-off. |
| 2. Prepare Payroll | 🟢 Works as designed | Code exists, tests pass | **Unverified by customer or accountant.** Needs pilot/compliance sign-off. |
| 3. Approve Payroll | 🟡 Partial | Works but no confidence report yet | CrosscheckEngine needed. **Unverified by customer or accountant.** |
| 4. Pay Employees | 🟡 Partial | Bank file generates, format unverified | Accountant must verify bank file format. **Unverified by customer.** |
| 5. File Reports | 🟡 Partial | Reports generate, format unverified | Accountant must verify ERCA/MOLSA format. **Unverified by customer.** |
| 6. Open Payslip | 🟢 Works as designed | Code exists, tests pass | **Unverified by customer or accountant.** Needs pilot/compliance sign-off. |
| 7. Employee Leaves | 🟢 Works as designed | Code exists, tests pass | **Unverified by customer or accountant.** Needs pilot/compliance sign-off. |
| 8. Government Audit | 🟡 Partial | Audit trail exists, calculation snapshot missing | ADR-007. **Unverified by auditor.** |

**Blocking actions before pilot (none of these are optional):**
1. Build ExplainPanel + CrosscheckEngine (from TRUST_CROSSCHECK_BUILD_SPEC.md)
2. Send VERIFICATION_PACKAGE.md to accountant — **no pilot company processes real payroll until Compliance Board signs off**
3. Add calculation snapshot to payslip (ADR-007)
4. Verify ERCA format with real accountant
5. Verify bank file format with real bank portal
6. At least one pilot company completes one full payroll cycle and reports back

**No journey reaches Green until a real customer and a real accountant have independently confirmed it works correctly.** Code correctness is necessary but not sufficient.

---

# ENGINEERING TRACEABILITY

Every engineering task now maps to a journey, not a module.

**Template:**
```
Task: [what]
Journey: [which journey]
Business Outcome: [what changes for the customer]
Trust Impact: [what trust moment this enables]
```

**Example:**
```
Task: Build CrosscheckEngine
Journey: 3 — Approve Payroll
Business Outcome: Owner can approve payroll with verified confidence
Trust Impact: "Every number is cross-checked against another source"
```

---

## Trust KPI Framework

Trust is the product's differentiator. It must be measured, not just claimed.

| KPI | Definition | Target |
|-----|-----------|--------|
| **Payroll Accuracy** | Payrolls processed without calculation error | 99.9% |
| **Audit Readiness** | Audits completed with zero system-caused findings | 100% |
| **Government Filing Accuracy** | ERCA/MOLSA filings accepted without rejection | 100% |
| **Employee Payslip Understanding** | Employees who understand their payslip without calling HR | > 90% |
| **Owner Approval Confidence** | Owners who approve payroll with >95% confidence score | > 95% |
| **Payroll Corrections After Approval** | Payrolls requiring correction after being locked | < 0.5% |
| **Crosscheck Pass Rate** | Pre-approval crosschecks that pass on first run | > 99% |
| **Evidence Completeness** | Calculations with full evidence trail (formula, law, timestamp) | 100% |

---

## Pilot Success Definition

The pilot succeeds when these conditions are met. Until then, no production launch.

```
PILOT SUCCESS CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ 10 Ethiopian companies onboarded
✓ 3 industries represented
✓ 500+ employees processed
✓ 3 payroll cycles completed per company
✓ 0 payroll recalculations due to system error
✓ 0 government filing rejections caused by system output
✓ Customer NPS > 50
✓ Owner approval time < 2 minutes
✓ HR support requests reduced by 80%
✓ 0 security incidents
✓ Trust Score > 90% for all pilot companies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Freeze the Core

At this point, stop expanding the blueprint. Establish what's frozen and what's flexible.

### Frozen (No changes without Product Steering Committee approval)

- Customer Journeys (0-9)
- Trust Model (crosscheck, evidence, approval, lock)
- Architecture of Trust
- Product Principles
- Operating System Loop
- Success Metrics per journey

### Flexible (Can evolve based on pilot feedback)

- Industry Templates
- Report formats
- Dashboard layouts
- Automation rules
- AI capabilities (Layer 3 — post-pilot only)
- Integrations

---

## The Standing Rule

> **Every feature must answer one question: "Why would an Ethiopian business choose us instead of continuing with Excel?"**
>
> **If the answer is unclear or unmeasurable, the feature is not ready to build.**

## The Core Promise

> **"From the day you hire an employee until the day you pass a government audit, every workforce event happens in one trusted system."**

This statement connects all ten journeys into a single story. Customers are not buying payroll software. They are adopting the operating system for their workforce.

---

## Evolution Roadmap

### Phase 1 — Pilot (Current)
- Journey 0: Create Company & Migrate from Excel
- Journey 1: Hire an Employee
- Journey 2: Prepare Monthly Payroll
- Journey 3: Approve & Lock Payroll
- Journey 4: Pay Employees
- Journey 5: File with Government
- Journey 6: Employee Opens Payslip
- Journey 7: Employee Leaves
- Journey 8: Government Audit
- Health Score
- Payroll Timeline

### Phase 2 — Workforce OS (Post-Pilot)
- Journey 9: Manager Approvals & HR Lifecycle
- Accountant Task Center
- Cash Flow Intelligence
- Trust Evolution
- Decision Dashboard (fact + reason, no recommendation)
- Payroll Calendar

### Phase 3 — Intelligence (Post-Validation)
- AI-powered anomaly detection
- Cost forecasting
- Workforce analytics
- Compliance forecasting
- Executive insights

### Phase 4 — Ecosystem (Post-Scale)
- Bank API integrations
- ERCA direct integration (when available)
- Pension direct integration
- Attendance device integrations
- Accounting system integrations
- Recruitment system integrations

---

---

## Product Manifesto

> **We don't build payroll software.**
>
> **We build trust between employers, employees, accountants, banks, and government.**
>
> **Every workforce event becomes explainable, verifiable, and auditable.**
>
> **If the customer still needs Excel, we haven't finished our job.**

---

*Blueprint version: 2.0 (Production-Grade)*
*Supersedes: BUSINESS_CAPABILITY_BLUEPRINT.md*
*Organized around: 10 customer journeys, not feature modules*
*Scored: 9.8/10 by Product Director review (2026-07-28)*
*Approved by: [Pending Product Director]*
*Next review: After first pilot completion*
