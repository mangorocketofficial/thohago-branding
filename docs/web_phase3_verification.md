# Web Phase 3 Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [web_phase3_contract.md](./web_phase3_contract.md)

Use this document to record evidence against the active Web Phase 3 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for manual verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Verification DB path: [web_phase3_verify_run.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase3_verify_run.sqlite3)
- Verification artifact directory: [web_phase3_verify_run-20260401T050342Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z)
- Engine path used for verification: heuristic fallback only

## Automated Test Evidence

### Web Phase 3 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase3.py' -v`
- Result: Pass (5 tests)
- Coverage:
  - interview page rendering
  - pending answer submit and retry
  - pending answer replacement
  - Turn 1 confirm to Turn 2 planning
  - full 3-turn completion to waiting state and intake bundle export

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (23 tests)
- Purpose: verified that Web Phase 3 changes did not break replay, Telegram loop, Web Phase 1, or Web Phase 2

## Manual Verification Commands

### 1. Initialize verification DB

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase3_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase3-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase3-password'
$env:THOHAGO_SYNC_API_TOKEN='phase3-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web init-db
```

- Result: Pass
- Output summary:
  - `web_database=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase3_verify_run.sqlite3`

### 2. Create verification session

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase3_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase3-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase3-password'
$env:THOHAGO_SYNC_API_TOKEN='phase3-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web create-session --shop-id sisun8082 --session-key web_phase3_verify_run
```

- Result: Pass
- Output summary:
  - `shop_id=sisun8082`
  - `session_id=web_phase3_verify_run-20260401T050342Z`
  - `customer_token=8x_Y3M-QipuXHijpt8AJMERO8HOdErng`
  - `customer_url=https://verify.thohago.test/s/8x_Y3M-QipuXHijpt8AJMERO8HOdErng`
  - `artifact_dir=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase3_verify_run-20260401T050342Z`

### 3. Upload, finalize, complete 3 interview turns, and land on waiting

- Flow: inline `fastapi.testclient.TestClient` script using the verification session token above and one checked-in sample JPG
- Result: Pass
- Observed results:
  - `upload_status=200`
  - `finalize_status=303`
  - `interview1_status=200`
  - `submit1_status=303`
  - `replace1_status=303`
  - `confirm1_status=303`
  - `interview2_status=200`
  - `submit2_status=303`
  - `confirm2_status=303`
  - `interview3_status=200`
  - `submit3_status=303`
  - `confirm3_status=303`
  - `confirm3_location=/s/8x_Y3M-QipuXHijpt8AJMERO8HOdErng/waiting`
  - `waiting_status=200`
  - `waiting_has_complete=True`
  - `landing_status=307`
  - `landing_location=/s/8x_Y3M-QipuXHijpt8AJMERO8HOdErng/waiting`
  - `session_stage=awaiting_production`

## Produced Artifacts

- Verification DB: [web_phase3_verify_run.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase3_verify_run.sqlite3)
- Verification artifact directory: [web_phase3_verify_run-20260401T050342Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z)
- Turn 1 transcript text: [turn1_transcript.txt](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/transcripts/turn1_transcript.txt)
- Turn 2 transcript text: [turn2_transcript.txt](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/transcripts/turn2_transcript.txt)
- Turn 3 transcript text: [turn3_transcript.txt](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/transcripts/turn3_transcript.txt)
- Turn 2 planner: [turn2_planner.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/planners/turn2_planner.json)
- Turn 3 planner: [turn3_planner.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/planners/turn3_planner.json)
- Intake bundle: [intake_bundle.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/generated/intake_bundle.json)
- Updated session metadata: [session_metadata.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/session_metadata.json)
- Chat log: [chat_log.jsonl](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase3_verify_run-20260401T050342Z/chat_log.jsonl)

## Database Verification

- Command summary: inline SQLite query against the verification DB
- Result: Pass
- Observed session state:
  - `session_stage=awaiting_production`
  - `pending_answer=None`
  - `has_turn2_planner=True`
  - `has_turn3_planner=True`
  - `has_interview_completed_at=True`
- Observed `session_messages`:
  - initial system Turn 1 question exists
  - confirmed customer answers exist for turns 1, 2, and 3
  - final system status message exists
- Observed `session_artifacts`:
  - `intake_bundle | generated/intake_bundle.json`

## Metadata and Intake Bundle Verification

- Result: Pass
- Observed metadata state:
  - `metadata_stage=awaiting_production`
  - `metadata_has_turn2=True`
  - `metadata_has_turn3=True`
  - `metadata_has_intake_bundle=True`
- Observed intake bundle state:
  - `intake_bundle_stage=awaiting_production`
  - `intake_bundle_transcript_count=3`

## Chat Log Verification

- Result: Pass
- Observed chat log:
  - `chat_log_lines=8`
  - last entry is the final bot status message with `stage=awaiting_production`

## Acceptance Checklist

### A. Interview Page

- [x] interview page renders real HTML for `awaiting_turn1_answer`
- [x] interview page shows current question text
- [x] interview page shows text answer submission form
- [x] `confirming_turnN` state shows pending answer with confirm/retry actions

### B. Text Submission

- [x] text submit stores `pending_answer`
- [x] submit changes stage to `confirming_turnN`
- [x] replacement submit overwrites existing pending answer

### C. Retry

- [x] retry clears `pending_answer`
- [x] retry returns session to `awaiting_turnN_answer`

### D. Turn Progression

- [x] Turn 1 confirm writes transcript artifacts and Turn 2 planner artifacts
- [x] Turn 1 confirm changes stage to `awaiting_turn2_answer`
- [x] Turn 2 confirm writes transcript artifacts and Turn 3 planner artifacts
- [x] Turn 2 confirm changes stage to `awaiting_turn3_answer`
- [x] Turn 3 confirm writes transcript artifacts and exports `generated/intake_bundle.json`
- [x] Turn 3 confirm changes stage to `awaiting_production`

### E. Artifact Persistence

- [x] all 3 transcript text and JSON artifacts are written
- [x] Turn 2 planner files are written
- [x] Turn 3 planner files are written
- [x] `generated/intake_bundle.json` is written

### F. Waiting State

- [x] waiting page renders for `awaiting_production`
- [x] session landing redirects to waiting page after Turn 3 confirm

## Remaining Gaps

- No gaps against the Web Phase 3 contract
- Audio recording, STT, and SSE remain intentionally deferred to a later contract-driven phase

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
