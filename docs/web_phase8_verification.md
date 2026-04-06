# Web Phase 8 Verification

> Status: Verified  
> Date: 2026-04-01  
> Contract: [web_phase8_contract.md](./web_phase8_contract.md)

Use this document to record evidence against the active Web Phase 8 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Event verification script: [web_phase8_manual_verify.py](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase8_manual_verify.py)
- STT mode used in verification: `stub`

## Automated Test Evidence

### Web Phase 8 targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase8.py' -v`
- Result: Pass (4 tests)
- Coverage:
  - transcript events are stored durably in SQLite
  - SSE replay after `Last-Event-ID`
  - preview upload publishes durable `preview_ready`
  - waiting page contains live preview-ready listener

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (44 tests)
- Purpose: verified that durable SSE hardening did not regress earlier web phases or replay/Telegram behavior

## Scripted Verification Flow

### Command

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\Thohago_branding\src'
python runs/_web_runtime/web_phase8_manual_verify.py
```

### Result

- Pass

### Output Summary

- `stored_event_count=2`
- `stored_event_1=transcribing`
- `stored_event_2=transcript_ready`
- `replay_event_id=2`
- `replay_event_type=transcript_ready`
- `preview_event_type=preview_ready`
- `waiting_has_preview_listener=True`

## Acceptance Checklist

### A. Durable Event Storage

- [x] published session events are written to SQLite
- [x] stored events can be queried by session and ordered id

### B. Live SSE Stream

- [x] live SSE stream still delivers events to connected clients
- [x] SSE frames include `id:` fields

### C. Replay On Reconnect

- [x] reconnect with `Last-Event-ID` replays newer missed events
- [x] replay preserves event ordering

### D. Preview-Ready Event

- [x] preview upload publishes durable `preview_ready`
- [x] waiting-session clients can receive `preview_ready` via SSE/replay

### E. Waiting Page UX

- [x] waiting page still renders normally without SSE
- [x] waiting page contains live redirect wiring for `preview_ready`

## Remaining Gaps

- No gaps against the Web Phase 8 contract
- Cross-process pub/sub and retention cleanup remain intentionally out of scope

## Final Result

- Contract status: Verified
- Verified by: Codex
- Verified on: 2026-04-01
