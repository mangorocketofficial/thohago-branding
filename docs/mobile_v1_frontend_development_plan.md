# Thohago Mobile_V1 Frontend Development Plan

> Status: Draft  
> Date: 2026-04-08  
> Scope: Mobile web frontend only  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)

---

## 1. Objective

The goal of `Mobile_V1` is to complete the customer-facing mobile web flow from first visit to interview completion.

The target user journey is:

1. Service website landing
2. User onboarding
3. Session open
4. Photo and video upload
5. Interview completion

This version does **not** include:

- content generation result delivery
- regeneration UX
- publish/download package UX
- operator tooling
- advanced billing analytics

The purpose of this phase is to finish the mobile intake frontend so a paying customer can enter the service, start a job, upload media, and complete the guided interview on a phone.

---

## 2. Product Principles For Mobile_V1

### 2.1 Single mobile-first experience

The product is a mobile web app with optional PWA installation. The user should be able to complete the full intake flow on a phone without needing desktop access.

### 2.2 Chat-style workflow, not free chat

The interface should look like a conversation thread, but it must remain workflow-driven.

- Free text is allowed only for interview answers.
- Primary actions are button/card-based.
- The system always controls the next step.

### 2.3 Korean-only UI

All customer-facing UI text must be written in Korean.

This includes:

- page titles
- buttons
- status messages
- upload instructions
- interview system prompts
- empty states
- errors where practical

### 2.4 One main thread per user

The user should not manage multiple chat rooms like ChatGPT. Instead:

- one main workspace exists per user
- new work starts inside that workspace as a new session block

For Mobile_V1, a simplified single active session model is acceptable.

---

## 3. Frontend Scope

## 3.1 In Scope

- Marketing/entry landing page
- Google sign-in entry point
- onboarding gate after sign-in
- payment/subscription gate UI shell
- authenticated customer workspace shell
- create/open session flow
- mobile media upload UI
- interview UI with text + voice entry
- SSE/polling-based progress updates where needed
- PWA install readiness basics

## 3.2 Out of Scope

- generated content review pages
- download package pages
- regeneration action rows
- multi-session browsing UX beyond the active session shell
- admin dashboard
- complex offline mode

---

## 4. Information Architecture

Mobile_V1 should use the following top-level frontend surfaces.

### 4.1 Public Pages

- `/`
  - landing page
  - product value proposition
  - pricing summary
  - CTA to sign in

- `/pricing`
  - simple pricing explanation
  - usage-based plan summary
  - purchase CTA

### 4.2 Authenticated App Pages

- `/app`
  - main customer workspace shell
  - shows current active session or empty state

- `/app/onboarding`
  - onboarding checklist after sign-in
  - profile completion
  - payment status gate

- `/app/session/:sessionId`
  - active intake thread
  - upload cards
  - interview cards

### 4.3 System/Utility

- install prompt banner/sheet
- error state page
- loading state shell

---

## 5. Core UX Flow

## 5.1 Landing To Sign-In

The user opens the service website and sees:

- what the service does
- what the user needs to prepare
- how the workflow works
- how payment works

Primary CTA:

- `구글로 시작하기`

## 5.2 Onboarding

After sign-in, the user enters onboarding.

Required onboarding tasks:

- confirm account identity
- understand service workflow
- confirm payment/subscription access
- accept the session-based workflow

Onboarding completion CTA:

- `새 작업 시작`

## 5.3 Session Open

When the user opens a new session, the app creates a new session block in the main workspace.

The first system messages should:

- confirm that the new session started
- explain the next action
- ask for media upload first

## 5.4 Media Upload

The upload experience must be mobile-first.

Required support:

- multiple photo upload
- video upload
- visible upload limits
- upload progress state
- uploaded file list/grid
- remove/retry actions

The user should be guided by chat-style system cards rather than a raw form screen.

## 5.5 Interview

After media upload is complete, the system opens the interview flow.

Required support:

- current question card
- prior conversation history
- text answer composer
- voice recording button
- answer confirmation state
- progress state for Turn 1 / Turn 2 / Turn 3

The interview must feel like a guided chat, not a wizard form.

---

## 6. Technical Direction

## 6.1 Recommended Stack

The current codebase already supports a lightweight mobile web architecture:

- FastAPI
- Jinja2 templates
- static CSS
- vanilla JavaScript
- SSE
- PWA manifest + service worker

For Mobile_V1, this stack should be kept.

### Why this is the right stack

- lighter than introducing a SPA frontend
- faster to ship
- already aligned with the current repository
- sufficient for landing, onboarding, upload, and interview
- simpler deployment and debugging

## 6.2 Frontend Rendering Model

Use server-rendered HTML for:

- landing
- onboarding
- main workspace shell
- interview thread shell

Use JavaScript only where interactivity is necessary:

