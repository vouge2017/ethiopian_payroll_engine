# Proposed Product Baseline Structure

**Status:** Proposed outline and blank working templates — not approved requirements
**Prepared:** 2 November 2026; reconciled 3 November 2026

## Baseline availability and authority

Product Baseline V4 was not found in the current checkout or the origin/main Markdown files inspected for Phase 0. This document does not reconstruct it. The Product Baseline is approved only after management records the customer, scope, requirements and approval evidence. It is subordinate to the approved product/company governance and does not replace `PLAN.md` as the current engineering-priority source.

Keep three planning levels separate:

| Level | Governs | Evidence/approval |
|---|---|---|
| Product North Star | Long-term ambition and trust principles. | Management endorsement; remains separate from release scope. |
| Approved Product Baseline | Validated customer, user problems, approved capabilities, release boundaries and measurable outcomes. | Recorded management decision, customer evidence and professional/provider review where applicable. |
| Delivery roadmap | Sequenced engineering tasks, dependencies and acceptance evidence. | Product/technical approval, current implementation evidence and capacity; `PLAN.md` governs immediate work. |

## First-baseline decision boundary

The first baseline must make a bounded monthly payroll workflow reviewable. Before approval, resolve or explicitly constrain D01–D04, D06–D16 and the manual-handoff boundary in D17. Those decisions must establish the first customer hypothesis, employer/accountant responsibilities, permissions and approval, language needs, supported payroll inputs and outputs, rule-approval process, data protection, save/recovery, support, portability and pilot gates. D12/D13 evidence required before real-data use remains an independent gate; a written unresolved status is not legal/privacy approval.

Do not add the following as first-release requirements without new evidence and explicit approval: final commercial pricing (D05; required before commercial release), direct provider integrations (D17/D19/D20), attendance capture/connectors (D18), electronic filing (D21), system-specific accounting connectors (D22), voice (D23), AI functionality (D24), or a public API/generalized integration platform (D25). D24 governance must be approved before any AI feature is released. D25 internal contracts are permitted only when a separately approved first-phase requirement needs them.

## Proposed baseline sections

1. Document owner, version, approval record and change history.
2. Product purpose, approved North Star reference, boundaries and non-goals.
3. Initial customer segment/buyer and evidence from research.
4. Customer problems, current workflow and measurable value hypotheses.
5. Approved first-release scope, deferred capabilities and explicit exclusions.
6. End-to-end business, employee, payroll, review, approval, output, correction and support journeys.
7. Roles, company-scoped permissions and responsibility matrix.
8. Supported payroll rules, source governance, effective dates and professional approval records.
9. Filing/payment responsibilities and evidence states.
10. Required first-phase imports/exports versus candidate future integrations.
11. Language, terminology and accessibility acceptance.
12. Privacy, hosting, subprocessors, minimization, retention, export and closure.
13. Save/recovery, backup/restore, failure handling and support expectations.
14. Measurable quality and performance targets for the defined pilot envelope.
15. Commercial assumptions and customer research; no unvalidated price claims.
16. Pilot entry/exit gates, consent, success measures and stop conditions.
17. Operations, incident handling and customer responsibilities.
18. Release criteria, known limitations and rollback/stop conditions.
19. Requirement-to-decision, architecture, implementation, test and evidence traceability.
20. Assumptions, unresolved items, external approvals and reopening triggers.

## Reusable requirement record

Create one record per requirement. Do not populate it with a North Star idea unless it has been approved for a release.

| Field | Required content |
|---|---|
| Requirement ID | Stable unique ID, e.g. `BASE-001`; do not reuse IDs. |
| User/business problem | Evidence-backed problem and expected outcome. |
| User role | Who experiences or performs the behavior. |
| Requirement statement | One testable “The system shall…” statement. |
| Acceptance criteria | Observable pass/fail conditions, including boundaries and failure behavior. |
| Test/evidence method | Test type or operational evidence, environment and expected reviewer. |
| Related decision IDs | D01–D25 IDs that authorize, constrain or defer the requirement. |
| Owner | Accountable role for delivery and acceptance. |
| Dependencies | Prior decisions, data, provider, legal or technical work. |
| Release phase | Internal synthetic, supervised shadow, controlled pilot, commercial or later. |
| Legal/security constraints | Source/interpretation, data classification, access, retention and safe-state controls, or “not applicable with reason.” |
| Approval status | PROPOSED / OPEN / APPROVED / DEFERRED / REJECTED, with approver role/date/evidence for APPROVED. |

## Decision-to-evidence traceability view

Keep one row per approved requirement. Blank rows below are a template, not missing work presented as complete.

| Decision ID | Requirement ID | Acceptance criteria reference | Test or evidence receipt | Approval record |
|---|---|---|---|---|
| (D01–D25) | (BASE-###) | (AC-###) | (test/workflow/source, exact SHA and result) | (role, date, selected option/condition) |

Traceability rule: **Decision → Requirement → Acceptance criteria → Test evidence → Approval.** A link at an earlier stage does not imply later-stage completion. No baseline requirements are approved by this outline.

## Baseline acceptance rule

Approve the baseline only when every included requirement has the required fields above, each included requirement links to an approved decision, all exclusions and unresolved issues are visible, and the management approval record names the exact baseline version. Legal or provider claims require their own source/acceptance evidence; management approval cannot manufacture it.
