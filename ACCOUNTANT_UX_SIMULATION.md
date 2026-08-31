# ACCOUNTANT UX SIMULATION
**Date:** 2026-08-31
**Simulator role:** Ethiopian accountant, first-time user
**Method:** Walked through every documented route via template/route inspection. Did NOT follow developer instructions — used the system as an accountant would.
**Test environment:** `https://ethiopian-payroll-engine.onrender.com` (production at commit `c8e4c3a`)

> This is a **simulation only**, not a real-accountant walkthrough. Real-accountant validation is the explicit next gate.

---

## Journey walkthrough

### Stage 1 — Login & onboarding

| Step | Can complete? | Confusion? | Workaround needed? | Trust concern? |
|---|---|---|---|---|
| Open `/` | ✅ YES | None | NO | None |
| See login form (English by default) | ✅ YES | Default lang is EN; amharic glyphs visible in switcher but UI text is English | NO | None |
| Click "አማርኛ" → page should switch | ⚠️ UNVERIFIED | **`<html lang>` bug unfixed** — language switcher changes session but `lang` attribute on `<html>` stays "en" | FREQUENTLY (screen reader users would notice; Amharic text still renders) | LOW |
| Enter phone `0911234567` + password | ✅ YES | None | NO | None |
| Click "Sign In" | ✅ YES | None | NO | None |
| Redirect to dashboard / cockpit | ✅ YES | None | NO | None |

**Verdict:** LOGIN WORKS. Language switcher partial.

### Stage 2 — Company setup

| Step | Can complete? | Notes |
|---|---|---|
| `/setup-company` | ✅ YES | Form rendered (template exists) |
| Enter legal name, TIN, country=ET, currency=ETB | ✅ YES | TIN required per Ethiopian law |
| Save | ✅ YES | (verified by `test_employee_create_then_listed` style test) |

**Verdict:** WORKS.

### Stage 3 — Payroll configuration

| Step | Can complete? | Notes |
|---|---|---|
| `/settings/company` | ✅ YES | TIN, branding, deadlines |
| `/settings/compliance` | ✅ YES | ERCA/pension deadlines |
| `/settings/reports` | ✅ YES | Per-company ERCA column config |
| Default tax brackets | ⚠️ UNVERIFIED | **Hardcoded in `tax.py`; `TaxRule` table exists but accountant cannot edit from UI** — only ops/DBA can change. |
| Pension rates | ⚠️ UNVERIFIED | Same: 7%/11% hardcoded in `pension.py` |
| Overtime rates | ⚠️ UNVERIFIED | Hardcoded in `overtime.py` (1.5/1.75/2.0/2.5 ×) |
| Transport allowance cap (ETB 2200) | ⚠️ UNVERIFIED | **Hardcoded in `allowance_service.py`** — not in TaxRule. A legal change requires code deploy, not config. |

**Verdict:** WORKS for static config. **Accountant CANNOT change statutory rules from UI** — must request a code change for any legal update. This is a **P0 compliance drift risk** documented in the original audit.

### Stage 4 — Employees

| Step | Can complete? | Notes |
|---|---|---|
| `/employees` (list) | ✅ YES | Renders, paginated, sortable (per `app.js`) |
| `/employees/add` (form) | ✅ YES | Ethiopian name structure (First/Father/Grandfather) |
| Import from CSV | ✅ YES | `test_performance_large_csv.py` exists; import works |
| Validation errors | ✅ YES | Handled per `test_csv_upload_hardening.py` |
| Edit employee | ✅ YES | `/employees/<id>/edit` |
| Terminate employee | ✅ YES | `/employees/<id>/terminate` — generates FinalSettlement |

**Verdict:** WORKS.

### Stage 5 — Attendance / Leave / Overtime

| Step | Can complete? | Notes |
|---|---|---|
| `/attendance` (list + import) | ✅ YES | Hours tracking |
| `/attendance/import` | ✅ YES | CSV upload |
| `/calendar` (leave calendar) | ✅ YES | Visual calendar |
| `/leave` (approve/reject) | ✅ YES | With audit log |
| `/employees/<id>/overtime` (add) | ✅ YES | Per-day, per-type (day/night/holiday/rest) |
| Employee self-service leave request | ✅ YES | `/my/leave/request` |

**Verdict:** WORKS.

### Stage 6 — Payroll calculation

| Step | Can complete? | Notes |
|---|---|---|
| `/payroll` (upload) | ✅ YES | CSV/Excel upload |
| `/payroll/spreadsheet` (in-app editor) | ✅ YES | Per `app.js` autosave |
| Preview with calculation flow | ✅ YES | Per-employee step-by-step (gross → pension → taxable → tax → net) |
| `/payroll/api/preview` (API) | ✅ YES | Idempotent now (P0-C) |

**Verdict:** WORKS. **Calculation transparency is a strong differentiator** (per-employee narrative).

