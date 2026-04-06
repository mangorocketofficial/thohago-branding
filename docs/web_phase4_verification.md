# Web Phase 4 Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [web_phase4_contract.md](./web_phase4_contract.md)

Use this document to record evidence against the active Web Phase 4 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for manual verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Verification DB path: [web_phase4_verify_run.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase4_verify_run.sqlite3)
- Verification artifact directory: [web_phase4_verify_run-20260401T053018Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase4_verify_run-20260401T053018Z)
- Verification preview source: [web_phase4_preview_source](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase4_preview_source)
- Verification preview manifest source: [web_phase4_preview_manifest.json](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase4_preview_manifest.json)
- Verification pull output directory: [web_phase4_pulled](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase4_pulled)

## Automated Test Evidence

### Web Phase 4 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase4.py' -v`
- Result: Pass (5 tests)
- Coverage:
  - sync token auth and session listing
  - sync download zip
  - preview upload and preview page rendering
  - revision and approval state transitions
  - live CLI `list`, `pull`, and `push` against a local uvicorn server

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (28 tests)
- Purpose: verified that Web Phase 4 changes did not break replay, Telegram loop, or earlier web phases

## Manual Verification Commands

### 1. Initialize verification DB

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase4_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase4-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase4-password'
$env:THOHAGO_SYNC_API_TOKEN='phase4-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web init-db
```

- Result: Pass
- Output summary:
  - `web_database=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase4_verify_run.sqlite3`

### 2. Create verification session

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase4_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase4-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase4-password'
$env:THOHAGO_SYNC_API_TOKEN='phase4-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web create-session --shop-id sisun8082 --session-key web_phase4_verify_run
```

- Result: Pass
- Output summary:
  - `session_id=web_phase4_verify_run-20260401T053018Z`
  - `customer_token=YDLnNklJ-gtiqPnXGgfd0fZbnB-o3vDF`
  - `customer_url=https://verify.thohago.test/s/YDLnNklJ-gtiqPnXGgfd0fZbnB-o3vDF`

### 3. Prepare awaiting_production intake state

- Flow: inline `fastapi.testclient.TestClient` script uploaded one photo, finalized uploads, and completed 3 text interview turns
- Result: Pass
- Observed result:
  - `stage awaiting_production`

### 4. Create preview source and manifest

- Flow: inline Python script wrote preview files and `web_phase4_preview_manifest.json`
- Result: Pass
- Produced source files:
  - `shorts/preview.mp4`
  - `blog/index.html`
  - `threads/thread.txt`
  - `carousel/slide_01.jpg`

### 5. Live sync CLI + preview + approval flow

- Command: `python runs/_web_runtime/web_phase4_manual_verify.py`
- Script behavior:
  - starts local uvicorn server for the current app
  - runs `thohago sync list`
  - runs `thohago sync pull`
  - runs `thohago sync push`
  - opens preview page
  - requests revision once
  - approves once
- Result: Pass
- Output summary:
  - `list_output=count=1 || session_1=web_phase4_verify_run-20260401T053018Z|sisun8082|awaiting_production|https://verify.thohago.test/s/YDLnNklJ-gtiqPnXGgfd0fZbnB-o3vDF`
  - `pull_output=session_id=web_phase4_verify_run-20260401T053018Z || downloaded_zip=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase4_pulled\web_phase4_verify_run-20260401T053018Z.zip || extract_dir=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase4_pulled\web_phase4_verify_run-20260401T053018Z`
  - `push_output=session_id=web_phase4_verify_run-20260401T053018Z || stage=awaiting_approval || preview_url=/s/YDLnNklJ-gtiqPnXGgfd0fZbnB-o3vDF/preview || manifest_path=published/manifest.json`
  - `preview_status=200`
  - `preview_has_blog=True`
  - `revision_status=303`
  - `revision_landing=/s/YDLnNklJ-gtiqPnXGgfd0fZbnB-o3vDF/preview`
  - `approve_status=303`
  - `approve_location=/s/YDLnNklJ-gtiqPnXGgfd0fZbnB-o3vDF/complete`
  - `complete_status=200`
  - `complete_has_text=True`
  - `final_landing=/s/YDLnNklJ-gtiqPnXGgfd0fZbnB-o3vDF/complete`
  - `final_stage=approved`

