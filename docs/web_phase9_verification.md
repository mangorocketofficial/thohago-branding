# Web Phase 9 Verification

> Status: Verified  
> Date: 2026-04-02  
> Contract: [web_phase9_contract.md](./web_phase9_contract.md)

Use this document to record evidence against the active Web Phase 9 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for live verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Live server: `https://34.180.80.140.sslip.io`
- Live verification script: [web_phase9_manual_verify.py](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase9_manual_verify.py)

## Automated Test Evidence

### Web Phase 9 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase9.py' -v`
- Result: Pass (5 tests)
- Coverage:
  - interview page chat layout and Korean controls
  - waiting page chat layout and Korean copy
  - preview page chat layout and Korean approval actions
  - complete page chat layout after approval
  - upload page remains form-first

### Affected regression tests

- Commands:
  - `python -m unittest discover -s tests -p 'test_web_phase3.py' -v`
  - `python -m unittest discover -s tests -p 'test_web_phase4.py' -v`
  - `python -m unittest discover -s tests -p 'test_web_phase5.py' -v`
  - `python -m unittest discover -s tests -p 'test_web_phase8.py' -v`
- Result: Pass
- Purpose: confirmed chat-style UI conversion did not break interview progression, waiting SSE redirect, preview upload, or approval flow

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (50 tests)
- Purpose: verified that customer UI conversion did not regress previous web phases or replay/Telegram behavior

## Live Server Verification

### Deployment

- Deploy artifact: `runs/_deploy_tmp/thohago-phase9-ui.tgz`
- Deployment path: `/opt/thohago/app/src`
- Service restart result: `thohago-web active`

### Command

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
python runs/_web_runtime/web_phase9_manual_verify.py
```

### Result

- Pass

### Output Summary

- `session_key=phase9_live_verify_1775101531`
- `session_id=phase9_live_verify_1775101531-20260402T034518Z`
- `customer_url=https://34.180.80.140.sslip.io/s/6gJ5n_kJcsbOCJz-rvDi97YK-swMTSgI`
- `upload_ui=ok`
- `interview_chat_ui=ok`
- `waiting_chat_ui=ok`
- `preview_chat_ui=ok`
- `complete_chat_ui=ok`

## Acceptance Checklist

### A. Interview Conversation UI

- [x] interview page renders as a conversation thread
- [x] bot questions and confirmed customer answers render as chat bubbles
- [x] retry, edit, and confirm actions still work

### B. Waiting Conversation UI

- [x] waiting page renders in the same conversation shell
- [x] timed refresh and `preview_ready` redirect still work

### C. Preview Conversation UI

- [x] preview page renders in the same conversation shell
- [x] approval and revision actions remain functional
- [x] preview assets still render correctly

### D. Complete Conversation UI

- [x] complete page renders in the same conversation shell
- [x] approved state is clear in Korean

### E. Regression Safety

- [x] upload remains form-first
- [x] interview progression still works
- [x] sync preview upload still works
- [x] approval flow still works

## Remaining Gaps

- No gaps against the Web Phase 9 contract
- Admin pages remain English and utility-style by design; this was out of scope

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-02
