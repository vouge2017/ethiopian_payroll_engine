# Retirement Round Cleanup (RC-38000-01) — Pension deducted before PAYE

Work order RC-38000-01. User-directed task: isolate the "pension deducted before tax"
assumption behind a named constant and make every derived statement honest and honest
about the pending accountant confirmation.

The treatment (employee pension contribution (7%) deducted from taxable income before
applying the racket schedule) is long-standing practice and instantly familiar to
every accountant in Ethiopia, but the 1395/2025 racket schedule itself does not
explicitly mandate the treatment direction, so we:
- made the assumption a named constant with leave it inadvertently hard-coded,
- removed every statute citation or "Legal source" badge that asserted the treatment
  is legally granted (the citations remain only where they refer to bracket rates or
  the contribution amount itself, which ARE statutory),
- pinned the exact current behaviour in a dedicated regression test,
- gated all user-facing "pending confirmation" notices behind a documented
  environment switch (default ON).

No arithmetic was changed. Any flag=True path produces byte-identical numbers.

## 1. Named constant and notice switch

`payroll_engine/constants.py`:

```python
PENSION_DEDUCTED_BEFORE_TAX = True
# Pending accountant sign-off, RC-38000-01. Flipping this changes PAYE for
# every employee with pension.
```

`pending_paye_notice_enabled()` reads `PAYROLL_PENDING_TAX_NOTICE` (default `1` /
on; `0` turns every in-app / PDF notice off). `.env.example` documents the switch.
`PENDING_PAYE_NOTICE_TEXT` is the one shared notice string:
"PAYE note: employee pension contribution is deducted from taxable pay by current
practice; the tax law article confirming this treatment is pending accountant
confirmation (RC-38000-01)."

Every calculation site reads the constant at call time
(`from payroll_engine import constants as _constants` +
`_constants.PENSION_DEDUCTED_BEFORE_TAX`) so tests can monkeypatch it and a future
fix can flip it in one place.

## 2. List 1 — every call site on the default brackets

Original-era line numbers. The test `tests/test_pension_before_tax_rc38000_01.py::test_flip_changes_all_monthly_paths`
proves each of these changes result when the flag is False on a 38,000/2,000-ETB
employee (tax 10,319 → 10,350), and that the daily-worker path is NOT affected.

| # | Call site | Now reads flag | Notes |
|---|-----------|----------------|-------|
| 1 | `payroll_engine/payroll.py` ~249 — `calculate_payroll` (monthly/legacy engine) | yes | main entry自查 also confirmed Excel engine numbers tie to it in tests |
| 2 | `payroll_engine/excel_payroll.py` ~482 — `ExcelPayrollEngine.calculate_employee` step 7 | yes | also drives all exporters (CSV/XLSX/PDF) built from engine steps |
| 3 | `payroll_engine/payroll_elements.py` ~267 — `calculate_payroll_from_assignments` (worksheet/engine path) | yes | NOT in the supplied list — found and wired |
| 4 | `payroll_engine/services/settlement_service.py` ~147 — `calculate_settlement` | yes | settlement taxable basis |
| 5 | `payroll_engine/impact.py` ~329 — `preview_termination` | yes | preview and the payable computation both use the same tax( taxable ) call |
| 6 | `payroll_engine/impact.py` ~442 onwards — legacy allowance what-if | yes | NOT in the supplied list; logic derived from the same `calculate_tax` |
| 7 | `payroll_engine/payroll.py` ~121 — daily-worker path | NO (intentional) | daily workers earn no pension; taxable stays gross. Leaves documented in comment. |
| 8 | `payroll_engine/payroll.py` ~340 — pension-savings comparison in `generate_calculation_flow` | NO (intentional) | shows what the accountant would pay without the treatment; when flag becomes False the step correctly shows 0 savings |
| 9 | `payroll_engine/excel_payroll.py` ~506 — the same comparison inside `ExcelPayrollEngine` | NO (intentional) | same rationale |

`models.py:1656` (`TaxRule.pension_deduction_order` JSON property) remains defined
but unwired — no calculation path reads it. Left as-is; it is the custom-rules
retention knob for a future PR.

No other call sites of `calculate_tax` / `calc_tax` exist (grep-checked).

## 3. List 2 — every user-facing string changed

