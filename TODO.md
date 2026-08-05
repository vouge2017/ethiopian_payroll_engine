# TODO — Accountant Operating System Roadmap

**Last updated:** 2026-08-05
**Philosophy:** The product is not a toolbox. It's a guided workflow that leads the accountant through their entire month-end process with confidence.

---

## Architecture

```
Ethiopian Payroll Platform

┌────────────────────┐
│  Payroll Engine     │ ← Correct calculations (DONE)
│  Calculates payroll │
└────────────────────┘
        │
        ▼
┌────────────────────┐
│  Knowledge Platform │ ← Verified source of truth (DONE)
│  Laws, rules, tests │
└────────────────────┘
        │
        ▼
┌────────────────────┐
│  Trust Platform     │ ← Explains payroll (IN PROGRESS)
│  Change summaries,  │
│  confidence, filing │
└────────────────────┘
        │
        ▼
┌────────────────────┐
│  Accountant OS      │ ← Guides monthly work (NEXT)
│  Workspaces,        │
│  guided workflows,  │
│  exception handling │
└────────────────────┘
```

---

## Phase 1 — Payroll Review Workspace 🔲

**The most important screen in the product.**

Everything the accountant needs to review and approve payroll in one view.

| Section | Content | Status |
|---|---|---|
| Executive Summary | Employee count, net payroll, delta %, status badge | 🔲 |
| Payroll Narrative | Plain-English paragraph explaining what happened | 🔲 (engine exists in change_summary.py) |
| What Changed | New hires, departures, salary changes, overtime, leave | ✅ (change_summary.py — needs UI) |
| Attention Items | Salary variances >20%, missing data, negative adjustments | 🔲 (variance logic exists, needs exception classification) |
| Confidence Score | Weighted checklist: validation, tax, pension, variance, review | 🔲 |
| Next Action | "Ready for Approval" with Approve button | 🔶 (exists, needs trust context) |

**Files to create/modify:**
- [ ] `payroll_engine/narrative.py` — Generate plain-English summary from Change Summary
- [ ] `payroll_engine/exceptions.py` — Classify issues by severity (Critical/High/Medium/Low)
- [ ] `payroll_engine/confidence.py` — Weighted confidence score from system checks
- [ ] `payroll_engine/templates/payroll_review_workspace.html` — Single-page review experience
- [ ] `payroll_engine/payroll_bp.py` — Wire all components into review route
- [ ] API: `GET /api/v1/payroll-runs/<id>/review` — Returns all workspace data

---

## Phase 2 — Trust Layer 🔲

**The accountant can verify every number.**

| Component | Description | Status |
|---|---|---|
| Confidence Score | Weighted % from system checks | 🔲 |
| Compliance Status | Filing deadline, pension deadline, payment deadline | 🔶 (compliance.py exists) |
| Audit Evidence | Link every number to source (employee record, rule, approval) | 🔲 |
| Validation Report | List of all checks that passed/failed | 🔲 |

---

## Phase 3 — Filing Workspace 🔲

**Guides the accountant through month-end filing.**

| Step | Status |
|---|---|
| Payroll Complete | 🔶 (status tracked) |
| ERCA Report Ready | 🔶 (export exists) |
| Pension Report Ready | 🔶 (export exists) |
| Bank File Ready | 🔶 (export exists) |
| Submission Deadline | 🔶 (deadlines configurable) |
| Mark as Filed | 🔶 (FilingRecord model exists) |

**Gap:** No single workspace that shows all steps together. Each is scattered across different pages.

---

## Phase 4 — Recovery Workspace 🔲

**The accountant knows they can fix mistakes.**

| Component | Status |
|---|---|
| Time-bounded Undo | 🔶 (undo exists, no time window) |
| Adjustment Payroll | 🔶 (adjustment payslip exists) |
| Audit Trail | ✅ (hash-chained audit log) |
| Clear Messaging | 🔲 ("Undo until 2:43 PM, then create adjustment") |

---

## Phase 5 — Accountant Cockpit 🔲

**The landing page answers 5 questions in 10 seconds.**

1. What needs my attention today?
2. What changed since last payroll?
3. Is anything unusual?
4. Am I ready to file?
5. What is blocking me?

---

## Exception Intelligence

**Every payroll run classifies issues by severity.**

| Level | Example | Action |
|---|---|---|
| Critical | Payroll cannot be approved | Block approval |
| High | Large unexplained variance (>20%) | Require review |
| Medium | Missing bank account | Warning, allow proceed |
| Low | New employee, first payroll | Informational |

**File:** `payroll_engine/exceptions.py` (new)

---

## Priority

| # | What | Why |
|---|---|---|
| 1 | **Payroll Narrative** | Highest impact per line of code. Turns numbers into story. |
| 2 | **Exception Classification** | Prioritizes what deserves attention. |
| 3 | **Confidence Score** | Builds trust before approval. |
| 4 | **Payroll Review Workspace** | Combines all Phase 1 into one screen. |
| 5 | **Filing Workspace** | Guides month-end filing. |
| 6 | **Recovery Workspace** | Removes fear of mistakes. |
| 7 | **Accountant Cockpit** | Combines everything into landing page. |

---

## What to STOP building

Per the strategic direction: **pause unrelated engineering features** unless they unblock production.

- ❌ No more webhook events
- ❌ No more API endpoints for the sake of API endpoints
- ❌ No more export formats
- ❌ No more infrastructure improvements

✅ Focus entirely on the workspaces and trust layers.

---

## Validation Gate

After completing Phases 1-3, conduct **usability sessions with real Ethiopian accountants**.

The question is not "does it work?" but "do they prefer it over Excel?"

That's the point where the product is merely correct vs genuinely preferred.
