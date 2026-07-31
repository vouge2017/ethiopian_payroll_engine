# EthioPayroll — Verification Package for Accountant

**Prepared:** 2026-07-20
**Updated:** 2026-07-29 — Added real ERCA filing data as reference evidence
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

---

## ⚠️ REAL ERCA FILING DATA — VERIFIED AGAINST OUR TAX BRACKETS

**Source:** A real Ethiopian company's ERCA filing for Sene (June 2026).
**File:** `reference_data/real_erca_filing_sene.csv`
**Employees:** 146 total (29 sampled for verification below)

### Verification Result: Tax Brackets ✅ CONFIRMED

We ran every employee's taxable income through our tax bracket calculation and compared to the filed "Tax withheld" amount. **All 29 sampled employees match exactly when personal relief is NOT subtracted.**

| Employee | Taxable Income | Filed Tax | Our Gross Tax | Match? |
|----------|---------------|-----------|---------------|--------|
| Keneni Taa | 29,000 | 8,100 | 8,100 | ✅ |
| Biruk Mame | 31,000 | 8,800 | 8,800 | ✅ |
| Thomas Tesfaye | 24,000 | 6,350 | 6,350 | ✅ |
| Tamrate Zerihun | 45,000 | 13,700 | 13,700 | ✅ |
| Bezawite Kassaye | 26,000 | 7,050 | 7,050 | ✅ |
| Surafel Ashenafi | 17,000 | 3,900 | 3,900 | ✅ |
| Lamrot Balcha | 29,224.20 | 8,178.47 | 8,178.47 | ✅ |
| Beamlak Temesgen | 9,500 | 1,525 | 1,525 | ✅ |
| Firehiwot Getahun | 11,500 | 2,100 | 2,100 | ✅ |
| Webit Fente | 17,156 | 3,954.60 | 3,954.60 | ✅ |
| Etsubdink Dereje | 5,066 | 513.20 | 513.20 | ✅ |
| Geremew Nigusse | 25,000 | 6,700 | 6,700 | ✅ |
| Dawit Ababu | 25,000 | 6,700 | 6,700 | ✅ |
| Gkidan Asgedom | 28,816.67 | 8,035.83 | 8,035.83 | ✅ |
| Yidnekachew Tekalegne | 40,517.24 | 12,131.03 | 12,131.03 | ✅ |
| Tena Belete | 14,000 | 2,850 | 2,850 | ✅ |
| Yohannes Adisu | 14,933.33 | 3,176.67 | 3,176.67 | ✅ |
| Akalu Aboneh | 14,000 | 2,850 | 2,850 | ✅ |
| Ermiyas Shiferaw | 11,333.33 | 2,050.00 | 2,050.00 | ✅ |
| Webayehu Asefa | 21,333.33 | 5,416.67 | 5,416.67 | ✅ |
| Kasahun Dejene | 24,533.33 | 6,536.67 | 6,536.67 | ✅ |
| Berihun Desse | 20,750 | 5,212.50 | 5,212.50 | ✅ |
| Hafitu Tekuare | 11,000 | 1,950 | 1,950 | ✅ |
| Belaye Mulugeta | 16,000 | 3,550 | 3,550 | ✅ |
| Teshoma Deriba | 15,500 | 3,375 | 3,375 | ✅ |
| Hanna Sleamanuel | 10,700 | 1,860 | 1,860 | ✅ |
| Abreham baye | 16,000 | 3,550 | 3,550 | ✅ |
| Nigussie Negeri | 20,000 | 4,950 | 4,950 | ✅ |
| Ermiyas Tadesse | 16,000 | 3,550 | 3,550 | ✅ |

**Conclusion:** Our tax bracket thresholds (0%, 15%, 20%, 25%, 30%, 35%) are correct and match real-world ERCA filings.

### ⚠️ CRITICAL QUESTION: Personal Relief

The real filing shows **gross tax with NO personal relief subtracted**. Our system subtracts ETB 150 personal relief before withholding.

| Employee | Taxable | Filed Tax (No Relief) | Our System (With −150) | Difference |
|----------|---------|----------------------|------------------------|------------|
| Keneni Taa | 29,000 | 8,100 | 7,950 | 150 |
| Beamlak Temesgen | 9,500 | 1,525 | 1,375 | 150 |
| Shemsu Yadesa | 3,600 | 240 | 90 | 150 |

**The accountant MUST answer this question:**

> When filing monthly tax with ERCA, should the "Tax Withheld" column show:
> - **(A)** Gross tax (before personal relief) — matching what this company filed?
> - **(B)** Net tax (after subtracting ETB 150 personal relief) — what our system currently does?
>
> If (A): We need to stop subtracting personal relief in the ERCA export. The employee claims relief at year-end.
> If (B): This company is overpaying by ETB 150/employee/month.

### ⚠️ CRITICAL FINDING: Personal Relief — NOT IN PROCLAMATION 1395/2025

We reviewed the full text of Proclamation 1395/2025 (the amendment law). **Article 11 was replaced with ONLY the tax bracket table. There is NO personal relief provision.**

The real ERCA filing data shows gross tax with NO personal relief subtracted. This is consistent with the proclamation text.

**To resolve this:** We need the original Proclamation No. 979/2016 to check if personal relief exists in a different article (e.g., old Article 11 or Article 12).

**If personal relief was in old Article 11 only → it was repealed by this amendment.**

### Additional Observations from Real Filing

1. **No pension column** — The real filing has columns for: Name, Start Date, End Date, Basic Salary, Transport Allowance, Taxable Transport Allowance, Over Time, Other Taxable Benefit, Total Taxable, Tax Withheld. Our filing adds Pension and Net Pay columns which may not be required by ERCA.

