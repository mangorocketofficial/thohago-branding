# Web Phase 2 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_migration_spec.md](./web_migration_spec.md)

## Goal

Deliver the customer upload flow for the web migration so that a customer session can move from `collecting_media` to `awaiting_turn1_answer`.

This phase must make the customer session useful beyond raw session creation:

- upload photos and optional video from the customer page
- persist uploaded files into the canonical artifact directory
- support delete-before-finalize during the upload step
- run media preflight at upload finalization time
- generate and persist the Turn 1 question
- route the customer into the interview page with the generated Turn 1 question

## Business Outcome

An operator-created customer link must support a real upload flow. After the customer uploads valid media and presses "Next", the session must produce preflight artifacts and land on the interview page with Turn 1 ready.

## In Scope

1. Upload page implementation
   - upload page shows current uploaded media list
   - page exposes upload actions and finalize action
   - page shows validation and error states relevant to this phase

2. Upload persistence
   - customer can upload photo files
   - customer can upload at most one video file
   - uploaded files are saved into `raw/`
   - uploads are indexed in `media_files`
   - uploads are recorded in `session_messages`
   - uploads are appended to `chat_log.jsonl`

3. Delete-before-finalize
   - customer can remove a previously uploaded file while stage is `collecting_media`
   - deletion removes the file from the active upload set
   - deletion is reflected in the rendered upload list

4. Upload finalization
   - finalization validates the current upload set
   - at least one photo is required
   - preflight runs against the uploaded media
   - `generated/media_preflight.json` is written
   - Turn 1 question is generated and persisted
   - session stage changes to `awaiting_turn1_answer`

5. Interview landing
   - `GET /s/<customer_token>/interview` renders a real HTML page
   - interview page shows the generated Turn 1 question for `awaiting_turn1_answer`

## Out of Scope

- audio recording
- text answer submission
- STT
- Turn 2 or Turn 3 planning
- SSE
- intake bundle export
- preview flow
- approval flow
- chunked uploads
- video duration analysis
- client-side progress bars

## Required Inputs

- a valid web session in `collecting_media`
- at least one uploaded photo before finalization
- valid image MIME type or extension for photos
- optional single video file

## Required Outputs

For a successfully finalized upload step, the implementation must produce:

- uploaded media files under `raw/`
- `media_files` rows for active uploaded media
- `session_messages` rows recording upload activity
- `chat_log.jsonl` entries for upload activity and Turn 1 question
- `generated/media_preflight.json`
- `planners/turn1_question.txt`
- `planners/turn1_planner.json`
- updated `session_metadata.json`
- a session row whose stage is `awaiting_turn1_answer`

## Acceptance Criteria

### A. Upload Page

- `GET /s/<customer_token>/upload` renders a real HTML page for a `collecting_media` session.
- The page includes the current uploaded media list.
- The page includes an upload action and a finalize action.

### B. Upload Persistence

- Posting a valid photo upload stores the file under the session `raw/` directory.
- Posting a valid upload creates a `media_files` row.
- Posting a valid upload creates a `session_messages` row.
- Posting a valid upload appends an upload event to `chat_log.jsonl`.
- Uploads beyond the configured count limit are rejected clearly.

### C. Delete Flow

- A previously uploaded media item can be deleted while the session is still in `collecting_media`.
- Deletion removes the active `media_files` row.
- Deletion removes the file from disk.
- Deletion updates the rendered upload list.

### D. Finalize Flow

- Finalization fails clearly if there are zero uploaded photos.
- Finalization writes `generated/media_preflight.json`.
- Finalization persists Turn 1 question text.
- Finalization writes `planners/turn1_question.txt`.
- Finalization writes `planners/turn1_planner.json`.
- Finalization updates `sessions.preflight_json`.
- Finalization updates `sessions.turn1_question`.
- Finalization changes session stage to `awaiting_turn1_answer`.

### E. Interview Landing

- After successful finalization, the customer can load `/s/<customer_token>/interview`.
- The interview page renders the generated Turn 1 question.
- The session landing route now redirects to `/s/<customer_token>/interview`.

## Operator Flows Required

1. Create a web session for `sisun8082`
2. Upload at least one photo
3. Optionally delete an uploaded file before finalizing
4. Finalize uploads
5. Confirm that the interview page shows Turn 1

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Shop registry source: checked-in JSON config
- Existing artifact root and SQLite runtime from Web Phase 1
- For verification, the heuristic engine path is acceptable
- External API-backed multimodal engines may be configured later, but they are not required for verification

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. automated test command(s)
3. manual verification commands or scripted flows
4. produced artifact paths for:
   - uploaded raw file(s)
   - `generated/media_preflight.json`
   - `planners/turn1_question.txt`
   - `planners/turn1_planner.json`
   - updated `session_metadata.json`
5. pass/fail status for each acceptance group
6. evidence that finalization moves the session to `awaiting_turn1_answer`
7. evidence that interview landing shows Turn 1 question

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- uploads only exist in temporary memory and are not written to `raw/`
- uploads are written to disk but not indexed in SQLite
- delete-before-finalize does not work
- finalization does not write preflight artifacts
- finalization does not persist Turn 1 question
- session stage remains `collecting_media` after successful finalization
- interview page still shows only a placeholder after finalization
