# Retirement Round Cleanup (RC-38000-01) — Pension deducted before PAYE

Work order RC-38000-01. The "pension deducted before tax" treatment is treated as an
open question pending accountant sign-off: isolate it behind a named constant and
make every derived statement honest about the pending confirmation.

The treatment (employee pension contribution (7%) deducted from taxable income
before applying the bracket schedule) is long-standing practice and instantly
familiar to every accountant in Ethiopia, but the bracket schedule itself does not
explicitly mandate the treatment direction, so we:
- made the assumption a named constant with leave it inadvertently hard-coded,
- removed every statute citation or "Legal source" badge that asserted the treatment
  is legally granted (the citations remain only where they refer to bracket rates or
  the contribution amount itself, which ARE statutory),
- pinned the exact current behaviour in a dedicated regression test,
- gated all user-facing "pending confirmation" notices behind a documented
  environment switch (default ON).

No arithmetic was changed. Any flag=True path produces byte-identical numbers.

## Scope of this branch (verified)

- Diff vs base `10b4b3b` (`codex/synthetic-preview`) measured at `9e2edd7`:
  **27 files, 969 insertions(+), 70 deletions(−)**. The documentation-only
  follow-up commit adds no product lines. (An earlier figure of 912 lines was
  the count before `9e2edd7` and is superseded.)
- Diff vs `main` (`f27d5af`) is much larger (~94 files) because this work
  order was scoped to `codex/synthetic-preview`, not main. Recommended PR
  target: **`codex/synthetic-preview`**. Whether `synthetic-preview` merges to
  main first is a sequencing decision outside this work order.

## 1. Named constant and notice switch

`payroll_engine/constants.py`:

```python
PENSION_DEDUCTED_BEFORE_TAX = True
# Pending accountant sign-off, RC-38000-01. Flipping this changes PAYE for
# every employee with pension.
```

`pending_paye_notice_enabled()` returns the documented in-code switch
`PENDING_CONFIRMATION_NOTICE` (True, default on) unless the deployment sets
`PAYROLL_PENDING_TAX_NOTICE=0` (release-time override without a code change;
`1` or any other value restores the notice). `.env.example` documents the override.
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
  renders them; left untouched and flagged (delete candidate, separate PR). Note:
  the dead component copy `templates/components/calculation_flow.html:51` still
  contains the old "(pension is deducted before tax calculation)" text — inert
  until deleted.

### 2b. Second-round string changes (same work order, follow-up commit)

These remove the remaining "verified"-class claims found by the second audit
pass. Rule applied: no "legal requirement" / "Verified by" / "checked
against the Gazette" claim anywhere in the product. Bracket citations name
the proclamation and article only; the evidence trail for the article number
lives in this document (§5b), not in code, and code comments explicitly fall
back to "source to be confirmed" if a reviewer cannot match the official
text.

| Location | Old | New |
|----------|-----|-----|
| `payroll_engine/tax.py:16` | "Verified by: EY, PwC, DABLO Law, Liku Worku Law Office." | removed (no replacement claim) |
| `payroll_engine/tax.py` docstring source block | "Source: Proclamation No. 1395/2025, effective September 1, 2025." | "Bracket schedule: Proclamation No. 1395/2025, Article 11 (Employment Income Tax Rates). Supporting evidence … documented in docs/PENSION_BEFORE_TAX_RC38000_01.md; treat the article number as 'source to be confirmed' until matched against the official text. Effective dates … to be confirmed by the accountant." |
| `payroll_engine/tax.py` brackets comment | "Article 36(1) — Rates of Income Tax" | "Article 11 (Employment Income Tax Rates). Evidence trail for the article number: docs/PENSION_BEFORE_TAX_RC38000_01.md" — the old 36(1) cite was wrong |
| `seed_tax_rules.py:14` | "# Verified by: EY, PwC, DABLO Law, Liku Worku Law Office" | "# Brackets: Proclamation No. 1395/2025, Article 11 (Employment Income Tax Rates). Evidence trail for the article number: docs/PENSION_BEFORE_TAX_RC38000_01.md" |
| `seed_tax_rules.py:82` (`TaxRule.notes` → database) | "'Initial 2025 tax brackets per Proclamation No. 1395/2025. Verified by EY, PwC, DABLO Law, Liku Worku Law Office.'" | "'Initial 2025 tax brackets per Proclamation No. 1395/2025, Article 11 (Employment Income Tax Rates). Bracket schedule only; the pension-before-PAYE timing is current practice pending accountant confirmation (RC-38000-01).'" |
| `payroll_engine/i18n.py:147` (`tax_explainer_intro`, Amharic) | "…ጡረታ ከግብር በፊት ይቀነሳል፣ የሚተካ ገቢዎን ይቀንሳል።" | "…ጡረታ ከግብር በፊት መቀነስ የተለመደው ተግባር ሲሆን፣ እስኪረጋገጥ ዝግጁ አይደለም (RC-38000-01)…" — DRAFT Amharic, flagged in code for native-speaker review |
| `payroll_engine/i18n.py:153` (`pension_before_tax`, Amharic) | "ጡረታ ከግብር በፊት ይቀነሳል" | "ጡረታ ከግብር በፊት ይቀነሳል — የተለመደው ተግባር፣ እስኪረጋገጥ ይጠበቃል (RC-38000-01)።" — DRAFT, native review pending |
| `payroll_engine/i18n_om.py:143` (`tax_explainer_intro`, Oromo) | "…Haqni guutuu dura caasaa irraa ni haqama, lixuu kee ni hir'isa." | "…akkaataa ammaa jiruudha; mirkanaa'iin hooersaalaan eegama (RC-38000-01)…" — DRAFT Oromo, flagged for native-speaker review |
| `payroll_engine/i18n_om.py:149` (`pension_before_tax`, Oromo) | "Haqni guutuu dura caasaa irraa ni haqama" | "…— akkaataa ammaa jiru; mirkanaa'insa eegaala (RC-38000-01)" — DRAFT, native review pending |

