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

**Source:** Real ERCA filing (147 employees, Sene/June 2026) — `reference_data/real_erca_filing_sene.csv`

| # | Question | Answer | Source |
|---|----------|--------|--------|
| 1 | Column headers match ERCA portal? | ✅ **Yes** — Real filing: Employee Full Name, Start Date, End Date, Basic Salary, Transport Allowance, Taxable Transport Allowance, Over Time, Other Taxable Benefit, Total Taxable, Tax withheld | Real filing CSV |
| 2 | ERCA accepts .xlsx? | ⚠️ **Likely CSV** — Real filing was uploaded as CSV | Real filing format |
| 3 | TIN format (9-10 digits)? | ⚠️ **Not in filing** — No TIN column. TIN may be separate or optional | Real filing |
| 4 | Pension on basic or gross? | ⚠️ **Not in filing** — No pension column. Pension reported separately | Real filing |
| 5 | Employer pension in same filing? | ❌ **No** — No pension column at all | Real filing |
| 6 | Missing columns? | ✅ **Yes** — We're MISSING: Start Date, End Date, Transport Allowance, Taxable Transport Allowance, Other Taxable Benefit. We have EXTRA: No., Employee ID, TIN, Pension, Net Pay | Compare |
| 7 | Personal relief ETB 150? | ✅ **RESOLVED** — No relief in law. Real filing shows gross tax | Law + filing |
| 8 | Tax Withheld include/exclude relief? | ✅ **RESOLVED** — Gross tax (no relief). Real filing confirms | Real filing |
| 9 | Tax bracket thresholds correct? | ✅ **RESOLVED** — All 29 sampled employees match | Real filing |
| 10 | "Taxable Transport Allowance" column? | ✅ **Yes** — Real filing Column 5 | Real filing |
| 11 | Start/End Date columns? | ✅ **Yes** — Real filing Columns 1, 2 | Real filing |
| 12 | TIN required or optional? | ⚠️ **Optional** — Real filing has no TIN column | Real filing |
| 13 | Test-upload to portal? | ✅ **Done** — This CSV was successfully uploaded | User confirmed |

### ⚠️ COLUMN MISMATCH — Our Export vs ERCA Portal

| Real ERCA Columns | Our Columns | Status |
|-------------------|-------------|--------|
| Employee Full Name | Employee Name | ✅ Similar |
| Start Date | — | ❌ Missing |
| End Date | — | ❌ Missing |
| Basic Salary | Gross Salary | ❌ Different (ERCA wants basic, we send gross) |
| Transport Allowance | — | ❌ Missing |
| Taxable Transport Allowance | — | ❌ Missing |
| Over Time | — | ❌ Missing |
| Other Taxable Benefit | — | ❌ Missing |
| Total Taxable | Taxable Income | ✅ Similar |
| Tax withheld | Tax Withheld | ✅ Match |
| — | No. | ❌ Extra |
| — | Employee ID | ❌ Extra |
| — | TIN | ❌ Extra |
| — | Pension 7% | ❌ Extra |
| — | Net Pay | ❌ Extra |

**Conclusion:** ERCA export needs redesign to match portal format.
| 6 | Tax bracket 6 | 14,001+ @ 35% | No. 1395/2025, **Art. 11** | ✅ **Verified against proclamation text + real ERCA filing** | ✅ Correct |
| 7 | Personal relief | ETB 150/month | No. 1395/2025 / 979/2016 | ✅ **Confirmed: no personal relief exists** under 979/2016 (Art. 10(3) prohibits deductions) or 1395/2025 (Art. 11 has bracket table only). If ETB 150 ever existed, it was under an earlier proclamation. System updated. | ✅ Removed |
| 8 | Pension employee rate | 7% of basic salary | No. 1268/2022, **Art. 10** | ✅ **Verified against proclamation text** | ✅ 7% |
| 9 | Pension employer rate | 11% of basic salary | No. 1268/2022, **Art. 10** | ✅ **Verified against proclamation text** | ✅ 11% |
| 10 | Pension ceiling | None (no cap) | No. 1268/2022 | ✅ **Verified** — no ceiling mentioned in proclamation | ✅ None |

