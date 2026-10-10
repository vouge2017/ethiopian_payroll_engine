# Employee workspace delivery — 2026-10-08

The first-user journey now continues into readable employee forms and a recoverable employee list. Existing login/company setup work was reused. Local, uncommitted on `codex/monthly-payroll-ui`, baseline/HEAD `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`; no upstream, commit, hosted checks or deployment.

## Delivered

- Consistent company context, serif page headings, phone layouts and labeled View/Edit actions; accurate filtered counts, clear no-match recovery and working pagination retaining encoded search/department/archive parameters.
- Employee form errors return the same form with escaped submitted entries and HTTP 400. Successful saves retain the existing redirect. Native invalid fields inside closed optional details are revealed; unsaved navigation can be cancelled; submitting/busy state resets on browser return.
- Imported full-name records remain editable without converting their name format or duplicating existing name parts. Ethiopian phone prefix display is corrected. Accounts without email show a real name/phone fallback.
- Deactivation matches existing owner permission, uses safe name data attributes, confirms the consequence, restores the action after failure and refreshes counts after success. Archived employees actually appear through the existing soft-delete query API, still explicitly company-scoped; archived-only department choices and pagination are consistent.
- Real recovery testing found an archived employee ID being reused during creation, causing a unique-constraint failure. Generation and duplicate checks now include archived records in the same company, preserving the existing uniqueness rule and archived history.

Server employee search and department filtering remain; duplicate client filtering and mouse-only sorting were removed. The list retains its server alphabetical order. Existing calculation, billing limits, owner/accountant permissions, audit behavior and payroll approval policy were not changed.

Concurrent first-use dashboard/component work from another chat was preserved and inspected, not credited as this pass's redesign. This pass contributes a next-step block for the existing dashboard's no-completed-run state and scoped stylesheet integration. Combined task-start diffs include those shared-file changes; they are not a clean standalone commit.

## Verification

Evidence: `local-evidence/first-employee-20261008/`; exact task-start source diff and screenshots: `D:/ethiopian_payroll_engine/output/payroll-employee-workspace-2026-10-08/`.

- Initial reproduction: `4 failed, 1 passed, 10 warnings in 10.93s` (`red.log`). Recovery/name fixes then passed; pagination initially remained failing because the default query excluded archived employees. Earlier failing receipts retained.
- Archived-ID reproduction: `1 failed, 6 deselected, 2 warnings in 6.06s` (`id-red.log`).
- Final selected regressions: `11 passed, 14 warnings in 17.02s` (`tests-verified.log`): seven new cases use generated Alembic-migrated PostgreSQL; four existing phone cases use their original fixtures. Includes retained invalid attempts/no saved mutation, legacy-name preservation, archive/filter pagination, foreign-company denial, accountant action/403 and archived-ID reservation. This is not a full suite.
- Final Chrome: 16 layouts, 10 interactions, no detected overflow, checked axe A/AA violations or JavaScript errors (`browser-report.json`, `browser-verified.log`). Covers empty workspace/add/list/edit at 320/768/1440px, dark 390px, enlarged text, imported full-name edit, actual CSRF registration/company/create/edit, invalid collapsed details, unsaved cancellation, no-match recovery, deactivation cancellation/retry/success and subsequent creation. Disposable fixture disables unrelated scheduled hooks/rate limiting and is loopback-only; it is not a live tester server.
- Ruff check/format, changed CSS Stylelint, employee-form JavaScript syntax and source whitespace pass. Initial contrast failures, selector failure and archived-ID browser failure remain recorded; final receipt supersedes them.

Independent review was requested but the reviewer hit its usage limit and did not finish this slice. The preceding monthly peer review does not certify these changes. Real devices, screen readers, complete Amharic/Oromo critical-path copy, session/network-save recovery, full payroll acceptance and practitioner observation remain open. No new 90/100 or whole-platform stability claim is made.

Next: finish the independent review and observe an uncoached real-phone first-user/payroll walkthrough in an identified stable tester environment, then fix observed friction. Do not expand into unrelated features before that evidence.
