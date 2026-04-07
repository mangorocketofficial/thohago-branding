# Desktop Phase 10 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase9_contract.md](./desktop_phase9_contract.md), [desktop_phase9_verification.md](./desktop_phase9_verification.md)

## Goal

Deliver publish UX hardening and supported-provider expansion on top of the phase 9 live execution track:

- add a publish summary layer that explains what is live-ready, blocked, or manual-only,
- add bulk publish actions for operator workflows,
- expand previously unsupported publish targets into manual handoff support where direct live posting is still unavailable,
- persist the new operator-visible publish state across restart.

Desktop Phase 10 does not promise direct live posting for every target. Instead, it hardens the publish route into an operational dashboard and expands support coverage by converting some unsupported targets into structured manual handoff outputs.

## Scope

### In Scope

1. Publish summary model
   - Introduce a publish summary for each project that computes, per content type:
     - support tier
     - live status
     - recommended action
     - latest run linkage
   - Required support tiers:
     - `live_api`
     - `manual_handoff`

2. Publish route UX hardening
   - Extend `#/project/:id/publish` with:
     - aggregate summary counts
     - validate-all action
     - run-recommended-publish action
     - clearer per-card support tier and readiness messaging
     - live button labels that reflect the actual action, including manual package creation

3. Supported-provider expansion
   - Expand previous `unsupported` targets into manual handoff support where feasible:
     - Naver Blog live target -> manual handoff package
     - Instagram Reels live target -> manual handoff package
   - Continue real live API execution for:
     - Instagram carousel
     - Threads

4. Manual handoff artifacts
   - Persist manual handoff artifacts on disk for manual-only targets.
   - Required artifacts:
     - Naver Blog manual markdown package
     - Instagram Reels manual caption or handoff package

5. Verification support
   - Extend automated tests to cover publish summary logic and manual handoff persistence.
   - Extend smoke verification to cover validate-all plus recommended publish flow.
   - Update direct operator verification to capture the new provider outcomes.

### Out of Scope

- Guaranteed successful live posting to external platforms
- Real Naver Blog posting
- Real Instagram Reels upload
- Publish scheduling
- Multi-account publish routing

## Provider Coverage Matrix

### Required in Phase 10

- Blog:
  - mock publish supported
  - live action creates a manual Naver handoff package
- Carousel:
  - mock publish supported
  - live publish uses Instagram Graph API path
- Video:
  - mock publish supported
  - live action creates a manual Reels handoff package
- Thread:
  - mock publish supported
  - live publish uses Threads API path

Contract note:

- Manual handoff support counts as supported-provider expansion in this phase. It is not equivalent to direct external posting.

## Required Inputs

Desktop Phase 10 implementation must support:

- a project with generated content
- saved publish credentials
- operator-triggered validate-all or run-recommended actions from the publish route

## Required Outputs

Desktop Phase 10 must produce:

1. Repository outputs
   - publish summary model and IPC
   - publish route summary UI and bulk actions
   - manual handoff support for Naver Blog and Reels

2. Runtime outputs
   - per-content publish readiness or manual support status
   - persisted manual handoff artifacts
   - restart-safe publish dashboard state

3. Inspectable evidence
   - summary and recommended-publish smoke evidence
   - manual handoff artifacts on disk
   - direct operator verification showing the current provider outcome matrix

## Required Commands and Operator Flows

Desktop Phase 10 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

4. Direct operator verification
   - `python apps/desktop/scripts/verify-live-publish-execution.py`

Phase 10 must support this operator flow:

1. Open the publish route for a generated project.
2. Save or confirm publish credentials.
3. Run validate-all from the publish route.
4. Run recommended publish actions from the publish route.
5. Inspect the generated manual handoff artifacts or live provider results.
6. Restart the app and confirm the publish summary and history are preserved.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 9 functionality is already present and working.
- Existing local `.env` credentials may be used for direct operator verification.
- Because the current local credentials may be missing or expired, verification may complete with structured `missing`, `error`, or `manual_ready` outcomes instead of successful external posts.

## Acceptance Criteria

### A. Publish Summary

- The publish route shows support tier and readiness per content type.
- The publish route shows aggregate summary counts.

### B. Bulk Actions

- Validate-all works from the publish route.
- Run-recommended-publish works from the publish route.

### C. Supported-Provider Expansion

- Naver Blog live action produces a manual handoff package.
- Instagram Reels live action produces a manual handoff package.
- Instagram carousel and Threads remain on the live API path.

### D. Persistence

- Manual handoff artifacts persist on disk.
- Publish summary remains meaningful after restart.
- Publish run history remains preserved after restart.

### E. Automated Verification

- `pnpm desktop:test` covers publish summary or manual handoff behavior.
- Clean `pnpm desktop:smoke` succeeds.
- Restart `pnpm desktop:smoke` confirms persisted publish summary and history.
- Direct operator verification records actual provider outcomes.

## Completion Evidence Required

Desktop Phase 10 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 10 clean `pnpm desktop:smoke` command/result
   - exact phase 10 restart `pnpm desktop:smoke` command/result
   - exact direct operator verification command/result

3. Artifact evidence
   - manual handoff artifact evidence
   - publish summary smoke evidence

4. Flow evidence
   - evidence that validate-all and run-recommended worked
   - evidence that manual handoff outputs were produced
   - evidence that restart preserved publish state

## Explicit Non-Completion Cases

- publish route still behaves like a flat button list without readiness guidance
- recommended publish is not available
- Naver Blog and Reels still only return raw unsupported with no handoff artifact
- manual handoff artifacts are not persisted
- restart loses publish summary usefulness or publish history

## Change Control

- Desktop Phase 10 is publish UX hardening plus manual-handoff-based support expansion.
- If direct live posting for Naver Blog or Reels is pulled into this phase, update the contract first.
