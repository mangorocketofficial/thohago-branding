# Mobile_V1 Phase 4 Verification

> Status: Verified  
> Date: 2026-04-08  
> Contract: [mobile_v1_phase4_contract.md](./mobile_v1_phase4_contract.md)

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
  - existing sync/preview runtime reused from the web flow
  - heuristic interview engine path for deterministic local verification

---

## 2. Commands Executed

### 2.1 Mobile_V1 Phase 4 Test Suite

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase4.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.2 Mobile_V1 Phase 3 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase3.py"
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

### 2.4 Mobile_V1 Phase 2 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase2.py"
```

Result:

- Pass
- `Ran 5 tests`
- `OK`

### 2.5 Mobile_V1 Phase 1 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase1.py"
```

Result:

- Pass
- `Ran 4 tests`
- `OK`

### 2.6 Local App Startup And Live Route Verification

Startup method:

- started local uvicorn server on `127.0.0.1:8014`
- used isolated verification runtime paths under:
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts`
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\runtime\web.sqlite3`
- forced:
  - `THOHAGO_DEFAULT_INTERVIEW_ENGINE=heuristic`
  - `THOHAGO_SYNC_API_TOKEN=phase4-live-token`

Effective startup command:

```powershell
$env:PYTHONPATH='src'
python -m uvicorn thohago.web.app:create_app --factory --host 127.0.0.1 --port 8014
```

Live verification method:

- signed in through the stub app route
- completed onboarding
- created a real app-side session
- uploaded one real JPG and one real MP4 from the checked-in sample assets
- finalized uploads from `/app/session/:sessionId`
- submitted and confirmed Turn 1, Turn 2, and Turn 3 text answers
- uploaded preview assets through the existing sync upload API
- reopened the same `/app/session/:sessionId`
- confirmed preview assets rendered inside the app shell
- requested revision once from the app shell
- approved once from the app shell
- reloaded `/app/session/:sessionId` and `/app`
- confirmed published preview files and metadata were written for the approved session

Observed live route results:

```json
{
  "session_id": "mobile_v1_app_20260408043718-20260408T043718Z",
  "sign_in_status": 303,
  "onboarding_status": 303,
  "create_status": 303,
  "upload_status": 200,
  "finalize_status": 303,
  "preview_upload_status": 200,
  "preview_upload_stage": "awaiting_approval",
  "preview_page_status": 200,
  "preview_has_blog": true,
  "preview_has_thread": true,
  "preview_has_video_url": true,
  "preview_has_carousel_url": true,
  "image_asset_status": 200,
  "video_asset_status": 200,
  "revision_status": 303,
  "approve_status": 303,
  "session_stage": "approved",
  "production_completed_at_present": true,
  "approved_at_present": true,
  "artifacts_exist": {
    "manifest": true,
    "shorts_preview": true,
    "blog_preview": true,
    "thread_preview": true,
    "carousel_preview": true,
    "session_metadata": true
  }
}
```

Observed completion page snippet:

```html
<p class="eyebrow">승인 완료</p>
<h1>승인이 완료되었어요</h1>
```

Observed workspace snippet for the verified session:

```html
<a href="/app/session/mobile_v1_app_20260408043718-20260408T043718Z" class="session-card">
  <strong>mobile_v1_app_20260408043718-20260408T043718Z</strong>
  <span class="stage-chip">승인 완료</span>
</a>
```

---

## 3. Implemented Outputs

### 3.1 App-Side Preview And Approval Routing

- app-side preview file and approval routes:
  - [product.py](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/routes/product.py)

### 3.2 Updated App Session Template

- app-side waiting, preview, revision, and completion UI:
  - [app_session.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/app_session.html)

### 3.3 Automated Tests

- Phase 4 app-shell preview coverage:
  - [test_mobile_v1_phase4.py](/C:/Users/User/Desktop/Thohago_branding_mobile/tests/test_mobile_v1_phase4.py)

---

## 4. Artifact Evidence

Verified session artifact root:

- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts\demo_shop_2\mobile_v1_app_20260408043718-20260408T043718Z`

Verified published preview files:

- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts\demo_shop_2\mobile_v1_app_20260408043718-20260408T043718Z\published\manifest.json`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts\demo_shop_2\mobile_v1_app_20260408043718-20260408T043718Z\published\shorts\preview.mp4`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts\demo_shop_2\mobile_v1_app_20260408043718-20260408T043718Z\published\blog\index.html`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts\demo_shop_2\mobile_v1_app_20260408043718-20260408T043718Z\published\threads\thread.txt`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts\demo_shop_2\mobile_v1_app_20260408043718-20260408T043718Z\published\carousel\slide_01.jpg`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase4_live_verify_20260408113528\artifacts\demo_shop_2\mobile_v1_app_20260408043718-20260408T043718Z\session_metadata.json`

Observed `session_artifacts` rows:

- `intake_bundle | generated/intake_bundle.json`
- `manifest | published/manifest.json`
- `shorts_video | published/shorts/preview.mp4`
- `blog_html | published/blog/index.html`
- `thread_text | published/threads/thread.txt`
- `carousel_image | published/carousel/slide_01.jpg`

Observed preview decision messages:

- `system | status | 미리보기가 준비되었어요. 확인 후 승인하거나 수정 요청을 남겨주세요.`
- `customer | status | 미리보기 수정 요청을 남겼어요.`
- `customer | status | 미리보기를 승인했어요.`

---

## 5. Acceptance Criteria Check

### A. Waiting State

- [x] `/app/session/:sessionId` renders a real waiting state for `awaiting_production`
- [x] the waiting state is Korean and mobile-readable
- [x] the workspace can reopen a waiting session

### B. Preview Rendering

- [x] `/app/session/:sessionId` renders a real preview state for `awaiting_approval`
- [x] `/app/session/:sessionId` renders a real preview state for `revision_requested`
- [x] preview rendering is driven by the existing uploaded manifest and published assets
- [x] uploaded preview assets are visibly rendered in the app shell

### C. Approval And Revision

- [x] app-side revision action changes the session stage to `revision_requested`
- [x] app-side approve action changes the session stage to `approved`
- [x] after each action, the customer remains in the app-side route surface
- [x] session messages and chat-log style status history continue to record the decision

### D. Completion State

- [x] `/app/session/:sessionId` renders a real completion state for `approved`
- [x] the completion state clearly shows the review flow is complete
- [x] the workspace reflects the approved session state

### E. App Shell Continuity

- [x] the normal authenticated customer flow remains under `/app`
- [x] the app-side flow does not require `/s/<customer_token>/preview` for normal usage
- [x] the app-side flow does not require `/s/<customer_token>/complete` for normal usage

### F. Mobile UX And Language

- [x] all customer-facing Phase 4 UI introduced in this phase is Korean
- [x] preview sections and action controls remain usable on mobile widths
- [x] the waiting, preview, revision, and completion states each show one clear next action

---

## 6. Remaining Gaps

These items remain intentionally deferred:

- final download-package delivery inside the app shell
- bounded regeneration UX
- voice recording and SSE transcription work
- real auth, billing, and ownership enforcement

---

## 7. Final Result

Mobile_V1 Phase 4 is verified.

The repository now supports:

- app-side waiting state for `awaiting_production`
- app-side preview rendering for uploaded manifest-driven assets
- app-side revision and approval actions without leaving `/app`
- app-side completion state for `approved`
- workspace visibility for waiting, preview, revision, and approved sessions
