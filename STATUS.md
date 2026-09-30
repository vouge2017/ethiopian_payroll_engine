# STATUS.md — Command-Verified State

**Last updated:** 2026-09-30 18:27 UTC

## CI/runtime dependency repair — 2026-09-30 18:27 UTC

Report repair `d227939` is committed and pushed. Application code is unchanged
in this slice; the complete green local baseline in the preceding section stands.
Hosted CI at `35f2852` failed before its main tests: unpinned installation selected
dependencies that could not import SQLAlchemy-Utils and requested an uninstalled
PostgreSQL driver. Both CI jobs now install the existing Docker runtime lock and
key pip caches to that file. No test, lint or failure gate was disabled.

The actual Flask-Migrate rollback call also had an independent API bug:
`downgrade('-1')` treats `-1` as a directory. It reproduced exit 1 with
`Error: Path doesn't exist: -1. Please use the 'init' command to create a new scripts folder.`
CI now calls `downgrade(revision='-1')`. This was not proven by earlier Alembic
command-level cycles; the new full-application wrapper check closes that gap.

- Fresh isolated install of all direct pins: SQLAlchemy 2.0.51,
  SQLAlchemy-Utils 0.42.1, psycopg2-binary 2.9.12, Python 3.12.13.
- Actual create_app and Flask-Migrate downgrade base -> upgrade head ->
  downgrade one -> upgrade head passed on disposable PostgreSQL 16; final
  revision f4a5b6c7d8ef, 33 public tables. No create_all or stamping proof.
- Exact strict security/tenancy selection:
  `103 passed, 2 skipped, 10 warnings in 241.07s (0:04:01)`.
  The two native migration skips were executed in the separate PG selection.
- Locked native PG and startup selection:
  `40 passed, 101 warnings in 54.51s`; all 26 required PG cases executed.
- CI YAML/install/cache/rollback configuration checks and diff check passed.

The complete suite was not repeated under the lock; its recorded green run uses
SQLAlchemy 2.0.54. Python 3.11 and the repaired hosted workflow need remote results.
Whole-repo lint remains red. Source preflight now has two DIFF_AUTH_REVIEW points
(compare/download public isolation), down from three after removing the embedded
Git remote credential; it remains BLOCKED, not a security certification.
Schema-aware readiness, recoverable post-commit jobs, settlement zero balances,
historical employee warnings, shared worker keys and restore proof remain open.
Render's new DATABASE_URL was saved only; no deployed recovery is proven.

Raw summaries, commands, dependency versions and the full-app migration record:
[ci-runtime-2026-09-30.json](docs/evidence/ci-runtime-2026-09-30.json).

## Green local baseline and bounded report reads — 2026-09-30 18:02 UTC

Encryption repair `35f2852` is committed and pushed. After the bounded report-read
repair, the frozen worktree at that parent plus the recorded source diff completed:
`1241 passed, 26 skipped, 20 warnings in 13769.11s (3:49:29)`, exit 0.
This supersedes the red `44c6810` baseline: its four benchmark failures now pass;
six startup/target cases add six passes, and seven encryption plus three report
PostgreSQL cases add ten skips in the SQLite run. Total is 1267, up from 1251.
Every one of the 26 native PG skips executed separately in the combined check:
`40 passed, 101 warnings in 33.05s` (26 native plus 14 structural/unit cases).
This is a green local regression baseline, not a green hosted CI or release claim.

- Query regressions before: `2 failed, 1 passed, 15 warnings in 2.30s`.
- After: `3 passed, 15 warnings in 3.73s`.
- Report/exception/dashboard/unchanged benchmark checks:
  `70 passed, 3 warnings in 38.33s`.
- Real migrated PostgreSQL, 500 committed synthetic employees: report time
  6.100s -> 0.883s; employee SELECTs 1501 -> 2; total SELECTs 2006 -> 507.
  At 50/200 employees the employee SELECT count is also 2. No benchmark limits
  were relaxed. Tenant checks still exclude foreign names and foreign runs;
  a report must perform no writes. Changed lint/format and diff checks passed.

Evidence and exception passes now reuse tenant-scoped bulk employee reads.
Active-list and soft-delete behavior are preserved. PostgreSQL separately showed
that deactivated employees' negative-pay warnings are skipped today; repair that
as a money-safety slice, rather than hiding the behavior in a speed change.
Draft employee lookup and first-payroll COUNT growth remain. These one-run local
measurements do not establish production capacity.

