# Mobile_V1 Phase 6 Verification

> Status: Verified  
> Date: 2026-04-08  
> Contract: [mobile_v1_phase6_contract.md](./mobile_v1_phase6_contract.md)

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
  - app-side session workflow states from prior mobile phases

---

## 2. Commands Executed

### 2.1 Mobile_V1 Phase 6 Test Suite

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase6.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.2 Mobile_V1 Phase 1 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase1.py"
```

Result:

- Pass
- `Ran 4 tests`
- `OK`

### 2.3 Mobile_V1 Phase 2 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase2.py"
```

Result:

- Pass
- `Ran 5 tests`
- `OK`

### 2.4 Mobile_V1 Phase 3 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase3.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.5 Mobile_V1 Phase 4 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase4.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.6 Mobile_V1 Phase 5 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase5.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.7 Local App Startup And Live Route Verification

Startup method:

- started local uvicorn server on `127.0.0.1:8017`
- used isolated verification runtime paths under:
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase6_live_verify_20260408142836\artifacts`
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase6_live_verify_20260408142836\runtime\web.sqlite3`
- forced `THOHAGO_DEFAULT_INTERVIEW_ENGINE=heuristic` for deterministic UI verification

Effective startup command:

```powershell
$env:PYTHONPATH='src'
python -m uvicorn thohago.web.app:create_app --factory --host 127.0.0.1 --port 8017
```

Live verification method:

- signed in through the stub app route
- confirmed direct redirect into `/app`
- confirmed `/app/onboarding` redirects back to `/app`
- created a new session from the chat-shell UI
- opened the new `/app/session/:sessionId`
- confirmed sidebar, mobile menu button, active session styling, and upload state all render inside the same shell structure

Observed live route results:

```json
{
  "sign_in_status": 303,
  "sign_in_location": "/app",
  "workspace_status": 200,
  "onboarding_status": 303,
  "onboarding_location": "/app",
  "create_status": 303,
  "session_id": "mobile_v1_app_20260408072954-20260408T072954Z",
  "session_status": 200,
  "workspace_has_app_frame": true,
  "workspace_has_sidebar": true,
  "workspace_has_menu_button": true,
  "session_has_sidebar": true,
  "session_has_menu_button": true,
  "session_has_active_session": true,
  "session_has_drawer_backdrop": true
}
```

Observed `/app` shell snippet:

```html
<div class="app-frame" data-app-frame>
  <aside class="app-sidebar" id="app-sidebar" aria-label="작업 세션 목록">
    <button type="submit" class="secondary-button">새 작업</button>
  </aside>
  <section class="app-main">
    <button type="button" class="icon-button app-menu-button" data-sidebar-toggle>
    <h1>고객님님의 작업 공간</h1>
    <button type="submit">새 작업 시작</button>
  </section>
</div>
```

Observed `/app/session/:sessionId` shell snippet:

```html
<div class="app-frame" data-app-frame>
  <aside class="app-sidebar" id="app-sidebar" aria-label="작업 세션 목록">
    <a href="/app/session/mobile_v1_app_20260408072908-20260408T072908Z" class="app-session-link is-active">
      <strong>세션 04-08 07:29</strong>
    </a>
  </aside>
  <section class="app-main">
    <button type="button" class="icon-button app-menu-button" data-sidebar-toggle>
    <h1>새 작업을 준비할게요</h1>
  </section>
</div>
```

---

## 3. Implemented Outputs

### 3.1 Routing Changes

- direct sign-in and onboarding compatibility redirect:
  - [product.py](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/routes/product.py)

### 3.2 Shared App-Shell Layout

- base page/card class hooks:
  - [base.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/base.html)
- sidebar partial:
  - [app_sidebar.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/partials/app_sidebar.html)
- workspace shell:
  - [app_workspace.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/app_workspace.html)
- session shell:
  - [app_session.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/app_session.html)

### 3.3 Supporting UI Updates

- marketing CTA updates away from onboarding:
  - [landing.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/landing.html)
  - [pricing.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/pricing.html)
- app-shell, sidebar, and mobile drawer styling:
  - [app.css](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/static/app.css)

### 3.4 Automated Tests

- Phase 6 UI shell coverage:
  - [test_mobile_v1_phase6.py](/C:/Users/User/Desktop/Thohago_branding_mobile/tests/test_mobile_v1_phase6.py)
- updated phase 1 expectations for direct workspace entry:
  - [test_mobile_v1_phase1.py](/C:/Users/User/Desktop/Thohago_branding_mobile/tests/test_mobile_v1_phase1.py)

---

## 4. Acceptance Criteria Check

### A. Sign-In Flow

- [x] sign-in no longer lands on a standalone onboarding page
- [x] signed-in customers land directly in `/app`
- [x] `/app` is accessible without the old onboarding gate

### B. Unified Shell

- [x] `/app` renders a real chat-style app shell
- [x] `/app/session/:sessionId` renders inside the same shell structure
- [x] the shell looks like one application rather than separate page families

### C. Sidebar Navigation

- [x] desktop widths show a left session sidebar
- [x] the sidebar includes recent sessions and a new-session action
- [x] the active session is visually identifiable

### D. Mobile Navigation

- [x] narrow widths expose the session list through a toggleable drawer/panel
- [x] the chat pane remains usable on mobile widths

### E. Workflow Compatibility

- [x] upload, interview, preview, and approved delivery states still render within the new shell
- [x] existing session routes still work after the UI change

### F. Language And UX

- [x] customer-facing UI introduced in this phase remains Korean
- [x] the shell keeps a clear next action for empty state and active sessions

---

## 5. Remaining Gaps

These items remain intentionally deferred:

- content-type selection and generation orchestration from the app shell
- bounded regeneration UX
- usage billing or credit deduction
- voice recording and SSE transcription work
- real auth, billing, and ownership enforcement

---

## 6. Final Result

Mobile_V1 Phase 6 is verified.

The repository now supports:

- direct sign-in into the main app shell
- a unified `/app` and `/app/session/:sessionId` chat-style UI
- persistent session navigation in a left sidebar
- a mobile drawer-style session navigation trigger
- preservation of existing mobile workflow states inside the new shell
