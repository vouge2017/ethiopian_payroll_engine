# STATUS.md — Command-Verified State

## CURRENT AUTHORITATIVE STATE - 2026-10-05

- **Merged:** PR #11 was merged with explicit user approval at
  `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110` on 2026-10-04, 13:21:46 UTC.
  This is remote main and preserves accepted PR #8/#10 plus the monthly journey.
  The merge tree is identical to reviewed/tested head
  `6eb7fd13037741b18b4dfa8d3ec7a9d24360abf9` (no file differences).
- **Schema:** 77 Alembic revisions, sole head `f4a5b6c7d8f3`; source graph checked.
- **Implemented and locally tested, not merged/deployed:** readiness now checks
  real revisions, model tables and columns and fails closed with HTTP 503.
  Strict container probe handles internal HTTP/HTTPS correctly and refuses
  redirects/unknown schema. Final focused receipt:
  `22 passed, 18 warnings in 99.62s (0:01:39)`; independent review and Ruff pass.
  Release branch `feature/render-readiness` starts from current main `2f6f4e6`.
- **Locally verified:** reconciliation and correction PostgreSQL receipts below
  remain attributable to their tested slices; they are not full-main CI proof.
  Persistent synthetic trial launcher is now verified locally on
  `feature/founder-synthetic-trial`: empty-DB Alembic upgrade, normal sign-in,
  CSRF rejection, encryption readback, non-destructive reinitialization and
  saved-input/key persistence across app restart. Desktop/390px browser sign-in
  and worksheet passed. This launcher is not merged or hosted-CI verified.
- **Hosted CI on exact PR head:** Python 3.11 and 3.12 each
  `TOTAL: 1563 passed, 0 failed, 0 errors, 124 skipped`;
  PostgreSQL `128 passed, 286 warnings in 66.04s (0:01:06)`;
  lint/format, strict tenant/security gates and both standalone migration jobs
  passed. [PR CI](https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/37202508112).
- **Hosted CI on merge SHA:** Python 3.11/3.12, PostgreSQL, lint/format and both
  standalone migration jobs completed successfully on `2f6f4e6`. These are
  completed merge-job results, distinct from the earlier PR-head receipt.
  [Merge CI](https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/37205352561).
- **GitGuardian:** success on exact PR #11 head `6eb7fd1`, check `111436890883`;
  no separate GitGuardian check is attached to merge SHA `2f6f4e6`. Historical
  incident 37741140 is classified Ignored / Test credential.
- **Hosted recovery:** with explicit user approval, initialized the web service's
  confirmed empty database using the existing 77 Alembic revisions. Completed
  2026-10-04 20:37:03 UTC at sole head `f4a5b6c7d8f3`; no missing model tables or
  columns. Hosted login GET 200, unknown-login POST 302 then GET 200 with
  `Invalid credentials.`; registration GET 200. The reported table-missing
  HTTP 500 is recovered. User confirmed this was only a new/test setup.
- **Deployed:** this is a verified hosted schema change, not an identified
  application release or restore drill. User-supplied Render Settings now identify
  Docker on main, `./Dockerfile`, override `gunicorn -b 0.0.0.0:10000 wsgi:app`,
  blank pre-deploy/health path and auto-deploy On Commit. Override bypasses the
  source migration guard. Latest successful deployed SHA remains unidentified.
  Readiness fix and settings correction are not deployed; earlier hosted probe
  reported migrations `unknown` with 200. No hosted account/payroll was created.
- **Practitioner verified:** founder/Tigist monthly trial not yet completed.
- **Implemented, tested and merged:** repaired the two stale CI test contracts;
  closed the three known results/review controls; connected existing saved
  review, previous approved comparison and deterministic checks. Founder/Tigist
  scripts are prepared. **Still open:** practitioner acceptance, unresolved policy
  and deployment/recovery evidence. The isolated local synthetic trial is ready;
  founder observation remains open. Hosted schema/login recovery is complete;
  successful owner sign-in requires a hosted account. The synthetic trial owner
  remains local. No new application deployment, PR or merge occurred.

This section supersedes older pending/next-task statements below. Historical
receipts remain unchanged. Working branch: `feature/render-readiness`
in `payroll-pr8-integration`; accepted main remains authoritative. Founder work
is preserved on `feature/founder-synthetic-trial` (local checkpoint `9a22b6c`,
remote receipt `ac04ecf`) and is excluded from the release source. No new folder.
Earlier dirty workspaces are preserved.

