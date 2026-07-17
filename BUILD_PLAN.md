# BUILD PLAN — What to Build Next (Prioritized)

**Based on:** FRICTION_PATTERNS.md + Tigist user testing
**Started:** 2026-07-17

---

## THE CORE PROBLEM YOU JUST IDENTIFIED

Right now, the compliance panel and reports are **hardcoded to the latest completed run**. If Tigist wants to:

- Generate ERCA for last month (not this month)
- Download a bank file for a specific payroll run
- See compliance status for a different period
- Change the reporting date

She can't. The system picks for her. **She needs a date/run selector on every compliance and report screen.**

---

## PHASE 1 — Date/Period Selector (Do This First)

This fixes the most frustrating thing: "I want to see July's data, not August's."

### What to build:

**A. Period selector component (reusable)**
- Dropdown showing all completed payroll runs with period labels (e.g., "Hamle 2018 — PR-2018-10-001")
- Default: latest completed run
- When she changes it, all compliance cards, download buttons, and reports update

**B. Dashboard compliance panel with selector**
- Period dropdown at the top
- ERCA/Pension/Bank download buttons tied to selected run
- "How to file" instructions always visible

**C. Reports page with period selector**
- Same dropdown
- All downloads (ERCA, Pension, Bank, CSV exports) tied to selected run
- Compliance score recalculated for selected period

### Files to change:
1. `payroll_engine/templates/_compliance_panel.html` — NEW (from FRICTION_PATTERNS.md, add period dropdown)
2. `payroll_engine/templates/dashboard.html` — replace hardcoded deadline cards with compliance panel
3. `payroll_engine/templates/reports.html` — add period dropdown, wire downloads to selected run
4. `payroll_engine/main.py` — pass all completed runs to dashboard context
5. `payroll_engine/reports_bp.py` — add period filter to reports page

---

## PHASE 2 — Pre-Approval Validation (Highest ROI) ✅ DONE

Tigist's biggest fear: approving payroll with mistakes. The validation engine now catches 3 additional issues.

### What was built:
1. **Payroll variance check** — flags when total payroll changes >20% from last month
2. **Salary change 30% detection** — flags when individual salary changes >30% (lowered from 10x)
3. **Pending unpaid leave detection** — flags employees with approved unpaid leave who still show full salary

### Files changed:
1. `payroll_engine/validation.py` — added `_check_salary_change_significant()`, `_check_payroll_variance()`, `_check_pending_leave_impact()`
2. `tests/test_validation_phase2.py` — 19 tests covering all edge cases

---

## PHASE 3 — Proactive System (Tigist's Phone Buzzes)

The system should work before Tigist opens it.

### What to build:
1. **Monthly draft pre-calculation** — on the 28th, auto-create draft payroll from existing employees
2. **Compliance deadline nudges** — daily check, WhatsApp notification 3 days before ERCA/Pension due
3. **"Draft ready" notification** — in-app + WhatsApp when draft is prepared

### Files to change:
1. `payroll_engine/services/monthly_preparer.py` — NEW (from FRICTION_PATTERNS.md Pattern 7)
2. `payroll_engine/__init__.py` — register scheduler hook
3. `cron` or `APScheduler` — trigger on 28th + daily

---

## PHASE 4 — Employee Self-Service Polish

Employees should be able to do everything without Tigist's help.

### What to build:
1. **Payslip acknowledgment** — "I received this payslip" button (from FRICTION_PATTERNS.md Pattern 2)
2. **Notification when payslip is ready** — WhatsApp + in-app to each employee after approval
3. **Leave balance in employee portal** — show remaining days per leave type

### Files to change:
1. `payroll_engine/models.py` — add `PayslipAcknowledgment` model
2. `payroll_engine/portal_bp.py` — add acknowledge route
3. `payroll_engine/templates/employee_portal/payslip_detail.html` — add acknowledge button
4. `payroll_engine/services/payroll_service.py` — notify employees after approval

---

## PHASE 5 — Disbursement Progress

The gap between "payroll approved" and "employees paid."

### What to build:
1. **Disbursement progress page** — shows all employees grouped by bank with download buttons
2. **"Mark as disbursed" flow** — clear status progression: pending → file downloaded → disbursed → confirmed
3. **Per-bank download** — download CBE file separately from Telebirr file

### Files to change:
1. `payroll_engine/templates/disbursement_progress.html` — NEW (from FRICTION_PATTERNS.md Pattern 5)
2. `payroll_engine/payroll_bp.py` — add disbursement route

---

## PHASE 6 — Size-Appropriate Interface

### What to build:
1. **Sidebar adapts to company size** — hide advanced features for small companies
2. **Quick Start as default onboarding** — not "Add Employee" one-by-one
3. **Context-aware labels** — "Compliance & Reports" for small companies, "Reports" for large

### Files to change:
1. `payroll_engine/templates/base.html` — conditional sidebar items
2. `payroll_engine/__init__.py` — inject `employee_count` into context processor
3. `payroll_engine/templates/dashboard.html` — make Quick Start the primary first-run path

---

## WHAT TO BUILD TODAY

**Phase 1 — the date/period selector.** It's the single most impactful change because:

1. It fixes Tigist's #1 frustration: "I can't pick which month to look at"
2. It unblocks all compliance workflows — she can now generate ERCA for any past month
3. It's the foundation for the compliance calendar panel
4. It's relatively small — a dropdown + wiring existing routes

After Phase 1, do Phase 2 (validation) because it prevents costly mistakes.

---

## PRIORITY ORDER

```
Phase 1: Date/Period Selector     ← DO THIS NOW
Phase 2: Pre-Approval Validation  ← DO THIS NEXT
Phase 3: Proactive System         ← THEN THIS
Phase 4: Employee Self-Service    ← THEN THIS
Phase 5: Disbursement Progress    ← THEN THIS
Phase 6: Size-Appropriate UI      ← LAST
```

Each phase is 2-4 hours of work. Total for all 6 phases: about 2-3 days.
