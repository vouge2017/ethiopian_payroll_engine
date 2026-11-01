# PLAN.md — EthioPayroll single source of truth

This file is the one plan for the project. If another document disagrees with
this file, this file wins. Keep it short. Update it at the end of every session.

---

## 1. Status

### Holiday calendar corrected to Proc. 1334/2024 (branch `fix/holiday-calendar-1334-2024`)

- State: implemented, 13/13 tests pass, PR #46 open. CI: lint ✅,
  Migration Tests ✅, GitGuardian ✅, test-postgres passing (fixed `down_revision`
  from `d1e2f3a4b5c6` to `a4b5c6d7e8f9` — main head).
- What: Patriots' Victory Day → May 5 (Art. 4); May 28 "Downfall of the Dergue" abolished;
  Dec 9 & Feb 20 are memorial days only (Art. 5). Old seed wrongly put Patriots' Victory Day
  AND Downfall of the Dergue both on May 28 of 2025 and 2026.
- `payroll_engine/holidays.py` rewritten: `national_holidays(year)` builds 9 closed holidays;
  `orthodox_easter()` via Julian computus; 2027 September shift; `add_national_holiday()`
  for lunar dates (Mawlid/Eid al-Fitr/Eid al-Adha) announced per official gazette.
- Migration `h1334c2024a1`: delete wrong May 28 rows, seed corrected 2025-2027 (idempotent).
- Cross-checked with `holidays` Python package — all dates match. ruff clean.
- PostgreSQL migration proof: CI only (no local PG available).

### Adviser pack second review (2026-10-30)

- Second review found two source-register links incorrectly pointed to Labour Proclamation 1156/2019; corrected them to the official Regulation 410/2017 and Pension Proclamation 1268/2022 Gazette PDFs.
- Corrected the Directive 1085/2025 date attribution: its actual Justice record displays 25 Ginbot 2017 E.C. (a date in June 2025), consistent at month level with the June 2025 PDF date. The 10 March 2026 date belongs to a separate explanatory-note record. Article 74 effective date remains unverified pending registration/upload evidence.
- Rechecked official Justice records and direct Gazette links. No payroll code changed; documentation validation only; no test suite run.

### Adviser pack critical corrections (2026-10-30)

- Updated the three legal adviser-pack documents after critical source review.
- Corrected Proc. 1434/2026 references to Article 2 items 4 and 12 and Article 3; separated assessment limitation from monthly PAYE return amendment.
- Recorded the June 2025 directive PDF date and 10 March 2026 Justice explanatory-record date; Directive 1085/2025 effective date remains unverified because Art. 74 registration/upload evidence was not found.
- Added the official MoR Proc. 979 technical note as explanatory evidence; exact transport/per diem formula and operative directive remain provisional/unconfirmed.
- No payroll code, calculations, rates, thresholds, migrations or production behavior changed. Documentation checks only; no test suite run. No legal approval or adviser acceptance is claimed.

### Final legal adviser pack (2026-10-30)

- Created `ETHIOPAYROLL_LEGAL_ADVISER_PACK_FINAL.md`,
  `LEGAL_SOURCE_VERIFICATION_REGISTER.md`, and
  `LEGAL_RULE_IMPLEMENTATION_STATUS.md` for the five agreed topics.
- Verified pension multiple-employer provision is Proclamation 1268/2022
  Article 52(2), not Article 53(2); added the official 1085/2025 directive.
  The 45-day commencement interpretation remains open.
- Compared original Proc. 983/2016 Article 29 with Proc. 1434/2026: Article
  28 limitation period amended; Article 29 is not expressly changed in the
  amendment reviewed; its 120-day decision period appears textually unchanged.
  The official current monthly PAYE operational guidance was not located and
  is labelled `OFFICIAL GUIDANCE UNVERIFIED`. The original Proc. 983 text was
  checked from a non-government copy; obtain an official copy before legal
  reliance.
- No payroll code, calculations, rates, thresholds, migrations or production
  behavior changed. No tests run for this documentation-only task. No claim
  that all five topics are legally resolved or adviser-accepted.

### Adviser pack review (2026-10-30)

- Branch `docs/adviser-pack-evidence`, based on merged report revision
  `6f041d78`: research-only review in `docs/decisions/2026-10-25-payroll-rules.md`.
  Five topics have source references, examples and unanswered adviser questions.
- Located the Ministry of Justice's Amharic exempt-income directive: Article 6
  appears to use the higher per-diem amount. Instrument identity, amendments,
  interpretation and applicability require qualified review. Corrected the
  assessment-revision citation to renumbered Article 96(2). No payroll code or
  statutory calculation changed; no practitioner acceptance is claimed.
- Validation: adviser-pack structure/citation assertions and `git diff --check`
  passed. With Python 3.12, SQLite, UTF-8 and `python -m pytest tests -q
  --capture=sys -p no:cacheprovider --tb=short`: **2000 passed, 235 skipped,
  66 warnings in 1401.05s (0:23:21)**. The prior runner timed out on
  `test_assignment_import.py`; a separate rerun passed: `28 passed, 4 warnings
  in 77.06s (0:01:17)`. PostgreSQL tests were skipped; no deployment or external
  review. Test base SHA `6f041d78e30848ce4e820604236bed75c035b242`; the slice
  changes documentation only.

### Report allowance breakdown correction (PR #44 merged)

- PR #44 was merged into `main` on 2026-10-27 as `6f041d78e30848ce4e820604236bed75c035b242`, based on `cc8815e` (PR #42). Implementation commits: `bf27760` and `0f26287`.
- XLSX/CSV reports read approved and locked run-item tax settings and saved
  payslip earning lines. Missing snapshots and unreconstructible
  percentage-based exemptions stay blank with an accountant-review note;
  migration-backfilled snapshots get a distinct warning because they may not
  reflect approval-time settings. Reports do not use today's catalog values.
- PostgreSQL report/snapshot/version tests: `13 passed, 38 warnings in
  57.96s`. Full suite: `2000 passed, 235 skipped, 66 warnings in 2596.63s
  (0:43:16)`, exit 0, `python -m pytest tests -q --capture=sys
  -p no:cacheprovider --tb=short`. PostgreSQL used an isolated UTF-8 PG 16
  test database; no production data was accessed.
- State: implemented, locally and hosted tested, and merged. Deployment and
  practitioner acceptance remain pending.

- Committed and pushed as `3ed083542e183d832db566f4f92c4a79ade574dc` on
  `fix/report-unknown-breakdowns`; exact-commit SQLite tests 13 passed and
  PostgreSQL report tests 4 passed. No hosted checks were listed on first
  lookup; no PR, merge, deployment or practitioner acceptance.
- Earlier revision `3ed0835`, based on `ba54f90`, was in isolated
  `report-review-worktree`; the original checkout contains separate holiday
  work and retains the original uncommitted report changes. PR #31
  (`fix/reports-frozen-values`) is already merged on main; its legacy snapshot
  gap remains. The default PAYE report previously described all non-basic,
  non-overtime earnings as transport and taxable transport, including housing.
- Earlier revision: left the three unverified allowance breakdown columns
  blank in XLSX and CSV, with a review-before-filing note. Approved taxable
  totals and withheld tax remain unchanged. This does not create a verified
  filing format or reconstruct missing historical classifications.
- Earlier revision's default and custom report columns left unknown per-item tax treatment and
  missing legacy snapshots blank and display a review warning; current catalog
  settings are not used to reconstruct historical tax treatment.
- Focused SQLite tests: `13 passed, 4 warnings in 15.58s`. Full suite:
  `1908 passed, 223 skipped, 45 warnings in 4623.35s (1:17:03)`; exit 0,
  `python -m pytest tests -q --capture=sys -p no:cacheprovider --tb=short`.
  The earlier per-file suite returned:
  `TOTAL: 1824 passed, 0 failed, 2 errors, 223 skipped` (exit 1):
  `test_exceptions.py` and `test_pay_item_settings.py` exceeded the runner's
  120-second process limit. Standalone reruns exited 0: respectively
  `30 passed, 4 warnings in 3.25s` and `52 passed, 4 warnings in 331.11s`.
  These reruns do not change the full-suite result.
  Isolated source preflight passed (one head `d1e2f3a4b5c6`); fresh disposable
  PostgreSQL 16 UTF-8 database migrated to that head, and report queries plus
  the report regression gave `4 passed, 20 warnings in 9.71s`. A second
  synthetic database upgraded from `9b4e6d2a8c13` with a locked payslip;
  count and gross, tax, pension and net sums were unchanged at head. Exact
  committed SHA, hosted checks and practitioner acceptance remain open.
- Earlier revision left custom `_pay_item:...:taxable` fields blank; this has
  been superseded by the snapshot-aware implementation described above.

### Which docs to trust

- **PLAN.md (this file) is the truth** for status, the current task and the
  queue.
- `AGENTS.md` is the working rules for AI sessions.
- `README.md` tells you how to run the app. `SECURITY.md` and `LICENSE` stay
  as they are.
- Do **not** treat the other ~130 Markdown files in the repo root (audits,
  session summaries, PRDs, catalogues, scorecards, `STATUS.md`, `TODO.md`,
  `ROADMAP.md`, `LATER.md`, `OPEN_QUESTIONS.md`, `docs/WORK_ORDERS.md`, …) as
  current. They are history. Many of them disagree with each other and with the code.
  Moving them to `docs/archive/` is Next item 10. Until then, read them only when
  you need history.

### Where the code is

- Baseline: `origin/main` @ `c65aaa0` (c65aaa072cb9243ef61722afcba498e41fcba47f,
  2026-10-25, "Merge pull request #32 from vouge2017/fix/paye-gross-income").
