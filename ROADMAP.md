# EthioPayroll — Prioritized Delivery Plan

**Date:** 2026-07-17
**Method:** Scored by (Value × Trust) ÷ Effort
**Owner:** [You]
**Constraint:** 1 developer, realistic velocity

---

## Scoring Legend

| Score | Value / Trust | Effort |
|-------|--------------|--------|
| 5 | Tigist won't use the product without it | 1-2 days |
| 4 | Major pain point, high daily impact | 3-5 days |
| 3 | Nice to have, improves experience | 1-2 weeks |
| 2 | Useful but not urgent | 2-3 weeks |
| 1 | Edge case or future | 3+ weeks |

---

## Full Scoring Table

| # | Item | Value | Trust | Effort | Score | Phase |
|---|------|-------|-------|--------|-------|-------|
| 1 | Transparent calculation breakdown | 5 | 5 | 2 | **12.5** | P0 |
| 2 | Auto-save drafts | 3 | 4 | 1 | **12.0** | P0 |
| 3 | Compliance calendar | 5 | 4 | 2 | **10.0** | P0 |
| 4 | Kill dead code | 2 | 1 | 1 | **2.0** | P0 |
| 5 | Undo approval (1hr window) | 4 | 5 | 3 | **6.7** | P1 |
| 6 | Export everything (CSV) | 2 | 3 | 1 | **6.0** | P1 |
| 7 | Mobile dashboard (2-tap) | 5 | 3 | 3 | **5.0** | P1 |
| 8 | Cash flow pre-flight | 4 | 4 | 3 | **5.3** | P1 |
| 9 | Quick Start wizard | 5 | 4 | 4 | **5.0** | P2 |
| 10 | Adjustment payslips | 3 | 4 | 3 | **4.0** | P2 |
| 11 | Employee leave requests | 4 | 3 | 3 | **4.0** | P2 |
| 12 | WhatsApp notifications | 5 | 3 | 4 | **3.75** | P2 |
| 13 | Accountant dashboard | 5 | 2 | 4 | **2.5** | P3 |
| 14 | Webhook on approval | 3 | 1 | 2 | **1.5** | P3 |
| 15 | Referral program | 3 | 1 | 2 | **1.5** | P3 |
| 16 | Bulk import API | 3 | 1 | 3 | **1.0** | P3 |

---

## P0 — Trust Foundation (Weeks 1-2)

> **Goal:** Tigist trusts the numbers. Data is safe. Compliance is visible.
> **Effort:** ~8 days

### 1. Transparent Calculation Breakdown
**Score:** 12.5 | **Effort:** 2 days

**Why first:** If Tigist doesn't trust the math, nothing else matters. She'll compare to Excel, find a discrepancy, and leave.

**What:**
- Every payslip shows: Gross → Pension (7%) → Taxable → Tax (bracket) → Deductions → Net
- PDF includes the same breakdown with Ethiopian tax bracket table
- Dashboard shows "How is tax calculated?" expandable section
- Highlight the specific bracket her employees fall into

**Where:** `payroll_engine/pdf.py`, `payroll_engine/templates/portal/payslip.html`, tax.py already has the bracket data

**Verify:** Print a payslip. Hand it to someone who doesn't know the system. Can they follow the math?

---

### 2. Auto-Save Drafts
**Score:** 12.0 | **Effort:** 1 day

**Why:** Connection drops. Browser crashes. Tigist loses 20 minutes of data entry. She won't come back.

**What:**
- PayrollDraft model already exists
- Wire auto-save on every form field change (debounced 2 seconds)
- Show "Draft saved" indicator
- On return: "You have an unsaved draft from [date]. Resume?"

**Where:** `payroll_engine/payroll_bp.py`, `templates/payroll/spreadsheet.html`

**Verify:** Start entering payroll. Close browser. Reopen. Draft is there.

---

### 3. Compliance Calendar
**Score:** 10.0 | **Effort:** 2 days

**Why:** ERCA/PSSA deadlines are the #1 reason Tigist pays an accountant. If the system tracks them, she doesn't need one.

**What:**
- `compliance.py` already has deadline data
- Dashboard widget: "Next 3 deadlines" with days remaining
- Color coding: green (>7 days), yellow (3-7), red (<3)
- Each deadline links to the pre-generated report
- Monthly email/SMS reminder (even manual to start)

