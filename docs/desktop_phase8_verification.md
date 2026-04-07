# Desktop Phase 8 Verification

> Status: Verified  
> Date: 2026-04-07  
> Contract: [desktop_phase8_contract.md](./desktop_phase8_contract.md)

Use this document only after implementation begins. Record evidence against the active Desktop Phase 8 contract. Do not use this document to change scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Node: `v22.18.0`
- pnpm: `10.30.1`
- Python: `Python 3.12.8`
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- Desktop runtime data directory: `C:\Users\User\Desktop\Thohago_branding\apps\desktop\.thohago-desktop\phase8-proof`

## Automated Test Evidence

- Command: `pnpm desktop:test`
- Result: Pass (9 tests)
- Notes:
  - preserved phases 1-7 verification coverage
  - added live credential persistence coverage for:
    - encrypted credential storage
    - persisted credential presence
    - persisted provider validation results
    - restart-safe validation state recovery

## Smoke Verification Evidence

- Clean command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase8'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase8-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase8-proof-report.json'; pnpm desktop:smoke`
- Clean result:
  - Pass
- Restart command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase8-restart'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase8-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase8-proof-restart-report.json'; pnpm desktop:smoke`
- Restart result:
  - Pass
- Notes:
  - clean smoke completed the full local project cycle through publish, saved live credential placeholders, ran provider validation, and opened `#/project/:id/publish`
  - clean smoke report recorded:
    - `instagramCredentialPresent=true`
    - `threadsCredentialPresent=true`
    - `instagramValidation=missing`
    - `threadsValidation=missing`
    - `naverValidation=unsupported`
  - restart smoke reopened the same publish route against the same data directory and preserved the identical credential and validation state

## Direct Live Validation Evidence

- Command:
  - `python apps/desktop/scripts/verify-live-publish-credentials.py`
- Result:
  - Pass as an operator verification command
  - current local credential status was surfaced without attempting a live publish
- Observed provider outcomes:
  - Instagram:
    - `status=error`
    - Meta Graph returned an expired-session error
    - the error explicitly states the session expired on `Tuesday, 31-Mar-26 05:00:00 PDT`
  - Threads:
    - `status=missing`
    - current local Threads credentials are incomplete
  - Naver:
    - `status=unsupported`
    - desktop notes can be stored, but live Naver publishing is still not implemented in this phase

## Credential and Publish Route Verification

- Publish route:
  - `#/project/phase2-smoke-project-20260407095017/publish`
- Saved placeholder credential evidence:
  - Instagram access token presence persisted
  - Instagram business account id persisted as `17841400000000000`
  - Threads access token presence persisted
  - Threads user id persisted as `1234567890`
  - Naver live note persisted and survived restart
- Validation persistence evidence:
  - Instagram validation persisted as `missing` in smoke
  - Threads validation persisted as `missing` in smoke
  - Naver validation persisted as `unsupported` in smoke
  - direct live validation separately showed real local Instagram failure state as `error`

## Produced Artifacts

- Smoke evidence:
  - [phase8-proof-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-proof-report.json)
  - [phase8-proof-restart-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-proof-restart-report.json)
- Direct validation evidence:
  - [phase8-live-validation-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-live-validation-report.json)
  - [verify-live-publish-credentials.py](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/scripts/verify-live-publish-credentials.py)
- Runtime persistence evidence:
  - [thohago-desktop.sqlite](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-proof/thohago-desktop.sqlite)
- Phase 7 publish artifacts still preserved under the phase8 smoke project:
  - [blog_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-proof/projects/phase2-smoke-project-20260407095017/published/blog_publish_result.json)
  - [carousel_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-proof/projects/phase2-smoke-project-20260407095017/published/carousel_publish_result.json)
  - [video_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-proof/projects/phase2-smoke-project-20260407095017/published/video_publish_result.json)
  - [thread_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase8-proof/projects/phase2-smoke-project-20260407095017/published/thread_publish_result.json)

## Acceptance Checklist

### A. Credential Persistence

- [x] publish route allows saving live publishing credentials
- [x] saved credential presence is reflected in the UI
- [x] saved credential presence survives restart

### B. Provider Validation

- [x] Instagram validation executes and returns a structured result
- [x] Threads validation executes and returns a structured result
- [x] Naver validation executes and returns a structured result
- [x] validation results persist and survive restart

### C. Publish Route UX

- [x] publish route shows meaningful credential state
- [x] publish route shows meaningful validation state
- [x] mock publish actions remain available

### D. Automated Verification

- [x] `pnpm desktop:test` covers credential persistence and validation behavior
- [x] clean `pnpm desktop:smoke` succeeds
- [x] restart `pnpm desktop:smoke` confirms persisted credential state

## Open Issues

- Electron dev runtime still emits the standard CSP warning while running from the Vite dev server. This does not block Phase 8 verification.
- Live publishing actions on the publish route remain mock. This phase integrates credential storage and live-provider validation readiness, not guaranteed real posting.
- Direct local Instagram validation currently fails because the configured Meta token is expired. The app now surfaces that failure explicitly instead of hiding it.

## Final Result

- Contract status: Verified
- Code status: Implemented and locally verified
- Verified by: Codex
- Verified on: 2026-04-07