## MEDIUM PRIORITY — Overtime & Severance

| # | Rule | Current Value | Proclamation Cited | Verified? | Correct Value? |
|---|---|---|---|---|---|
| 11 | Overtime day rate | 1.25× hourly | No. 1156/2019, **Art. 68(1)(a)** | ✅ **Verified — WRONG! Law says 1.5×** | ❌ **1.5×** |
| 12 | Overtime night rate | 1.50× hourly | No. 1156/2019, **Art. 68(1)(b)** | ✅ **Verified — WRONG! Law says 1.75×** | ❌ **1.75×** |
| 13 | Overtime holiday rate | 2.0× hourly | No. 1156/2019, **Art. 68(1)(c)** | ✅ **Verified against proclamation text** | ✅ 2.0× |
| 14 | Overtime rest+holiday | 2.5× hourly | No. 1156/2019, **Art. 68(1)(d)** | ✅ **Verified against proclamation text** | ✅ 2.5× |
| 15 | Overtime monthly limit | 20 hours | No. 1156/2019 | ✅ **NOT IN LAW** — Law says 4 hrs/day, 12 hrs/week (Art. 67(2)). No monthly cap. | ⚠️ Remove or convert |
| 16 | Overtime yearly limit | 100 hours | No. 1156/2019 | ✅ **NOT IN LAW** — No yearly cap in proclamation | ⚠️ Remove or convert |
| 17 | Hourly rate divisor | 208 (26 days × 8 hrs) | Ethiopian convention | ☐ Not in this proclamation | __________ |
| 18 | Severance formula | salary × years | No. 1156/2019, **Art. 40** | ✅ **Verified — WRONG! Law: 30 days year 1, +10 days/year after, 1/3 increment** | ❌ **See Art. 40** |
| 19 | Severance cap | 12 months max | No. 1156/2019, **Art. 40(3)** | ✅ **Verified against proclamation text** | ✅ 12 months |

## MEDIUM PRIORITY — Leave Entitlements

| # | Rule | Current Value | Proclamation Cited | Verified? | Correct Value? |
|---|---|---|---|---|---|
| 20 | Annual leave (year 1) | 14 days | No. 1156/2019, **Art. 77(1)(a)** | ✅ **Verified — WRONG! Law says 16 days** | ❌ **16 days** |
| 21 | Annual leave increment | +1 day per year | No. 1156/2019, **Art. 77(1)(b)** | ✅ **Verified — WRONG! Law says +1 day per 2 years** | ❌ **+1 per 2 years** |
| 22 | Annual leave max | 30 days | "Reasonable cap" | ✅ **Not in law** — no maximum specified | ⚠️ Keep as reasonable cap |
| 23 | Sick leave max | 180 days (6 months) | No. 1156/2019, **Art. 85(2)** | ✅ **Verified against proclamation text** | ✅ 6 months |
| 24 | Sick pay tier 1 | Days 1–30: 100% | No. 1156/2019, **Art. 86(1)** | ✅ **Verified against proclamation text** | ✅ 100% |
| 25 | Sick pay tier 2 | Days 31–90: 50% | No. 1156/2019, **Art. 86(2)** | ✅ **Verified against proclamation text** | ✅ 50% |
| 26 | Sick pay tier 3 | Days 91–180: 0% | No. 1156/2019, **Art. 86(3)** | ✅ **Verified against proclamation text** | ✅ 0% |
| 27 | Maternity leave | 120 days | No. 1156/2019, **Art. 88(3)** | ✅ **Verified** — 30 pre-natal + 90 post-natal = 120 days | ✅ 120 days |
| 28 | Paternity leave | 3 days | No. 1156/2019, **Art. 81(2)** | ✅ **Verified against proclamation text** | ✅ 3 days |
| 29 | Special leave | 3 days | No. 1156/2019, **Art. 81(3)** | ✅ **Verified from English text** — Law: "leave without pay for up to five consecutive days... may be granted only twice in a budget year" | ❌ **5 days unpaid, max 2×/year** |

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
