# TODO — Accountant Operating System Roadmap

**Last updated:** 2026-08-05
**Philosophy:** The explanation comes first. The score comes second. Never build a black box.

---

## What's Built ✅

| Component | Tests | What it does |
|---|---|---|
| Change Summary | 20 | Compares current vs previous payroll |
| Narrative | 30 | Plain-English paragraph explaining the month |
| Exception Intelligence | 20 | Classifies issues as Critical/High/Medium/Low |

---

## Sprint 1 — Evidence Engine 🔲 NEXT

**Every trust signal must be explicit and explainable.**

Not a percentage. A checklist the accountant can see.

```
Payroll Status

✓ 128/128 employees processed
✓ No validation errors
✓ Tax rules verified (Proclamation 1395/2025)
✓ Pension rules verified (Proclamation 1268/2022)
✓ No duplicate payroll
✓ No critical exceptions
✓ All mandatory employee data present
✓ Payroll balanced (debits = credits)

Ready for approval
```

**Build:**
- [ ] `payroll_engine/evidence.py` — collects all trust signals
- [ ] Each signal: name, status (pass/fail/warn), source, explanation
- [ ] Grouped by category: Validation, Compliance, Data Quality, Integrity
- [ ] API: `GET /api/v1/payroll-runs/<id>/evidence`
- [ ] Tests: `tests/test_evidence.py`

**After evidence exists, optionally add:**
```
97% — from: Validation ✓, Compliance ✓, Data Quality ✓, Exceptions ✓, Integrity ✓
```

---

## Sprint 2 — Resolution Intelligence 🔲

**Every issue answers: Impact → Cause → Recommendation → Action.**

Not just "Missing Bank Account." Tell the accountant what to do.

```
⚠ Missing Bank Account

Impact:   Employee cannot receive bank transfer.
Risk:     High
Cause:    Bank account field is empty.
Fix:      Collect bank details or switch to Telebirr.
Action:   [Update Employee →]
Time:     2 minutes
```

**Build:**
- [ ] Enhance `payroll_engine/exceptions.py` — add impact, cause, recommendation, action_url, estimated_time
- [ ] Each issue becomes a mini-guide, not just a warning
- [ ] API: issue objects include resolution fields
- [ ] Tests: update `test_exceptions.py`

---

## Sprint 3 — Payroll Review Workspace 🔲

**One unified flow that matches how accountants think.**

```
Payroll Review — August 2026

1. STORY — What happened?
   [Narrative paragraph]

2. EVIDENCE — Why should I trust this?
   [Evidence checklist]

3. ISSUES — Anything wrong?
   [Exception list with resolution]

4. RESOLUTION — How do I fix it?
   [Actionable guidance for each issue]

5. APPROVAL — Ready?
   [Approve button — only if no critical issues]
```

**Build:**
- [ ] `payroll_engine/templates/payroll_review_workspace.html`
- [ ] Route: `GET /payroll/runs/<id>/review`
- [ ] Combines: Narrative + Evidence + Exceptions + Resolution
- [ ] Approve button disabled if `report.can_approve is False`

---

## Sprint 4 — Confidence Summary 🔲 (only after Sprint 1-3)

**If it genuinely helps users, add an overall score.**

```
Confidence: 97%

From:
✓ Validation (20%)
✓ Compliance (20%)
✓ Data Quality (20%)
✓ Exceptions (20%)
✓ Payroll Integrity (20%)
```

Only build this if accountants in usability sessions say they want it.

---

## Future — Predictive Intelligence 🔲

**Before payroll runs, not after.**

```
Before running payroll:

Expected Net Payroll: ETB 2,847,000
Expected Change: +1.2%
Potential Risks: 3
  - Large overtime: 2 employees
  - Missing TIN: 1 employee

Payroll likely ready after these fixes.
```

Fix problems before payroll is calculated.

---

## Future — Per-Employee Narrative 🔲

**Click one employee, see their story.**

```
Dawit Mekonnen

Salary increased by ETB 2,000.
Reason: Promotion (approved by HR, 2026-07-15)
Tax increased because taxable income moved into next bracket.
Net salary increased by ETB 1,420.
```

---

## What to STOP building

- ❌ No more webhook events
- ❌ No more API endpoints for the sake of endpoints
- ❌ No more export formats
- ❌ No more infrastructure improvements

✅ Focus entirely on the Payroll Review Workspace.

---

## Validation Gate

After Sprint 3, conduct usability sessions with real Ethiopian accountants.

Question: "Do they prefer it over Excel?"

Not: "Does it work?"
