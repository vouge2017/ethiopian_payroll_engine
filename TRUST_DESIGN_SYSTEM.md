# EthioPayroll — Trust Design System

**Date:** 2026-08-04
**Purpose:** Define confidence patterns that make every screen feel safe, clear, and trustworthy.
**Standard:** Stripe, Mercury, Linear, Rippling — products where users never hesitate.

---

# Philosophy

Features answer: "Can I do this?"

Trust answers: "Should I trust this?"

Every screen in EthioPayroll must answer five questions:

1. What changed?
2. Why did it change?
3. Is that expected?
4. What needs attention?
5. Can I safely proceed?

If a screen answers fewer than three of these, it's not ready.

---

# Pattern 1: Change Summary

**Purpose:** Show what changed since last payroll, not just what is.

**Where it applies:** Dashboard, Payroll Review, Employee List

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  PAYROLL CHANGE SUMMARY                                 │
│                                                         │
│  This month: 128 employees · ETB 2,872,000              │
│  Last month: 126 employees · ETB 2,840,000              │
│                                                         │
│  Difference: +ETB 32,000 (+1.1%)                        │
│                                                         │
│  What changed:                                          │
│  ✓ 2 new employees (EMP129, EMP130)                     │
│  ✓ 4 overtime claims processed                          │
│  ✓ 1 salary increase (Dawit M.: 10,000 → 12,000)       │
│  ✓ 1 resignation (Abebe K.) — last paycheck             │
│                                                         │
│  No unusual variances detected.                         │
│                                                         │
│  [View Details]                        [Approve Payroll]│
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Always show current vs. previous
- Always explain the delta
- Flag anything > 20% change as "review needed"
- Never show raw numbers without context

**Implementation status:** NOT IMPLEMENTED

---

# Pattern 2: Variance Explanation

**Purpose:** Explain why a specific number changed.

**Where it applies:** Any number that differs from last month

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  Dawit Mekonnen — Salary Change                         │
│                                                         │
│  Last month: ETB 10,000                                 │
│  This month: ETB 12,000                                 │
│  Change: +ETB 2,000 (+20%)                              │
│                                                         │
│  Why: Salary increase effective Meskerem 1, 2018        │
│  Approved by: Tigist (owner) on Aug 3, 2026             │
│                                                         │
│  [View Contract]  [Mark as Expected]  [Flag for Review] │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Every salary change must have a reason
- Every reason must be traceable (who approved, when)
- Changes > 10% require explicit acknowledgment
- "No reason provided" is itself a red flag

**Implementation status:** NOT IMPLEMENTED

---

# Pattern 3: Compliance Badge

**Purpose:** Show legal basis and verification status for every rule.

**Where it applies:** Tax brackets, pension rates, overtime rates, leave rules

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  Income Tax Brackets                                    │
│                                                         │
│  Source: Proclamation No. 1395/2025, Article 11         │
│  Status: ✅ Verified against actual proclamation text   │
│  Last verified: August 1, 2026                          │
│  Verified by: MimoClaw (automated)                      │
│                                                         │
│  0 – 2,000 ETB:     0%                                  │
│  2,001 – 4,000 ETB: 15%                                 │
│  4,001 – 7,000 ETB: 20%                                 │
│  7,001 – 10,000 ETB: 25%                                │
│  10,001 – 14,000 ETB: 30%                               │
│  14,001+ ETB:       35%                                 │
│                                                         │
│  ⚠️ Accountant verification: PENDING                    │
│  [View Proclamation]  [Request Verification]            │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Every rule must show its legal source
- Every rule must show verification status
- Unverified rules must be visually distinct (yellow, not green)
- "Verified" means an accountant confirmed it, not just that the code works

**Implementation status:** PARTIALLY IMPLEMENTED (sources in code comments, no UI badges)

---

# Pattern 4: Safe Approval

**Purpose:** Confirm exactly what will happen before irreversible actions.

**Where it applies:** Payroll approval, employee termination, period lock

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  APPROVE PAYROLL                                        │
│                                                         │
│  By approving, the following will happen:               │
│                                                         │
│  ✓ 128 payslips will be generated                       │
│  ✓ Bank file will be created (ETB 2,450,000)            │
│  ✓ ERCA report will be available for download           │
│  ✓ Employees will be able to view their payslips        │
│                                                         │
│  This action can be undone within 1 hour.               │
│  After 1 hour, you'll need to create an adjustment.     │
│                                                         │
│  [Cancel]                    [Confirm & Approve Payroll] │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Safety checks:                                         │
│  ✅ No duplicate employees                              │
│  ✅ No negative net pay                                 │
│  ✅ All bank accounts valid                             │
│  ✅ Tax calculated using current brackets               │
│  ✅ Pension calculated at 7%/11%                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Always list what will happen (not just "are you sure?")
- Always state the undo policy honestly
- Always show safety checks that passed
- Never say "cannot be undone" if it can be undone

