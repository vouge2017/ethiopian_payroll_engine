# Payroll rule decisions — adviser response, 2026-10-25

Written answers the owner received from a payroll/tax adviser on 2026-10-25 to
the four open payroll questions (first review), updated the same day with the
adviser's second review of Q2–Q4. Recorded here so code, PRs and `PLAN.md` can
point at one place. This is a record of the adviser's answers, not independent
legal certification.

| # | Question | Status | Affects |
|---|----------|--------|---------|
| Q1 | PAYE base: before or after the 7 % employee pension? | **CONFIRMED** (2026-10-25) | PR #32 `fix/paye-gross-income` (R1) |
| Q2 | Tax on termination payments (severance, notice, unused-leave pay) | **ACCEPTED** as statutory default (2026-10-25, second review) | PR #33 `fix/settlement-taxation`: tax method |
| Q3 | Leave-encashment formula | **PARTIAL** (2026-10-25, second review) | PR #33: leave basis/divisor must be confirmed per company |
| Q4 | Tax errors in locked (approved) months | **PENDING** correction procedure | Parked: historical PAYE difference report |

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

## Q2 — Termination payments — ACCEPTED (statutory default)

First review: these payments are taxable employment income; aggregation with
the final month was a supportable but unverified interpretation, and no
ERCA/Ministry of Revenues spreading directive was identified.

Second review answer: taxable severance, pay in lieu of notice and unused-leave pay are
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

First review: no universal formula is approved. Art 77(2): leave pay is the
wage the worker would have received had they been working; Art 77(4): unused
leave is paid out on termination; Art 77(3): the 26-day figure concerns
counting service, not a daily-rate divisor; components must follow the Art 53
wage definition, not the payroll's own "allowance" labels.

Second review answer:

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

First review: locking a month does not remove the duty to address a tax
error; quantify the difference per period; Tax Administration Proclamation
No. 983/2016 Arts 28–29 as amended.

Second review answer:

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

## Owner-requested adviser pack — evidence review (2026-10-27)

This is a research brief for an Ethiopian payroll/tax adviser, not legal advice
or practitioner acceptance. Calculations below are synthetic and illustrate
the questions; they are not new payroll policy.

**Review status (2026-10-30):** This pack is ready to submit for review;
none of the new questions below has an adviser answer recorded. “Officially
sourced” means the cited provision was located, not that every application or
effective date has been confirmed. The adviser should supply a dated, signed
response and identify the law and version relied on for each question.

### 1. Private-sector pension: coverage, salary base and concurrent employers

**Status: partial; eligibility, concurrent employment and effective date unanswered.**

**Primary-source findings.** Private Organization Employees' Pension
Proclamation No. 1268/2022 defines a covered private-organization employee as
a salaried person employed for at least 45 days (Art. 2(1)). The scheme applies
to Ethiopian nationals, subject to the stated foreign-origin and treaty
exceptions (Art. 3(1)); Directive No. 1085/2025 says Ethiopian-born foreign
nationals may join voluntarily (Art. 5(3)) and lists other excluded categories
(Art. 7). Directive No. 1087/2025 defines salary as full monthly salary for
regular working hours, excluding overtime, allowances, bonuses, commissions,
incentives and service fees (Art. 2(13)); the contribution rates are 7% employee
and 11% employer (Art. 5). The directive says contributions are collected with
salary income tax (Art. 6). The Proclamation says an employee joining another
covered private organization must notify it of the social security
identification number (Art. 4(2)).

Directive 1087/2025 Art. 46 makes effectiveness conditional on Ministry of
Justice registration and publication on the administration's website. The
exact date both conditions were met has not been verified; do not infer it
from the directive's 2025 title or from the date of the PDF upload.

**Worked example.** If qualifying regular-hours salary is ETB 10,000, the
employee share is ETB 700 and employer share ETB 1,100 (ETB 1,800 total).
Overtime and allowances are excluded from this pension salary definition.

**Ask the adviser.** Does the 45-day threshold count calendar days, actual work
days or another service measure, and from which date? For concurrent employers,
does each employer contribute on the salary it pays, or is there any employee
election, coordination or ceiling? No general ceiling or other-employer
exemption was identified in the reviewed provisions. Confirm how foreign
employees, Ethiopian-origin foreign nationals, treaties, employees aged 60+
and any exception should be represented. The current engine's basic-only
pension base matches the exclusion of allowances/overtime, but the coverage
gate remains a separate implementation gap.

