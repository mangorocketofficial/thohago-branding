# Mobile_V1 Phase 6 Contract

> Status: Active  
> Date: 2026-04-08  
> Workflow: [phase_workflow.md](./phase_workflow.md)  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)  
> Reference: [mobile_v1_phase5_verification.md](./mobile_v1_phase5_verification.md)

---

## 1. Goal

Deliver the `Mobile_V1` app-shell UI rework so the authenticated customer experience behaves like a single chat application instead of a sequence of separate utility pages.

This phase must:

- remove the standalone onboarding page from the normal customer flow
- send signed-in users directly into `/app`
- rebuild `/app` and `/app/session/:sessionId` into a unified chat-shell UI
- add a left session sidebar on desktop and a mobile drawer-equivalent session navigation
- preserve the existing session workflow states inside the new shell

The business outcome is that the product feels like one continuous chat workspace rather than a stack of unrelated pages.

---

## 2. Business Outcome

At the end of Phase 6:

- signing in lands the customer directly in the main app shell
- the onboarding page is no longer required for normal usage
- the app visually behaves like a chat application with persistent session navigation
- the customer can browse existing sessions from the left sidebar and reopen them without leaving the chat-shell structure
- existing upload, interview, preview, approval, and delivery flows still work inside the new UI shell

---

## 3. In Scope

### 3.1 Auth Entry Flow Simplification

- remove onboarding from the normal signed-in path
- change the sign-in stub to land directly in `/app`
- allow `/app` access without the onboarding gate
- redirect `/app/onboarding` back into `/app` for compatibility

### 3.2 Unified Chat Shell

- rebuild `/app` into a real chat-style workspace shell
- rebuild `/app/session/:sessionId` to share the same shell structure
- keep the session content as the main conversation pane
- keep customer-facing UI in Korean

### 3.3 Left Session Sidebar

- show recent sessions in a persistent left sidebar on desktop/tablet widths
- allow opening a session directly from the sidebar
- include a “new session” action inside the sidebar
- visually distinguish the active session

### 3.4 Mobile Session Navigation

- replace the desktop sidebar with a mobile-friendly drawer/panel pattern on narrow widths
- allow opening and closing the session list from the top bar
- keep the chat pane usable without the sidebar always occupying width

### 3.5 Workspace Main Pane

- make `/app` itself look like a chat room rather than a dashboard card list
- show an empty-state or welcome conversation when no session is selected
- show guidance for selecting an existing session or starting a new one

### 3.6 Compatibility With Existing Workflow States

- preserve current app session state rendering for:
  - upload
  - interview
  - waiting
  - preview
  - approved delivery
- keep existing routes functional inside the new shell

---

## 4. Out Of Scope

- new interview logic
- new generation logic
- download flow redesign beyond shell integration
- bounded regeneration UX
- real Google OAuth
- real billing integration
- admin UI redesign
- PWA feature expansion beyond what already exists

---

## 5. Required Inputs

The implementation may assume:

- the existing FastAPI + Jinja2 + static CSS + JS stack remains in use
- Phase 5 mobile app session flow is already verified
- existing session data and stage labels remain available
- the current auth model remains a stub cookie-based flow

If route compatibility shims are needed for `/app/onboarding`, they must be explicit and documented.

---

## 6. Required Outputs

Phase 6 must produce:

1. App-shell outputs
   - direct sign-in into `/app`
   - unified chat-shell layout
   - desktop sidebar and mobile drawer navigation

2. Routing outputs
   - `/app` remains the main authenticated shell
   - `/app/session/:sessionId` uses the same shell structure
   - `/app/onboarding` is no longer a normal destination

3. Verification outputs
   - Phase 6 verification document
   - command evidence
   - route/UI evidence

---

## 7. Acceptance Criteria

### A. Sign-In Flow

- sign-in no longer lands on a standalone onboarding page
- signed-in customers land directly in `/app`
- `/app` is accessible without the old onboarding gate

### B. Unified Shell

- `/app` renders a real chat-style app shell
- `/app/session/:sessionId` renders inside the same shell structure
- the shell looks like one application rather than separate cards/pages

### C. Sidebar Navigation

- desktop widths show a left session sidebar
- the sidebar includes recent sessions and a new-session action
- the active session is visually identifiable

### D. Mobile Navigation

- narrow widths expose the session list through a toggleable drawer/panel
- the chat pane remains usable on mobile widths

### E. Workflow Compatibility

- upload, interview, preview, and approved delivery states still render within the new shell
- existing session routes still work after the UI change

### F. Language And UX

- customer-facing UI introduced in this phase remains Korean
- the shell keeps a clear next action for empty state and active sessions

---

## 8. Required Commands And Operator Flows

Phase 6 must support and document these commands or equivalent commands:

1. Install dependencies
2. Run local web app
3. Run Phase 6 tests
4. Run key mobile regression checks
5. Operator verification flow:
   - sign in through the stub path
   - confirm direct landing into `/app`
   - start a new session from the sidebar
   - open an existing session from the sidebar
   - confirm the shell remains consistent across session states
   - verify mobile-width drawer behavior through local browser checks or responsive verification

Exact command strings will be captured in the verification document after implementation.

---

## 9. Dependencies, Credentials, And Environment Assumptions

- current repository branch: `mobile-web-pivot`
- FastAPI application remains the delivery surface
- Jinja2 template rendering remains acceptable for the app-shell redesign
- existing tests may be updated where the old onboarding behavior is intentionally removed

---

## 10. Completion Evidence Required

Phase 6 is only verified when the verification document includes:

1. Environment evidence
   - OS
   - Python/runtime version
   - local startup method

2. Command evidence
   - exact app startup command
   - exact Phase 6 test command
   - exact regression commands

3. UI/route evidence
   - direct sign-in landing result
   - `/app` shell evidence
   - `/app/session/:sessionId` shell evidence
   - sidebar/drawer evidence

4. Flow evidence
   - new session creation from the shell
   - existing session reopening from the shell

---

## 11. Explicit Non-Completion Cases

Phase 6 is **not** complete if:

- sign-in still lands on the old onboarding page
- `/app` and `/app/session/:sessionId` still look like separate page families
- no persistent session navigation exists
- the sidebar works only on desktop and has no mobile equivalent
- existing workflow states break inside the new shell

---

## 12. Change Control

- If implementation expands into new workflow logic, update this contract first.
- If implementation changes app-side route structure beyond the shell redesign, update the contract first.
- Verification may not silently expand the scope after implementation.