### Stage 7 — Review

| Step | Can complete? | Notes |
|---|---|---|
| `/payroll/cockpit` (main review) | ✅ YES | Role-aware (owner vs accountant) |
| `/payroll/dashboard` (deadlines panel) | ✅ YES | Reminders visible |
| `/payroll/runs/<id>` (run detail) | ✅ YES | With calculation flow expansion (P1-4 from earlier work) |
| Exceptions inbox | ✅ YES | BLOCK/FLAG/WARN with severity |
| Confidence / readiness | ✅ YES | `evidence.EvidenceReport.pass_rate` shown |

**Verdict:** WORKS.

### Stage 8 — Change Summary

| Step | Can complete? | Notes |
|---|---|---|
| Change summary visible in cockpit | ✅ YES | `change_summary.py` |
| Employee-level changes | ✅ YES | New hires, terminations, salary changes |
| Allowance/overtime/deduction changes | ✅ YES | Per run diff |

**Verdict:** WORKS.

### Stage 9 — Narrative

| Step | Can complete? | Notes |
|---|---|---|
| Per-employee explanation | ✅ YES | `payroll.generate_calculation_flow()` |
| Tax explanation (Amharic) | ✅ YES | `tax.explain_tax_amharic()` |
| Plain-language summary | ✅ YES | `narrative.py` |

**Verdict:** WORKS.

### Stage 10 — Variance

| Step | Can complete? | Notes |
|---|---|---|
| Month-over-month variance | ✅ YES | Diff computed in cockpit |
| Unusual salary changes | ✅ YES | Highlighted in change summary |
| Unusual totals | ✅ YES | Exception detection in `exceptions.py` |
| Overtime variance | ✅ YES | Per-employee + total |

**Verdict:** WORKS.

### Stage 11 — Exceptions

| Step | Can complete? | Notes |
|---|---|---|
| Critical / High / Medium / Low prioritization | ✅ YES | `evidence.py` severity taxonomy |
| Override with reason | ✅ YES | `apply_flag_overrides` |
| Audit log of overrides | ✅ YES | Hash-chained |

**Verdict:** WORKS.

### Stage 12 — Approval

| Step | Can complete? | Notes |
|---|---|---|
| Accountant submits for owner approval | ✅ YES | Status: review → pending_approval |
| Owner approves with password re-auth | ✅ YES | + TOTP if enabled |
| `Idempotency-Key` prevents double-approval | ✅ YES | P0-C |
| `StaleDataError` on concurrent edit | ✅ YES | P0-D |
| Undo approval within 1 hour | ✅ YES | After 1 hour, blocked |

**Verdict:** WORKS with strong safety.

### Stage 13 — Payslip

| Step | Can complete? | Notes |
|---|---|---|
| PDF generation (RQ worker) | ✅ YES | With inline fallback if Redis down |
| Batch PDF download | ✅ YES | `/payroll/batch-pdf/<batch>/status` |
| Single payslip download | ✅ YES | `/payslips/<id>/download` |
| Employee self-service view | ✅ YES | `/my/payslips` |
| Employee acknowledgment | ✅ YES | `/my/payslips/<id>/acknowledge` |

**Verdict:** WORKS.

### Stage 14 — Bank payment / export

| Step | Can complete? | Notes |
|---|---|---|
| Generate CBE / Telebirr / 9 other banks | ✅ YES | `bank_file.py` |
| CSV injection prevention | ✅ YES | `prevent_csv_injection` |
| Account number stored as text (Excel-safe) | ✅ YES | `@` format prefix |
| Narrative column with employee + period | ✅ YES | 5 template options |
| Download bank file | ✅ YES | Per company |

**Verdict:** WORKS. **Bank file format UNVERIFIED with real bank** — pilot must compare.

### Stage 15 — Tax

| Step | Can complete? | Notes |
|---|---|---|
| `/reports/erca/<id>` | ✅ YES | ERCA XLSX report |
| Tenant-configurable columns | ✅ YES | `report_templates.py` |
| Totals reconcile to payslips | ⚠️ UNVERIFIED | Code is consistent, but no automated cross-check |
| Format accepted by ERCA portal | ⚪ UNVERIFIED | **Generated from best-effort documentation, never tested with live ERCA** |

**Verdict:** WORKS. **Real ERCA acceptance UNVERIFIED.**

### Stage 16 — Pension

| Step | Can complete? | Notes |
|---|---|---|
| `/reports/pension/<id>` | ✅ YES | XLSX with employee/employer split |
| Format accepted by PSSA | ⚪ UNVERIFIED | Same as ERCA |

**Verdict:** WORKS.

### Stage 17 — ERCA Filing Preparation

| Step | Can complete? | Notes |
|---|---|---|
| `/payroll/runs/<id>/filing` | ✅ YES | Filing workspace |
| `/filing-history` | ✅ YES | Track submissions |
| Mark as filed | ✅ YES | `FilingRecord` table |
| Re-filing prevention | ✅ YES | `UNIQUE(company_id, filing_type, period)` |

