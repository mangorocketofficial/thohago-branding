# Desktop Phase 9 Verification

> Status: Verified  
> Date: 2026-04-07  
> Contract: [desktop_phase9_contract.md](./desktop_phase9_contract.md)

Use this document only after implementation begins. Record evidence against the active Desktop Phase 9 contract. Do not use this document to change scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Node: `v22.18.0`
- pnpm: `10.30.1`
- Python: `Python 3.12.8`
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- Desktop runtime data directory: `C:\Users\User\Desktop\Thohago_branding\apps\desktop\.thohago-desktop\phase9-proof`

## Automated Test Evidence

- Command: `pnpm desktop:test`
- Result: Pass (10 tests)
- Notes:
  - preserved phases 1-8 verification coverage
  - added live publish execution coverage for:
    - explicit `executionMode=live`
    - archived publish result artifacts
    - persisted provider error state
    - payload wiring from saved desktop credentials into sidecar publish calls

## Static Validation Evidence

- Command:
  - `python -m py_compile sidecar/dispatcher.py apps/desktop/scripts/verify-live-publish-execution.py`
- Result:
  - Pass
- Command:
  - `pnpm --filter @thohago/desktop exec tsc --noEmit`
- Result:
  - Pass

## Smoke Verification Evidence

- Clean command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase9'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase9-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase9-proof-report.json'; pnpm desktop:smoke`
- Clean result:
  - Pass
- Restart command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase9-restart'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase9-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase9-proof-restart-report.json'; pnpm desktop:smoke`
- Restart result:
  - Pass
- Notes:
  - clean smoke generated a fresh project, saved live credential placeholders, executed four live publish attempts, and opened `#/project/:id/publish`
  - clean smoke report recorded:
    - `publishRunCount=4`
    - `latestPublishModes.blog=live`
    - `latestPublishModes.carousel=live`
    - `latestPublishModes.video=live`
    - `latestPublishModes.thread=live`
    - `latestPublishStatuses.blog=unsupported`
    - `latestPublishStatuses.carousel=missing`
    - `latestPublishStatuses.video=unsupported`
    - `latestPublishStatuses.thread=missing`
  - restart smoke reopened the same publish route against the same data directory and preserved the same execution modes and statuses

## Direct Live Execution Evidence

- Command:
  - `python apps/desktop/scripts/verify-live-publish-execution.py`
- Result:
  - Pass as an operator verification command
  - the command attempted the live publish code path without requiring a successful external post
- Observed provider outcomes:
  - Instagram carousel live:
    - `status=error`
    - Meta Graph returned an expired-session error
    - the returned message explicitly states the session expired on `Tuesday, 31-Mar-26 05:00:00 PDT`
  - Threads live:
    - `status=missing`
    - current local Threads credentials are incomplete
  - Naver live:
    - `status=unsupported`
    - live Naver Blog publishing is not implemented in this phase
  - Instagram Reels live:
    - `status=unsupported`
    - live Reels upload is not implemented in this phase

## Publish Route and Persistence Verification

- Publish route:
  - `#/project/phase2-smoke-project-20260407100556/publish`
- Mode distinction evidence:
  - publish route exposes both `Mock Publish` and `Live Publish` actions per content card
  - publish run history now records `executionMode`
- Live execution persistence evidence:
  - clean smoke persisted four archived live publish result artifacts
  - restart smoke preserved:
    - `publishRunCount=4`
    - live mode visibility for all four content types
    - latest live provider statuses
- Content/project status evidence:
  - unsupported or missing live attempts did not incorrectly mark content as published
  - clean and restart smoke both recorded:
    - `projectStatus=content_generated`
    - `publishedContentCount=0`

## Produced Artifacts

- Smoke evidence:
  - [phase9-proof-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-proof-report.json)
  - [phase9-proof-restart-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-proof-restart-report.json)
- Direct live execution evidence:
  - [phase9-live-execution-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-live-execution-report.json)
  - [verify-live-publish-execution.py](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/scripts/verify-live-publish-execution.py)
- Runtime persistence evidence:
  - [thohago-desktop.sqlite](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-proof/thohago-desktop.sqlite)
- Archived live publish run artifacts:
  - [blog live unsupported](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-proof/projects/phase2-smoke-project-20260407100556/published/history/blog/20260407100556559_live_unsupported.json)
  - [carousel live missing](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-proof/projects/phase2-smoke-project-20260407100556/published/history/carousel/20260407100556573_live_missing.json)
  - [video live unsupported](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-proof/projects/phase2-smoke-project-20260407100556/published/history/video/20260407100556587_live_unsupported.json)
  - [thread live missing](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase9-proof/projects/phase2-smoke-project-20260407100556/published/history/thread/20260407100556599_live_missing.json)

## Acceptance Checklist

### A. Execution Mode

- [x] publish actions explicitly distinguish `mock` and `live`
- [x] `publish_runs` persist execution mode

### B. Live Execution

- [x] carousel live publish attempts execute through the real Instagram publish path
- [x] thread live publish attempts execute through the real Threads publish path
- [x] unsupported live targets return structured `unsupported` results

### C. Persistence

- [x] live publish attempts persist archived artifacts and DB history
- [x] restart preserves live publish history and execution mode visibility

### D. Automated Verification

- [x] `pnpm desktop:test` covers live execution persistence and payload wiring
- [x] clean `pnpm desktop:smoke` succeeds
- [x] restart `pnpm desktop:smoke` confirms persisted live publish state
- [x] direct live execution command records actual provider outcomes

## Open Issues

- Electron dev runtime still emits the standard CSP warning while running from the Vite dev server. This does not block Phase 9 verification.
- Live Naver Blog publishing remains unsupported in this desktop track.
- Live Instagram Reels upload remains unsupported in this desktop track.
- Threads live execution currently uses the existing single publish shape of `ThreadsPublisher`; a full multi-reply chain is still out of scope.
- The current local Instagram token is expired, so direct live execution records a real provider error rather than a successful post.

## Final Result

- Contract status: Verified
- Code status: Implemented and locally verified
- Verified by: Codex
- Verified on: 2026-04-07