- This plan was first written on branch `docs/plan-md`, cut from `f335bf2`
  (PR #29); the audit test numbers below are from that SHA.
- Production (per the 2026-10-21 notes in STATUS.md, not re-checked here): one Render web service with a Neon Free Postgres. There is **no** Redis and **no** worker
  service. `render.yaml` still describes a Render Postgres + Redis + worker +
  cron, so it does not match reality.
- 78 Alembic migrations with a single head, `f4a5b6c7d8f3` (on main @ `c65aaa0`; `fix/settlement-taxation` adds `f4a5b6c7d8f4`, `f4a5b6c7d8f5` and `f4a5b6c7d8f6`).

### Tests (2026-10-25, this audit)

- How they were run: Python 3.12.15 in a fresh venv, using `requirements.txt` +
  `requirements-test.txt` (not `requirements-lock.txt`), SQLite. Each test file
  ran in its own process, the same way `run_tests.py` does it. 165 test files.
- Result: **1705 passed, 0 failed, 0 errors, 205 skipped** (about 13 min wall
  time, 2 CPUs).
- The 205 skips are almost all PostgreSQL-only tests (`test_pg_*`, migration
  chain). They need a disposable `TEST_DATABASE_URL`. No Postgres was available
  in this sandbox, so **none of the PostgreSQL proofs were run in this audit**.
  CI has a `test-postgres` job that is meant to run them.
- A plain `pytest` from the repo root fails to collect 3 files
  (`ModuleNotFoundError: payroll_engine`). Use `python -m pytest` or
  `python3 run_tests.py`.

### What works (code read + tests green)

- PAYE brackets match Proc. 1395/2025 (0 / 15 / 20 / 25 / 30 / 35 % at 2,000 /
  4,000 / 7,000 / 10,000 / 14,000) (`payroll_engine/tax.py:45-52`).
- Pension is 7 % employee and 11 % employer, on basic salary only
  (`payroll_engine/pension.py:25-26`).
- Overtime: 1.5 / 1.75 / 2.0 / 2.5 ×, with hourly rate = basic / 208
  (`payroll_engine/overtime.py:30-44`).
- Transport exemption is the lower of ETB 2,200, 25 % of basic, or the amount
  actually paid, in both engines (`models.py:897-913`,
  `payroll_elements.py:675-695`).
- Money columns are `Numeric(12,2)` and Python uses `Decimal` with
  `ROUND_HALF_UP` throughout the engines.
- API endpoints carry `api_role_required` guards and company-scoped queries.
  Payslip download checks ownership (`api.py`). Tenant-isolation and
  tenant-bypass test suites exist and pass.
- Bank account, TIN and Fayda FIN are stored encrypted at rest
  (`models.py:697-699`). The app refuses to start without `DB_ENCRYPTION_KEY`.
- Payroll runs have approve → lock and owner-only unlock, with audit-log rows and
  optimistic `version_id`.
- Reports exist for the PAYE (ERCA) schedule, pension schedule, bank CSV
  (CBE / Dashen / Awash / telebirr) and bilingual PDF payslips with the Noto
  Ethiopic font.
- No real secrets were found in tracked files. CI files only hold obviously fake
  test values. `.env` is not tracked.

### Reports use frozen payroll values (branch `fix/reports-frozen-values`, 2026-10-25)

- State: implemented, locally tested on SQLite. Not hosted-tested, not merged.
  PR against `main` opened on the owner's instruction. Cut from `docs/plan-md`
  @ `cc9065d`.
- New `payroll_engine/frozen_payslip.py` reads each month's figures from the
  payslip itself: gross, tax, employee/employer pension, net, taxable income and
  exempt allowances (stored columns), and basic salary and overtime from the
  `line_items` snapshot. Nothing reads `employee.basic_salary` any more for a
  past month.
- Switched to it: ERCA/PAYE schedule (default columns and company templates),
  pension schedule, both CSV fallbacks, the payslip-details export
  (`/payroll/payslips/export`), and payslip PDF regeneration (`pdf.py`,
  `tasks.py`). The bank file and yearly summary already used stored net/gross.
- Fixed on the way: report template paths `taxable`, `gross`, `net`,
  `pension_employee`, `overtime_pay` are not Payslip attributes, so those ERCA
  columns were blank (Total Taxable was empty). Decimal cells were not totalled
  in the ERCA sheet. The ERCA CSV fallback crashed (`Payslip.overtime_pay`).
  Locked runs could not be downloaded from `/reports/*` (only `completed`), and
  locked months were left out of the yearly summary and the reports page list.
- Gap, not fixed (needs a column + migration + PG proof): legacy-path payslips
  (employee approved before having any pay-item assignment) have no
  `line_items` and no `taxable_income`. Their basic salary was never stored.
  Reports now leave Basic Salary / Total Taxable blank for them and print a red
  note saying how many employees are affected; the PDF omits the Basic /
  Allowances rows. All other figures are the approved ones.
- Still open from Next item 2: "Transport" in ERCA is still "all non-basic,
  non-overtime earnings" (now from the frozen basic), not a real transport
  split; employee name/TIN/bank in reports still come from the current
  employee record (deliberate: corrected bank accounts must reach the bank
  file); no TIN / pension-number columns by default.
- Tests: new `tests/test_reports_frozen_values.py` (approve → lock → raise
  salaries → regenerate ERCA, pension, CSVs, yearly, bank file, payslip export,
  PDF data; all identical and equal to the approved values). Full suite:
  1707 passed, 0 failed, 0 errors, 205 skipped (166 files, one process each, `python -m pytest`, SQLite; baseline 1705 + 2 new). PostgreSQL tests not run.

### Settlement taxation (branch `fix/settlement-taxation`, 2026-10-25)

- State: implemented, locally tested on SQLite. Not hosted-tested, not merged.
  Draft PR against `main`: the tax method **needs accountant confirmation**.
  Cut from `origin/main` @ `bb47054`.
- Severance, pay in lieu of notice and leave encashment are now added to the
  final month's taxable employment income and taxed once with the normal
  monthly brackets (`SETTLEMENT_LUMP_SUM_TAX_METHOD = 'final_month_aggregate'`
  in `services/settlement_service.py`). Source: Proc. 979/2016 Art. 12(1)(c)
  (termination payments are employment income) and Art. 10(2) (tax on the
  total employment income received for the month); rates per Proc. 1395/2025.
  No law, regulation (410/2017) or MoR directive was found that prescribes
  spreading a lump sum over months or years.
- The settlement's PAYE base follows `PENSION_DEDUCTED_BEFORE_TAX`, which is
  `False` on main since PR #32 (PAYE on gross, R1).
- No leave record → 0 days paid and the warning "No leave records — enter
  unused leave days manually". The terminate form takes optional unused leave
  days and pay in lieu of notice. Leave year stays the Gregorian year of the
  last day, because every LeaveBalance writer uses that key.
- New columns on `final_settlement` (migration `f4a5b6c7d8f4`): `notice_pay`,
  `taxable_income`, `calculation_details` (JSON: taxable lines, tax on salary
  alone vs. extra tax from lump sums, method, leave-day source, warnings).
  `tax_on_salary` now holds the total final-month tax. PostgreSQL migration
  proof not run.
- Tests: new `tests/test_settlement_taxation.py` (hand-checked worked examples
  with the flag True and False, missing-leave-record warning, route tests);
  `tests/test_settlement_edges.py` statutory-fallback tests replaced.
  Full suite: 1719 passed, 0 failed, 0 errors, 205 skipped (167 files, one process each, `python -m pytest`, SQLite; baseline 1707 + 12 new). PostgreSQL tests not run.

### Leave daily-rate basis setting (branch `fix/settlement-taxation`, PR #33, 2026-10-25)

- State: implemented, locally tested on SQLite. Not hosted-tested, not merged.
- Leave encashment's daily rate was hard-coded `(basic + allowances) / 30`.
  It is now a per-company setting on `company`: `leave_rate_basis`
  (`basic_plus_regular_allowances` = previous behaviour and the default, or
  `basic_only`) and `leave_rate_divisor` (default 30, whole days 1-31, check
  constraints in model and migration). Defaults live in `constants.py`.
  Existing companies keep the defaults, so no figure changes until a company
  changes the setting. "Regular allowances" = `Employee.allowances` (the
  monthly allowance on record), exactly as before; pay-item assignments are
  not read here.
- Daily rate stays unrounded; encashment = rate x days, rounded once.
  Settlement `calculation_details.leave` now freezes the basis, label,
  divisor, monthly base, components (basic, regular allowances, included or
  not), rounded and unrounded daily rate and the formula. The settlement page
  shows them under Leave Encashment.
- UI: Settings → Company Profile ("Payroll rules: leave encashment"), owner
  only like the rest of that page; changes are audit-logged
  (`leave_rate_setting_change`). There is no separate payroll-settings page.
- Migration `f4a5b6c7d8f5` (after `f4a5b6c7d8f4`); downgrade refuses to drop
  non-default settings. PostgreSQL proof: CI only.
- Which basis and divisor are legally right is a practitioner question
  (Labour Proc. 1156/2019 "wage"); the app keeps the old default.

### Adviser answers on settlement (2026-10-25, second review) — Q2 ACCEPTED, Q3 PARTIAL, Q4 PENDING

Recorded in `docs/decisions/2026-10-25-payroll-rules.md` (Q2–Q4 sections,
second review; Q1 is the PAYE-on-gross answer).

- **Q2 — termination-payment tax: ACCEPTED as statutory default.** Taxable
  severance, notice pay and unused-leave pay are aggregated with other
  taxable employment income in the month received (Proc. 979/2016 Arts 10,
  12; withholding Art 88), unless a specific exemption/rule applies. Not a
  confirmation that every directive was reviewed. Code unchanged
  (`final_month_aggregate`); `TAX_METHOD_STATUS = 'statutory_default'`; each
  settlement shows "Tax method: statutory default: aggregated in month
  received (Proc. 979/2016 Arts 10, 12, 88)".
- **Q3 — leave-pay formula: PARTIAL.** Qualifying wages under Labour Proc.
  1156/2019 Arts 53 and 77 together; Art 53 exclusions apply; fixed /
  contractual / regular does not by itself make an allowance includable; no
  universal ÷26 or ÷30. "Do not use an unconfirmed default for live
  settlements." Implemented: per-company confirmation
  (`company.leave_rate_confirmed_at` / `_by`, migration `f4a5b6c7d8f6`,
  existing companies unconfirmed). Settings → Company Profile has a
  confirmation checkbox (audit `leave_rate_confirmation_change`; changing the
  basis/divisor without re-ticking clears it). A settlement with leave
  encashment > 0 is refused at finalize (terminate POST → 409, nothing saved,
  employee stays active; `LeaveRuleNotConfirmedError` in
  `create_settlement_record`) with "Choose and confirm your leave-pay basis
  and divisor (Labour Proc. 1156/2019 Arts 53, 77) before finalizing" and a
  link to the setting. New "Preview settlement" button (no password, nothing
  saved) computes with a visible warning. Basis label is now "Basic +
  allowances that qualify as wages (Art. 53)"; "(default)" tag removed. The
  leave-pay pending notice stays on a settlement until the company confirms.
- **Q4 — locked-month tax errors: PENDING procedure.** Preserve originals,
  recalculate affected periods, formal correction under Tax Administration
  Proc. 983/2016 as amended by Proc. 1434/2026; the 5-yr (10-yr fraud)
  assessment period is not the PAYE amendment procedure; exact monthly PAYE
  amendment procedure unconfirmed. Still parked.
- PR #33 stays draft (owner decides on merge).
- Tests: new `tests/test_settlement_leave_rule_confirmation.py` (12: block,
  preview, zero-leave allow, confirm → allow, change clears, re-save keeps
  stamp, override basis not confirmed); settlement fixtures in
  `test_settlement_taxation.py` / `test_settlement_leave_rate.py` now confirm
  the company. Full suite (2026-10-26, after merging main @ `c65aaa0`, PR #32,
  and the pension-note rewording): **1778 passed, 0 failed, 0 errors, 205
  skipped** (171 files, one process each, `python -m pytest`, SQLite).
  Single Alembic head `f4a5b6c7d8f6`. ruff check + format clean
  (`payroll_engine/ tests/`). PostgreSQL: CI only. Screens not checked in a
  real browser (no browser in the sandbox); HTML asserted in tests.
- Tests: new `tests/test_settlement_leave_rate.py` (hand-checked: basic 10,000
  + 2,000 regular allowance, 10 days → basic_only 3,333.33, basic_plus
  4,000.00; divisor 26; default unchanged; validation; DB constraint;
  settings route + audit; settlement page). Full suite: 1731 passed, 0 failed, 0 errors, 205 skipped (168 files, one process each, `python -m pytest`, SQLite; baseline 1719 + 12 new). PostgreSQL tests not run locally.

### Branch `fix/paye-gross-income` (2026-10-25, merged to main as PR #32 @ `c65aaa0`)

- R1 done on the branch: `PENSION_DEDUCTED_BEFORE_TAX = False`, so PAYE is on
  gross taxable income. The flag is still there (set it to `True` to go back).
  Both engines (`payroll.py`, `payroll_elements.py`), the Excel engine,
  final settlement, the termination and allowance what-ifs and the Excel diff
  check all follow it. Quick Start only imports employees, so it has no
  calculation of its own. The explanation texts (calculation flow, notices,
  tooltips) were updated.
- Worked example: basic 10,000 → pension 700.00, PAYE 1,650.00, net 7,650.00.
- Locked months: approved payslips keep the tax, taxable and net that were
  stored on them. Nothing recomputes them from the flag. Two display paths
  re-derived taxable as `gross − pension` (employee portal payslip page and
  the payslip CSV export). They now read the stored `Payslip.taxable_income`.
  On the portal and the payroll results screen, only rows with no stored value
  fall back to the old formula. Since the merge of PR #31 the CSV export uses
  `frozen_figures` and leaves taxable blank for those legacy rows instead. `freeze_context` now records which rule was
  used.
- Tests on the branch (after merging main @ `2b0d15e`, PR #34): **1742 passed,
  0 failed, 0 errors, 205 skipped** (168 files, one process each, SQLite,
  `python -m pytest`, Python 3.12; 1736 + 6 from #34). PostgreSQL tests run in
  CI only.
- Rule **confirmed by the adviser in writing, 2026-10-25** (Q1 in
  `docs/decisions/2026-10-25-payroll-rules.md`; Income Tax Proc. 979/2016
  Arts 10–12, Art 11 as amended by Proc. 1395/2025). RC-38000-01 is closed.
- Still open: drafts/reviews still open at deploy (see Now), and what to do
  about already-locked months (Q4, pending; see Parked).

### Amharic label fixes (branch `fix/amharic-labels`, 2026-10-25)

- State: implemented, locally tested on SQLite. Not hosted-tested, not merged.
  PR against `main` opened on the owner's instruction. Cut from `origin/main` @
  `bb47054`.
- Replaced 41 clearly wrong strings (39 Amharic, 2 Afaan Oromoo): all 19
  wrong pay-item `name_am` labels in `catalog.py` (e.g. employer pension
  "ፀጉሮች" → "የአሠሪ የጡረታ መዋጮ 11%", "ስያፍ" → "… አበል"), the overtime
  placeholder, PDF "Position"/"NET PAY", severance, tax explanation, compliance,
  month-close, rule-source names (one had a corrupted U+FFFD character),
  Enkutatash, and the tax certificate. The `pension_before_tax` and
  `tax_explainer_intro` strings (am + om) no longer call pension-before-tax
  "common practice". Since 2026-10-26 they (and the matching English notes,
  help FAQ, verification checklist, PAYE notice) state the confirmed rule: PAYE
  on gross taxable pay before the 7% pension (Proc. 979/2016).
- Review table for the owner (native speaker) in the PR body: changed strings
  with confidence, plus a "for review" list that was NOT changed.
- PDF: NotoSansEthiopic is registered and embedded; Ethiopic renders. Gap:
  pension, income-tax and overtime rows pass `custom_label`, which also
  overrides the Amharic, so they print English-only (`payroll_elements.py`
  `_line_item_dict`). Not fixed (engine code).
- Not done: data migration for existing companies' `pay_item_type.name_am`
  rows (seeding skips existing rows). Needs PG proof.
- Tests: new `tests/test_amharic_labels.py` (6 tests). Full suite: 1713 passed, 0 failed, 0 errors, 205 skipped (167 files, one process each, `python -m pytest`, SQLite; baseline 1707 + 6 new). ruff check + format clean. PostgreSQL tests not run.

### Pay-item catalog PR 1: seeding + tenant isolation (branch `feat/catalog-foundation`, PR #35, 2026-10-26)

- State: PR #35, SQLite suite and CI (incl. PostgreSQL job) green; PostgreSQL
  tests also run locally (PG 17). Cut from `origin/main` @ `70b7b8d`.
- One seeder: `catalog.seed_company_catalog(company_id)` (system items +
  company templates, idempotent, never overwrites a customised row, SAVEPOINT
  so a concurrent seed cannot fail the caller; proven with a real two-session
  race on PostgreSQL). Called by every company creation path (signup
  setup-profile, Google signup, setup-company, demo, `seed_staging.py`,
  `run.py seed-db`). The duplicate `payroll_elements.seed_pay_item_types` is
  removed; backfill and the spreadsheet advance path build items through the
  same `item_from_spec`.
- Migration `b7c1d2e3f4a5` (data only): seeds system items + every missing
  template key for every existing company; refuses to run if any assignment
  already links another company's employee, pay item or base assignment;
  downgrade is a no-op.
- Migration `c8d9e0f1a2b3` (PostgreSQL only, single head): triggers reject
  any `payroll_item_assignment` insert/update that links another company's
  employee, pay item (system items allowed) or base assignment, and block
  moving a referenced employee / pay item to another company (SQLSTATE 23514).
  Re-checks existing rows first; downgrade drops triggers and functions.
- "Run flask migrate-pay-items" error replaced: employee screens re-seed a
  missing catalog on demand (commits only when rows were created).
- `PayItemType` / `PayrollItemAssignment` use `TenantQuery` (system items
  must be queried with an explicit `company_id IS NULL`; unscoped queries
  raise, they never return empty). ORM guard (before insert/update) plus the PG
  triggers enforce assignment tenancy.
- The partial unique indexes on `pay_item_type` are now declared on the model
  too (same names as the migration), so `create_all` databases enforce them.
- Open: SQLite has no trigger (ORM guard only); `backfill` still creates
  ad-hoc items for unknown legacy keys (by design).

### Pay-item catalog PR 2: company pay-item settings page (branch `feat/catalog-settings-ui`, 2026-10-26)

- State: draft PR, cut from `main` @ `fcd9b31` (PR #35 merged). Not merged.
- What: Settings → Pay items (`/settings/pay-items`), owner-only (there is no
  admin role yet). Lists system + company items grouped as earnings,
  allowances, deductions, employer contributions, tax; add a custom item,
  rename (English / Amharic / Afaan Oromoo labels; key immutable), move
  up/down, deactivate / reactivate, delete. Linked from the sidebar (Prepare)
  and the company profile page. Rules in
  `payroll_engine/services/pay_item_settings.py`; routes in `settings_bp.py`.
- Rules: system items (`company_id IS NULL`) are visible but locked (403 on
  any change); another company's item is 404. Used items (any assignment,
  ended or soft-deleted, or any payslip snapshot) are deactivate-only, and
  only once no assignment is still running. General allowance and salary
  advance (written by imports) can never be deactivated. Only unused custom
  items can be deleted (template items are re-seeded, so they deactivate).
  New custom items are always fixed and fully taxable with no exemption caps
  until catalog PR 3 adds reviewed tax settings. Reordering is display-only;
  no amount changes. Reserved keys (system, engine, template) are refused.
  Every change writes an audit-log row; CSRF via the app-wide CSRFProtect.
- No tax, pension or legal formula changed.
- Migration `9b4e6d2a8c13` (schema only): nullable `pay_item_type.name_om`;
  downgrade drops it. Single Alembic head.
- Tests: `tests/test_pay_item_settings.py` (SQLite) and
  `tests/test_pg_pay_item_settings.py` (PostgreSQL, added to the CI PG job).
- Open: native-speaker review of the 18 new Amharic / Afaan Oromoo strings
  (draft); give the page to an admin role once one exists; catalog PR 3 (tax
  treatment and exemption caps per item, reviewed).

### Pay-item catalog PR 3: legal attributes and centralised caps (branch `feat/catalog-legal-attributes`, 2026-10-26)

- State: draft PR, cut from `main` @ `62682e6` (PR #37 merged). Not merged.
  **Behaviour-preserving: no payroll, pension, tax or settlement amount
  changes** (golden test below). Versioning/snapshots (planned items 4–5)
  are deferred to the next PR.
- Audit (how amounts are computed today, before this PR):
  - Pension: 7 % / 11 % of `Employee.basic_salary` only, in both engines
    (`pension.py`, `payroll_elements.py`, `payroll.py`, `excel_payroll.py`).
    No allowance or overtime is pensionable. Matches Directive 1087/2025
    Art. 2(13) as read in the research note (pending confirmation).
  - Taxable = gross − exempt allowances (pension not deducted, R1). Exempt
    allowances come from: elements engine `_apply_exempt_cap` (catalog row
    caps; transport = lower of ETB 2,200, 25 % of basic, amount; percent cap
    rounded half-up to cents); legacy `EmployeeAllowance.calculated_exempt_amount`
    (same lower-of rule); `allowance_service.calculate_transport_exempt_amount`
    (what-if fallback; percent cap NOT rounded); `excel_payroll` (partial =
    min(amount, `exempt_cap_amount`) only, ignores the percent cap). The
    2,200 / 25 % numbers were in `allowance_service` and `catalog.py`.
  - Inconsistencies found and deliberately NOT changed (each changes tax):
    (a) a PARTIAL item with no cap (hardship) is fully exempt in the elements
    engine but fully taxable on the legacy `EmployeeAllowance` path;
    (b) medical is `exempt` in the legacy writer but `taxable` in the catalog
    template; (c) per diem: catalog template taxable; legacy writer caps it at
    `min(max(255 x 30, 4 % basic), 2,200)` = flat 2,200 for any salary up to
    191,250 — not the statutory per-day rule; (d) `excel_payroll` ignores the
    percent cap; (e) `payroll_elements` puts exempt/taxable the wrong way
    round in `allowance_details` for fully EXEMPT/TAXABLE items (display
    only; totals are right); (f) at approval the elements engine is called
    with `for_date = run.run_date or today`, not the Ethiopian period's dates.
  - Leave encashment: (basic + `Employee.allowances`) / 30 or basic / 30 by
    company setting (PR #33); severance: basic / 30 (`severance.py`); no pay
    item is read for either. Notice pay is entered by hand.
  - Freezing today: approval (`services/payroll_service.process_payroll`,
    worksheet `services/worksheet_review.py`) stores amounts on `Payslip`
    plus `line_items` and `calculation_context` v1 (date, PAYE timing flag,
    tax brackets, employee details). Lock is `PayrollRun.status='locked'`
    (owner-only unlock back to `completed`). Corrections use the frozen
    brackets (`correction_context.frozen_tax`). Item settings (tax treatment,
    caps, flags) are NOT in the snapshot; nothing recomputes an approved
    payslip today, but a future recalculation path would read live items.
- What changed:
  - `payroll_engine/exemption_caps.py`: the one source of truth for exemption
    caps (`TRANSPORT`, `LEGACY_PER_DIEM` marked legacy-unreviewed,
    `HOME_TO_WORK_TRANSPORT` ETB 600 defined but never applied) and the shared
    `lower_of_caps` arithmetic used by the model and the elements engine.
    `allowance_service` constants are now aliases; the catalog seeds the
    transport row from `TRANSPORT`. Home-to-work: no catalog item, no
    calculation (safer than an inactive item every company would see).
  - `pay_item_type.pensionable` and `pay_item_type.counts_as_art53_wage`
    (NOT NULL, default false), migration `d1e2f3a4b5c6` (schema + backfill
    by key; downgrade drops them). Seeded: pensionable = basic salary only;
    Art. 53 wage = basic salary + allowances not excluded by Art. 53(2)
    (general, housing, communication, medical, food, education, uniform,
    other); transport, hardship, per diem, deductions, tax, employer charges
    and custom items = false. **No calculation reads either flag.**
  - Settings → Pay items shows each earning's tax treatment and cap, and the
    two flags, read-only with "Pending legal confirmation". Nothing can edit
    them (not even custom items), because the engine does not honour them.
  - Single Alembic head `d1e2f3a4b5c6`.
- Tests: `tests/test_catalog_caps_golden.py` + `tests/golden/catalog_caps_golden.json`
  (generated on main @ `62682e6` before the refactor, committed separately:
  elements engine 182 scenarios, legacy engine 91, cap helpers 91, what-if
  previews 80, settlement 16; basic 0 / 0.01 / 1,999.99 / 8,799.99 / 8,800 /
  8,800.01 … × transport 0 / 2,199.99 / 2,200 / 2,200.01 / 25,000 …, with
  overtime, per diem, hardship, medical, housing; exact `str(Decimal)`
  match). `tests/test_catalog_legal_attributes.py` (seeded flags, migration
  lists = catalog lists, SQLite downgrade/upgrade backfill, flipping flags
  changes no amount, page read-only, owner-only, no cap literals outside
  `exemption_caps`). `tests/test_pg_catalog_legal_attributes.py` (isolated
  PG database: upgrade/backfill on native enums, downgrade keeps indexes and
  tenancy trigger, re-upgrade; ORM seed on PG) — added to the CI PG job.
  Full SQLite suite (181 files, one process each): 1906 passed, 0 failed,
  0 errors, 222 skipped. PostgreSQL list (25 files, local PG 17): 195 passed.
  ruff check / format clean.
- Open legal questions (adviser): pension base under Directive 1087/2025
  (is a position allowance "salary"?); Art. 53 classification of housing and
  position allowances (and medical / uniform); per diem tiers (4 % / ETB 500
  per day, managers 5 % / ETB 1,000; accommodation variants); home-to-work
  ETB 600 and how practitioners split the two transport kinds; hardship
  (exempt portion by area, list unpublished) — and whether hardship should be
  fully exempt as the elements engine does today.
- Next PR (deferred from this one): versioned item settings with effective
  dates (labels, flags, caps, rates; assignments), an item-settings snapshot
  in `calculation_context` (v2) at approval, backfill for existing approved
  runs from current settings (documented), recalculation of unlocked periods
  using the settings effective for the period date, version history and
  audit entries on the settings page, PG proofs. Then catalog PR 4: switch
  leave pay basis to the Art. 53 flags — **that changes amounts** for
  companies on `basic_plus_regular_allowances`, so it needs the adviser's
  answer first.

### Pay-item catalog PR 4a: approval-time item-settings snapshots (branch `feat/catalog-versioning`, PR #40, 2026-10-27)

- State: **merged** to `main` as PR #40 (`173c1d4`, 2026-10-27).
  **Behaviour-preserving: no payroll, tax, pension or settlement amount
  changes** (`tests/test_catalog_caps_golden.py` unchanged and green).
- New table `payroll_run_item_snapshot` (model
  `PayrollRunItemSnapshot`, TenantQuery-registered): one row per run
  (unique `payroll_run_id`, `ON DELETE CASCADE`), `company_id` NOT NULL,
  JSON `snapshot` (every pay item visible to the company: own + system rows,
  active or not, with labels en/am/om, classification, tax treatment, caps,
  method, rate, `max_percent_of_net`, pensionable, Art. 53 flag, is_active,
  dates), `calculation_date`, `backfilled`, `captured_at`.
  Serialiser: `payroll_engine/item_snapshot.py`.
- Written in the approval transaction in both paths
  (`services/payroll_service.process_payroll`, calculation date = the
  approval's existing `run.run_date or today`; worksheet
  `apply_approved_rows`, calculation date = the rows' month end).
  Approval `for_date` and `calculation_context` v1 unchanged.
- ERCA `_pay_item:<key>:taxable` (`report_templates._pay_item_amount`) reads
  `tax_treatment` from the snapshot (company's own rows only, as the live
  lookup did); runs without a snapshot fall back to the live item.
- Guards: ORM (`before_insert` company must match the run; `before_update`
  rejects any change) and PostgreSQL triggers
  `trg_payroll_run_item_snapshot_tenancy` / `_immutable` (SQLSTATE 23514).
- Migration `e2f3a4b5c6d7` (single head): creates the table and triggers and
  **backfills every existing `completed`/`locked` run from the settings
  current at migration time** (`backfilled = true`, `calculation_date =
  run_date`). Those rows record today's settings, not necessarily the ones
  used at approval (never stored). Downgrade drops triggers, functions and
  table. Historical-import runs (`source='import'`, created `completed`
  outside approval) get no snapshot when created after the migration; they
  have no line items, so the taxable column is 0 for them either way.
- Tests: `tests/test_run_item_snapshot.py` (SQLite, 13) and
  `tests/test_pg_run_item_snapshot.py` (PG, 3; trigger tests also show the
  same statements succeed once the trigger is dropped) — added to the CI PG
  job. Head constants bumped in `test_pg_pr8_reconciliation.py` and
  `test_pg_catalog_legal_attributes.py`. Full SQLite
  suite (182 files, one process each, `python -m pytest`): 1919 passed, 0
  failed, 0 errors, 222 skipped (PR 3 baseline 1906 + 13 new). PostgreSQL
  list (26 files, local PG 17): 198 passed. ruff check / format clean.
- Left for catalog PR 4b: `pay_item_type_version` table, effective-dated
  resolution of item settings (and recalculation of unlocked periods with
  them), version history and audit entries on the settings page. Then the
  Art. 53 leave-basis switch (changes amounts, needs the adviser).

### Pay-item catalog PR 4b: versioned item settings with effective dates (branch `feat/catalog-item-versions`, PR #41, 2026-10-27)

- State: draft PR #41, cut from `main` @ `173c1d4` (PR #40 merged).
  Not merged. **Behaviour-preserving: no payroll, tax, pension or settlement
  amount changes** (PR 3 golden file unchanged and green; new golden tests
  below).
- New table `pay_item_type_version` (model `PayItemTypeVersion`,
  TenantQuery-registered): one row per version of an item's settings
  (labels en/am/om, calculation method, rate, percent-of-item key, tax
  treatment, exemption caps amount/percent/basis, max % of net, regulation
  reference, pensionable, Art. 53 flag, is_active), `version_no` (unique per
  item), `effective_from`, `source` (`migration` / `created` / `settings` /
  `direct`), `changed_by_user_id`, `changes` (field: old/new), `created_at`.
  `company_id` = the item's company (NULL for system items). Key,
  classification and sort order are not versioned. New column
  `pay_item_type.current_version_no` mirrors the newest version; the
  `pay_item_type` row always holds that version's settings.
- Writers: version 1 is written for every new item by a `before_flush` hook
  (seeder, demo, backfill, settings page). The settings page records a new
  version for rename (effective date chosen by the owner: today by default,
  not in the future, not before the current version's date), deactivate and
  reactivate (effective today). Any other ORM change of a versioned setting
  is versioned as `direct` with the replaced version's date, i.e. the same
  "applies to every covered date" effect overwriting had before. Raw-SQL
  edits of `pay_item_type` (future data migrations) must write their own
  version. Used items are still never deleted; deleting an unused custom
  item removes its versions (`ON DELETE CASCADE`).
- Engine (`payroll_elements`): system items and assignments resolve the
  version effective on the calculation date (`item_versions.resolve_item_types`:
  latest `(effective_from, version_no)` on or before the date; before every
  version, the item as first known). Items with one version, and dates the
  current version covers, use the live row unchanged (no extra query). Only
  the versioned settings come from an older version, through read-only views
  (`ResolvedItemType`, `ResolvedAssignment`); declining-balance writes still
  go to the real assignment. The active filter moved from SQL to the
  resolved version. Approved/locked runs never resolve versions (stored
  amounts; 4a snapshots). The approval snapshot now records, per item, the
  version effective on the approval's calculation date (the same settings
  the engine used); the snapshot JSON format is unchanged.
- Settings page: "Version N" per item, a history link per item (system
  items too) and `/settings/pay-items/<id>/history` (owner-only, 404 for
  another company's item): version, effective date, who, when (UTC), what
  changed (old → new). Rename form has an effective-date field. New i18n
  keys `version`, `version_history`, `effective_from`, `changed_by`,
  `recorded_at`, `what_changed`, `current_version`, `first_version` (English
  from the key; Amharic / Afaan Oromoo DRAFT, pending native-speaker
  review).
- Migration `f3a4b5c6d7e8` (single head): adds the column (plain ADD
  COLUMN), creates the table and **backfills version 1 for every existing
  item** (system and company, active or not) from its settings at migration
  time (`source = migration`, `effective_from` = item `effective_date`, else
  its `created_at` date). PostgreSQL triggers (SQLSTATE 23514):
  `trg_pay_item_type_version_tenancy` (version company = item company),
  `trg_pay_item_type_version_immutable` (no UPDATE),
  `trg_pay_item_type_versioned_company` (an item with versions cannot move
  company). ORM guards mirror the first two on SQLite. Downgrade drops
  triggers, functions, table and column.
- Not changed (still open): no tax setting is editable in the UI (pending
  adviser: pension base, Art. 53 leave basis, per diem tiers, ETB 600
  transport, hardship/medical). The engine is still called with
  `for_date = run.run_date or today` at approval (audit item (f)), so
  "the period's version" means the version effective on that date. The
  legacy `payroll.py` / `excel_payroll` / `allowance_service` paths do not
  read `pay_item_type`, so they do not resolve versions.
- Tests: `tests/test_item_versions.py` (SQLite, 27: version 1 = row for
  every item, migration field list / columns / head, SQLite downgrade →
  upgrade backfill; golden: PR 3 elements + what-if matrices byte-identical
  after label/active versions on every company item, and amounts identical
  before/after on the dates they cover; engine resolution of tax treatment,
  cap and active flag per period; snapshot uses the version for its
  calculation date; settings page versions, effective-date validation,
  history page access; immutability, tenancy, direct-change versioning,
  unscoped query raises) and `tests/test_pg_item_versions.py` (PG, 3:
  single head; isolated DB upgrade/backfill on native enums, the three
  triggers each proven by dropping it in a rolled-back transaction, cascade,
  downgrade/re-upgrade; ORM + service + engine + snapshot on the shared DB)
  — added to the CI PG job. Head constant bumped in
  `test_pg_pr8_reconciliation.py`; `test_pg_run_item_snapshot.py` now
  targets its own revision. Full SQLite suite (185 files, one
  process each, `python -m pytest`): 1946 passed, 0 failed, 0 errors, 228
  skipped (4a baseline 1919 + 27 new). PostgreSQL CI list (27 files, local
  PG 17): 201 passed (4a 198 + 3 new). ruff check /
  format clean.

### Pay-item catalog PR 5: employee assignments from the catalog (branch `feat/catalog-employee-assignments`, 2026-10-27)

- State: draft PR, cut from `main` @ `b2847fa` (PRs #40, #41 merged). Not
  merged. **Behaviour-preserving: no payroll, tax, pension or settlement
  amount changes** (golden test below; engine untouched).
- Employee page: new "Assigned pay items" card lists every
  `PayrollItemAssignment` of the employee (status active / scheduled /
  ended / inactive, amount or %, dates, "used in approved payroll up to …",
  "own amount" badge when it differs from the company default). It also
  shows rows written by the old allowance/deduction routes, which the page
  never listed before. Add from the company catalog (own active earnings and
  deductions only; system items refused): `fixed` ETB/month,
  `percent_of_basic` (earnings) or `percent_of_net` (deductions), start /
  end dates, label (required for deductions), reference. Edit / end /
  delete per row. Routes `employees.add_assignment`, `edit_assignment`,
  `end_assignment`, `delete_assignment`; rules in
  `payroll_engine/services/employee_assignments.py`.
- Rules: an assignment is **used** once an approved payslip carries its id
  (line items or deduction details). Used: never deleted; start date fixed;
  amount/type change only from a date after the last approved month that
  used it (old row end-dated the day before, new row added, audit
  `pay_item_assignment_revised`); end date not before the end of that month;
  label editable. Unused: edited in place or deleted. Earnings: one running
  assignment per item (no overlapping dates). Deductions may overlap with
  different labels. Rate-times-units is not offered (the worksheet cannot
  capture units).
- Legacy allowances: the worksheet pays `EmployeeAllowance` records /
  `Employee.allowances` only while the employee has no catalog earning other
  than basic. Adding the first catalog earning to such an employee now needs
  an explicit confirmation (page checkbox, import checkbox), never a silent
  switch. Deductions do not need it.
- Roles: owner and accountant edit (there is no HR role in the codebase;
  `role_required` knows owner / accountant / employee). Employee role:
  403 on all employee pages; reads own active/scheduled pay items on
  `/my/profile` (read-only). Another company's employee / assignment: 404.
- Company default amount: `pay_item_type.default_amount` (migration
  `a4b5c6d7e8f9`, nullable, not versioned), owner sets it on Settings → Pay
  items → item page. It pre-fills the add form; an assignment's own amount is
  what payroll uses (Keka-style per-employee override). **No calculation
  reads the default.**
- Import: Employees → "Import pay items" (`/employees/pay-items/import`,
  owner/accountant). CSV or .xlsx: `employee_id, item_key, amount,
  start_date, end_date, amount_type, label`. Dry-run preview (create /
  update / unchanged / error per row), then apply re-validates and writes
  all rows or none. Re-import is a no-op. Match = employee + item + start
  (+ label for deductions); unused rows update in place, used rows are
  refused. Employee IDs match exactly; rejected, never guessed: "1" when
  only "0001" exists (suggests it), numeric Excel cells when two IDs read as
  the same number ("1" and "0001"), duplicate rows, overlapping rows,
  deleted employees. Template CSV download. Max 2,000 rows.
- JSON bulk import (`POST /api/v1/employees/bulk`): optional per-employee
  `pay_items` list → catalog assignments through the same service, saved
  with the employee in a SAVEPOINT (one bad item rejects that employee only).
  `allowances` plus an earning in `pay_items` is refused (the worksheet
  would stop paying `allowances`). The CSV payroll upload's `allowances` →
  General Allowance mapping is unchanged; Quick Start has no allowance
  column.
- i18n: new keys `assigned_pay_items`, `import_pay_items`, `pay_item`,
  `amount`, `ends_on`, `starts_on`, `edit`, `end_assignment`, `amount_type`,
  `label`, `assign`, `deduction`, `change_from`, `dry_run_preview`,
  `default_amount`, `own_amount` (English from the key; Amharic / Afaan
  Oromoo DRAFT, pending native-speaker review). Existing `start_date`
  (employment start) and `override` keys were not reused because their
  Amharic means something else.
- Tests: `tests/test_catalog_assignment_golden.py` +
  `tests/golden/catalog_assignment_golden.json` (generated on `main` @
  `b2847fa` before any change, committed first: 8 employees in every
  existing data state through the worksheet review and the engine for two
  months, overtime matrix on all engines with and without a TaxRule
  override, deductions above one third); `tests/test_employee_assignments.py`
  (16) and `tests/test_assignment_import.py` (28) on SQLite;
  `tests/test_pg_employee_assignments.py` (PG, 3: head, isolated
  upgrade/downgrade keeps rows, versions, indexes and triggers; service,
  used-revision, import and tenancy trigger on the shared DB) — added to
  the CI PG job. Head pins bumped/relaxed in `test_item_versions.py`,
  `test_pg_item_versions.py`, `test_pg_pr8_reconciliation.py`.
  Full SQLite suite (189 files, one process each, `python -m pytest`): 1995
  passed, 0 failed, 0 errors, 231 skipped (4b baseline 1946 + 49 new).
  PostgreSQL CI list (28 files, local PG 17): 204 passed. ruff check /
  format clean. Single Alembic head `a4b5c6d7e8f9`. Screens not checked in
  a real browser (none in the sandbox); HTML asserted in tests.

### Local commit 8597610 (branch `fix/api-role-scoping`, never pushed)

- Main already has it. Main contains `9a49f88 fix: api role guards, allowance
  exempt caps, and quick-start onboarding bugs`, which covers the same three fixes. The 3 test files from 8597610 (`test_api_role_scoping.py`,
  `test_quick_start.py`, `test_transport_exempt_cap.py`, 21 tests) were run
  against main and **all 21 pass**.
- These small things are in 8597610 but NOT in main. None of them is urgent:
  - Quick Start accepts a salary of 0. 8597610 rejected it.
  - Quick Start rejects `"6,000"`. 8597610 stripped the commas.
  - Quick Start does not strip spaces, dashes or brackets from a phone before
    validating it.
  - When `download_payslip` checks that an employee owns the payslip, it does not
    filter `is_deleted=False`. It would also raise an error, not return a clean
    404, if `user` were ever None (`api.py`, `download_payslip`).
- Do not cherry-pick it. Delete the local branch once the owner agrees.

### Remote branches (28 besides main)

- **Fully merged, safe to delete (16):** codex/monthly-payroll-ui,
  codex/neon-migration-receipt, codex/pension-assumption-isolation,
  codex/rc-verification, codex/recovery-drill-receipt,
  codex/rq-thread-signal-fix, codex/rq-timer-penalty, codex/salary-change-links,
  codex/synthetic-preview, docs/reconciliation-review-stop-20261003,
  feature/approved-payroll-corrections, feature/elements-architecture,
  feature/ethiopian-calendar-first, feature/money-math-gaps,
  prod-hardening-2026-08, recovery/restore-main-aa2e657.
- **Unmerged; someone needs to look at them (commits ahead of main):**
  - chore/legacy-diff-template-cleanup (2)
  - codex/shared-worker-encryption-key (1)
  - feat/platform-admin-control-plane-… (1)
  - feature/amharic-prep-review-and-ops (5)
  - feature/founder-synthetic-trial (5)
  - feature/mobile-ui-redesign (8)
  - feature/monthly-payroll-journey (2)
  - feature/render-readiness (1)
  - platform-gap-analysis-and-strategic-scorecard-… (15)
- **Very old, unrelated history, archive or delete:** archive/pre-rebuild-2026-08
  (412), ci/auto-fix-ruff (375), scale-optimization-security-api-… (389).

### Payroll-rule check against the verified rules (mismatches)

| # | Rule | What the code does | Where |
|---|------|--------------------|-------|
| R1 | PAYE is on gross taxable income, **not** after the 7 % pension (adviser-confirmed 2026-10-25) | **Fixed on main by PR #32 (`c65aaa0`)**: `PENSION_DEDUCTED_BEFORE_TAX = False`. Before that, pension was subtracted before tax, under-withholding e.g. ETB 175 per month on a 10,000 basic (1,475 instead of 1,650) | `constants.py:28`; used in `payroll.py:265`, `payroll_elements.py:262`, `excel_payroll.py:461`, `impact.py:328,444`, `settlement_service.py:176` |
| R2 | Severance, termination pay and leave encashment are taxable | Final settlement taxes **only** outstanding salary. Severance and leave encashment are paid with no tax | `services/settlement_service.py:159-203` (tax at :178) |
| R3 | Leave encashment counts unused days | When there is no balance row, it assumes **no leave was taken** and pays the full entitlement. It also uses the Gregorian `end_date.year` | `settlement_service.py:100-121` |
| R4 | Per diem (>25 km): lower of 4 % of basic or ETB 500/day; managers lower of 5 % or ETB 1,000/day | Uses `max(255×30, 4 % of basic)` capped at 2,200 per month. There is no per-day logic, no manager tier and no distance check. The catalog per-diem item is fully TAXABLE | `services/allowance_service.py:123-128`; `catalog.py:216-228` |
| R5 | Home-to-work transport is exempt up to ETB 600/month (separate from work-travel transport) | There is only one "Transport" type, using the 2,200 / 25 % rule. There is no 600 type | `catalog.py:151-168` |
| R6 | Pension: nationals only, eligible from 45 days, "paid by another employer" option | No per-employee eligibility at all. `expat_pension_exempt` is a TaxRule flag that no engine reads. There is no 45-day rule and no other-employer flag | `pension.py`, `models.py:1693`, `payroll_elements.py:257-259`, `payroll.py:258-259` |
| R7 | Casual unskilled worker ≤ 30 days in 12 months with the same employer is exempt | Not implemented. Daily workers are taxed on full gross using the monthly brackets | `payroll.py:120-140` |
| R8 | Consistent Decimal rounding | Engines are fine. The overtime hourly rate is rounded to 0.01 before it is multiplied (small drift). JSON API and some report cells turn money into `float` | `overtime.py:155`; `api.py:844-848,1062`; `reports.py:512-529`; `bank_file.py:154` |

### Other things a senior engineer or payroll accountant would worry about

- **Reports read today's employee record, not the month's numbers.** Fixed on
  branch `fix/reports-frozen-values` (see above), except legacy-path payslips,
  which have no stored basic. "Transport" in ERCA is still every non-basic,
  non-overtime earning. Payslips have no `basic_salary` snapshot column.
- **Payslip PDFs are on ephemeral disk.** `UPLOAD_FOLDER` defaults to
  `/tmp/uploads` (`__init__.py:134`, `pdf.py:154`). A Render redeploy wipes them.
  No worker runs in production.
- **Two calculation engines are live.** The CSV upload path uses legacy
  `payroll.calculate_payroll(basic, allowances)`, with all allowances taxable
  (`services/payroll_workflow.py:129`, `payroll_bp.py:139`). The worksheet path
  uses `payroll_elements`. The same employee can get different numbers.
  `excel_payroll.py` (1,497 lines) is imported only by tests. `cockpit.py` and
  `cockpits.py` overlap.
- **Tax falls back to default brackets silently.** If reading `TaxRule` fails,
  `tax.py` swallows the error and uses the hard-coded brackets
  (`tax.py`, `_get_brackets_and_relief`, `except Exception: pass`).
- **Amharic labels on payslip items are wrong.** Examples: employer pension
  "ፀጉሮች 11%" (means "hairs"), income tax "የእጅሮ ስሚስ" (not Amharic), basic
  salary "ቀሜታ", and allowance written "ስያፍ" instead of "አበል" (`catalog.py:38,58,76,94,153-363`).
  These labels print on bilingual payslips (`pdf.py:_item_label`).
- **Backups and keys.** Neon Free keeps only 6 hours of restore history. Backups
  are manual dumps on the owner's PC. If `DB_ENCRYPTION_KEY` is lost, bank
  accounts and TINs are lost with it. No offline escrow is recorded.
- **Unlock needs no written reason.** Unlocking a locked month is owner-only and
  audited, but no reason is required (`payroll_bp.py:2041`).
- **Docs sprawl.** About 131 root `.md` files, and `README.md`/`AGENTS.md` point at
  a Windows path. `drill.sql` is an empty tracked dump.

---

## 2. Now

**Owner-agreed working agreement, 2026-10-26 — six bounded points, in this
order** (owner pasted an independent review and asked to adopt it; I concur).
No merge or deployment without the owner's explicit go-ahead. Reconciled: the
previous "Now" said PR #32 (PAYE on gross, R1) was awaiting merge — it is
merged on main @ `c65aaa0`.

1. **Review slice: reports use frozen payroll values (first code slice).**
   Review `fix/reports-frozen-values` against main @ `ba54f90`, including
   legacy payslips that lack snapshots (missing history is shown, never
   invented). Synthetic proof: approve a month, change the salary, regenerate
   payslip / PAYE report / pension report / bank file. Done when the supported
   historical figures reconcile to the approved month and PostgreSQL/migration
   checks pass on the exact reviewed revision. (PLAN Next item 2.)
2. **Adviser pack, in parallel, no code.** Written worked examples for:
   pensionable salary and eligibility (Proc. 1268/2022 + Directive 1087/2025);
   per diem, transport and casual-worker exemptions with the actual directive
   and effective dates; holiday work vs holiday overtime (2.5× Art. 68(1)(d)
   vs 2× Art. 75); leave encashment (Art. 53 qualifying components and the
   company-confirmed divisor); the exact procedure for correcting a filed PAYE
   month (Q4; Proc. 1434/2026 hook). Decision record:
   `docs/decisions/2026-10-25-payroll-rules.md`. A company setting is not
   itself proof that the selected rule is lawful. (PLAN Next items 1, 3, 4.)
    Research pack reviewed 2026-10-30 with official-source citations, synthetic
    examples, and explicit unanswered questions. It is ready for adviser review;
    legal and practitioner answers and applicable directive versions remain open.
3. **One dependable monthly workflow.** One accountant completes a synthetic
   month across import → calculate → review → approve → lock → payslips →
   reports → bank file; identical worked cases across every calculation path;
   retry / duplicate-approval and tenant-access tests; screens checked in a
   real browser. Prerequisite for an accountant trial; not proof of a real
   filing, bank payment or statutory acceptance. (PLAN Next item 5.)
4. **/diff/ accountant wedge — demo before public.** Demonstrate the existing
   authenticated tool with synthetic spreadsheets; accountants identify
   confusing explanations, missing columns and disagreements; design the free
   experience around what they need. Before any public upload: period
   selection, rule versions, data retention, upload limits, result
   availability across workers, privacy and abuse controls. "Free, no login"
   is a product decision needing safe design and user evidence.
5. **Real filing and payment formats (needs a live pilot account).** Obtain
   authorized blank or sanitized templates for one accountant's e-Tax process,
   pension process (Directive 1087/2025 contribution form) and primary bank;
   record portal version, field definitions, sample validation and acceptance
   result; only then build format-specific exports. Generating a file, filing
   it and paying employees stay three different states; payout APIs and
   reconciliation come later, once a provider's contract and failure responses
   are understood.
6. **Service, pricing and recovery.** Interview accountants on ETB pricing,
   deadline support, procurement and who buys/refers. In parallel verify
   backup/restore, encryption-key recovery, durable payslips and the deployed
   revision before any real-data pilot.

- Carried over from the R1 slice: already-locked months — the lock does not
  remove the duty to address an error (Q4; see point 2); do not overwrite
  them. Drafts and worksheet reviews still open at deploy hold pre-R1
  figures; refresh or re-upload them after deploy.
- Checkout note 2026-10-26: main @ `ba54f90`; PLAN.md modified (this file);
  untracked webhook migration and deprecated mobile files preserved, touched
  by no one.

---

## 3. Next

Ordered by what stops one real accountant from running one real month of payroll.
Each item still needs the owner to confirm it before it moves to Now.

1. **Tax severance, termination pay and leave encashment in final settlement (R2, R3).**
   - What: add severance and encashment to taxable income using the agreed method.
     Stop assuming "no leave taken" when there is no balance row; ask for the
     unused days instead. Use the right leave year.
   - Why: settlements currently pay these amounts out untaxed.
   - Files: `services/settlement_service.py`, `severance.py`,
     `tests/test_settlement_edges.py`.
   - Size: M. Risk: high. Needs accountant input on the method for lump sums.
   - Status (2026-10-25): implemented on `fix/settlement-taxation` (draft PR
     #33), final-month aggregate method. Adviser second review 2026-10-25:
     Q2 (tax method) ACCEPTED as statutory default; Q3 (leave formula,
     Labour Proc. 1156/2019 Arts 53, 77) PARTIAL — leave pay blocked at
     finalize until each company confirms its basis and divisor. PostgreSQL proof of migrations
     `f4a5b6c7d8f4`/`f4a5b6c7d8f5`: CI only.
2. **Reports use the month's frozen numbers, not today's employee record.**
   - Partly done on `fix/reports-frozen-values` (reports read stored payslip
     values and the `line_items` basic). Left: a `basic_salary` column for
     legacy-path payslips, a real transport split, TIN/pension-number columns.
   - What: snapshot basic salary and allowance splits on `Payslip` (new column
     plus migration, or read them from `calculation_context`/`line_items`). Point
     the PAYE and pension schedules at the snapshot. Fix the CSV fallback
     "transport = gross − basic". Add employee TIN and pension number columns
     by default.
   - Why: a locked month's filing must never change after a raise.
   - Files: `reports.py`, `report_templates.py`, `models.py` (Payslip),
     `migrations/`.
   - Size: M. Risk: medium (needs a migration and PG proof).
3. **Pension eligibility per employee (R6).**
   - What: add per-employee pension fields: national or not, start date for the
     45-day rule, and "pension paid by another employer". Apply them in both
     engines.
   - Why: foreigners and new starters get pension deducted wrongly.
   - Files: `models.py` (Employee), `pension.py`, `payroll_elements.py`,
     `payroll.py`, the employee form templates, `migrations/`.
   - Size: M. Risk: medium.
4. **Correct allowance types: per diem, home-to-work transport, casual workers (R4, R5, R7).**
   - What: per diem as a per-day calculation (lower of 4 % or 500, managers 5 %
     or 1,000, more than 25 km). A separate home-to-work transport type with a
     600 cap. A casual-worker exemption (≤ 30 days in 12 months, same employer).
   - Why: wrong exemptions mean wrong tax and wrong ERCA filings.
   - Files: `services/allowance_service.py`, `catalog.py`, `payroll_elements.py`,
     `payroll.py`, tests.
   - Size: M. Risk: medium.
5. **One calculation engine.**
   - What: route the CSV upload and Quick Start through `payroll_elements` (or
     prove both give identical numbers with a shared golden test). Remove or wall
     off `excel_payroll.py`, and merge `cockpit.py` with `cockpits.py`. Make
     `tax.py` log or raise when `TaxRule` lookup fails, not silently fall back.
   - Why: two engines will drift, and every fix above must otherwise be made several
     times.
   - Files: `services/payroll_workflow.py`, `payroll_bp.py`, `payroll.py`,
     `excel_payroll.py`, `tax.py`.
   - Size: L. Risk: medium-high. Do it after items 1–4, or first if the owner
     prefers fixing rules only once.
6. **Payslip PDFs that survive a redeploy.**
   - What: store PDFs durably (Postgres bytea or object storage), or regenerate
     them on demand from the snapshot. Confirm the in-process worker runs in
     production.
   - Why: payslips vanish from `/tmp/uploads` on every Render deploy.
   - Files: `pdf.py`, `__init__.py`, `inprocess_worker.py`, `tasks.py`.
   - Size: M. Risk: medium.
7. **Fix the Amharic labels on payslip and statutory items.**
   - What: replace the wrong `name_am` strings, using a native-speaker or
     accountant-reviewed list (for example መሠረታዊ ደመወዝ, የገቢ ግብር,
     የጡረታ መዋጮ 7 % / 11 %, የትራንስፖርት አበል, የውሎ አበል). Add a test so no
     label is empty. Add a data migration for companies that already exist.
   - Why: a printed payslip with nonsense Amharic kills trust right away.
   - Files: `catalog.py`, `i18n.py`, `migrations/`.
   - Size: S-M. Risk: low.
8. **Backups, keys and a deploy file that matches reality.**
   - What: automate a daily `pg_dump` of Neon to off-site storage. Escrow
     `DB_ENCRYPTION_KEY` offline. Run one restore drill. Rewrite `render.yaml`
     to match the real setup (Neon, no Redis or worker, cron secret wiring).
   - Why: Neon Free keeps 6 hours of history, and losing the key loses bank and
     TIN data.
   - Files: `render.yaml`, `scripts/`, `verify_backup*.py`, `DISASTER_RECOVERY.md`
     (then archive it).
   - Size: M. Risk: medium.
9. **Small money and API cleanups.**
   - What: return money as strings, not `float`, in the JSON API and reports.
     Carry the full hourly overtime rate and round once. Require a reason to
     unlock a locked month. Port the 4 Quick Start and payslip-ownership details
     that were only in 8597610.
   - Why: rounding and audit-trail hygiene.
   - Files: `api.py`, `reports.py`, `bank_file.py`, `overtime.py`,
     `payroll_bp.py:2041`, `wizard_bp.py`.
   - Size: S. Risk: low.
10. **Clean the repo: archive the docs and prune the branches.**
    - What: `git mv` every root planning/audit `.md` (keep `README.md`,
      `PLAN.md`, `AGENTS.md`, `SECURITY.md`, `CHANGELOG.md`) into
      `docs/archive/`. Remove the Windows paths from `README.md`. Delete
      `drill.sql`. Delete the 16 merged remote branches and the local
      `fix/api-role-scoping`. Decide, one at a time, on the 9 unmerged branches.
    - Why: the sprawl is the owner's main pain, and it misleads every new session.
    - Files: repo root, `docs/`.
    - Size: S. Risk: low (history stays in git).

---

## 4. Parked ideas

AI sessions put new ideas here, one line each, with the reason they are parked.

- Use the per-pay-item "Art. 53 wage" flag (`counts_as_art53_wage`, added
  informational-only in catalog PR 3) so the leave base sums only qualifying
  components instead of `Employee.allowances`. Parked: Q3 is PARTIAL
  (2026-10-25); for now the company confirms the basis (label "Basic +
  allowances that qualify as wages (Art. 53)") before any leave pay is
  finalized. This is catalog PR 4 and changes amounts.

- Future-dated pay-item versions (effective after today) and an owner-chosen
  date for deactivate / reactivate. Parked: the row must mirror the newest
  version, so future versions need a scheduled switch; not needed until tax
  settings become editable (catalog PR 4b).
- Record the resolved `version_no` per item in the approval snapshot.
  Parked: changes the frozen 4a snapshot format (needs a v2 + migration).
- Assignments that follow the company default amount (no own amount, so a
  default change applies to them). Parked: payroll would then read
  `default_amount`, which needs versioning and changes amounts (catalog PR 5).
- Rate-times-units assignments (hours, days) on the employee page and in the
  import. Parked: the worksheet review cannot capture units yet.
- Apply only the valid rows of an assignment import. Parked: all-or-nothing
  is the safer default for payroll data; owner to decide.
- Retire the old Allowances / Deductions cards on the employee page (they
  show legacy `EmployeeAllowance` / `EmployeeDeduction` rows and the old add
  forms). Parked: legacy rows still exist and are still paid; needs a data
  migration into assignments with a money proof.
- Mid-month assignment start/end proration. Parked: the engine uses the
  month-end date; proration is a payroll rule (Next item, mid-month joiners).
- Run the PostgreSQL test suite locally or in a sandbox. Parked: needs a
  disposable Postgres; CI covers it for now.
- e-Tax / ERCA portal direct filing (`ETAX_INTEGRATION_PATH.md`). Parked: the
  manual export must be right first.
- Afaan Oromo UI (`i18n_om.py`). Parked: Amharic is not correct yet.
- Push notifications, webhooks, mobile PWA. Parked: nothing to do with one
  accountant's month.
- Billing / plans (`billing_bp.py`). Parked: no paying customers yet.
- Platform admin control plane and analytics. Parked: one pilot does not need them.
- Excel diff check onboarding improvements. Parked: the engine rules need fixing
  first.
- Upgrade `EncryptedType` to `StringEncryptedType` (deprecation warning).
  Parked: needs a careful data migration.
- Historical PAYE difference report for locked months (quantify only, no
  overwrite; correction via explicit adjustment run after procedure confirmed).
  Parked: correction/amended-declaration procedure (Tax Administration Proc.
  983/2016 Arts 28–29, as amended incl. Proc. 1434/2026) not yet confirmed (Q4).
- Amharic/Oromo `pension_before_tax` and `tax_explainer_intro` still say the
  pension-before-tax question is "still being confirmed" (RC-38000-01). Q1 is
  now confirmed (tax on gross). Parked: needs native-speaker wording.
- Unused i18n key `pension_before_tax` (am/om) still describes the old rule.
  Parked: not shown anywhere, so fix it with the Amharic label work (Next item 7).

---

## 5. Log

- 2026-10-30 — Codex — Second review corrected the source register's Regulation 410/2017 and Pension Proclamation 1268/2022 links and distinguished the directive's actual Justice record date from a separately dated explanatory-note record. Directive dates are consistent at month level; Article 74 effective date remains unverified. No payroll code changed; documentation checks only, no tests run.

- 2026-10-30 — Codex — Corrected the adviser pack's Proc. 1434 citation structure, separated assessment limitation from filed monthly PAYE correction, recorded the pension directive date discrepancy/effectiveness evidence gap, and downgraded transport/per diem formula claims. Updated legal documents and PLAN.md; no payroll code changed; documentation checks only, no tests run.

- 2026-10-30 — Codex — Prepared final five-topic adviser pack, source register
  and implementation-status sheet. Corrected pension reference to Article
  52(2), compared Proc. 983/2016 Article 29 with Proc. 1434/2026, and left
  current Ministry of Revenue PAYE guidance unverified. No code changed.

- 2026-10-30 — Codex — Reviewed the staged adviser pack, located the Amharic
  exempt-income directive and corrected the assessment-revision article citation;
  retained unresolved legal questions for an adviser. Full SQLite suite 2000
  passed, 235 skipped, 66 warnings; no payroll code changed.

- 2026-10-27 — Codex — PR #44 merged to main as `6f041d78`; report snapshot
  behavior passed all required hosted checks, including Python 3.12 and
  PostgreSQL. Next: adviser pack research completed; external answers remain
  open. No production database accessed.

- 2026-10-27 — Codex — Rebased the report correction onto current main
  `cc8815e` (PR #42). Snapshot-aware reports passed the full SQLite suite
  (2000 passed, 235 skipped) and PostgreSQL report/snapshot/version tests
  (13 passed). No production database accessed.

- 2026-10-27 — Codex — Rebased report correction onto main `b2847fa`; use
  run-item snapshots, warn on missing/backfilled data and incomplete totals.
  SQLite suite 1951 passed, 232 skipped; PostgreSQL report/snapshot/version
  tests 13 passed. No PR, merge or deployment.

- 2026-10-27 — Codex — Report breakdown correction: unknown categories and missing snapshots remain blank with a warning. SQLite full suite 1908 passed, 223 skipped, 45 warnings; PostgreSQL report checks 4 passed. Exact-commit proof, hosted validation and practitioner acceptance remain open.

- 2026-10-25 — Hark — Full audit. Cut `docs/plan-md` from `origin/main` @
  `f335bf2`. Tests: 1705 passed, 0 failed, 0 errors, 205 skipped (PostgreSQL
  tests not run). Confirmed that local 8597610 is already covered by main
  (`9a49f88`): its 21 tests pass on main. Found pension-before-tax, untaxed
  settlement lump sums, wrong per diem, missing pension eligibility, reports
  reading live employee data, ephemeral PDFs and wrong Amharic labels. Wrote
  this PLAN.md and rewrote the top of AGENTS.md. Committed locally, not pushed (no
  GitHub credentials).
- 2026-10-25 — Hark — Reports use frozen payroll values (branch fix/reports-frozen-values)
  — ERCA, pension, CSV fallbacks, payslip export and PDF regeneration read the
  payslip's stored figures and `line_items` basic, not `employee.basic_salary`.
  Locked runs downloadable and included in the yearly summary. Legacy-path
  payslips have no stored basic: left blank with a note. Tests:
  1707 passed, 0 failed, 0 errors, 205 skipped (166 files, one process each, `python -m pytest`, SQLite; baseline 1705 + 2 new). PostgreSQL tests not run.
- 2026-10-25 — Hark — Settlement taxation (branch fix/settlement-taxation)
  — severance, pay in lieu of notice and leave encashment added to the final
  month's taxable income (normal brackets, method constant, needs accountant
  confirmation). No leave record → 0 days + warning; manual unused-days and
  notice-pay inputs. Migration `f4a5b6c7d8f4`. Tests: 1719 passed, 0 failed, 0 errors, 205 skipped (167 files, one process each, `python -m pytest`, SQLite; baseline 1707 + 12 new). PostgreSQL tests not run.
- 2026-10-25 — Hark — leave daily-rate basis setting (PR #33) — per-company
  `leave_rate_basis` (`basic_plus_regular_allowances` default / `basic_only`)
  and `leave_rate_divisor` (default 30), migration `f4a5b6c7d8f5`, frozen in
  settlement `calculation_details`, shown on the settlement page, set in
  Settings → Company Profile. Tests: 1731 passed, 0 failed, 0 errors, 205 skipped (168 files, one process each, `python -m pytest`, SQLite; baseline 1719 + 12 new). PostgreSQL tests not run locally.
- 2026-10-25 — Hark — PAYE on gross income (branch fix/paye-gross-income).
  Set `PENSION_DEDUCTED_BEFORE_TAX = False` (the flag stays configurable).
  Portal payslip, payslip CSV export and the results screen now read the
  stored taxable income rather than working out `gross − pension` again.
  Added `tests/test_paye_gross_income.py`, which covers the worked examples
  on all engines and shows that locked months keep their values. Updated 10
  test files that pinned the old numbers. Tests: 1734 passed, 0 failed,
  205 skipped (SQLite). PR opened, DO NOT MERGE until accountant sign-off.
- 2026-10-25 — Hark — PR #32 rebased on main, CI fixed. Merged origin/main
  (bb47054, PRs #30 and #31) into fix/paye-gross-income. Payslip CSV export now
  uses #31's `frozen_figures` (legacy rows without stored taxable are blank, not
  re-derived). CI failure was `test-postgres`: 7 PostgreSQL-only tests still
  pinned after-pension tax (2,310.15 instead of 2,520.15 on gross 12,900.50);
  updated to the gross rule. Removed the parked ERCA "Total Taxable" item (fixed
  by #31). GitGuardian flagged test passwords `OwnerPass1!`/`EmpPass1!` in
  `tests/test_paye_gross_income.py`; switched to the repo's `Test1234!`. Tests: 1736 passed, 0 failed, 205 skipped (167 files, one process
  each, SQLite). Still DO NOT MERGE until accountant sign-off.
- 2026-10-25 — Hark — Amharic label fixes (branch fix/amharic-labels) — 41
  wrong Amharic/Oromo strings replaced (catalog pay items, PDF, severance, tax
  text, rule sources, tax certificate); stale pension-before-tax copy made
  neutral; review table in the PR. Existing companies' DB labels need a data
  migration (not done). Tests: 1713 passed, 0 failed, 0 errors, 205 skipped (167 files, one process each, `python -m pytest`, SQLite; baseline 1707 + 6 new). ruff check + format clean. PostgreSQL tests not run.
- 2026-10-25 — Hark — Adviser answers recorded. Added
  `docs/decisions/2026-10-25-payroll-rules.md` (Q1 PAYE on gross CONFIRMED;
  Q2 termination-payment tax, Q3 leave-pay formula, Q4 locked-month
  corrections PENDING). Merged origin/main (`2b0d15e`, PR #34 Amharic labels)
  into fix/paye-gross-income; PLAN.md conflicts resolved keeping all entries.
  PR #32 title no longer says DO NOT MERGE. Parked: historical PAYE difference
  report for locked months; Amharic/Oromo pension-before-tax copy now stale.
  Tests: 1742 passed, 0 failed, 205 skipped (168 files, one process each,
  SQLite). ruff check + format clean.
- 2026-10-25 — Hark — PR #33: merged origin/main (`2b0d15e`, PR #34) into
  fix/settlement-taxation; PLAN.md conflicts resolved keeping all entries;
  single Alembic head `f4a5b6c7d8f5`. Recorded adviser answers Q2 (tax
  method) and Q3 (leave formula, Labour Proc. 1156/2019 Arts 53, 77) as
  PENDING. Every settlement now stores and shows "Termination-payment tax
  method and leave-pay formula pending written tax/labour-law confirmation".
  Parked an "Art. 53 wage" leave basis. Tests: 1737 passed, 0 failed, 205
  skipped (169 files, SQLite). ruff check + format clean. Still draft.
- 2026-10-25 — Hark — adviser Q2/Q3 applied to PR #33. Q2 ACCEPTED as
  statutory default (aggregated in month received, Proc. 979/2016 Arts 10,
  12, 88); Q3 PARTIAL: per-company leave-rule confirmation (migration
  `f4a5b6c7d8f6`), settlements with leave encashment > 0 blocked at finalize
  until confirmed, preview still allowed with a warning, basis relabelled
  "Basic + allowances that qualify as wages (Art. 53)"; Q4 PENDING procedure.
  Decisions in `docs/decisions/2026-10-25-payroll-rules.md`. Tests: 1749
  passed, 0 failed, 205 skipped (170 files, SQLite). ruff clean. Still draft.
- 2026-10-26 — Hark — Catalog PR 2 (`feat/catalog-settings-ui`): company
  pay-item settings page (owner-only; add, rename, reorder, deactivate /
  reactivate, delete unused custom items; system items locked; new items
  fixed + taxable until PR 3). Migration `9b4e6d2a8c13` adds
  `pay_item_type.name_om`. Tests: SQLite 1879 passed, 0 failed, 219
  skipped (178 files); PostgreSQL 192 passed (CI PG list, local PG 17).
  ruff clean. Draft PR.
- 2026-10-26 — Hark — Catalog PR 3 (branch feat/catalog-legal-attributes):
  audit of pension / exemption / leave bases written above; exemption caps
  centralised in `exemption_caps.py`; informational `pensionable` and
  `counts_as_art53_wage` flags (migration `d1e2f3a4b5c6`) shown read-only on
  the settings page. Golden test proves no amount changed. Versioned
  snapshots deferred to the next PR.
- 2026-10-27 — Hark — Catalog PR 4a (`feat/catalog-versioning`, draft PR
  #40): approval-time pay-item settings snapshot table
  `payroll_run_item_snapshot` written in both approval paths, ERCA taxable
  column reads it, migration `e2f3a4b5c6d7` with backfill and PG triggers.
  No amount changes. Tests: SQLite 1919
  passed, 0 failed, 222 skipped (182 files); PostgreSQL 198 passed (26
  files, local PG 17). ruff clean.
- 2026-10-27 — Hark — Catalog PR 4b (`feat/catalog-item-versions`, draft
  PR #41): `pay_item_type_version` + `current_version_no` (migration
  `f3a4b5c6d7e8`, version 1 backfilled for every item, PG triggers),
  effective-dated resolution in the elements engine and approval snapshot,
  settings-page edits recorded as versions with a history page. No amount
  changes (golden). Tests: SQLite 1946 passed, 0 failed, 228 skipped (185
  files); PostgreSQL 201 passed (27 files, local PG 17). ruff clean.
- 2026-10-27 — Hark — Catalog PR 5 (`feat/catalog-employee-assignments`):
  employee page lists/adds/edits/ends/deletes catalog assignments (used ones
  never deleted, changed only from a date after the last approved month),
  legacy-allowance confirmation, employee read-only portal list, company
  default amount (migration `a4b5c6d7e8f9`, display/pre-fill only), CSV/xlsx
  assignment import with dry run, all-or-nothing apply, idempotent re-import
  and strict employee-ID matching, JSON bulk import `pay_items`. No amount
   changes (golden generated on main first). Tests: SQLite 1995 passed, 0
   failed, 231 skipped (189 files); PostgreSQL 204 passed (28 files, local
   PG 17). ruff clean.
- 2026-10-31 — Hark — Fixed holiday calendar migration chain. Changed
  `down_revision` from `d1e2f3a4b5c6` (not a main head) to `a4b5c6d7e8f9`
  (actual main head) to prevent a second Alembic head. Updated test
  `test_pg_pr8_reconciliation.py` HEAD constant to `h1334c2024a1`. PR #46
  ready for CI rerun.
