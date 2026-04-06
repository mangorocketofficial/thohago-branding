# Web Phase 9 Chat Composer Simplification Contract

> Status: Active  
> Date: 2026-04-02  
> Reference: [web_phase9_contract.md](./web_phase9_contract.md)

## Goal

Simplify the interview input area into one compact chat composer while keeping voice input available through an icon-based control.

## In Scope

1. Remove the separate voice answer card section from the interview page
2. Remove the current titled edit card layout from the interview page
3. Replace both with one compact chat-style composer
4. Keep text submission available from the same composer
5. Keep voice recording available through a microphone icon button
6. Show a clear recording-state icon or badge after the microphone button is pressed
7. Keep confirm-state editing and `다음 인터뷰하기` working
8. Update tests and live deployment for the new interview UI

## Out of Scope

- backend interview stages
- record/transcription backend endpoints
- waiting/preview/complete page redesign
- admin UI changes

## Acceptance Criteria

### A. Interview Composer

- interview page no longer shows the old separate `음성 답변 / 말로 답변하기` card
- interview page no longer shows the old titled `답변 수정 / 직접 입력하기` card block
- interview page shows one compact chat-style composer instead

### B. Voice Input

- the composer shows a microphone icon button
- pressing the microphone button switches the UI into a visible recording state
- the user can still complete recording from the simplified composer flow

### C. Confirm Flow

- when a pending answer exists, the same simple composer allows editing the answer
- `다음 인터뷰하기` continues to work

### D. Regression Safety

- text interview progression still works
- backend voice/STT routes continue to work
- live server reflects the new simplified composer

## Completion Evidence Required

The verification record must include:

1. targeted automated test evidence
2. full regression result
3. live server fetch evidence for the simplified composer and voice icon state
