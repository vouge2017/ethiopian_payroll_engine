# EthioPayroll — Verification Package for Accountant

**Prepared:** 2026-07-20
**Purpose:** Send this document to an Ethiopian accountant or tax compliance officer for verification.
**Contains:** ERCA format verification + statutory rule verification checklist

---

# PART 1: ERCA EXPORT FORMAT VERIFICATION

## What the System Generates

A monthly tax filing report in `.xlsx` (Excel) format with 9 columns:

| Column | Header | Description |
|---|---|---|
| A | No. | Sequential row number |
| B | Employee ID | Company employee identifier |
| C | Employee Name | Full name |
| D | TIN | Tax Identification Number |
| E | Gross Salary | Monthly gross in ETB |
| F | Pension 7% | Employee pension (7% of basic salary) |
| G | Taxable Income | Gross − Pension |
| H | Tax Withheld | Monthly income tax |
| I | Net Pay | Take-home pay |

## Sample Export — June 2026

**Company:** Addis Global Trading PLC

| No. | Employee ID | Name | TIN | Gross | Pension 7% | Taxable | Tax | Net Pay |
|---|---|---|---|---|---|---|---|---|
| 1 | EMP001 | Abebe Kebede | 1234567890 | 15,000 | 1,050 | 13,950 | 2,685 | 11,265 |
| 2 | EMP002 | Fatuma Hassan | 0987654321 | 8,000 | 560 | 7,440 | 1,610 | 5,830 |
| 3 | EMP003 | Gebrehiwot Tesfaye | 1122334455 | 5,500 | 385 | 5,115 | 500 | 4,615 |
| 4 | EMP004 | Hana Mulugeta | 5566778899 | 3,500 | 245 | 3,255 | 38.25 | 3,216.75 |
| 5 | EMP005 | Yonas Daniel | 9988776655 | 18,000 | 1,260 | 16,740 | 3,689 | 13,051 |
| | | **TOTALS** | | **50,000** | **3,500** | **46,500** | **8,522.25** | **37,977.75** |

## Tax Calculation — Step by Step

### Abebe Kebede (Gross ETB 15,000)

| Step | Calculation | Amount |
|---|---|---|
| Gross Salary | | 15,000.00 |
| Pension (7% of basic) | 15,000 × 0.07 | 1,050.00 |
| Taxable Income | 15,000 − 1,050 | 13,950.00 |
| Bracket 0–2,000 @ 0% | 2,000 × 0% | 0.00 |
| Bracket 2,001–4,000 @ 15% | 2,000 × 15% | 300.00 |
| Bracket 4,001–7,000 @ 20% | 3,000 × 20% | 600.00 |
| Bracket 7,001–10,000 @ 25% | 3,000 × 25% | 750.00 |
| Bracket 10,001–14,000 @ 30% | 3,950 × 30% | 1,185.00 |
| Gross Tax | | 2,835.00 |
| Personal Relief | | −150.00 |
| **Tax Withheld** | | **2,685.00** |
| **Net Pay** | 15,000 − 1,050 − 2,685 | **11,265.00** |

### Hana Mulugeta (Gross ETB 3,500 — low-income)

| Step | Calculation | Amount |
|---|---|---|
| Gross Salary | | 3,500.00 |
| Pension (7%) | 3,500 × 0.07 | 245.00 |
| Taxable Income | 3,500 − 245 | 3,255.00 |
| Bracket 0–2,000 @ 0% | 2,000 × 0% | 0.00 |
| Bracket 2,001–4,000 @ 15% | 1,255 × 15% | 188.25 |
| Gross Tax | | 188.25 |
| Personal Relief | | −150.00 |
| **Tax Withheld** | | **38.25** |
| **Net Pay** | 3,500 − 245 − 38.25 | **3,216.75** |

## ERCA Verification Checklist

| # | Question | Answer Needed |
|---|---|---|
| 1 | Do these 9 column headers match the ERCA portal upload template exactly? | ☐ Yes / ☐ No — correct headers: __________ |
| 2 | Does the ERCA portal accept `.xlsx` files? | ☐ Yes / ☐ No — required format: __________ |
| 3 | Is the TIN format correct (9-10 digits)? | ☐ Yes / ☐ No |
| 4 | Is pension calculated on basic salary or gross salary? | ☐ Basic / ☐ Gross |
| 5 | Is employer pension (11%) required in the same filing? | ☐ Yes / ☐ No |
| 6 | Are there missing columns ERCA requires? | ☐ No / ☐ Yes — list: __________ |
| 7 | Is personal relief ETB 150/month correct? | ☐ Yes / ☐ No — correct amount: __________ |
| 8 | Are the tax bracket thresholds correct? | ☐ Yes / ☐ No |
| 9 | Can you test-upload a sample file to the ERCA portal? | ☐ Yes / ☐ No |

---

# PART 2: STATUTORY RULES VERIFICATION

These are ALL the legal rules hardcoded in the system. Each one needs verification against the actual proclamation text.

## HIGH PRIORITY — Tax & Pension (affects every payroll)