Hosted CI at `35f2852` is red: PostgreSQL startup requests an uninstalled psycopg
driver; SQLAlchemy-Utils fails collection on ScalarAttributeImpl; lint is also
red. CI installs unpinned requirements.txt while Docker uses the existing lock.
The next CI slice must verify and use that lock; no gates should be disabled.
Render DATABASE_URL is saved only per the user; no deployment/recovery is proven.
The exposed GitHub token must be revoked. Its embedded remote URL credential was
removed in favor of Credential Manager; no token is stored in this evidence.

Raw summaries, commands, source hashes and PostgreSQL measurements:
[report-performance-2026-09-30.json](docs/evidence/report-performance-2026-09-30.json).

## Current evidence — 2026-09-30

Branch: `feature/elements-architecture`. Test-runner/collection repair `2c05019`
is committed and pushed. The following complete baseline is at that exact revision:

- Collection without a shell-supplied encryption key: `1235 tests collected in 13.42s`, exit 0.
- All 104 files executed sequentially through the repaired `run_tests.py` functions:
  **1225 passed, 8 failed, 0 errors, 2 skipped**, exit 1; no file timeouts.
- The single-process full suite timed out after 600 seconds. Its final failure
  count is unknown. No whole-suite green claim is made.

Per-file summaries, failures, revision and controlled configuration are retained
in [baseline-2026-09-30.json](docs/evidence/baseline-2026-09-30.json).
Raw local outputs: `D:/payroll-work-2026-09-30/baseline-<filename>.log`.
The capture command was `python D:/payroll-work-2026-09-30/file_baseline.py`;
each child ran `python -m pytest <file> --tb=line -q` with the recorded options.

Known failures remain open: document upload coverage (3), filing deadlines (2),
webhook flag assumptions (2), and quick-start visibility (1). The webhook test
group separately returned `5 passed, 3 warnings in 6.63s` when enabled, with
thread/HTTP delivery mocked. This supplemental result does not rewrite the baseline.

## Regression net repair — 2026-09-30 11:51 UTC

At source revision `f63f636`, the prior eight failing cases reproduced:
`8 failed, 84 passed, 3 warnings in 219.34s (0:03:39)`, exit 1.
After this test-only slice, the same five files plus environment guards and two
deadline boundary cases returned `98 passed, 3 warnings in 212.57s (0:03:32)`, exit 0.
Those eight known failures are now resolved in the focused checks. The older
file-isolated baseline remains a historical record; the current complete suite
has not yet been run to completion.

The production guard probe no longer reloads or first imports shared config under
temporary PostgreSQL settings. An independent identity probe failed before and
passed after without contacting a database. Deduction upload fixtures now seed
the company catalog; accepted documents must persist their exact bytes and an
assignment-linked audit, while rejected files must leave neither records nor
files. Filing tests control the clock and cover due-day/overdue boundaries.
Webhook unit tests set and restore their flag with delivery threads mocked.
Quick Start checks the actual primary link and separately checks its paste page.
The ineffective `db.engine_options` assignment and unsupported hang claim were
removed; the fixtures retain per-test database/tenant cleanup.

Changed test lint and formatter checks passed. No production behavior, payroll
policy or schema changed. SQLite fixture setup is not migration evidence.
Raw output and exact commands:
[regression-net-2026-09-30.json](docs/evidence/regression-net-2026-09-30.json).
Public `/readyz` was checked again and returned HTTP 503, database down.

## Complete baseline and fail-fast startup — 2026-09-30 13:02 UTC

Regression repair `44c6810` is committed and pushed. For the first completed
single-process run at that exact revision:
`4 failed, 1231 passed, 16 skipped, 20 warnings in 1656.48s (0:27:36)`, exit 1.
All four failures are `test_benchmark.py` evidence/combined report performance
at 200/500 employees. There are no collection or fixture errors. The previous
600-second timeout is superseded by this count, not a green claim. The 16 skips
are the native PostgreSQL migration, catalog and money cases, tested separately.

Container startup now upgrades visibly and starts Gunicorn only on success;
there is no stamp fallback. `sqlalchemy.url` is blank in the committed INI.
Flask-Migrate uses the application URL; standalone Alembic requires an explicit
Config URL or DATABASE_URL, normalizes postgres://, and gives the Config override
precedence. Required rollback failures no longer turn into CI success. Native
CI explicitly supplies TEST_DATABASE_URL and runs independently of the general
suite; branch pushes now trigger CI. Synthetic CI encryption keys are explicit.

