# Desktop Phase 3 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase2_contract.md](./desktop_phase2_contract.md), [desktop_phase2_verification.md](./desktop_phase2_verification.md)

## Goal

Deliver the generation-setup layer on top of the verified desktop project/interview flow:

- capture the structured generation profile,
- persist it to the desktop DB and project artifacts,
- surface generation readiness in the UI,
- make the project explicitly ready for the later "Generate All Content" phase.

Desktop Phase 3 maps to the "Generation Setup" step in the Electron app spec, not to the full content generation phase. This phase ends when a completed project/interview can be configured for generation and its generation profile survives restart.

The business outcome is that the desktop app now collects all inputs needed before content generation begins, without yet invoking the 4-content generation pipeline.

## Scope

### In Scope

1. Generation profile persistence
   - Add storage for a structured generation profile on each project.
   - Persist the profile in the desktop DB and as a project artifact file.

2. Generation setup route and UI
   - Add a real `#/project/:id/generate` route.
   - Add a generation setup screen with editable fields for:
     - industry
     - tone
     - content length
     - emphasis point
     - must-include keywords
     - excluded phrases
     - photo priority
     - representative media asset

3. Readiness gating
   - Generation setup is only actionable after:
     - a project exists
     - media exists
     - interview is completed
   - The project view must surface whether the project is or is not ready for generation setup.

4. Profile defaults and media linkage
   - Default photo priority to current media order.
   - Default representative media to the current hero media asset.
   - Saving generation setup must preserve consistency with current media IDs.

5. Project status update
   - Saving a valid generation profile marks the project as `ready_to_generate`.
   - Project/dashboard UI must surface that status.

6. Inspectable artifacts
   - Write `generation/generation_profile.json` under the project folder.
   - Artifact contents must be sufficient to inspect the saved generation setup without opening the DB.

7. Local verification support
   - Extend the smoke flow so phase 3 verification can complete generation setup automatically after phase 2 prerequisites.
   - Extend automated tests to cover generation profile persistence and readiness behavior.

### Out of Scope

- Actual content generation for blog/carousel/video/thread
- Progress UI for generation jobs
- Rendering generated outputs
- AI regeneration actions
- Publishing
- Voice interview input or STT changes

## Required Inputs

Desktop Phase 3 implementation must support:

- a completed Desktop Phase 2 project
- imported media with stable media IDs
- completed 3-turn interview
- generation profile inputs:
  - industry
  - tone
  - content length
  - emphasis point
  - must-include keywords
  - excluded phrases
  - photo priority
  - representative media asset

Contract note:

- No live AI credentials are required for Desktop Phase 3 verification.
- Clicking "generate all content" is not part of this phase; the UI may present a placeholder or disabled next-step CTA as long as scope is explicit.

## Required Outputs

Desktop Phase 3 must produce:

1. Repository outputs
   - migration file(s) for generation setup persistence
   - generation setup route and UI components
   - main-process services or equivalent methods to save/load generation profiles

2. Runtime outputs
   - generation profile persisted in the desktop DB
   - project status updated to `ready_to_generate`

3. Inspectable filesystem artifacts
   - `generation/generation_profile.json`

## Required Commands and Operator Flows

Desktop Phase 3 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

Phase 3 must support this operator flow:

1. Open an onboarded desktop data directory with a completed Phase 2 project.
2. Open the project view.
3. Navigate to generation setup.
4. Review default photo priority and representative media.
5. Enter or edit the structured generation fields.
6. Save the generation profile.
7. Return to project view and see the project marked ready for generation.
8. Restart the app and confirm the generation profile persists.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 2 functionality is already present and working.
- Verification may use the same local media fixtures and smoke flow strategy established in Phase 2.
- No live provider keys are required to contract-verify this phase.

## Acceptance Criteria

### A. Route and UI Coverage

- `#/project/:id/generate` is a real route.
- The generation setup screen renders meaningful state, not placeholder-only text.
- The project view links to generation setup when interview completion conditions are met.

### B. Generation Profile Editing

- A user can save a generation profile from the desktop UI.
- The saved profile includes all contracted fields.
- Photo priority is stored as an ordered list of media IDs.
- Representative media can be selected and saved from available project media.

### C. Readiness Gating

- Generation setup is blocked or clearly disabled before interview completion.
- After interview completion, generation setup becomes available.
- Saving a valid generation profile marks the project `ready_to_generate`.

### D. Persistence

- The generation profile persists in the desktop DB.
- The generation profile survives app restart.
- The saved representative media ID and photo priority survive restart.

### E. Inspectable Artifacts

- `generation/generation_profile.json` exists after save.
- The artifact reflects the saved profile fields and media linkage.

### F. Automated Verification

- `pnpm desktop:test` covers generation profile persistence or readiness behavior.
- `pnpm desktop:smoke` completes successfully for a phase 3 clean run.
- A restart smoke run confirms the saved generation profile persists.

## Completion Evidence Required

Desktop Phase 3 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 3 clean `pnpm desktop:smoke` command/result
   - exact phase 3 restart `pnpm desktop:smoke` command/result

3. Artifact evidence
   - desktop DB path
   - project folder path
   - `generation/generation_profile.json`

4. Flow evidence
   - evidence that generation setup route was reached
   - evidence that profile save succeeded
   - evidence that project status became `ready_to_generate`
   - evidence that the saved profile persisted after restart

## Explicit Non-Completion Cases

- the app still has no real generation setup route
- generation profile fields are held only in renderer state and not persisted
- representative media or photo priority is not saved with stable media IDs
- the project status never reflects generation readiness
- no inspectable generation-profile artifact exists
- verification does not prove persistence after restart

## Change Control

- Desktop Phase 3 is generation setup only.
- If real content generation is pulled into this phase, update the contract first.
- If phase 3 needs server-side or live-AI validation for profile save, update the contract first.
