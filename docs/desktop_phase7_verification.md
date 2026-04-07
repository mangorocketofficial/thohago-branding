# Desktop Phase 7 Verification

> Status: Verified  
> Date: 2026-04-07  
> Contract: [desktop_phase7_contract.md](./desktop_phase7_contract.md)

Use this document only after implementation begins. Record evidence against the active Desktop Phase 7 contract. Do not use this document to change scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Node: `v22.18.0`
- pnpm: `10.30.1`
- Python: `Python 3.12.8`
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- Desktop runtime data directory: `C:\Users\User\Desktop\Thohago_branding\apps\desktop\.thohago-desktop\phase7-proof`

## Automated Test Evidence

- Command: `pnpm desktop:test`
- Result: Pass (8 tests)
- Notes:
  - preserved phases 1-6 verification coverage
  - added mock publishing verification covering:
    - four mock publish actions
    - persisted publish results
    - project-wide `published` status after all four succeed

## Smoke Verification Evidence

- Clean command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase7'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase7-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase7-proof-report.json'; pnpm desktop:smoke`
- Clean result:
  - Pass
- Restart command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase7-restart'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase7-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase7-proof-restart-report.json'; pnpm desktop:smoke`
- Restart result:
  - Pass
- Notes:
  - clean smoke completed the full local project cycle through publish and opened the real publish route with `publishedContentCount=4`
  - restart smoke reopened the publish route against the same data directory and preserved the `published` project state

## Publish Verification

- Project id: `phase2-smoke-project-20260407091320`
- Blog publish evidence:
  - platform: `naver_blog`
  - permalink: `mock://naver/phase2-smoke-project-20260407091320`
- Carousel publish evidence:
  - platform: `instagram_carousel`
  - permalink: `mock://instagram/carousel/phase2-smoke-project-20260407091320`
- Video publish evidence:
  - platform: `instagram_reels`
  - permalink: `mock://instagram/reels/phase2-smoke-project-20260407091320`
- Thread publish evidence:
  - platform: `threads`
  - permalink: `mock://threads/phase2-smoke-project-20260407091320`
- Project publish-complete evidence:
  - clean smoke report recorded `projectStatus=published`
  - clean and restart smoke reports both recorded `publishedContentCount=4`
  - DB inspection showed all four `content_specs.status = 'published'`

## Produced Artifacts

- `published/blog_publish_result.json`:
  - [blog_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase7-proof/projects/phase2-smoke-project-20260407091320/published/blog_publish_result.json)
- `published/carousel_publish_result.json`:
  - [carousel_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase7-proof/projects/phase2-smoke-project-20260407091320/published/carousel_publish_result.json)
- `published/video_publish_result.json`:
  - [video_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase7-proof/projects/phase2-smoke-project-20260407091320/published/video_publish_result.json)
- `published/thread_publish_result.json`:
  - [thread_publish_result.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase7-proof/projects/phase2-smoke-project-20260407091320/published/thread_publish_result.json)
- Other evidence:
  - [phase7-proof-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase7-proof-report.json)
  - [phase7-proof-restart-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase7-proof-restart-report.json)
  - DB inspection showed 4 persisted `publish_runs` rows with stable artifact paths and mock permalinks

## Acceptance Checklist

### A. Publish Route

- [x] publish route is real
- [x] publish route renders meaningful status

### B. Mock Publish Actions

- [x] blog mock publish succeeds
- [x] carousel mock publish succeeds
- [x] video mock publish succeeds
- [x] thread mock publish succeeds

### C. Persistence

- [x] publish runs persist in DB
- [x] publish artifacts persist on disk
- [x] publish state survives restart

### D. Project/Content Status

- [x] content items reflect published status
- [x] project reflects publish-complete state when all four succeed

### E. Automated Verification

- [x] `pnpm desktop:test` covers publish persistence behavior
- [x] clean `pnpm desktop:smoke` succeeds
- [x] restart `pnpm desktop:smoke` confirms persistence

## Open Issues

- Electron dev runtime still emits the standard CSP warning while running from the Vite dev server. This does not block Phase 7 verification.
- Publishing is mock/local only in this phase. No live platform credential validation or network publishing is attempted yet.

## Final Result

- Contract status: Verified
- Code status: Implemented and locally verified
- Verified by: Codex
- Verified on: 2026-04-07
