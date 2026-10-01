# Founder trial before Tigist

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

Later worksheet edits do not silently change the preserved review. Before
submission, use **Refresh from saved worksheet** deliberately if edits must be
included. Worksheet approval cannot yet be undone or corrected through this flow.

## Remaining before this work order closes

- Expose on-demand individual PDF on the results screen before a PDF already exists.
- Hide the unsupported worksheet Undo button and correct the completed review badge.
- Complete the final browser download click and founder trial feedback.
- A sample generated PDF is available in the local handoff. PostgreSQL HTTP/worker
  tests already verify PDF and bank figures, persistence, retries and rollback.

Tell us which step was confusing, whether the deductions are understandable, and
whether this would reduce monthly spreadsheet checking. Then observe Tigist using
the same synthetic journey. Daily workers, unit-based items, linked corrections,
production release gates and direct payment integrations remain separate work.