- Startup/target probes before: `4 failed, 2 passed, 3 warnings in 4.87s`.
- After: `6 passed, 3 warnings in 2.40s`.
- Native CI selection on disposable migrated PostgreSQL 16:
  `24 passed, 39 warnings in 22.30s`. All 16 required PG cases executed.
- Real Alembic upgrade -> downgrade base -> upgrade and downgrade -1 -> upgrade
  passed on `payroll_slice_20260930`, loopback port 55432; head `f4a5b6c7d8ee`.
- Changed files lint/format and CI YAML/configuration checks passed. Whole-repo
  lint remains red with 135 errors; GitHub-hosted execution and Docker build are
  unverified. No create_all or stamping was used as migration proof.

Deployment remains blocked: a normal employee TIN insert failed on migrated
PostgreSQL (encrypted payload exceeds VARCHAR(20)); bank/Fayda ORM reads also
failed. Five targeted before-cases are red, contradicting drift rows 18-20.
The next schema slice must preserve existing ciphertext and reject unsafe
rollback or unreadable legacy values. Render's replacement `ethiopian-payroll-db`
is Available, Oregon, same workspace, and its DATABASE_URL was saved only, per
the user. No dashboard access or deployed migration was verified. The last
public readyz check returned 503, database down. Tigist's chosen first task is
preparing/checking her payroll spreadsheet; employee count remains unknown.

Raw outputs and exact commands:
[startup-gate-2026-09-30.json](docs/evidence/startup-gate-2026-09-30.json).

## Employee encryption/schema compatibility — 2026-09-30 13:20 UTC

Startup repair `eb5b4d9` is committed and pushed. A migrated PostgreSQL TIN
write failed with StringDataRightTruncation, and bank/Fayda reads failed because
the driver returned VARCHAR strings to an EncryptedType that expects bytes.
Drift rows 18-20 were incorrectly called false positives. Migration
`f4a5b6c7d8ef` now uses BYTEA for all three columns and preserves ciphertext.

- Seven regressions before: `7 failed, 43 warnings in 7.73s`.
- After: `7 passed, 53 warnings in 8.40s`.
- Combined migration/catalog/money/encryption/startup selection:
  `37 passed, 89 warnings in 27.04s`. This includes 23 required native PostgreSQL
  cases and 14 structural/unit checks, with no required skips.
- Real empty PostgreSQL upgrade -> downgrade base -> upgrade and one-revision
  rollback/forward passed at the new head. Existing bank ciphertext also passed
  a data-bearing rollback/forward round-trip at the preceding head.
- Wrong keys and legacy plaintext are rejected before DDL. Oversized ciphertext
  rejects rollback before any column changes; the revision and values survive.
  This guarded refusal is expected behavior, not permission to force rollback.
- New migration/test lint and formatter checks passed. Global lint and the last
  complete suite remain red; no new whole-suite green claim is made.

The migration takes a PostgreSQL table lock to make preflight/type changes
atomic. It does not change encryption keys or payroll policy. Earlier historical
data-bearing migrations, backups/restore and live Render initialization remain
unverified. CI explicitly includes these seven native regression cases.
Raw commands and results:
[employee-encryption-2026-09-30.json](docs/evidence/employee-encryption-2026-09-30.json).

While profiling synthetic committed rows on this migrated PG schema, evidence
collection took 2.276s/806 SELECTs at 200 employees and 6.100s/2006 SELECTs at
500; employee SELECTs were 601/1501. This confirms repeated per-payslip reads
in evidence/exception reports. No performance thresholds have been relaxed.
That report query path and the existing four benchmark failures remain next.

## PostgreSQL catalog compatibility slice — 2026-09-30 09:11 UTC

Three model String columns did not match migration-owned native enum columns.
An actual bulk ORM insert failed with PostgreSQL `DatatypeMismatch`. Model
variants now bind the existing native types; no schema migration was added.

Commands used the explicitly identified disposable PostgreSQL 16 database
`payroll_slice_20260930` on loopback port 55432, never the live Render database:

- `python -m pytest tests/test_pg_catalog_types.py -q --tb=short`
  before: `1 failed, 5 warnings in 4.20s`; after:
  `1 passed, 5 warnings in 3.08s`. The test commits and reads the rows through
  an independent connection against a real Alembic-upgraded schema.
- Affected SQLite engine, consumer and backfill files:
  `43 passed, 3 warnings in 57.32s`, exit 0.
- Real Alembic `upgrade head -> downgrade base -> upgrade head` succeeded on
  the disposable empty schema; independently inspected revision
  `f4a5b6c7d8ee` and 33 public tables. No stamping or `create_all()` was used
  as migration proof. Data-bearing rollback/backfill safety remains unverified.

Raw outputs: `D:/payroll-work-2026-09-30/money-pg-catalog-before.log`,
`money-pg-catalog-after.log`, `enum-sqlite-verified.log`, `pg-upgrade.log`,
and `pg-downgrade.log` in the same directory.

## Deduction identity repair (F05) — 2026-09-30 09:52 UTC

Catalog prerequisite `1949d12` is committed and pushed. The next slice keeps
legacy deduction row IDs separate from new assignment IDs and retains support
for older legacy payloads without identity flags. Mechanical import/date-expression
lint cleanup does not change payroll policy.

Same-tenant ID collision on migrated PostgreSQL before the repair: a legacy
balance of 500 became 400 instead of 480, despite its own deduction being 20.
The new assignment's separate balance correctly became 900 after recovering 100.

- Before, eight money cases: `4 failed, 4 passed, 19 warnings in 11.97s`.
- After, those eight plus the catalog regression: `9 passed, 21 warnings in 11.30s`.
- Affected SQLite service/backfill/transaction/period checks:
  `52 passed, 3 warnings in 51.85s`.
- Final collection, without a shell-supplied encryption key:
  `1244 tests collected in 3.45s`, exit 0. Collection is not execution.
- Changed service/test lint passed; the new test's formatter check passed.

The database cases prove committed balances, repeated approval, two competing
locked same-run approvals, pre-commit rollback, two foreign scope cases, an
assignment identity without the legacy flag, and older legacy payload compatibility.
Completion audit and payslip counts are checked through a separate connection.
HTTP authorization, undo reconciliation, all concurrency patterns and post-commit
delivery recovery remain outside this proof. Only external PDF enqueue/webhook
delivery are stubbed. No production data was used.

Raw before/after output and exact commands:
[deduction-identity-2026-09-30.json](docs/evidence/deduction-identity-2026-09-30.json).
The complete baseline above remains the unchanged record at `2c05019`, not a
claim that the current whole suite is green.

## Legacy single recovery repair (F06) — 2026-09-30 10:04 UTC

Identity repair `5c71fe1` is committed and pushed. A migrated PostgreSQL
fallback approval recovered 20 from net pay but consumed 40 from the legacy
balance: 500 became 460. The legacy loop now computes recovery only; the
tenant/employee-scoped helper consumes that amount once within the transaction.

- Five new cases before: `3 failed, 2 passed, 8 deselected, 13 warnings in 8.29s`.
- All 13 money cases plus catalog after: `14 passed, 31 warnings in 16.89s`.
- Relevant SQLite checks: `52 passed, 3 warnings in 51.31s`.
- Collection: `1249 tests collected in 4.51s`, exit 0; not a whole-suite pass.
- Changed-file lint and test formatting checks passed.

The five additional PostgreSQL cases cover persisted debt/net reconciliation,
retry, competing locked approvals, rollback before commit, and capped final
recovery/deactivation. Separate connections inspect the committed ledger,
payslip net amount and completion audit count. No ORM persistence or transaction
is mocked. F05's foreign-scope and identity cases remain green alongside them.

Exact commands and raw outputs:
[legacy-recovery-2026-09-30.json](docs/evidence/legacy-recovery-2026-09-30.json).
The historical file-isolated baseline and single-process timeout remain the
whole-suite state; these bounded green slices do not erase the eight failures.

## Live incident and remaining gates

Public endpoint check at 2026-09-30 04:07 UTC: `/healthz` 200 and `/readyz`
503 with database down. User-provided deployed SHA is `aa2e657`; it has not
been independently matched to Render. The configured short internal hostname
matches the DNS failure in supplied logs. The user reports no PostgreSQL database listed in the dashboard and confirms
only demo/test data was stored. Database removal/expiry versus a different
workspace is not independently resolved. Demo recovery can use a new disposable
database; a new URL does not recover the old data. No production database connection or configuration change occurred.