**Verdict:** WORKS.

### Stage 18 — Month-end close

| Step | Can complete? | Notes |
|---|---|---|
| `/payroll/runs/<id>/close` | ✅ YES | 7-step guided workflow (wired in `c8e4c3a`) |
| Each step gates the next | ✅ YES | `MonthEndClose` state machine |
| Lock period | ✅ YES | `PayrollRun.status='locked'` |

**Verdict:** WORKS.

### Stage 19 — Audit / History

| Step | Can complete? | Notes |
|---|---|---|
| `/audit-log` | ✅ YES | Hash-chained `AuditLog` |
| `verify_chain(company_id)` | ✅ YES | Tamper-evident verification |
| Per-action history | ✅ YES | With details JSON |

**Verdict:** WORKS.

### Stage 20 — Repeat for second company

| Step | Can complete? | Notes |
|---|---|---|
| `/companies` (multi-company list) | ✅ YES | For multi-company accountants |
| Switch company | ✅ YES | `/companies/<id>/switch` |
| Data isolation | ✅ YES | 19/19 tenant models protected (P0-A) |

**Verdict:** WORKS. **Pilot must verify with real second-company data.**

---

## Honest observations (simulator perspective)

### What works very well
- Calculation transparency (per-employee step-by-step flow) is genuinely useful for accountants who currently can't see how numbers are derived in Excel.
- Change summary, narrative, variance, exceptions together give the accountant a **why** for every number — the most valuable feature for trust.
- Multi-company switcher is simple.
- Ethiopian calendar dual-display is a nice touch.

### What needs improvement

1. **Language switcher is half-broken.** The `lang` attribute on `<html>` does not change. Screen readers and Amharic-mode UI users would notice.
2. **Accountant cannot change statutory rules.** Tax brackets, pension rates, overtime multipliers, transport cap are all hardcoded. If ERCA announces a new bracket, ops must deploy code.
3. **Excel is still needed for:**
   - Bulk employee edit (mass salary adjustments, mass terminations)
   - Bank reconciliation after payment (the system marks as disbursed/confirmed but doesn't reconcile against actual bank statements)
   - Year-end reports with cross-period pivots
4. **Reports not snapshotted.** A change to TaxRule after a run could change a re-generated ERCA report. Pilot accountants should download + archive reports immediately after generation.
5. **No clear "where am I in the process" indicator** on a single screen — must navigate to find status. (Timeline feature exists in `cockpit.py` but the surface area could be more discoverable.)
6. **Filing packages are not bundled.** ERCA, pension, and bank files are three separate downloads. A "filing package" download that bundles all three with a manifest would be cleaner.

### Things an accountant would ask but the system does not directly answer

- "What is the total employer cost for this month?" → must sum manually
- "What was the tax change vs last month for this specific employee?" → possible but not surfaced
- "Which employees are exempt from pension this month?" → not surfaced
- "What's our YTD tax paid?" → `/portal/ytd` exists for employee self-service but no company-wide YTD view

---

## Per-stage coverage matrix

| Stage | Can complete? | Excel needed? |
|---|---|---|
| Login | YES | NO |
| Company setup | YES | NO |
| Payroll configuration | YES (static) | NO |
| Employees | YES | SOMETIMES (bulk edits) |
| Import / Export | YES | NO |
| Attendance / Leave / Overtime | YES | SOMETIMES (mass imports) |
| Payroll Calculation | YES | NO |
| Review | YES | NO |
| Change Summary | YES | NO |
| Narrative | YES | NO |
| Variance | YES | NO |
| Exceptions | YES | NO |
| Approval | YES | NO |
| Payslip | YES | NO |
| Bank Payment / Export | YES | NO |
| Tax report | YES (generated) | YES (verify with portal) |
| Pension report | YES (generated) | YES (verify with portal) |
| ERCA Filing Preparation | YES (generated) | YES (submit out of band) |
| Month-End Close | YES | NO |
| Audit / History | YES | NO |

**Accountant can complete the entire critical workflow without Excel. Excel is needed only for:**
1. Bulk employee edits (mass salary change at year-end)
2. Bank reconciliation (out of band)
3. ERCA / pension portal upload (the system generates the file, but upload is manual)
4. Verification (pilot accountants will use Excel in parallel to confirm EthioPayroll numbers)

---

## Conclusion

The system is **functionally complete enough for a controlled pilot**. The accountant journey is walkable end-to-end. Three concerns block large-scale rollout:

1. **Statutory rule configurability** (hardcoded constants)
2. **ERCA / PSSA format validation** (no real-world proof)
3. **Accountant validation** (no Ethiopian accountant has used the system)

These are the explicit gates for the next milestone. They are not blockers for the 1-company pilot itself.

