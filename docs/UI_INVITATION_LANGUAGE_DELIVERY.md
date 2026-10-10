# Invitation and critical-language continuity — 2026-10-09

Local, uncommitted work in `D:\ethiopian_payroll_engine\payroll-pr8-integration`,
branch `codex/monthly-payroll-ui`, baseline HEAD
`2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`. Earlier and concurrent dirty work,
including outer mobile work, is preserved.

## Delivered outcome

The employee invitation is now a deliberate public, token-only account creation
route. Employee management remains authenticated. A valid, unexpired, unused,
non-deleted employee invitation can create exactly one employee-scoped account;
the server ignores submitted company and role fields. The form keeps a submitted
phone number after a recoverable validation error and never repopulates either
password. It gives an honest next step: account creation finishes at sign-in;
it does not promise payroll access or payment.

The invitation, first-use dashboard and saved-employee continuation now use the
same English and critical Amharic language path. The document language follows
the selected locale. At 320px the language chooser remains available, password
visibility works by keyboard, and the dark theme has explicit contrast fixes.
Oromo uses the reviewed English fallback for this new copy until Oromo copy is
provided and reviewed.

This slice does not change payroll calculations, approvals, payment execution,
employee management authorization, migrations or hosted configuration.

## Verification

Evidence is local and synthetic in `local-evidence/invitation-language-20261008/`.

- Final browser receipt: `browser-final.log` and `browser-report.json` record
  25 desktop/phone/large-text/dark-mode layouts and 13 real interaction checks,
  with no detected horizontal overflow, Axe A/AA violation or page error. The
  journey performs owner registration, employee creation, CSRF-protected invite
  generation, rejected missing-CSRF submission, English and Amharic recovery,
  actual invitee sign-in, safe invalid-token recovery, first employee and payroll
  preparation. It uses a generated local file-backed SQLite preview only for
  browser execution.
- Invitation-focused non-PostgreSQL tests: `65 passed, 4 skipped, 4 warnings in
  7.07s` in `tests-nonpg-final.log`. Final recovery/language/layout rerun after
  the success-message correction: `44 passed, 3 skipped, 4 warnings in 15.65s`
  in `tests-recovery-final.log`. Together these cover invitation CSRF enforcement,
  invalid/reused/expired/deleted tokens, scoped account creation, password and
  phone recovery, localisation behavior and the visible reset confirmation.
- Python compilation, JavaScript syntax and `git diff --check` pass. The local
  Stylelint executable is unavailable and its registry fallback cannot resolve,
  so a fresh Stylelint receipt is not claimed. Earlier browser and test failures
  are retained as development evidence and superseded by the final run above.

After the final adjustments, the combined first-employee and invitation
selection passed on disposable PostgreSQL 16 upgraded from empty through the
current Alembic head: `25 passed, 6 warnings in 29.90s`. Its first run was red
(`1 failed, 24 passed, 6 warnings in 28.92s`) because an invited employee could
open a coworker's management detail page. The adjacent route review also found
missing role gates on overtime create/delete, leave balance/request, and
settlement detail. Those five management routes now require owner/accountant;
the regression asserts that invited employees receive 403 responses. Earlier
non-PostgreSQL receipts remain separate and are not added to this count. No
hosted CI, deployment, real-phone test, screen-reader review or practitioner
acceptance is claimed.

### 2026-10-11 follow-up

Independent review found selected-company labels and owner-only employee
actions could use the default company role on employee pages. The context now
uses the active membership for the `employees` blueprint. A migrated-PostgreSQL
regression checks selected-company employees and add-form labels plus owner and
accountant action visibility with opposite default roles. The complete focused
selection passed: `49 passed, 55 warnings in 57.00s`. Fresh Stylelint also passed
on all changed CSS files and the design-system stylesheet.

## Next action

Run hosted checks on the reviewed patch, then observe an uncoached owner and
invited employee on a real phone. Review and ship Oromo copy only after it has
been supplied or checked by a fluent reviewer.