### Readiness / startup verification receipt - 2026-10-05

Scope: shared revision/table/column inventory, readiness route and read-only
operator CLI, strict container probe, health-path declarations, narrowly scoped
health exemptions and regression tests. No migration, money/statutory policy,
UI, worker-delivery policy or payroll data changed. Private `local-evidence/`
is now excluded from Docker build context. Trial launcher/screenshots are not
part of this release branch; their verified receipts below remain historical.

Initial sandbox run failed on Windows temporary-directory permissions before
behavior validation. Authorized disposable-PostgreSQL run reproduced the defect:
`8 failed, 1 passed, 25 warnings in 51.93s`. First fix passed
`14 passed, 14 warnings in 57.09s`. Independent review then reproduced a real
production Talisman redirect: HTTP loopback 302 versus forwarded-HTTPS 200,
with and without ProxyFix. Fixed probe uses loopback only, no HTTP proxy, no
redirect following, a five-second timeout and explicit healthy JSON checks.

Final executed targets: `tests/test_pg_readiness.py`,
`tests/test_pg_schema_inventory.py`, `tests/test_startup_gate.py`,
`tests/test_container_healthcheck.py` via ignored locked-environment wrapper.
`22 passed, 18 warnings in 99.62s (0:01:39)`; exit 0. Every schema-damage case
uses an owned UUID PostgreSQL database upgraded through existing Alembic; no
production DDL or create_all. Checks cover healthy/missing/stale/multiple heads,
missing table/column, dependency errors without secret disclosure, PostgreSQL
read-only statements, more than the default rate limit, expired authenticated
sessions/password/billing/maintenance, migration-failure startup and actual
Docker shell probe against HTTP/Talisman (ready, 503, unknown and redirect).
Ruff check/format pass; independent follow-up found no concrete issue. Source
preflight has 77 revisions/one head/no source findings; it is not deployment proof.
Raw ignored receipts: `readiness-before-authorized.log`, `readiness-after.log`,
`readiness-reviewed.diff`. Release source/test files are byte-identical to the
tested checkpoint payload; no duplicate expensive suite run for branch isolation.

