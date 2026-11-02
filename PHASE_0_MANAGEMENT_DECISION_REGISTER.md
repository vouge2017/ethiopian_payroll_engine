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

## Product-direction alignment — proposed, not approved

The owner has proposed a long-term North Star: progressively automate controlled, repetitive work across employee/workforce records, attendance, payroll, validation, approvals, payments, statutory reporting, reconciliation and employee records. The proposed operating principle is **Human-led accountability, machine-led execution**. This proposal does not approve these capabilities for immediate delivery and does not amend the current engineering task in `PLAN.md`.

The original D01–D17 questions, positions, options, recommendations and statuses above are preserved as the decision history. The following addenda specify how each question relates to the proposed North Star. They are proposals, not management decisions. Public sources and existing project documents do not prove customer demand, provider access, legal approval or implementation.

### D01 — Customer segment and buyer alignment

- **Original question:** Which Ethiopian employer and buyer should the first release serve?
- **Proposed revised position:** Keep self-managed businesses and accountant-supported businesses in the long-term audience; choose one evidence-backed first-pilot profile. Do not declare the SME/employee range validated.
- **Evidence / unknowns:** Existing project documents state the intended audience; no current interview or willingness-to-pay evidence is recorded here. Historical readiness findings need fresh verification.
- **Research / external confirmation / approval:** Customer research required; no provider/legal confirmation for segment choice. Product owner approval required.
- **Architecture impact:** Business-owned workspaces with optional scoped accountant membership remain proposed; portfolio access is a later capability.
- **Dependencies / timing:** P0, before requirements approval and first-pilot recruitment.

### D02 — Employee range and capacity alignment

- **Original question:** What pilot size and tested capacity should be supported without imposing a permanent ceiling?
- **Proposed revised position:** Treat headcount as an evidence-based operating envelope and test target, not a permanent limit. Workforce/attendance ambition does not place those modules in the first release.
- **Evidence / unknowns:** Draft PRDs contain inconsistent 50, 100 and 50–200 figures; no accepted market or load evidence is established here.
- **Research / external confirmation / approval:** Customer research and technical performance evidence; product owner approval.
- **Architecture impact:** Avoid schema/API limits tied to pilot size; test imports, calculation, reports and exports at a representative workload.
- **Dependencies / timing:** P0 for requirements/capacity claims; revisit before pilot size is fixed.

### D03 — Business subscription and workspace ownership alignment

- **Original question:** Does the business contract directly or does an accountant buy a multi-client service?
- **Proposed revised position:** Retain business-owned workspaces as the proposed starting model; allow a customer to use the platform alone or invite a scoped accountant. Keep portfolio billing a later commercial choice.
- **Evidence / unknowns:** Draft journeys support owner-created workspaces; payer and packaging preferences remain unvalidated.
- **Research / external confirmation / approval:** Interview businesses/accounting firms; review contracting and data-control responsibilities; management approval required.
- **Architecture impact:** Separate tenant ownership, membership, billing account and accountant organization; do not assume they are one identity.
- **Dependencies / timing:** P0 before workspace, permission and subscription requirements.

### D04 — Accountant access alignment

- **Original question:** What may an external accountant do for a business?
- **Proposed revised position:** Preserve optional accountant participation. Long-term multi-company operations should cross only businesses that granted and can revoke access. Defer a portfolio cockpit until need and isolation are proven.
- **Evidence / unknowns:** Drafts describe accountant review; current demand and end-to-end isolation evidence are not established by this register.
- **Research / external confirmation / approval:** Accountant research, authorization design review and tenant-isolation evidence; management approval required.
- **Architecture impact:** Company-scoped membership, explicit action permissions, revocation and audit history; portfolio grouping must not grant permission.
- **Dependencies / timing:** P0 policy; technical proof before any real data or pilot access.

### D05 — Pricing alignment

