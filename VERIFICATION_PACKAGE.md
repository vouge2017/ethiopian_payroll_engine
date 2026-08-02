# EthioPayroll — Accountant Review Package

**Date:** August 2026
**Prepared for:** Ethiopian accountant / tax compliance officer
**Time needed:** 30 minutes (quick review) or 2-3 hours (full verification)

---

## What Is This?

We built a payroll system for Ethiopian businesses. Before we let real companies use it, we need an Ethiopian accountant to confirm that our tax, pension, and labour calculations are correct.

**We are NOT asking you to review code.** We are asking you to review the numbers and rules the system uses, and tell us if anything is wrong.

---

## SECTION 1: Income Tax Brackets

Our system uses these tax brackets to calculate monthly income tax:

| Monthly Taxable Income (ETB) | Tax Rate |
|------------------------------|----------|
| 0 – 2,000 | 0% |
| 2,001 – 4,000 | 15% |
| 4,001 – 7,000 | 20% |
| 7,001 – 10,000 | 25% |
| 10,001 – 14,000 | 30% |
| 14,001 and above | 35% |

**Source:** Proclamation No. 1395/2025, Article 11

**We verified this against:** A real company's ERCA filing for Sene 2018 (June 2026) with 146 employees. Every employee's tax matched exactly.

**Your confirmation needed:**
- [ ] These brackets are correct
- [ ] These brackets are NOT correct — the correct brackets are: _______________

---

## SECTION 2: Personal Relief (ETB 150)

**Question:** Does Ethiopian income tax law currently allow a ETB 150 personal relief (deduction from tax)?

**What we found:**
- Proclamation No. 979/2016, Article 10(3) says: "An employee shall not be allowed a deduction for any expenditure incurred in deriving employment income"
- Proclamation No. 1395/2025, Article 11 contains ONLY the tax bracket table — no personal relief
- The real ERCA filing we reviewed does NOT subtract personal relief

**Our system:** Does NOT apply personal relief. Tax = gross tax (no deduction).

**Your confirmation needed:**
- [ ] Correct — there is no personal relief in current law
- [ ] Incorrect — personal relief EXISTS. The reference is: _______________

---

## SECTION 3: Pension Contributions

Our system calculates pension as:

| Contribution | Rate | Applied To |
|-------------|------|------------|
| Employee | 7% | Basic salary |
| Employer | 11% | Basic salary |
| Ceiling | None | No maximum cap |

**Source:** Proclamation No. 1268/2022, Article 10

**Your confirmation needed:**
- [ ] These rates are correct
- [ ] These rates are NOT correct. The correct rates are: _______________
- [ ] There IS a ceiling. The ceiling is: _______________

---

## SECTION 4: Overtime Rates

Our system calculates overtime as:

| Type | Rate | Example (ETB 100/hr base) |
|------|------|---------------------------|
| Day overtime | 1.5× hourly rate | ETB 150/hr |
| Night overtime | 1.75× hourly rate | ETB 175/hr |
| Holiday overtime | 2.0× hourly rate | ETB 200/hr |
| Rest day + holiday | 2.5× hourly rate | ETB 250/hr |

**Hourly rate calculation:** Monthly salary ÷ 208 (26 days × 8 hours)

**Limits:**
- Maximum 4 hours per day
- Maximum 12 hours per week
- Monthly limit (admin control): 20 hours
- Yearly limit (admin control): 100 hours

**Source:** Proclamation No. 1156/2019, Articles 67-68

**Your confirmation needed:**
- [ ] These rates are correct
- [ ] These rates are NOT correct. The correct rates are: _______________
- [ ] The hourly rate divisor should be different: _______________

---

## SECTION 5: Leave Entitlements

| Leave Type | Our System | Source |
|------------|-----------|--------|
| Annual leave (year 1) | 16 days | Art. 77(1)(a) |
| Annual leave increase | +1 day every 2 years | Art. 77(1)(b) |
| Annual leave maximum | 30 days (company policy) | Not in law |
| Sick leave | 180 days (6 months) | Art. 85(2) |
| Sick pay (days 1-30) | 100% of salary | Art. 86(1) |
| Sick pay (days 31-90) | 50% of salary | Art. 86(2) |
| Sick pay (days 91-180) | 0% (unpaid) | Art. 86(3) |
| Maternity leave | 120 days | Art. 88(3) |
| Paternity leave | 3 days | Art. 81(2) |
| Special leave | 5 days unpaid, max 2×/year | Art. 81(3) |

**Source:** Proclamation No. 1156/2019

**Your confirmation needed:**
- [ ] These entitlements are correct
- [ ] Something is wrong. The correct value is: _______________

---

## SECTION 6: Severance Pay

**Formula:**
- Year 1: 30 days (1 month) basic salary
- Each additional year: +10 days basic salary
- Maximum: 12 months basic salary
- Eligible reasons: redundancy, mutual agreement

**Source:** Proclamation No. 1156/2019, Article 40

**Your confirmation needed:**
- [ ] This formula is correct
- [ ] This formula is NOT correct. The correct formula is: _______________

---

## SECTION 7: ERCA Filing

**What our system generates:** A monthly tax filing report with these columns:

| Column | Description |
|--------|-------------|
| Employee Full Name | Employee name |
| Start Date | Employment start date |
| End Date | Employment end date (if applicable) |
| Basic Salary | Monthly basic salary in ETB |
| Transport Allowance | Monthly transport allowance |
| Taxable Transport Allowance | Taxable portion of transport |
| Over Time | Overtime pay for the period |
| Other Taxable Benefit | Other taxable benefits |
| Total Taxable | Total taxable income |
| Tax Withheld | Monthly income tax |

**These columns match:** A real ERCA filing that was successfully uploaded for 146 employees.

**Your confirmation needed:**
- [ ] These columns match what the ERCA portal expects in my region
- [ ] These columns do NOT match. The correct columns are: _______________
- [ ] The portal accepts .xlsx files
- [ ] The portal requires .csv files
- [ ] TIN is required in the filing
- [ ] TIN is NOT required in the filing

---

## SECTION 8: Cash Payment Limit

**Our system:** Flags any salary above ETB 50,000 for electronic payment.

**Source:** Proclamation No. 1395/2025, Article 81

**Your confirmation needed:**
- [ ] ETB 50,000 is the correct limit
- [ ] The correct limit is: _______________

---

## SECTION 9: Compliance Deadlines

Our system tracks these deadlines (configurable per company):

| Filing | Default Deadline |
|--------|-----------------|
| ERCA tax filing | 25th of following month |
| Pension remittance | 10th of following month |
| PSSA contribution | 10th of following month |
| Salary disbursement | 5 days after month end |

**Your confirmation needed:**
- [ ] These deadlines are correct for my region
- [ ] The correct deadlines for my region are: _______________

---

## HOW TO RETURN THIS DOCUMENT

1. Print this document (or edit the digital copy)
2. Check [ ] the boxes that apply
3. Write corrections in the blank spaces
4. Return to us via email / WhatsApp / in person

**Questions?** Contact us at: _______________

---

## WHAT HAPPENS AFTER YOU RETURN THIS

1. We fix anything you flagged
2. We send you the corrected version for final approval
3. Once approved, the system is ready for pilot companies

**Thank you for your time. Your review helps ensure Ethiopian businesses get accurate, compliant payroll calculations.**

---

*This document is part of the EthioPayroll production readiness process.*
