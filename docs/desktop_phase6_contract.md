# Desktop Phase 6 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase5_contract.md](./desktop_phase5_contract.md), [desktop_phase5_verification.md](./desktop_phase5_verification.md)

## Goal

Deliver bounded regeneration on top of the verified generated-content review flow:

- add regeneration actions to the four review routes,
- persist each regeneration run,
- update the latest generated output after regeneration,
- preserve regeneration history and the latest regenerated preview after restart.

Desktop Phase 6 maps to the "bounded regeneration" model described in the Electron app spec:

- regenerate
- tone shift
- shorter
- longer
- premium
- CTA boost

This phase is intentionally bounded. It does not include freeform chat editing.

The business outcome is that generated content becomes iteratively improvable through predictable one-click controls without requiring a full conversational editor.

## Scope

### In Scope

1. Regeneration persistence
   - Add durable storage for regeneration runs.
   - Track at minimum:
     - target content type
     - regeneration mode
     - produced spec snapshot
     - produced preview artifact path
     - creation time

2. Bounded regeneration actions
   - Support these actions for each content type:
     - `regenerate`
     - `tone_shift`
     - `length_shorter`
     - `length_longer`
     - `premium`
     - `cta_boost`
   - Regeneration must update the latest content spec and latest preview artifact for the selected content type.

3. Review route action row
   - Add regeneration controls to:
     - `#/project/:id/blog`
     - `#/project/:id/carousel`
     - `#/project/:id/video`
     - `#/project/:id/thread`
   - The user must be able to trigger a bounded regeneration directly from the review route.

4. Generation run history
   - Each review route must surface a readable history of prior generation/regeneration runs for that content type.
   - History must survive restart.

5. Deterministic local regeneration
   - Regeneration must remain verifiable without live AI credentials.
   - Phase 6 may use deterministic local regeneration transforms as long as modes produce materially distinct outputs and persist correctly.

6. Inspectable artifacts
   - The latest preview artifact for each content type must continue to exist.
   - Each regeneration run must retain an inspectable spec snapshot and preview artifact reference.

7. Local verification support
   - Extend automated tests to cover regeneration run persistence.
   - Extend smoke verification so phase 6 runs at least one regeneration action for each content type and confirms history survives restart.

### Out of Scope

- Freeform AI chat editing
- Diff viewer for arbitrary JSON edits
- Publishing
- High-fidelity final rendering
- Billing

## Required Inputs

Desktop Phase 6 implementation must support:

- a `content_generated` project
- generated blog/carousel/video/thread content
- a bounded regeneration mode chosen from the contracted set

Contract note:

- No live provider keys are required for contract verification.
- Regeneration may be deterministic and mode-driven rather than provider-backed AI for this phase.

## Required Outputs

Desktop Phase 6 must produce:

1. Repository outputs
   - migration file(s) for regeneration run persistence
   - main-process regeneration orchestration
   - sidecar regeneration methods or equivalent deterministic regeneration boundary
   - review-route action controls and run-history UI

2. Runtime outputs
   - latest content spec updated after regeneration
   - latest preview artifact updated after regeneration
   - generation run history persisted

3. Inspectable filesystem artifacts
   - latest preview artifacts per content type
   - run-history artifact files or persisted preview-path references for regeneration runs

## Required Commands and Operator Flows

Desktop Phase 6 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

Phase 6 must support this operator flow:

1. Open a project with generated content.
2. Open each review route.
3. Trigger at least one bounded regeneration action.
4. Observe the latest preview update.
5. Observe run history for the selected content type.
6. Restart the app and confirm the latest regenerated output and run history persist.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 5 functionality is already present and working.
- Verification may reuse the same deterministic smoke generation path used in earlier phases.
- No live provider keys are required for contract verification.

## Acceptance Criteria

### A. Regeneration Actions

- The review route exposes bounded regeneration actions for each content type.
- Triggering a regeneration action updates the latest stored spec for that content type.
- Triggering a regeneration action updates the latest preview artifact for that content type.

### B. Run History

- A regeneration run record is persisted for each regeneration action.
- Review routes display readable generation/regeneration history.
- Run history survives restart.

### C. Bounded Modes

- At least one regeneration action per content type can be executed successfully.
- Different regeneration modes produce materially different output content or metadata.

### D. Persistence and Restart

- The latest regenerated output remains available after restart.
- Preview artifact paths remain resolvable after restart.
- Run history remains available after restart.

### E. Automated Verification

- `pnpm desktop:test` covers regeneration persistence or run-history behavior.
- Clean `pnpm desktop:smoke` succeeds.
- Restart `pnpm desktop:smoke` confirms regenerated output and history persistence.

## Completion Evidence Required

Desktop Phase 6 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 6 clean `pnpm desktop:smoke` command/result
   - exact phase 6 restart `pnpm desktop:smoke` command/result

3. Artifact evidence
   - latest preview artifact path(s)
   - persisted regeneration run record evidence

4. Flow evidence
   - evidence that regeneration actions executed
   - evidence that run history was visible or persisted
   - evidence that restart preserved the regenerated state

## Explicit Non-Completion Cases

- regeneration actions are missing or dead buttons
- regeneration runs are not persisted
- latest preview updates only in memory and not on disk
- restart loses run history or latest regenerated output
- verification does not record regeneration evidence for the four content types

## Change Control

- Desktop Phase 6 is bounded regeneration only.
- If freeform conversational editing is pulled into this phase, update the contract first.
