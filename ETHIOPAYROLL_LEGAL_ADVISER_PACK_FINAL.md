# EthioPayroll — Ethiopian payroll legal adviser pack

**Prepared:** 30 October 2026
**Purpose:** Request written professional interpretation of five Ethiopian payroll-law topics.
**Scope:** This is a source-backed question pack, not a legal opinion, compliance certification, or approval to change payroll calculations.

## How to answer

For each answer, please identify the law and version relied on, exact provision, effective date, and any current official form, directive or portal instruction. Please distinguish the wording of the law from your professional interpretation. Where the evidence is incomplete, please mark the answer unresolved and identify the document or authority needed to resolve it.

### Status labels used

- **CONFIRMED LEGAL PROVISION:** The stated proposition is supported by an identified legal source; this does not resolve how it applies to every payroll case.
- **PROFESSIONAL INTERPRETATION REQUIRED:** The text exists, but its application is uncertain.
- **OFFICIAL GUIDANCE UNVERIFIED:** No identifiable current official guidance supporting the operational claim has been located.
- **DEVELOPMENT RECOMMENDATION:** A software control suggestion, not a legal requirement.
- **IMPLEMENTATION BLOCKED:** Do not treat the disputed calculation or workflow as legally approved.

## 1. Transport allowance and per diem exemptions

**Legal question.** Which transport, travel and per diem payments qualify for income-tax exemption, and what limits, salary base and evidence apply?

**Sources and provisions.** Income Tax Proclamation No. 979/2016, Article 65(1)(a), addresses specified employee benefits and employment travel payments, subject to limitations set by directive. The Ministry of Revenue's *Federal Income Tax Proclamation No. 979/2016 Technical Notes* discusses Article 65(1)(a), including contractual transportation allowance and transport expenses/per diem for employment travel. The Ministry of Justice hosts an Amharic exempt-income directive PDF labelled No. 200/2013 (Arts. 5, 6 and 14); the Ministry of Finance's tax-directive index lists a file labelled No. 1/2011. Their identity, operative status and amendment history have not been established. Regulation No. 410/2017, Article 54(1)(b)-(c), also addresses qualifying unskilled casual workers.

**CONFIRMED LEGAL PROVISION.** Article 65 establishes the listed exemption categories, with limitations to be set by directive. It does not itself state the numerical transport or per diem limits discussed below.

**TECHNICAL NOTE SUPPORT — NOT AN INDEPENDENT BINDING RULE.** The Ministry of Revenue technical note explains the statutory categories and that transport/per diem exemption amounts are subject to directive limits. It is explanatory material; it does not by itself resolve which directive is operative or replace its text.

**PROVISIONAL READING — NOT CONFIRMED.** A reading of the Justice-hosted Amharic directive PDF suggests transport figures including 25% of salary capped at ETB 2,200 and home-to-work transport of ETB 600, and daily domestic per diem figures expressed as the greater of a fixed amount or a percentage for specified employee categories. These amounts and formulas are not approved here: the directive identity/number, salary base, precise wording and current applicability remain unsettled. Secondary summaries conflict on the formula.

**PROFESSIONAL INTERPRETATION REQUIRED.** Confirm the operative directive and amendments; its correct number and relationship, if any, to the Ministry of Finance listing; the exact formula and salary base; employee categories; distance and travel tests; lodging/meal treatment; required evidence; and distinction between commuting allowance, contractual transport allowance and actual work-travel reimbursement. Regulation 410/2017 Article 54 contains a casual-worker test with period wording that requires interpretation, including what counts as the relevant prior employment period.

**Adviser question.** Please provide or identify the currently operative directive and amendments, confirm the exact exemption and formula for each payment type and employee category, identify the salary base and substantiation records, and explain the casual-worker rule in Regulation 410/2017 Article 54. Please state which conclusions come from binding text and which are interpretation.

**Payroll impact.** Payment classification, exempt/taxable portions, PAYE and evidence retention.

**Implementation status.** Categories may be represented as data fields (**DEVELOPMENT RECOMMENDATION**). Exact thresholds/formulas are **CONFIGURABLE PENDING CONFIRMATION**; production use of disputed exemption calculations is **IMPLEMENTATION BLOCKED**.

## 2. Correction of filed monthly PAYE returns

**Legal question.** What must an employer do after discovering an error in an already-submitted monthly PAYE declaration?

**Sources and provisions.** Federal Tax Administration Proclamation No. 983/2016, Article 29(1)-(5), is available in a publicly accessible non-government copy; an official government copy of the original text was not located in this review. Article 29(2) refers to the period in Article 28(2)(b)(1), and Article 29(3) states a 120-day period for the Authority's decision and refers to an Authority directive. Tax Administration Amendment Proclamation No. 1434/2026, **Article 2, item 4**, replaces Article 28(2); **Article 2, item 12**, adds Articles 97–102 concerning revision of assessment notices; **Article 3** provides that the amendment takes effect upon publication in the Federal Negarit Gazette. The official Gazette is dated 30 July 2026.