- **Original question:** What package and price will a target customer pay for?
- **Proposed revised position:** Keep pricing open; test value around time saved, reduced rework, support and compliance evidence, not a list of future integrations.
- **Evidence / unknowns:** No validated prices, recurring-use data or cost-to-serve evidence is recorded.
- **Research / external confirmation / approval:** Customer willingness-to-pay research and commercial review; management approval before commercial release.
- **Architecture impact:** Keep billing packaging/provider choices open; avoid billing complexity before selection.
- **Dependencies / timing:** P2 before commercial release; not a blocker to synthetic validation or supervised shadow payroll.

### D06 — Language alignment

- **Original question:** Which languages and payroll artifacts must be complete for launch?
- **Proposed revised position:** Preserve English, Amharic and existing Afaan Oromoo translations; define and validate the initial customer-facing minimum. Additional Ethiopian languages are an extensibility goal, not a readiness claim.
- **Evidence / unknowns:** Project documents/catalogs show intent; current native-speaker and accountant acceptance evidence is not established.
- **Research / external confirmation / approval:** Customer language research and native-speaker/payroll-practitioner review; management approval.
- **Architecture impact:** Localization keys and reviewed payroll terminology; voice interaction cannot substitute for reviewed text and artifact translation.
- **Dependencies / timing:** P0 boundaries; P1 for a pilot user relying on a language.

### D07 — Approval workflow alignment

- **Original question:** When can one person prepare and approve, and when is maker-checker required?
- **Proposed revised position:** Keep workflow configurable to business policy and size. People authorize inputs, resolve exceptions and approve sensitive actions. Automation may prepare and validate but may not self-approve payroll.
- **Evidence / unknowns:** Drafts propose owner approval; universal legal, bank-mandate and customer controls are not established here.
- **Research / external confirmation / approval:** Customer research, role tests and professional review if a statutory duty is asserted; management approval.
- **Architecture impact:** Separate preparation, payroll approval, payment authorization, submission and external status; no AI approval path.
- **Dependencies / timing:** P0 policy; technical proof before pilot.

### D08 — Payment responsibility alignment

- **Original question:** Who prepares, authorizes, submits, co-signs and verifies salary transfer?
- **Proposed revised position:** Long-term payment orchestration is proposed. Initial safe boundary remains approved payment instructions/file preparation and evidence-backed reconciliation, while employer-authorized users and licensed providers control transfer.
- **Evidence / unknowns:** Ethio telecom documents organization bulk payments; Bank of Abyssinia documents corporate bulk transfer with configurable inputter/checker/authorizer roles. Neither establishes an EthioPayroll contract, API, mandate or successful transfer. See evidence register.
- **Research / external confirmation / approval:** Pilot bank/provider must confirm format, eligibility, fees, limits, verification, authorization, status and settlement evidence; legal review for any intermediary role.
- **Architecture impact:** Keep approved, initiated, processing, settled, failed and reconciled separate. Do not hold customer salary funds absent an approved legal/provider model.
- **Dependencies / timing:** P1 payment-file handoff; P2 provider orchestration after contract and evidence.

### D09 — First pilot profile alignment

- **Original question:** Which willing company and accountant should complete the first supervised parallel payroll?
- **Proposed revised position:** Select a real employer with a qualified accountant, manageable complexity, appropriate employee notice/consent and willingness to compare against its existing authoritative payroll.
- **Evidence / unknowns:** No participating company or written accountant acceptance is established here.
- **Research / external confirmation / approval:** Recruit and document a customer; legal/privacy/provider review before real data or movement of funds.
- **Architecture impact:** Use manual provider handoffs until an integration is separately approved and accepted.
- **Dependencies / timing:** P1 after synthetic gates; before real employee data.

### D10 — Pilot sequence alignment