Rule: wherever a phrase asserted the pension-before-tax treatment has a statutory
basis, the phrase now says it is current practice pending accountant confirmation
(RC-38000-01), and no "Legal source"/"Verified" badge may suggest otherwise.

| Location | Old | New |
|----------|-----|-----|
| `payroll.py` docstring | "tax using 2025 brackets" phrasing attributing the pension-first scheduling to the law | "pension reduces taxable income (current practice, RC-38000-01)" |
| `payroll.py` pension step note (step 3) | "Deducted BEFORE tax (legal requirement)" | "Deducted before PAYE — current practice, pending accountant confirmation (RC-38000-01)" |
| `payroll.py` flow savings note | "You save this much because employee pension is deducted before tax (this is a legal deduction that reduces your tax. Without this rule, tax would be ETB X" | "You save this much because pension is deducted before PAYE — current practice, pending accountant confirmation (RC-38000-01). Without it, tax would be ETB X" |
| `payroll.py` summary suffix | "Pension deducted before tax as required by law." | "Pension deducted before PAYE (current practice RC-38000-01, pending confirmation)." |
| `excel_payroll.py` pension step note | "Deducted BEFORE tax per Proclamation 1268/2022 Art. 10" | "Deducted before PAYE — current practice, pending accountant confirmation (RC-38000-01)" |
| `excel_payroll.py` pension step `legal_reference` | `'Proclamation No. 1268/2022, Article 10'` | removed entirely |
| `excel_payroll.py` savings note | "…because pension is deducted before tax (legal requirement)…" | "…deducted before PAYE — current practice, pending accountant confirmation (RC-38000-01)…" |
| `tax.py` module docstring | "Pension: employee pension (7%) deducted BEFORE tax as required by law" | "Pension: deducted before tax (current practice, pending accountant confirmation RC-38000-01)" |
| `diff_check.py` `_explain_tax` | "Pension treated as deducted before tax (statutory treatment) → taxable ... (law)" | "Pension is deducted from taxable pay before the bracket schedule under current practice, pending accountant confirmation (RC-38000-01) → taxable ..." |
| `diff_check.py` Tax (PAYE) explanation law field | bracket wording only | "Brackets: Proclamation 1395/2025, Art. 11 — pension-first timing: current practice, pending confirmation (RC-38000-01)" |
| `help_bp.py` (3 answers) | "Deducted BEFORE tax (legal requirement)" wording | updated with pending confirmation wording; statute reference kept only on contribution rate (Art. 12) which IS statutory |
| `verification_bp.py` PAYE-method step | "What to check: Pension deducted before tax per proclamation" | "confirm the pension-before-PAYE timing is intended practice (RC-38000-01)" |
| `templates/diff/upload.html` (live tree) | "Deductions include employee pension before tax (legal requirement)" badge examples + prose | pending-confirmation wording |
| `templates/payroll_results.html` pension line + new banner | "(deducted before tax as required by law)" | pending wording; new notice banner (gated) |
| `templates/_calculation_flow.html` tax step tooltip | "Tax: calculated on salary minus pension (statutory)" | "Tax: calculated on taxable income. Pension-first timing is current practice, pending confirmation (RC-38000-01)." |
| `templates/payroll_confirm.html` | — | gated notice banner + tax row tooltip updated |
| `templates/employee_portal/payslip_detail.html` | footer "Calculated according to Proclamation No. 1268/2022 … pension_pay taxable income" | footer now scoped to brackets/contributions; gated banner added at top |
| `templates/settlement_detail.html` | — | gated notice banner added |
| `pdf.py` footer | generic footer | adds the pending notice line when `pending_paye_notice_enabled()` (gated) |
| `__init__.py` | — | Jinja globals `pending_paye_notice()` / `pending_paye_notice_text` registered |

Strings deliberately NOT changed:
- Contribution-rate citations (7% employee / 11% employer, Proclamation 1268/2022
  Art. 12) — the contribution amount IS statutory; only the payroll-tax timing is
  not, and that is what we rescoped.
- Bracket citations (Proclamation 1395/2025 Art. 11 rates) — kept where scoped to
  bracket amounts/tax computation, which are statutory.
- `verification_summary.html` heading "All Calculations Verified" — reflects the
  accountant's own recorded check state on the self-verification page, not a
  system-claimed legal badge for the PAYE timing. Left untouched (flagged here for
  reviewer attention).
