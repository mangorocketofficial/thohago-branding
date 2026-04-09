# Mobile_V1 Phase 3 Verification

> Status: Verified  
> Date: 2026-04-08  
> Contract: [mobile_v1_phase3_contract.md](./mobile_v1_phase3_contract.md)

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
  - existing upload/interview pipeline with heuristic interview engine for verification

---

## 2. Commands Executed

### 2.1 Mobile_V1 Phase 3 Test Suite

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase3.py"
```

Result:

- Pass
- `Ran 3 tests`
- `OK`

### 2.2 Mobile_V1 Phase 2 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase2.py"
```

Result:

- Pass
- `Ran 5 tests`
- `OK`

### 2.3 Mobile_V1 Phase 1 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_mobile_v1_phase1.py"
```

Result:

- Pass
- `Ran 4 tests`
- `OK`

### 2.4 Web Phase 3 Regression Check

Command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_web_phase3.py"
```

Result:

- Pass
- `Ran 5 tests`
- `OK`

### 2.5 Local App Startup And Live Route Verification

Startup method:

- started local uvicorn server on `127.0.0.1:8013`
- used isolated verification runtime paths under:
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts`
  - `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\runtime\web.sqlite3`
- forced `THOHAGO_DEFAULT_INTERVIEW_ENGINE=heuristic` for deterministic local verification

Effective startup command:

```powershell
$env:PYTHONPATH='src'
python -m uvicorn thohago.web.app:create_app --factory --host 127.0.0.1 --port 8013
```

Live verification method:

- signed in through the stub app route
- completed onboarding
- created a real app-side session
- uploaded one real JPG and one real MP4 from the checked-in sample assets
- finalized uploads from `/app/session/:sessionId`
- submitted and confirmed Turn 1, Turn 2, and Turn 3 text answers
- confirmed the session stayed under `/app/session/:sessionId`
- reloaded `/app/session/:sessionId` and `/app`
- confirmed artifact files were written for the completed session

Observed live route results:

```json
{
  "session_id": "mobile_v1_app_20260408033220-20260408T033220Z",
  "sign_in_status": 303,
  "onboarding_status": 303,
  "create_status": 303,
  "upload_status": 200,
  "upload_has_photo": true,
  "upload_has_video": true,
  "finalize_status": 303,
  "finalize_location": "/app/session/mobile_v1_app_20260408033220-20260408T033220Z",
  "turn1_submit_status": 303,
  "turn1_confirm_status": 303,
  "turn2_submit_status": 303,
  "turn2_confirm_status": 303,
  "turn3_submit_status": 303,
  "turn3_confirm_status": 303,
  "session_page_status": 200,
  "workspace_status": 200,
  "session_stage": "awaiting_production",
  "interview_completed_at_present": true,
  "session_page_has_waiting_label": true,
  "session_page_has_stage_key": true,
  "workspace_has_session": true,
  "message_count": 9,
  "artifact_count": 1,
  "artifacts_exist": {
    "preflight": true,
    "turn1_question": true,
    "turn2_planner": true,
    "turn3_planner": true,
    "turn1_transcript": true,
    "turn2_transcript": true,
    "turn3_transcript": true,
    "intake_bundle": true,
    "session_metadata": true
  }
}
```

Observed workspace HTML snippet for the verified session:

```html
<a href="/app/session/mobile_v1_app_20260408033220-20260408T033220Z" class="session-card">
  <strong>mobile_v1_app_20260408033220-20260408T033220Z</strong>
  <span class="stage-chip">제작 대기</span>
