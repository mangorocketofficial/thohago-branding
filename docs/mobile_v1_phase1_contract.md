# Mobile_V1 Phase 1 Contract

> Status: Active  
> Date: 2026-04-08  
> Workflow: [phase_workflow.md](./phase_workflow.md)  
> Reference: [mobile_v1_frontend_development_plan.md](./mobile_v1_frontend_development_plan.md)  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)

---

## 1. Goal

Deliver the first customer-facing frontend slice for `Mobile_V1`:

- public service website
- authenticated onboarding shell
- authenticated workspace shell
- new session entry shell

This phase defines the app shape before media upload and interview are implemented.

The business outcome is that a customer can open the mobile website, understand the service, move through the authenticated onboarding gate, and land in an app workspace that clearly presents the next step: start a new job.

---

## 2. Business Outcome

At the end of Phase 1:

- the product has a real mobile-first public entry point
- the user can move from public website to app shell
- the app has a Korean-language onboarding gate
- the app has a Korean-language workspace shell
- the workspace can show an empty state and a “start new session” action

This phase does **not** need to complete media upload or interview execution yet.

---

## 3. In Scope

### 3.1 Public Service Website

- build a public landing page at `/`
- build a pricing page at `/pricing`
- present product value proposition in Korean
- present the Mobile_V1 workflow in Korean
- provide a clear sign-in/start CTA

### 3.2 Authenticated Frontend Shell

- build `/app` workspace shell
- build `/app/onboarding` onboarding shell
- define routing/redirect rules between public and authenticated surfaces
- add a minimal signed-in app layout suitable for mobile

### 3.3 Onboarding Gate UI

- show onboarding checklist or gate state
- show payment/subscription gate placeholder or stub state
- present a clear completion path into the workspace
- keep all customer-facing UI in Korean

### 3.4 Workspace Empty State

- show the authenticated customer workspace with no active session
- show a clear “new session” action
- create a placeholder session entry state that can be extended in later phases
- define the visual language for the chat/workflow shell

### 3.5 PWA Baseline Readiness

- preserve or improve manifest/service worker wiring already present in the web app
- keep the app installable as a mobile web app
- ensure the shell pages render correctly in a PWA-style context

### 3.6 Frontend Design System Baseline

- establish shared mobile page shell
- establish chat/workflow card styling
- establish button hierarchy and empty state styling
- standardize Korean UI text style across the pages added in this phase

---

## 4. Out of Scope

- real Google OAuth integration
- real payment provider integration
- usage ledger or billing computation
- media upload execution
- upload progress handling
- session persistence beyond a basic placeholder path
- interview question rendering
- voice recording flow
- SSE-driven interview events
- generated content review/download pages
- regeneration controls
- admin/operator surfaces

Out of scope items may be represented by stubs or placeholders when needed for shell completion, but they must not be presented as completed production features.

---

## 5. Required Inputs

The implementation may assume:

- the existing FastAPI + Jinja2 + static CSS + JS stack remains in use
- current PWA routes (`manifest.webmanifest`, `sw.js`) remain available
- temporary placeholder auth/payment state is acceptable for Phase 1

If runtime data is needed for layout proof, fixture or stub data may be used.

---

## 6. Required Outputs

Phase 1 must produce:

1. Public frontend outputs
   - landing page
   - pricing page

2. Authenticated shell outputs
   - onboarding shell page
   - workspace shell page

3. Reusable UI outputs
   - shared mobile layout primitives
   - shared Korean copy baseline for core shell pages

4. Verification outputs
   - Phase 1 verification document
   - screenshots or equivalent page evidence captured through local verification

---

## 7. Acceptance Criteria

### A. Public Website

- `/` renders a real service landing page
- `/pricing` renders a real pricing page
- both pages are mobile-first and readable on a narrow viewport
- both pages use Korean customer-facing UI

### B. Authenticated App Shell

- `/app/onboarding` renders a real onboarding shell
- `/app` renders a real workspace shell
- the app shell visually differs from the public marketing pages
- the workspace clearly presents a next action to start a session

### C. UX Language

- all customer-facing UI introduced in this phase is Korean
- empty states, CTAs, labels, and notices are Korean
- no obvious English placeholder copy remains on the implemented shell pages

### D. Mobile-First Layout

- landing, onboarding, and workspace pages are usable on mobile widths
- primary actions are touch-friendly
- the shell supports PWA-style standalone presentation without breaking layout

### E. Implementation Discipline

- no upload/interview/generation logic is falsely implied as complete
- placeholder states are explicit where backend integration is deferred

---

## 8. Required Commands And Operator Flows

Phase 1 must support and document these commands or equivalent commands:

1. Install dependencies
   - project environment setup command

2. Run local web app
   - local app startup command

3. Run tests
   - test command for the web app

4. Operator verification flow
   - open landing page
   - open pricing page
   - reach onboarding shell
   - reach workspace shell
   - confirm the “new session” empty state

Exact command strings will be captured in the verification document after implementation.

---

## 9. Dependencies, Credentials, And Environment Assumptions

- current repository branch: `mobile-web-pivot`
- FastAPI application remains the delivery surface
- Jinja2 template rendering remains acceptable for Mobile_V1
- customer-facing pages are expected to work in mobile browsers first
- real auth and billing providers are not required in this phase

---

## 10. Completion Evidence Required

Phase 1 is only verified when the verification document includes:

1. Environment evidence
   - OS
   - Python/runtime version
   - local startup method

2. Command evidence
   - exact app startup command
   - exact test command

3. Visual/page evidence
   - landing page
   - pricing page
   - onboarding shell
   - workspace shell

4. Flow evidence
   - proof that the user can move from public site into the app shell
   - proof that the workspace exposes a clear new-session entry state

---

## 11. Explicit Non-Completion Cases

Phase 1 is **not** complete if:

- the public site is still only a placeholder redirect surface
- onboarding exists only as a missing page or raw JSON response
- the workspace does not exist as a real mobile screen
- customer-facing shell pages still contain mixed or mostly English UI
- the app shell does not show a new-session entry point

---

## 12. Change Control

- If implementation reveals that Phase 1 must include real auth wiring, update this contract first.
- If upload or interview work begins, it must be moved into Phase 2 or a revised contract.
- Verification may not silently expand the scope after implementation.

