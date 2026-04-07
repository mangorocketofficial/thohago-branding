# Desktop Phase 9 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase8_contract.md](./desktop_phase8_contract.md), [desktop_phase8_verification.md](./desktop_phase8_verification.md)

## Goal

Deliver real publish execution orchestration on top of the credential-aware publish route:

- expose explicit `mock` and `live` publish actions from the desktop UI,
- persist execution mode and live provider results in `publish_runs`,
- route live publish requests into the Python sidecar with saved credentials and local media paths,
- surface structured provider outcomes even when the external publish fails or is unsupported.

Desktop Phase 9 is the first phase where the desktop app performs real publish execution attempts instead of validation-only checks. Successful real posting is not required for every provider in this phase, but the runtime must now attempt the live publish path where a publisher exists and must persist the real provider response or failure.

## Scope

### In Scope

1. Publish execution modes
   - Introduce explicit publish execution modes:
     - `mock`
     - `live`
   - Persist execution mode per publish run.

2. Publish route live actions
   - Extend `#/project/:id/publish` so each content type can run:
     - mock publish
     - live publish
   - Keep credential save and validation actions from Phase 8.

3. Live provider orchestration
   - Build publish payloads from stored content specs, local media assets, and saved credentials.
   - Wire live sidecar execution for currently supported providers:
     - Instagram carousel via `InstagramGraphPublisher`
     - Threads via `ThreadsPublisher`
   - For providers without a production-ready implementation in this desktop track, return structured results rather than silent failure:
     - Naver Blog -> `unsupported`
     - Instagram Reels -> `unsupported`

4. Persistence and artifacts
   - Persist every publish attempt as a publish run with:
     - execution mode
     - provider result
     - archived artifact path
   - Preserve the latest publish artifact per content type.

5. Verification support
   - Extend automated tests to cover live execution persistence and payload wiring.
   - Extend smoke verification to cover deterministic live publish attempts with restart-safe publish history.
   - Add a direct operator command that attempts real live publish execution with current local credentials and records the actual provider outcomes.

### Out of Scope

- Guaranteed successful posting to every provider
- Live Naver Blog posting
- Live Instagram Reels upload
- Multi-reply Threads chain orchestration
- Scheduling or delayed publishing

## Provider Coverage Matrix

### Required in Phase 9

- Blog:
  - mock publish supported
  - live publish returns structured `unsupported`
- Carousel:
  - mock publish supported
  - live publish attempts real Instagram Graph execution
- Video:
  - mock publish supported
  - live publish returns structured `unsupported`
- Thread:
  - mock publish supported
  - live publish attempts real Threads execution

Contract note:

- Threads live execution may map the generated thread content into the currently supported publish shape of the existing `ThreadsPublisher`. A full threaded reply chain is not required in this phase.

## Required Inputs

Desktop Phase 9 implementation must support:

- a project with generated content
- saved live credentials from Phase 8
- live publish intent selected from the desktop UI

## Required Outputs

Desktop Phase 9 must produce:

1. Repository outputs
   - publish-service live execution wiring
   - sidecar live publish methods
   - publish route mock/live action controls
   - execution-mode persistence in publish runs

2. Runtime outputs
   - structured live publish results
   - persisted run history across mock and live attempts

3. Inspectable evidence
   - archived publish result artifacts for live attempts
   - smoke reports showing persisted live publish state
   - direct live execution report showing actual provider outcomes in the current environment

## Required Commands and Operator Flows

Desktop Phase 9 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

4. Direct live execution verification
   - `python apps/desktop/scripts/verify-live-publish-execution.py`

Phase 9 must support this operator flow:

1. Open the publish route for a generated project.
2. Save or confirm publish credentials.
3. Run a live publish attempt from the publish route.
4. Inspect the persisted live publish result.
5. Restart the app and confirm the run history remains visible.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 8 functionality is already present and working.
- Existing local `.env` credentials may be used for direct operator verification.
- Because the current local credentials may be missing or expired, Phase 9 verification may complete with structured live errors instead of successful external posts.

## Acceptance Criteria

### A. Execution Mode

- Publish actions explicitly distinguish `mock` and `live`.
- `publish_runs` persist execution mode.

### B. Live Execution

- Carousel live publish attempts execute through the real Instagram publisher path.
- Thread live publish attempts execute through the real Threads publisher path.
- Unsupported live targets return structured `unsupported` results instead of crashing.

### C. Persistence

- Live publish attempts persist archived artifacts and DB history.
- Restart preserves publish run history and execution mode visibility.

### D. Automated Verification

- `pnpm desktop:test` covers live execution persistence or payload wiring.
- Clean `pnpm desktop:smoke` succeeds.
- Restart `pnpm desktop:smoke` confirms persisted live publish state.
- Direct live execution command records actual provider outcomes in the current environment.

## Completion Evidence Required

Desktop Phase 9 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 9 clean `pnpm desktop:smoke` command/result
   - exact phase 9 restart `pnpm desktop:smoke` command/result
   - exact direct live execution command/result

3. Artifact evidence
   - live publish run artifact evidence
   - live execution report evidence

4. Flow evidence
   - evidence that mock/live actions are distinct
   - evidence that live publish responses were persisted
   - evidence that restart preserved live publish history

## Explicit Non-Completion Cases

- publish route still only exposes mock publish
- live publish attempts do not reach the sidecar
- live publish results are not persisted
- unsupported providers crash instead of returning structured results
- restart loses publish run history or execution mode

## Change Control

- Desktop Phase 9 is real publish execution orchestration for the currently supported live providers.
- If successful posting for every provider is pulled into this phase, update the contract first.
