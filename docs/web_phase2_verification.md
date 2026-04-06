# Web Phase 2 Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [web_phase2_contract.md](./web_phase2_contract.md)

Use this document to record evidence against the active Web Phase 2 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for manual verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Verification DB path: [web_phase2_verify_run.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase2_verify_run.sqlite3)
- Verification artifact directory: [web_phase2_verify_run-20260401T045107Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z)
- Engine path used for verification: heuristic fallback only

## Automated Test Evidence

### Web Phase 2 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase2.py' -v`
- Result: Pass (5 tests)
- Coverage:
  - photo upload persistence
  - delete-before-finalize
  - upload count limit rejection
  - finalize rejection with zero photos
  - finalize to interview with preflight and Turn 1 artifacts

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (18 tests)
- Purpose: verified that Web Phase 2 changes did not break existing replay, Telegram loop, or Web Phase 1 tests

## Manual Verification Commands

### 1. Initialize verification DB

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase2_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase2-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase2-password'
$env:THOHAGO_SYNC_API_TOKEN='phase2-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web init-db
```

- Result: Pass
- Output summary:
  - `web_database=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase2_verify_run.sqlite3`

### 2. Create verification session

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase2_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase2-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase2-password'
$env:THOHAGO_SYNC_API_TOKEN='phase2-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web create-session --shop-id sisun8082 --session-key web_phase2_verify_run
```

- Result: Pass
- Output summary:
  - `shop_id=sisun8082`
  - `session_id=web_phase2_verify_run-20260401T045107Z`
  - `customer_token=nGEE6nATzBrojpZFLzpFh7B4cYNQywp_`
  - `customer_url=https://verify.thohago.test/s/nGEE6nATzBrojpZFLzpFh7B4cYNQywp_`
  - `artifact_dir=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase2_verify_run-20260401T045107Z`

### 3. Upload, delete, finalize, and land on interview

- Flow: inline `fastapi.testclient.TestClient` script using the verification session token above and one checked-in sample JPG
- Result: Pass
- Observed results:
  - `upload1_status=200`
  - `upload2_status=200`
  - `delete_status=200`
  - `finalize_status=303`
  - `finalize_location=/s/nGEE6nATzBrojpZFLzpFh7B4cYNQywp_/interview`
  - `interview_status=200`
  - `interview_has_turn1=True`
  - `landing_status=307`
  - `landing_location=/s/nGEE6nATzBrojpZFLzpFh7B4cYNQywp_/interview`
  - `session_stage=awaiting_turn1_answer`
  - `active_upload_count=1`
  - `active_upload_filename=photo_01.jpg`

## Produced Artifacts

- Verification DB: [web_phase2_verify_run.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase2_verify_run.sqlite3)
- Verification artifact directory: [web_phase2_verify_run-20260401T045107Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z)
- Active raw upload: [photo_01.jpg](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z/raw/photo_01.jpg)
- Generated preflight: [media_preflight.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z/generated/media_preflight.json)
- Turn 1 question text: [turn1_question.txt](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z/planners/turn1_question.txt)
- Turn 1 planner: [turn1_planner.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z/planners/turn1_planner.json)
- Updated session metadata: [session_metadata.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z/session_metadata.json)
- Chat log: [chat_log.jsonl](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase2_verify_run-20260401T045107Z/chat_log.jsonl)

## Database Verification

- Command summary: inline SQLite query against the verification DB
- Result: Pass
- Observed session state:
  - `session_stage=awaiting_turn1_answer`
  - `has_turn1_question=True`
  - `has_preflight_json=True`
- Observed active `media_files` rows:
  - `1 | photo | photo_01.jpg | raw/photo_01.jpg`
- Observed `session_messages` rows:
  - `customer | photo |  | raw/photo_01.jpg`
  - `customer | photo |  | raw/photo_02.jpg`
  - `customer | status | Deleted photo upload | raw/photo_02.jpg`
  - `system | text | <turn1_question> |`

## Metadata and Chat Log Verification

- Result: Pass
- Observed metadata state:
  - `metadata_stage=awaiting_turn1_answer`
  - `metadata_has_preflight_path=True`
  - `metadata_has_turn1_question=True`
- Observed chat log:
  - `chat_log_lines=4`
  - last entry is the bot Turn 1 question with `turn_index=1` and planner path metadata

## Acceptance Checklist

### A. Upload Page

- [x] upload page renders real HTML for `collecting_media`
- [x] upload page includes current uploaded media list
- [x] upload page includes upload and finalize actions

### B. Upload Persistence

- [x] photo upload stores file under `raw/`
- [x] upload creates `media_files` row
- [x] upload creates `session_messages` row
- [x] upload appends `chat_log.jsonl`
- [x] uploads beyond count limit are rejected clearly

### C. Delete Flow

- [x] uploaded media can be deleted during `collecting_media`
- [x] deletion removes active `media_files` row
- [x] deletion removes file from disk
- [x] deletion updates rendered upload list

### D. Finalize Flow

- [x] finalization fails with zero uploaded photos
- [x] finalization writes `generated/media_preflight.json`
- [x] finalization persists Turn 1 question
- [x] finalization writes `planners/turn1_question.txt`
- [x] finalization writes `planners/turn1_planner.json`
- [x] finalization updates `sessions.preflight_json`
- [x] finalization updates `sessions.turn1_question`
- [x] finalization changes stage to `awaiting_turn1_answer`

### E. Interview Landing

- [x] customer can load `/s/<customer_token>/interview` after finalization
- [x] interview page renders the generated Turn 1 question
- [x] session landing route now redirects to interview

## Remaining Gaps

- No gaps against the Web Phase 2 contract
- Audio recording, answer submission, STT, and Turn 2 or Turn 3 planning remain intentionally deferred to Web Phase 3

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