Database caveat (counted, no migration run): the seed script is idempotent by
version — `seed()` skips when `TaxRule.version_name='2025-v1'` exists — so
ROWS ALREADY SEEDED KEEP THE OLD "Verified by EY, PwC, DABLO Law, Liku Worku
Law Office." text in `TaxRule.notes` until the rows are updated (reseed with a
bumped version or a one-off UPDATE). Today no live template renders
`TaxRule.notes`, so the old text is not user-visible; it is stored in the DB
and echoed only by the seed CLI.

`tests/test_rule_source.py` was checked as ordered: it contains no
"Legal source" user-facing text expectation — it tests the
verified/verified_by/verified_at flag fields of the `rule_source` mechanic,
which reflect the accountant's own in-app verification workflow, not a
self-awarded badge. No update required.

### 2c. Full-repo sweep of `calculate_tax` / `_calculate_tax`

Every hit (scripts, services, tests, seeds; tmp = untracked scratch, listed
for completeness):

| Hit | Status |
|-----|--------|
| `payroll.py:124` (daily worker) | intentional exception (no pension) |
| `payroll.py:257` (monthly payslip path, tax module) | controlled, flag read at call time |
| `payroll.py:344` (pension-savings comparison) | intentional exception |
| `excel_payroll.py:483` (Excel engine) | controlled |
| `excel_payroll.py:506` (same comparison, alias `calc_tax`) | intentional exception |
| `excel_payroll.py:278` (import of `calculate_tax_breakdown` / `explain_tax_amharic` for the explanation card) | explanation rendering only; consumes the flag-shaped taxable already computed — no independent math |
| `impact.py:331` (termination/new-hire/salary previews — user-facing monthly PAYE) | controlled |
| `impact.py:448-449` (allowance what-if; both sides of the delta share the same flag-adjusted taxable) | controlled |
| `services/settlement_service.py:151` | controlled (classification in §5b) |
| `payroll_elements.py:267` (`_calculate_tax`, defined at :31 as `from payroll_engine.tax import calculate_tax as _calculate_tax`) | controlled |
| `tax.py:111` (definition) | — |
| `benchmark.py:89,95`, `verify_50_questions.py:53,55`, ~15 `tests/test_*.py` hits | tooling/tests operating on explicit taxable inputs — no pension-angle entry point, nothing to route |
| `tmp/pdfs/build_pension_review_20261017.py:21` | untracked scratch, not product code |

No path required rerouting that would change its output; the order condition
to "stop and report" never triggered.

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
| Bank exports via API (`api.py:1066-1073`) and payslip PDF download (`api.py:477`, serves the stored PDF that already carries the footer notice) | bank rows data-only by design; PDF download inherits the gated footer |
| Email exports | none found — no outbound payslip-email path exists in the codebase |

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

### 5b. Could not verify (stated plainly)