- recording audio
- upload progress
- SSE event handling
- small chat state transitions

## 6.3 PWA Baseline

Mobile_V1 should keep basic PWA capability:

- manifest
- service worker registration
- install-ready icons and metadata
- standalone display mode

PWA is a convenience layer, not a separate application.

---

## 7. Phase Breakdown

## Phase 1. Frontend Foundation

### Goal

Stabilize the mobile web shell and define Korean UI rules for all customer pages.

### Tasks

- confirm page layout baseline for mobile
- standardize typography, spacing, and card system
- define Korean UI terminology rules
- create reusable layout primitives:
  - page shell
  - chat card
  - action row
  - system notice
  - empty state

### Deliverables

- consistent mobile CSS system
- Korean UI copy baseline
- reusable template partials

### Exit Criteria

- all new customer-facing pages can be composed from shared mobile primitives

---

## Phase 2. Service Website

### Goal

Ship the public entry experience.

### Tasks

- build landing page
- build pricing page
- add product explanation sections
- add CTA buttons for sign-in
- ensure mobile-first layout quality

### Deliverables

- `/`
- `/pricing`

### Exit Criteria

- a user can understand the service and move into sign-in from a phone

---

## Phase 3. Auth And Onboarding

### Goal

Move from anonymous visitor to ready-to-start customer.

### Tasks

- add Google sign-in entry flow
- build onboarding page shell
- add payment/subscription gate UI
- add “ready to start” state
- redirect authenticated users into the app shell

### Deliverables

- `/app/onboarding`
- signed-in workspace redirect behavior

### Exit Criteria

- a signed-in, paid user can reach the start-session state

---

## Phase 4. Workspace And Session Open

### Goal

Create the main app experience and session start flow.

### Tasks

- build `/app` workspace shell
- add empty-state session view
- add new session creation CTA
- render active session as a chat-style thread
- add session header and session stage state

### Deliverables

- workspace shell
- session open card/message flow

### Exit Criteria

- a signed-in user can start a session and land in an active thread

---

## Phase 5. Media Upload Experience

### Goal

Complete mobile media intake.

### Tasks

- build upload cards inside the session thread
- support photo upload
- support video upload
- show upload limits clearly
- render uploaded media list/grid
- support remove/retry
- show preflight pending/complete states

### Deliverables

- upload thread UI
- upload state messaging
- uploaded media visual list

### Exit Criteria

- a user can upload the required media from mobile and proceed to the interview stage

---

## Phase 6. Interview Experience

### Goal

Complete the mobile interview UI.

### Tasks

- render conversation thread
- show current question card
- support text answer entry
- support voice recording UI
- show transcription/confirmation state
- show turn progress
- show clear next-step messaging after each answer

### Deliverables

- interview thread UI
- voice recording controls
- answer confirmation UI

### Exit Criteria

- a user can complete Turn 1, Turn 2, and Turn 3 from mobile

---

## Phase 7. Mobile Polish And QA

### Goal

Make the full Mobile_V1 journey production-readable.

### Tasks

- fix Korean copy consistency
- improve install prompt placement
- improve loading/error states
- test on iPhone Safari and Android Chrome
- verify touch targets, file inputs, and microphone permissions

### Deliverables

- Mobile_V1 UI polish
- compatibility checklist

### Exit Criteria

- the full flow is stable on real mobile browsers

---

## 8. UI Requirements

All UI must be in Korean.

### Required Korean UI surfaces

- landing hero copy
- onboarding explanations
- button labels
- upload instructions
- interview guidance
- progress/status labels
- error notices
- recording hints

### UX style requirements

- large touch-friendly buttons
- high-contrast action hierarchy
- minimal typing where possible
- upload-first and card-driven interaction
- one clear next action at all times

---

## 9. Backend Dependencies Required For Frontend Completion

Even though this plan is frontend-first, the following backend capabilities must exist or be stubbed:

- Google auth/session check
- payment/subscription state endpoint
- create session endpoint
- upload endpoint
- upload list/delete endpoint
- interview question fetch/state endpoint
- audio record/transcription endpoint
- session stage/status endpoint
- SSE endpoint for interview and processing events

If some backend features are not ready yet, Mobile_V1 frontend may use temporary stubs, but the page structure must still match the final workflow.

---

## 10. Success Criteria

Mobile_V1 frontend is complete when:

- a user can visit the public service website from mobile
- a user can sign in with Google
- a user can pass onboarding/payment gate UI
- a user can open a new session
- a user can upload photos and videos from a phone
- a user can complete the 3-turn interview
- the entire UI is presented in Korean
- the experience works in a chat-style mobile flow

---

## 11. Recommended Next Document

After this plan is accepted, the next artifact should be:

- `mobile_v1_phase1_contract.md`

That contract should define the first implementation slice for:

- landing page
- onboarding shell
- workspace shell

