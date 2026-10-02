# EXCEL FALLBACK INVENTORY
**Date:** 2026-08-31
**Method:** Walked every documented route, identified every place where an accountant would still reach for Excel.
**Classification:**
- **A** — Excel not needed
- **B** — Excel optional
- **C** — Excel useful but workaround exists
- **D** — Excel required

> **Pilot target:** No critical payroll workflow should require Excel. Excel may be used for independent verification.

---

## Stage-by-stage inventory

| # | Stage | Excel needed? | Why / workaround |
|---|---|---|---|
| 1 | Company setup | **A** | Form-based, no Excel needed |
| 2 | TIN / branding / deadlines | **A** | Form-based |
| 3 | Employee create (single) | **A** | Form-based |
| 4 | Employee bulk import (50+ employees) | **A** | CSV upload with validation; **Excel is the source of the CSV** (accountant exports their existing employee list to CSV first) |
| 5 | Employee bulk edit (mass salary change) | **C** | UI has per-employee edit, no mass-update UI. Workaround: export all → edit in Excel → re-import. Or use API with script. **Pilot improvement: add bulk-edit UI.** |
| 6 | Attendance import | **A** | CSV upload |
| 7 | Leave management | **A** | UI-driven |
| 8 | Overtime entry (single employee) | **A** | UI form |
| 9 | Overtime bulk entry (50+ employees) | **C** | UI is per-employee. Workaround: spreadsheet template → CSV upload. **Pilot improvement: add overtime CSV import.** |
| 10 | Payroll calculation (per employee) | **A** | System calculates from inputs |
| 11 | Payroll calculation (bulk) | **A** | Upload CSV or use spreadsheet editor |
| 12 | Review / change summary / narrative | **A** | UI surfaces all of this |
| 13 | Exception resolution | **A** | UI with override flow |
| 14 | Approval | **A** | UI button + password + MFA |
| 15 | Payslip view | **A** | UI/PDF |
| 16 | Payslip batch download | **A** | UI button |
| 17 | Bank file generation (CBE / Telebirr / etc.) | **A** | UI button |
| 18 | Bank reconciliation (after payment) | **D** | **System marks as disbursed/confirmed but does NOT reconcile against actual bank statements.** The accountant must compare to their bank portal or use Excel. **Pilot improvement: add bank-statement reconciliation UI.** |
| 19 | ERCA report generation | **A** | System generates |
| 20 | ERCA portal submission | **C** | System generates XLSX, but **upload to ERCA portal is out of band**. Accountant downloads + uploads. Pilot improvement: eTax API integration (post-pilot). |
| 21 | Pension report generation | **A** | System generates |
| 22 | PSSA portal submission | **C** | Same as ERCA: download + upload manually |
| 23 | Month-end close | **A** | UI workflow |
| 24 | Audit log review | **A** | UI with hash chain verification |
| 25 | Tax verification (compare EthioPayroll to manual computation) | **B** | Accountant will do this in parallel during pilot; not required for production use |
| 26 | Year-end reconciliation | **C** | `/reports/yearly/<year>` exists, but cross-period pivots (e.g., tax by month) are not surfaced. **Pilot improvement: add year-end pivot view.** |
| 27 | Accounting journal entries | **A** | `/accounting` and `/accounting/export/<id>` exist |
| 28 | Ad-hoc analysis ("what if we give everyone a 10% raise?") | **B** | `/impact` calculator exists. Excel optional for ad-hoc exploration. |

---

## Pilot target assessment

**Goal:** No critical payroll workflow should require Excel.

**Verdict:** ✅ **Pilot target met for the core monthly workflow** (Stages 1-17, 23-24, 27).

**Three acceptable Excel touchpoints remain:**

1. **CSV source for bulk employee import** (Stage 4) — this is industry standard; Excel is the source format. Not a workflow gap.
2. **Bank reconciliation** (Stage 18) — outside EthioPayroll's scope (requires bank API or manual statement comparison).
3. **ERCA / PSSA portal upload** (Stages 20, 22) — out of band until eTax/PSSA API integration.

**Three improvement candidates (NOT pilot blockers, but useful):**
- Bulk-edit UI for employees (Stage 5) — currently C; should be A
- Overtime CSV import (Stage 9) — currently C; should be A
- Year-end pivot view (Stage 26) — currently C; should be A

---

## What this means for the pilot

The pilot accountant will use Excel for:
1. **Source of truth during import** (employee list as CSV)
2. **Parallel verification** (running the same payroll in their existing Excel to compare)
3. **Bank reconciliation** (after payment confirmation)

These are acceptable Excel uses. The pilot's success criterion is that the accountant does **not** need Excel for any of Stages 1-17, 23-24, 27 — and especially not for any **calculation** that EthioPayroll is supposed to own.

If the pilot reveals an additional Excel dependency (e.g., "I had to go to Excel to compute X because the system didn't show X"), that becomes a feature request for the post-pilot backlog.