- **Original question:** How do one-business validation, three-business pilot and ten-business adoption relate?
- **Proposed revised position:** Preserve distinct gates: internal synthetic validation → one supervised parallel run → three independent controlled businesses → separate commercial-release decision → ten-business adoption milestone.
- **Evidence / unknowns:** Existing plan/pilot docs include inconsistent historical gates; no current pilot completion is claimed here.
- **Research / external confirmation / approval:** Evidence from each gate and recorded management go/no-go; continue customer research through each stage.
- **Architecture impact:** Do not claim portfolio-scale maturity or build scale-only features from one pilot.
- **Dependencies / timing:** Approve gate definitions P0; each progression requires a separate decision.

### D11 — Tax and pension submission alignment

- **Original question:** What does EthioPayroll prepare, submit, receive and reconcile for PAYE and pension?
- **Proposed revised position:** Progress from filing-ready preparation and clear instructions to authorized electronic submission only where official channels and agreements permit. Report generated, submitted, accepted/rejected, paid and reconciled separately.
- **Evidence / unknowns:** Official MoR e-tax references exist, but EthioPayroll API/authorization and current PAYE correction procedure were not verified. POESSA publishes its mandate and official laws/directives; an employer API/contract was not found in this review.
- **Research / external confirmation / approval:** Confirm process with MoR/POESSA/revenue authority and qualified tax/pension advisers; provider/API access is required for electronic submission.
- **Architecture impact:** Future submission adapter/status evidence; no portal-automation assumption.
- **Dependencies / timing:** P1 manual handoff and report acceptance; P2 electronic submission integration.

### D12 — Calculation authority alignment

- **Original question:** Who approves statutory rules and interpretations?
- **Proposed revised position:** Calculations remain deterministic, versioned and independently testable. AI/automation cannot determine statutory obligations or alter rule values. Each production rule needs an official source, effective date, worked tests and written professional interpretation when application is unclear.
- **Evidence / unknowns:** Official legal sources/adviser documents exist for some topics; some interpretations, current procedures and effective dates remain unresolved.
- **Research / external confirmation / approval:** Qualified Ethiopian tax, pension and labour review; management assigns an accountable rule owner.
- **Architecture impact:** Versioned rules and reproducible calculation records separate from AI and providers.
- **Dependencies / timing:** P0 governance; written professional acceptance before real reliance on each unresolved rule.

### D13 — Data protection alignment

- **Original question:** What personal data may be processed, where, by whom, for how long and under what controls?
- **Proposed revised position:** Before real employee data, establish controller/processor roles, minimization, hosting/transfer map, retention/deletion, contracts, incident response and sensitive-data controls. Do not require Fayda/national ID or biometrics without verified need and legal basis.
- **Evidence / unknowns:** Official Proclamation 1321/2024 is in force and includes processor, security, processing-record, data-sovereignty and sensitive-data transfer provisions. EthioPayroll’s hosting/subprocessors and application require counsel/infrastructure review.
- **Research / external confirmation / approval:** Ethiopian privacy/legal review and deployment/provider evidence; management approval before real data.
- **Architecture impact:** Data-location inventory, processor agreements, access/security controls, export/deletion and audit records.
- **Dependencies / timing:** Reserve controls in P0 requirements; satisfy before P1 real-data pilot.

### D14 — Connectivity and recovery alignment

- **Original question:** What connectivity failures and offline operation must customers tolerate?
- **Proposed revised position:** Reliable saving, synchronization, recovery and auditability are North Star outcomes. Full offline payroll is unapproved until need and conflict handling are researched.
- **Evidence / unknowns:** Pilot connectivity/device needs and restore/sync evidence are unknown.
- **Research / external confirmation / approval:** Customer interviews, failure/recovery tests and management scope decision.
- **Architecture impact:** Define durable-save acknowledgement and recovery boundaries; do not queue approval or payment offline.
- **Dependencies / timing:** P1 save/recovery evidence; P3 full offline, reopen only if pilot evidence warrants it.

### D15 — Onboarding and support alignment