Release is blocked. F05 and F06 have the bounded PostgreSQL evidence above.
Settlement dates (F08), preview/undo balance ownership, post-commit delivery,
and remaining test failures are still open. Deployment stamp fallback,
hardcoded Alembic URL, swallowed CI rollback failure, and remaining source
review findings still need bounded repairs. Source preflight is a limited
source check, not a production security verdict.

## Historical records (superseded where current evidence above differs)


**Last updated:** 2026-09-15 14:30 UTC  
**Rule:** Any claim about test counts, verification status, or floor state below must cite a line in this file with a timestamp — or the claim is "not yet checked."

---

## Test Count — Machine Fact

Command run: `cd ethiopian_payroll_engine && python -m pytest --co -q 2>&1 | tail -1`

**Result (2026-09-15 14:30 UTC):** 1127 tests collected in 14.97s

Full command output (last 3 lines):
```
C:\Users\25191\payroll_audit\ethiopian_payroll_engine\tests\test_performance_large_csv.py:69: PytestUnknownMarkWarning: Unknown pytest.mark.benchmark - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.benchmark

-- Docs: https://docs.pytest.org/en/stable/how-to/mark.html
1127 tests collected in 14.97s
```

**Note:** This is *collected*, not *passed*. The pass/fail state is NOT recorded here until a full pytest run completes and the summary line is captured verbatim.

---

## Current Branch — Machine Fact

Command run: `git branch --show-current && echo "---" && git log --oneline -5`

**Result (2026-09-15 14:30 UTC):**
```
prod-hardening-2026-08
---
4cd799c EMERGENCY VALVE: env-gated CSRF exemption for auth routes behind broken prod proxy pairing
12bef26 P0: failed login for unknown account crashed 500 (NULL audit company_id); skip tenant audit for unknown identifiers + regression test
a788ee0 Fix register phone mask: force 9 digits starting 9/7 (strips 251/0 prefixes, caps length) - unblocks registration
73dd152 Fix register phone input: accept 09.. / +2519.. / 9.. formats (mask was truncating valid numbers, silently blocking registration)
552745d render.yaml: managed Postgres (standard) with PITR for production
```

**Branch:** `prod-hardening-2026-08` (verified, not assumed)

---

## Known State (to be re-verified each session)

These entries are **claims with timestamps** — re-run the cited command to verify, or treat as "not yet checked" if the timestamp is old.

### Phone validation fix — claimed resolved

- **Claim:** Phone numbers in test fixtures fixed from `0911000001` (10-digit, invalid) to `911000001` (9-digit, valid).
- **Claimed scope:** 10 test files, ~47 tests blocked.
- **Timestamp:** Not yet re-verified on this session. Run `grep -r "0911000001" tests/` to check.
- **Status:** NOT YET CHECKED — session start.

### CI/CD pipeline — claimed on roadmap

- **Source:** `ROADMAP.md` line 309-314 — CI/CD is listed as Floor 9 in the roadmap narrative (not explicitly in the scored table).
- **Status:** NOT YET CHECKED — no `.github/workflows/` directory confirmed present.
- **Action needed:** Create minimal GitHub Actions workflow that runs `pytest --co` on push. This makes test count a machine fact, not a Hermes recollection.

### Floor 4 closed — claimed

- **Source:** User directive, captured in `PROJECT_RULES.md` line 23-30.
- **Status:** Verified by file existence — `PROJECT_RULES.md` line 23 states "Floor 4 is closed."
- **Meaning:** Calculator math definition locked. New bugs = new issues, not re-litigation.

---

## What Must Be Verified Before Any Work Claim

Before claiming any of the following, re-run the cited command and update the timestamp + result:

| Claim | Verification Command | Last Verified |
|-------|---------------------|---------------|
| Total test count | `pytest --co -q \| tail -1` | 2026-09-15 14:30 UTC (1127 collected) |
| Pass/fail state | Full `pytest` run + summary line | NOT YET RUN THIS SESSION |
| Current branch | `git branch --show-current` | 2026-09-15 14:30 UTC (prod-hardening-2026-08) |
| Recent commits | `git log --oneline -5` | 2026-09-15 14:30 UTC |
| Phone fixture validity | `grep -r "09110000" tests/ \| wc -l` | NOT YET CHECKED |
| CI workflow exists | `ls -la .github/workflows/ 2>/dev/null \| head` | NOT YET CHECKED |

