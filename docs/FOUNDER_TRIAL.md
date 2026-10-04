# Founder trial before Tigist

## Current trial - 2026-10-04

PR #11 is merged on main `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`.
The local trial launcher is a separate feature-branch change, not deployed or
merged. This section supersedes the old temporary demo and pending UI defects
below; those older receipts are preserved as history.

In PowerShell:

```powershell
cd D:\ethiopian_payroll_engine\payroll-pr8-integration
powershell -NoProfile -ExecutionPolicy Bypass -File .\START_FOUNDER_TRIAL.ps1
```

Keep that terminal open. Visit http://127.0.0.1:5058/auth/login in Chrome on
this computer. Choose **Email**. Account details are in
`local-evidence\founder-trial\ACCOUNT_DETAILS.txt`; use the accountant first,
then the owner. The script uses the existing locked Python environment and
local PostgreSQL at 127.0.0.1:55439. It installs nothing. For another machine,
the local PostgreSQL service/role and Python environment need setup first.

The generated synthetic database, session/encryption keys and PDFs persist
when you stop with Ctrl+C. Starting again preserves your edits and approvals;
it does not reset data, recreate the database or migrate an existing trial.
Never commit the ignored `local-evidence` folder or use real employee details.
If the month changes or setup fails, preserve the files and request help.
This fixture is a single current Gregorian month, not a shared online demo.

### Your next action

1. Sign in as accountant and open **Payroll Spreadsheet**. The synthetic prior
   month is approved; basic salary was 10,000 and allowances 2,000. Current basic
   is 12,000 and allowances remain 2,000. Enter **day overtime 4 hours**, **bonus
   500**, **advance 100**, **additional unpaid days 0**. Save and recalculate.
2. Review the saved payroll. Explain the salary, overtime, bonus, gross, net and
   recovery differences. Submit to owner. Sign out and use the owner account to
   review, confirm with password and approve once.
3. Compare approved review/results, the individual PDF and bank download.
   Expected current net for this scenario: **ETB 11,053.99**. Payment remains
   pending; downloading a file does not execute a payment or statutory filing.
   Record the first unclear label, missing explanation or difficult phone action.

The prior approval is a synthetic fixture created through existing payroll
services. It is not practitioner approval or evidence of statutory correctness.
Do not reset the approved current month to repeat the exercise; ask for another
isolated fixture. Founder/Tigist acceptance and production release remain open.

For Tigist: give only the source notes above and ask her to prepare, explain,
submit and reconcile the month without coaching. Record hesitation, missing
office decisions, and whether she could identify the next action. Use the
existing detailed scripts in `MONTHLY_PAYROLL_JOURNEY_2026-10-03.md`.

## Historical temporary demo handoff

Use synthetic data only. This is a local founder trial, not a deployed release.
The current demo is at http://127.0.0.1:5057 on the development computer.
The separate Chrome tab shows the completed QA example; a fresh founder company
is also prepared. Local account details are kept with the demo handoff on D:.

## One journey to try

1. Open Payroll Spreadsheet for the displayed Gregorian month.
2. For Demo Employee (basic 10,000; allowances 2,000), enter extra unpaid days **2**,
   monthly taxable bonus **900.50**, and advance **500**. Leave overtime at zero.
3. Click **Save & Recalculate**, then **Review saved payroll**.
4. Check gross **12,900.50**, tax **2,310.15**, employee pension **700.00**, unpaid
   deduction **800.00**, advance **500.00**, net **8,590.35**.
5. Click **Continue to approval**. Expand the employee breakdown, check total
   deductions **4,310.15**, enter the demo password, confirm and approve.
6. The payroll is approved; no bank transfer, wallet payment or tax filing is sent.
7. Click **Download All (ZIP)** on the results screen; its payslip shows the same amounts.

Later worksheet edits do not silently change the preserved review. Before
submission, use **Refresh from saved worksheet** deliberately if edits must be
included. Worksheet approval cannot yet be undone or corrected through this flow.

## Remaining before this work order closes

- Expose on-demand individual PDF on the results screen before a PDF already exists.
- Hide the unsupported worksheet Undo button and correct the completed review badge.
- Founder trial feedback remains. The browser ZIP download succeeded and its PDF amounts match.
- A sample generated PDF is available in the local handoff. PostgreSQL HTTP/worker
  tests already verify PDF and bank figures, persistence, retries and rollback.

Tell us which step was confusing, whether the deductions are understandable, and
whether this would reduce monthly spreadsheet checking. Then observe Tigist using
the same synthetic journey. Daily workers, unit-based items, linked corrections,
production release gates and direct payment integrations remain separate work.
