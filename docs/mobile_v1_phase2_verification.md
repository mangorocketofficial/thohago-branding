# Mobile_V1 Phase 2 Verification

> Status: Verified  
> Date: 2026-04-08  
> Contract: [mobile_v1_phase2_contract.md](./mobile_v1_phase2_contract.md)

---

## 1. Verification Environment

- OS: Windows (PowerShell)
- Python: `3.12.8`
- Working directory: `C:\Users\User\Desktop\Thohago_branding_mobile`
- Frontend/runtime stack under test:
  - FastAPI
  - Jinja2 templates
  - static CSS
  - vanilla JavaScript
  - PWA manifest/service worker
  - existing SQLite session/media runtime

---

## 2. Commands Executed

### 2.1 Mobile_V1 Phase 2 Test Suite

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase2.py"
```

Result:

- Pass
- `Ran 4 tests`
- `OK`

### 2.2 Phase 1 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase1.py"
```

Result:

- Pass
- `Ran 4 tests`
- `OK`

### 2.3 Existing Web Phase 1 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_web_phase1.py"
```

Result:

- Pass
- `Ran 4 tests`
- `OK`

### 2.4 Local App Startup And Live Route Verification

Startup command:

```powershell
$env:PYTHONPATH='src'
python -m uvicorn thohago.web.app:create_app --factory --host 127.0.0.1 --port 8012
```

Live verification method:

- started local uvicorn server on `127.0.0.1:8012`
- signed in through the stub app route
- completed onboarding
- created a real app-side session
- uploaded one photo and one video
- deleted one uploaded file
- confirmed the workspace still listed the session
- stopped the local process after verification

Observed live route results:

```json
{
  "session_id": "mobile_v1_app_20260408021829-20260408T021829Z",
  "upload_status": 200,
  "delete_status": 200,
  "workspace_status": 200,
  "upload_has_photo": true,
  "upload_has_video": true,
  "workspace_has_session": true,
  "delete_removed_first_file": true
}
```

---

## 3. Implemented Outputs

### 3.1 App-Side Session And Upload Routes

- app shell and upload flow:
  - [product.py](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/routes/product.py)

### 3.2 Updated Templates

- workspace with recent sessions:
  - [app_workspace.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/app_workspace.html)
- app session page with upload and delete actions:
  - [app_session.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/app_session.html)

### 3.3 Supporting Files

- styling updates for workspace/session upload UI:
  - [app.css](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/static/app.css)
- automated tests:
  - [test_mobile_v1_phase2.py](/C:/Users/User/Desktop/Thohago_branding_mobile/tests/test_mobile_v1_phase2.py)

---

## 4. Acceptance Criteria Check

### A. Session Creation

- [x] the workspace can create a real app-side session
- [x] the session route uses a persisted session identifier
- [x] the session page can be reopened after creation

### B. Upload Functionality

- [x] the app session page accepts photo uploads
- [x] the app session page accepts video uploads
- [x] upload constraints are enforced by the reused upload runtime
- [x] validation failures stay within the app-side session surface

### C. Persistence

- [x] uploaded media is written to disk
- [x] uploaded media rows are written to `media_files`
- [x] related session messages are written to `session_messages`

### D. Mobile UX

- [x] uploaded items are visible on the session page
- [x] uploaded items can be deleted from the session page
- [x] the app workspace can show created session entries
- [x] customer-facing upload UI is Korean

### E. Implementation Discipline

- [x] normal app-side upload flow stays within `/app` and `/app/session/:sessionId`
- [x] users are not redirected into the legacy `/s/<customer_token>` upload page for the new app flow
- [x] interview is clearly deferred to the next phase

---

## 5. Remaining Gaps

These items are intentionally deferred to later phases:

- interview execution in the new app shell
- upload finalization into turn 1 question
- voice recording flow in the new app shell
- real auth/user ownership
- real payment integration

---

## 6. Final Result

Mobile_V1 Phase 2 is verified.

The repository now supports:

- real app-side session creation from the workspace
- mobile photo/video upload from `/app/session/:sessionId`
- uploaded file listing in the app shell
- uploaded file deletion in the app shell
- workspace visibility for app-created sessions