## Produced Artifacts

- Pulled intake zip: [web_phase4_verify_run-20260401T053018Z.zip](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase4_pulled/web_phase4_verify_run-20260401T053018Z.zip)
- Pulled extract dir: [web_phase4_verify_run-20260401T053018Z](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase4_pulled/web_phase4_verify_run-20260401T053018Z)
- Pushed preview manifest: [manifest.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase4_verify_run-20260401T053018Z/published/manifest.json)
- Pushed preview video: [preview.mp4](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase4_verify_run-20260401T053018Z/published/shorts/preview.mp4)
- Pushed blog preview: [index.html](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase4_verify_run-20260401T053018Z/published/blog/index.html)
- Pushed thread text: [thread.txt](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase4_verify_run-20260401T053018Z/published/threads/thread.txt)
- Pushed carousel image: [slide_01.jpg](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase4_verify_run-20260401T053018Z/published/carousel/slide_01.jpg)
- Updated session metadata: [session_metadata.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase4_verify_run-20260401T053018Z/session_metadata.json)

## Database Verification

- Command summary: inline SQLite query against the verification DB
- Result: Pass
- Observed session state:
  - `session_stage=approved`
  - `has_production_completed_at=True`
  - `has_approved_at=True`
- Observed `session_artifacts`:
  - `intake_bundle | generated/intake_bundle.json`
  - `manifest | published/manifest.json`
  - `shorts_video | published/shorts/preview.mp4`
  - `blog_html | published/blog/index.html`
  - `thread_text | published/threads/thread.txt`
  - `carousel_image | published/carousel/slide_01.jpg`
- Observed latest `session_messages`:
  - `customer | status | Customer approved preview.`
  - `customer | status | Customer requested revision.`
  - `system | status | Preview uploaded and ready for approval.`

## Pull Archive Verification

- Result: Pass
- Observed:
  - `pull_zip_exists=True`
  - `extract_dir_exists=True`
  - `zip_has_intake_bundle=True`
  - `extract_has_intake_bundle=True`

## Metadata Verification

- Result: Pass
- Observed metadata state:
  - `metadata_stage=approved`
  - `metadata_has_preview_manifest=True`
  - `metadata_has_approved_at=True`

## Acceptance Checklist

### A. Sync Auth

- [x] sync API rejects unauthenticated requests
- [x] sync API succeeds with valid Bearer token

### B. Sync List

- [x] API lists `awaiting_production` sessions
- [x] API supports stage filtering, including revision-capable state checks
- [x] CLI lists sessions from the sync API

### C. Sync Download

- [x] API downloads a zip of the session artifact directory
- [x] zip contains `generated/intake_bundle.json`
- [x] CLI pulls and extracts the session zip locally

### D. Sync Upload

- [x] API accepts preview bundle upload with manifest JSON
- [x] upload writes files under `published/`
- [x] upload writes `published/manifest.json`
- [x] upload records `session_artifacts`
- [x] upload changes stage to `awaiting_approval`
- [x] CLI pushes local preview artifacts to the sync API

### E. Preview Page

- [x] preview page renders real HTML for `awaiting_approval`
- [x] preview page renders manifest-driven content
- [x] session landing redirects to preview for `awaiting_approval`

### F. Approval and Revision

- [x] revision action changes stage to `revision_requested`
- [x] approve action changes stage to `approved`
- [x] session landing redirects to `complete` for `approved`
- [x] session landing redirects to `preview` for `revision_requested`

## Remaining Gaps

- No gaps against the Web Phase 4 contract
- Direct platform publishing and notification delivery remain intentionally deferred to later phases

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
