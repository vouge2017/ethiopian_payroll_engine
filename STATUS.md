# STATUS.md — Command-Verified State

## Calculation context slice - 2026-10-02

Fixed reproduced code defects: full calendar months receive the full settlement
salary (February, leap February, October previously miscalculated); the existing
30-day midmonth convention is unchanged. Percentage-of-basic and rate-times-units
deductions now receive employee salary and period units. Overtime uses the selected
rule date and no longer crashes constructing its saved line item.

Before: `6 failed, 3 passed` for new regressions. After: `69 passed, 3 warnings in
80.60s` for calculation, elements, services and deductions; then `25 passed, 35
warnings in 49.60s` for final calculation fixtures, persisted PostgreSQL deductions
and worksheet journey (overlap). Native PG cases added to CI. No statutory rate or
tax-base policy change, dependency change, migration or deployment. New tests and
settlement service pass Ruff; existing unrelated elements-file lint remains open.
Malformed Excel salaries, exemption caps and first/final-month policy remain open.

## Approved register slice - 2026-10-02

The register now selects a completed/locked run in the active company and reads
saved payslip amounts instead of calculating today's employee salaries. Approved
worksheet names survive later master edits; soft-deleted employees remain in the
historical register. Its ZIP link targets the same run. Legacy runs without identity
snapshots explicitly warn about current names and leave unavailable breakdowns blank.

Before: two new PostgreSQL regressions failed. After: `23 passed, 61 warnings in
37.54s` for register, accounting and worksheet journey checks on the isolated migrated
database. Checks cover unapproved/unknown/foreign runs, authorized company switching,
revoked membership and anonymous access. Changed Python passes Ruff; diff checks pass.
HTTP rendering is checked; visual browser review is still pending. No deployment.
GitHub API still reports `push: false`; committed fixes remain local pending access.
Statutory reports, calculation defects and all broader release blockers remain open.

## Accounting reconciliation slice - 2026-10-02

Isolated implementation checkout: `D:\ethiopian_payroll_engine\payroll-production-work`,
based on pushed `5c9e682` on `feature/elements-architecture`. Older dirty checkout
and the separate audit checkout were preserved. No deployment was performed.

Accounting now accounts for unpaid/sick reductions, loan/advance recoveries and
other deductions using explicitly synthetic trial defaults. Each employee and
the journal must reconcile before any CSV/IIF export; no balancing plug exists.
Worksheet identity and money remain tied to the approved snapshot. Preview
links use actual run IDs, and accounting uses the active company context.

Before: `4 failed, 5 warnings in 9.90s` (unit export guards), and
`5 failed, 19 warnings in 19.43s` (migrated PostgreSQL output cases).
After: `55 passed, 3 warnings in 3.07s` (accounting unit/export cases), and
`19 passed, 52 warnings in 35.50s` (PG accounting plus existing worksheet journey).
Target: isolated PostgreSQL 16.6 database `payroll_fixes_20261002`, local port 55439;
upgraded from empty by the real Alembic chain. No customer database was used.
Changed accounting source and new tests pass Ruff. Native PG cases are added to CI.

The access regression then reproduced a real bug: deleting foreign-company
membership still allowed export (HTTP 200), because the user's default role
was used for any company. That fallback now applies only to the default company.
After the fix: `57 passed, 27 warnings in 56.48s` for PG accounting plus existing
roles, membership, tenant and security regressions. Authorized switching works;
removed membership receives 403. The full source gate still reports the two
Diff authorization review points; they remain required release work.

Account mapping is authorized for synthetic testing only. Practitioner chart
validation, register/statutory consistency, calculation defects, legacy failure
handling, Diff authorization, user trial and production gates remain open.
Whole-repository lint and source preflight are not claimed green by this slice.
Statutory calculations remain deterministic; see `docs/PAYROLL_CALCULATION_POLICY.md`.

**Last updated:** 2026-10-02 02:11 UTC




## Pushed worksheet code and hosted verification - 2026-10-02 02:11 UTC

