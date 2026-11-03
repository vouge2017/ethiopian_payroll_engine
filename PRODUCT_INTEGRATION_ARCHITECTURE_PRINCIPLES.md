# Product Architecture Implications and Integration Principles

**Status:** Proposed design guidance for management/technical review — not an approved architecture decision
**Prepared:** 2 November 2026; reconciled 3 November 2026

## Reconciliation with current project direction

Existing project governance and architecture documents favor a narrow payroll foundation and defer broad API, AI, offline and multi-company platform scope. The proposed North Star is wider and integration-oriented. These directions can coexist if small internal boundaries are created only for an approved requirement, while provider-specific integrations and automation remain later work. This document does not authorize a redesign, code change, public API or amendment to an existing ADR. Material choices belong in an approved ADR after current architecture review.

## Conflict and compatibility register

| Topic | Existing repository position | New Phase 0 proposal | Actual conflict? | Proposed disposition | ADR required? | Required approval |
|---|---|---|---|---|---|---|
| D07 vs ADR-011 | ADR-011 is recorded as decided: one-level business-owner approval with confidence report and lock; multi-level approval is future. | D07's prior alignment text suggested configurable maker-checker. | Yes, if configurable maker-checker is treated as first-release behavior. | For the first baseline, propose retaining ADR-011 unchanged, subject to management confirmation. Keep configurable maker-checker as a future option. This register does not amend ADR-011. | Yes, a new/amended ADR if approval workflow changes. | Product Owner + Tech Lead for ADR; management records first-release policy. Legal/bank mandates require separate confirmation. |
| D08 vs D20 and ADR-012 | ADR-012 records a payment-batch/file lifecycle and distinguishes file generation, bank acceptance, transfer and receipt; its legacy state names do not prove current provider integration. | D08 limits first pilot to instructions/file handoff and customer/provider-controlled transfer. D20 proposes later initiation/orchestration. | No conflict if D08 is manual pilot boundary and D20 is a separately gated future capability. | Preserve current payroll/payment behavior. Do not infer “paid/settled” from file or request status. Before initiation, reconcile state names, safe retry/duplicate/reversal behavior and provider evidence in a reviewed design. | Yes before changing payment lifecycle, authorization or retry semantics. | Product Owner + Tech Lead; legal/provider/security and employer authorization before real initiation. |
| D11 vs D21 | D11 allocates current preparation, submission and reconciliation responsibilities; no EthioPayroll authority/API is verified. | D21 proposes future electronic submission and acknowledgements. | No, if D11 remains the manual/current responsibility and D21 remains future capability. | First pilot uses verified customer-authorized submission and records evidence. Electronic submission is not in baseline without direct authority/provider access and a separate release decision. | Yes if submission changes the architecture, authority model or external workflow. | Product Owner, qualified tax/pension professional, relevant authority/provider and Tech Lead. |
| D25 vs ADR-018 | ADR-018 defers public API versioning until an external integration exists. | D25 proposes internal contracts where an approved need requires them and separately gates public APIs. | No, if internal contracts are not a public API program and not a generalized platform. | Do not create public API commitments. Add only the minimum internal schema/adapter boundary needed by an approved requirement; record material changes. | New ADR for public API/versioning or material architecture; not for a local implementation detail unless governance rules require it. | Product Owner + Tech Lead; security review and management business case for public API. |
| PLAN.md vs PROJECT_RULES.md | PLAN.md states it is the current project source and lists the immediate engineering priorities. PROJECT_RULES.md says “Nothing else until pilot is running” and contains older scope restrictions. | The owner expressly authorized Phase 0 strategic documentation, while retaining narrow implementation focus. | Apparent scope conflict, resolved only for this bounded documentation task by the owner’s explicit instruction. No permanent repeal is established. | PLAN.md continues to govern immediate engineering work. Preserve PROJECT_RULES.md as historical until management formally amends it. The Phase 0 request authorizes this documentation reconciliation only; no feature scope follows from it. | Not an ADR; formal management/document-control approval is required to supersede a governance rule. | Management/Product Owner; document authority and effective date must be recorded. |

No existing ADR was edited or silently superseded. The dispositions above are proposals for management/technical review, not approvals.

## Proposed principles

