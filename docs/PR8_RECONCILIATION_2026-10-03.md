# PR #8 reconciliation — 2026-10-03

## Scope and pinned history

- Repository: `vouge2017/ethiopian_payroll_engine`; PR #8, `feature/elements-architecture`.
- Feature input: `e1d5e375919af18d32c896dff646548198b0597a`.
- Main input: `facf818f4c02972d6197016c164d7627f183d9d0`.
- Recovery PR #9 was already merged at `3f3ae3ba05c80dae1a176e954086f13974510125`.
- Reconciliation workspace: `D:\ethiopian_payroll_engine\payroll-pr8-integration`, branch `integration/pr8-main-20261003`.

This merges current main into the existing feature history. It does not rewrite
history, force-push, deploy, stamp an unapplied database revision, or delete any
file present in restored main. The original dirty checkout and the feature
checkout's pending status/work-order/worksheet UI changes remain separate.
Review diffs and raw test logs are retained locally under ignored `local-evidence/`.

## Reconciliation decisions

1. Preserve worksheet inputs, payroll snapshots, authorization, Decimal money
   paths, feature migrations and the ephemeral pytest encryption-key fix.
2. Preserve main's progressive registration, password recovery, support/admin
   tools, adjustment service, payroll uniqueness constraint and startup checks.
3. Resolve the duplicate favicon registration and duplicate fixture keywords.
   Preserve the feature's actual PNG favicon and fail-fast migration startup;
   retain Gunicorn's supported `--worker-tmp-dir`, removing unsupported `--tmp-dir`.
4. Keep authenticated HTML out of the service-worker cache. Main's offline page
   caching would expose private payroll pages after logout; static caching and
   push support remain. This is an intentional integrity decision.
5. Preserve legacy phone identities during login and recovery. Canonicalize
   lockout identifiers, reject ambiguous aliases, and prevent registration from
   shadowing an existing leading-zero account. New-registration validation stays
   strict. No existing user's stored phone is rewritten.
6. Register support tickets/messages and worksheet inputs with tenant guards.
   Support administration uses an explicitly authorized cross-company query;
   tenant ticket/message reads include company filters. Membership discovery
   retains the restored user-scoped UserCompany behavior.
7. Adapt old fixtures to both real onboarding steps, the current phone/password
   contract and required tenant arguments. Preserve payroll and security
   assertions. Use a file database for the SQLite thread-race test instead of
   concurrently sharing one in-memory connection. Apply required Ruff cleanup to
   restored source/tests, including unused imports and formatting.

## Combined migrations

The graph contains **76 revisions**, with one head, **`f4a5b6c7d8f2`**.

- `p0f1a2b3c4d5` depends on the revision creating `payslip_type`.
- `j0k1l2m3n4o5` depends on the revision creating `employee.is_deleted`.
- The profiling merge removes redundant parent `z6a7b8c9d0e9`, already an ancestor
  of `e9a0b1c2d3e4`; retaining both broke Alembic version bookkeeping.
- Both historical compliance-column revisions remain. They validate/reuse the
  shared JSON column and retain its data while the other owning branch is applied.
- `f4a5b6c7d8f1` joins feature, profiling and compliance branches.
- `f4a5b6c7d8f2` supplies the four restored support/platform tables, permits the
  tenantless registration state, and moves webhook signing secrets into the
  binary encrypted storage expected by restored main. It preserves the logical
  signing key; ambiguous ciphertext/key mismatches fail before changes commit.
- Downgrade refuses populated support/audit history, tenantless registrations,
  or signing keys that cannot fit the legacy column. Existing employee-encryption
  and saved-worksheet downgrade protections remain.

PostgreSQL regressions use generated disposable databases: fresh installation,
populated feature baseline, populated main baseline, full empty graph rollback,
shared-column ownership, signing-key continuity, wrong-key refusal and support
history preservation. Saved financial amounts are compared before/after upgrades.
These tests do not establish that an unknown deployed database has no duplicate
payslips or ambiguous legacy secrets. Inspect a backup/staging copy before release;
the uniqueness migration must fail rather than delete duplicates silently.

## Validation evidence

The first broad subprocess-isolated local run reported:

`TOTAL: 1471 passed, 36 failed, 37 errors, 98 skipped`

Its failures came from old onboarding/phone fixtures, missing tenant arguments,
the incomplete model registry, startup-command expectations, and the SQLite
thread fixture. The repaired file selection then reported:

`TOTAL: 199 passed, 0 failed, 0 errors, 2 skipped`

The strict security/tenant gate, new phone-compatibility tests and real migration
checks reported:

`173 passed, 1 skipped, 41 warnings in 205.76s (0:03:25)`

The first broader PostgreSQL run reported:

`3 failed, 89 passed, 260 warnings in 195.05s (0:03:15)`

Those three failures were outdated assumptions that a branch rollback has one
version row or that the current head remains the old worksheet revision. Updated
assertions retain the data/type/refusal checks and passed:

`23 passed, 92 warnings in 33.37s`

