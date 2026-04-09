# Mobile_V1 Phase 3 Contract

> Status: Active  
> Date: 2026-04-08  
> Workflow: [phase_workflow.md](./phase_workflow.md)  
> Reference: [mobile_v1_frontend_development_plan.md](./mobile_v1_frontend_development_plan.md)  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)  
> Reference: [web_phase3_contract.md](./web_phase3_contract.md)  
> Depends On: [mobile_v1_phase2_contract.md](./mobile_v1_phase2_contract.md), [mobile_v1_phase2_verification.md](./mobile_v1_phase2_verification.md)

---

## 1. Goal

Deliver the app-side upload finalization and interview flow inside the authenticated `Mobile_V1` app shell.

This phase must turn the Phase 2 upload session into a complete intake flow:

- finalize uploads from the app session surface
- create the media preflight and Turn 1 question using the existing pipeline
- render the 3-turn interview inside the app-side session flow
- accept text answers with confirm/retry behavior
- persist transcript, planner, and intake artifacts
- end the session in `awaiting_production` without sending the customer into the legacy token-based portal

The business outcome is that a signed-in user can complete the full mobile intake journey from `/app` and `/app/session/:sessionId` after Phase 2 media upload is done.

---

## 2. Business Outcome

At the end of Phase 3:

- an app-side upload session can be finalized into interview mode
- the customer can complete Turn 1, Turn 2, and Turn 3 inside the authenticated app shell
- interview artifacts persist to the existing runtime and artifact directories
- the session reaches a production-ready waiting state that is visible from the app shell and workspace
- the customer-facing intake flow remains Korean and mobile-first

This phase intentionally targets a text-first interview flow in the app shell. App-side voice recording and SSE-driven transcription remain a later phase.

---

## 3. In Scope

### 3.1 Upload Finalization In The App Shell

- add an explicit “upload complete / start interview” action to the app-side session flow
- require at least one uploaded photo before finalization
- reuse the current upload finalization pipeline where compatible
- create `media_preflight`, Turn 1 planner artifacts, and Turn 1 question
- move the session from `collecting_media` to `awaiting_turn1_answer`

### 3.2 App-Side Interview Routing And Rendering

- render interview state within the authenticated app-side session surface
- keep normal customer flow under `/app/session/:sessionId` and app-side helper routes beneath that prefix
- show the current question, turn progress, and prior conversation messages
- render a pending-answer confirmation state for `confirming_turn*`
- show a production-waiting state once interview is complete

### 3.3 Text Answer Submission

- support text answer submission for Turn 1, Turn 2, and Turn 3
- store submitted text as `pending_answer`
- allow replacing the pending answer while the session remains in `confirming_turn*`

### 3.4 Retry And Confirm Behavior

- allow retry from any `confirming_turn*` state
- retry clears `pending_answer` and returns the session to `awaiting_turnN_answer`
- confirm writes transcript artifacts for the current turn
- Turn 1 confirm generates Turn 2 planner/question artifacts
- Turn 2 confirm generates Turn 3 planner/question artifacts
- Turn 3 confirm exports the intake bundle and marks interview completion

### 3.5 Workspace Continuity

- allow the app workspace to reopen a session after interview progress
- show updated stage/status text for interview-ready and production-waiting sessions
- keep the normal authenticated customer experience in the app shell rather than redirecting into legacy `/s/<customer_token>` screens

### 3.6 Korean UI Requirement

- all customer-facing Phase 3 UI must be Korean
- finalize actions, interview labels, confirm/retry controls, waiting messages, and visible validation errors must be Korean

---

## 4. Out Of Scope

- voice recording flow in the new app shell
- app-side SSE event stream or live transcription UI
- app-side microphone permission handling
- generated content creation, preview, regeneration, or download flows
- real Google OAuth
- real payment integration
- usage ledger or billing deduction
- multi-user ownership enforcement beyond the current auth stub
- admin/operator tooling changes
- removal of the legacy `/s/<customer_token>` interview flow

Out-of-scope legacy routes may remain for regression safety, but they must not be the normal authenticated customer path for the new Phase 3 app flow.

---

## 5. Required Inputs

The implementation may assume:

- the existing FastAPI + Jinja2 + static CSS + JS stack remains in use
- the existing SQLite session/media/message/artifact runtime remains available
- Phase 2 app-side session creation and upload flow already works
- the current upload finalization and interview services may be reused where compatible
- the current authenticated user model remains a Phase 1 stub
- verification may use the current local/default interview engine path rather than requiring live provider credentials

If adapter helpers are required to bind app-side session routes to the existing interview services, that binding must be explicit and documented.

---

## 6. Required Outputs

Phase 3 must produce:

1. App shell outputs
   - upload-finalization action in the app session flow
   - app-side interview thread UI
   - app-side production-waiting state after Turn 3 completion

2. Routing outputs
   - app-side finalize route
   - app-side interview submit/retry/confirm routes under `/app/session/:sessionId`
   - no normal authenticated app-side redirects into legacy `/s/<customer_token>` interview or waiting pages