| # | Rule | Current Value | Proclamation Cited | Verified? | Correct Value? |
|---|---|---|---|---|---|
| 1 | Tax bracket 1 | 0–2,000 @ 0% | No. 1395/2025, Art. 36(1) | ☐ | __________ |
| 2 | Tax bracket 2 | 2,001–4,000 @ 15% | No. 1395/2025, Art. 36(1) | ☐ | __________ |
| 3 | Tax bracket 3 | 4,001–7,000 @ 20% | No. 1395/2025, Art. 36(1) | ☐ | __________ |
| 4 | Tax bracket 4 | 7,001–10,000 @ 25% | No. 1395/2025, Art. 36(1) | ☐ | __________ |
| 5 | Tax bracket 5 | 10,001–14,000 @ 30% | No. 1395/2025, Art. 36(1) | ☐ | __________ |
| 6 | Tax bracket 6 | 14,001+ @ 35% | No. 1395/2025, Art. 36(1) | ☐ | __________ |
| 7 | Personal relief | ETB 150/month | No. 1395/2025 | ☐ | __________ |
| 8 | Pension employee rate | 7% of basic salary | No. 1268/2022 | ☐ | __________ |
| 9 | Pension employer rate | 11% of basic salary | No. 1268/2022 | ☐ | __________ |
| 10 | Pension ceiling | None (no cap) | No. 1268/2022 | ☐ | __________ |

## MEDIUM PRIORITY — Overtime & Severance

| # | Rule | Current Value | Proclamation Cited | Verified? | Correct Value? |
|---|---|---|---|---|---|
| 11 | Overtime day rate | 1.25× hourly | No. 1156/2019, Art. 68(1) | ☐ | __________ |
| 12 | Overtime night rate | 1.50× hourly | No. 1156/2019, Art. 68(2) | ☐ | __________ |
| 13 | Overtime holiday rate | 2.0× hourly | No. 1156/2019, Art. 68(3) | ☐ | __________ |
| 14 | Overtime rest+holiday | 2.5× hourly | No. 1156/2019, Art. 68(4) | ☐ | __________ |
| 15 | Overtime monthly limit | 20 hours | No. 1156/2019, Art. 89 | ☐ | __________ |
| 16 | Overtime yearly limit | 100 hours | No. 1156/2019, Art. 89 | ☐ | __________ |
| 17 | Hourly rate divisor | 208 (26 days × 8 hrs) | Ethiopian convention | ☐ | __________ |
| 18 | Severance formula | salary × years | No. 1156/2019, Art. 40-42 | ☐ | __________ |
| 19 | Severance cap | 12 months max | No. 1156/2019, Art. 42 | ☐ | __________ |

## MEDIUM PRIORITY — Leave Entitlements

| # | Rule | Current Value | Proclamation Cited | Verified? | Correct Value? |
|---|---|---|---|---|---|
| 20 | Annual leave (year 1) | 14 days | No. 1156/2019 | ☐ | __________ |
| 21 | Annual leave increment | +1 day per year | No. 1156/2019 | ☐ | __________ |
| 22 | Annual leave max | 30 days | "Reasonable cap" | ☐ | __________ |
| 23 | Sick leave max | 180 days (6 months) | No. 1156/2019 | ☐ | __________ |
| 24 | Sick pay tier 1 | Days 1–30: 100% | No. 1156/2019 | ☐ | __________ |
| 25 | Sick pay tier 2 | Days 31–90: 50% | No. 1156/2019 | ☐ | __________ |
| 26 | Sick pay tier 3 | Days 91–180: 0% | No. 1156/2019 | ☐ | __________ |
| 27 | Maternity leave | 120 days | No. 1156/2019 | ☐ | __________ |
| 28 | Paternity leave | 3 days | No. 1156/2019 | ☐ | __________ |
| 29 | Special leave | 3 days | No. 1156/2019 | ☐ | __________ |

## LOW PRIORITY — Compliance Deadlines

| # | Rule | Current Value | Source | Verified? | Correct Value? |
|---|---|---|---|---|---|
| 30 | ERCA filing deadline | 25th of following month | Common practice | ☐ | __________ |
| 31 | Pension payment deadline | 15th of following month | Common practice | ☐ | __________ |
| 32 | Salary disbursement deadline | 5 days after period end | Common practice | ☐ | __________ |
| 33 | Tax record retention | 10 years (3650 days) | "Ethiopian tax law" | ☐ | __________ |
| 34 | Cash payment limit | ETB 30,000 | No. 1395/2025 | ☐ | __________ |

---

# PART 3: WHAT TO DO WITH THIS DOCUMENT

## For the Accountant

1. **Download the official ERCA monthly filing template** from the ERCA portal
2. **Compare column headers** character-by-character with Part 1
3. **Verify the tax brackets** against Proclamation No. 1395/2025 (the actual PDF, not summaries)
4. **Verify pension rates** against Proclamation No. 1268/2022
5. **Test-upload** a sample file to the ERCA portal
6. **Fill in the "Correct Value?" column** in Part 2 for each rule
7. **Return this document** with corrections marked

## For the Developer

Once the accountant returns this document:
1. Update any incorrect values in the `TaxRule` database
2. Update hardcoded defaults in `overtime.py`, `leave.py`, `severance.py`
3. Adjust ERCA column headers if the portal requires different names
4. Add any missing columns the ERCA portal requires
5. Update the `DIAGNOSTIC_ANSWERS.md` compliance score

## Estimated Time

- **Accountant:** 2–3 hours to verify all 34 rules + test ERCA upload
- **Developer:** 1–2 hours to implement corrections

---

*This document is part of the EthioPayroll production readiness process.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
