# Desktop Phase 6 Verification

> Status: Verified  
> Date: 2026-04-07  
> Contract: [desktop_phase6_contract.md](./desktop_phase6_contract.md)

Use this document only after implementation begins. Record evidence against the active Desktop Phase 6 contract. Do not use this document to change scope retroactively.

## Verification Environment

- OS: Windows (PowerShell)
- Node: `v22.18.0`
- pnpm: `10.30.1`
- Python: `Python 3.12.8`
- Working directory: `C:\Users\User\Desktop\Thohago_branding`
- Desktop runtime data directory: `C:\Users\User\Desktop\Thohago_branding\apps\desktop\.thohago-desktop\phase6-proof`

## Automated Test Evidence

- Command: `pnpm desktop:test`
- Result: Pass (7 tests)
- Notes:
  - preserved phases 1-5 verification coverage
  - added bounded regeneration verification covering:
    - latest spec update
    - latest preview update
    - generation run history persistence
    - materially different regenerated output for blog content

## Smoke Verification Evidence

- Clean command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase6'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase6-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase6-proof-report.json'; pnpm desktop:smoke`
- Clean result:
  - Pass
- Restart command:
  - `$env:THOHAGO_DESKTOP_SMOKE_FLOW='phase6-restart'; $env:THOHAGO_DESKTOP_DATA_DIR='.thohago-desktop/phase6-proof'; $env:THOHAGO_DESKTOP_SMOKE_OUTPUT='.thohago-desktop/phase6-proof-restart-report.json'; pnpm desktop:smoke`
- Restart result:
  - Pass
- Notes:
  - clean smoke completed onboarding, project/media/interview/generation-setup prerequisites, generated content, then executed one regeneration action per content type before walking all review routes
  - restart smoke reopened against the same data directory and confirmed regenerated review state and run history remained available

## Regeneration Verification

- Project id: `phase2-smoke-project-20260407084902`
- Blog regeneration evidence:
  - mode: `premium`
  - clean smoke report recorded `generationRunCount=2` and `regenerationMode=premium` on the blog route
- Carousel regeneration evidence:
  - mode: `cta_boost`
  - clean smoke report recorded `generationRunCount=2` and `regenerationMode=cta_boost` on the carousel route
- Video regeneration evidence:
  - mode: `length_shorter`
  - clean smoke report recorded `generationRunCount=2` on the video route and the latest preview artifact was updated
- Thread regeneration evidence:
  - mode: `tone_shift`
  - clean smoke report recorded `generationRunCount=2` and `regenerationMode=tone_shift` on the thread route
- Run history evidence:
  - DB inspection shows 8 total `generation_runs` rows:
    - 4 initial runs
    - 4 regeneration runs
  - each run stores a persisted preview artifact path under `generated/history/...`

## Produced Artifacts

- Latest blog preview:
  - [blog_preview.html](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/blog_preview.html)
- Latest carousel preview:
  - [carousel_preview.html](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/carousel_preview.html)
- Latest video preview:
  - [video_preview.html](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/video_preview.html)
- Latest thread preview:
  - [thread_preview.html](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/thread_preview.html)
- Regeneration run evidence:
  - [blog initial history](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/history/blog/20260407084903255_initial.html)
  - [blog premium history](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/history/blog/20260407084903630_premium.html)
  - [carousel cta_boost history](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/history/carousel/20260407084904082_cta_boost.html)
  - [video length_shorter history](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/history/video/20260407084904180_length_shorter.html)
  - [thread tone_shift history](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof/projects/phase2-smoke-project-20260407084902/generated/history/thread/20260407084904202_tone_shift.html)
- Other evidence:
  - [phase6-proof-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof-report.json)
  - [phase6-proof-restart-report.json](/C:/Users/User/Desktop/Thohago_branding/apps/desktop/.thohago-desktop/phase6-proof-restart-report.json)
  - DB inspection showed non-null latest `preview_artifact_path` for all content types and archived preview paths for all regeneration runs

## Acceptance Checklist

### A. Regeneration Actions

- [x] review routes expose bounded regeneration actions
- [x] regeneration updates latest stored spec
- [x] regeneration updates latest preview artifact

### B. Run History

- [x] regeneration run records persist
- [x] review routes display readable run history
- [x] run history survives restart

### C. Bounded Modes

- [x] at least one regeneration action per content type succeeds
- [x] different modes produce materially different output or metadata

### D. Persistence and Restart

- [x] latest regenerated output survives restart
- [x] preview artifact paths remain resolvable after restart
- [x] run history remains available after restart

### E. Automated Verification

- [x] `pnpm desktop:test` covers regeneration behavior
- [x] clean `pnpm desktop:smoke` succeeds
- [x] restart `pnpm desktop:smoke` confirms persistence

## Open Issues

- Electron dev runtime still emits the standard CSP warning while running from the Vite dev server. This does not block Phase 6 verification.
- The regeneration implementation is deterministic and bounded by design for this phase. It does not yet perform provider-backed semantic rewriting.
- Some rapid smoke-route transitions still produce minor `about:srcdoc` load-cancel noise in dev logging. This does not block regeneration persistence verification.

## Final Result

- Contract status: Verified
- Code status: Implemented and locally verified
- Verified by: Codex
- Verified on: 2026-04-07