**CONFIRMED LEGAL PROVISION.** Article 2, item 4 of Proclamation 1434/2026 replaces Article 28(2) of Proclamation 983/2016. The amended Article 28(2) provides a five-year period for amendment of self-assessments counted from filing, five years for other assessments counted from issuance of the assessment notice, and ten years in the specified tax-fraud case. Article 2, item 12 adds a distinct assessment-notice revision framework in Articles 97–102. Article 3 makes the amendment effective upon Gazette publication. These are assessment provisions; they do not, by themselves, establish a five-year employer deadline for correcting a monthly PAYE declaration.

**PROFESSIONAL INTERPRETATION REQUIRED.** In the original text reviewed, Article 29 is not expressly amended by Proclamation 1434/2026. Its cross-reference to Article 28(2)(b)(1) must be read against the substituted Article 28(2). However, the original Article 29 copy was not government-hosted, and no consolidated official text was located. Do not infer from the assessment limitation period that Article 29 is the correct or exclusive route for amending a filed monthly PAYE declaration.

**OFFICIAL GUIDANCE UNVERIFIED.** No identifiable current Ministry of Revenue document was located that specifies the monthly PAYE return correction portal process, form, submission deadline, supporting documents, additional liabilities or overpayment procedure. Do not rely on an unnamed FAQ or transition guide.

**Adviser question.** Please confirm, in writing: (1) the assessment limitation period applicable under the amended Article 28; (2) the legal route for correcting an already-filed monthly PAYE declaration and whether Article 29 applies; (3) additional tax, interest and penalties; (4) overpayment, credit and refund treatment; and (5) the current portal/form, required documents and applicable submission deadlines. Please provide the official consolidated text or guidance relied on, including title, issuing authority, number, date and relevant provision.

**Payroll impact.** Historical-period correction, employee-level schedules, additional liability or overpayment, approvals, evidence and submission references.

**Implementation status.** Internal preservation and comparison controls are **DEVELOPMENT RECOMMENDATIONS**. The legal filing, payment/interest and credit/refund workflow is **OFFICIAL GUIDANCE UNVERIFIED** and **IMPLEMENTATION BLOCKED** pending an authoritative procedure.

## 3. Pension eligibility, the 45-day rule and multiple employers

**Legal question.** When does coverage and contribution liability start around the 45-day employee-definition threshold, and how is the multiple-employer election administered?

