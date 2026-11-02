# Product Architecture Implications and Integration Principles

**Status:** Proposed design guidance for management/technical review — not an approved architecture decision
**Prepared:** 2 November 2026

## Reconciliation with current project direction

Existing project governance and architecture documents favor a narrow payroll foundation and defer broad API, AI, offline and multi-company platform scope. The proposed North Star is wider and integration-oriented. These directions can coexist if the team distinguishes small, reversible integration seams now from provider-specific integrations and automation later. This document does not authorize a redesign or code change. Material choices belong in an approved ADR after current architecture review.

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

## Decisions required before implementation

- Approve North Star versus baseline scope and priorities.
- Confirm the initial pilot’s manual versus automated handoff responsibilities.
- Confirm architecture constraints and record material decisions as ADRs.
- Obtain customer/provider/authority access and contracts for any connector.
- Complete legal/privacy assessment and technical failure/recovery design before real-data or money movement.
