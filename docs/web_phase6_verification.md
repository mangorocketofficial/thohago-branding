# Web Phase 6 Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [web_phase6_contract.md](./web_phase6_contract.md)

Use this document to record evidence against the active Web Phase 6 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for verification: `C:\Users\User\Desktop\Thohago_branding\src`
- STT mode used for verification: `stub`
- Live Groq STT verification: not required for this contract and not executed

## Automated Test Evidence

### Web Phase 6 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase6.py' -v`
- Result: Pass (5 tests)
- Coverage:
  - interview page voice controls and SSE wiring
  - audio upload persistence and `pending_answer` population
  - live uvicorn SSE path emitting `transcribing` then `transcript_ready`
  - live uvicorn SSE path emitting `transcript_failed` when transcriber raises
  - voice answer confirm path advancing to Turn 2

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (38 tests)
- Purpose: verified that Web Phase 6 changes did not break replay, Telegram loop, or earlier web phases

## Manual / Scripted Execution Evidence

### 1. Initialize verification DB

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase6_verify_exec.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase6-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase6-password'
$env:THOHAGO_SYNC_API_TOKEN='phase6-sync-token'
$env:THOHAGO_WEB_STT_MODE='stub'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web init-db
```

- Result: Pass
- Output summary:
  - `web_database=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase6_verify_exec.sqlite3`

### 2. Create verification session

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase6_verify_exec.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase6-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase6-password'
$env:THOHAGO_SYNC_API_TOKEN='phase6-sync-token'
$env:THOHAGO_WEB_STT_MODE='stub'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web create-session --shop-id sisun8082 --session-key web_phase6_exec_run
```

- Result: Pass
- Output summary:
  - `session_id=web_phase6_exec_run-20260401T062217Z`
  - `customer_token=weRs1LyHeu_rn-w0bNyw9p1L7H1fpnUL`
  - `customer_url=https://verify.thohago.test/s/weRs1LyHeu_rn-w0bNyw9p1L7H1fpnUL`

### 3. Scripted voice upload and confirm flow

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase6_verify_exec.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase6-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase6-password'
$env:THOHAGO_SYNC_API_TOKEN='phase6-sync-token'
$env:THOHAGO_WEB_STT_MODE='stub'
$env:THOHAGO_VERIFY_SESSION_ID='web_phase6_exec_run-20260401T062217Z'
$env:THOHAGO_VERIFY_CUSTOMER_TOKEN='weRs1LyHeu_rn-w0bNyw9p1L7H1fpnUL'
python runs/_web_runtime/web_phase6_record_confirm.py
```

- Result: Pass
- Output summary:
  - `upload_status=200`
  - `finalize_status=303`
  - `record_status=202`
  - `record_stage=confirming_turn1`
  - `record_pending=[stub transcript] turn1_audio`
  - `confirm_status=303`
  - `confirm_location=/s/weRs1LyHeu_rn-w0bNyw9p1L7H1fpnUL/interview`
  - `session_stage=awaiting_turn2_answer`
  - `audio_path=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase6_exec_run-20260401T062217Z\raw\turn1_audio.webm`
  - `transcript_json=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase6_exec_run-20260401T062217Z\transcripts\turn1_transcript.json`
  - `turn2_planner=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase6_exec_run-20260401T062217Z\planners\turn2_planner.json`

### 4. Live SSE execution evidence

- Command: `python -m unittest discover -s tests -p 'test_web_phase6.py' -v`
- Scripted live-server checks included in this command:
  - `test_sse_emits_transcribing_and_transcript_ready`
  - `test_sse_emits_transcript_failed_when_transcriber_raises`
- Result: Pass
- Verified event sequence:
  - success path: `transcribing` -> `transcript_ready`
  - failure path: `transcribing` -> `transcript_failed`

## Produced Artifacts

- Verification DB: [web_phase6_verify_exec.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase6_verify_exec.sqlite3)
- Verification artifact directory: [web_phase6_exec_run-20260401T062217Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase6_exec_run-20260401T062217Z)
- Recorded audio: [turn1_audio.webm](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase6_exec_run-20260401T062217Z/raw/turn1_audio.webm)
- Turn 1 transcript JSON: [turn1_transcript.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase6_exec_run-20260401T062217Z/transcripts/turn1_transcript.json)
- Turn 2 planner: [turn2_planner.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase6_exec_run-20260401T062217Z/planners/turn2_planner.json)

## Database Verification

- Command summary: inline SQLite query against the verification DB
- Result: Pass
- Observed session state:
  - `session_stage=awaiting_turn2_answer`
  - `pending_answer=None`
- Observed `media_files`:
  - `audio | interview_turn1 | raw/turn1_audio.webm`
  - `photo | upload | raw/photo_01.jpg`
- Observed recent `session_messages`:
  - system Turn 2 question exists
  - customer confirmed Turn 1 text exists
  - customer audio event exists
- Observed transcript artifact:
  - `transcript_source=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase6_exec_run-20260401T062217Z\raw\turn1_audio.webm`
  - `transcript_text=[stub transcript] turn1_audio`

## Acceptance Checklist

### A. Recording UI

- [x] interview page includes recording controls
- [x] interview page loads `recorder.js`
- [x] interview page connects to the SSE endpoint

### B. Audio Intake

- [x] audio record endpoint accepts audio uploads
- [x] audio file is written to `raw/`
- [x] audio upload creates `media_files` row with `kind=audio`
- [x] audio upload creates `session_messages` row

### C. STT

- [x] successful voice upload produces transcribed text
- [x] successful transcription sets `pending_answer`
- [x] successful transcription changes stage to `confirming_turnN`
- [x] STT failure path emits a clear failure and does not advance incorrectly

### D. SSE

- [x] SSE endpoint opens a valid event stream
- [x] server emits `transcribing`
- [x] server emits `transcript_ready` on success
- [x] server emits `transcript_failed` on failure

### E. Voice Confirmation Flow

- [x] customer can confirm a transcribed voice answer
- [x] confirm uses the existing interview progression logic
- [x] retry path remains available and tested in existing interview flow

## Remaining Gaps

- No gaps against the Web Phase 6 contract
- Live Groq STT is implemented but not executed in this verification run because stub mode was intentionally used
- Durable SSE replay remains intentionally out of scope

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