- Legacy/dead template copies (root `templates/diff/*.html`,
  `payroll_engine/templates/diff/diff_upload.html` / `diff_results.html`) — no route
  renders them; left untouched and flagged (delete candidate, separate PR).

## 4. List 3 — every visible output path and its notice status

Legislative paths that WILL show the pending notice (default switch ON):

| Output path | Notice |
|-------------|--------|
| Web results screen (`templates/payroll_results.html`) | banner + pension row note |
| Confirm/payroll_run screen (`templates/payroll_confirm.html`) | banner + tax tooltip |
| Calculation-flow step listing (`templates/_calculation_flow.html`) | tax step tooltip |
| Employee self-service payslip page (`templates/employee_portal/payslip_detail.html`) | banner + footer |
| Settlement detail page (`templates/settlement_detail.html`) | banner |
| Generated PDF payslip (`pdf.py`) | footer notice line |
| Diff upload/results screens (`templates/diff/upload.html`, `results.html` via `_explain_tax`) | wording in explanation text |
| Bot/help answers (`help_bp.py`) and verification walkthrough (`verification_bp.py`) | wording |

Official exchange formats that do NOT carry the notice (deliberate):

| Output path | Reason |
|-------------|--------|
| Bank transfer CSV/XLSX (`bank_file.py`) | strict portal-schema data rows; the notice is shown on the confirm screen the file is exported from |
| ERCA filing XLSX (`reports.py::generate_erca_report`) | official tax-authority grid with fixed column set; adding an internal caveat row could break portal parsing |

Training/demo/sandbox runs (synthetic preview data) also render the same templates,
so they carry the same gate.

## 5. Honest limitation list

- **The tax treatment itself is NOT Changed.** With the default flag every path
  produces exactly the historical taxable-income and PAYE numbers for every
  employee with a basic salary (test-pinned on legacy + Excel + worksheet +
  settlement + impact paths).
- **Ruff was unavailable on this machine.** Lint was run by the hosted CI lint job
  message (file set listed at top); locally only `py_compile` could run. Requires
  follow-up if any lint finding occurs.
- **Wording only covers ENGINE paths that run the flag.** The daily-worker path
  intentionally still taxes on gross pay (no pension), and the
  pension-savings comparison steps intentionally show what the accountant would
  pay without the treatment — both are part of the same business rule, not
  secondary bugs.
- **The `TaxRule.pension_deduction_order` property is unwired.** Rules-json flag
  (models.py:1656) is unused by all engines. Keeping it is fine; wiring it is a
  future PR.
- **Unverified items** (stated plainly, no coverage invented):
  - mobile app (out-of-repo worktree) — not touched, per repo policy.
  - the "0 savings vs wrong savings" wording nuance for the comparison steps when
    a future PR flips the flag — behaviour verified by test, exact UX copy for
    that future state not yet decided.
- **Test changes:** two pre-existing tests were updated to the new honest wording
  (substring assertions); the numeric expectations were NOT modified.

## 6. Tests

- New: `tests/test_pension_before_tax_rc38000_01.py`
  - `test_pension_before_tax_default_pin_legacy_and_excel` — pins legacy engine and
    Excel engine on the 38,000/2,000 textbook employee (pension 2,660, taxable
    35,340, tax 10,319, net 25,021).
  - `test_flip_changes_all_monthly_paths_and_not_daily_worker` — flag False makes
    every monthly path tax 10,350 with taxable 36,660; daily worker unchanged;
    comparison steps show 0 savings.
  - `test_pending_notice_switch` — default env → banner text present; `=0` → no
    banner; wording says "current practice".
  - `test_excel_pension_step_has_no_statute_citation` — Excel pension step carries
    no `legal_reference`.
- Updated: `tests/test_calculation_flow.py::test_calc_flow_pension_savings_in_steps`
  (wording substring), `tests/test_excel_payroll.py::TestCalculationFlow::test_legal_references`
  (now asserts NO `legal_reference` on the pension step + note wording).

Ran against: `pytest tests/test_pension_before_tax_rc38000_01.py tests/test_payroll.py
tests/test_calculation_flow.py tests/test_excel_payroll.py tests/test_elements_engine.py
tests/test_tax.py tests/test_tax_breakdown.py tests/test_services.py
tests/test_deductions.py tests/test_bugfixes.py tests/test_diff_check_e2e.py
tests/test_verification.py` → all pass.
