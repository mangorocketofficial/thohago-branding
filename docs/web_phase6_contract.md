# Web Phase 6 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_migration_spec.md](./web_migration_spec.md)

## Goal

Deliver the voice recording, STT, and SSE augmentation layer for the web migration:

- browser audio recording from the interview page
- server-side audio upload endpoint
- STT transcription for uploaded audio
- SSE updates for transcription progress and transcript-ready states
- transcript confirmation flow integrated with the existing text-first interview flow

## Business Outcome

Customers should be able to answer interview turns by voice instead of text only. The server should transcribe the recording, push the transcript into the page in real time, and let the customer confirm or retry before progressing.

## Scope Decision

This phase supports two STT runtime modes:

1. live Groq STT when `GROQ_API_KEY` is configured
2. deterministic stub STT when live credentials are unavailable

The stub mode exists so the phase can be fully executed and verified in the current development environment. Live Groq STT remains the production path.

## In Scope

1. Browser recording UI
   - interview page includes voice recording controls
   - browser records audio with MediaRecorder
   - browser posts recorded audio to the interview record endpoint

2. Server audio intake
   - `POST /s/<customer_token>/interview/record` accepts one audio blob
   - audio is stored under `raw/` with turn-aware naming
   - uploaded audio is indexed in `media_files`
   - uploaded audio activity is recorded in `session_messages`

3. STT integration
   - server resolves a transcription provider
   - live Groq path works when configured
   - stub path works without external credentials
   - STT success writes/updates `pending_answer`
   - STT failure does not corrupt session state

4. SSE event stream
   - `GET /s/<customer_token>/events` returns a working event stream
   - audio upload emits `transcribing`
   - successful transcription emits `transcript_ready`
   - failed transcription emits `transcript_failed`

5. Interview UI integration
   - interview page opens an SSE connection
   - transcript-ready events update the page to confirmation state
   - customer can confirm or retry the transcribed answer using the existing text-first flow

## Out of Scope

- durable SSE replay across reconnects
- background workers or multi-node pub/sub
- waveform visualization
- advanced audio format conversion pipeline
- production-grade retry queues

## Required Inputs

- a valid session already in `awaiting_turnN_answer`
- browser-recorded audio upload for the current turn
- either configured Groq STT credentials or stub-mode STT fallback

## Required Outputs

For a successful voice answer cycle, the implementation must produce:

- one audio file under `raw/turnN_audio.*`
- one `media_files` row for the audio upload
- one `session_messages` row recording the audio upload
- `pending_answer` populated with transcribed text
- session stage changed to `confirming_turnN`
- SSE events showing progress and transcript readiness

## Acceptance Criteria

### A. Recording UI

- Interview page includes recording controls.
- Interview page loads the recorder client script.
- Interview page connects to the SSE endpoint.

### B. Audio Intake

- `POST /s/<customer_token>/interview/record` accepts an audio file for an interview turn.
- The audio file is written to the session `raw/` directory.
- The upload creates a `media_files` row with `kind=audio`.
- The upload creates a `session_messages` row for the audio event.

### C. STT

- A successful voice upload produces transcribed text.
- Successful transcription sets `pending_answer`.
- Successful transcription changes the session stage to `confirming_turnN`.
- When STT fails, the server returns a clear failure signal and the session does not advance incorrectly.

### D. SSE

- `GET /s/<customer_token>/events` opens a valid SSE stream.
- The server emits `transcribing` before transcription completes.
- The server emits `transcript_ready` with transcript text on success.
- The server emits `transcript_failed` on failure.

### E. Voice Confirmation Flow

- After a successful voice upload, the customer can confirm the transcribed answer.
- Confirm uses the existing interview progression logic.
- Retry clears the pending answer and returns to `awaiting_turnN_answer`.

## Operator Flows Required

1. Prepare a session in `awaiting_turn1_answer`
2. Open the interview page and confirm recording controls are present
3. Open the SSE stream
4. Upload a recorded audio blob
5. Observe `transcribing` and `transcript_ready`
6. Confirm the transcribed answer and verify turn progression

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Existing artifact root and SQLite runtime from earlier web phases
- Verification may use stub STT mode
- Live Groq STT remains optional for verification and available for production

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. automated test command(s)
3. manual verification commands or scripted flows
4. pass/fail status for each acceptance group
5. produced artifact path for at least one audio upload
6. evidence of SSE `transcribing` and `transcript_ready` or `transcript_failed`
7. evidence that voice confirmation advances the session

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- recording controls are missing from the interview page
- audio uploads are accepted but not stored under `raw/`
- STT never populates `pending_answer`
- SSE endpoint exists but does not emit transcription events
- voice answers cannot be confirmed through the existing interview flow
