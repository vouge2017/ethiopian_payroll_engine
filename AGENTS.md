# AGENTS.md — rules for every AI session

## Start and finish (mandatory)

1. **Read `PLAN.md` first.** It is the single source of truth. When any other doc
   (STATUS.md, TODO.md, ROADMAP.md, WORK_ORDERS.md, old audits) disagrees with it,
   `PLAN.md` wins. Read older docs only for history.
2. **Work only on the task in `PLAN.md` → "2. Now".** If Now is empty or says
   "proposed — owner to confirm", ask the owner before you start. A later explicit
   instruction from the owner can change the task.
3. **New ideas go only in `PLAN.md` → "4. Parked ideas"**, one line each with a
   reason. Do not start them. Do not create new planning, audit, status or summary
   `.md` files.
4. **Money is `Decimal`, never `float`.** Quantize to 0.01 with `ROUND_HALF_UP`,
   rounding once at the end of each step. Money columns are `Numeric(12,2)`.
5. **Every change comes with tests.** Add or adjust focused tests, then run the full
   suite before you finish (`python3 run_tests.py --continue`, or
   `python -m pytest`, never a bare `pytest`). Record the exact summary line.
6. **Never commit secrets.** That covers keys, passwords, connection strings,
   `.env` files, DB dumps with real data and tokens. Use environment variables.
   Test values must be obviously fake.
7. **Never push to `main`.** Work on a branch (`fix/…`, `feat/…`, `docs/…`).
   Opening PRs, merging, force-pushing and deploying need the owner's explicit
   go-ahead.
8. **Before finishing:** update `PLAN.md` → "1. Status" (what changed, test
   numbers, branch and SHA) and add a line to "5. Log" (date, who, what). Then
   commit and push your branch.

## Working rules (kept from earlier guidance)

- Confirm the Git root, branch, HEAD, upstream and dirty state before working.
  Use explicit `git -C <repo>`; `safe.directory` does not select a repository.
- Remote `main` is the accepted baseline. A tested feature branch is not
  automatically merged.
- Owner's local machine only (ignore elsewhere): the owner's Windows checkout is
  `D:\ethiopian_payroll_engine\payroll-pr8-integration`. Preserve the owner's
  other worktrees and recovery checkouts there.
- Deliver one bounded outcome per session. Do not redesign the UI or start
  another task by default.
- Use code review before recommending a merge. Check changed screens in a
  browser. Use PDF/spreadsheet tooling when checking those artifacts. Report
  tool failures as limitations, not as passed checks.
- PostgreSQL/Alembic proof is required for money and schema guarantees. SQLite
  and `create_all()` are not proof. Reuse hosted CI evidence only when it is tied
  to the exact tested SHA.
- Preserve statutory arithmetic, tenant authorization (every query scoped by
  `company_id`, role guards on every endpoint), approved/locked historical
  payroll facts and single-consumption behaviour. Do not choose business or
  legal thresholds silently. If a payroll rule is unclear, park it in `PLAN.md`
  and ask.
- Commit only the verified slice. Never delete user work to make a checkout
  clean.
- Handoffs say which of these states each change has reached: implemented,
  locally tested, hosted tested, merged, deployed or practitioner accepted.
  Include the SHA, the checks run, open limits and the next action.

Human decisions still needed: founder/practitioner acceptance, unresolved payroll
policy, new external access or spending, and production-release authorization.