- **Original question:** Who configures customers, supports monthly operations and handles incidents?
- **Proposed revised position:** Guided onboarding, clear responsibility and supportable process states are part of the operating product. Automation may assist routine communication; people own exception decisions and customer commitments.
- **Evidence / unknowns:** Service hours, response targets, onboarding effort and support cost are unverified.
- **Research / external confirmation / approval:** Pilot support observations, customer research and operating-capacity estimate; management approval before commercial promises.
- **Architecture impact:** Actionable errors, support evidence export and escalation records; no AI-only decisions on high-impact outcomes.
- **Dependencies / timing:** P1 pilot support; P2 published service levels.

### D16 — Data export and closure alignment

- **Original question:** What records can a customer export, retain and remove at closure?
- **Proposed revised position:** Make business records portable and closure predictable, subject to statutory retention and data-subject rights confirmed by counsel.
- **Evidence / unknowns:** Complete export inventory, closure procedure and applicable retention schedule are not established here.
- **Research / external confirmation / approval:** Customer/accountant export review and privacy/legal advice; management approval.
- **Architecture impact:** Export payroll history, reports, rule/version provenance and audit evidence; deletion respects statutory retention/legal holds.
- **Dependencies / timing:** P1 pilot exit/continuity; P2 commercial closure policy.

### D17 — Provider and integration alignment

- **Original question:** Which integrations are justified, supported and worth maintaining?
- **Proposed revised position:** Keep banks/payment providers, attendance systems, accounting/business software and government systems as candidate integrations. Integration readiness is a design principle, not an approved connector or provider promise.
- **Evidence / unknowns:** Telebirr organizational bulk payment and developer/test materials are public; salary-batch API access, permissions, fees, limits and settlement/status contract remain unverified. NBE salary API language located is in a draft strategy.
- **Research / external confirmation / approval:** Provider docs, eligibility, sandbox/account, contract, service limits, fees, data responsibilities and test acceptance; counsel for regulated role; management prioritization.
- **Architecture impact:** Provider adapters, secure credentials, idempotency, status evidence and reconciliation are proposed principles; defer provider-specific production integration.
- **Dependencies / timing:** P1 manual handoff; P3 direct connector until customer demand/provider access.

## Proposed additional decisions D18–D25

The following proposals extend the register without changing D01–D17 identifiers or history. None is approved.

### D18 — Attendance and workforce time management

- **Priority / status:** P2 — PROPOSED
- **Decision question:** Which attendance, shifts, overtime, leave and time inputs should EthioPayroll own, import or integrate, and what evidence is required before they affect pay?
- **Existing position:** Project direction includes leave/overtime and broader workforce operations; device/mobile/third-party scope is not approved.
- **Options and consequences:** Manual entry/import minimizes initial scope but retains work; native capture improves workflow but adds privacy, device and dispute handling; integration reuses customer systems but depends on provider access/data quality.
- **Recommendation:** Start with reviewable, sourced payroll inputs and explicit correction; research attendance sources before selecting native capture/connectors. Missing punches must not auto-create deductions.
- **Evidence / unknowns:** Customer/device mix, data quality, labour-law treatment and provider access; customer research and professional confirmation required.
- **Management approval:** Required before adding attendance product scope.
- **Architecture impact:** Provenance, approval, period, correction history and non-destructive imports; biometric capture is not compulsory.
- **Owner / contributors:** Product owner; employers, accountants, HR practitioners, legal adviser, attendance vendors.
- **Dependencies / timing:** D12 and payroll input model; P2 after reliable monthly payroll.

### D19 — Employee bank-account verification and payment preferences

- **Priority / status:** P2 — RESEARCH REQUIRED
- **Decision question:** What payment details may employees nominate, how can each provider verify them, and who approves changes?
- **Existing position:** Employee payment details are part of payroll preparation; no universal provider verification is established.
- **Options and consequences:** Syntax checks are cheap but not ownership proof; employer document checks add manual work; provider confirmation may improve accuracy but requires service access, terms and privacy basis.
- **Recommendation:** Distinguish format validation from provider-confirmed verification; never label unconfirmed details verified; review and audit changes.
- **Evidence / unknowns:** Provider-supported account types, verification response/fees, employee preferences, consent and mismatch handling; customer/provider/legal validation required.
- **Management approval:** Required for data collection scope.
- **Architecture impact:** Store verification source/time/status and change history; minimize and protect sensitive fields.
- **Owner / contributors:** Product owner; customers, bank/payment providers, privacy counsel, security reviewer.
- **Dependencies / timing:** D08/D13; manual verification P1, provider validation P2.