Code commit 715ddd8 is pushed on feature/elements-architecture. GitHub's branch
head was independently read through its API and matched the local commit.
[Run 36877266566](https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/36877266566) verifies this exact code:

- test (3.11): `TOTAL: 1245 passed, 0 failed, 0 errors, 61 skipped`.
- test-postgres: `69 passed, 177 warnings in 23.57s`.
- lint: `Found 132 errors.`.

Python 3.11 and 3.12 main suites each report 1,245 passed, zero failures/errors
and 61 skipped. Both strict security gates and the Python 3.12 coverage job passed.
All hosted jobs have completed; lint is the sole failing job.
PostgreSQL migration, native tests and rollback passed. These hosted results
supplement the earlier timed-out local full run; that timeout remains recorded.
The general runner skips native PG cases; they execute in the separate PG job.

Whole CI remains red due to lint. Comparing the changed Python files at bb39cde
and 715ddd8 with the same Ruff config found 13 vs 12 findings, zero introduced,
one unused import removed. The 132 global findings are not waived or fixed.
Source preflight still flags the two existing Diff authorization review points.

Visible Chrome completed Download All (ZIP) for the approved synthetic run.
Its PDF contains gross 12,900.50, deductions 4,310.15 and net 8,590.35. This closes
the browser download check; the results-screen individual PDF control, unsupported
Undo button and completed-review badge remain small UI fixes before founder sign-off.
No application deployment, merge, rebase or PR occurred. DESIGN.md remains untouched.
[Hosted evidence](docs/evidence/worksheet-review-hosted-2026-10-01.json).


## Saved worksheet review and approval - 2026-10-01 14:30 UTC

Monthly worksheet amounts now freeze into a tenant-owned review. The accountant
can submit it; the owner confirms with a password. Approval persists those exact
amounts, consumes declining balances once and commits the audit with the money.
Later employee/worksheet edits cannot rewrite the retained snapshot. PDF worker,
on-demand PDF, bank export and history CSV reuse the approved facts. The sample
is gross 12,900.50, deductions 4,310.15 and net 8,590.35 ETB.

Preview no longer consumes balances on this path. Monthly advances end in their
month; saving this month preserves future overtime. Historic legacy approval uses
run date instead of click date. PDF amounts and bilingual labels are readable.
Browser inspection also corrected zero-value draft evidence, missing confirmation
deductions and the unsupported undo promise on the confirmation page.

Verbatim focused results (overlap; not a full-suite total):
- Before handoff: `6 failed, 15 warnings in 32.54s` (review endpoint absent).
- Combined PG money/absence/worksheet selection: `46 passed, 101 warnings in 106.55s (0:01:46)`.
- Relevant existing regressions: `54 passed, 3 warnings in 64.76s (0:01:04)`.
- Existing PDF/output regressions: `16 passed, 3 warnings in 60.51s (0:01:00)`.
- Final PG journey including confirmation: `14 passed, 31 warnings in 48.96s`.
- Whole local isolated suite: `TIMEOUT after 600s; full suite outcome unknown`;
  42 of 113 files completed before timeout, so no whole-suite green claim.

Real Alembic-upgraded PostgreSQL verifies persisted outputs, competing approvals,
tenant/role rejection, audit rollback, stale balances and queue failure recovery.
No schema migration was added in this slice. No create_all migration claim.
The parent bb39cde hosted Python 3.11/3.12 and PG jobs passed; lint failed.
Hosted CI for this patch must be checked after pushing.

Actual local browser login/save/review/password approval succeeded with synthetic
data, CSRF enabled; desktop/phone review and PDF visual captures are on D:.
The local demo is open in a separate Chrome tab. No live payroll was changed.
Work order 2 is not yet closed: results still hide the individual PDF until it
exists, still offer unsupported worksheet Undo, and the completed review badge
says Ready for Approval. Final browser download click and founder feedback remain.
These are the next bounded customer-facing fixes; avoid broader feature work.

