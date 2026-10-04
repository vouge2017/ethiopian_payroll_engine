# Payroll working guidance

Read `PROJECT_RULES.md`, the current summary at the top of `STATUS.md`, and
`docs/WORK_ORDERS.md`. Later explicit user instructions determine active scope.

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

Human decisions still needed: founder/practitioner acceptance, unresolved payroll
policy, new external access/spending and production-release authorization.
