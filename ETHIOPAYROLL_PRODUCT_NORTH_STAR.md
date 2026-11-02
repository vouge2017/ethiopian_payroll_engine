# EthioPayroll — Product North Star

**Status:** Proposed management direction — not formally approved
**Prepared:** 2 November 2026
**Purpose:** Describe the long-term product ambition without changing approved engineering scope or claiming current capability.

## Proposed North Star

EthioPayroll should progressively automate the complete Ethiopian payroll and workforce-operations lifecycle: employee onboarding and workforce information; attendance, shifts, overtime and leave; payroll preparation and deterministic statutory calculations; validation, review and approval; salary-payment preparation and, when legally and contractually available, provider orchestration; statutory reporting and authorized submission; reconciliation; payslips and employee records.

The proposed operating principle is:

> **Human-led accountability. Machine-led execution.**

Business owners and authorized personnel provide or authorize information, resolve exceptions, make business decisions and approve sensitive actions. The platform should perform repetitive, controlled work when the inputs, legal basis, provider capability and evidence support it. This principle is proposed for management consideration; it is not recorded as approved.

## Intended capability horizon

This horizon is an ambition inventory, not an approved requirements list or statement of current functionality.

| Capability | Long-term intent | Boundary |
|---|---|---|
| Employee and workforce management | Maintain employment, compensation, status and supporting records across the employee lifecycle. | Collect only data with a documented purpose and legal basis. |
| Attendance and time | Support shifts, hours, overtime, leave, absence, holidays and corrections; consume device/mobile/third-party inputs where justified. | Do not automatically penalize missing or disputed attendance. Biometric capture is not compulsory. |
| Employee self-service | Let employees review or submit appropriate information, payment preferences and requests. | Employer-authorized review remains for material record changes. |
| Payroll preparation | Turn approved employment and time inputs into a monthly payroll run with clear changes and exceptions. | Payroll calculations remain deterministic, versioned and independently testable. |
| Validation and exceptions | Check missing/invalid inputs, compare periods and surface anomalies with reasons. | An anomaly is a review prompt, not an automatic adverse decision. |
| Approval and authorization | Configure preparation, review, employer approval and provider authorization to customer controls. | AI cannot approve payroll, authorize payment or submit a statutory return. |
| Payment | Prepare instructions; later orchestrate through contracted and authorized providers if feasible. | Distinguish prepared, approved, initiated, processing, settled, rejected/failed and reconciled. Never claim settlement without provider evidence. |
| Tax and pension | Prepare filing schedules; later submit only through authorized channels and track acknowledgement/rejection. | A generated file is not a submission; a dispatch is not acceptance. |
| Reconciliation and records | Reconcile payroll, payment, statutory and accounting results; retain explainable histories and exportable evidence. | Preserve approved/locked payroll facts and trace corrections. |
| Accounting/business integrations | Exchange payroll journals and statuses with customer-selected business systems. | Do not force replacement of the customer’s ERP/accounting system. |
| Voice and languages | Explore conversational access and multilingual help, with English and Amharic priorities and existing Afaan Oromoo translations preserved. | Language and speech readiness requires native-speaker, practitioner, accessibility and privacy validation. |
| AI assistance | Assist document extraction, explanations, anomaly review and workflow preparation. | No AI statutory calculation, legal interpretation, payroll approval, payment authorization or statutory submission. Human confirmation for writes. |
| Integration foundation | Use secure APIs, webhooks and provider adapters as useful boundaries for banks, attendance, accounting and government systems. | Do not assume any specific API is accessible or authorized. Avoid generalized integration infrastructure before validated demand. |
| Reliability and auditability | Provide durable saving, synchronization, recovery, access control and evidence of material actions. | Define and test recovery behavior before real customer data or transactions. |

## Product boundaries

- EthioPayroll is intended to be an Ethiopian payroll and workforce-compliance operating platform, not a general ERP.
- The first complete monthly payroll cycle is an evidence milestone, not the complete product definition.
- Current implementation priorities are governed by PLAN.md. This document does not authorize broader implementation.
- North Star ambition, approved Product Baseline and delivery roadmap are separate controlled artifacts.
- Legal interpretation, provider permission, customer demand, production implementation and operational use require separate evidence.

## Trust controls throughout the horizon

1. **Deterministic statutory calculations:** rule source, effective date, inputs and outputs must be reproducible. Changes require review and independent tests.
2. **Human control:** authorized people decide exceptions and approve sensitive actions. Automation cannot bypass role checks or approval.
3. **Truthful states:** prepared, submitted, accepted, paid/settled and reconciled are distinct states with supporting evidence.
4. **Privacy by design:** minimize data; assess Ethiopian data-protection requirements, local hosting and cross-border transfers, sensitive-data handling, retention and subprocessors before real data.
5. **Non-compulsory biometrics:** do not make facial, fingerprint or other biometric attendance a prerequisite.
6. **Account verification clarity:** distinguish syntax/format checks from provider confirmation of account or account-holder identity.
7. **Integration readiness without provider claims:** design small seams where requirements justify them; obtain provider documentation, access, terms and test acceptance before promising a connector.
8. **No unsupported regulation:** do not act as a payment provider or hold customer funds without a written legal/provider assessment and required authorization.

## Approval and change control

Management must record whether it accepts, changes or rejects this North Star and the proposed operating principle. Approval does not automatically make every listed capability part of the Product Baseline. Each capability must separately enter the baseline through customer evidence, legal/provider feasibility, technical architecture review, capacity and an explicit release decision.

**Related controlled documents:** PHASE_0_MANAGEMENT_DECISION_REGISTER.md, PROPOSED_PRODUCT_BASELINE_STRUCTURE.md, PRODUCT_INTEGRATION_ARCHITECTURE_PRINCIPLES.md, and ETHIOPAYROLL_STAGED_DELIVERY_SEQUENCE.md.
