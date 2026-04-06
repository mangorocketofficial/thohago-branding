# Web Phase 1 Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [web_phase1_contract.md](./web_phase1_contract.md)

Use this document to record evidence against the active Web Phase 1 contract. Do not use it to redefine scope.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for manual verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Verification DB path: [web_phase1_verify.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase1_verify.sqlite3)
- Verification artifact root: [runs](/C:/Users/User/Desktop/Thohago_branding/runs)

## Automated Test Evidence

### Web Phase 1 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase1.py' -v`
- Result: Pass (4 tests)
- Coverage:
  - SQLite schema initialization
  - CLI session creation
  - customer token redirect to upload page
  - admin auth rejection and authenticated session creation

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (13 tests)
- Purpose: verified that Web Phase 1 changes did not break existing replay and Telegram loop tests

## Manual Verification Commands

### 1. Initialize web database

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase1_verify.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase1-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase1-password'
$env:THOHAGO_SYNC_API_TOKEN='phase1-sync-token'
python -m thohago web init-db
```

- Result: Pass
- Output summary:
  - `web_database=C:\Users\User\Desktop\Thohago_branding\runs\_web_runtime\web_phase1_verify.sqlite3`

### 2. Create session from CLI

- Command:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
$env:THOHAGO_WEB_DB_PATH='runs/_web_runtime/web_phase1_verify.sqlite3'
$env:THOHAGO_WEB_BASE_URL='https://verify.thohago.test'
$env:THOHAGO_ADMIN_USERNAME='phase1-admin'
$env:THOHAGO_ADMIN_PASSWORD='phase1-password'
$env:THOHAGO_SYNC_API_TOKEN='phase1-sync-token'
python -m thohago web create-session --shop-id sisun8082 --session-key web_phase1_verify
```

- Result: Pass
- Output summary:
  - `shop_id=sisun8082`
  - `session_id=web_phase1_verify-20260401T040150Z`
  - `session_key=web_phase1_verify`
  - `customer_token=dEw2xv9dVa4RefvQgnUHmWIRKA7JVu9g`
  - `customer_url=https://verify.thohago.test/s/dEw2xv9dVa4RefvQgnUHmWIRKA7JVu9g`
  - `artifact_dir=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase1_verify-20260401T040150Z`
  - `session_metadata=C:\Users\User\Desktop\Thohago_branding\runs\sisun8082\web_phase1_verify-20260401T040150Z\session_metadata.json`

## Produced Artifacts

- Verification DB: [web_phase1_verify.sqlite3](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase1_verify.sqlite3)
- CLI-created artifact directory: [web_phase1_verify-20260401T040150Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase1_verify-20260401T040150Z)
- CLI-created session metadata: [session_metadata.json](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase1_verify-20260401T040150Z/session_metadata.json)
- Admin-created artifact directory: [web_phase1_admin_verify-20260401T040205Z](/C:/Users/User/Desktop/Thohago_branding/runs/sisun8082/web_phase1_admin_verify-20260401T040205Z)

## Database Verification

- Command summary: inline Python query against the verification DB
- Result: Pass
- Observed tables:
  - `media_files`
  - `schema_migrations`
  - `session_artifacts`
  - `session_messages`
  - `sessions`
- Observed sessions:
  - `web_phase1_verify-20260401T040150Z | sisun8082 | collecting_media | sisun8082/web_phase1_verify-20260401T040150Z`
  - `web_phase1_admin_verify-20260401T040205Z | sisun8082 | collecting_media | sisun8082/web_phase1_admin_verify-20260401T040205Z`

## Customer and Admin Flow Verification

- Command summary: inline `fastapi.testclient.TestClient` script using the verification DB and token `dEw2xv9dVa4RefvQgnUHmWIRKA7JVu9g`
- Result: Pass
- Observed results:
  - `GET /s/<token>` -> `307`
  - redirect location -> `/s/dEw2xv9dVa4RefvQgnUHmWIRKA7JVu9g/upload`
  - `GET /s/<token>/upload` -> `200`
  - upload page contains `Upload Placeholder` -> `True`
  - `GET /s/not-a-real-token` -> `404`
  - `GET /admin/sessions` without credentials -> `401`
  - `POST /admin/sessions` with valid Basic auth -> `200`
  - authenticated admin response contains `Session created.` -> `True`

## Acceptance Checklist

### A. Web Package Foundation

- [x] `src/thohago/web/` exists and is importable
- [x] app factory builds a FastAPI app
- [x] customer and admin routes are mounted

### B. Config and Database

- [x] `load_config()` returns web-specific settings
- [x] DB initialization path creates schema from an empty file
- [x] schema contains `sessions`, `media_files`, `session_messages`, `session_artifacts`

### C. Session Creation

- [x] session creation works for a registered `shop_id`
- [x] unknown `shop_id` handling is implemented in service/admin path
- [x] `session_metadata.json` is written
- [x] new sessions start in `collecting_media`
- [x] customer URL contains the generated customer token

### D. Customer Routing

- [x] `GET /s/<customer_token>` redirects for a known session
- [x] `collecting_media` redirects to `/upload`
- [x] upload placeholder page renders with session/shop context
- [x] unknown customer tokens return `404`

### E. Admin Routing

- [x] admin routes require HTTP Basic auth
- [x] authenticated admin users can load the session list page
- [x] authenticated admin users can create a session

### F. CLI Entry Points

- [x] CLI can initialize the web database
- [x] CLI can create a web session and print identifiers plus customer URL

## Remaining Gaps

- No gaps against the Web Phase 1 contract
- Upload handling, interview flow, sync bridge, and preview flow remain intentionally deferred to later phases

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