Daily-worker attendance, unit-based items, historic worksheet selection and linked
corrections remain outside this monthly slice. General delivery durability,
release lint/security gates, shared worker keys, storage and restore proof remain
open. Not deployed; last user-confirmed live code is aa2e657 (not refreshed here).
[Raw evidence](docs/evidence/worksheet-review-2026-10-01.json) and
[founder trial](docs/FOUNDER_TRIAL.md) distinguish this slice from production readiness.


## Absence month-boundary regression - 2026-10-01 04:09 UTC

Latest a86f67d hosted run 36811249208: PostgreSQL job passed; Python 3.11
`TOTAL: 1241 passed, 1 failed, 0 errors, 42 skipped`; Python 3.12 cancelled;
lint `Found 133 errors.` This supersedes the pending hosted result for that
commit, not the earlier 8c42ce1 green test baseline. The one absence failure
reproduced locally: `1 failed, 5 passed, 3 warnings in 40.08s`.

On October 1 the case created September 29-30 leave but expected an October
deduction. That assertion was wrong for the run month. Explicit fixed dates
now cover October 1/2/3 and September 15, expecting 0/1/2/2 overlapping days.
After repair: `9 passed, 3 warnings in 24.85s`. Independently committed,
Alembic-migrated PostgreSQL cases plus retry: `4 passed, 11 warnings in 14.60s`.
These are focused runs, not a complete-suite result. No calculator/service
change, deployment, or claim that historic-period approval is repaired.

Work order 2 remains active: approval still reads click-day values; saved
worksheet bonus/absence is not yet connected to review and final outputs.
Raw output and current hosted baseline:
[absence-calendar-2026-10-01.json](docs/evidence/absence-calendar-2026-10-01.json).


## Monthly worksheet absence/bonus repair - 2026-09-30 20:44 UTC

At parent e10c369, actual worksheet HTTP cases on migrated PostgreSQL reproduced:
`8 failed, 19 warnings in 21.31s`. After persistence/validation repair:
`8 passed, 19 warnings in 19.71s`. Extended native migration/money selection:
`47 passed, 132 warnings in 74.54s (0:01:14)`.
Final worksheet selection (three additional autosave/role cases):
`16 passed, 41 warnings in 24.55s`. Relevant existing calculator/elements/draft/
payroll-flow checks: `39 passed, 4 warnings in 11.33s`.
These are overlapping focused runs, not a new complete-suite count.

The user confirmed the business meaning: additional unpaid days exclude recorded
approved leave and use (basic + allowances)/30; bonus is taxable for this month.
New spreadsheet_input stores employee/month values with a composite tenant FK
and primary key. Save applies them to the estimate, rejects invalid/foreign rows
before any writes, and commits input and change audit together. PG verifies retry,
competing saves, rollback, database ownership and actual autosave preservation.
Saved advances now reopen with their value. Daily-worker adjustments are rejected
explicitly; stale-month forms must reload. Native CI now includes this file.

Alembic head f4a5b6c7d8f0, 71 revisions. Real base->head and affected downgrade/
upgrade ran on disposable PG; employee rows survive. Downgrade refuses while
saved inputs exist and retains the money/head. It locks the table during its
preservation check. No create_all or stamping was migration proof.

Actual local Edge login/entry/save/reload verified 2 days and a 900.50 bonus:
gross 12,900.50, tax 2,310.15, estimated net 9,090.35. Desktop/390px captures are
on D:. Final label/scroll hint/contrast edits followed the captures. Phone editing,
screen-reader behavior and an actual Tigist trial are not proven. The local demo
tenant was deleted and server/browser stopped; no live data was changed.

This fixes the monthly worksheet estimate, NOT its connection to payroll review,
approval or exports. Estimated net excludes advances/other deductions and the UI
now states that limit. This is work order 1; work order 2 connects saved inputs to
one consistent review/approval outcome. [WORK_ORDERS.md](docs/WORK_ORDERS.md)
contains a reusable instruction, acceptance discipline and the ordered work.