</a>
```

---

## 3. Implemented Outputs

### 3.1 App-Side Session Routing And State Handling

- app-side finalize and interview routes:
  - [product.py](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/routes/product.py)

### 3.2 Updated App Session Template

- app-side upload, interview, and waiting UI:
  - [app_session.html](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/templates/app_session.html)

### 3.3 Styling Updates

- button row, question card, and app-side composer updates:
  - [app.css](/C:/Users/User/Desktop/Thohago_branding_mobile/src/thohago/web/static/app.css)

### 3.4 Automated Tests

- Phase 3 test coverage:
  - [test_mobile_v1_phase3.py](/C:/Users/User/Desktop/Thohago_branding_mobile/tests/test_mobile_v1_phase3.py)

---

## 4. Artifact Evidence

Verified session artifact root:

- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z`

Verified artifact files:

- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\generated\media_preflight.json`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\planners\turn1_question.txt`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\planners\turn2_planner.json`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\planners\turn3_planner.json`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\transcripts\turn1_transcript.txt`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\transcripts\turn2_transcript.txt`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\transcripts\turn3_transcript.txt`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\generated\intake_bundle.json`
- `C:\Users\User\Desktop\Thohago_branding_mobile\runs\phase3_live_verify_20260408102830\artifacts\demo_shop_2\mobile_v1_app_20260408033220-20260408T033220Z\session_metadata.json`

---

## 5. Acceptance Criteria Check

### A. Upload Finalization

- [x] the app session page exposes a real finalize/start-interview action
- [x] finalization requires at least one uploaded photo
- [x] finalization writes preflight and Turn 1 question artifacts
- [x] finalization changes the session stage to `awaiting_turn1_answer`
- [x] the customer remains in the app-side route surface after finalization

### B. Interview Rendering

- [x] the app-side session route renders the current question for `awaiting_turn*`
- [x] the app-side session route renders pending-answer confirmation UI for `confirming_turn*`
- [x] prior interview conversation messages are visible in the app-side session thread
- [x] the UI shows clear turn context in Korean

### C. Text Submission And Retry

- [x] app-side text submission stores `pending_answer`
- [x] submission changes the session stage to `confirming_turnN`
- [x] submitting replacement text while already in `confirming_turnN` overwrites the pending answer
- [x] retry clears `pending_answer`
- [x] retry returns the session to `awaiting_turnN_answer`

### D. Turn Progression And Persistence

- [x] Turn 1 confirm writes transcript artifacts and generates Turn 2 planner/question artifacts
- [x] Turn 1 confirm changes the session stage to `awaiting_turn2_answer`
- [x] Turn 2 confirm writes transcript artifacts and generates Turn 3 planner/question artifacts
- [x] Turn 2 confirm changes the session stage to `awaiting_turn3_answer`
- [x] Turn 3 confirm writes transcript artifacts and exports `generated/intake_bundle.json`
- [x] Turn 3 confirm changes the session stage to `awaiting_production`
- [x] `interview_completed_at` is recorded when Turn 3 is confirmed
- [x] `session_messages` and chat-log artifacts continue to record the conversation progression

### E. App Shell Continuity

- [x] the normal authenticated customer flow remains under `/app`
- [x] the workspace can reopen a session after interview progress or completion
- [x] the app-side flow does not redirect the customer into `/s/<customer_token>/interview` or `/s/<customer_token>/waiting` for normal usage

### F. Mobile UX And Language

- [x] finalize, interview, and waiting UI introduced in this phase are Korean
- [x] the app-side interview UI remains usable on mobile widths
- [x] the post-interview waiting state clearly says that generation is the next phase rather than falsely implying completion

---

## 6. Remaining Gaps

These items remain intentionally deferred:

- voice recording flow in the app-side interview shell
- app-side SSE/live transcription UI
- generation, preview, and download package flows after `awaiting_production`
- real auth, billing, and ownership enforcement

---

## 7. Final Result

Mobile_V1 Phase 3 is verified.

The repository now supports:

- app-side upload finalization from `/app/session/:sessionId`
- app-side 3-turn text interview inside the authenticated mobile shell
- confirm/retry/replace behavior without leaving `/app`
- transcript, planner, and intake bundle persistence for app-created sessions
- production-waiting state visibility from both the app session page and the workspace
