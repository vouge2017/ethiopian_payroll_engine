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
- 78 Alembic migrations with a single head, `f4a5b6c7d8f3`.

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

### Branch `fix/paye-gross-income` (2026-10-25, not merged)

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
  the payslip CSV export). They now read the stored `Payslip.taxable_income`,
  and only rows with no stored value fall back to the old formula. The payroll
  results screen does the same. `freeze_context` now records which rule was
  used.
- Tests on the branch: **1734 passed, 0 failed, 0 errors, 205 skipped**
  (SQLite, `python -m pytest` per file, Python 3.12). PostgreSQL tests not run.
- Waiting on: an Ethiopian accountant's written sign-off (RC-38000-01) before
  merge, and a decision on drafts/reviews still open at deploy (see Now).

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
| R1 | PAYE is on gross taxable income, **not** after the 7 % pension | **Fixed on branch `fix/paye-gross-income`, not merged.** On main, pension is subtracted before tax (`PENSION_DEDUCTED_BEFORE_TAX = True`). This under-withholds every month, e.g. ETB 175 per month on a 10,000 basic (1,475 instead of 1,650) | `constants.py:28`; used in `payroll.py:265`, `payroll_elements.py:262`, `excel_payroll.py:461`, `impact.py:328,444`, `settlement_service.py:176` |
| R2 | Severance, termination pay and leave encashment are taxable | Final settlement taxes **only** outstanding salary. Severance and leave encashment are paid with no tax | `services/settlement_service.py:159-203` (tax at :178) |
| R3 | Leave encashment counts unused days | When there is no balance row, it assumes **no leave was taken** and pays the full entitlement. It also uses the Gregorian `end_date.year` | `settlement_service.py:100-121` |
| R4 | Per diem (>25 km): lower of 4 % of basic or ETB 500/day; managers lower of 5 % or ETB 1,000/day | Uses `max(255×30, 4 % of basic)` capped at 2,200 per month. There is no per-day logic, no manager tier and no distance check. The catalog per-diem item is fully TAXABLE | `services/allowance_service.py:123-128`; `catalog.py:216-228` |
| R5 | Home-to-work transport is exempt up to ETB 600/month (separate from work-travel transport) | There is only one "Transport" type, using the 2,200 / 25 % rule. There is no 600 type | `catalog.py:151-168` |
| R6 | Pension: nationals only, eligible from 45 days, "paid by another employer" option | No per-employee eligibility at all. `expat_pension_exempt` is a TaxRule flag that no engine reads. There is no 45-day rule and no other-employer flag | `pension.py`, `models.py:1693`, `payroll_elements.py:257-259`, `payroll.py:258-259` |
| R7 | Casual unskilled worker ≤ 30 days in 12 months with the same employer is exempt | Not implemented. Daily workers are taxed on full gross using the monthly brackets | `payroll.py:120-140` |
| R8 | Consistent Decimal rounding | Engines are fine. The overtime hourly rate is rounded to 0.01 before it is multiplied (small drift). JSON API and some report cells turn money into `float` | `overtime.py:155`; `api.py:844-848,1062`; `reports.py:512-529`; `bank_file.py:154` |

### Other things a senior engineer or payroll accountant would worry about

- **Reports read today's employee record, not the month's numbers.** The PAYE and
  pension schedules use `employee.basic_salary`. After a raise, re-downloading a
  locked month gives a different basic (`reports.py:42,283,512`). In the CSV
  fallback, "Transport" is `gross − basic`, so overtime and every allowance end up
  in transport (`reports.py:514`). Payslips have no `basic_salary` snapshot column.
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

- Status: **done on branch `fix/paye-gross-income`, waiting for an accountant's
  sign-off before merge.** The PR is marked DO NOT MERGE.
- What changed: `PENSION_DEDUCTED_BEFORE_TAX = False`
  (`payroll_engine/constants.py`), with the flag kept. Every calculation path
  follows it. The notice text and explanations were updated. Worked examples
  were added (10,000 → 1,650 / 7,650; 3,000; 5,000; 20,000). The tests that
  pinned the old after-pension numbers were updated.
- Locked months keep their stored values. Tests now prove it for the export,
  portal and reports paths.
- Still to decide before merge:
  1. One Ethiopian accountant signs off on the rule in writing (closes
     RC-38000-01).
  2. Already-locked months: leave them, or issue correction runs.
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
2. **Reports use the month's frozen numbers, not today's employee record.**
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
- ERCA report "Total Taxable" column uses `data_path='taxable'`, but `Payslip`
  has only `taxable_income`, so the cell is blank (`reports.py:47`,
  `report_templates.py:62,78`). Parked: belongs to Next item 2 (reports use
  frozen values).
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
- 2026-10-25 — Hark — PAYE on gross income (branch fix/paye-gross-income).
  Set `PENSION_DEDUCTED_BEFORE_TAX = False` (the flag stays configurable).
  Portal payslip, payslip CSV export and the results screen now read the
  stored taxable income rather than working out `gross − pension` again.
  Added `tests/test_paye_gross_income.py`, which covers the worked examples
  on all engines and shows that locked months keep their values. Updated 10
  test files that pinned the old numbers. Tests: 1734 passed, 0 failed,
  205 skipped (SQLite). PR opened, DO NOT MERGE until accountant sign-off.