**Sources:** [Proclamation No. 1268/2022, Arts. 2–4, 10](https://justice.gov.et/wp-content/uploads/2025/02/%E1%8A%A0%E1%8B%8B%E1%8C%85-%E1%89%81%E1%8C%A5%E1%88%AD-1268-2014.pdf); [Directive No. 1085/2025, Arts. 5–10](https://justice.gov.et/wp-content/uploads/2026/02/1085-Private-Organizations-Employees-Pension-Implementation-Directive-No.-1085-2025.pdf); [Directive No. 1087/2025, Arts. 2, 5–6](https://justice.gov.et/wp-content/uploads/2026/03/1087-A-Directive-for-Planning-Collecting-Transferring-and-Controlling-of-Private-Organization-Employees-Pension-Contribution-No.-1087-2025.docx.pdf).

### 2. Per diem, transport and casual-worker PAYE exemptions

**Status: partial; directive identity, later amendments and application unanswered.**

**Primary-source findings.** Regulation No. 410/2017, Art. 54(1)(b) exempts
employment income of an unskilled employee working for the same employer,
continuously or intermittently, for no more than 30 days in any 12-month
period. If intermittent work exceeds 30 days in that period, the text says tax
is calculated only on income from the last employment. Art. 54(1)(c)'s
definition separately describes engagement aggregating no more than 30 days
during a calendar year. Those two time references need interpretation before a
production rule is encoded. The definition also requires no vocational
training and no use of machinery/equipment requiring special skill. This is
not a blanket exemption for every temporary worker.

The commonly cited amounts for work-related transport (ETB 2,200 / 25%),
home-to-work transport (ETB 600), and domestic per diem (more than 25 km;
ordinary staff 4% / ETB 500 daily; managers 5% / ETB 1,000 daily) are reported
in practitioner material as deriving from Tax Exempt Income Directive No.
1/2011. The [Ministry of Finance directive index](https://www.mofed.gov.et/mof-directive/tax-directive/)
lists an exempt-income Directive No. 1/2011. Its document could not be
retrieved there, but the Ministry of Justice hosts an Amharic
[exempt-income directive labelled 200/2013](https://justice.gov.et/wp-content/uploads/2019/03/Performance-of-Income-Exempted-from-Income-Tax-Directive-No.-200-2013.pdf).
Its Article 5 contains the 25% / ETB 2,200 work-travel and ETB 600 commuting
figures; Article 6(1)(a) uses “ከሁለቱ ከፍተኛ ከሆነው” (the higher of
the two) for the ETB 500 / 4% per-diem amounts. Article 14 states it takes
effect on 1 Miyazya 2011 E.C. (9 April 2019). The Justice index title and
the PDF both say 200/2013, while the Finance listing says 1/2011: whether
these identify the same legal instrument and whether later amendments apply
are unanswered. A [secondary payroll summary](https://za-kb.sage.com/portal/app/portlets/results/viewdocument.jsp?solutionid=240613102801517)
reports the lower per-diem amount, while an [earlier legal update](https://www.ensafrica.com/uploads/newsarticles/1284_africa%20regulatory%20ensight%20-%20issue%205%20of%202019.pdf)
reports the higher amount; a qualified reviewer should resolve this against the operative
text, rather than adopting either interpretation from a summary. The qualifying payment,
distance test, employee categories, accommodation treatment, and later
amendments therefore remain unverified and must not be treated as approved
code requirements yet.

**Worked examples to validate, not adopt.** At ETB 10,000 monthly basic,
the reported ordinary per-diem alternatives are ETB 400/day and ETB 500/day;
for a manager they are ETB 500/day and ETB 1,000/day. Which amount applies is
unanswered. For a
work-related monthly transport payment, the reported cap is the lower of ETB
2,500 and ETB 2,200. These examples do not resolve what evidence or contract
terms make a payment exempt.

**Ask the adviser.** Provide the exact directive and article, amendments and
effective dates; confirm cap direction and whether salary means basic salary;
define travel-distance measurement and manager categories; distinguish
work-related travel, home-to-work commuting and company-provided transport;
and resolve Art. 54's 12-month/calendar-year wording and the “last employment”
tax rule. Confirm whether the casual-worker PAYE exemption affects pension
coverage (a separate legal test).

**Sources:** [Council of Ministers Federal Income Tax Regulation No. 410/2017,
Art. 54](https://justice.gov.et/wp-content/uploads/2025/02/%E1%8B%B0%E1%8A%95%E1%89%A5-%E1%89%81%E1%8C%A5%E1%88%AD-410-2009.pdf);
[Ministry of Justice directive index and Amharic PDF](https://justice.gov.et/am/directives/performance-of-income-exempted-from-income-tax-directive-no-200-2013/).
Treat the figures as source findings pending identity, version and application review.

### 3. Public-holiday work versus public-holiday overtime

**Status: partial; application to overlapping hours and divisor unanswered.**

**Primary-source finding.** Labour Proclamation No. 1156/2019 Art. 75(1) says
work on a public holiday is paid at 2 times hourly wages for each hour. Art.
68(1)(d) sets at least 2.5 times the ordinary hourly rate for overtime work
done on a public holiday. The proposed distinction is ordinary scheduled
holiday hours versus hours qualifying as overtime; how the two provisions
interact for a particular hour remains an adviser question.
Art. 66 defines overtime by excess over normal daily hours; Art. 67 restricts
when overtime may be worked and caps it at four hours/day and twelve hours/week.

**Worked example.** Using the engine's current illustrative divisor of 208,
ETB 10,000 / 208 = ETB 48.0769 per hour. One ordinary scheduled holiday hour
would be ETB 96.15 at 2×; one holiday overtime hour would be ETB 120.19 at
2.5×, rounding once at the end.

**Ask the adviser.** Confirm that this distinction is the correct application
of Arts. 68 and 75, the ordinary hourly divisor for each work schedule, and
how an hour is classified when a shift crosses normal hours or overlaps a
weekly rest day and public holiday. Confirm whether the app should retain
separate “holiday work” and “holiday overtime” codes. The existing overtime
rate table's 2.5× holiday-overtime multiplier should not be reduced to 2×.

**Source:** [Labour Proclamation No. 1156/2019, Arts. 66–68, 73–75](https://justice.gov.et/wp-content/uploads/2025/02/%E1%8A%A0%E1%8B%8B%E1%8C%85-%E1%89%81%E1%8C%A5%E1%88%AD-1156-2011.pdf).

### 4. Leave pay and unused leave at termination

**Status: partial; component classification and divisor unanswered.**

**Primary-source findings.** Labour Proclamation No. 1156/2019 Art. 53 defines
wages as regular payment for work and expressly excludes overtime, per diem,
hardship and transport allowances, relocation expenses, bonuses, commissions,
incentives and service charges. Art. 77(2) sets leave pay at the wage the
worker would have received if working; Art. 77(4) requires payment for unused
leave on termination. Art. 77(3)'s 26-day figure is for converting service
days to a month for leave entitlement; it does not state a daily-pay divisor.

**Worked example.** If 5 unused days are payable and the adviser confirms
qualifying monthly wages of ETB 10,000 and a divisor of D, the amount is
`5 × (10,000 / D)`. Neither D nor whether a particular allowance enters the
ETB 10,000 wage base can be inferred from the software's current setting.

**Ask the adviser.** Classify each actual pay component under Art. 53; identify
the legally supported divisor and treatment of partial months, variable wages,
and rounding; and confirm how the recorded leave balance is reconciled at
termination. A company-selected divisor is configuration, not proof of legal
correctness. Keep the existing block on finalizing positive leave encashment
until that company's basis is confirmed.

**Source:** [Labour Proclamation No. 1156/2019, Arts. 53, 76–77](https://justice.gov.et/wp-content/uploads/2025/02/%E1%8A%A0%E1%8B%8B%E1%8C%85-%E1%89%81%E1%8C%A5%E1%88%AD-1156-2011.pdf).

### 5. Correcting a filed PAYE month

**Status: partial; actual monthly PAYE correction procedure unanswered.**

**New primary-source finding.** Tax Administration Proclamation No. 1434/2026
amends Proc. 983/2016 and adds a formal tax-assessment revision framework.
New Arts. 97–102 specify grounds (including arithmetic/computational error and
other mistakes affecting liability), materiality/evidence conditions, a
taxpayer application or authority-initiated process, time limits, notice
contents, and a limit against revising an assessment more than once for the
same error. Renumbered Art. 96(2) says the Authority may issue a directive for the
procedure. The amended Art. 28 separately sets assessment limitation periods.
Article 3 makes Proclamation 1434/2026 effective upon publication in the
Federal Negarit Gazette dated 30 July 2026; confirm applicability and any
implementing directive for the relevant payroll period with the adviser.

This confirms a formal route for revising a **tax assessment notice**. The
text reviewed does not itself identify the Ministry of Revenue's operational
form or portal steps for an employer to amend a previously filed monthly PAYE
withholding declaration. We should not claim that a specific monthly
correction workflow is settled solely from Proc. 1434/2026.

**Worked example.** If a locked payroll period has ETB 1,000 PAYE understated,
the product may calculate and preserve that period-specific difference, but
must not overwrite the approved run or create a replacement filing. The
employer/adviser must first establish whether the declaration is corrected in
the original period, through a tax-authority assessment revision, or by another
authorized adjustment, and whether interest/penalties apply.

**Ask the adviser / tax office.** For employer-filed monthly PAYE, identify the
legal route, applicable application/declaration form and portal menu, deadline,
supporting documents, payment/refund handling, interest/penalty treatment and
whether correction is performed by the employer or the Authority. Confirm how
to handle already-paid shortfalls and over-withholding. Until then, preserve
the original locked run and allow difference reporting only.

**Source:** [Tax Administration Proclamation (Amendment) No. 1434/2026,
especially amended Art. 28 and new Arts. 96–102](https://justice.gov.et/wp-content/uploads/2026/08/%E1%8A%A0%E1%8B%8B%E1%8C%85-%E1%89%81%E1%8C%A5%E1%88%AD-1434-2018.pdf).

### Adviser response record to complete

For each question above, capture the adviser's exact answer, legal citation and
version/effective date, any official form or portal evidence reviewed, and the
date/name of the reviewer. Mark answers “unanswered” where those receipts are
not provided. No code changes follow from this research pass.