### D20 — Salary payment orchestration

- **Priority / status:** P2 — PROPOSED
- **Decision question:** Should EthioPayroll progress from preparing instructions/files to provider initiation and status reconciliation, and under what authorization model?
- **Existing position:** Current materials describe external bank handoff; no provider contract or settlement integration is evidenced here.
- **Options and consequences:** File preparation leaves money movement with the employer/provider but stays manual; initiation reduces work but adds security, licensing, duplicate, reversal and support obligations; staged delivery limits risk.
- **Recommendation:** Stage file preparation/reconciliation first. Initiate only with provider contract, legal review, employer authorization, idempotency and independently verifiable settlement. Do not hold salary funds absent a legally approved model.
- **Evidence / unknowns:** API/accepted file spec, eligibility, fees/limits, mandates, callbacks, status/settlement reports and reversal/support process.
- **Management approval:** Required; provider and counsel evidence also required.
- **Architecture impact:** Explicit batch state machine, stable identity, safe retries, audit and reconciliation evidence.
- **Owner / contributors:** Product owner; finance, bank/provider, legal/regulatory adviser, security/operations.
- **Dependencies / timing:** D08/D13/D19; file handoff P1, initiation P2/P3.

### D21 — Electronic tax and pension submissions

- **Priority / status:** P2 — RESEARCH REQUIRED
- **Decision question:** Which statutory outputs may be prepared, electronically submitted and reconciled with authority acknowledgements?
- **Existing position:** PAYE/pension preparation is needed; employer/authorized-agent filing remains the assumed responsibility absent an approved integration.
- **Options and consequences:** Downloadable schedules leave manual submission; portal automation may be brittle or unauthorized; official APIs/contracts offer a stronger route only if actually available.
- **Recommendation:** First produce reproducible filing-ready outputs. Pursue only verified official APIs or explicitly authorized flows; store submission reference, acknowledgement/rejection and payment evidence separately.
- **Evidence / unknowns:** Current MoR/POESSA process, authority, terms, formats, access prerequisites and correction/acknowledgement behavior; current operational integration not verified.
- **Management approval:** Required after professional/authority evidence.
- **Architecture impact:** Submission package identity/version, external references, response evidence and safe retries; generated never means submitted/accepted.
- **Owner / contributors:** Product owner; tax/pension professionals, MoR/POESSA/revenue authority, customer accountant.
- **Dependencies / timing:** D11/D12; manual P1, electronic submission P2.

### D22 — Accounting and business-system integrations

- **Priority / status:** P2 — RESEARCH REQUIRED
- **Decision question:** Which accounting, ERP, HR and attendance systems justify a maintained connector, and what remains export/import?
- **Existing position:** Customers should be able to retain their existing accounting platform; no specific customer system or integration is approved.
- **Options and consequences:** Standard exports are lower-cost but manual; generic APIs/webhooks automate but require version/support commitments; provider-specific connectors improve fit but multiply maintenance.
- **Recommendation:** Start with reconciled standard exports and learn the pilot system mix; prioritize one connector only after repeated demand and verified provider access.
- **Evidence / unknowns:** Pilot system inventory, account mapping, provider specs/sandbox, data ownership and reconciliation acceptance.
- **Management approval:** Required before connector priority.
- **Architecture impact:** Stable internal contracts, versioned exports, adapters and idempotent imports; avoid a generalized platform prematurely.
- **Owner / contributors:** Product owner; accountants, customers, technical lead, vendors.
- **Dependencies / timing:** D01/D11/D17; P2 after pilot evidence.

### D23 — Voice and conversational interaction