1. **Keep payroll rules independent.** Statutory calculation is deterministic, versioned, Decimal-based and independently testable. Provider/AI code cannot change legal parameters or calculation results.
2. **Separate internal workflow from external transport.** Payroll run, approval, payment authorization, provider submission, external status and reconciliation are separate domain states.
3. **Use adapters only when an approved use case needs one.** A provider adapter translates a stable internal contract to a provider contract; do not create connectors before access and customer need are demonstrated.
4. **Version exchanges.** Document input/output schemas, effective versions, required fields, validation, error categories and compatibility policy.
5. **Make retries safe.** Assign stable idempotency keys and unique batch/transaction identifiers. Retry only when provider semantics make the outcome safe; reconcile uncertain outcomes before resubmission.
6. **Verify callbacks/status.** Authenticate provider messages, validate correlation and preserve source/time/reference. A request sent is not a completed payment or filing.
7. **Preserve provenance.** Store who authorized an action, which data/rule/report version was used, and what external evidence was received.
8. **Respect company scope.** Every exchange and user authorization is bound to the relevant business. Portfolio membership does not imply access to a company.
9. **Protect secrets and personal information.** Use managed credentials, least privilege, data minimization and a data-location/subprocessor inventory. Do not place credentials in logs or exports.
10. **Offer safe fallbacks.** If an API is unavailable, an authorized file/manual handoff may remain supported with clear status and responsibility. The fallback must not imply completion.
11. **Plan for failure and recovery.** Define timeout, duplicate, partial success, reversal, outage and restore behavior before initiating financial or statutory transactions.
12. **Avoid premature platform complexity.** A public API program, event bus, microservices, generalized workflow engine and offline transaction queue require evidence and an ADR; they are not implied by integration readiness.

## Proposed provider state models

**Salary payments:** prepared → employer-approved → authorized for handoff → submitted/initiated (only if integrated) → provider processing → settled or rejected/failed → reconciled. Keep manual handoff distinct. Only provider/bank evidence supports “settled”; reconciled means matched to approved payroll.

**Statutory submissions:** package prepared → authorized → submitted → acknowledgement received → accepted or rejected → correction/resubmission if required → payment/reconciliation evidence. A generated schedule is not a submission; a successful HTTP/request response alone is not authority acceptance.

## Candidate adapter contracts (future, subject to approval)

| Boundary | Internal contract should carry | External acceptance still needed |
|---|---|---|
| Bank/payment | Approved batch ID, beneficiary reference, amount, currency, payment purpose, authorization, idempotency key, provider status/reference and settlement evidence. | Accepted bank/provider format or API, mandate, fees/limits, beneficiary verification, co-signing, failure/reversal and settlement semantics. |
| Telebirr | Provider-neutral payment instruction plus Telebirr-specific mapping behind adapter. | Salary-batch API/portal route, organization eligibility, product subscription/contract, sandbox, limits/fees and transaction status evidence. |
| Tax authority | Versioned filing package, tax period, employee-level lines, totals, preparer/approver and authority reference/acknowledgement. | Current filing/correction process, authority to submit, accepted schema/API/portal terms and acknowledgement process. |
| Pension authority/revenue collector | Versioned employee contribution schedule, period, employer/employee totals, remittance reference and acknowledgement. | Current contribution collection route, eligibility/commencement interpretation, submission format/API and remittance evidence. |
| Accounting/ERP | Balanced, traceable journal/export with mapping version and source payroll run. | Customer’s chart-of-accounts mapping, system/API version, import rules and reconciliation acceptance. |
| Attendance/workforce | Source identity, event time/period, employee reference, correction state, approval and provenance. | Device/vendor access, data quality, legal/privacy basis, work-rule interpretation and customer acceptance. |

## Human/AI control boundary

AI may draft an explanation, extract fields, summarize changes or flag an outlier. A person reviews and authorizes any consequential change. AI does not calculate statutory tax/pension, decide a legal interpretation, approve payroll, authorize funds, submit an official return or mark an external event complete. Voice commands use the same authentication, permission, review and audit rules as the interface.

Before any AI functionality is released, an accountable owner must be assigned for provider/model selection, privacy and security review, representative evaluation cases, error monitoring, incident response, fallback behavior and review of model, prompt, tool and data-flow changes. Governance readiness is a prerequisite; it does not prioritize or approve an AI feature. Payroll calculation remains deterministic, versioned and independently tested.

## Internal contracts and public APIs

An internal input/output contract is permitted only when an approved first-phase requirement needs it. Keep it private to the application unless a separate public-API business case is approved. A public API requires a defined customer/use case, security and authorization review, versioning/compatibility decision (including ADR-018), operational support plan and Product Owner + Tech Lead and management approval. Provider adapters require documented customer need, provider authorization/specification, technical feasibility, failure/recovery design and legal/security review where applicable. No current proposal establishes provider access or API availability.

## Decisions required before implementation

- Approve North Star versus baseline scope and priorities.
- Confirm the initial pilot’s manual versus automated handoff responsibilities.
- Confirm architecture constraints and record material decisions as ADRs.
- Obtain customer/provider/authority access and contracts for any connector.
- Complete legal/privacy assessment and technical failure/recovery design before real-data or money movement.
