# Web Phase 9 Contract

> Status: Active  
> Date: 2026-04-02  
> Reference: [web_phase8_contract.md](./web_phase8_contract.md)

## Goal

Keep the upload step as a simple form, but convert every customer-facing step after upload into a chat-style interface.

This phase changes presentation, not orchestration:

- upload remains a form-first media step
- interview becomes a bot-led conversation UI
- waiting, preview, and complete screens reuse the same conversation shell
- customer-facing copy is normalized to Korean

## Business Outcome

After media upload, the customer should feel like they are staying inside one guided conversation instead of moving through unrelated utility pages.

## In Scope

1. Customer conversation UI shell
   - add a reusable chat-style layout for customer pages after upload
   - render bot and customer messages as conversation bubbles

2. Interview page conversion
   - show current interview flow as a guided conversation
   - keep voice recording, transcript confirmation, retry, and next-step controls working
   - keep turn titles visible as part of the conversation flow

3. Waiting page conversion
   - replace the plain status page with a conversation-style waiting state
   - keep timed refresh and SSE preview redirect behavior

4. Preview page conversion
   - present preview-ready guidance, assets, and approval actions inside the same chat shell

5. Complete page conversion
   - present approval completion inside the same chat shell

6. Customer-facing Korean copy polish
   - remove remaining English from customer upload/interview/waiting/preview/complete pages that are in scope for this phase

## Out of Scope

- upload step redesign beyond keeping the current form-first flow
- admin UI changes
- session stage transitions or backend orchestration changes
- sync API protocol changes
- single-page-app conversion
- Redis or SSE backend changes

## Required Inputs

- existing customer session flow from `collecting_media` through `approved`
- current session message history stored in SQLite
- existing preview artifacts and approval actions

## Required Outputs

For this phase, the implementation must produce:

- a chat-style customer UI for interview, waiting, preview, and complete routes
- Korean customer-facing copy for those routes
- preserved voice/STT/SSE/approval behavior

## Acceptance Criteria

### A. Interview Conversation UI

- Interview page renders as a conversation thread instead of a plain staged form.
- Existing bot questions and confirmed customer answers appear in a readable chat flow.
- Pending transcript confirmation still supports retry, edit, and confirm actions.

### B. Waiting Conversation UI

- Waiting page renders in the same conversation shell.
- Existing auto-refresh and `preview_ready` SSE redirect still work.

### C. Preview Conversation UI

- Preview page renders in the same conversation shell.
- Approval and revision actions remain available and functional.
- Preview assets still render correctly.

### D. Complete Conversation UI

- Complete page renders in the same conversation shell.
- Approved state is clear without relying on English copy.

### E. Regression Safety

- Upload step still works as the current form-first flow.
- Interview progression, sync preview upload, approval, and waiting redirect do not regress.

## Operator Flows Required

1. Create a customer session
2. Upload media and move into interview
3. Complete interview and reach waiting
4. Upload preview and open preview page
5. Approve preview and open complete page

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Existing FastAPI + Jinja2 web stack
- Existing deployed GCP MVP server may be updated after local verification

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. automated test command(s)
3. pass/fail status for interview, waiting, preview, and complete UI acceptance groups
4. evidence that upload flow still works
5. evidence that deployed customer pages reflect the new conversation UI

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- customer interview is still presented as a plain staged utility page
- waiting, preview, and complete pages still use the old page style
- customer-facing English remains on the in-scope pages
- retry / confirm / approval behavior regresses