**Implementation status:** PARTIALLY IMPLEMENTED (trust badges exist but are decorative, undo messaging is contradictory)

---

# Pattern 5: Undo Policy

**Purpose:** Clearly explain if and how actions can be reversed.

**Where it applies:** Every destructive or irreversible action

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  UNDO POLICY                                            │
│                                                         │
│  Action: Approve Payroll (Sene 2018)                    │
│                                                         │
│  Can I undo this?                                       │
│  YES — within 1 hour of approval.                       │
│                                                         │
│  What gets undone:                                      │
│  • Payslips will be deleted                             │
│  • Payroll run will revert to "review" status           │
│  • Bank file will be invalidated                        │
│                                                         │
│  What does NOT get undone:                              │
│  • Audit log will retain the approval record            │
│  • Any notifications already sent                       │
│                                                         │
│  After 1 hour:                                          │
│  You'll need to create adjustment payslips.             │
│  Contact support if you need help.                      │
│                                                         │
│  [I understand — Approve]                               │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Never say "cannot be undone" if undo exists
- Always explain the time window
- Always explain what gets undone vs. what doesn't
- For truly irreversible actions, require explicit confirmation

**Implementation status:** NOT IMPLEMENTED (current messaging is contradictory)

---

# Pattern 6: Filing Progress

**Purpose:** Show filing status step by step, not just a download button.

**Where it applies:** ERCA filing, pension remittance, bank disbursement

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  FILING STATUS — Sene 2018                              │
│                                                         │
│  ✅ Payroll processed        May 25                     │
│  ✅ Payslips generated       May 25                     │
│  ✅ Bank file created        May 25                     │
│  ✅ Bank file sent           May 26                     │
│  ✅ Bank confirmed payment   May 28                     │
│                                                         │
│  ⬜ ERCA filing              Due June 25 (21 days)      │
│     [Download ERCA File]  [Mark as Filed ✓]             │
│                                                         │
│  ⬜ Pension remittance       Due June 10 (6 days)       │
│     [Download Pension File]  [Mark as Remitted ✓]       │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  WHAT TO DO:                                            │
│  1. Download the ERCA file (.xlsx)                      │
│  2. Log in to the ERCA portal (etax.erca.gov.et)        │
│  3. Upload the file                                     │
│  4. Come back and mark as filed                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Show the complete workflow, not just the download
- Show deadlines with countdown
- Allow marking as completed
- Provide instructions for external steps

**Implementation status:** NOT IMPLEMENTED (download button only)

---

# Pattern 7: Audit Trail

**Purpose:** Make every important action traceable.

**Where it applies:** Payroll approval, salary changes, settings changes, user actions

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  AUDIT TRAIL — Dawit Mekonnen                           │
│                                                         │
│  Aug 4, 2026 14:30  Tigist (owner)                     │
│  → Approved payroll for Sene 2018                       │
│  → 128 employees, ETB 2,872,000 total                   │
│  → IP: 196.188.x.x                                     │
│                                                         │
│  Aug 3, 2026 10:15  Tigist (owner)                     │
│  → Changed Dawit Mekonnen salary                        │
│  → From: ETB 10,000 → To: ETB 12,000                   │
│  → Reason: Promotion to Senior Sales Manager            │
│                                                         │
│  Jul 25, 2026 16:00  System                            │
│  → ERCA filing downloaded for Sene 2018                 │
│                                                         │
│  Jul 1, 2026 09:00  Tigist (owner)                     │
│  → Created employee Dawit Mekonnen (EMP001)             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Every state change must be logged
- Every log must show who, when, what, and why (if applicable)
- Audit logs must be immutable
- Audit logs must be exportable

**Implementation status:** IMPLEMENTED (AuditLog model with hash chain exists, but UI is basic)

---

# Pattern 8: Recovery Guidance

**Purpose:** Explain how to fix mistakes, not just that they happened.

**Where it applies:** Validation errors, approval failures, data inconsistencies

