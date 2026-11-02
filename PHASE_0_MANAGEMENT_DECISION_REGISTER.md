# EthioPayroll — Phase 0 Management Decision Register

**Purpose:** Capture the decisions management must make before approving the product baseline and deriving release requirements. This register contains proposals, research needs and external questions; it is not itself an approved product strategy or legal opinion.

**Prepared:** 2 November 2026

**Source baseline:** `origin/main` at `f52330a` (PR #47 merge). The working checkout used for the earlier reconciliation was older and had unrelated user changes; they were preserved.
**Product Baseline V4:** Not found in the checkout or in the available `origin/main` Markdown files. This register does not recreate it.

## Executive summary

The owner’s stated direction is an Ethiopian payroll and workforce-compliance platform for businesses. A business may run payroll itself or give an external accountant controlled access. The first dependable monthly payroll cycle is the first proof milestone, not the whole product definition. This product is not intended to become a general ERP.

The immediate management work is to choose the first customer and operating model, define who may prepare and approve payroll, and agree the evidence gates for a one-business shadow run and a three-business pilot. Customer willingness to pay, legal interpretations, bank and filing procedures, and data-protection obligations require evidence from outside the development team. None is marked approved here.

**Recommended sequence:** approve the product and pilot decisions below; obtain required customer, legal, bank and infrastructure evidence; validate internally with synthetic data; run one supervised parallel payroll; expand to three controlled businesses; make a separate commercial-release decision; then consider ten-business adoption.

## Status and priority meanings

- **P0:** Resolve before approving product requirements.
- **P1:** Resolve or obtain required evidence before the first real-business pilot.
- **P2:** Resolve before commercial release.
- **P3:** May be deferred with a reason and a reopening trigger.

Statuses: **OPEN** means a decision is not made; **RESEARCH REQUIRED** means external evidence is needed; **PROPOSED** means a recommended answer is awaiting management approval; **APPROVED** is reserved for a recorded management decision; **DEFERRED** means intentionally delayed with a trigger. No item below is marked approved.

## Decision register

### D01 — Initial customer segment and buyer

- **Priority / status:** P0 — RESEARCH REQUIRED
- **Decision question:** Which business type and buyer will the first release serve: business owner/finance lead, HR/payroll operator, or external accountant acting for the business?
- **Existing position:** Draft documents describe Ethiopian SMEs and business owners; one historical review proposes 5–200 employees but explicitly says the segment was not validated. The owner’s direction includes both businesses running payroll internally and businesses using accountants.
- **Options and consequences:** (a) Owner-operated SMEs focus onboarding on owners but may under-serve professional accountants; (b) SMEs with payroll/HR staff need stronger role handoffs; (c) accountant-led service businesses validate multi-client workflows but raise portfolio and access needs; (d) one industry yields clearer cases but narrows initial reach.
- **Recommendation:** Begin discovery with Ethiopian employers that currently use Excel and run recurring monthly payroll, including both owner-operated and accountant-supported cases. Select one first-pilot profile from actual interviews; do not market 5–200 as a validated segment yet.
- **Evidence still required:** Interview business owners and accountants; document employee range, current workflow, payroll complexity, buyer, and switching barrier.
- **Consequences:** A broad segment delays focused onboarding and support design; a narrow segment may exclude useful demand.
- **Decision owner:** Product owner.
- **External contributors:** Ethiopian business owners, payroll accountants, HR/finance practitioners.
- **Dependencies:** Customer interviews.
- **Required milestone:** Before requirements approval and first-pilot recruitment.

### D02 — Initial employee-size target and capacity assumptions

- **Priority / status:** P0 — PROPOSED
- **Decision question:** What size of employer should the first pilot and initial release support, and what is a tested capacity envelope versus a permanent product limit?
- **Existing position:** Draft PRDs variously use 50 employees as a time-saving example, 50–200 for a ten-company pilot, and 100 as a proposed pilot ceiling. These are inconsistent and are not validated market evidence.
- **Options and consequences:** (a) A pilot-only range contains first-cycle risk but limits recruiting; (b) a tested operating envelope communicates demonstrated capacity without excluding future customers; (c) a permanent cap simplifies initial guarantees but may unnecessarily constrain the market.
- **Recommendation:** Set a pilot-only range after a representative workload test and customer selection. Publish tested capacity as an operational envelope, not a permanent product ceiling. Do not promise support for a size that has not been tested.
- **Evidence still required:** Measure end-to-end calculation, review, report and payslip generation for representative synthetic headcounts.
- **Consequences:** A low pilot range limits first-cycle complexity; an unsupported high range risks timeouts and trust; a permanent cap may unnecessarily constrain the product.
- **Decision owner:** Product owner.
- **External contributors:** Technical lead; pilot accountant to identify representative workloads.
- **Dependencies:** Internal performance evidence and D01 customer selection.
- **Required milestone:** Before confirming pilot size and approving capacity claims.

### D03 — Direct business subscription and workspace ownership

- **Priority / status:** P0 — PROPOSED
- **Decision question:** Will the employing business contract and subscribe directly, with its accountant invited, or will an accountant purchase a portfolio service and manage client workspaces?
- **Existing position:** Draft journeys make the business owner create and approve a company. Billing and pricing are explicitly parked in `PLAN.md`; no customer subscription model is validated.
- **Options and consequences:** (a) Direct business subscription gives the employer clear control but requires reliable delegated-accountant access; (b) accountant-purchased portfolio service simplifies multi-client buying but shifts billing and client-exit complexity to the accountant; (c) hybrid business-owned accounts with accountant service pricing preserve business control but require clear separation of software and accountant-service contracts.
- **Recommendation:** Use a business-owned workspace with the business controlling authorization as the proposed initial model; allow an invited accountant to operate within granted company scope. Validate who pays and how packaging works before implementing billing.
- **Evidence still required:** Interview owners and accounting firms about procurement, data control, revocation and client transfer; review contract implications.
- **Consequences:** Choosing without this evidence can make the account model and commercial packaging costly to change.
- **Decision owner:** Product owner.
- **External contributors:** Business owners, accountants, commercial adviser and legal counsel.
- **Dependencies:** D01 and D04.
- **Required milestone:** Before account, permission and billing requirements are approved.

### D04 — External accountant access and permissions

- **Priority / status:** P0 — PROPOSED
- **Decision question:** Can a business invite an external accountant, and which actions can that accountant perform or approve?
- **Existing position:** Draft PRDs include accountant review and owner approval. Older governance documents defer multi-company management until customer need is demonstrated. Current plan focuses on one-company workflow first.
- **Options and consequences:** (a) Owner-only access is simplest but may block outsourced accounting; (b) per-company invitations support the common accountant handoff with manageable scope; (c) portfolio access improves multi-client efficiency but expands tenant-isolation and support risk.
- **Recommendation:** Support company-authorized accountant access in the first customer model if tenant and role checks are verified. Defer an accountant portfolio cockpit until multi-company demand and isolation are proven. Keep approval authority explicitly assigned by the business.
- **Evidence still required:** Validate role boundaries and cross-company access with two-company tests and accountant interviews.
- **Consequences:** Owner-only access may block outsourced workflows; portfolio-wide access too early increases security and operational risk.
- **Decision owner:** Product owner.
- **External contributors:** External accountants; technical and security reviewers.
- **Dependencies:** D03 and verified tenant-scoped authorization.
- **Required milestone:** Before real employee data is loaded.

### D05 — Pricing and willingness to pay

- **Priority / status:** P2 — RESEARCH REQUIRED
- **Decision question:** What pricing basis and service package will the target customer pay for?
- **Existing position:** A historical market-readiness review says there was no pricing model or billing and no customer validation. `PLAN.md` calls for interviews on ETB pricing, deadline support and procurement.
- **Options and consequences:** (a) Per-employee pricing scales with usage but makes bills variable; (b) per-company bands are predictable but need clear thresholds; (c) portfolio pricing fits accounting firms but depends on multi-client value; (d) paid assisted service tests willingness to pay while revealing delivery costs but is less self-serve.
- **Recommendation:** Do not set production prices from internal estimates. Test at least two simple pricing presentations with target buyers and ask about support/service expectations as well as software value.
- **Evidence still required:** Record interview profiles, proposed prices, objections, alternatives and willingness-to-pay signals.
- **Consequences:** Delaying price does not block synthetic development, but it blocks a credible commercial-release and billing decision.
- **Decision owner:** Product owner.
- **External contributors:** Business owners, accounting firms and a commercial adviser if available.
- **Dependencies:** D01 customer selection and D03 contracting model.
- **Required milestone:** Before the commercial-release decision; not required for internal validation.

### D06 — English and Amharic launch requirements

- **Priority / status:** P0 — PROPOSED
- **Decision question:** Which languages must be complete and professionally reviewed for the first customer-facing release, including payroll explanations, payslips and support material?
- **Existing position:** Product documents target English and Amharic, with some older documents claiming broader localization. `PLAN.md` records that Amharic payroll labels have errors. No current native-speaker acceptance evidence was located.
- **Options and consequences:** (a) English-only reduces translation scope but may exclude users; (b) English plus reviewed Amharic for core payroll tasks and outputs covers the highest-stakes journey with bounded scope; (c) full bilingual coverage is more consistent but expands review and release effort.
- **Recommendation:** Define a minimum bilingual launch scope for payroll-critical screens, validation messages, payslips and employee communications, then obtain native-speaker and accountant review. Do not describe Amharic as launch-ready until that review is recorded. Decide Afaan Oromoo separately based on customer evidence.
- **Evidence still required:** Approved glossary and native-speaker/accountant review of representative flows and artifacts.
- **Consequences:** English-only may exclude users; partial unreviewed translation can mislead users in a high-stakes workflow; full localization expands launch scope.
- **Decision owner:** Product owner.
- **External contributors:** Amharic native reviewer and Ethiopian accountant/HR practitioner.
- **Dependencies:** Pilot profile and selected customer language needs.
- **Required milestone:** Before inviting a pilot participant who relies on Amharic; full bilingual release scope before commercial release.

### D07 — Single approver and maker-checker workflow

- **Priority / status:** P0 — PROPOSED
- **Decision question:** May one authorized person prepare and approve payroll for a small business, and when must a second person review or approve it?
- **Existing position:** Draft PRDs model payroll officer/accountant preparation followed by owner approval. Small-company owner-only operations are part of the intended market, but the exact control policy is not settled.
- **Options and consequences:** (a) Two-person approval strengthens separation but can make very small firms unable to run payroll; (b) one-person approval supports small firms but has weaker separation and needs clear audit evidence; (c) configurable policy fits varied controls but adds permission and verification complexity.
- **Recommendation:** Support a one-person workflow for very small businesses while making the same-person action visible in the audit record. Support maker-checker separation when the business requires it. Never imply that this software policy replaces a legal, bank-mandate or employer-control requirement.
- **Evidence still required:** User research, role/authorization tests, and written company policy; obtain legal advice before asserting a statutory two-person requirement.
- **Consequences:** Mandatory two-person approval can make one-person firms unable to operate; no separation option may fail larger customers’ controls; configurable policies add permission complexity.
- **Decision owner:** Product owner.
- **External contributors:** Business owners, accountants, security reviewer and legal adviser if a statutory requirement is asserted.
- **Dependencies:** D04 and server-side role enforcement.
- **Required milestone:** Before approval states are approved in requirements and before pilot authorization.

### D08 — Bank co-signing and payment responsibility

- **Priority / status:** P1 — RESEARCH REQUIRED
- **Decision question:** What does EthioPayroll do at payment time, and who authorizes, submits, co-signs and confirms the actual transfer?
- **Existing position:** Pilot materials describe downloading a file and sending it to the bank out of band. No bank mandate, co-signing requirement or payment API contract is established by the available product documents.
- **Options and consequences:** (a) File preparation keeps money movement outside the product but offers limited status visibility; (b) recording status/evidence improves reconciliation but requires clear proof rules; (c) a contracted integration can reduce manual steps but adds authorization, security, duplicate-payment and provider-availability risks.
- **Recommendation:** For the first pilot, stop at approved payment instructions/file preparation and reconciliation evidence. The employer’s authorized users submit/co-sign through their bank process; the bank/provider executes. Do not label a generated file or manual status as “paid” without bank evidence.
- **Evidence still required:** Obtain the pilot bank’s current template, validation rules, submission method, authorization/co-signing requirements and a sanitized acceptance result.
- **Consequences:** A file-only handoff keeps responsibilities clear but leaves submission to the customer; an unsupported API could create duplicate or unauthorized payments.
- **Decision owner:** Product owner for product responsibility boundaries; the business decides its own authorized signatories.
- **External contributors:** Pilot company finance/authorized signatory, bank/provider representative, security reviewer and legal adviser.
- **Dependencies:** D09 and approved payment-state definitions.
- **Required milestone:** Before the first real-business payment handoff.

### D09 — First real-business pilot profile

- **Priority / status:** P1 — RESEARCH REQUIRED
- **Decision question:** Which willing employer and qualified accountant can safely validate the first parallel monthly payroll, and what payroll complexity is in scope?
- **Existing position:** A pilot package describes a process but does not establish a currently willing company, current deployed release, or accountant acceptance. The product checkpoint requires a real accountant journey; no such acceptance is established here.
- **Options and consequences:** (a) A regular salaried employer makes the first comparison interpretable but tests fewer edge cases; (b) a high-complexity employer reveals more gaps but can confound product defects with unsupported scope; (c) waiting for a willing target customer avoids a false-fit pilot but delays real-world evidence.
- **Recommendation:** Recruit one willing employer with a named qualified accountant, stable monthly payroll and manageable first-cycle complexity. Include synthetic rehearsals first. Record excluded employee/pay items explicitly; do not hide them in a broad “supports payroll” claim.
- **Evidence still required:** Written participation, approved data-handling terms, accountant qualifications/role, employee-count and payroll-input profile, and a safe parallel-run plan.
- **Consequences:** A mismatch between pilot complexity and proven capability can produce misleading success or unsafe reliance; waiting for an appropriate volunteer delays real-world evidence.
- **Decision owner:** Product owner selects and scopes the pilot; the employer chooses whether to participate.
- **External contributors:** Willing business owner, qualified Ethiopian accountant and data-protection/legal adviser.
- **Dependencies:** D01, D06, D12–D16 and Gate 1 exit.
- **Required milestone:** Before processing real employee data.

### D10 — One-business and three-business pilot sequence

- **Priority / status:** P0 — PROPOSED
- **Decision question:** Does “three-business pilot” mean three businesses total including the first pilot, or three additional businesses after it?
- **Existing position:** The pilot package allows a one-company pilot to progress to “3-company scale”; older PRDs call ten companies the pilot. The stages are not consistently named.
- **Options and consequences:** (a) One business gives limited evidence and risks over-generalizing; (b) three total tests repeatability while keeping expansion controlled; (c) four total adds diversity but increases support/data exposure before the third independent case is understood.
- **Recommendation:** Define the controlled pilot as **three businesses total**, onboarded sequentially: first shadow customer, then two additional businesses after the first exit review. Treat ten businesses as a later adoption milestone, not as the initial pilot.
- **Evidence still required:** At each expansion, record workflow completion, discrepancies, record handling, support effort and written feedback separately for each business.
- **Consequences:** One business validates only one context; three total tests repeatability; expanding directly to ten increases operational exposure before a controlled pilot is understood.
- **Decision owner:** Product owner.
- **External contributors:** Participating businesses and accountants; operations and QA reviewers.
- **Dependencies:** D09 and documented stage exit reviews.
- **Required milestone:** Before publishing pilot invitations or success criteria.

### D11 — Tax and pension submission and reconciliation responsibilities

- **Priority / status:** P1 — RESEARCH REQUIRED
- **Decision question:** Which returns/schedules does the product prepare, who submits them, through which accepted channel, and what evidence closes reconciliation?
- **Existing position:** `PLAN.md` says to obtain authorized templates and distinguish file generation, filing and payment. Direct e-Tax integration is parked; available pilot materials describe out-of-band submission.
- **Options and consequences:** (a) Prepared schedules retain manual submission responsibility and require clear customer steps; (b) a verified portal workflow can reduce errors but needs current portal validation; (c) an authorized integration can automate a handoff but creates legal, credential, failure and reconciliation obligations.
- **Recommendation:** For the first pilot, generate reviewed schedules from locked payroll, have the employer/accountant submit through the verified current authority process, and record submission/payment receipts separately. Do not claim direct filing or automatic offsets/refunds.
- **Evidence still required:** Current official forms/portal procedure, accepted field definitions and deadline, sanitized submission/validation result, receipt and reconciliation procedure.
- **Consequences:** Manual submission requires customer action; an unverified automated route risks late, duplicate or rejected filing.
- **Decision owner:** Product owner for product scope; employer/accountant remains responsible for authorized submission unless a separately approved service is established.
- **External contributors:** Qualified Ethiopian tax and pension professionals, pilot accountant and relevant authorities where accessible.
- **Dependencies:** D12 and D09.
- **Required milestone:** Before any pilot filing or filing-ready claim.

### D12 — Authority and professional approval of payroll calculations

- **Priority / status:** P0 — RESEARCH REQUIRED
- **Decision question:** Who has authority to approve each statutory calculation interpretation and its effective date for production reliance?
- **Existing position:** The legal adviser pack records several confirmed provisions and unresolved questions. It is a professional review request, not blanket legal certification. Tests establish software behavior, not statutory correctness.
- **Options and consequences:** (a) Written professional approval provides a traceable interpretation but takes time and scope control; (b) official authority guidance is strongest for administrative procedure when available but may not resolve every calculation; (c) retaining provisional rules allows synthetic learning but blocks affected real-payroll reliance.
- **Recommendation:** Require a traceable legal source, written interpretation where needed, approved worked cases, effective date and named professional role for each material rule. Keep unresolved rule calculations visibly provisional and exclude them from real payroll reliance until the legal and calculation gates are satisfied.
- **Evidence still required:** Signed/dated adviser answers, source copies, formulas, independently checked expected values and regression evidence for each in-scope rule.
- **Consequences:** Proceeding without approval risks incorrect withholding or contributions; waiting blocks affected real-payroll reliance but not synthetic technical work.
- **Decision owner:** Product owner owns the approval process; the qualified professional owns their written interpretation.
- **External contributors:** Qualified Ethiopian tax, pension and labour-law professionals; accountant; engineering/QA reviewers for implementation evidence.
- **Dependencies:** Identified rule inventory, effective dates and worked cases.
- **Required milestone:** Before a shadow result is used to recommend payment or filing; before commercial release for each supported rule.

### D13 — Data protection, hosting and personal information

- **Priority / status:** P1 — RESEARCH REQUIRED
- **Decision question:** What employee information may the product collect, where is it hosted/processed, how long is it retained, and how can it be exported or deleted?
- **Existing position:** The application is intended to handle salary, tax, bank and identity-related data. Current repository documents do not establish a complete, professionally approved data-protection policy or verified hosting/data-location statement for this register.
- **Options and consequences:** (a) Data minimization reduces exposure but can defer future workflows; (b) collecting extra identifiers increases breach and retention burden without proving need; (c) selecting hosting on verified criteria may constrain provider choice but makes customer and legal commitments defensible.
- **Recommendation:** Minimize sensitive collection; do not require Fayda/national ID unless a verified customer/legal use case requires it. Document hosting, subprocessors, access, encryption, retention, breach response and deletion/export before real data is used.
- **Evidence still required:** Legal/privacy review, current hosting/provider terms and regions, security configuration, key recovery and backup-restore proof.
- **Consequences:** Extra collection increases breach impact; unclear retention or data location creates customer and compliance risk; restrictive hosting choices may add cost.
- **Decision owner:** Product owner for product policy; hosting/data-region choice must follow legal and security review.
- **External contributors:** Ethiopian data/privacy counsel, hosting providers and pilot company.
- **Dependencies:** D09 and D16.
- **Required milestone:** Before real employee personal data is loaded.

### D14 — Connectivity, autosave, recovery and offline expectations

- **Priority / status:** P1 — PROPOSED
- **Decision question:** What must happen when the connection drops during employee setup or payroll preparation, and is offline payroll required for the first release?
- **Existing position:** Product documents emphasize mobile use and poor-connection performance; offline mode/PWA expansion is deferred in `PROJECT_RULES.md` and parked in `PLAN.md`. No verified customer requirement for offline payroll was located.
- **Options and consequences:** (a) Online-first with durable save/recovery has simpler consistency but depends on reliable connectivity; (b) offline drafts tolerate outages but require conflict handling; (c) full offline payroll improves availability but greatly expands security, synchronization and reconciliation risk.
- **Recommendation:** Use an online-first pilot with visible save state, safe autosave, retry/resume and no silent loss. Defer offline calculation/synchronization until interviews demonstrate need and conflict/reconciliation behavior is designed.
- **Evidence still required:** Browser/network interruption tests, autosave durability, duplicate-submit and recovery behavior; customer interviews on connectivity.
- **Consequences:** Online-first is simpler but requires dependable recovery; offline drafts add conflict handling; full offline processing adds synchronization and data-security complexity.
- **Decision owner:** Product owner decides first-release expectation; technical lead assesses feasible recovery guarantees.
- **External contributors:** Pilot users and security/QA reviewers.
- **Dependencies:** D09 and tested save/recovery behavior.
- **Required milestone:** Save/recovery proof before first pilot; offline decision may be deferred to post-pilot.

### D15 — Onboarding, support and service responsibilities

- **Priority / status:** P1 — PROPOSED
- **Decision question:** What onboarding, month-end support hours, escalation and response commitments will be provided during pilot and at commercial launch?
- **Existing position:** Older pilot documents contain detailed support channels and on-call claims, but their current availability is not verified. A market review historically reported no support infrastructure.
- **Options and consequences:** (a) Assisted pilot improves learning but consumes founder time; (b) self-service scales better but requires proven onboarding and support coverage; (c) managed service may attract customers who need help but makes EthioPayroll responsible for more operational work.
- **Recommendation:** Start with assisted onboarding and a written pilot support procedure, including incident severity, response owner role, evidence capture and stop-processing authority. Set commercial service levels only after support demand and capacity are measured.
- **Evidence still required:** Actual support capacity, onboarding checklist, escalation rehearsal, user comprehension and incident-handling rehearsal.
- **Consequences:** Weak support undermines trust at payroll deadlines; promising an unstaffed service level creates operational and commercial risk; assisted service consumes staff time.
- **Decision owner:** Product owner.
- **External contributors:** Pilot accountant/business, operations/security reviewer and any support operator.
- **Dependencies:** D09 and an identified support owner role.
- **Required milestone:** Documented before pilot kickoff; commercial service levels before release.

### D16 — Data export and account closure

- **Priority / status:** P1 — PROPOSED
- **Decision question:** What records can a customer export, and how are account closure, retention and deletion handled?
- **Existing position:** Reports and payroll exports are part of product requirements, but a complete customer data-portability and account-closure policy was not established by the reviewed controlling sources.
- **Options and consequences:** (a) Full authorized export supports portability but needs careful permissions and format maintenance; (b) report-only export is simpler but may trap customer records; (c) managed closure supports accountable offboarding but requires staff time and a legally reviewed retention/deletion process.
- **Recommendation:** Provide a documented customer export covering employee records, payroll history, payslips/reports and audit evidence subject to authorization. Define closure, retention exceptions and deletion with privacy counsel before real customer data is accepted.
- **Evidence still required:** Export completeness/reconciliation test, access controls, deletion/retention policy and restore/audit requirements.
- **Consequences:** Inadequate export creates customer lock-in; immediate deletion may conflict with lawful retention obligations; a managed package requires operational effort.
- **Decision owner:** Product owner for export behavior; legal/privacy counsel for retention and deletion terms.
- **External contributors:** Privacy/legal adviser and pilot customer/accountant; technical lead supplies implementation evidence.
- **Dependencies:** D13 and an approved data inventory.
- **Required milestone:** Export and closure terms before pilot data; deletion schedule before commercial release.

### D17 — Telebirr and future integrations

- **Priority / status:** P3 — DEFERRED
- **Decision question:** Which payment, accounting, attendance or tax integrations are justified by customers, supported by a provider/authority, and worth maintaining?
- **Existing position:** The plan defers payout APIs until provider contracts and failure behavior are understood. Older documents sometimes describe Telebirr file generation and integration as if they were equivalent.
- **Options and consequences:** (a) Manual handoffs are easiest to support but retain customer effort; (b) verified provider files reduce formatting work but do not execute payments; (c) contracted APIs can automate processing but add credentials, provider dependency, failure/reversal and support obligations.
- **Recommendation:** Defer direct Telebirr/API integration. First verify whether pilot customers need it, obtain official technical/contract documentation, and prove the manual handoff. Reopen after customer evidence and provider authorization.
- **Evidence still required:** Customer demand, provider agreement/API documentation, sandbox behavior, failure/reversal semantics, security review, reconciliation and support ownership.
- **Consequences:** Deferral avoids unsupported money movement but retains customer effort; premature integration adds credentials, provider dependencies and operational risk.
- **Decision owner:** Product owner.
- **External contributors:** Customer/accountant, provider/bank, security and legal advisers.
- **Dependencies:** Successful controlled payroll and provider evidence.
- **Required milestone:** Post-pilot review; defer unless customer and provider evidence is available.

## Decision categories and external approvals

These categories clarify who can resolve an item; they do not replace the per-decision owners above.

| Category | Decisions | Evidence/approval required |
|---|---|---|
| **A. Management decisions** | D01–D04, D06–D10, D14–D17 | Product owner records a chosen option, rationale, scope and reopening trigger. Market claims remain provisional until researched. |
| **B. Customer research** | D01, D02, D05, D06, D09, D14, D15, D17 | Interview notes from actual business owners/accountants; distinguish stated interest from observed use and willingness to pay. |
| **C. Legal/professional** | D08, D11–D13, D16; statutory rule approval in D12 | Written Ethiopian tax, pension, labour and privacy interpretation as applicable; current official sources/forms; bank/provider requirements. Do not infer law or authority procedure from code. |
| **D. Technical/security evidence** | D02, D04, D07–D08, D13–D16 | Exact-SHA tenant/role tests, workflow/reconciliation evidence, safe payment-state transitions, backup/restore and data lifecycle evidence. |
| **E. Deferrable** | D05 final price, expanded portfolio dashboard, offline processing, D17 integrations, wider language expansion | Defer only with the stated trigger. Deferral does not waive a pilot prerequisite such as safe data handling, accurate calculations or reliable recovery. |

## Pilot and release gates

Each stage requires a recorded go/no-go review. Passing a stage does not automatically authorize the next one.

### Gate 1 — Internal end-to-end validation

- **Entry:** Isolated synthetic tenant/data; known test scenarios; a candidate release SHA; documented calculation assumptions.
- **Activities:** Complete setup, employee/input entry, payroll calculation, explanation, review, approval, lock, payslips, reports, payment-file preparation, reconciliation, retry and correction/reversal tests. Exercise tenant separation and interrupted-save recovery.
- **Exit evidence:** Repeatable test results at the exact SHA; PAYE/pension/net and all outputs reconcile to independently approved expected cases; no unresolved critical defect; PostgreSQL/migration and browser evidence where relevant.
- **Stop conditions:** Any incorrect statutory amount, cross-company disclosure, unauthorized approval, historical payroll mutation, data loss or unsafe payment instruction.

### Gate 2 — One real-business supervised parallel payroll

- **Entry:** Gate 1 passed; willing company and qualified accountant identified; legal/calculation approvals for in-scope rules; privacy/data terms, access controls, support and recovery approved; no unresolved critical security or payroll issue.
- **Activities:** Run EthioPayroll in parallel with the company’s existing payroll process. The existing approved process remains the payment/filing authority. Reconcile employee-level gross/net, PAYE, pension, allowances/deductions, payslips, bank file, schedules, accounting output and audit history.
- **Exit evidence:** Discrepancy log with causes, corrections and retests; no unexplained material differences; written accountant acceptance or written objections; company decision to repeat or stop.
- **Stop conditions:** Any unexplained amount difference, cross-company exposure, unauthorized approval, corruption of locked history, lost records or ambiguous/unsafe payment instructions.

### Gate 3 — Three-business controlled pilot

- **Entry:** Gate 2 exit accepted; first customer’s objections resolved or explicitly scoped out; onboarding/support/recovery process demonstrated.
- **Activities:** Expand sequentially to **three businesses total, including the first**, and record company-specific payroll complexity, user roles, exceptions, support effort and reconciliation results.
- **Exit evidence:** Each business completes its in-scope cycle; accountant feedback is recorded separately; no critical unresolved issue; repeatable onboarding, support and data export evidence.
- **Stop conditions:** Any severe calculation, isolation, approval, history or data-loss failure; repeated unhandled discrepancies; support cannot safely respond.

### Gate 4 — Commercial release decision

- **Entry:** Three-business pilot reviewed; product scope and customer segment approved; legal rules and data practices approved for marketed use; pricing and service offer tested; operational support, backups/restore and incident response demonstrated.
- **Exit evidence:** Signed management go/no-go decision, approved requirements and claims, current release/security evidence, published customer responsibilities, tested export/closure path and support plan.
- **Stop conditions:** Unapproved legal claims, no accountable support, unsafe recovery/data handling, unresolved critical calculation or tenant risk, or payment/filing claims beyond verified capability.

### Gate 5 — Ten-business adoption milestone

- **Entry:** Commercial release approved; controlled deployment and support capacity available; no open critical issue; portfolio/tenant monitoring and customer exit process proven.
- **Activities:** Add customers gradually, monitor successful cycles, discrepancy rates, support load, recoveries, onboarding completion and export/closure requests.
- **Exit evidence:** Management reviews observed adoption and operating capacity before any further scale step. Ten businesses is an adoption milestone, not a pilot definition or evidence of readiness for hundreds.
- **Stop conditions:** Deteriorating reconciliation, privacy/security incident, unmanageable support load, or inability to isolate/recover company records.

## Five highest-priority decisions

1. **D01 — Select the first customer and buyer hypothesis**, then validate it with real businesses and accountants.
2. **D04 and D07 — Define company-authorized accountant access and approval roles** before requirements are approved.
3. **D10 — Approve the staged pilot sequence** so “one,” “three,” and “ten” have distinct meanings.
4. **D12 — Establish who approves statutory calculations and what evidence is required** before real payroll reliance.
5. **D13 — Establish safe personal-data handling and hosting evidence** before any employee data is loaded.

## What can be decided now

Management can approve the broad direction, a business-owned workspace as the proposed model, a one-business shadow followed by three businesses total, and the separation between payroll approval, payment-file preparation, actual bank execution, tax/pension submission and receipt reconciliation. These approvals still need to be recorded by the authorized product owner; this document proposes them but does not presume approval.

## Customer research required

Validate the initial industry and employee range, buyer/operator roles, accountant access needs, language preference, pricing and support expectations, connectivity constraints, first-pilot profile, and demand for Telebirr or other integrations. Do not turn historical estimates or interview enthusiasm into “validated” claims without recorded evidence.

## Engineering work that can proceed without closing every decision

- Continue isolated synthetic end-to-end validation of the existing monthly workflow.
- Reconcile calculation paths using agreed synthetic inputs and independently reviewed expected results; keep unresolved legal assumptions visible.
- Verify tenant isolation, approval authorization, locked-history behavior, retry/idempotency and save/recovery behavior on the exact candidate revision.
- Make report, bank-file, filing and payment states explicit and distinguish generated, submitted, accepted, paid and reconciled.
- Keep real tax filing, bank payment APIs, offline payroll and broad portfolio tooling out of scope until the stated evidence gates are met.

These are recommendations for bounded engineering evidence, not authorization to change statutory calculations or production behavior.

## Recommended approval sequence

1. Product owner reviews and records D01–D04, D06–D07, D10 and the proposed product/payment boundaries.
2. Conduct targeted customer/accountant discovery for D01–D02, D05–D06, D09, D14–D15 and D17.
3. Obtain written professional and provider evidence for D08, D11–D13 and D16; record unresolved matters as blockers for the affected pilot scope.
4. Approve product requirements derived from these decisions, explicitly marking provisional and deferred capabilities.
5. Complete Gate 1; only then authorize Gate 2 with the named participating roles, written consent/terms and approved calculations.
6. Review pilot evidence before moving from one to three businesses, from three to commercial release, and from commercial release to ten-business adoption.

## Source notes

- `PLAN.md` — current engineering priorities and parked ideas; item 3 status text requires reconciliation with the merge state recorded in Git.
- `PRODUCT_GOVERNANCE.md`, `PRODUCT_GOVERNANCE_GUIDE.md`, `OPERATING_PRINCIPLES.md` — historical product direction and decision process; not a substitute for an approved baseline.
- `PROJECT_RULES.md` — historical narrow-SME/one-primary-user scope; conflicts with the owner-confirmed broader business-and-accountant direction and should not silently override it.
- `PRD-00` through `PRD-09` — July 2026 draft journeys; use as requirements references only after approval and evidence review.
- `ARCHITECTURE_DECISIONS.md`, `ROADMAP.md`, `ACTION_PLAN.md` — historical technical and delivery proposals; scale targets and estimates are not evidence of actual capacity or customer need.
- `PRODUCT_MARKET_READINESS_REVIEW.md` — explicitly records no customer interviews and no pricing model, while also making older readiness and capability claims that need fresh verification.
- `PILOT_PACKAGE.md`, `PILOT_READINESS_REPORT.md`, `docs/product-checkpoint-2026-09-30.md` — historical pilot process/readiness evidence with different dates, SHAs and conclusions. Do not use old deployment status as current proof.
- `docs/decisions/2026-10-25-payroll-rules.md`, `ETHIOPAYROLL_LEGAL_ADVISER_PACK_FINAL.md`, `LEGAL_SOURCE_VERIFICATION_REGISTER.md`, `LEGAL_RULE_IMPLEMENTATION_STATUS.md` — payroll-law questions and professional responses; unresolved items remain unresolved until written evidence closes them.

**Control note:** When management approves a decision, record the approver role, date, chosen option, rationale and evidence. Until that record exists, the status remains OPEN, RESEARCH REQUIRED, PROPOSED or DEFERRED. This register should feed the approved product baseline, PRDs and engineering plan; it does not replace them.
