# Accidental main-tree recovery

This branch recovers the pre-deletion application without rewriting history.
It is a reviewed source-recovery candidate, not a deployment-ready release.

## What happened

Main commit `aa2e657736a572dc4bc51bc3cd9140682aef4c25` changed 612 files,
adding 7,947 lines and removing 156,348. Its message describes an onboarding
fix, but the tree replaces most of the application with a smaller snapshot.
It also introduces a mode-160000 Git link named `ethiopian_payroll_engine`
without a `.gitmodules` definition. A Git link records a repository commit
reference, not the nested source files.

These facts are consistent with staging a mismatched checkout/snapshot and
an unintended nested repository. Git does not record the command or tool
that caused this, so the exact cause is unconfirmed. The user explicitly
confirmed that the deletions were accidental and requested restoration.

## Recovery scope

The source is main's preceding commit
`1ff33d18fd48563d408ea8f9088d42414d296733`. The index inventory in
`docs/evidence/main-recovery-2026-10-02.json` verifies:

- 445 previously deleted files recovered into the commit candidate.
- 37 deleted migration files recovered, for 55 migration files total.
- 572 parent files unchanged byte-for-byte in Git.
- Five deliberate differences: `.gitignore`, membership model/factory,
  membership regression tests and the tenancy inventory's user-scoped
  membership exception.
- No unexpected missing or modified parent files, no Git links and no
  tracked Python bytecode.

The 19 recovered private/generated artifacts (a payroll reference CSV,
17 generated screenshots and a terminal log) remain on disk under their
original paths. They are ignored and excluded from this new commit;
the preceding Git history also preserves them. No user checkout was reset.

The legitimate onboarding fix remains: `UserCompany` uses ordinary queries
because discovering a user's memberships must work before selecting an
active company. Queries remain explicitly user/company scoped at call sites;
the company-switch route still verifies the requesting user's membership.
Other tenant model registrations remain unchanged. The restored parent
already contains the phone prefix layout; no additional phone-padding patch
was identifiable in `aa2e657`.

The independently tested feature branch remains at
`e1d5e375919af18d32c896dff646548198b0597a`. Its GitHub CI run
`37056391715` completed successfully. It is not replaced by this recovery.
It must subsequently be integrated into this restored tree in bounded
steps: copying its entire tree would discard main-only onboarding/profile,
auth recovery, admin/support, cron/idempotency, Excel payroll, adjustments,
month-close and frontend work.

## Validation and limits

Python 3.12.13, PostgreSQL 16.6 and Ruff 0.16.9 were used locally.

The new membership-discovery regression failed before the narrow fix:
`1 failed, 5 passed, 4 warnings in 10.87s`.

After the fix, the onboarding/role/tenant selection reported
`1 failed, 64 passed, 5 warnings in 43.53s`; the remaining failure was the
restored support-model inventory check. A broader selection including auth
layout, payroll/services and integration fixtures reported
`2 failed, 125 passed, 1 skipped, 1 deselected, 5 warnings in 62.06s (0:01:02)`.
The inventory check was run separately and remains failing; it was not
weakened to exclude the support models.

All three remaining failures reproduce from an untouched Git archive of
the pre-deletion parent: `3 failed, 4 warnings in 8.78s`:

1. SupportTicket and SupportTicketMessage are not in TenantQuery's registry,
   despite the inventory expectation. Platform support routes intentionally
   query across companies; blindly registering them would break those
   routes. Explicit platform handling and tenant support isolation evidence
   are required before resolving this check.
2. Two unchanged integration fixtures construct Payslip without its required
   `company_id`, producing NOT NULL failures.

Fresh Alembic upgrade was attempted only against a verified empty, disposable
loopback PostgreSQL database, `payroll_recovery_20261002_2305` on port 55439,
owned by the synthetic `payroll_test` role. It fails before migration because
the restored graph has two heads: `a9b8c7d6e5f4` and `zz1a2b3c4d5e`.
No stamping, schema recreation or production connection was used.

Source preflight reports six inherited findings: multiple migration heads,
swallowed CI rollback failures, three missing CI encryption-key settings,
and a test-runner exit predicate that ignores failed processes. The full
restored tree has not passed the feature branch's release gates. Browser
rendering and deployed schema/SHA/key compatibility remain unverified.

The membership regression passes Ruff. Git whitespace checks against the
pre-deletion parent pass. Full-history backup
`local-evidence/payroll-before-recovery.bundle` verifies successfully and
includes both the accidental-main and tested-feature histories. Raw test
and PostgreSQL logs, plus the untouched parent archive, are local and ignored.

## Next integration gate

Preserve this recovery snapshot, then reconcile migrations against the
actual deployed revision/schema before bringing in the tested feature work.
Avoid duplicate compliance-deadline migrations and overlapping bank/TIN
encryption migrations. Check the parent payslip-uniqueness revision's
dependency on `payslip_type`, repeated adjustments, missing platform/support
table migrations, populated webhook-secret encryption and legacy phone
formats. Require fresh and data-bearing PostgreSQL upgrades plus rollback
proof for the resulting unified graph. Keep approved worksheet snapshots,
transaction/audit boundaries and recoverable PDF delivery from the feature.

Main has not been merged or deployed by this recovery operation.
The outer mobile checkout's local `.git/info/exclude` now excludes the
`payroll-production-work` and `payroll-main-recovery` directories, preventing
ordinary staging there from recording these work checkouts as nested Git links.