3. Persistence outputs
   - `generated/media_preflight.json`
   - `planners/turn1_question.txt`
   - transcript artifacts for turns 1, 2, and 3
   - planner artifacts for turns 2 and 3
   - `generated/intake_bundle.json`
   - updated session metadata, session messages, and session artifact records

4. Verification outputs
   - Phase 3 verification document
   - command evidence
   - route-level evidence
   - artifact path evidence

---

## 7. Acceptance Criteria

### A. Upload Finalization

- the app session page exposes a real finalize/start-interview action
- finalization requires at least one uploaded photo
- finalization writes preflight and Turn 1 question artifacts
- finalization changes the session stage to `awaiting_turn1_answer`
- the customer remains in the app-side route surface after finalization

### B. Interview Rendering

- the app-side session route renders the current question for `awaiting_turn*`
- the app-side session route renders pending-answer confirmation UI for `confirming_turn*`
- prior interview conversation messages are visible in the app-side session thread
- the UI shows clear turn context in Korean

### C. Text Submission And Retry

- app-side text submission stores `pending_answer`
- submission changes the session stage to `confirming_turnN`
- submitting replacement text while already in `confirming_turnN` overwrites the pending answer
- retry clears `pending_answer`
- retry returns the session to `awaiting_turnN_answer`

### D. Turn Progression And Persistence

- Turn 1 confirm writes transcript artifacts and generates Turn 2 planner/question artifacts
- Turn 1 confirm changes the session stage to `awaiting_turn2_answer`
- Turn 2 confirm writes transcript artifacts and generates Turn 3 planner/question artifacts
- Turn 2 confirm changes the session stage to `awaiting_turn3_answer`
- Turn 3 confirm writes transcript artifacts and exports `generated/intake_bundle.json`
- Turn 3 confirm changes the session stage to `awaiting_production`
- `interview_completed_at` is recorded when Turn 3 is confirmed
- `session_messages` and chat-log artifacts continue to record the conversation progression

### E. App Shell Continuity

- the normal authenticated customer flow remains under `/app`
- the workspace can reopen a session after interview progress or completion
- the app-side flow does not redirect the customer into `/s/<customer_token>/interview` or `/s/<customer_token>/waiting` for normal usage

### F. Mobile UX And Language

- finalize, interview, and waiting UI introduced in this phase are Korean
- the app-side interview UI remains usable on mobile widths
- the post-interview waiting state clearly says that generation is the next phase rather than falsely implying completion

---

## 8. Required Commands And Operator Flows

Phase 3 must support and document these commands or equivalent commands:

1. Install dependencies
2. Run local web app
3. Run Phase 3 tests
4. Run Phase 1 and Phase 2 regression checks
5. Operator verification flow:
   - open the landing page
   - sign in through the stub path
   - complete onboarding
   - create a new session
   - upload at least one photo
   - optionally upload one video within limits
   - finalize uploads from the app session
   - submit and confirm Turn 1 text answer
   - submit and confirm Turn 2 text answer
   - submit and confirm Turn 3 text answer
   - confirm the app session shows production-waiting state
   - confirm the workspace still lists the session with updated status

Exact command strings will be captured in the verification document after implementation.

---

## 9. Dependencies, Credentials, And Environment Assumptions

- current repository branch: `mobile-web-pivot`
- FastAPI application remains the delivery surface
- Jinja2 template rendering remains acceptable for `Mobile_V1`
- existing upload/interview pipeline runtime may be reused
- heuristic or local-default interview planning is acceptable for verification
- real auth and billing providers are not required in this phase

---

## 10. Completion Evidence Required

Phase 3 is only verified when the verification document includes:

1. Environment evidence
   - OS
   - Python/runtime version
   - local startup method

2. Command evidence
   - exact app startup command
   - exact Phase 3 test command
   - exact regression commands

3. Route evidence
   - app workspace route
   - app session upload/finalize route
   - app-side interview submit/retry/confirm behavior

4. Artifact evidence
   - `generated/media_preflight.json`
   - `planners/turn1_question.txt`
   - transcript files for turns 1, 2, and 3
   - Turn 2 planner files
   - Turn 3 planner files
   - `generated/intake_bundle.json`
   - updated `session_metadata.json`

5. Flow evidence
   - the session remains in app-side routes throughout the normal authenticated flow
   - the final session stage is `awaiting_production`
   - the workspace can reopen the interview-complete session

---

## 11. Explicit Non-Completion Cases

Phase 3 is **not** complete if:

- upload finalization still works only through the legacy `/s/<customer_token>/upload/done` route
- the app-side session redirects customers into the legacy token-based interview or waiting pages
- the app shell does not render the current question and confirmation state
- pending answer, confirm, or retry behavior is missing or broken
- transcript, planner, or intake bundle artifacts are missing
- the final session stage is not `awaiting_production`
- customer-facing interview UI remains mixed-language or mostly English

---

## 12. Change Control

- If implementation expands to app-side voice recording or SSE events, update this contract first.
- If implementation requires a different app-side route structure, update the contract first.
- Verification may not silently expand the scope after implementation.