**Component:**

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️ 3 ISSUES FOUND                                      │
│                                                         │
│  1. Dawit Mekonnen — No bank account                    │
│     → Fix: Go to employee profile → Edit → Add bank     │
│     [Go to Dawit's Profile →]                           │
│                                                         │
│  2. Hana Tesfaye — Salary changed +45%                  │
│     → Fix: Verify this is correct, then approve         │
│     [View Salary History →]  [Mark as Expected ✓]       │
│                                                         │
│  3. Kebede Alemu — Missing TIN                          │
│     → Fix: Add TIN for ERCA filing                      │
│     [Go to Kebede's Profile →]                          │
│                                                         │
│  After fixing, click "Re-validate" to continue.         │
│                                                         │
│  [Re-validate]                                          │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Every error must have a fix path
- Every fix path must be a link, not just text
- "Fix" should take the user directly to the edit screen
- After fixing, the user should return to where they were

**Implementation status:** PARTIALLY IMPLEMENTED (validation shows hints, but no direct links to fix)

---

# Applying Trust Patterns to Existing Screens

## Dashboard — Before vs. After

### Before:
```
4 metric cards (Employees, Compliance, Payroll Runs, Overtime)
+ Action Needed section
+ Charts
+ Compliance Deadlines
+ Recent Runs table
```

### After:
```
Hero: "Good morning, Tigist. August payroll is ready."

Change Summary:
"This month: 128 employees · ETB 2,872,000
 Last month: 126 employees · ETB 2,840,000
 Difference: +1.1% — 2 new employees, 4 overtime claims"

Compliance Checklist:
✅ Payroll processed (Aug 25)
✅ ERCA filed (Aug 28)
⬜ Pension remittance — due in 6 days [Download →]

Quick Actions:
[Run Payroll]  [Add Employee]  [View Reports]
```

## Payroll Review — Before vs. After

### Before:
```
4 summary cards
+ Expandable per-employee details
+ Cash flow check
+ Trust badges (decorative)
+ Password + MFA + checkbox
+ "This cannot be undone"
```

### After:
```
Change Summary:
"128 employees · +1.1% from last month
 2 new · 1 salary change · 4 overtime claims"

Variance Table:
Employee          Last    This    Change   Reason
Dawit Mekonnen    10,000  12,000  +20%     Promotion (Aug 3)
Hana Tesfaye       5,500   5,500   0%      —
Kebede Alemu      18,000  18,000   0%      —
...

Safety Checks:
✅ No duplicates · ✅ No negatives · ✅ All banks valid
✅ Tax: Proclamation 1395/2025 · ✅ Pension: 7%/11%

Approval:
"By approving: 128 payslips generated, bank file created.
 Can be undone within 1 hour."

[Approve Payroll]
```

## Reports — Before vs. After

### Before:
```
3 metric cards
+ Download buttons (ERCA, Pension, Register)
+ Quick links (History, Audit, Analytics)
```

### After:
```
Filing Status:
✅ Payroll processed (Aug 25)
✅ Payslips distributed (Aug 25)
⬜ ERCA filing — due Sep 25 (52 days)
⬜ Pension remittance — due Sep 10 (37 days)

[Download ERCA File]  [How to file →]

History:
Jul 2018 — Filed Jul 28 ✅
Jun 2018 — Filed Jun 30 ✅
```

---

# Trust Design System — Component Library

| Component | Purpose | Used In | Status |
|-----------|---------|---------|--------|
| ChangeSummary | Show current vs. previous with delta | Dashboard, Payroll Review | NOT IMPLEMENTED |
| VarianceExplainer | Explain why a number changed | Payroll Review, Employee Detail | NOT IMPLEMENTED |
| ComplianceBadge | Show legal source + verification status | Settings, Rules display | PARTIALLY IMPLEMENTED |
| SafeApproval | List what will happen + undo policy | Payroll Confirm, Terminate | PARTIALLY IMPLEMENTED |
| UndoPolicy | Clear explanation of reversal capability | Every destructive action | NOT IMPLEMENTED |
| FilingProgress | Step-by-step filing workflow | Reports | NOT IMPLEMENTED |
| AuditTrail | Who did what when | Employee Detail, Settings | IMPLEMENTED (basic) |
| RecoveryGuidance | Fix path for every error | Validation, Errors | PARTIALLY IMPLEMENTED |
| DeadlineCountdown | Days remaining for filing | Dashboard, Reports | IMPLEMENTED |
| ConfidenceIndicator | Visual trust level for each rule | Settings, Compliance | NOT IMPLEMENTED |

---

# Implementation Priority

| # | Component | Impact | Effort | Why First |
|---|-----------|--------|--------|-----------|
| 1 | ChangeSummary | Critical | 2 days | Answers the #1 accountant question: "is this right?" |
| 2 | SafeApproval + UndoPolicy | Critical | 1 day | Fixes the contradictory messaging that destroys trust |
| 3 | FilingProgress | Critical | 2 days | Turns a download button into a workflow |
| 4 | RecoveryGuidance | High | 1 day | Every error gets a direct fix link |
| 5 | VarianceExplainer | High | 2 days | Explains every number that changed |
| 6 | ComplianceBadge | Medium | 1 day | Shows legal basis for every rule |
| 7 | ConfidenceIndicator | Medium | 1 day | Visual distinction between verified and unverified |

Total estimated effort: 10 days

After these 7 components, every screen in the product will answer the five trust questions:
1. What changed? → ChangeSummary
2. Why did it change? → VarianceExplainer
3. Is that expected? → ComplianceBadge + ConfidenceIndicator
4. What needs attention? → FilingProgress + DeadlineCountdown
5. Can I safely proceed? → SafeApproval + UndoPolicy + RecoveryGuidance

---

*This document defines reusable confidence patterns, not one-off fixes.*
*Every new feature must use these patterns.*
*Every existing screen must be upgraded to use them.*
