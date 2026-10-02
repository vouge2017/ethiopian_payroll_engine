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
`TEST_DATABASE_URL` retains PostgreSQL for actual migration tests. Fresh hosted
results remain to be checked after this workflow correction.

GitGuardian's automatic scan reran on `110d670` and reported one finding; incident
classification remains pending in the owner dashboard.

## GitGuardian and remaining release limits

GitHub check `111002037835` still reports one finding and explicitly links incident
**37741140**, `tests/conftest.py`, and historical commit `2c05019`. Its workspace is
**685067**:

https://dashboard.gitguardian.com/workspace/685067/incidents/37741140?occurrence=300164515

The current test file generates an ephemeral missing test key. The historical
synthetic value remains in Git history. The accessible Mayademe1020 workspace
933702 has no source integration or membership in the incident workspace. The
owner signed in using another Chrome profile, outside the connected browser.

The owner supplied the incident page: it identifies the testing-only synthetic
default, its removal in `4b6c8c5`, three historical occurrences and zero files
requiring a code fix. Its status remains **Triggered**, so classification is
still pending.

Owner action: choose **Ignore → Test credential**,
then rerun the GitGuardian check. A source push triggers a fresh scan too, but a
scan alone does not classify the historical incident. Do not install another app,
erase `tests/conftest.py` from history, or force-push as a first response.

This reconciliation does not close the previously documented payment/adjustment
business gaps, finish the separate worksheet UI work, prove production deployment
or restore readiness, or authorize merging PR #8 into main. Those are distinct
from resolving its code conflicts and proving the combined migration graph.
