# Settlement rule decisions — adviser second review, 2026-10-25

Written answers the owner received from a payroll/tax adviser on 2026-10-25
(second review) on the final-settlement questions Q2–Q4. This file lives on
`fix/settlement-taxation` (PR #33) and is kept separate from
`docs/decisions/2026-10-25-payroll-rules.md` (added on `fix/paye-gross-income`,
PR #32, not merged yet) to avoid a merge conflict. When both are on `main`,
this file supersedes the Q2–Q4 sections of that one. Q1 (PAYE on gross,
CONFIRMED) is recorded only in that file.

This is a record of the adviser's answers, not independent legal
certification.

| # | Question | Status | Affects |
|---|----------|--------|---------|
| Q2 | Tax on termination payments (severance, notice pay, unused-leave pay) | **ACCEPTED** as statutory default (2026-10-25) | PR #33: tax method |
| Q3 | Leave-encashment formula | **PARTIAL** (2026-10-25) | PR #33: leave basis/divisor must be confirmed per company |
| Q4 | Tax errors in locked (approved) months | **PENDING** correction procedure | Parked: historical PAYE difference report |

## Q2 — Termination payments — ACCEPTED (statutory default)

Answer: taxable severance, pay in lieu of notice and unused-leave pay are
**aggregated with other taxable employment income in the month received**,
unless a specific exemption or rule applies.

References: Income Tax Proclamation No. 979/2016, Arts 10 and 12;
withholding, Art 88. Rates per Proclamation No. 1395/2025.

Caveat from the adviser: this is the statutory default, **not a confirmation
that every directive was reviewed**.

Effect in code: `SETTLEMENT_LUMP_SUM_TAX_METHOD = 'final_month_aggregate'`
(unchanged), `TAX_METHOD_STATUS = 'statutory_default'`. Each new settlement
stores and shows "Tax method: statutory default: aggregated in month received
(Proc. 979/2016 Arts 10, 12, 88)". The tax method is no longer shown as
pending.

## Q3 — Leave-encashment formula — PARTIAL

Answer:

- Leave pay uses **qualifying wages** under Labour Proclamation No. 1156/2019
  **Arts 53 and 77 read together**.
- Apply the **Art 53 exclusions**. An allowance being fixed, contractual or
  regular does **not by itself** make it includable.
- **No universal ÷26 or ÷30 divisor** is established.
- "A configurable divisor is a software feature, not legal approval. Do not
  use an unconfirmed default for live settlements."

Effect in code (PR #33):

- New company state `leave_rate_confirmed_at` / `leave_rate_confirmed_by`
  (migration `f4a5b6c7d8f6`). Existing companies start **unconfirmed**.
- The company confirms its basis and divisor in Settings → Company Profile
  ("Payroll rules: leave encashment", confirmation checkbox, audit-logged as
  `leave_rate_confirmation_change`). Changing the basis or divisor without
  re-ticking the box clears the confirmation.
- A settlement with leave encashment > 0 **cannot be finalized** (the
  terminate action is refused with HTTP 409, nothing saved, employee stays
  active) until the company has confirmed the exact basis and divisor used.
  Message: "Choose and confirm your leave-pay basis and divisor (Labour Proc.
  1156/2019 Arts 53, 77) before finalizing", linking to the setting.
- A **preview** (no password, nothing saved) still computes the figures, with
  a visible warning.
- Basis label renamed to "Basic + allowances that qualify as wages (Art. 53)";
  the "(default)" tag is removed. The app still reads `Employee.allowances`
  (monthly allowance on record); whether those amounts are Art 53 wages is
  the company's call when it confirms.
- Settlements created while unconfirmed (only possible with zero leave pay)
  carry the notice "Leave-pay basis and divisor pending: not yet confirmed by
  the company (Labour Proc. 1156/2019 Arts 53, 77)".

Open: which basis and divisor are right is still for each company (and its
adviser) to decide; the app does not choose.

## Q4 — Locked months with a tax error — PENDING (procedure)

Answer:

- Preserve the original records and the audit trail.
- Recalculate the **affected periods**.
- Follow the **formal correction process**: Tax Administration Proclamation
  No. 983/2016 as amended by Proclamation No. 1434/2026.
- The 5-year ordinary assessment period (10 years for fraud) is **not** the
  PAYE amendment procedure.
- The exact monthly PAYE amendment procedure is **still unconfirmed**.
- Never silently overwrite approved/locked figures.

Status: PENDING the exact procedure. Next step stays parked in `PLAN.md`: a
historical PAYE difference report that only quantifies per-period
differences; any correction goes through an explicit adjustment run once the
procedure is confirmed.
