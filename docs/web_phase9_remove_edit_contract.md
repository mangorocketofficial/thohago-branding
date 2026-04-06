# Web Phase 9 Remove Edit Button Contract

> Status: Active  
> Date: 2026-04-02  
> Reference: [web_phase9_chat_inline_actions_contract.md](./web_phase9_chat_inline_actions_contract.md)

## Goal

Remove the confirm-state edit button from the interview composer and make the confirm-state input clearly non-editable.

## In Scope

1. Remove the inline edit icon from confirm state
2. Mark confirm-state textarea as read-only
3. Update confirm-state helper copy to match the new behavior
4. Update tests and live deployment for the simplified confirm UI

## Out of Scope

- interview stage logic
- waiting/preview/complete pages
- admin UI
- recording backend changes

## Acceptance Criteria

### A. Confirm UI

- confirm state no longer renders the edit button
- confirm state textarea is rendered read-only
- confirm helper copy no longer suggests text editing

### B. Regression Safety

- initial interview state still shows the mic button inside the composer
- confirm state still shows the mic button and next-step button
- live server reflects the simplified confirm UI

## Completion Evidence Required

The verification record must include:

1. targeted automated test evidence
2. live fetch evidence for confirm-state edit removal
3. pass/fail status for confirm UI simplification
