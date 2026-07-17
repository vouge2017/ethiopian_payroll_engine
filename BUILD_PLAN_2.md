# BUILD PLAN 2 — Production Hardening

**Started:** 2026-07-17
**Based on:** ChatGPT readiness review + our own gap analysis
**Goal:** Make the system ready for 1,000+ real Ethiopian businesses

---

## What We're Building (5 tasks, ~7 hours)

| # | Task | Why It Matters | Effort |
|---|---|---|---|
| 1 | Production Readiness Scoring | Clear 1-10 scores for stakeholders | 30 min |
| 2 | PDF Generation Failure Handling | Will break at 50+ employees — partial payslips, stuck "processing" status | 2 hours |
| 3 | Ethiopian Calendar Edge Cases | Pagumē (13th month), year boundaries, leap years — real compliance risk | 1 hour |
| 4 | Performance Testing at 100 Employees | Know your limits before customers hit them | 1 hour |
| 5 | Print-Optimized Payslips | Ethiopian businesses print payslips — current PDFs aren't optimized for A4 printing | 2 hours |

---

## Phase 1: Production Readiness Scoring

**What:** Score every category 1-10 based on what we actually built.

**Categories:**
- Architecture
- Code Quality
- Security
- Performance
- Testing
- Payroll Accuracy
- Compliance
- UX
- Mobile Experience
- Localization
- Scalability
- Reliability
- Maintainability

**Output:** A markdown table with scores and explanations.

**Files:** `PRODUCTION_READINESS_SCORE.md` — NEW

---

## Phase 2: PDF Generation Failure Handling

**Problem:** `process_payroll()` in `payroll_service.py` generates PDFs in a loop. If one PDF fails (font missing, disk full, corrupt data), the entire approval fails mid-way. Some payslips are created, some aren't. The run stays "processing" forever.

**What to build:**
1. Wrap each PDF generation in try/except
2. If a PDF fails, log the error and continue with remaining employees
3. Track which PDFs failed in the result
4. Show Tigist: "7 of 8 payslips generated. 1 failed — Dawit Mekonnen (disk full)"
5. Add retry route: re-generate failed PDFs without re-running entire payroll

**Files to change:**
- `payroll_engine/services/payroll_service.py` — wrap PDF generation in try/except
- `payroll_engine/payroll_bp.py` — add retry route
- `payroll_engine/templates/payroll_results.html` — show failed PDFs
- `tests/test_pdf_failure.py` — NEW: test failure + retry

---

## Phase 3: Ethiopian Calendar Edge Cases

**Problem:** The Ethiopian calendar has a 13th month (Pagumē) with 5 or 6 days. Year boundaries are different from Gregorian. We haven't tested these edge cases.

**What to build:**
1. Test Pagumē period string generation ("2018-13")
2. Test year boundary (Meskerem 1 = September 11/12)
3. Test leap year handling (every 4 years, no exceptions in Ethiopian calendar)
4. Test payroll for employees who start mid-Pagumē
5. Test ERCA deadline calculation for Pagumē payroll

**Files to change:**
- `tests/test_ethiopian_calendar_edge.py` — NEW: edge case tests
- `payroll_engine/ethiopian_calendar.py` — fix any issues found
- `payroll_engine/compliance.py` — verify deadline calculation for Pagumē

---

## Phase 4: Performance Testing at 100 Employees

**Problem:** We've only tested with 8-15 employees. What happens at 100?

**What to build:**
1. Create a test that generates 100 employees and runs payroll
2. Measure: CSV upload time, validation time, approval time, PDF generation time
3. Identify bottlenecks (N+1 queries, unbounded loops)
4. Add indexes if needed
5. Document limits: "Payroll approval takes X seconds for N employees"

**Files to change:**
- `tests/test_performance_100.py` — NEW: performance benchmark
- `payroll_engine/services/payroll_service.py` — optimize if needed
- `PERFORMANCE_LIMITS.md` — NEW: documented limits

---

## Phase 5: Print-Optimized Payslips

**Problem:** Current PDF payslips look fine on screen but aren't optimized for printing. Ethiopian businesses need printed payslips for employees without smartphones.

**What to build:**
1. Add print-specific CSS to PDF generation
2. Ensure A4 page size with proper margins
3. Add company logo, name, TIN to header
4. Add employee name, ID, period prominently
5. Add signature line at bottom
6. Ensure all amounts are right-aligned and readable

**Files to change:**
- `payroll_engine/pdf.py` — optimize layout for printing
- `payroll_engine/templates/employee_portal/payslip_detail.html` — add print button
- Test with sample data

---

## Order of Execution

```
Phase 1: Scoring           ← Do first (quick win, sets baseline)
Phase 2: PDF Failure       ← Do second (highest risk)
Phase 3: Calendar Edge     ← Do third (compliance risk)
Phase 4: Performance       ← Do fourth (know your limits)
Phase 5: Print Payslips    ← Do last (polish)
```

---

## Rules

- Follow PRE_FLIGHT_CHECKLIST.md for every phase
- Run full test suite after every phase
- Update this plan as we go
- If we find new issues, add them here