- **Priority / status:** P3 — DEFERRED
- **Decision question:** Which tasks benefit from voice/conversation, in which languages, and under what confirmation controls?
- **Existing position:** English, Amharic and existing Afaan Oromoo translations are targets; voice/conversation is proposed ambition only.
- **Options and consequences:** No conversational layer minimizes risk; read-only assistance may improve explanations; preparing actions could reduce entry effort but adds transcription, ambiguity and privacy risks.
- **Recommendation:** Defer until core workflows and language terminology are validated. If reopened, start read-only/draft preparation with user review and explicit confirmation before writes or high-impact actions.
- **Evidence / unknowns:** User value, speech accuracy, language coverage, accessibility, data location/retention and threat model.
- **Management approval:** Required before a voice/conversation feature.
- **Architecture impact:** Authenticated, scoped tools; no privileged direct action; confirmation and audit of input/output.
- **Owner / contributors:** Product owner; local-language users, accessibility, privacy/security and AI reviewers.
- **Dependencies / timing:** D06/D13/D24; P3; reopen on measured workflow friction.

### D24 — AI and workflow automation governance

- **Priority / status:** P1 — PROPOSED
- **Decision question:** Which administrative tasks may AI prepare/explain, and what actions must stay deterministic and human-authorized?
- **Existing position:** Proposed ambition includes document extraction, explanations, anomaly detection and workflow support; no AI scope is approved for immediate delivery.
- **Options and consequences:** No AI is simplest; bounded assistance can reduce clerical work but may err or expose data; action-taking AI adds high-impact control risk.
- **Recommendation:** Allow only bounded assistive uses after privacy/security review. AI must not calculate statutory obligations, change legal parameters, approve payroll, authorize payment or submit returns. Require provenance, human review and audit.
- **Evidence / unknowns:** Model/provider, data location/retention, threat model, accuracy/error evaluation, monitoring and fallback.
- **Management approval:** Required before any AI feature.
- **Architecture impact:** Separate deterministic calculator from AI; low-privilege tools, typed actions, provenance and confirmation; no unrestricted write access.
- **Owner / contributors:** Product owner; technical/security lead, privacy counsel, payroll professionals, customers.
- **Dependencies / timing:** D12/D13; governance P1 before any feature, AI implementation P3.

### D25 — Integration and automation architecture

- **Priority / status:** P1 — PROPOSED
- **Decision question:** Which integration seams should be standardized now, and which provider connectors should wait for verified demand/access?
- **Existing position:** Governance documents favor a narrow initial system and defer broad API/AI/multi-company scope; the proposed North Star favors integration readiness.
- **Options and consequences:** Premature provider work risks rework; light internal contracts preserve options at modest cost; a generalized event platform/microservices add complexity before demonstrated need.
- **Recommendation:** Propose only light seams: versioned payroll input/output contracts, idempotency, explicit external states, audit provenance and secure adapter boundaries. Defer public API, event platform and provider connectors until approved use cases.
- **Evidence / unknowns:** Existing ADR compatibility, actual provider/customer demand, security and operating capacity; not resolved by this proposal.
- **Management approval:** Product owner and technical lead approval; record material architecture choices in an ADR.
- **Architecture impact:** Keep statutory calculation provider-independent; make callbacks/retries safe; never infer completion from request dispatch.
- **Owner / contributors:** Product owner for scope; technical lead, security/operations, customers and provider representatives.
- **Dependencies / timing:** D17/D20/D21/D22; P1 principles; implement only seams required by approved first-phase requirements.

## Decision categories and external approvals

These categories clarify who can resolve an item; they do not replace the per-decision owners above.

