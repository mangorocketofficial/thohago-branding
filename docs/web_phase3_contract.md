# Web Phase 3 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_migration_spec.md](./web_migration_spec.md)

## Goal

Deliver the text-first interview flow for the web migration so that a customer session can move from `awaiting_turn1_answer` to `awaiting_production`.

This phase must complete the customer intake interview orchestration:

- render the current interview turn
- accept text answers
- support confirm and retry
- write transcript artifacts on confirm
- generate Turn 2 and Turn 3 follow-up questions
- export an intake bundle after Turn 3
- route the customer to the production waiting page

## Business Outcome

After uploads are finalized, a customer must be able to complete a 3-turn interview through the web app and leave the session in a state that the local production bridge can pick up later.

## Scope Decision

This phase intentionally uses a text-first contract so it can be fully verified in the current development environment.

Out of the original broader Web Phase 3 plan, the following are deferred:

- audio recording UI
- STT provider integration
- SSE-based live transcription

These deferred items require provider-dependent runtime behavior and will be handled in a later contract-driven phase.

## In Scope

1. Interview page implementation
   - interview page renders the current question for `awaiting_turn*` stages
   - interview page renders pending answer confirmation UI for `confirming_turn*` stages
   - interview page renders clear turn and stage context

2. Text answer submission
   - customer can submit a text answer for Turn 1, Turn 2, and Turn 3
   - submission stores the answer as `pending_answer`
   - submission moves the stage from `awaiting_turnN_answer` to `confirming_turnN`

3. Retry flow
   - customer can discard the pending answer
   - retry clears `pending_answer`
   - retry returns the session to `awaiting_turnN_answer`

4. Confirm flow
   - confirm writes transcript artifacts for the current turn
   - confirm appends customer answer and next system question to `chat_log.jsonl`
   - confirm records relevant `session_messages`
   - Turn 1 confirm generates Turn 2 planner and question
   - Turn 2 confirm generates Turn 3 planner and question
   - Turn 3 confirm exports `generated/intake_bundle.json`
   - Turn 3 confirm changes session stage to `awaiting_production`

5. Waiting page
   - `GET /s/<customer_token>/waiting` renders a real waiting page for `awaiting_production`
   - session landing redirects to waiting page once interview is complete

## Out of Scope

- audio recording
- voice upload endpoints
- STT
- SSE
- admin-to-customer messaging
- sync download/upload endpoints
- preview rendering
- approval flow
- publishing

## Required Inputs

- a valid session already in `awaiting_turn1_answer`
- preflight already written from Web Phase 2
- Turn 1 question already written from Web Phase 2
- text answers for all 3 turns

## Required Outputs

For a successfully completed interview, the implementation must produce:

- transcript artifacts for turns 1, 2, and 3 under `transcripts/`
- planner artifacts for turns 2 and 3 under `planners/`
- `generated/intake_bundle.json`
- `session_messages` rows recording answers and questions
- `chat_log.jsonl` entries recording the same conversation progression
- updated `session_metadata.json`
- a session row whose stage is `awaiting_production`

## Acceptance Criteria

### A. Interview Page

- `GET /s/<customer_token>/interview` renders a real HTML page for `awaiting_turn1_answer`.
- The page shows the current question text.
- The page shows a text answer submission form.
- When the session is in `confirming_turnN`, the page shows the pending answer and confirm/retry actions.

### B. Text Submission

- `POST /s/<customer_token>/interview/submit` stores the submitted text as `pending_answer`.
- Submission changes the session stage to `confirming_turnN`.
- Submitting a replacement answer while already in `confirming_turnN` overwrites the pending answer.

### C. Retry

- `POST /s/<customer_token>/interview/retry` clears `pending_answer`.
- Retry returns the session to `awaiting_turnN_answer`.

### D. Turn Progression

- Turn 1 confirm writes transcript artifacts and generates Turn 2 planner artifacts.
- Turn 1 confirm changes the session stage to `awaiting_turn2_answer`.
- Turn 2 confirm writes transcript artifacts and generates Turn 3 planner artifacts.
- Turn 2 confirm changes the session stage to `awaiting_turn3_answer`.
- Turn 3 confirm writes transcript artifacts and exports `generated/intake_bundle.json`.
- Turn 3 confirm changes the session stage to `awaiting_production`.

### E. Artifact Persistence

- `transcripts/turn1_transcript.txt` and `.json` are written.
- `transcripts/turn2_transcript.txt` and `.json` are written.
- `transcripts/turn3_transcript.txt` and `.json` are written.
- `planners/turn2_question.txt` and `turn2_planner.json` are written.
- `planners/turn3_question.txt` and `turn3_planner.json` are written.
- `generated/intake_bundle.json` is written.

### F. Waiting State

- `GET /s/<customer_token>/waiting` renders a real waiting page after Turn 3 confirm.
- The session landing route redirects to `/s/<customer_token>/waiting` for `awaiting_production`.

## Operator Flows Required

1. Create and prepare a web session through Web Phase 2 flow
2. Submit Turn 1 text answer
3. Retry once or confirm directly
4. Complete Turn 2 text answer
5. Complete Turn 3 text answer
6. Confirm that the session lands on the waiting page
7. Confirm that `intake_bundle.json` exists

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Shop registry source: checked-in JSON config
- Existing artifact root and SQLite runtime from Web Phase 2
- For verification, the heuristic engine path is acceptable
- External API-backed interview engines may be configured later, but they are not required for verification

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. automated test command(s)
3. manual verification commands or scripted flows
4. produced artifact paths for:
   - transcript files for all 3 turns
   - Turn 2 planner files
   - Turn 3 planner files
   - `generated/intake_bundle.json`
   - updated `session_metadata.json`
5. pass/fail status for each acceptance group
6. evidence that the final session stage is `awaiting_production`
7. evidence that session landing redirects to waiting page

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- text answer submission does not persist pending state
- retry does not clear pending state
- transcript artifacts are missing for any turn
- Turn 2 or Turn 3 planner artifacts are not persisted
- the final interview step does not export `intake_bundle.json`
- the final session stage is not `awaiting_production`
- the customer still lands on the interview page after Turn 3 confirm
