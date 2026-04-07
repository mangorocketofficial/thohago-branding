# Desktop Phase 4 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase3_contract.md](./desktop_phase3_contract.md), [desktop_phase3_verification.md](./desktop_phase3_verification.md)

## Goal

Deliver the first deterministic local content-generation pass on top of the verified generation-setup flow:

- build a normalized content bundle from project, media, interview, and generation profile data,
- generate all 4 content types,
- persist the generated specs and artifacts,
- expose read-only review routes for the generated outputs.

Desktop Phase 4 maps to the "Content Generation" step in the Electron app spec, but it is intentionally scoped to deterministic local spec generation and lightweight read-only review. Heavy rendering pipelines and publishing remain out of scope.

The business outcome is that a completed desktop project can now move from "ready_to_generate" to "content_generated" with inspectable outputs for blog, carousel, video, and thread.

## Scope

### In Scope

1. Content bundle orchestration
   - Build one normalized content bundle from:
     - project metadata
     - imported media
     - media preflight
     - completed interview answers
     - generation profile
   - Persist the content bundle as an inspectable artifact.

2. Deterministic 4-content generation
   - Generate:
     - blog spec
     - carousel spec
     - video spec
     - thread spec
   - Use the Python sidecar for generation calls.
   - The generation path must not require live AI credentials for verification.

3. Desktop persistence
   - Persist generated content specs in the desktop DB.
   - Persist generated content artifacts to the project folder.
   - Update project status to `content_generated` after successful generation of all 4 content types.

4. Generation trigger
   - Add a real "Generate All Content" action from generation setup when the project is ready.
   - Surface generation status in the project view.

5. Read-only review routes
   - Add real routes for:
     - `#/project/:id/blog`
     - `#/project/:id/carousel`
     - `#/project/:id/video`
     - `#/project/:id/thread`
   - Each route must render meaningful review state for the corresponding generated output.

6. Inspectable artifacts
   - Persist at minimum:
     - `generated/content_bundle.json`
     - `generated/blog_spec.json`
     - `generated/blog_preview.html`
     - `generated/carousel_spec.json`
     - `generated/video_spec.json`
     - `generated/thread_spec.json`

7. Local verification support
   - Extend the smoke flow so phase 4 verification can:
     - satisfy onboarding/project/interview/generation-setup prerequisites
     - trigger "Generate All Content"
     - verify the generated review routes
   - Extend automated tests to cover content generation persistence.

### Out of Scope

- Carousel image rendering to final JPEG slides
- Video rendering to final MP4
- Regeneration actions
- Publishing
- Live AI-backed prompt quality tuning
- Rich WYSIWYG editing

## Required Inputs

Desktop Phase 4 implementation must support:

- a project with:
  - imported media
  - completed interview
  - saved generation profile

Contract note:

- Phase 4 verification does not require live Gemini, Anthropic, OpenAI, or Groq access.
- The generated outputs may be deterministic local templates/specs as long as all 4 content types are produced and persisted.

## Required Outputs

Desktop Phase 4 must produce:

1. Repository outputs
   - migration file(s) for generated content persistence
   - main-process generation orchestration code
   - sidecar generation methods for all 4 content types
   - read-only review route components

2. Runtime outputs
   - persisted content specs in the desktop DB
   - project status `content_generated`

3. Inspectable filesystem artifacts
   - `generated/content_bundle.json`
   - `generated/blog_spec.json`
   - `generated/blog_preview.html`
   - `generated/carousel_spec.json`
   - `generated/video_spec.json`
   - `generated/thread_spec.json`

## Required Commands and Operator Flows

Desktop Phase 4 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

Phase 4 must support this operator flow:

1. Open a project that is `ready_to_generate`.
2. Open generation setup and confirm the saved profile.
3. Trigger "Generate All Content".
4. Return to the project view and see generation complete state.
5. Open each review route for blog, carousel, video, and thread.
6. Restart the app and confirm the generated content still exists.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 3 functionality is already present and working.
- Verification may reuse the same deterministic smoke scenario pattern used in prior phases.
- No live provider keys are required for contract verification.

## Acceptance Criteria

### A. Generation Trigger

- A user can trigger "Generate All Content" from a `ready_to_generate` project.
- The generate action is blocked or disabled before the project reaches `ready_to_generate`.

### B. Content Bundle

- One `content_bundle.json` is produced per generated project.
- The bundle includes project identity, media references, interview answers, preflight, and generation profile.

### C. Four Content Types

- Blog spec is generated and persisted.
- Carousel spec is generated and persisted.
- Video spec is generated and persisted.
- Thread spec is generated and persisted.

### D. Review Routes

- `#/project/:id/blog` is a real route with meaningful review state.
- `#/project/:id/carousel` is a real route with meaningful review state.
- `#/project/:id/video` is a real route with meaningful review state.
- `#/project/:id/thread` is a real route with meaningful review state.

### E. Persistence

- Generated content specs persist in the DB.
- Generated artifact files persist on disk.
- Generated content remains available after restart.
- Project status is `content_generated` after successful generation.

### F. Automated Verification

- `pnpm desktop:test` covers generated-content persistence or sidecar generation behavior.
- A clean `pnpm desktop:smoke` run succeeds for phase 4.
- A restart `pnpm desktop:smoke` run confirms generated content persistence.

## Completion Evidence Required

Desktop Phase 4 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 4 clean `pnpm desktop:smoke` command/result
   - exact phase 4 restart `pnpm desktop:smoke` command/result

3. Artifact evidence
   - desktop DB path
   - `generated/content_bundle.json`
   - `generated/blog_spec.json`
   - `generated/blog_preview.html`
   - `generated/carousel_spec.json`
   - `generated/video_spec.json`
   - `generated/thread_spec.json`

4. Flow evidence
   - evidence that generation trigger succeeded
   - evidence that all 4 review routes were reached
   - evidence that generated content persisted after restart

## Explicit Non-Completion Cases

- "Generate All Content" exists only as a dead button
- fewer than 4 content types are generated
- outputs exist only in memory and are not persisted
- no read-only review routes exist for the generated outputs
- restart loses generated content
- verification does not record generated artifact paths

## Change Control

- Desktop Phase 4 is content generation only.
- If heavy rendering or publishing is pulled into this phase, update the contract first.
- If deterministic local generation is replaced with a live AI-only path, update the contract first.
