# Web Phase 9 Chat Action Row Patch Contract

> Status: Active  
> Date: 2026-04-02  
> Reference: [web_phase9_chat_composer_contract.md](./web_phase9_chat_composer_contract.md)

## Goal

Adjust the simplified interview composer so its action controls sit below the chat textarea, and use an icon-style edit button in confirm state.

## In Scope

1. Place interview composer action controls below the textarea
2. Keep microphone control in the lower action row
3. Replace confirm-state text edit button with an edit icon button
4. Update tests and live deployment for the adjusted action row

## Out of Scope

- interview stage logic
- waiting/preview/complete pages
- admin UI
- STT backend changes

## Acceptance Criteria

### A. Action Row Placement

- microphone control is rendered below the textarea
- send/edit action is rendered in the same lower action row

### B. Edit Icon

- confirm state no longer renders the text button `답변 수정하기`
- confirm state renders an edit icon button instead

### C. Regression Safety

- simplified composer still renders
- text submission still works
- live server reflects the adjusted layout

## Completion Evidence Required

The verification record must include:

1. targeted automated test evidence
2. live fetch evidence for the lower action row
3. pass/fail status for action-row placement and edit icon acceptance