New Python lint/format and diff checks pass. Source preflight remains BLOCKED on
the same two Diff authorization review points; graph has one head/no problems.
Global lint/release gates remain open. No deployment or whole-suite green claim
for this patch; hosted results after pushing must be checked.
Raw before/after commands, outputs and source hashes:
[worksheet-inputs-2026-09-30.json](docs/evidence/worksheet-inputs-2026-09-30.json).

## Product checkpoint and confirmed hosted baseline - 2026-09-30 19:51 UTC

Feature source 8c42ce1 is pushed. Latest hosted run 36764061946 completed:
Python 3.11 and 3.12 each `TOTAL: 1242 passed, 0 failed, 0 errors, 26 skipped`
(311.2s / 287.9s). The Python 3.12 coverage execution also completed
`1242 passed, 26 skipped, 20 warnings in 247.99s (0:04:07)`.
Both strict security selections passed. Separate native PostgreSQL job:
`34 passed, 101 warnings in 8.56s`; real migrations and rollback passed.
Whole CI is still red: lint reports `Found 134 errors.` and format was skipped.
This supersedes the pending hosted PDF results above; one PDF case now passes
and one runner diagnostic case was added, yielding 1242 general passes.

Live public readiness reports database/self up. Isolated Edge browser review
viewed login on desktop and phone; /diff/ returned 404. Last user-confirmed live
SHA remains aa2e657, not independently refreshed. No signed-in/live payroll
workflow or feature deployment occurred. Application code is unchanged.

The next product task is saved-advance preservation in the spreadsheet, then
truthful edits/totals and one complete accountant journey. Source review found
zero-initialized advances submitted by whole-form autosave, unused submitted
absence/bonus values, and no direct spreadsheet-to-approval action. These are
source findings requiring real PG before/after evidence, not live reproductions.
Detailed priority, value, effort limits and acceptance cases:
[product-checkpoint-2026-09-30.md](docs/product-checkpoint-2026-09-30.md).
Raw hosted logs remain under D:/payroll-work-2026-09-30/hosted-current-*.log.

## Hosted baseline and PDF test environment — 2026-09-30 19:09 UTC

CI/runtime repair `669849d` is committed and pushed. Hosted PostgreSQL CI is now
green, including application migrations, explicit native tests and real rollback.
Both Python strict security selections passed. The Python 3.12 isolated suite
completed `TOTAL: 1240 passed, 1 failed, 0 errors, 26 skipped` in 295.2s; the only
failed file is test_ac10_pdf.py. Python 3.11's full run was cancelled by matrix
fail-fast. Lint remains red. This remote record supplements the earlier green
local single-process baseline; it does not overwrite either result.

The PDF case reproduced in a clean runtime-lock install:
`1 failed, 3 warnings in 57.29s`, ModuleNotFoundError for pypdf. The local baseline
had pypdf 6.19.0 installed outside the declared dependencies. requirements-test.txt
now pins that same reader; general CI and README install it alongside the existing
runtime lock. Docker/runtime dependencies and application code are unchanged.

Normal runner output also suppressed the failed child's reason. A before probe
returned `1 failed in 0.48s`; the runner now prints failed child diagnostics even
without --verbose and keeps the child's failure exit code. The existing runner
suite plus the real rendered-PDF case returned:
`21 passed, 3 warnings in 7.98s`. A new runner case increases collection by one;
do not report the prior complete count as a newly executed suite. Changed Python
lint/format, YAML/install/cache/rollback checks and diff checks passed.

Public readyz now returns HTTP 200 with database/self up. The user confirmed
Render Events still shows aa2e657, Deploy succeeded / Live. Connectivity recovered
on that old release; feature repairs have not been deployed. Current live schema,
payroll workflow, workers and restore are unverified. The repaired hosted full
suites need results after this push. PDF label extraction passes; numeric PDF
amounts and visual/font appearance remain outside this test's proof.

Raw summaries, before/after diagnostics and remote/live evidence limits:
[pdf-test-environment-2026-09-30.json](docs/evidence/pdf-test-environment-2026-09-30.json).

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
