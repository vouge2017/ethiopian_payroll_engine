# Payroll policy decision sheet — 2026-11-15

Two questions need a decision from the owner (+ accountant if possible).
Per project rules, the engine does not choose money/legal thresholds silently.

## Already resolved by merged work — no decision needed

| Question | Status |
|---|---|
| Bonus taxed as standalone income | **Fixed** — corrections (commit `90779cb`) now tax a bonus/overtime addition marginally on the month's total taxable income using the frozen tax brackets, exactly like the monthly worksheet path. |
| Overtime hourly rate rounded to 2dp before multiplying | **Fixed** — commit `356678d` (2026-11-11): hourly rate is unrounded; rounding happens once, after hours × multiplier. |

## Q1 — Final settlement: may the net be negative (employer recovers more than owed)?

**What the code does today** (`services/settlement_service.py:401`):
`net_final = earnings − deductions` with **no floor at zero, no warning, no special approval**.

**Worked example**: employee with 2 years' service, basic 5,000
- Earnings: severance 1,250.00 + leave encashment 700.00 = **1,950.00**
- Deductions: pension 200.00 + tax 0.00 + salary advance 3,000.00 = **3,200.00**
- **Net final payment: −1,250.00** — the system would record this and pay out a negative amount (or demand repayment) with no extra signal.

**Context**: for regular payroll the engine already enforces the statutory caps (deduction engine BLOCKs `DEDUCTIONS_EXCEED_NET`, court orders capped at 1/3, 50% for child support). Settlements subtract "pending deductions" as a lump sum, so those caps do not apply there.

**Options** (pick one)
- **A — Allow negative, but warn + require owner confirmation.** Keep the true number; settlement approval gets a big warning and an explicit confirm step (same pattern as payroll's negative-net approval block). Least new machinery, nothing hidden.
- **B — Floor at zero, carry the remainder.** Net paid is never negative; the uncollected −1,250 becomes a recorded receivable recovered next month. Needs a new "recoverable balance" feature (design + tests).
- **C — Floor at zero, write off the remainder.** Simplest, but the employer silently loses money. Not recommended.
- **D — Block settlement approval while negative.** Owner must first reduce the advance or split the settlement. Strictest; may trap legitimate cases.

**Recommendation: A.**

## Q2 — When should negative net pay be stopped?

**What the code does today** (`validation.py`):
- A draft/review **can be saved** with a negative net; it is only **BLOCKed at approval** (`NEGATIVE_NET_PAY`, severity BLOCK).
- The deduction engine already BLOCKs `DEDUCTIONS_EXCEED_NET` at preparation, so the remaining route to negative net is tax + pension exceeding gross (rare, but possible with odd inputs).

**Options** (pick one)
- **A — Keep as is.** Draft is not money movement; the approval gate is the real control. Accountants may be surprised late.
- **B — Block earlier (at save/preparation).** Nothing negative can ever be saved; stricter, but blocks legitimate "I'll fix it tomorrow" drafts.
- **C — Keep the approval block + add an early WARN at preparation.** Accountant sees a warning banner immediately when a row's net goes negative, fix it early, approval still hard-blocks. 

**Recommendation: C.**

## How to answer

Reply with one letter per question, e.g. "Q1: A, Q2: C", or "ask the accountant first".
Nothing in the engine changes until you answer; both behaviors are recorded here as deliberate-current-state in the meantime.
