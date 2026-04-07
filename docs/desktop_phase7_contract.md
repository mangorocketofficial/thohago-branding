# Desktop Phase 7 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase6_contract.md](./desktop_phase6_contract.md), [desktop_phase6_verification.md](./desktop_phase6_verification.md)

## Goal

Deliver the first publishing layer on top of the verified content-generation and regeneration flow:

- add a real publish route,
- support mock publishing for blog, carousel, video, and thread,
- persist publish run results,
- surface publishing status after restart.

Desktop Phase 7 is intentionally scoped to mock/local publishing. It does not attempt live Naver, Instagram, or Threads platform integration yet.

The business outcome is that the desktop app can complete a full local cycle from project creation through publish simulation, with durable publish status and inspectable publish artifacts.

## Scope

### In Scope

1. Publish persistence
   - Add durable storage for publish runs.
   - Track at minimum:
     - content type
     - target platform
     - status
     - permalink or mock URL
     - publish metadata
     - creation time

2. Mock publish methods
   - Support mock publishing for:
     - blog -> Naver blog
     - carousel -> Instagram carousel
     - video -> Instagram reels
     - thread -> Threads
   - Publishing must be verifiable without live credentials.

3. Publish route and UI
   - Add a real `#/project/:id/publish` route.
   - Surface publish actions and latest status for the four content types.
   - Allow publishing each content type individually from the publish route.

4. Project/content publish status
   - Persist latest publish status per content type.
   - Surface project-level publish completeness when all four content types have mock-published successfully.

5. Inspectable artifacts
   - Persist publish result artifacts at minimum:
     - `published/blog_publish_result.json`
     - `published/carousel_publish_result.json`
     - `published/video_publish_result.json`
     - `published/thread_publish_result.json`

6. Local verification support
   - Extend automated tests to cover publish-run persistence.
   - Extend smoke verification so phase 7 completes all four mock publish actions and confirms results survive restart.

### Out of Scope

- Live Naver Blog posting
- Live Instagram Graph API posting
- Live Threads API posting
- Credential validation against real platforms
- Retry queues or background publishing workers

## Required Inputs

Desktop Phase 7 implementation must support:

- a `content_generated` project
- generated content for blog, carousel, video, and thread

Contract note:

- No live provider credentials are required for contract verification.
- The mock publish path must still preserve platform identity and durable result metadata.

## Required Outputs

Desktop Phase 7 must produce:

1. Repository outputs
   - migration file(s) for publish persistence
   - main-process publish orchestration code
   - sidecar publish methods for mock/local verification
   - publish route component(s)

2. Runtime outputs
   - persisted publish results
   - updated content status for published items
   - updated project status when the full publish set is complete

3. Inspectable filesystem artifacts
   - `published/blog_publish_result.json`
   - `published/carousel_publish_result.json`
   - `published/video_publish_result.json`
   - `published/thread_publish_result.json`

## Required Commands and Operator Flows

Desktop Phase 7 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

Phase 7 must support this operator flow:

1. Open a project with generated content.
2. Open the publish route.
3. Publish blog, carousel, video, and thread through mock/local publish actions.
4. Observe per-item publish status and mock permalinks.
5. Restart the app and confirm publish status remains visible.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 6 functionality is already present and working.
- No live provider keys are required for contract verification.

## Acceptance Criteria

### A. Publish Route

- `#/project/:id/publish` is a real route.
- The publish route renders meaningful status for all 4 publishable content types.

### B. Mock Publish Actions

- Blog mock publish succeeds and persists a result.
- Carousel mock publish succeeds and persists a result.
- Video mock publish succeeds and persists a result.
- Thread mock publish succeeds and persists a result.

### C. Persistence

- Publish runs are persisted in the desktop DB.
- Publish result artifacts are persisted on disk.
- Publish status survives restart.

### D. Project/Content Status

- Individual published content items reflect published status after mock publish.
- The project can reflect an overall published-complete state when all four publish actions succeed.

### E. Automated Verification

- `pnpm desktop:test` covers publish persistence behavior.
- Clean `pnpm desktop:smoke` succeeds.
- Restart `pnpm desktop:smoke` confirms persisted publish state.

## Completion Evidence Required

Desktop Phase 7 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 7 clean `pnpm desktop:smoke` command/result
   - exact phase 7 restart `pnpm desktop:smoke` command/result

3. Artifact evidence
   - four publish result JSON files
   - persisted publish-run DB evidence

4. Flow evidence
   - evidence that all four mock publish actions executed
   - evidence that publish state remained visible after restart

## Explicit Non-Completion Cases

- publish route is missing or placeholder-only
- publish actions are dead buttons
- publish results are not persisted
- restart loses publish state
- verification does not record all four publish result artifacts

## Change Control

- Desktop Phase 7 is mock/local publishing only.
- If live platform integrations are pulled into this phase, update the contract first.