**Where:** New template partial in `templates/dashboard/`, data from `compliance.py`

**Verify:** Open dashboard. See "ERCA filing: 4 days (July 21)". Click → downloads the file.

---

### 4. Kill Dead Code
**Score:** 2.0 | **Effort:** 1 day

**Why:** Reduces confusion, speeds up onboarding for future developers, shrinks attack surface.

**What:**
- Delete demo mode with hardcoded fake data
- Remove 50 dead i18n keys
- Delete orphaned `celery_worker.py`
- Remove unused Flask-Babel dependency

**Verify:** `pytest -q` still passes. No dead imports.

---

## P1 — Safety & Daily Use (Weeks 3-5)

> **Goal:** Tigist uses this daily, not just on the 29th. Mistakes are fixable.
> **Effort:** ~12 days

### 5. Undo Approval
**Score:** 6.7 | **Effort:** 3 days

**Why:** The fear of "what if I screw up" keeps Tigist in Excel. Undo removes that fear.

**What:**
- "Undo" button visible for 1 hour after approval
- Only works if disbursement hasn't happened
- Reverts status to "draft", clears approval metadata
- Audit log records the undo

**Where:** `payroll_bp.py`, `payroll_service.py`, `templates/payroll/run_detail.html`

**Verify:** Approve payroll. Click undo within 1 hour. Status returns to draft. After 1 hour, button disappears.

---

### 6. Export Everything
**Score:** 6.0 | **Effort:** 1 day

**Why:** "Can I get this in Excel?" is the first question every Ethiopian business owner asks. Saying yes builds trust.

**What:**
- One-click CSV export for: employees, payroll history, payslips summary, leave balances, audit log
- Button on each list page: "Export CSV"
- Filename includes date: `employees_2026-07-17.csv`

**Where:** Each blueprint's list view

**Verify:** Click export on employees page. Open CSV. All columns, all rows, correct encoding.

---

### 7. Mobile Dashboard
**Score:** 5.0 | **Effort:** 3 days

**Why:** Tigist checks payroll on her phone during lunch. If it's painful, she waits until she's at a laptop — and forgets.

**What:**
- Redesign dashboard for mobile: single column, large touch targets
- "Approve payroll" as a single button (not buried in a form)
- Employee list: search + tap to view (not a table)
- Payslip: tap to download PDF
- Leave the full accountant view for desktop — just make mobile *usable*

**Where:** `templates/dashboard.html`, `static/css/`, new mobile-specific templates

**Verify:** Open on a phone. Can Tigist approve payroll in 2 taps? Can she see a payslip in 3?

---

### 8. Cash Flow Pre-Flight
**Score:** 5.3 | **Effort:** 3 days

**Why:** Approving payroll you can't afford is worse than not having a payroll system.

**What:**
- Before approval: show total payroll cost vs. bank balance (manual input)
- Highlight if shortfall: "You're short 67,000 ETB. Consider staggering payments."
- Show breakdown: salaries, tax, pension — what's due when
- "Stagger" suggestion: split into 2 payments, show schedule

**Where:** `payroll_bp.py`, new template partial in approval flow

**Verify:** Enter bank balance of 89,000. Try to approve payroll of 156,000. System warns and suggests staggering.

---

## P2 — Growth Features (Weeks 6-10)

> **Goal:** Employees love it. It spreads. Corrections are easy.
> **Effort:** ~16 days

### 9. Quick Start Wizard
**Score:** 5.0 | **Effort:** 4 days

**Why:** 30+ minutes of form-filling before first payslip = instant churn.

**What:**
- Step 1: Company name + your name + phone
- Step 2: Paste or upload Excel (name, phone, salary)
- Step 3: Auto-detect columns, preview, confirm
- Step 4: First payroll auto-generated, show payslips
- Total time: under 10 minutes

**Where:** New blueprint `wizard_bp.py`, new templates

**Verify:** New user signs up. Pastes Excel with 8 employees. Sees first payslips in 8 minutes.

---

### 10. Adjustment Payslips
**Score:** 4.0 | **Effort:** 3 days

**Why:** Payroll is approved, then Tigist realizes she forgot overtime. Without this, she's stuck.

**What:**
- "Create adjustment" button on approved payroll runs
- Enter adjustment amount + reason
- Generates separate payslip marked "Adjustment"
- Links to original run for audit trail