Current remote main was refreshed through GitHub API: exact `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`.
User supplied Render Settings: source vouge2017/ethiopian_payroll_engine, main,
Dockerfile `./Dockerfile`, context `.`, Docker Command
`gunicorn -b 0.0.0.0:10000 wsgi:app`, blank pre-deploy and health-check path,
On Commit auto-deploy. This override demonstrably skips the Dockerfile's existing
`flask db upgrade` / failure-stop path; blank health path is only TCP evidence.
Reference: [Docker command overrides](https://render.com/docs/docker),
[Render HTTP health checks](https://render.com/docs/health-checks).

Concrete pending release settings: leave Docker Command blank to use the tested
Dockerfile startup; Health Check Path `/readyz` after promoting this fix. Saving
settings/merging into main can deploy automatically, so PR/merge/deploy approval
is still required. Actual latest deploy SHA and complete hosted owner sign-in
remain unverified. No settings change, app deployment, PR or merge performed.
Worker availability remains informational; this gate does not certify schema
types/constraints/data, encryption keys, payroll outputs or production readiness.

### Approved Render schema initialization / login recovery - 2026-10-04

User explicitly approved database initialization and asked to investigate older
data first, then confirmed the website was only a new/test setup. Read-only
catalog inspection found only the target `ethiopian_payroll_db_kn8y` and default
`postgres` database on this server. The default has only `primarytable`, with
`key`/`value` VARCHAR(20) columns; SELECT is not permitted. No payroll tables
were found there. A count attempt was denied and is not recovery evidence;
permission metadata was subsequently read without changing permissions/data.
Other Render instances/backups cannot be enumerated without dashboard/API access.

The bounded project-file search found local `instance/app.db` with 5 employees,
1 payroll run and 5 payslips. Preserved a byte-identical SHA-256-verified copy in
ignored `local-evidence/historical-candidates/app.db`; original untouched.
Its provenance remains unidentified. It was not imported, upgraded or deleted.
The other three inspected local SQLite files have no employee/payroll records.

Immediately before applying migrations, reconfirmed matching private external
and web-service connections, approved database identity, no non-system
relations, no Alembic revision, and the tested source graph (77 revisions,
sole head `f4a5b6c7d8f3`). Migration/application source has no differences from
the accepted main schema. Executed ignored operator wrapper
`python -X utf8 local-evidence/initialize_render_schema.py`: exit 0; used
Flask-Migrate's existing upgrade, no stamping, create_all, reset or new revision.
Completed 20:37:03 UTC. Post-upgrade read-only inventory: matching sole head,
no missing model tables/columns; user/company/employee/payroll_run/payslip and
login_attempt counts all zero before the hosted smoke check. Temporary local
keys initialized model types only; Render keys/configuration were not changed.

`python -X utf8 local-evidence/check_render_login.py`: initial sandbox URL error,
then authorized external-network retry exit 0. Actual hosted HTTP evidence:
login GET 200; one randomized nonexistent login with real CSRF/session POST 302
to `/auth/login`, final GET 200 containing `Invalid credentials.`; registration
GET 200. This creates one ordinary failed-login record, not an account or payroll.
Successful owner authentication is not claimed: local trial credentials do not
exist on Render. Use hosted registration for a separate test account, or the
local trial URL for the already-tested synthetic account.

Reused earlier focused disposable-PostgreSQL evidence:
`3 passed, 6 warnings in 11.09s`; no expensive suite rerun. Ruff check/format and
diff checks pass for the diagnostic/documents slice. Raw ignored evidence:
`render-history-investigation.json`, `render-default-database.json`,
`render-initialization-receipt.json`, `render-initialization-migrations.log`,
`render-login-smoke.json`. Table/column inventory does not certify every type,
constraint, encryption value or money path. Deployed SHA/startup verification,
false-positive readiness, practitioner acceptance and release guarantees remain
open; no app deployment, feature expansion, PR or merge in this recovery.

### Render database identity / empty-schema receipt - 2026-10-04

User saved the database External URL and web service DATABASE_URL in ignored
local files. A private comparison returned true for database name, user, cluster
host, port and password; neither URL nor password was printed or committed.
Successful database-enforced read-only inspection of
`ethiopian_payroll_db_kn8y` returned: schema `public`, search path `"$user", public`,
no non-system tables, no recorded Alembic revisions, and all 38 registered model
tables missing. Inventory exit 1 denotes this real schema mismatch, not a
connection failure. Expanded CLI identity/catalog output confirms this is not
only one missing login table or a table located in another schema.

Existing source graph has 77 revisions and sole head `f4a5b6c7d8f3`. Its real
empty-PostgreSQL upgrade is already exercised by the focused disposable-DB
fixture: `3 passed, 6 warnings in 11.09s`. The local synthetic DB inventory
matches that head with no missing model tables/columns. The separate first
identity probe produced no result due to a native process exit; only the
successful expanded inventory is used as identity evidence.

Proposed repair: apply the existing Alembic upgrade to the confirmed empty
Render target, then rerun the inventory and verify hosted login rejects unknown
credentials normally. This initializes schema; it neither creates the local
trial owner in Render nor restores historical records from an older database.
No production writes have occurred. Await explicit approval for initialization;
deployed commit, startup settings and the misleading readiness route remain open.

### Render login incident / initial diagnosis - 2026-10-04

Confirmed from user-provided traceback: `UndefinedTable: relation "login_attempt"
does not exist` during the lockout query, before credential validation. Existing
migration `b8c9d0e1f2b4` creates that table and its indexes. Missing schema,
connection/schema selection or recorded-revision drift requires investigation;
the exact deployment and historical cause are unidentified. Current Dockerfile
stops on migration failure; this does not prove Render used that startup command.

Related verified source defect: `/readyz` interprets Flask-Migrate's print-only
`current()` result as migration evidence and still returns 200 for unknown state.
The earlier observed hosted response was database up / migrations unknown.
That is connectivity evidence, not complete schema readiness. This route has
not been changed or deployed in this diagnostic slice.

Prepared locally: `scripts/check_deployed_schema.py`, with real
PostgreSQL regression cases in `tests/test_pg_schema_inventory.py`. The inventory
uses a database-enforced read-only transaction, compares source/recorded heads
and all registered model tables/columns, and prints no credentials or row data.
It does not certify types, constraints, encryption or historical data.
Local synthetic DB: sole head `f4a5b6c7d8f3`, no missing model tables/columns.
Final focused PostgreSQL receipt: `3 passed, 6 warnings in 11.09s`; missing table and
missing column were simulated only in a generated disposable DB and rolled back.
Ruff check/format pass. Raw receipt: `local-evidence/schema-inventory-tests-final.log`.
The browser connector cannot access Render due to a request-header-policy error;
there is no configured Render API credential. User was given one read-only
Render Shell command, but confirmed their Free service has no Shell access.
Alternative: external PostgreSQL connection from this computer. Private URL
will stay ignored in `local-evidence/render-database-url.txt`; local wrapper
uses TLS, a connection timeout, temporary model-only keys and read-only SQL.
No production encryption key or payroll row data is required. Await that URL
and deployment/migration completion evidence. No production
DDL, reset, stamp, credential rotation, merge or deployment was performed.

### Persistent founder trial receipt - 2026-10-04

Scope: `scripts/founder_trial.py`, `START_FOUNDER_TRIAL.ps1`, the founder guide
and evidence documents. No application, calculator, authorization, schema or CI
workflow changed. Starts only on 127.0.0.1:5058, with a uniquely named/marked
synthetic database on the existing local PostgreSQL instance. Inherited live
integration settings are removed in this dedicated process. Generated account
password, session/encryption keys and PDFs stay ignored in
`local-evidence/founder-trial`. Restart never drops/reseeds or auto-migrates.

Executed with the locked Python environment:

- `python -X utf8 scripts/founder_trial.py init`: exit 0; real empty-PostgreSQL
  upgrade to sole head `f4a5b6c7d8f3`. Repeated `init` preserved state and data.
- `python -X utf8 local-evidence/check_founder_trial.py`: exit 0; normal owner
  and accountant login, rejected CSRF-less login without an authenticated
  session, encrypted bank readback, worksheet save/reload and unchanged keys
  across a new app instance. Prior approved net 9,260.00; current estimate
  11,053.99. Current month remains unapproved; payment pending. Existing friendly
  CSRF handling redirects with 302; that response is not successful login.
- Cached Playwright CLI: normal accountant login and worksheet at 1440x900 and
  390x844. Phone page width 390 equals viewport. Screenshots in `docs/evidence`.
  No new packages installed. Its first credential helper was incompatible;
  successful replacement kept credentials/output in ignored local files.
  A stale login form expired; refreshing it allowed normal browser sign-in.
- Ruff check/format check on the launcher: pass. Source preflight: 77 revisions,
  one head, no known source findings (not full security proof).
- Independent narrow review caught HTTPS/cookie forcing in the local launcher;
  browser reproduced it. Fixed only that loopback app's transport settings,
  retaining login, CSRF, CSP and authorization. Re-review found no blocker.
- `powershell -NoProfile -ExecutionPolicy Bypass -File START_FOUNDER_TRIAL.ps1`
  restarted the preserved trial. Full suites were not rerun: merged application
  source is unchanged; exact-main hosted evidence remains above.

This is a machine-local, current-month exercise, not deployment or practitioner
acceptance. Incomplete setup stops for recovery; no destructive reset command
exists. [Current founder guide](docs/FOUNDER_TRIAL.md) contains the next action.

### PR #11 merge receipt - 2026-10-04

[PR #11](https://github.com/vouge2017/ethiopian_payroll_engine/pull/11) is merged.
The clean working checkout was fast-forwarded to the verified merge object.
An initial fetch updated FETCH_HEAD but left the old origin/main tracking ref;
the exact fetched SHA was verified before fast-forward, then origin/main was
explicitly refreshed. No old files were restored/deleted from the stale ref.
Source tree equality against `6eb7fd1` was verified. No tests were rerun locally.
Completed PR receipts are in `local-evidence/pr11-final-{python311,python312,postgres}.log`.

This follow-up updates only the three status/report documents. It is published
on the existing feature branch with `[skip ci]` to avoid repeating suites for
documentation alone; it does not change remote main, tested source, schema or
workflow. Historical unmerged/pending statements below describe their original
checkpoint and are superseded by this current summary.

### Bounded review follow-up - 2026-10-04

Remote main is still `9670a92487c705a6614e3c6df67aff24d29c7bcf`. Existing CI on
`9f0f4a3` remains green; no expensive local full-suite rerun was performed.
No monthly PR is open; PR #7 is the separate unfinished mobile redesign.

Independent review found misleading BLOCK/comparison-error success messages and
retained recovery changes described as unchanged by the API/cockpit narrative.
Both were reproduced and repaired; payroll absence now says Absent from payroll,
not Departures. Pending approval is labeled Waiting for owner approval.
No arithmetic, authorization, migration or approval-write behavior changed.

Before fixes: `2 failed, 1 passed, 5 deselected, 10 warnings in 13.61s` (PG UI);
`2 failed, 30 deselected, 4 warnings in 2.10s` (narrative).
An intermediate run exposed that existing informational issues hid the attention
banner: `2 failed, 72 passed, 20 warnings in 41.33s`; the banner is now independent.
Final: `74 passed, 20 warnings in 47.54s` across `test_pg_monthly_journey`,
`test_narrative`, `test_change_summary`, `test_error_boundaries`.
Log: `local-evidence/integration-20261004-064246-831510.log`.
Ruff passes; `231 files already formatted`. Independent fix review found no
remaining blocker in the four changed source/test files; this is bounded review,
not a fresh whole-repository security or statutory certification.

Installed cached Playwright CLI verified the synthetic BLOCK page at 1440/390px:
DOM/page width equaled viewport, approval unavailable, correct blocker count,
no false all-checks-passed text or Continue control. Screenshots are in
`docs/evidence/review-blocked-{desktop,phone}-2026-10-04.png`.
The browser connector failed twice before page access; the first Python fallback
had no installed Playwright package. Cached CLI worked without a new installation.
Browser and loopback preview are stopped; the preview used its own disposable DB.

Working guidance is now in AGENTS.md and linked from README.md. A local-only
AGENTS.md at the outer workspace directs future sessions here and preserves
unfinished mobile work. No user files were deleted or moved.

**Next:** publish/read new-commit CI, obtain the missing PR/GitGuardian evidence,
then prepare a stable synthetic founder/Tigist trial. Opening a PR, merging and
deploying remain separate authorization steps. New follow-up hosted CI is not
covered by the older `9f0f4a3` receipt above. Policy and release gates remain open.

### Monthly slice completion - 2026-10-03

Prepared on the review branch, unmerged and undeployed. Repaired the obsolete CI
test contracts; closed individual PDF, worksheet Undo and completed-review label
defects; connected existing change summary to frozen review and earlier approved
regular payroll. Existing exceptions and saved checker findings are visible.
No new policy thresholds, statutory math, migrations or correction categories.

Affected result: `136 passed, 104 warnings in 80.49s (0:01:20)`.
Final recheck: `57 passed, 20 warnings in 20.60s`. Counts overlap.
Ruff passes; `231 files already formatted`. CSRF-enabled accountant/owner browser
journey verified on desktop and 390px; saved phone review width 384 <= 390.
Downloaded PDF/bank both contain net 11,053.99; payment remains Pending.
Implementation `9f0f4a3e1613cb36a2eb14bced55915b8827982b` is pushed.
Hosted PostgreSQL: `128 passed, 286 warnings in 69.69s (0:01:09)`; empty-database
migration and rollback/rollforward passed. Hosted lint/format and strict security/
tenant gates on both Python versions passed. Full Python 3.11 and 3.12 each:
`TOTAL: 1561 passed, 0 failed, 0 errors, 124 skipped`.
[All four branch CI jobs passed](https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/37130741492).
No GitGuardian check is attached to this implementation SHA. These receipts
belong to `9f0f4a3`; the later documentation-only receipt commit changes no
tested source, tests, migrations or workflow and does not rerun the same CI.

[Scope, receipts, policy/release limits and founder/Tigist scripts](docs/MONTHLY_PAYROLL_JOURNEY_2026-10-03.md).
STOP after this slice; no further work order or practitioner expansion is started.

## Ruff gates and overtime page repair - 2026-10-02

The existing pending cleanup was reviewed and completed on
`feature/elements-architecture`, based on `4b6c8c5`. A real employee-detail bug
was reproduced when the employee had current-month overtime: the route evaluated
`Decimal('1')` without importing Decimal. The module import now repairs that path;
the regression also checks the saved overtime row and its existing rounded pay.
No payroll rate, tax policy or schema revision was changed.

Ruff 0.16.9 now reports `All checks passed!` and `201 files already formatted`.
The earlier 128 findings were at the pushed baseline; the previously pending
cleanup left 41, and this slice closes those 41. Formatting touched 64 files,
with zero AST changes across the 201 checked Python files. No lint rules or gates
were relaxed. Manual import, exception-chaining and row-closure fixes were reviewed
separately. `git diff --check` passes.

Before the route fix: `1 failed, 3 warnings in 16.96s`.
The first expanded run passed 94 other cases but exposed an incorrect expected
rounding value in the new assertion (144.23 rather than the existing 144.24).
After correcting that test expectation, final affected checks:
`95 passed, 19 warnings in 90.69s (0:01:30)`.
Native PostgreSQL checks: `63 passed, 178 warnings in 168.91s (0:02:48)`.
These selections are focused checks, not a full-suite total.

The native target is the newly created disposable database
`payroll_cleanup_20261002_2240`, PostgreSQL 16.6 on `127.0.0.1:55439`.
The real Alembic chain upgraded the empty database; native encryption tests
also exercise affected downgrade/upgrade and preservation guards. Money,
worksheet approval/retry, accounting/register, imports, Diff access and legacy
delivery cases passed. No customer database was used. Windows denied pytest's
temporary-directory cleanup inside the sandbox; the successful complete runs
used authorized execution outside it.

Source preflight reports zero findings, 71 revisions and one head
`f4a5b6c7d8f0`; this is a limited static check. The initial INCOMPLETE result was
resolved by passing repository-local safe-directory configuration to the Git
subprocess, without changing global Git configuration.

Independent review found no remaining blocker in this slice. GitGuardian browser
access still fails to load its request-header policy; the user is handling
incident 37741140. PR #8 still conflicts with main `aa2e657` in 75 files.
No integration, deployment or production-readiness claim is made here.
[Evidence](docs/evidence/cleanup-2026-10-02.json).

## PR #8 security finding and integration blockers - 2026-10-02

GitHub PR #8 is open against the correct repository. Source head `9dc65b3`
was published successfully. GitGuardian incident 37741140 points at the fixed
synthetic pytest encryption default introduced in `2c05019`, not a configured
production credential. `tests/conftest.py` now generates an ephemeral default
only in testing and preserves explicitly configured keys. No production key,
encryption policy, persistent customer data or Git history was changed.

Regression before: `1 failed, 3 passed, 3 warnings in 4.09s`. Focused checks
after: `12 passed, 3 warnings in 5.58s`. The additional encrypted-field run on
the previously used synthetic database returned `3 failed, 16 passed, 39 warnings
in 8.99s`: unrelated retained test rows blocked downgrade to short text columns.
Rerunning on a newly created disposable PostgreSQL database, upgraded through
the actual Alembic chain, returned `19 passed, 54 warnings in 11.78s`. This covers
encrypted employee fields, migration rejection/rollback guards, production
startup policy and the new key-default regressions. Changed test files pass Ruff.

Removing the literal does not erase its earlier commit: GitGuardian scans each
PR commit. The historical incident needs dashboard classification as a test
credential and a check re-run. Browser automation failed to load its request-header
policy; the user was given the exact incident and dashboard action. No broad
scanner exclusion or fabricated successful check was applied.

GitHub Actions run `37018121375` at `6262a17` completed: both Python test jobs
and the PostgreSQL job succeeded; lint failed. Local Ruff 0.16.9 reports
`Found 128 errors.` and `64 files would be reformatted, 137 files already formatted`.
These are current measurements, separate from older lint counts at earlier SHAs.
This security slice does not resolve that existing lint backlog.

GitHub reports PR #8 `mergeable=false`, `mergeable_state=dirty`. A non-mutating
`git merge-tree --write-tree --name-only HEAD FETCH_HEAD` inspection against main
`aa2e657` identifies 75 conflicting files: six migration files, 33 payroll source
files, 29 tests and seven other files. Before this fix the feature branch and main
have 50 and 61 unique commits respectively. Conflicts include tenant constraints,
models, payroll services and migration deletions; choosing an entire side would
discard independently developed work. Main integration needs a separately reviewed
reconciliation, migration proof and passing checks. No merge, rebase, force-push or
deployment was performed. PR #8 remains unmerged and is not production-ready.

## GitHub publication recovered - 2026-10-02 14:13 UTC

The remote URL was already correct: `https://github.com/vouge2017/ethiopian_payroll_engine.git`.
Git Credential Manager had multiple saved accounts and selected `Mayademe1020`,
which GitHub denied with HTTP 403. Selecting the already-saved `vouge2017` account
passed a dry run and the actual push. Repository-local
`credential.https://github.com.username=vouge2017` is now configured in both the
isolated hardening checkout and the original checkout; global credentials and the
original checkout's dirty code were preserved.

All six hardening commits are published to `feature/elements-architecture`.
`git ls-remote` independently verified the remote source head exactly matches
`6262a1713b65da25e14074b6c24f2bff92cb835f`. GitHub access is no longer the push blocker.
No main-branch merge or deployment was performed. Remote CI and remaining production
gates are not claimed verified. This publication note changes documentation only.

## Strict money import slice - 2026-10-02 13:53 UTC

Malformed text, currency-only text, booleans, NaN and Infinity no longer become
zero money. Existing numeric/currency formats and the existing blank-as-zero policy
are preserved. Excel workflow reports numeric row errors. CSV/Excel upload and API
preview now reject every file with row errors before persisting a partial draft or
preview; users must correct the file. Diff shows a row-specific HTTP 400 and creates
no cached result for malformed money.

Before: `11 failed, 13 passed` for parser/workflow/Diff checks; partial-upload
regressions then failed four cases. That negative test also exposed two fixture
cleanup errors from missing preview-table cleanup; the fixture now cleans previews
before its synthetic users. After: `40 passed, 35 warnings in 106.56s` for valid and
invalid native PG CSV/Excel uploads/previews, parser/workflow and Diff checks. Target
is the identified synthetic database, never customer data. New tests and changed
import/payroll source pass Ruff; existing unrelated Diff lint remains open.

Six bounded hardening slices are pushed on `feature/elements-architecture` (publication
recovery above). Remote CI and deployment remain unverified. Remaining
work includes statutory snapshots/classifications, exemption and joining/exit policy,
correction/undo accounting, previous-period checks, results/review UI, practitioner
trial and full production gates. No production-readiness or legal-compliance claim.

## Private Diff authorization slice - 2026-10-02

Comparisons and downloads require a signed-in owner/accountant, use the authorized
active company and bind cached results to the requesting user and company. Anonymous
company lookup is removed. The public landing page remains available. Old cache entries
without ownership are rejected, including same-company entries belonging to another user.

Before: `6 failed, 1 passed` on actual PostgreSQL-backed HTTP requests. After: `25
passed, 17 warnings in 39.05s` for Diff access plus role/isolation checks. Existing
mocked comparison/XLSX tests: `8 passed, 3 warnings in 5.40s`. Native PG checks added
to CI. Source preflight has zero findings and one migration head; this is a limited
static gate, not proof of production safety. Existing unrelated Diff lint remains open.
At this slice's completion the default account lacked push access; publication was
subsequently recovered above. No fixes from this checkout are claimed deployed.

Next: statutory exports must freeze identity, salary and tax classifications;
correction/undo accounting and previous-period validation
must be safe. Browser/founder trial, practitioner policy/chart sign-off, full CI/lint,
worker/storage/key configuration and backup/restore evidence remain release requirements.

## Legacy delivery slice - 2026-10-02

A reproduced PDF queue exception previously returned failure after money committed.
Legacy approval now protects delivery outside the committed money transaction, as
the worksheet path already does. Approval messages say payment is pending.

Before: the new PostgreSQL service regression returned `Synthetic PDF queue outage`.
After: `20 passed, 33 warnings in 92.48s` for delivery, existing PDF and worksheet
journey checks. Final guard verification: `1 passed, 5 warnings in 8.36s`. Independent
PG connection confirms completed status; one payslip, one loan recovery, one completion
audit, no failure audit and a safe HTTP retry are checked. No real payment occurs.
Changed source/tests pass Ruff. Native PG regression added to CI. Durable queue handoff,
correction/reversal accounting and full legacy user journey remain separate open work.

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
At this slice's completion GitHub reported `push: false`; publication was subsequently
recovered using the saved repository-owner account as recorded above.
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

## 2026-10-03 — PR #8 reconciliation

Reconciled feature input `e1d5e37` with restored main `facf818`; recovery PR #9
was already merged at `3f3ae3b`. No restored main files are deleted. The combined
Alembic graph has 76 revisions and one head, `f4a5b6c7d8f2`.

- Final PostgreSQL selection: `93 passed, 262 warnings in 186.20s (0:03:06)`.
- Strict security/tenant and migration gate: `173 passed, 1 skipped, 41 warnings in 205.76s (0:03:25)`.
- Repaired broad-suite file selection: `TOTAL: 199 passed, 0 failed, 0 errors, 2 skipped`.
- Ruff lint and formatting pass. All hosted Python 3.11/3.12, PostgreSQL,
  standalone migration and lint checks passed at `c121558`.
- GitGuardian 37741140 is confirmed as the historical synthetic pytest default;
  owner supplied updated status Ignored / Test credential on 2026-10-03.
  Direct GitHub rerequest returned HTTP 404; this status push triggers a fresh scan.
- PR #8 merge into main and production deployment remain pending.

Full scope, initial failures, fixes and evidence:
[PR8_RECONCILIATION_2026-10-03.md](docs/PR8_RECONCILIATION_2026-10-03.md).

## 2026-10-03 — approved-payroll correction slice

Supersedes the prior pending merge checkpoint: the user merged PR #8 into main
at `9a46f2880188c7bb473bd3ac1c42fd89053bf839`; GitGuardian passed after the owner
classified incident 37741140 as a test credential.

New branch `feature/approved-payroll-corrections` implements evidenced drafts and
explicit owner approval for additional taxable overtime/bonus. Approved originals
are preserved; retained-period tax deltas, source identity, active membership,
atomic audit, concurrency/retries, PDF and bank outputs are verified. New reviews
retain calculation context; missing/ambiguous historical context is blocked.
Migration `f4a5b6c7d8f3` is the sole head of 77 revisions. Original dirty workspaces
remain unchanged.

- Affected migration/output/approval checks: `118 passed, 132 warnings in 142.72s (0:02:22)`.
- Final correction selection: `39 passed, 5 warnings in 97.16s (0:01:37)`.
- Intermediate security/correction batch: `1 failed, 121 passed, 12 warnings in 162.44s (0:02:42)`;
  its sole failure was a new test mocking nonexistent enqueue_pdf, fixed and
  rechecked in the final correction selection. Counts overlap; not a full-suite total.
- Ruff passes; `230 files already formatted`. CSRF-enabled desktop/phone synthetic
  draft-to-approval journey verified; no phone page overflow.
- Branch publication/hosted CI are separate from these local checks. No merge,
  production migration or deployment performed for this slice.

Scope, logs and screenshots:
[PAYROLL_CORRECTIONS_2026-10-03.md](docs/PAYROLL_CORRECTIONS_2026-10-03.md).
## Priority Override review and stop - 2026-10-03

The latest user instruction is reconciliation only, then STOP. This supersedes
automatic continuation into later work orders. No new product code was changed
in this review.

Both `c2b636f` recovery and `e1d5e37` hardening are ancestors of merged PR #8
`9a46f2880188c7bb473bd3ac1c42fd89053bf839` (ancestry commands exit 0).
The reconciliation is complete and published; no repeat merge is required.
Hosted checks re-read today at that SHA: lint, Python 3.11/3.12, PostgreSQL,
standalone migrations 3.11/3.12 all success.

Recorded local receipts, not rerun for this documentation-only review:
`93 passed, 262 warnings in 186.20s (0:03:06)`;
`173 passed, 1 skipped, 41 warnings in 205.76s (0:03:25)`;
`TOTAL: 199 passed, 0 failed, 0 errors, 2 skipped` (repaired selection).
Selections overlap. Reconciliation: 76 revisions, sole head `f4a5b6c7d8f2`.

Actual remote main is `9670a92487c705a6614e3c6df67aff24d29c7bcf`, after PR #10
merged later correction work `90779cb`. Its head is `f4a5b6c7d8f3` (77 revisions).
Current main lint, PostgreSQL and both standalone migration checks pass; full
Python 3.11/3.12 remain running at this checkpoint. These are separate from the
fully passed reconciliation checks. No deployment was performed.

Preservation, resolved conflicts, exact test selections, receipts and limits:
[reconciliation review](docs/PR8_RECONCILIATION_2026-10-03.md#priority-override-review-and-stop-checkpoint---2026-10-03).
Later work is on hold pending review; do not interpret previous next-order text
as authorization to continue.