**Sources and provisions.** Private Organization Employees' Pension Proclamation No. 1268/2022: Article 2(1) defines a private-organization employee by reference to employment for not less than 45 days; Article 4(2) addresses notification of the employee's social-security identification number when joining another covered organization; Article 10 sets contribution rates; Article 52(2) addresses an employee employed and salaried by two or more private organizations; Article 53 concerns evidentiary data/cooperation. Official sources: [Proclamation 1268/2022](https://justice.gov.et/wp-content/uploads/2025/02/%E1%8A%A0%E1%8B%8B%E1%8C%85-%E1%89%81%E1%8C%A5%E1%88%AD-1268-2014.pdf) and [Directive 1085/2025 PDF](https://justice.gov.et/wp-content/uploads/2026/02/1085-Private-Organizations-Employees-Pension-Implementation-Directive-No.-1085-2025.pdf). The Ministry of Justice page associated with the directive shows 10 March 2026 but is titled as an explanatory note; the directive PDF says “Done at Addis Ababa, June 2025.”

**CONFIRMED LEGAL PROVISION.** Article 52(2), not Article 53(2), is the multiple-private-employer provision. It allows the contribution to be collected, according to the employee's choice, from salary paid by one of the private organizations, subject to the statutory qualification in that provision. Article 53 is a separate evidence/data and cooperation provision.

**PROFESSIONAL INTERPRETATION REQUIRED.** The 45-day definition alone does not establish whether contributions start on the first employment day, after 45 days, or retrospectively once the definition is met. Article 52(2)'s practical evidence, employer notification, election changes and duplicate-contribution controls also need clarification.

**OFFICIAL GUIDANCE UNVERIFIED.** Directive 1085/2025 Article 74 states an effectiveness condition involving registration by the Ministry of Justice and upload/publication on the Administration website. The Justice record page displays 10 March 2026 for an explanatory-note record, while the directive PDF is dated June 2025. No dated registration record or evidence of the required Administration-site upload/publication was located. Therefore the directive's effective date is **UNVERIFIED** in this pack; no conclusion is drawn that the condition has or has not been met.

**Adviser question.** How are the 45 days counted, and what date starts pension coverage and contributions? Are contributions due from the beginning of employment, only after qualification, or retrospectively? What written election and employer/Administration process implements Article 52(2)? Does Directive 1085/2025 clarify these questions, and can you provide evidence of its registration and required upload/publication date under Article 74?

**Payroll impact.** Pension enrolment, first-period deductions, employer contributions, remittance, multi-employer coordination and audit evidence.

**Implementation status.** The statutory provisions can be represented, but commencement and election procedures are **PROFESSIONAL INTERPRETATION REQUIRED**; Directive 1085/2025's effective date is **OFFICIAL GUIDANCE UNVERIFIED**. Eligibility commencement and election workflow are **IMPLEMENTATION BLOCKED** pending written confirmation.

## 4. Public-holiday work versus overtime

**Legal question.** How should ordinary scheduled work on a public holiday be paid, and how are hours also classified as overtime or weekly-rest-day work treated?

**Source and provisions.** Labour Proclamation No. 1156/2019, Articles 66–68 and 73–75. [Official Ministry of Justice Gazette PDF](https://justice.gov.et/wp-content/uploads/2025/02/%E1%8A%A0%E1%8B%8B%E1%8C%85-%E1%89%81%E1%8C%A5%E1%88%AD-1156-2011.pdf).

**CONFIRMED LEGAL PROVISION.** Article 66 defines overtime by reference to work beyond normal daily hours, subject to its provisions. Article 68(1)(d) sets the public-holiday overtime rate at not less than 2.5 times the ordinary hourly rate. Article 75(1) provides twice the hourly wage for each hour worked on a public holiday. Article 74(1) protects monthly-paid workers' wages where they do not work because of a public holiday.

**PROFESSIONAL INTERPRETATION REQUIRED.** The reviewed text does not settle how Article 75 payment interacts with ordinary monthly salary, or how a single hour overlapping public holiday, overtime and weekly rest day is classified and paid.

**Adviser question.** For monthly-paid and hourly-paid employees, what additional amount is due for scheduled public-holiday work? For hours also qualifying as overtime or weekly-rest-day work, which rate applies and can rates be combined? How should shifts crossing normal hours be classified, and what hourly divisor applies?

**Payroll impact.** Work-hour classification, holiday/overtime calculation, payroll totals and avoidance of underpayment or duplicate payment.

**Implementation status.** Statutory categories and rates are **CONFIRMED LEGAL PROVISIONS**; their interaction in disputed work patterns is **PROFESSIONAL INTERPRETATION REQUIRED** and **IMPLEMENTATION BLOCKED** pending confirmation.

## 5. Annual-leave pay and unused leave on termination

**Legal question.** Which wage components and divisor determine annual-leave pay and payment for unused leave at termination?

**Source and provisions.** Labour Proclamation No. 1156/2019, Articles 36, 53 and 76–78 (official Justice PDF linked in section 4).

**CONFIRMED LEGAL PROVISION.** Article 53 defines wages and excludes listed items, including overtime, per diem, hardship and transport allowances, relocation expenses, bonuses, commissions, incentives and service charges. Article 77(2) provides leave pay equal to the wage the worker would have received if work continued; Article 77(4) provides payment for unused leave on termination; Article 77(5) provides proportional entitlement for service below one year. Article 77(3)'s 26-day equivalence is for determining qualifying service for leave entitlement, not an express monetary divisor. Article 36 provides a seven-working-day period for payment of wages and other termination payments due, subject to its exception.

**PROFESSIONAL INTERPRETATION REQUIRED.** The reviewed provisions do not expressly establish a daily cash divisor. Application of the wage definition to actual fixed/variable components, partial periods, carried leave and termination requires confirmation.

**Adviser question.** Which current and variable components count as wages under Articles 53 and 77? What divisor and reference period apply to leave taken and unused leave paid at termination? How should partial years, variable pay, carryover and the Article 36 payment deadline be applied?

**Payroll impact.** Leave entitlement, leave-period pay, balances, termination amounts and payment timing.

**Implementation status.** Entitlement provisions are **CONFIRMED LEGAL PROVISIONS**; component selection and divisor are **PROFESSIONAL INTERPRETATION REQUIRED**, may be **CONFIGURABLE PENDING CONFIRMATION**, and disputed live calculations are **IMPLEMENTATION BLOCKED**.

## Development recommendations (not legal conclusions)

- Preserve submitted/approved originals and audit history; never silently overwrite a filed return or locked payroll period.
- Keep an internal period-difference calculation separate from filing an amended return or recording payment, credit or refund.
- Record the source, effective date, reviewer and employer decision for any configured rule.

These are software-control recommendations only. They do not establish a statutory process or approve any unresolved calculation.

## Change log from the prior pack

- Corrected Proclamation 1434/2026 citations: Article 2 item 4 amends Article 28; Article 2 item 12 adds Articles 97–102; Article 3 is the effective-date clause.
- Separated the Article 28 assessment limitation from any deadline for correcting an already-filed monthly PAYE declaration; operational correction, charges, refund/credit and portal process remain unverified.
- Recorded both Directive 1085/2025 dates and the Article 74 condition; effective date remains unverified without evidence of registration and upload/publication.
- Retained the correct pension multiple-employer reference, Article 52(2), and the unresolved 45-day commencement question.
- Downgraded exact transport/per diem figures to a provisional reading, separated the Ministry of Revenue technical note from binding text, and retained the directive/salary-base/formula gap.
- Repaired encoding and aligned legal and implementation status labels across the pack and companion registers.

## Written answers requested

Please answer the adviser questions in sections 1–5 in writing. Identify the exact sources and distinguish confirmed legal text from your interpretation. This pack is not a legal opinion or compliance certification.