---

## The Test-Count Drift Problem — Structural Fix

The root cause of test-count drift is that test counts come from Hermes recollection, not from a machine source.

**The fix is Floor 9 — CI/CD pipeline.** Even a minimal GitHub Actions workflow that runs on every push and records:
- `pytest --co -q` output (test count)
- Full `pytest` summary (pass/fail)

...makes "current test count" a machine fact stored in the CI logs, not a number Hermes remembers.

**Until CI exists:** Every session re-runs `pytest --co -q` and updates this file with the verbatim result and timestamp.

---

## Phase 2 Regression Triage — 2026-09-26 (command-verified)

Baseline established on a git worktree at merge-base `7e87ebb` (detached), running
the 16 failing test IDs: **13 failed, 3 passed**. The 13 are genuinely pre-existing.
The 3 that pass on merge-base but fail on this branch were the regression set:

| Test | merge-base | branch | Status |
|---|---|---|---|
| `test_employee_phone.py::test_employee_accepts_non_ethiopian_phone` | PASS | PASS | **RESOLVED — 4/4 green, TypeError gone** |
| `test_dashboard_api.py::…::test_accountant_gets_trust_metrics` | PASS | FAIL | **OPEN** — `TypeError: '<=' not supported between 'int' and 'MagicMock'` |
| `test_evidence.py::…::test_invalid_run_returns_empty` | PASS | FAIL | **DIAGNOSED, not fixed — stale test, NOT a money bug** |

### test_evidence — root cause (stale expectation, not a money bug)

`collect_evidence` changed its read seam from `db.session.get(PayrollRun, id)` to
`PayrollRun.query.filter_by(id=..., company_id=...).first()` (tenant isolation).
The test still mocks the OLD seam (`mock_db.session.get.return_value = None`), which
is now dead code, so `not current_run` is False against a MagicMock, the guard is
bypassed, and the full check suite runs against mock data — returning 8 instead of 0.

`collect_evidence` performs **no writes** (no `.add(`/`.commit(`/`.delete(` in
`evidence.py`). It is a read-only report builder and never calls `process_payroll`.
Nothing creates payslips or financial records for a rejected run. The production
change is correct and strictly more secure; only the test's mock seam is stale.

### test_dashboard_api — OPEN, root cause not isolated

Trace: `dashboard_api.py:648` → `filing_workspace.py:120` → `compliance.py:114` →
`calendar.py:170`. A MagicMock reaches compliance date math (`min(day, max_day)` /
`calendar.monthrange`) and is compared against an int. NOT the Free-plan
5-employee cap (that cap is in `test_employee_phone.py:42`, which is green).
The specific mock leaking into the date path was not isolated.

### conftest cleanup restored (did NOT fix either failure)

`tests/conftest.py` autouse fixture had lost `db.session.rollback()` +
`db.session.remove()` when tenant-context clearing was added. Both are restored —
correct on their own merits, since the identity map otherwise leaks across tests.
**This was a wrong hypothesis: restoring it did not fix either failure.** The fix is
retained; the cause lies elsewhere.

### Interim full suite (chunked, 8 slices)

`passed=1137 failed=16 errors=14 skipped=2 TOTAL=1169`. The 14 errors are
`psycopg2.OperationalError: connection refused localhost:5432` and do not reproduce
when the four PG-referencing files run alone (24/24 pass) — cross-test config leak,
still unexplained. Note the suite cannot run as one process here; it is killed at
~36-75%, so chunked slices are the only way to get a complete number.

---

## Not Yet Checked (session start)

The following are NOT verified in this session. Do not cite them as fact until re-checked:

- Actual pass/fail state of all tests (last complete number: 1169, chunked)
- Whether the phone fixture fix is actually in place across all 10 files
- Whether `.github/workflows/` exists
- Whether VERIFICATION_PACKAGE.md has been sent to the accountant
- Excel Diff Check status
- Root cause of the test_dashboard_api MagicMock leak
- `cookies.txt` was a LOCAL DEV session (`domain=localhost`, `_user_id=2`) — not a
  production credential. Now gitignored; never committed or pushed.

---

*Update this file every session. Timestamp every claim. When in doubt, run the command.*
