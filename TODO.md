# TODO — Trust Architecture Roadmap

**Last updated:** 2026-08-05
**Philosophy:** Stop thinking in features. Think in Trust Layers.

Every layer answers one question an accountant asks before trusting the system.

---

## Layer 1 — Visibility: "What changed?" ✅ IN PROGRESS

| Pattern | Status | File |
|---|---|---|
| Change Summary | ✅ Implemented (20 tests) | `payroll_engine/change_summary.py` |
| Payroll Narrative | 🔲 Not started | New file: `payroll_engine/narrative.py` |

**Remaining:**
- [ ] Wire Change Summary into payroll review template
- [ ] API endpoint: `GET /api/v1/payroll-runs/<id>/changes`
- [ ] Payroll Narrative — generate plain-English paragraph from Change Summary

---

## Layer 2 — Explanation: "Why did it change?" 🔲

| Pattern | Status | File |
|---|---|---|
| Variance Explanation | 🔲 Not started | New file: `payroll_engine/variance.py` |
| Per-employee drill-down | 🔲 Not started | Template update |

**What to build:**
- [ ] For each employee with salary change, generate explanation:
  - "Salary increased from ETB 10,000 to ETB 12,000 because of promotion (approved by HR on 2026-07-15)"
- [ ] Aggregate explanations into human-readable breakdown:
  - "Net payroll increased by ETB 43,500: 3 promotions (+18,000), overtime (+14,200), 2 new hires (+8,000), transport allowance (+3,300)"
- [ ] Link to audit log entries for each change
- [ ] API endpoint: `GET /api/v1/payroll-runs/<id>/explanation`

---

## Layer 3 — Confidence: "Can I trust this?" 🔲

| Pattern | Status | File |
|---|---|---|
| Confidence Score | 🔶 Compliance score exists, needs trust layer | `payroll_engine/compliance.py` |
| Validation Checklist | 🔲 Not started | New file: `payroll_engine/confidence.py` |

**What to build:**
- [ ] Confidence score = weighted checklist of system checks:
  - No validation errors (25%)
  - Tax rules current (20%)
  - Pension calculated correctly (20%)
  - No unusual salary variance (15%)
  - All employees reviewed (10%)
  - Filing deadline not passed (10%)
- [ ] Display as percentage with green/yellow/red
- [ ] Show which checks passed and which failed
- [ ] API endpoint: `GET /api/v1/payroll-runs/<id>/confidence`

---

## Layer 4 — Filing: "Am I ready to submit?" 🔲

| Pattern | Status | File |
|---|---|---|
| Filing Workspace | 🔶 FilingRecord model exists | `payroll_engine/models.py` |
| Filing Progress Tracker | 🔲 Not started | New template: `filing_workspace.html` |

**What to build:**
- [ ] Single page showing all filing readiness:
  - Payroll: ✅ Complete
  - Tax Report: ✅ Ready
  - Pension Report: ✅ Ready
  - Bank File: ✅ Ready
  - Submission Deadline: 3 days remaining
- [ ] "Generate Filing Package" button (all files in one download)
- [ ] Deadline countdown with color coding
- [ ] Mark as filed with confirmation number

---

## Layer 5 — Recovery: "What if I'm wrong?" 🔲

| Pattern | Status | File |
|---|---|---|
| Undo with time window | 🔶 Undo exists, no time window | `payroll_bp.py` line 700 |
| Adjustment workflow | 🔶 Adjustment payslip exists | `payroll_bp.py` line 821 |

**What to build:**
- [ ] Time-bounded undo: "Undo available until 2:43 PM"
- [ ] Clear messaging: "After that, create Adjustment Payroll"
- [ ] Adjustment payslip with mandatory reason field
- [ ] Show adjustment history on original payslip
- [ ] No contradictory messaging

---

## Layer 6 — Narrative: "Tell me the story" 🔲

| Pattern | Status | File |
|---|---|---|
| Payroll Narrative | 🔲 Not started | New file: `payroll_engine/narrative.py` |

**What to build:**
- [ ] Generate plain-English paragraph from Change Summary:
  > "August payroll includes 128 employees, 2 new hires, 1 resignation, 3 promotions, 12 overtime claims, and no tax rule changes. Total payroll increased by 1.4%, primarily because of overtime and new hires. No unusual variances were detected."
- [ ] Include on dashboard, payroll review, and filing workspace
- [ ] API endpoint: `GET /api/v1/payroll-runs/<id>/narrative`

---

## The Cockpit Dashboard 🔲

**The landing page answers 5 questions in under 10 seconds:**

1. **What needs my attention today?** → Action items, deadlines, errors
2. **What changed since last payroll?** → Change Summary (Layer 1)
3. **Is anything unusual?** → Variance flags (Layer 2)
4. **Am I ready to file?** → Filing readiness (Layer 4)
5. **What is blocking me?** → Validation errors, missing data

**Status:** 🔲 Not started
**File:** New template: `cockpit.html`

---

## Priority Order

| # | What | Layer | Why first |
|---|---|---|---|
| 1 | Wire Change Summary into payroll review | 1 | Already built, just needs UI |
| 2 | Payroll Narrative | 6 | Highest impact per line of code |
| 3 | Variance Explanation | 2 | Explains the "why" behind changes |
| 4 | Confidence Score | 3 | Builds trust before approval |
| 5 | Filing Workspace | 4 | Turns reports into guided workflow |
| 6 | Recovery improvements | 5 | Removes fear of mistakes |
| 7 | Cockpit Dashboard | All | Combines all layers into one view |

---

## Completed (for reference)

- [x] Trust Design System defined (5 patterns, 489 lines)
- [x] Experience Review completed (716 lines, 12 findings)
- [x] Customer Journey Blueprint (2,073 lines)
- [x] Friction Patterns catalog (1,129 lines)
- [x] Trust Pattern #1: Change Summary (20 tests)
- [x] Webhook events (7 total with retry)
- [x] Accounting exports (QuickBooks, Xero, Peachtree, CSV)
- [x] API endpoints (19 total including accounting + bank file)
- [x] Backup/restore test suite (38 tests)

---

## Long-term Vision

```
Payroll Engine → Knowledge Platform → Trust Platform
     ↓                  ↓                   ↓
  Computes          Proves it's         Explains it
  correctly         legally correct     understandably
```

The Trust Platform is the product differentiator. Anyone can build a payroll calculator. Nobody in Ethiopia has built one that accountants actually trust.
