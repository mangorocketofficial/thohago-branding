# Mobile_V1 Phase 4 Contract

> Status: Active  
> Date: 2026-04-08  
> Workflow: [phase_workflow.md](./phase_workflow.md)  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)  
> Reference: [mobile_v1_phase3_contract.md](./mobile_v1_phase3_contract.md)  
> Reference: [mobile_v1_phase3_verification.md](./mobile_v1_phase3_verification.md)  
> Reference: [web_phase4_contract.md](./web_phase4_contract.md)

---

## 1. Goal

Deliver the app-side production waiting, preview review, and approval flow inside the authenticated `Mobile_V1` app shell.

This phase must extend the Phase 3 intake-complete session so that a signed-in customer can continue from `awaiting_production` through preview review without falling back to the legacy token-based customer portal.

The phase must:

- keep the normal customer journey inside `/app` and `/app/session/:sessionId`
- show a real production-waiting state while preview assets are not yet ready
- render uploaded preview artifacts inside the app-side session view once available
- support customer approve and revision-request actions from the app shell
- reflect updated preview/approval states back into the workspace

The business outcome is that the authenticated mobile customer can open the same app session after interview completion, review the prepared preview assets, and complete the approval decision inside the app shell.

---

## 2. Business Outcome

At the end of Phase 4:

- a Phase 3-complete session in `awaiting_production` shows a real app-side waiting state
- once preview assets are uploaded by the existing production bridge, the same app session renders a real preview surface
- the customer can request revision or approve from the app-side session route
- the workspace and app session both reflect the updated status after preview actions
- the customer no longer needs `/s/<customer_token>/preview` or `/s/<customer_token>/complete` for the normal mobile app flow

This phase is an app-shell adaptation of the existing production/preview runtime. It does **not** yet introduce final download-package delivery or bounded regeneration UX.

---

## 3. In Scope

### 3.1 App-Side Waiting State

- render `awaiting_production` inside `/app/session/:sessionId`
- keep the waiting state customer-facing, mobile-first, and Korean
- show clear next-step messaging that preview preparation is in progress
- allow reopening the waiting session from `/app`

### 3.2 App-Side Preview Rendering

- render preview-ready sessions inside the authenticated app-side session route
- support sessions in `awaiting_approval` and `revision_requested`
- reuse the existing preview manifest and published artifact loading logic where compatible
- render available preview sections for:
  - shorts/reels video
  - blog HTML
  - thread text
  - carousel images

### 3.3 App-Side Approval Actions

- add app-side approve action
- add app-side revision request action
- keep the customer inside the app shell after each action
- show clear Korean action labels and feedback

### 3.4 App-Side Completion State

- render a real terminal state for `approved` inside `/app/session/:sessionId`
- show that preview review is complete
- allow returning to the workspace from the completed session

### 3.5 Workspace Continuity

- show preview-related status labels in the authenticated workspace
- allow reopening sessions in `awaiting_production`, `awaiting_approval`, `revision_requested`, and `approved`
- keep the workspace/customer experience consistent with the session route state

### 3.6 Korean UI Requirement

- all customer-facing Phase 4 UI must be Korean
- waiting notices, preview section labels, action buttons, status labels, and visible error states must be Korean

---

## 4. Out Of Scope

- direct content generation implementation from the app shell
- new sync API endpoints or new operator-side production workflows
- download-package delivery UX
- bounded regeneration UX
- usage billing or credit deduction
- voice recording or SSE transcription work
- real Google OAuth
- real payment integration
- removal of the legacy `/s/<customer_token>` preview and complete routes

Out-of-scope legacy routes may remain for regression safety, but they must not be the normal authenticated app-side path for the new Phase 4 mobile flow.

---

## 5. Required Inputs

The implementation may assume:

- the existing FastAPI + Jinja2 + static CSS + JS stack remains in use
- Phase 3 app-side upload and interview flow is already verified
- the existing sync/preview runtime from the web flow remains available for reuse
- preview artifacts may already be uploaded into `published/` by the existing sync service
- preview-ready sessions use the current manifest-driven artifact structure
- the current authenticated user model remains a Phase 1 stub

If app-side helper adapters are required to bind app session routes to the existing preview/approval services, that binding must be explicit and documented.

---

## 6. Required Outputs

Phase 4 must produce:

1. App shell outputs
   - app-side waiting state for `awaiting_production`
   - app-side preview rendering for `awaiting_approval` and `revision_requested`
   - app-side completion state for `approved`