**Where:** `payroll_bp.py`, `models.py` (Payslip type field), new template

**Verify:** Approve payroll. Add 2,000 ETB overtime adjustment. Separate payslip generated. Original unchanged.

---

### 11. Employee Leave Requests
**Score:** 4.0 | **Effort:** 3 days

**Why:** Employees asking "can I take leave?" via WhatsApp is the #1 daily interruption for Tigist.

**What:**
- Employee portal: "Request Leave" form (type, dates, reason)
- Manager dashboard: pending requests with approve/reject
- Auto-updates leave balance on approval
- Notification to employee on decision

**Where:** `portal_bp.py`, `employees_bp.py`, new templates

**Verify:** Employee requests 3 days annual leave. Manager approves. Balance updates. Employee sees status.

---

### 12. WhatsApp Notifications
**Score:** 3.75 | **Effort:** 4 days

**Why:** Tigist's employees don't check email. They don't check the portal. They check WhatsApp.

**What:**
- On payroll approval: "Your salary of 9,232 ETB has been processed. Download payslip: [link]"
- On leave decision: "Your leave request has been approved."
- Start with a WhatsApp Business API integration (or manual send to start)

**Where:** New notification service, webhook on payroll approval

**Verify:** Approve payroll. Employee receives WhatsApp message with net pay and link.

---

## P3 — Scale & Distribution (Weeks 11+)

> **Goal:** Accountants bring clients. API enables partners. Product grows without you.
> **Effort:** ~12 days

### 13. Accountant Dashboard
**Score:** 2.5 | **Effort:** 4 days

**Why:** 1 accountant serves 50 SMEs. Win the accountant, win 50 Tigists.

**What:**
- Accountant role: see all linked companies
- Batch ERCA filing for all clients at once
- Compliance overview: which clients are late?
- Accountant gets Standard tier free

**Where:** New blueprint `accountant_bp.py`, role system extension

**Verify:** Accountant logs in. Sees 5 companies. Files ERCA for all in one click.

---

### 14. Webhook on Payroll Approval
**Score:** 1.5 | **Effort:** 2 days

**What:** `after_payroll_approved` event fires webhook URL. Enables Sage/Xero/accounting integrations.

---

### 15. Referral Program
**Score:** 1.5 | **Effort:** 2 days

**What:** "Refer a business, both get 1 month free." Track via unique link.

---

### 16. Bulk Import API
**Score:** 1.0 | **Effort:** 3 days

**What:** `POST /api/v1/employees/bulk` with CSV/JSON. For partners importing from other systems.

---

## Summary

| Phase | Weeks | Items | Focus | Days |
|-------|-------|-------|-------|------|
| P0 | 1-2 | 4 | Trust + Safety + Compliance | ~8 |
| P1 | 3-5 | 4 | Daily Use + Mistake Recovery | ~12 |
| P2 | 6-10 | 4 | Growth + Self-Service | ~16 |
| P3 | 11+ | 4 | Scale + Distribution | ~12 |
| **Total** | **~11 weeks** | **16** | | **~48 days** |

---

## What NOT to Build (Yet)

| Item | Why Not |
|------|---------|
| Full offline mode | Hawassa has 4G. Auto-save covers 90% of the risk. |
| White-labeling | No clients yet. Build for Tigist first. |
| Multi-country | Ethiopia first. Expand after product-market fit. |
| Push notifications | WhatsApp is where Ethiopian users are. Push is noise. |
| Redis / advanced infra | SQLite→Postgres migration is done. Scale infra when you have scale. |

---

## Decision Rules

1. **If Tigist doesn't trust the number, nothing else matters.** → Transparent math is always first.
2. **If she can't undo a mistake, she won't commit.** → Undo + adjustments before growth features.
3. **If employees don't use it, it's Tigist's tool not a platform.** → Leave requests + WhatsApp before API.
4. **If the accountant isn't the channel, you're selling 1-by-1.** → Accountant dashboard before referral program.
5. **If the beta isn't in front of real Tigists, everything is theory.** → Beta after P1, not after P3.

---

## The Only Metric That Matters

> **After 8 weeks:** Can Tigist go from "I have employees" to "everyone got paid, ERCA is filed, and I did it on my phone in 5 minutes"?

If yes → you have a product.
If no → find out why and fix that before building anything else.
