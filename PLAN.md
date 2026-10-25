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

- Baseline: `origin/main` @ `f335bf2` (f335bf22490ede3bd7af90daa67b8b9ab7a555e8,
  2026-10-25, "Merge pull request #29 … rq-timer-penalty").
- This plan was written on branch `docs/plan-md`, cut from that SHA.
- Production (per the 2026-10-21 notes in STATUS.md, not re-checked here): one Render web service with a Neon Free Postgres. There is **no** Redis and **no** worker
  service. `render.yaml` still describes a Render Postgres + Redis + worker +
  cron, so it does not match reality.
- 78 Alembic migrations with a single head, `f4a5b6c7d8f3` (on main; `fix/settlement-taxation` adds `f4a5b6c7d8f4`).

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
- The pension-before-tax base follows `PENSION_DEDUCTED_BEFORE_TAX` as-is (not
  changed here; R1 is on `fix/paye-gross-income`).
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
| R1 | PAYE is on gross taxable income, **not** after the 7 % pension | Pension is subtracted before tax (`PENSION_DEDUCTED_BEFORE_TAX = True`). This under-withholds every month, e.g. ETB 175 per month on a 10,000 basic (1,475 instead of 1,650) | `constants.py:28`; used in `payroll.py:265`, `payroll_elements.py:262`, `excel_payroll.py:461`, `impact.py:328,444`, `settlement_service.py:176` |
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

**Proposed — owner to confirm:**

**Make PAYE use gross taxable income, without taking the 7 % pension off first (R1).**
- What: set `PENSION_DEDUCTED_BEFORE_TAX = False` in
  `payroll_engine/constants.py:28`. Update the pending-PAYE notice text. Update
  the tests that assert the old base (`tests/test_pension_before_tax_rc38000_01.py`
  and any golden numbers). Add one worked example to the tests: basic 10,000 →
  taxable 10,000, tax 1,650, pension 700, net 7,650.
- Why: it changes every payslip and every PAYE schedule. The current setting
  under-withholds tax, and the employer carries that liability. It is a one-line
  switch that was built for exactly this, so the risk is in the tests and
  numbers, not the design.
- Before merging: one Ethiopian accountant signs off on the rule in writing
  (closes RC-38000-01). Decide what happens to months already locked: leave
  them, or issue correction runs.
- Size: S. Risk: high business impact, low code risk.

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
   - Status (2026-10-25): implemented on `fix/settlement-taxation` (draft PR),
     final-month aggregate method, pending accountant confirmation of the
     method and PostgreSQL proof of migration `f4a5b6c7d8f4`.
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