2. Routing outputs
   - app-side preview/review actions under `/app/session/:sessionId`
   - no normal authenticated redirects into `/s/<customer_token>/preview` or `/s/<customer_token>/complete`

3. Preview outputs
   - manifest-driven rendering of available preview assets in the app shell
   - app-side approve and revision actions backed by the existing session state

4. Verification outputs
   - Phase 4 verification document
   - command evidence
   - route-level evidence
   - preview artifact evidence

---

## 7. Acceptance Criteria

### A. Waiting State

- `/app/session/:sessionId` renders a real waiting state for `awaiting_production`
- the waiting state is Korean and mobile-readable
- the workspace can reopen a waiting session

### B. Preview Rendering

- `/app/session/:sessionId` renders a real preview state for `awaiting_approval`
- `/app/session/:sessionId` renders a real preview state for `revision_requested`
- preview rendering is driven by the existing uploaded manifest and published assets
- at least one uploaded preview asset is visibly rendered in the app shell

### C. Approval And Revision

- app-side revision action changes the session stage to `revision_requested`
- app-side approve action changes the session stage to `approved`
- after each action, the customer remains in the app-side route surface
- session messages and chat-log style status history continue to record the decision

### D. Completion State

- `/app/session/:sessionId` renders a real completion state for `approved`
- the completion state clearly shows the review flow is complete
- the workspace reflects the approved session state

### E. App Shell Continuity

- the normal authenticated customer flow remains under `/app`
- the app-side flow does not require `/s/<customer_token>/preview` for normal usage
- the app-side flow does not require `/s/<customer_token>/complete` for normal usage

### F. Mobile UX And Language

- all customer-facing Phase 4 UI introduced in this phase is Korean
- preview sections and action controls remain usable on mobile widths
- the waiting, preview, revision, and completion states each show one clear next action

---

## 8. Required Commands And Operator Flows

Phase 4 must support and document these commands or equivalent commands:

1. Install dependencies
2. Run local web app
3. Run Phase 4 tests
4. Run Phase 3 regression checks
5. Operator verification flow:
   - sign in through the stub path
   - complete onboarding
   - open an app-side session already in `awaiting_production`
   - confirm the app-side waiting state renders
   - prepare preview-ready assets through the existing preview upload/runtime path
   - reopen the same `/app/session/:sessionId`
   - confirm preview artifacts render in the app shell
   - request revision once
   - confirm the session remains accessible from the app shell
   - approve once
   - confirm the app-side completion state renders
   - confirm the workspace reflects the updated stage

Exact command strings will be captured in the verification document after implementation.

---

## 9. Dependencies, Credentials, And Environment Assumptions

- current repository branch: `mobile-web-pivot`
- FastAPI application remains the delivery surface
- Jinja2 template rendering remains acceptable for `Mobile_V1`
- existing sync token and preview upload runtime may be reused for verification
- preview verification may use local fixture artifacts rather than real rendered media
- real auth and billing providers are not required in this phase

---

## 10. Completion Evidence Required

Phase 4 is only verified when the verification document includes:

1. Environment evidence
   - OS
   - Python/runtime version
   - local startup method

2. Command evidence
   - exact app startup command
   - exact Phase 4 test command
   - exact regression commands

3. Route evidence
   - app workspace route
   - app session waiting state route
   - app-side preview route behavior
   - app-side approve/revision route behavior

4. Artifact evidence
   - `published/manifest.json`
   - at least one published preview asset path
   - updated `session_metadata.json`

5. Flow evidence
   - the session remains in app-side routes throughout the normal authenticated preview flow
   - the final approved session is reopenable from the workspace
   - preview and completion states do not require legacy token-based routes for normal usage

---

## 11. Explicit Non-Completion Cases

Phase 4 is **not** complete if:

- app-side waiting is still only a placeholder with no preview-state continuation
- preview content exists but the app shell still redirects customers into `/s/<customer_token>/preview`
- approve or revision actions are only available through legacy token-based routes
- the workspace does not reflect preview-related state changes
- customer-facing preview/completion UI remains mixed-language or mostly English

---

## 12. Change Control

- If implementation expands to final download-package delivery, update this contract first.
- If implementation expands to bounded regeneration UX, update this contract first.
- If implementation requires a different app-side route structure, update the contract first.
- Verification may not silently expand the scope after implementation.
