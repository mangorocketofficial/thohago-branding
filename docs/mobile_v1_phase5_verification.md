# Mobile_V1 Phase 5 Verification

> Status: Verified  
> Date: 2026-04-08  
> Contract: [mobile_v1_phase5_contract.md](./mobile_v1_phase5_contract.md)

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
  - existing sync/preview runtime reused for approved-session downloads
  - heuristic interview engine path for deterministic local verification

---

## 2. Commands Executed

### 2.1 Mobile_V1 Phase 5 Test Suite

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase5.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.2 Mobile_V1 Phase 4 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase4.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.3 Existing Web Phase 4 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_web_phase4.py"
```

Result:

- Pass
- `Ran 5 tests`
- `OK`

### 2.4 Local App Startup And Live Route Verification

Startup method:

- started local uvicorn server on `127.0.0.1:8015`
- used isolated verification runtime paths under:
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\artifacts`
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\runtime\web.sqlite3`
- forced:
  - `THOHAGO_DEFAULT_INTERVIEW_ENGINE=heuristic`
  - `THOHAGO_SYNC_API_TOKEN=phase5-live-token`

Effective startup command:

```powershell
$env:PYTHONPATH='src'
python -m uvicorn thohago.web.app:create_app --factory --host 127.0.0.1 --port 8015
```

Live verification method:

- signed in through the stub app route
- completed onboarding
- created a real app-side session
- uploaded one real JPG and one real MP4 from the checked-in sample assets
- finalized uploads and completed the 3-turn interview
- uploaded preview assets through the existing sync upload API
- approved the preview from the app shell
- reopened the same `/app/session/:sessionId`
- downloaded one individual result file from the app shell
- downloaded the delivery bundle archive from the app shell
- reloaded `/app` and confirmed the approved session still reopened normally

Observed live route results:

```json
{
  "session_id": "mobile_v1_app_20260408050303-20260408T050303Z",
  "sign_in_status": 303,
  "onboarding_status": 303,
  "create_status": 303,
  "upload_status": 200,
  "preview_upload_status": 200,
  "approved_page_status": 200,
  "approved_page_has_bundle_action": true,
  "approved_page_has_thread_download": true,
  "approved_page_has_blog_download": true,
  "thread_download_status": 200,
  "thread_download_body": "Live Delivery Thread",
  "blog_download_status": 200,
  "blog_download_has_html": true,
  "bundle_download_status": 200,
  "bundle_contains_manifest": true,
  "bundle_contains_video": true,
  "bundle_contains_blog": true,
  "bundle_contains_thread": true,
  "bundle_contains_carousel": true,
  "workspace_status": 200,
  "workspace_has_session": true,
  "session_stage": "approved",
  "approved_at_present": true
}
```

Observed approved delivery page snippet:

```html
<title>결과 받기</title>
<p class="eyebrow">승인 완료</p>
<h1>결과 파일을 받을 수 있어요</h1>
```

Observed workspace snippet for the verified session:

```html
<a href="/app/session/mobile_v1_app_20260408050303-20260408T050303Z" class="session-card">
  <strong>mobile_v1_app_20260408050303-20260408T050303Z</strong>
  <span class="stage-chip">승인 완료</span>
</a>
```

---

## 3. Implemented Outputs

### 3.1 Approved-Session Delivery Routing

- customer delivery zip helper:
  - [sync.py](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/services/sync.py)
- app-side individual file and bundle download routes:
  - [product.py](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/routes/product.py)

### 3.2 Updated Approved Session UI

- approved delivery view with bundle and per-file download actions:
  - [app_session.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/app_session.html)
- download action styling:
  - [app.css](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/static/app.css)

### 3.3 Automated Tests

- Phase 5 delivery coverage:
  - [test_mobile_v1_phase5.py](/C:/Users/User/Desktop/Thohago_branding_mobile/tests/test_mobile_v1_phase5.py)

---

## 4. Artifact Evidence

Verified session artifact root:

- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\artifacts\demo_shop_2\mobile_v1_app_20260408050303-20260408T050303Z`

Verified approved published files:

- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\artifacts\demo_shop_2\mobile_v1_app_20260408050303-20260408T050303Z\published\manifest.json`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\artifacts\demo_shop_2\mobile_v1_app_20260408050303-20260408T050303Z\published\shorts\preview.mp4`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\artifacts\demo_shop_2\mobile_v1_app_20260408050303-20260408T050303Z\published\blog\index.html`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\artifacts\demo_shop_2\mobile_v1_app_20260408050303-20260408T050303Z\published\threads\thread.txt`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase5_live_verify_20260408120209\artifacts\demo_shop_2\mobile_v1_app_20260408050303-20260408T050303Z\published\carousel\slide_01.jpg`

Saved downloaded artifacts from live verification:

- downloaded thread file:
  - [thread.txt](/C:/Users/User/Desktop/Thohago_branding_mobile/runs/phase5_live_verify_20260408120209/downloads/thread.txt)
- downloaded bundle archive:
  - [mobile_v1_app_20260408050303-20260408T050303Z-delivery.zip](/C:/Users/User/Desktop/Thohago_branding_mobile/runs/phase5_live_verify_20260408120209/downloads/mobile_v1_app_20260408050303-20260408T050303Z-delivery.zip)

---

## 5. Acceptance Criteria Check

### A. Approved Session Delivery UI

- [x] `/app/session/:sessionId` renders a real delivery state for `approved`
- [x] the page clearly shows that review is complete and files are available
- [x] the approved conversation/status history remains visible

### B. Individual Result Downloads

- [x] the app-side approved session exposes download actions for available published assets
- [x] at least one published asset can be downloaded directly from an app-side route
- [x] the customer does not need admin or sync routes for normal retrieval

### C. Bundle Download

- [x] the app-side approved session exposes a bundle download action
- [x] the bundle route returns a real downloadable archive
- [x] the archive contains approved session delivery artifacts or equivalent published outputs

### D. Workspace Continuity

- [x] the workspace reopens an approved session after delivery work is added
- [x] the workspace still shows the approved/delivery-ready session entry
- [x] downloading files does not break the app-side session route

### E. App Shell Continuity

- [x] the normal authenticated customer flow remains under `/app`
- [x] the app-side flow does not require admin pages
- [x] the app-side flow does not require sync CLI or sync API usage by the customer

### F. Mobile UX And Language

- [x] all customer-facing Phase 5 UI introduced in this phase is Korean
- [x] download controls remain usable on mobile widths
- [x] the approved delivery view shows one clear primary retrieval action

---

## 6. Remaining Gaps

These items remain intentionally deferred:

- content-type selection and generation orchestration from the app shell
- bounded regeneration UX
- usage billing or credit deduction
- voice recording and SSE transcription work
- real auth, billing, and ownership enforcement

---

## 7. Final Result

Mobile_V1 Phase 5 is verified.

The repository now supports:

- approved-session delivery UI inside `/app/session/:sessionId`
- per-file download access for published assets from the app shell
- delivery bundle download from the app shell
- workspace continuity after customer downloads
