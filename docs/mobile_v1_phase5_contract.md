# Mobile_V1 Phase 5 Contract

> Status: Active  
> Date: 2026-04-08  
> Workflow: [phase_workflow.md](./phase_workflow.md)  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)  
> Reference: [mobile_v1_phase4_contract.md](./mobile_v1_phase4_contract.md)  
> Reference: [mobile_v1_phase4_verification.md](./mobile_v1_phase4_verification.md)  
> Reference: [web_phase4_contract.md](./web_phase4_contract.md)

---

## 1. Goal

Deliver the app-side result delivery and download flow for approved `Mobile_V1` sessions.

This phase must extend the Phase 4 approved session so that a signed-in customer can reopen the same `/app/session/:sessionId` route and actually retrieve the prepared deliverables instead of seeing only preview/approval history.

The phase must:

- keep the normal customer journey inside `/app` and `/app/session/:sessionId`
- render approved-session result cards in the mobile app shell
- expose customer-facing file download actions for available published assets
- expose a bundle download for the approved session output
- reflect download-ready state in the workspace and session view

The business outcome is that an approved customer session ends with a practical mobile result-delivery surface, not only a status confirmation page.

---

## 2. Business Outcome

At the end of Phase 5:

- an approved app-side session renders a real result delivery state
- the customer can download available result files from the app shell
- the customer can download a packaged session bundle from the app shell
- the workspace still reopens the same session and reflects the delivered/approved status
- the customer no longer needs admin or sync tooling to retrieve finished outputs

This phase intentionally focuses on delivery of already prepared outputs. It does **not** yet add new content-type generation orchestration or bounded regeneration UX.

---

## 3. In Scope

### 3.1 App-Side Result Delivery State

- replace the app-side approved terminal state with a real delivery-oriented session view
- keep the approved conversation history visible
- show that review is complete and files are ready for retrieval
- keep the delivery UI mobile-first and Korean

### 3.2 Published Asset Download Actions

- expose app-side download actions for available published assets referenced by the existing manifest
- support download actions for the available artifact types already present in the runtime:
  - shorts/reels video
  - blog HTML file
  - thread text file
  - carousel image files
- keep customer file delivery under app-side routes rather than requiring legacy token routes

### 3.3 Bundle Download

- expose an app-side bundle download route for the approved session
- allow the customer to download a packaged archive of the approved result directory or equivalent approved output package
- make the bundle action visible from the approved app session page

### 3.4 Workspace Continuity

- show a clear approved/delivery-ready status in the workspace
- allow reopening approved sessions from the workspace
- keep the session route consistent before and after file retrieval

### 3.5 Korean UI Requirement

- all customer-facing Phase 5 UI must be Korean
- download labels, file section titles, helper text, and visible errors must be Korean

---

## 4. Out Of Scope

- new content-type generation request flow
- content-type selection cards for not-yet-generated outputs
- bounded regeneration UX
- usage billing or credit deduction
- voice recording or SSE transcription work
- real Google OAuth
- real payment integration
- operator-side production workflow changes
- removal of legacy `/s/<customer_token>` preview or file routes

Legacy routes may remain for regression safety, but they must not be the normal authenticated app-side path for customer result retrieval.

---

## 5. Required Inputs

The implementation may assume:

- the existing FastAPI + Jinja2 + static CSS + JS stack remains in use
- Phase 4 app-side preview and approval flow is already verified
- approved sessions may already contain `published/manifest.json` plus published preview/output files
- the existing sync/preview runtime may be reused where compatible
- the current authenticated user model remains a Phase 1 stub

If the bundle download reuses an existing sync/archive helper internally, that reuse must be explicit and documented.

---

## 6. Required Outputs

Phase 5 must produce:

1. App shell outputs
   - delivery-oriented approved session page
   - download cards or action rows for available result files
   - bundle download action

2. Routing outputs
   - app-side result download route(s) under `/app/session/:sessionId`
   - app-side bundle download route under `/app/session/:sessionId`
   - no normal authenticated app-side redirects into admin or sync tooling

3. Delivery outputs
   - customer-facing download access to published files
   - customer-facing download access to a packaged bundle

4. Verification outputs
   - Phase 5 verification document
   - command evidence
   - route-level evidence
   - downloaded artifact evidence

---

## 7. Acceptance Criteria

### A. Approved Session Delivery UI

- `/app/session/:sessionId` renders a real delivery state for `approved`
- the page clearly shows that review is complete and files are available
- the approved conversation/status history remains visible

### B. Individual Result Downloads

- the app-side approved session exposes download actions for available published assets
- at least one published asset can be downloaded directly from an app-side route
- the customer does not need admin or sync routes for normal retrieval

### C. Bundle Download

- the app-side approved session exposes a bundle download action
- the bundle route returns a real downloadable archive
- the archive contains approved session delivery artifacts or equivalent published outputs

### D. Workspace Continuity

- the workspace reopens an approved session after delivery work is added
- the workspace still shows the approved/delivery-ready session entry
- downloading files does not break the app-side session route

### E. App Shell Continuity

- the normal authenticated customer flow remains under `/app`
- the app-side flow does not require admin pages
- the app-side flow does not require sync CLI or sync API usage by the customer

### F. Mobile UX And Language

- all customer-facing Phase 5 UI introduced in this phase is Korean
- download controls remain usable on mobile widths
- the approved delivery view shows one clear primary retrieval action

---

## 8. Required Commands And Operator Flows

Phase 5 must support and document these commands or equivalent commands:

1. Install dependencies
2. Run local web app
3. Run Phase 5 tests
4. Run Phase 4 regression checks
5. Operator verification flow:
   - sign in through the stub path
   - complete onboarding
   - open an approved app-side session with published artifacts
   - confirm the approved session renders a real delivery view
   - download at least one individual asset from the app shell
   - download the bundle archive from the app shell
   - confirm the workspace still reopens the session after downloads

Exact command strings will be captured in the verification document after implementation.

---

## 9. Dependencies, Credentials, And Environment Assumptions

- current repository branch: `mobile-web-pivot`
- FastAPI application remains the delivery surface
- Jinja2 template rendering remains acceptable for `Mobile_V1`
- existing sync/archive helpers may be reused for verification
- local verification may use fixture preview/output assets already produced by the current runtime
- real auth and billing providers are not required in this phase

---

## 10. Completion Evidence Required

Phase 5 is only verified when the verification document includes:

1. Environment evidence
   - OS
   - Python/runtime version
   - local startup method

2. Command evidence
   - exact app startup command
   - exact Phase 5 test command
   - exact regression commands

3. Route evidence
   - app workspace route
   - app-side approved delivery route
   - at least one app-side file download route
   - app-side bundle download route

4. Artifact evidence
   - at least one downloaded published asset path or response proof
   - downloaded bundle archive path or response proof
   - updated `session_metadata.json` if delivery metadata changes are introduced

5. Flow evidence
   - the session remains in app-side routes throughout the normal authenticated delivery flow
   - the approved session is reopenable from the workspace after downloads

---

## 11. Explicit Non-Completion Cases

Phase 5 is **not** complete if:

- the approved app session still only shows a static status message with no retrieval actions
- downloads are available only through admin or sync tooling
- the app shell cannot download even one published asset directly
- the bundle archive route is missing or broken
- customer-facing delivery UI remains mixed-language or mostly English

---

## 12. Change Control

- If implementation expands to new generation-request orchestration, update this contract first.
- If implementation expands to bounded regeneration UX, update this contract first.
- If implementation requires a different app-side route structure, update the contract first.
- Verification may not silently expand the scope after implementation.
