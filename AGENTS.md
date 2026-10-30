# Payroll working guidance

Read `PLAN.md` before doing anything; then read `PROJECT_RULES.md`, the current
summary at the top of `STATUS.md`, and `docs/WORK_ORDERS.md`. Later explicit user
instructions determine active scope.

- Confirm the Git root, branch, HEAD, upstream and dirty state. Use explicit
  `git -C <repo>`; `safe.directory` does not select a repository.
- The designated working checkout on this machine is
  `D:\ethiopian_payroll_engine\payroll-pr8-integration`. Remote `main` is the
  accepted baseline; a tested feature branch is not automatically merged.
  Preserve the outer mobile checkout and other recovery/correction worktrees.
- Deliver one bounded user outcome. Do not repeat accepted PR #8/#10 work,
  reopen calculator policy, redesign UI or begin another work order by default.
- Use `payroll-production-review` for money/security/release work, code review
  before recommending a merge, browser tooling for changed screens, and PDF/
  spreadsheet skills when checking those artifacts. Use relevant capabilities;
  do not load every skill, add redundant connectors or install tools by default.
- Reuse completed hosted evidence attributable to the exact tested SHA. Run
  focused regressions for new changes. PostgreSQL/Alembic proof is required for
  applicable money/schema guarantees; SQLite and `create_all()` are not proof.
- Preserve statutory arithmetic, tenant authorization, approved historical facts
  and single-consumption behavior. Do not choose business thresholds silently.
- Commit only the verified slice. Standing work orders allow feature-branch
  pushes; opening PRs, merging, force-pushing and deploying require explicit
  authorization. Never delete user work to make a checkout clean.
- Keep the current status summary concise and historical receipts unchanged.
  Handoffs distinguish implemented, locally tested, hosted tested, merged,
  deployed and practitioner accepted. Include SHA, checks, open limits and next
  action. Report browser/tool failures as limitations, not successful checks.

## Audit follow-through guardrails

- Read `PLAN.md` before starting its proposed follow-up work; it is a prioritized
  plan, not blanket authorization to edit, deploy, create users, change secrets,
  invite testers, push, merge or contact external parties. Preserve the local
  `main` audit baseline and identify its SHA/remote relationship before acting.
- Treat company membership, effective role, tenant scope and target-record
  ownership as separate checks. Company-wide salary, payslip, tax-ID, bank,
  accounting, audit and payroll-review data must not be exposed to employee-role
  users; employee-facing reads must be constrained to that employee's own rows.
  Test session and API-token paths, including revoked/stale membership and keys.
- Do not alter Ethiopian statutory calculations based only on old notes, code
  comments or secondary summaries. Record the primary law/directive, effective
  date, assumptions and practitioner sign-off. Keep unresolved PAYE/pension
  ordering, transport/per-diem rules, casual-worker scope and overtime overlap
  explicit; never silently choose a threshold or use the 208-hour divisor as law.
- Stop a requested test run at its first failure. Preserve the exact command and
  failure; do not patch, mask or rerun it without authorization. Keep any live
  browser/E2E test out of normal pytest collection. The existing `scripts/e2e_test.py`
  targets the Render URL and includes registration, so run it only against an
  explicitly approved, isolated disposable target with synthetic data.
- Never display, log, commit or copy production credentials, secret values,
  employee PII or real payroll into test evidence. Use synthetic data and a
  disposable PostgreSQL database for authorized checks. Treat `/tmp` artifacts,
  worker readiness, backup/restore and key recovery as unproven until exercised
  for the exact SHA/deployment.
- For this audit's plan, local `main` is `3605c9e4` and was three commits behind
  `origin/main`; that finding does not authorize a pull, merge, branch change or
  implementation against an unreviewed SHA.

## Owner workflow rules for future AI sessions

- `PLAN.md` is the single project plan. Work only on the task the owner places
  in `Now`; proposed `Next` items and `Parked ideas` are not approval. Put new
  findings in `Parked ideas`, never directly into code or an unapproved workstream.
- Respect the exact files the owner permits for each task. A read-only or
  documentation-only audit must not change application code, tests, configuration,
  database contents, deployment settings or production state.
- Use `Decimal` for monetary calculations, state rounding explicitly, and add
  or update regression tests for each authorized change. Run the required suite;
  at the first test failure, preserve the command/result and stop as directed.
- Do not create accounts, log in as a user, use production credentials, access
  employee PII, or submit payroll/tax/bank instructions unless the owner has
  explicitly authorized that exact external action and its target.
- Never commit secrets. Never push to `main`; use a named feature branch. Before
  finishing an authorized task, update `Status` and the one-line `Log` in
  `PLAN.md`, commit only the verified authorized files, and push that feature
  branch when the current task authorizes publication. Do not open a PR, merge,
  force-push or deploy without separate explicit authorization.

Human decisions still needed: founder/practitioner acceptance, unresolved payroll
policy, new external access/spending and production-release authorization.