The final PostgreSQL CI selection, including all six reconciliation cases,
reported:

`93 passed, 262 warnings in 186.20s (0:03:06)`

Raw log: `local-evidence/integration-20261003-023319-018137.log`.

Ruff check and formatting check pass for `payroll_engine/` and `tests/`.
Inherited whitespace in merged main documents is not a code validation failure;
existing document sections were preserved. Hosted CI for the published merge
must be distinguished from these local checks.

### Hosted follow-up

Reconciliation commit `110d67045bab85b60f4f3c45021070a6d2328fc6` was pushed
to the existing PR #8 head. GitHub confirms `mergeable: true`: code conflicts are
resolved. Hosted lint and stylelint passed. The restored standalone Migration
Tests workflow failed before exercising the schema: its unbounded dependencies
selected an incompatible SQLAlchemy/sqlalchemy-utils combination and a missing
psycopg driver. Its dependency installation now uses the same locked requirements
as the passing CI/local environment. Application fixtures use SQLite while
`TEST_DATABASE_URL` retains PostgreSQL for actual migration tests. At workflow
correction `c12155873b853ca602fd8bce4eaa5d421a19a3cf`, all hosted Python 3.11/3.12,
PostgreSQL, standalone migration and lint checks passed.

GitGuardian's automatic scans at `110d670` and `c121558` reported the same historical
finding. The owner subsequently supplied confirmation of **Ignored / Test credential**.

## GitGuardian and remaining release limits

GitHub check `111075344252` reported one finding and explicitly links incident
**37741140**, `tests/conftest.py`, and historical commit `2c05019`. Its workspace is
**685067**:

https://dashboard.gitguardian.com/workspace/685067/incidents/37741140?occurrence=300164515

The current test file generates an ephemeral missing test key. The historical
synthetic value remains in Git history. The accessible Mayademe1020 workspace
933702 has no source integration or membership in the incident workspace. The
owner signed in using another Chrome profile, outside the connected browser.

The owner supplied the incident page: it identifies the testing-only synthetic
default, its removal in `4b6c8c5`, three historical occurrences and zero files
requiring a code fix. On 2026-10-03, the owner supplied the updated Details panel:
**Status Ignored**, reason **Test credential**. Classification is complete based
on that owner-provided evidence; the connected browser still lacks this workspace.

The direct GitHub check-rerequest endpoint returned HTTP 404. Publishing this
status checkpoint triggers a fresh GitGuardian scan; its result must be verified
separately. No history rewrite or additional integration installation is needed.

This reconciliation does not close the previously documented payment/adjustment
business gaps, finish the separate worksheet UI work, prove production deployment
or restore readiness, or authorize merging PR #8 into main. Those are distinct
from resolving its code conflicts and proving the combined migration graph.

## Priority Override review and stop checkpoint - 2026-10-03

The reconciliation requested between recovery `c2b636f` and hardening `e1d5e37`
has already been delivered. Do not repeat the merge or start another work order.
Earlier open-PR statements above are historical checkpoints, superseded here.

### Source line and preservation

`git merge-base --is-ancestor` returned exit 0 for both inputs against merged
PR #8 commit `9a46f2880188c7bb473bd3ac1c42fd89053bf839`. Integration commit
`110d67045bab85b60f4f3c45021070a6d2328fc6` has parents `e1d5e37` and restored
main `facf818`; migration CI repair `c121558` and documentation `49abb22`
followed. Both inputs remain available locally. No source deletion or force-push
was performed. Dirty mobile/webhook work was not incorporated.

| Area | Recovery capability retained | Hardening guarantee retained / resolution |
|---|---|---|
| Schema / models | Profiling, support/platform models, payslip uniqueness | Feature element/worksheet/encryption revisions retained; corrected dependencies, compliance ownership and convergence revisions; real branch-data upgrades |
| Calculation / services | Restored payroll and employee services | Decimal calculation, period context, deduction identities and saved worksheet consumption retained; no statutory-policy redesign |
| Approval / locking | Existing approval and immutable-payroll paths | Saved review approval, locks, atomic audits, loan single consumption, competing approval and rollback tests retained |
| Tenant / authorization | Onboarding and membership discovery, support/admin access | Support and worksheet models registered with tenant guards; explicit authorized admin bypass; active-company and removed-membership protections, including Diff access |
| Encryption | Main webhook signing-key behavior | Binary employee storage retained; webhook storage reconciled to restored model; logical key continuity, wrong-key refusal and rollback safeguards tested |
| Corrections / month close | Adjustment service, routes/screens and month-close service retained | Reconciliation retained these capabilities without declaring their business policies safe; the later correction slice is separate evidence |
| Excel / import | Main Excel-payroll workflow retained | Strict finite Decimal money and atomic invalid-import refusal retained; tenant-protected Diff and saved worksheet remain |
| Outputs | Restored results and delivery routes retained | Approved accounting/register facts retained; legacy committed money survives delivery failure and retry |
| Tests / startup | Main onboarding, recovery and platform tests retained | Assertions adapted to real contracts, not removed; actual PostgreSQL gates, strict security gate, locked migration dependencies, Ruff and fail-fast startup retained |