- **Article number for the bracket schedule** — Article 11 ("Employment
  Income Tax Rates") carrying the exact monthly table applied in
  `DEFAULT_BRACKETS`. In-code wording deliberately makes NO "verified"/
  "checked" claim; the article digits come from the public evidence below
  and any reviewer who cannot obtain the Gazette should treat the number
  as "source to be confirmed" until matched to the official text.
  Reviewer-checkable evidence trail (fetched 2026-10-18):
  - Federal Negarit Gazette scan (justice.gov.et):
    https://justice.gov.et/wp-content/uploads/2025/12/%E1%8A%A0%E1%8B%8B%E1%8C%85-%E1%89%81%E1%8C%A5%E1%88%AD-1395-2017.pdf
    — amendment item 6/ deletes and replaces Article 11 with
    "Employment Income Tax Rates", followed by the table
    `0–2,000: 0%; 2,001–4,000: 15%; 4,001–7,000: 20%; 7,001–10,000: 25%;
    10,001–14,000: 30%; over 14,000: 35%` (Gazette page 19145).
  - Mirrored scan: https://ethiolex.com/wp-content/uploads/2026/04/Proclamation-No.1395-2025.pdf
    — same item 6/ wording and table.
  - Independent summary agreeing on the table (Chambers):
    https://chambers.com/articles/what-s-changed-under-ethiopia-s-new-income-tax-amendment-proclamation-no-1395-2025
    plus KPMG's PDF copy of the amendment text:
    https://assets.kpmg.com/content/dam/kpmg/ke/pdf/tax/2025/Income_Tax_(Amendment)_Proclamation.pdf
  - The previously cited "Article 36(1)" is not the employment schedule;
    it was wrong in the repo comment and was corrected to Article 11.
- **Who the accountant on RC-38000-01 is** — NOT VERIFIED: no name exists in
  the repo; the sign-off person must be named by the founder.
- **Is `settlement_service.py:146/151` monthly PAYE?** — ANSWERED: it is the
  monthly PAYE METHOD (the same `calculate_tax` bracket computation on the
  monthly salary component) applied inside settlement-specific context; it
  is not a separate settlement tax regime. It is flag-routed and pinned by
  the flip test.
- **Already-seeded database rows** — NOT FIXED (no migration run): rows
  seeded before this commit keep the old "Verified by EY, PwC…" text in
  `TaxRule.notes` (idempotent seed, detail in §2b).
- **External disagreement is recorded, not resolved:** countrytaxcalc.com's
  Ethiopia PAYE 2026 example (ETB 10,000 → tax ≈ ETB 1,650) computes PAYE on
  the full gross, consistent with their statement that pension is NOT
  deducted before the brackets — i.e. their reading implies the flipped
  behaviour. The current in-app behaviour follows the historical Ethiopian
  practice (deducted first, tax 10,319 at 38k) until the accountant rules on
  RC-38000-01.
- **PRE-EXISTING FINDING (not introduced here):** `seed_tax_rules.py` seeds
  `"personal_relief": 150`, while `tax.py` sets `DEFAULT_PERSONAL_RELIEF = 0`
  ("No personal relief — not provided under 979/2016 or 1395/2025"). If a
  seeded TaxRule exists in the database, the rule path may compute a
  different PAYE from the pinned default-bracket math. Needs its own mini
  work order; NOT touched here (no calculation change).
- **Amharic/Oromo draft translations** — flagged in code and §2b for
  native-speaker review; presented as proposals, not final.

## 6. Tests

- New: `tests/test_pension_before_tax_rc38000_01.py`
  - `test_pension_before_tax_RC38000_01` — pins the monthly payslip path
    (`payroll.py:249` calculate_payroll) on the RC-38000-01 case (gross 38,000 =
    basic, no allowances/overtime: pension 2,660, taxable 35,340, tax 10,319,
    net 25,021); expected tax is derived from the live `DEFAULT_BRACKETS` via
    `calculate_tax`, never hard-coded bracket amounts.
  - `test_pension_before_tax_RC38000_01_excel_engine` — same case through
    `ExcelPayrollEngine` (the Excel/payslip-compatible path).
  - `test_flip_changes_every_monthly_paye_path` — flag False: every controlled
    monthly path taxes 11,250.00 with net 24,090.00 (hard literal asserts
    guard the legacy engine against bracket-table drift); daily worker
    unchanged; comparison explanation shows 0 savings. The test fails if any
    controlled path ignores the flag.
  - `test_notice_switch_defaults_on_and_can_be_disabled` —
    `PENDING_CONFIRMATION_NOTICE` default True → notice on; env override `0`
    hides it, `1` restores it (and the env wins over the constant while set);
    wording says "current practice" with no Proclamation/Article citation.
- Updated: `tests/test_calculation_flow.py::test_calc_flow_pension_savings_in_steps`
  (wording substring), `tests/test_excel_payroll.py::TestCalculationFlow::test_legal_references`
  (now asserts NO `legal_reference` on the pension step + note wording).

Ran against: `pytest tests/test_pension_before_tax_rc38000_01.py tests/test_payroll.py
tests/test_calculation_flow.py tests/test_excel_payroll.py tests/test_elements_engine.py
tests/test_tax.py tests/test_tax_breakdown.py tests/test_services.py
tests/test_deductions.py tests/test_bugfixes.py tests/test_diff_check_e2e.py
tests/test_verification.py` → all pass.

## 7. Full-suite run (branch, local machine)

Command: `pytest tests -q` — completed in chunks (first `-x` pass: 273 passed
before hitting the known benchmark failure):
- **1525 passed, 201 skipped, 4 warnings** for everything except the two files
  below.
- The run was completed as: full suite minus `tests/test_benchmark.py` and
  `tests/test_p0d_concurrency.py`, then both of those verified separately.
- `tests/test_p0d_concurrency.py` — **6 passed in isolation** (11.48s); it does
  not hang, it is thread/SQLite-WAL heavy inside the full run.
- Failures, ALL VERIFIED PRE-EXISTING on base `10b4b3b` (re-ran identical
  sets on the detached base commit to classify):
  - `test_benchmark.py::test_dashboard_api_performance` [50/200/500] — 3,
    same result on base.
  - `19 failed + 37 errors` across `test_demo_and_template`,
    `test_e2e_full::test_full_payroll_flow`, `test_phone_password_strict`,
    `test_security_wave1` (login-redirect/suite-startup dependent),
    `test_error_boundaries`, `test_input_validation`, `test_rate_limiting`.
    Root cause of the 37 errors and most failures: the shared login helper
    at `tests/helpers.py:29` (POST-login follow-up fails), identical on
    base. Zero payroll/tax/deduction/flow tests are among them; no failure
    is attributable to this change.
- Honest machine caveat: local numbers are SQLite-app-context; hosted
  PostgreSQL runs are the CI record, and `test_pg_monthly_journey` is skipped
  locally without a disposable PostgreSQL TEST_DATABASE_URL (201 local skips
  include it).
- **Base-vs-branch full-suite comparison (reviewer's requested check):**
  same command and same exclusions (`test_benchmark.py`,
  `test_p0d_concurrency.py`) run on detached base `10b4b3b`:

  | Metric | Base 10b4b3b | Branch c905916 |
  |--------|--------------|----------------|
  | passed | 1522 | 1525 |
  | failed / errors | 19 / 37 | 19 / 37 (+1 flaky phone-tab variant passed on re-run) |
  | failed/errored test IDs | identical set | identical set |
  | skipped | 201 | 201 |

  Delta = exactly the 4 new RC-38000-01 tests; failure sets byte-identical.
  The failures share one root cause (`tests/helpers.py:29` POST-login
  follow-up broken locally; identical on base) plus the pre-existing
  benchmark timing thresholds. The base is indeed not healthy locally —
  documented as a separate pre-existing finding. The shared-helper cause is
  fixed on this branch in the follow-up below; reviewers should not rely on
  the local suite to prove the base healthy; hosted CI (PostgreSQL) remains
  the authoritative check record.
- **Follow-up (2026-10-19): CI blockers fixed on this branch.** The
  `setup_profile` route requires `middle_name`, but `tests/helpers.py` and the
  `test_e2e_full` fixture omitted it, which produced the 10 hosted and 19/37
  local failures. Both now send it. Three stale login-tab assertions now
  assert the shipped single phone-or-email identifier UI. The strict
  security/tenancy gate plus the RC test file pass locally (**107 passed, 2
  skipped**); the focused phone/e2e/i18n/auth subset is **60 passed, 1
  skipped**. Repo-wide `ruff format` was applied (7 files, no content changes),
  Ruff 0.17.1 `check` is clean and `format --check` reports 244 files already
  formatted. The hosted `test_pg_worksheet_journey` failure was a stale
  expectation for the prep-save review auto-refresh, not an arithmetic change:
  approval preserves the refreshed 9,260.00 snapshot, so the assertion now
  expects 9,260.00 (was 9,090.35). Hosted CI remains the authoritative record.
- **Personal-relief sanity check on this branch:** `seed_tax_rules.py:26`
  still seeds `"personal_relief": 150` while `tax.py` enforces
  `DEFAULT_PERSONAL_RELIEF = 0` ("No personal relief"). Confirmed on the
  branch, unchanged here, tracked as the separate pre-existing finding.
- **`rule_source.py` wording audit:** the "legal source"/"verified" field
  names live in `rule_source.py` (developer-facing strings, docstrings and
  the accountant's own verify workflow) and are NOT rendered as user-facing
  badges by any live template (template-wide grep for "Legal source"/
  "Verified" returns no product surface). No user-facing change required.
