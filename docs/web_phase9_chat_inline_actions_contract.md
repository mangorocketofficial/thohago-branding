# Web Phase 9 Chat Inline Actions Patch Contract

> Status: Active  
> Date: 2026-04-02  
> Reference: [web_phase9_chat_action_row_contract.md](./web_phase9_chat_action_row_contract.md)

## Goal

Move the interview composer microphone and edit actions inside the chat input field.

## In Scope

1. Render the microphone action inside the chat input field
2. Render the confirm-state edit icon inside the chat input field
3. Keep recording-state and edit behavior working
4. Update tests and live deployment for the inline action layout

## Out of Scope

- interview stage logic
- waiting/preview/complete pages
- admin UI
- STT backend changes

## Acceptance Criteria

### A. Inline Controls

- microphone control is rendered inside the chat input field
- confirm-state edit icon is rendered inside the chat input field

### B. Regression Safety

- text submission still works
- recording flow still works
- live server reflects the inline action layout

## Completion Evidence Required

The verification record must include:

1. targeted automated test evidence
2. live fetch evidence for inline mic/edit controls
3. pass/fail status for inline control placement