The strategy was a history-preserving merge with conflict-specific decisions,
not selecting either whole branch. Additional concrete conflicts resolved were
duplicate app registration/fixture arguments, legacy phone aliases and lockout
identity, unsupported startup options, and authenticated service-worker caching.
Private HTML caching was removed to protect payroll data after logout; static
caching remains. Restored screens were retained, not redesigned.

### Acceptance receipts and exact checks

The reconciliation graph at `9a46f28` has **76 revisions, one head
`f4a5b6c7d8f2`**. Fresh PostgreSQL install, populated feature/main upgrades,
financial-value preservation, empty full rollback/upgrade, shared compliance
ownership, encryption continuity/refusal and populated-history downgrade refusal
were exercised through Alembic, not `create_all()` or stamping.

Recorded local results (not rerun during this documentation-only review):

- `93 passed, 262 warnings in 186.20s (0:03:06)`;
  receipt `local-evidence/integration-20261003-023319-018137.log`.
- `173 passed, 1 skipped, 41 warnings in 205.76s (0:03:25)`;
  receipt `local-evidence/integration-20261003-022651-508181.log`.
- `TOTAL: 199 passed, 0 failed, 0 errors, 2 skipped`;
  receipt `local-evidence/repaired-suite-summary.log`. This repaired selection
  followed the initial failures documented above; it is not an independent
  claim that the first broad local run passed. Counts overlap.

Executed hosted commands are pinned in the reconciliation commit's workflows:

```text
ruff check payroll_engine/ tests/
ruff format --check payroll_engine/ tests/
python -m pytest tests/test_migration_chain.py -v
python run_tests.py --continue
```

The strict fail-hard pytest gate selected `test_lockout`,
`test_tenant_isolation`, `test_tenant_bypass_guards`, `test_billing`,
`test_period_and_lock`, `test_usercompany_tenant`, `test_migration_chain`,
`test_security_wave1`, and `test_security_regressions` under `tests/`, with `-q`.

The PostgreSQL `pytest -q` selection was exactly these files under `tests/`:
`test_migration_chain.py`, `test_pg_pr8_reconciliation.py`,
`test_pg_catalog_types.py`, `test_pg_deduction_identity.py`,
`test_pg_encrypted_employee.py`, `test_pg_report_queries.py`,
`test_pg_spreadsheet_inputs.py`, `test_pg_period_absence.py`,
`test_pg_worksheet_journey.py`, `test_pg_accounting_outputs.py`,
`test_pg_published_register.py`, `test_pg_calculation_context.py`,
`test_pg_legacy_delivery.py`, `test_pg_diff_access.py`, and
`test_pg_import_money.py`. These cover worksheet save/review/approval/output,
single-consumption loans, accounting/register integrity, strict imports,
Diff access and delivery failure safety in addition to migrations.

The repaired subprocess selection's saved file logs list: `test_benchmark`,
`test_console_cleanups`, `test_demo_and_template`, `test_error_boundaries`,
`test_impact_whatif`, `test_input_validation`, `test_p0a_tenant_isolation`,
`test_p0d_concurrency`, `test_phone_auth`, `test_profile_changes`,
`test_rate_limiting`, `test_rq_pdf`, `test_security_regressions`,
`test_security_wave1`, `test_startup_gate`, and `test_verification`.

GitHub checks re-read in this review confirm **all six checks success at
`9a46f28`**: lint, Python 3.11/3.12, PostgreSQL, standalone migrations 3.11/3.12.
[CI](https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/37096955402)
and [migration checks](https://github.com/vouge2017/ethiopian_payroll_engine/actions/runs/37096955349).
Fresh GitGuardian success at `49abb22` is a separate prior verified receipt;
no new incident classification was performed in this review.

### Actual current baseline and limits

GitHub main is now `9670a92487c705a6614e3c6df67aff24d29c7bcf`: PR #10 merged
the separately authorized correction commit `90779cb` onto `9a46f28`.
The recovery/hardening reconciliation is therefore already in the authoritative
main source line. Current main additionally contains that later correction
work; it is not the reconciliation-only snapshot. Its graph now has 77 revisions
and head `f4a5b6c7d8f3`. At this review, its hosted lint, PostgreSQL and both
standalone migration jobs passed; full Python 3.11/3.12 jobs were still running.
Do not substitute those incomplete current checks for the completed `9a46f28`
reconciliation evidence.

Production schema/duplicate inspection, deployment SHA, shared web/worker keys,
durable artifacts and restore proof remain release limits. No production-ready
claim follows from this integration. No deployment or rollback was performed.

**STOP:** the user's latest Priority Override supersedes the board's reusable
automatic-continuation instruction. Review this reconciliation result before
starting corrections, late inputs, UI, AI, bank/tax integrations or any later
work order. This checkpoint changes documentation only.
