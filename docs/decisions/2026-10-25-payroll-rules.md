# Payroll rule decisions — adviser response, 2026-10-25

Written answers the owner received from a payroll/tax adviser on 2026-10-25 to
the four open payroll questions. Recorded here so code, PRs and `PLAN.md` can
point at one place. This is a record of the adviser's answers, not independent
legal certification.

| # | Question | Status | Affects |
|---|----------|--------|---------|
| Q1 | PAYE base: before or after the 7 % employee pension? | **CONFIRMED** (2026-10-25) | PR #32 `fix/paye-gross-income` (R1) |
| Q2 | Tax on termination payments (severance, notice, leave encashment) | **PENDING** written tax confirmation | PR #33 `fix/settlement-taxation` (R2) |
| Q3 | Leave-encashment formula | **PENDING** written labour-law confirmation | PR #33 `fix/settlement-taxation` (R3) |
| Q4 | Tax errors in locked (approved) months | **PENDING** correction procedure confirmation | Parked: historical PAYE difference report |

## Q1 — PAYE base — CONFIRMED

Answer: **Yes.** PAYE is calculated on gross taxable employment income
**before** deducting the 7 % employee pension contribution.

Worked example: taxable employment income ETB 10,000 → PAYE ETB 1,650,
employee pension ETB 700, net ETB 7,650.

References: Income Tax Proclamation No. 979/2016, Arts 10–12; Art 11 as
amended by Proclamation No. 1395/2025.

Effect: closes RC-38000-01 (see `docs/PENSION_BEFORE_TAX_RC38000_01.md` for the
history). Code: `PENSION_DEDUCTED_BEFORE_TAX = False`
(`payroll_engine/constants.py`), PR #32.

## Q2 — Termination payments — PENDING

Answer: severance pay, payment in lieu of notice and leave encashment are
**taxable employment income**. Aggregating them with the final month's income
is a **supportable starting interpretation, but it is not verified**. No
ERCA/Ministry of Revenues directive on spreading such payments over months
was identified.

Status: needs **written tax confirmation** of the method (aggregation in the
final month vs. any spreading) before PR #33 is merged.

## Q3 — Leave-encashment formula — PENDING

Answer: **no universal formula is approved.** Relevant provisions of Labour
Proclamation No. 1156/2019:

- Art 77(2): leave pay is the wage the worker would have received had they
  been working.
- Art 77(4): unused annual leave is paid out on termination.
- Art 53: definition of "wage", with its exclusions. The components used for
  leave pay must follow the **Art 53 wage definition**, not the payroll's own
  "allowance" labels.
- Art 77(3): the 26-day figure concerns **counting service**, not a divisor
  for a daily rate.

Status: needs **written labour-law confirmation** of the formula (daily-rate
basis and which pay components count as Art 53 wage) before PR #33 is merged.
Product follow-up: the leave basis setting should eventually offer an
"Art. 53 wage" basis definition rather than "allowance" labels.

## Q4 — Locked months with a tax error — PENDING

Answer: locking a payroll month **does not remove the duty to address a tax
error**. Required approach:

- Preserve the original records and the audit trail.
- Quantify the difference **per period**.
- Confirm the correction / amended declaration procedure before acting:
  Tax Administration Proclamation No. 983/2016, Arts 28–29, as amended
  (including Proclamation No. 1434/2026).
- **Never silently overwrite** approved/locked figures.

Status: correction procedure to be confirmed. Next step (parked in
`PLAN.md`): a historical PAYE difference report for locked months that only
quantifies differences; any correction goes through an explicit adjustment
run once the procedure is confirmed.
