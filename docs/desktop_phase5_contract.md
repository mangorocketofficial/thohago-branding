# Desktop Phase 5 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase4_contract.md](./desktop_phase4_contract.md), [desktop_phase4_verification.md](./desktop_phase4_verification.md)

## Goal

Deliver rendering/review polish on top of the verified content-generation flow:

- render review-oriented preview artifacts for all generated content types,
- persist those preview artifacts,
- upgrade the desktop review routes to show richer preview content,
- verify that the polished review experience survives restart.

Desktop Phase 5 is intentionally about review rendering and preview polish, not regeneration. Freeform or bounded regeneration stays out of scope for this phase.

The business outcome is that generated content is no longer just inspectable as raw JSON. It is reviewable through richer, presentation-oriented artifacts and routes that feel closer to a real product workflow.

## Scope

### In Scope

1. Preview artifact persistence
   - Persist preview-oriented artifacts for all 4 content types:
     - blog preview HTML
     - carousel preview HTML
     - video review/storyboard HTML
     - thread preview HTML
   - Track preview artifact paths in persistence.

2. Review route polish
   - Upgrade:
     - `#/project/:id/blog`
     - `#/project/:id/carousel`
     - `#/project/:id/video`
     - `#/project/:id/thread`
   - Each review route must render a meaningful preview-first experience rather than only raw structured data.

3. Artifact-backed review loading
   - Review routes must load from persisted preview artifacts or equivalent persisted render output, not only in-memory generation results.
   - Preview routes must remain functional after restart against the same data directory.

4. Inspectable artifact outputs
   - Persist at minimum:
     - `generated/blog_preview.html`
     - `generated/carousel_preview.html`
     - `generated/video_preview.html`
     - `generated/thread_preview.html`

5. Local verification support
   - Extend smoke verification to confirm preview artifacts exist and review routes open successfully after generation.
   - Extend automated tests to cover preview artifact persistence or preview path tracking.

### Out of Scope

- Regeneration or edit controls
- High-fidelity final carousel JPEG rendering
- Final MP4 video rendering
- Publishing
- Live AI-backed review improvements

## Required Inputs

Desktop Phase 5 implementation must support:

- a `content_generated` desktop project
- generated content specs for blog, carousel, video, and thread

Contract note:

- Phase 5 verification does not require live AI credentials.
- This phase may use deterministic HTML-based preview rendering rather than production-grade final exports.

## Required Outputs

Desktop Phase 5 must produce:

1. Repository outputs
   - migration file(s) if needed for preview artifact tracking
   - main-process preview rendering/persistence code
   - upgraded read-only review route components

2. Runtime outputs
   - preview artifact paths persisted for generated content entries

3. Inspectable filesystem artifacts
   - `generated/blog_preview.html`
   - `generated/carousel_preview.html`
   - `generated/video_preview.html`
   - `generated/thread_preview.html`

## Required Commands and Operator Flows

Desktop Phase 5 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

Phase 5 must support this operator flow:

1. Open a project with generated content.
2. Open each review route.
3. See preview-first rendering for blog, carousel, video, and thread.
4. Inspect preview artifact files on disk.
5. Restart the app and confirm the review routes still work from persisted artifacts.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 4 functionality is already present and working.
- Verification may reuse the same deterministic smoke generation path used in phase 4.
- No live provider keys are required for contract verification.

## Acceptance Criteria

### A. Preview Artifact Persistence

- `blog_preview.html` exists and is persisted.
- `carousel_preview.html` exists and is persisted.
- `video_preview.html` exists and is persisted.
- `thread_preview.html` exists and is persisted.

### B. Review Routes

- Blog review route shows preview-first rendering.
- Carousel review route shows preview-first rendering.
- Video review route shows preview-first rendering.
- Thread review route shows preview-first rendering.

### C. Persistence and Restart

- Review routes work after restart against the same data directory.
- Preview artifact paths remain resolvable after restart.

### D. Automated Verification

- `pnpm desktop:test` covers preview artifact persistence or preview path tracking.
- Clean `pnpm desktop:smoke` succeeds.
- Restart `pnpm desktop:smoke` confirms persisted review behavior.

## Completion Evidence Required

Desktop Phase 5 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 5 clean `pnpm desktop:smoke` command/result
   - exact phase 5 restart `pnpm desktop:smoke` command/result

3. Artifact evidence
   - `generated/blog_preview.html`
   - `generated/carousel_preview.html`
   - `generated/video_preview.html`
   - `generated/thread_preview.html`

4. Flow evidence
   - evidence that all 4 review routes were reached
   - evidence that the routes remained functional after restart

## Explicit Non-Completion Cases

- review routes still show only raw JSON or plain text dumps
- preview artifacts are not persisted to disk
- preview behavior is lost after restart
- verification does not record all 4 preview artifact paths

## Change Control

- Desktop Phase 5 is rendering/review polish only.
- If regeneration is pulled into this phase, update the contract first.
