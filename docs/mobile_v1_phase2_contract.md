# Mobile_V1 Phase 2 Contract

> Status: Active  
> Date: 2026-04-08  
> Workflow: [phase_workflow.md](./phase_workflow.md)  
> Reference: [mobile_v1_frontend_development_plan.md](./mobile_v1_frontend_development_plan.md)  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)  
> Depends On: [mobile_v1_phase1_contract.md](./mobile_v1_phase1_contract.md), [mobile_v1_phase1_verification.md](./mobile_v1_phase1_verification.md)

---

## 1. Goal

Deliver the `Mobile_V1` media upload flow inside the new authenticated app shell.

This phase must turn the Phase 1 session shell into a real mobile upload experience:

- create a real app-side session
- allow photo and video upload from the session page
- persist uploaded media in the existing runtime
- display uploaded items inside the mobile app session thread
- support delete/retry behavior for uploaded items

The business outcome is that a signed-in user can start a session from the mobile workspace and complete the media intake part of the job without falling back to the old token-based customer portal.

---

## 2. Business Outcome

At the end of Phase 2:

- the authenticated workspace can create a real session
- the session page can accept photo and video uploads
- the uploaded files persist to disk and DB
- the session page shows the uploaded items in a Korean mobile UI
- the customer can remove uploaded items and continue within the same app shell

This phase does **not** yet need to complete the interview flow.

---

## 3. In Scope

### 3.1 App-Side Session Creation

- replace the Phase 1 placeholder session open path with a real persisted session
- create app-side sessions using the existing SQLite/session artifact runtime
- keep app-side session routing under `/app/session/:sessionId`

### 3.2 Mobile Upload UI

- add a real upload form/card inside the app session page
- support multiple photo upload
- support video upload
- show upload constraints in Korean
- show uploaded item count and list

### 3.3 Uploaded Media List

- render uploaded media records inside the app session page
- show filename, media type, and file size when available
- show delete action per uploaded item

### 3.4 Delete / Retry Behavior

- allow deleting uploaded media from the app session page
- keep the user inside the app session flow after delete
- show explicit error feedback when upload validation fails

### 3.5 Workspace Visibility

- show app-created sessions from the authenticated workspace
- allow opening an existing app session from the workspace

### 3.6 Korean UI Requirement

- all customer-facing Phase 2 UI must be Korean
- upload labels, limits, buttons, and status messages must be Korean

---

## 4. Out Of Scope

- interview execution in the new app shell
- interview question rendering inside `/app/session/:sessionId`
- voice recording flow in the new app shell
- upload finalization into turn 1 interview
- generation, regeneration, preview, or download package flows
- real Google OAuth
- real payment integration
- multi-user ownership enforcement beyond the current Phase 1 auth stub

Out-of-scope features may be referenced as “next step” messaging, but they must not be presented as already functional in the app shell.

---

## 5. Required Inputs

The implementation may assume:

- the existing FastAPI + Jinja2 + static CSS + JS stack remains in use
- existing SQLite schema for sessions/media/messages remains available
- existing upload runtime may be reused where compatible
- the current authenticated user model is still a Phase 1 stub

If a placeholder shop binding is needed internally for app-side session persistence, it must be explicit and documented.

---

## 6. Required Outputs

Phase 2 must produce:

1. App shell outputs
   - real session creation from the workspace
   - real app session page with upload capability

2. Persistence outputs
   - session DB row
   - media file DB rows
   - uploaded files written under the artifact root

3. UI outputs
   - uploaded file list
   - delete action
   - Korean upload status and validation states

4. Verification outputs
   - Phase 2 verification document
   - command evidence
   - route-level evidence
   - persistence evidence

---

## 7. Acceptance Criteria

### A. Session Creation

- the workspace can create a real app-side session
- the session route uses a persisted session identifier
- the session page can be reopened after creation

### B. Upload Functionality

- the app session page accepts photo uploads
- the app session page accepts video uploads
- upload constraints are enforced
- validation failures are shown clearly

### C. Persistence

- uploaded media is written to disk
- uploaded media rows are written to `media_files`
- related session messages are written to `session_messages`

### D. Mobile UX

- uploaded items are visible on the session page
- uploaded items can be deleted from the session page
- the app workspace can show the created session entry
- customer-facing upload UI is Korean

### E. Implementation Discipline

- the user is not redirected into the legacy `/s/<customer_token>` upload page for normal app-side upload flow
- upload flow remains within `/app` and `/app/session/:sessionId`
- interview is not falsely shown as complete in this phase

---

## 8. Required Commands And Operator Flows

Phase 2 must support and document these commands or equivalent commands:

1. Install dependencies
2. Run local web app
3. Run Phase 2 tests
4. Operator verification flow:
   - open landing page
   - sign in through the stub path
   - complete onboarding
   - create a new session
   - upload at least one photo
   - upload at least one video when within limits
   - confirm uploaded files appear
   - delete one uploaded file
   - confirm the session still renders correctly

Exact command strings will be captured in the verification document after implementation.

---

## 9. Dependencies, Credentials, And Environment Assumptions

- current repository branch: `mobile-web-pivot`
- FastAPI application remains the delivery surface
- Jinja2 template rendering remains acceptable for Mobile_V1
- upload tests may use temporary local fixture files
- real auth and billing providers are not required in this phase

---

## 10. Completion Evidence Required

Phase 2 is only verified when the verification document includes:

1. Environment evidence
   - OS
   - Python/runtime version
   - local startup method

2. Command evidence
   - exact app startup command
   - exact Phase 2 test command

3. Route evidence
   - workspace route
   - app session route
   - upload route behavior

4. Persistence evidence
   - session DB persistence
   - media file DB persistence
   - uploaded file path evidence

5. Flow evidence
   - create session
   - upload media
   - delete media
   - remain in app shell

---

## 11. Explicit Non-Completion Cases

Phase 2 is **not** complete if:

- app-side session creation is still only a placeholder redirect
- upload works only through the legacy token-based portal
- media files are not persisted
- the app session page does not show uploaded media
- delete is missing or broken
- customer-facing upload UI is still mixed-language or mostly English

---

## 12. Change Control

- If implementation requires a new app-specific session model, update the contract first.
- If interview flow begins inside the new app shell, move that work into Phase 3 or update the contract first.
- Verification may not silently expand the scope after implementation.

