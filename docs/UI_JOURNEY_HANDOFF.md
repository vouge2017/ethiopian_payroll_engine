# Preparation to review — local UI handoff, 2026-10-05

The real application now provides a compact preparation ledger on desktop,
labeled employee inputs on phones, and a review that puts preserved amounts,
findings, previous-payroll changes and the next permitted action in a consistent
order. One explicit Save & recalculate action saves all canonical inputs through
the existing backend. Unsaved edits disable review and warn before navigation.
Opening an existing review preserves its amounts; refreshing remains explicit.

Checkout: `D:\ethiopian_payroll_engine\payroll-pr8-integration`.
Branch: `codex/monthly-payroll-ui`.
Baseline HEAD: `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`.
Delivery state: uncommitted local patch; no PR, merge, deployment or practitioner
acceptance. The separate readiness branch and outer mobile work are preserved.

## Design references and implementation

[Taste](https://www.tasteskill.dev/docs) and
[Impeccable](https://impeccable.style/docs/) informed preservation of existing
behavior, simpler hierarchy, clearer wording, phone adaptation and hardening.
Neither package was installed. This is application HTML/CSS/JavaScript using
existing fonts and tokens; it adds no generated image assets or model integration.
The locked QA dependencies were installed with npm ci; no manifest/lock changes.

- Preparation: `payroll_spreadsheet.html`, new `monthly-payroll.css` and
  `monthly-payroll.js`. Same form field names, server validation, CSRF and routes.
- Review: `payroll_review_workspace.html`. Preserved employee amounts, grouped
  case-sensitive employee changes, expandable successful evidence and visible
  blockers/errors. Owner/accountant actions retain their existing conditions.
- Confirmation: `payroll_confirm.html`. Phone totals, the same step structure,
  return-to-review link and no automatic jump past the summary to the password.
- Repairs: mobile card table minimum widths/wrapping; dashboard preparation
  links including their producers; Help question/answer serialization/search;
  accurate Net pay, Approved and Payment pending wording; no repeated confetti.
- Shared navigation: ordinary navigation semantics, readable sidebar contrast,
  accessible notification label and employee filter labels.
- Regression tests: `test_pg_monthly_ui.py`; existing persisted-value worksheet
  test adapted to employee cards without weakening its amount assertions.

## Verification receipts

Real PostgreSQL was upgraded through all 77 Alembic revisions to
`f4a5b6c7d8f3` in uniquely generated disposable databases. These are overlapping
focused runs, not a summed full-suite count:

```text
40 passed, 86 warnings in 79.01s (0:01:19)
11 passed, 22 warnings in 39.23s
3 passed, 6 warnings in 10.63s
```

The 40-test run covers inputs, preserved review/refresh, role/tenant access,
repeated/concurrent saves and approvals, stale balances, audit/queue failures,
and persisted amounts agreeing with PDF and bank CSV. The 11-test follow-up
checks final confirmation/comparison/link changes; the final 3-test run adds
the independently identified EMP1/emp1 grouping regression. Warnings are existing
Alembic/Flask-SQLAlchemy deprecations. Earlier sandbox temp-access errors, stale
table-row assertions and collection-name mistakes are superseded by these runs.

Playwright checked preparation and review at 1440, 1280, 1200, 1150, 1100, 1024,
900, 768, 390 and 360px, plus Employees, dashboard and Help at 360px: 23 layouts,
no page overflow, zero axe violations in the checked areas and zero page errors.
It exercised dirty/reverted edits, keyboard focus, actual save/reload, preserved
review, explicit refresh, accountant submission, owner password confirmation,
approval and real PDF/CSV downloads. A separate saved-BLOCK fixture kept the
finding visible and denied both accountant submission and owner approval.
Final confirmation fits 360px and opens at the summary; a full-page preparation
axe scan also passed. These checks do not certify accessibility compliance.

Authenticated Lighthouse measured preparation and review on desktop and mobile;
all four accessibility and best-practices category scores reached 100. Local
performance ranged 78–100 in the final recorded run. CDN/font loading, compression
and rendering costs remain performance follow-up areas. These are development
server lab scores, not deployed performance or a design/market ranking.

Stylelint passed for both changed stylesheets; Ruff check and format check passed
for all six changed Python files. JavaScript syntax and git diff whitespace
checks passed. Source preflight reported zero findings and a single migration
head; that limited source check is not a release/security certification.

Local evidence: `local-evidence/monthly-ui/report.json`, `blocked-report.json`,
`confirmation-report.json`, `lighthouse-summary.json`, Lighthouse HTML/JSON,
desktop/phone PNGs and synthetic PDF. These ignored files contain synthetic data.
The loopback-only disposable preview launcher and audit runners are in
`local-evidence/preview_monthly.py`, `monthly-ui-qa.cjs`, `monthly-lighthouse.mjs`
and `run_monthly_ui_tests.py`; none is a production authentication entry point.

## Next acceptance step

1. Observe founder/Tigist preparing the synthetic month on a real phone and web:
   enter changes, save, identify what was preserved, refresh deliberately, submit,
   approve and download. Record hesitation, errors and assistance rather than
   giving hints during the attempt.
2. Address the observed friction and check larger employee lists, supported
   language rendering and the actual phone keyboard/network.
3. Identify the reviewed commit/build and obtain the existing rollout decision;
   hosted checks, deployed SHA/readiness, restore and practitioner acceptance
   remain separate gates. No rollout has been performed by this UI work.

Current design judgment for this changed journey: approximately 7/10, with 8/10
as a target after observation and refinement. This is a subjective design
assessment, not a whole-platform maturity score or measured competitor ranking.

The existing locked QA dependency install reported 33 advisories (17 moderate,
16 high). No automatic upgrades were made; tool dependency remediation remains
separate from this UI patch.
