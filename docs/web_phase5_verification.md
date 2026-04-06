# Web Phase 5 Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [web_phase5_contract.md](./web_phase5_contract.md)

Use this document to record evidence against the active Web Phase 5 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for manual verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Verification DB path: [web_phase5_verify_run.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase5_verify_run.sqlite3)
- Verification artifact directory: [web_phase5_verify_run-20260401T060053Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase5_verify_run-20260401T060053Z)
- Verification script: [web_phase5_manual_verify.py](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase5_manual_verify.py)

## Automated Test Evidence

### Web Phase 5 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase5.py' -v`
- Result: Pass (5 tests)
- Coverage:
  - admin session list auth and detail links
  - dedicated admin create page and create redirect
  - admin session detail message/artifact rendering
  - waiting page auto-check hint
  - PWA manifest, service worker, and offline routes

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (33 tests)
- Purpose: verified that Web Phase 5 changes did not break replay, Telegram loop, or earlier web phases

## Manual Verification Commands

### 1. Initialize verification DB

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase5_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase5-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase5-password'
$env:THOHAGO_SYNC_API_TOKEN='phase5-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web init-db
```

- Result: Pass
- Output summary:
  - `web_database=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase5_verify_run.sqlite3`

### 2. Create verification session

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase5_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase5-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase5-password'
$env:THOHAGO_SYNC_API_TOKEN='phase5-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python -m thohago web create-session --shop-id sisun8082 --session-key web_phase5_verify_run
```

- Result: Pass
- Output summary:
  - `session_id=web_phase5_verify_run-20260401T060053Z`
  - `customer_token=9N3g33VbtLxedprT7eyMqWWYxwrl7Pp6`
  - `customer_url=https://verify.thohago.test/s/9N3g33VbtLxedprT7eyMqWWYxwrl7Pp6`

### 3. Manual phase verification script

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase5_verify_run.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase5-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase5-password'
$env:THOHAGO_SYNC_API_TOKEN='phase5-sync-token'
$env:GROQ_API_KEY=''
$env:ANTHROPIC_API_KEY=''
$env:CLAUDE_API_KEY=''
$env:OPENAI_API_KEY=''
$env:GPT_API_KEY=''
python runs/_web_runtime/web_phase5_manual_verify.py
```

- Result: Pass
- Output summary:
  - `waiting_status=200`
  - `waiting_has_hint=True`
  - `waiting_has_refresh=True`
  - `admin_list_status=200`
  - `admin_list_has_detail_link=True`
  - `admin_detail_status=200`
  - `admin_detail_has_messages=True`
  - `admin_detail_has_artifacts=True`
  - `admin_new_status=200`
  - `admin_create_status=303`
  - `admin_create_location=/admin/sessions/web_phase5_created_via_form-20260401T060220Z?created=1`
  - `created_detail_has_customer_url=True`
  - `manifest_status=200`
  - `manifest_name=Thohago`
  - `sw_status=200`
  - `sw_has_cache=True`
  - `offline_status=200`
  - `offline_has_text=True`

## Produced Artifacts

- Verification DB: [web_phase5_verify_run.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase5_verify_run.sqlite3)
- Verification artifact directory: [web_phase5_verify_run-20260401T060053Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase5_verify_run-20260401T060053Z)
- Updated session metadata: [session_metadata.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase5_verify_run-20260401T060053Z/session_metadata.json)
- Preview manifest: [manifest.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase5_verify_run-20260401T060053Z/published/manifest.json)

## Database Verification

- Command summary: inline SQLite query against the verification DB
- Result: Pass
- Observed session state:
  - `session_stage=awaiting_approval`
- Observed artifact records:
  - `intake_bundle | generated/intake_bundle.json`
  - `manifest | published/manifest.json`
  - `shorts_video | published/shorts/preview.mp4`
  - `blog_html | published/blog/index.html`
  - `thread_text | published/threads/thread.txt`
  - `carousel_image | published/carousel/slide_01.jpg`
- Observed message history includes:
  - `Preview uploaded and ready for approval.`
  - earlier interview completion message and customer text turns
- Observed metadata state:
  - `metadata_stage=awaiting_approval`
  - `metadata_has_preview_manifest=True`

## Acceptance Checklist

### A. Admin Session List

- [x] admin session list remains authenticated
- [x] session list includes detail links
- [x] session list still supports session creation flow

### B. Admin Session Detail

- [x] admin session detail renders real HTML
- [x] detail page shows session id, shop id, stage, and customer URL
- [x] detail page shows session message history
- [x] detail page shows artifact records

### C. Admin Session Creation Page

- [x] dedicated create page renders real HTML
- [x] admin can create a session from the dedicated page
- [x] successful creation surfaces the customer URL via redirected detail page

### D. Waiting Page Polish

- [x] waiting page renders real HTML for `awaiting_production`
- [x] waiting page includes preview-ready wording
- [x] waiting page includes automatic re-check behavior back to the landing route

### E. PWA Shell

- [x] manifest route returns JSON
- [x] service worker route returns JavaScript
- [x] offline fallback route returns real HTML
- [x] base layout references manifest and service worker registration

### F. Mobile and UX Polish

- [x] admin pages remain readable with wrapped tables and detail sections
- [x] customer pages continue rendering after layout changes
- [x] no existing automated tests regressed

## Remaining Gaps

- No gaps against the Web Phase 5 contract
- Notification delivery, richer admin tooling, and advanced PWA features remain intentionally deferred

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
