# Web Phase 10 Verification

> Status: Blocked  
> Date: 2026-04-02  
> Contract: [web_phase10_contract.md](./web_phase10_contract.md)

Use this document to record evidence against the active Web Phase 10 contract. Do not use it to redefine scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Python: 3.12.x local interpreter
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- PYTHONPATH used for live verification: `C:\Users\User\Desktop\Thohago_branding\src`
- Live server: `https://34.180.80.140.sslip.io`
- Live verification script: [web_phase10_live_verify.py](/C:/Users/User/Desktop/Thohago_branding/runs/_web_runtime/web_phase10_live_verify.py)

## Automated Test Evidence

### Targeted tests

- Command: `python -m unittest discover -s tests -p 'test_web_phase10.py' -v`
- Result: Pass (4 tests)
- Coverage:
  - `THOHAGO_DEFAULT_INTERVIEW_ENGINE=claude` selects Anthropic planning even when Groq is present
  - `THOHAGO_DEFAULT_INTERVIEW_ENGINE=heuristic` is respected even when API keys are present
  - explicit `claude` without a key fails clearly
  - web flow can use Anthropic planning while runtime transcriber remains Groq under mocked planning calls

### Full regression suite

- Command: `python -m unittest discover -s tests -v`
- Result: Pass (55 tests)
- Purpose: confirmed the engine selection refactor did not regress previous web phases or replay/Telegram behavior

## Implementation Evidence

- Web planning engine selection now respects `THOHAGO_DEFAULT_INTERVIEW_ENGINE`.
- Explicit values supported in web runtime:
  - `claude` / `anthropic`
  - `groq`
  - `openai`
  - `heuristic`
  - `auto`
- STT remains separately resolved through `THOHAGO_WEB_STT_MODE`.
- Startup now validates explicit interview-engine configuration.

## Live Server Attempt

### Applied server config

- `THOHAGO_DEFAULT_INTERVIEW_ENGINE=claude`
- `CLAUDE_API_KEY=<present>`
- `THOHAGO_WEB_STT_MODE=groq`

### Observed result

- Live upload finalize failed with `500 Internal Server Error`
- Root cause from server-side Anthropic probe:

```text
http_error=400
{"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits."},"request_id":"req_011CZeRBzWXQ8yZikJkwYHSU"}
```

### Operational decision

- To avoid leaving the public MVP web flow broken, the live server was reverted to:
  - `THOHAGO_DEFAULT_INTERVIEW_ENGINE=groq`
- After revert, live customer flow was rechecked and works again using the existing Groq planner path.

## Acceptance Checklist

### A. Config Application

- [x] `THOHAGO_DEFAULT_INTERVIEW_ENGINE` is applied by the web runtime
- [x] explicit `claude` selection uses Anthropic engine when a key is present locally
- [x] explicit `groq`, `openai`, and `heuristic` selections are supported

### B. Planning vs STT Separation

- [x] web planning engine selection is independent from STT selection
- [x] local/test runtime can use Claude planning while STT remains Groq

### C. Planning Flow

- [x] `media_preflight.json` uses the selected planning engine in automated verification
- [x] turn1 question generation uses the selected planning engine in automated verification
- [x] turn2 planning uses the selected planning engine in automated verification

### D. Live Server

- [ ] live server currently uses Claude for planning
- [x] live server keeps Groq for STT capability
- [ ] live verification currently shows Anthropic planning mode on the deployed public flow

## Blocker

- Anthropic/Claude API key on the current environment is valid syntactically but cannot be used because the Anthropic account has insufficient credit balance.
- Until Anthropic billing is topped up, the public web server cannot be safely kept on `THOHAGO_DEFAULT_INTERVIEW_ENGINE=claude`.

## Final Result

- Contract status: Blocked by external billing dependency
- Code status: Implemented and locally verified
- Live status: Reverted to Groq planning to keep the public MVP usable
