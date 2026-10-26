# PLAN.md — EthioPayroll single source of truth

This file is the one plan for the project. If another document disagrees with
this file, this file wins. Keep it short. Update it at the end of every session.

---

## 1. Status

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

### Pay-item catalog PR 1: seeding + tenant isolation (branch `feat/catalog-foundation`, 2026-10-26)

- State: draft PR, SQLite suite green, not hosted-tested, not merged. Cut from
  `origin/main` @ `70b7b8d`.
- One seeder: `catalog.seed_company_catalog(company_id)` (system items +
  company templates, idempotent, never overwrites a customised row, SAVEPOINT
  so a concurrent seed cannot fail the caller). Called by every company
  creation path (signup setup-profile, Google signup, setup-company, demo,
  `seed_staging.py`). The duplicate `payroll_elements.seed_pay_item_types`
  (copied system rows into companies; tests only) is removed; backfill and the
  spreadsheet advance path build items through the same `item_from_spec`.
- Migration `b7c1d2e3f4a5` (data only): seeds system items + every missing
  template key for every existing company; refuses to run if any assignment
  already links another company's employee or pay item; downgrade is a no-op.
- "Run flask migrate-pay-items" error replaced: employee screens re-seed a
  missing catalog on demand.
- `PayItemType` / `PayrollItemAssignment` now use `TenantQuery` (system items
  must be queried with an explicit `company_id IS NULL`). Assignments are
  guarded at the model layer (before insert/update): employee and base
  assignment must be the same company; pay item same company or system. No DB
  constraint: a composite FK cannot express "same company OR system item" and
  needs SQLite table rebuilds. Bulk/Core inserts bypass the guard.
- Open: PostgreSQL run of the migration (CI only); DB-level trigger if wanted;
  partial unique indexes exist only in migrations, not in the model (SQLite
  tests built with `create_all` do not enforce them).

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

**Make PAYE use gross taxable income, without taking the 7 % pension off first (R1).**
Owner approved 2026-10-25.

- Status: **done on branch `fix/paye-gross-income` (PR #32). Rule confirmed by
  the adviser in writing on 2026-10-25** (Q1,
  `docs/decisions/2026-10-25-payroll-rules.md`). Ready for owner review; merge
  needs the owner's go-ahead.
- What changed: `PENSION_DEDUCTED_BEFORE_TAX = False`
  (`payroll_engine/constants.py`), with the flag kept. Every calculation path
  follows it. The notice text and explanations were updated. Worked examples
  were added (10,000 → 1,650 / 7,650; 3,000; 5,000; 20,000). The tests that
  pinned the old after-pension numbers were updated.
- Locked months keep their stored values. Tests now prove it for the export,
  portal and reports paths.
- Still to decide:
  1. ~~Accountant sign-off on the rule (RC-38000-01)~~ — confirmed by the
     adviser 2026-10-25.
  2. Already-locked months: the lock does not remove the duty to address the
     error (Q4, pending procedure). Do not overwrite them; see the parked
     historical PAYE difference report.
  3. Drafts and worksheet reviews still open when this deploys hold figures
     calculated under the old rule. CSV drafts are approved from those stored
     figures. Refresh or re-upload them after deploy.

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

- Per-pay-item "Art. 53 wage" flag (Labour Proc. 1156/2019 Art 53 with its
  exclusions) so the leave base sums only qualifying components instead of
  `Employee.allowances`. Parked: Q3 is PARTIAL (2026-10-25); for now the
  company confirms the basis (label "Basic + allowances that qualify as wages
  (Art. 53)") before any leave pay is finalized.

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