| Category | Decisions | Evidence/approval required |
|---|---|---|
| **A. Management decisions** | D01–D25 for product scope, priorities, roles and gates | Record a chosen option, rationale, scope and reopening trigger. A management choice does not replace customer, professional, provider or technical proof. |
| **B. Customer research** | D01–D02, D05–D06, D09, D14–D15, D17–D19, D22–D24 | Interview actual business owners/accountants/employees as relevant; distinguish stated interest from observed use and willingness to pay. |
| **C. Legal/professional** | D08, D11–D13, D16, D18–D21, D24 | Obtain written Ethiopian tax, pension, labour, privacy and payment-role interpretation as applicable; current official sources/forms and provider requirements. Do not infer law or authority procedure from code. |
| **D. Technical/security evidence** | D02, D04, D07–D08, D13–D16, D18–D25 | Exact-SHA tenant/role tests, calculation and workflow reconciliation, safe payment/submission states, backup/restore, data lifecycle and connector evidence. |
| **E. Deferrable** | Final D05 pricing, portfolio cockpit, full offline processing, D17/D19/D20 provider connections, D21 electronic submission, D22 connectors, D23 voice, D24 AI features, generalized D25 integration platform, wider language expansion | Defer with a trigger. Deferral does not waive a pilot prerequisite such as safe data handling, accurate calculations or reliable recovery. |

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

Management can decide whether to endorse the proposed North Star and operating principle, choose the first segment to validate, confirm a bounded first-phase scope and approve distinct pilot gates. A business-owned workspace and staged file/manual handoff are proposals, not approved decisions. Any approval must be recorded by the authorized product owner; this document does not presume approval.

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

- ETHIOPAYROLL_PRODUCT_NORTH_STAR.md, PROPOSED_PRODUCT_BASELINE_STRUCTURE.md, PRODUCT_INTEGRATION_ARCHITECTURE_PRINCIPLES.md, PHASE_0_EVIDENCE_AND_EXTERNAL_VALIDATION_REGISTER.md, PHASE_0_MANAGEMENT_APPROVAL_LIST.md and ETHIOPAYROLL_STAGED_DELIVERY_SEQUENCE.md are proposed companion documents created for this alignment; none records management approval or implementation.
- The current source-control note in PLAN.md reconciles its dated 1 November PR #47 status with origin/main at f52330a; the earlier dated line is retained as history.

- `PLAN.md` — current engineering priorities and parked ideas; item 3 status text requires reconciliation with the merge state recorded in Git.
- `PRODUCT_GOVERNANCE.md`, `PRODUCT_GOVERNANCE_GUIDE.md`, `OPERATING_PRINCIPLES.md` — historical product direction and decision process; not a substitute for an approved baseline.
- `PROJECT_RULES.md` — historical narrow-SME/one-primary-user scope; conflicts with the owner-confirmed broader business-and-accountant direction and should not silently override it.
- `PRD-00` through `PRD-09` — July 2026 draft journeys; use as requirements references only after approval and evidence review.
- `ARCHITECTURE_DECISIONS.md`, `ROADMAP.md`, `ACTION_PLAN.md` — historical technical and delivery proposals; scale targets and estimates are not evidence of actual capacity or customer need.
- `PRODUCT_MARKET_READINESS_REVIEW.md` — explicitly records no customer interviews and no pricing model, while also making older readiness and capability claims that need fresh verification.
- `PILOT_PACKAGE.md`, `PILOT_READINESS_REPORT.md`, `docs/product-checkpoint-2026-09-30.md` — historical pilot process/readiness evidence with different dates, SHAs and conclusions. Do not use old deployment status as current proof.
- `docs/decisions/2026-10-25-payroll-rules.md`, `ETHIOPAYROLL_LEGAL_ADVISER_PACK_FINAL.md`, `LEGAL_SOURCE_VERIFICATION_REGISTER.md`, `LEGAL_RULE_IMPLEMENTATION_STATUS.md` — payroll-law questions and professional responses; unresolved items remain unresolved until written evidence closes them.

**Control note:** When management approves a decision, record the approver role, date, chosen option, rationale and evidence. Until that record exists, the status remains OPEN, RESEARCH REQUIRED, PROPOSED or DEFERRED. This register should feed the approved product baseline, PRDs and engineering plan; it does not replace them.