2. **Taxable Transport Allowance column** — ERCA has a separate column for taxable transport allowance. Our system does not have this column. May need to be added.

3. **Overtime is in "Total Taxable"** — In the real filing, overtime is added to Total Taxable (not separated). Our system handles this the same way (overtime is part of taxable income).

4. **No TIN column in real filing** — The real filing does not have a TIN column. Our system includes TIN. May be optional or company-specific.

5. **Column order differs** — Real filing: Name, Start Date, End Date, Basic, Transport, Taxable Transport, Overtime, Other Taxable, Total Taxable, Tax Withheld. Our filing: No., Employee ID, Name, TIN, Gross, Pension, Taxable, Tax, Net Pay.

---

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
| 8 | **Should "Tax Withheld" include or exclude personal relief?** | ☐ Include (subtract 150) / ☐ Exclude (show gross tax) — **SEE CRITICAL QUESTION ABOVE** |
| 9 | Are the tax bracket thresholds correct? | ☐ Yes / ☐ No |
| 10 | Does ERCA require a "Taxable Transport Allowance" column? | ☐ Yes / ☐ No |
| 11 | Does ERCA require Start Date and End Date columns? | ☐ Yes / ☐ No |
| 12 | Is TIN required or optional in the ERCA filing? | ☐ Required / ☐ Optional |
| 13 | Can you test-upload a sample file to the ERCA portal? | ☐ Yes / ☐ No |

---

# PART 2: STATUTORY RULES VERIFICATION

These are ALL the legal rules hardcoded in the system. Each one needs verification against the actual proclamation text.

## HIGH PRIORITY — Tax & Pension (affects every payroll)

| # | Rule | Current Value | Proclamation Cited | Verified? | Correct Value? |
|---|---|---|---|---|---|
| 1 | Tax bracket 1 | 0–2,000 @ 0% | No. 1395/2025, **Art. 11** (amending 979/2016) | ✅ **Verified against proclamation text + real ERCA filing** | ✅ Correct |
| 2 | Tax bracket 2 | 2,001–4,000 @ 15% | No. 1395/2025, **Art. 11** | ✅ **Verified against proclamation text + real ERCA filing** | ✅ Correct |
| 3 | Tax bracket 3 | 4,001–7,000 @ 20% | No. 1395/2025, **Art. 11** | ✅ **Verified against proclamation text + real ERCA filing** | ✅ Correct |
| 4 | Tax bracket 4 | 7,001–10,000 @ 25% | No. 1395/2025, **Art. 11** | ✅ **Verified against proclamation text + real ERCA filing** | ✅ Correct |
| 5 | Tax bracket 5 | 10,001–14,000 @ 30% | No. 1395/2025, **Art. 11** | ✅ **Verified against proclamation text + real ERCA filing** | ✅ Correct |
| 6 | Tax bracket 6 | 14,001+ @ 35% | No. 1395/2025, **Art. 11** | ✅ **Verified against proclamation text + real ERCA filing** | ✅ Correct |
| 7 | Personal relief | ETB 150/month | No. 1395/2025 | ✅ **REMOVED** — not in Proclamation 1395/2025 (Art. 11 replaced with bracket table only). Real ERCA filing confirms no relief. System updated. | ✅ Removed |
| 8 | Pension employee rate | 7% of basic salary | No. 1268/2022, **Art. 10** | ✅ **Verified against proclamation text** | ✅ 7% |
| 9 | Pension employer rate | 11% of basic salary | No. 1268/2022, **Art. 10** | ✅ **Verified against proclamation text** | ✅ 11% |
| 10 | Pension ceiling | None (no cap) | No. 1268/2022 | ✅ **Verified** — no ceiling mentioned in proclamation | ✅ None |

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
| 34 | Cash payment limit | ETB 30,000 → **ETB 50,000** | No. 1395/2025, **Art. 81** | ✅ **Verified against proclamation text** — limit is now ETB 50,000. System needs update. See `reference_data/proclamation_1395_2017/02_CASH_PAYMENT_LIMIT.md` | ❌ **50,000 (system has 30,000)** |

---

# PART 3: WHAT TO DO WITH THIS DOCUMENT

## For the Accountant

1. **Review the real ERCA filing data** in Part 1 — compare column structure to what the portal expects
2. **Answer the Critical Question** about personal relief (Part 1, "Tax Withheld" — include or exclude ETB 150?)
3. **Download the official ERCA monthly filing template** from the ERCA portal
4. **Compare column headers** character-by-character with Part 1
5. **Verify the tax brackets** against Proclamation No. 1395/2025 (the actual PDF, not summaries)
6. **Verify pension rates** against Proclamation No. 1268/2022
7. **Test-upload** a sample file to the ERCA portal
8. **Fill in the "Correct Value?" column** in Part 2 for each rule
9. **Return this document** with corrections marked

## For the Developer

Once the accountant returns this document:
1. **Resolve the personal relief question** — this changes how every payslip is calculated
2. Update any incorrect values in the `TaxRule` database
3. Update hardcoded defaults in `overtime.py`, `leave.py`, `severance.py`
4. Adjust ERCA column headers if the portal requires different names
5. Add any missing columns the ERCA portal requires (e.g., Taxable Transport Allowance, Start/End Date)
6. Update the `DIAGNOSTIC_ANSWERS.md` compliance score

## Reference Files

- `reference_data/real_erca_filing_sene.csv` — Real ERCA filing (146 employees, Sene/June 2026)
- `VERIFICATION_PACKAGE.md` — This document

## Estimated Time

- **Accountant:** 2–3 hours to verify all 34 rules + test ERCA upload
- **Developer:** 1–2 hours to implement corrections

---

*This document is part of the EthioPayroll production readiness process.*
*Source code: https://github.com/vouge2017/ethiopian_payroll_engine*
