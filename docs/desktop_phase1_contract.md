# Desktop Phase 1 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)

## Goal

Deliver the desktop foundation for the Electron-based Thohago app so development can proceed on a stable local runtime instead of continuing from document-only planning.

Desktop Phase 1 maps to the "Phase A: Foundation" scope in the Electron app spec. Completion means a developer can install dependencies, launch the desktop app locally, complete onboarding, confirm the Python sidecar is connected, and land on a dashboard shell that is ready for later project/interview/content phases.

The business outcome for this phase is simple: turn the Electron desktop plan into a runnable product skeleton with reliable local state, process lifecycle management, and a verifiable operator flow.

## Scope

### In Scope

1. Desktop workspace foundation
   - Create the Node/pnpm workspace needed for desktop development.
   - Add an Electron + React + TypeScript application shell under `apps/desktop/`.
   - Add shared package scaffolding required for sidecar communication under `packages/python-sidecar/`.
   - Add root scripts so the desktop app can be installed, run, and tested from the repository root.

2. Application boot and shell
   - Electron main process boots successfully in local development.
   - Preload bridge exists and only exposes the minimum desktop APIs needed for Phase 1.
   - Renderer starts with a hash-router-based shell.
   - Routes exist for onboarding and dashboard.

3. Plugin/runtime foundation
   - Register and load `thohago-onboarding` and `thohago-sidecar`.
   - Provide a minimal dashboard shell after onboarding completes.
   - Provide a sidecar status surface in the renderer.

4. Python sidecar foundation
   - Implement a single long-lived Python sidecar process reachable over stdio JSON-RPC.
   - Implement at minimum `system.ping`, `system.shutdown`, and one health/status path.
   - Implement Node-side process start/stop/restart logic with basic crash handling.
   - Keep stderr logging visible for local debugging.

5. Settings and persistence foundation
   - Add the first desktop migration set for the Electron app.
   - Persist onboarding state and desktop settings locally through a main-process-owned persistence layer.
   - Store API keys only through the main process, not directly from renderer code.
   - Protect stored API-key values at rest using Electron-safe encryption or a clearly documented fallback.

6. Onboarding flow
   - Implement an activation-gated onboarding wizard.
   - Steps required in Phase 1:
     - Welcome
     - AI API key entry
     - Project folder selection
     - Dependency check for Python and FFmpeg
     - Ready/summary
   - Persist the resulting onboarding state.

7. Local verification support
   - Provide a deterministic local runtime data path override so verification artifacts can be collected outside OS-managed app-data directories.
   - Provide at least one automated test path for desktop foundation code.

### Out of Scope

- Project CRUD
- Media upload
- Interview flow
- STT
- Content generation
- Rendering of blog/carousel/video/thread outputs
- Publishing
- Regeneration controls
- Billing
- macOS packaging and notarization
- Production auto-update flow

## Required Inputs

Phase 1 implementation must support these developer/operator inputs:

- Windows development environment
- Node.js 22+
- pnpm
- Python 3.12+
- Optional FFmpeg installed locally or bundled later
- Optional AI keys

Contract note:

- Live AI credentials are not required to contract-verify Desktop Phase 1.
- If no API key is entered, the onboarding flow may still complete for local foundation verification, but the UI must make it clear that later generation phases will require a valid key.

## Required Outputs

Desktop Phase 1 must produce these outputs:

1. Repository outputs
   - root Node workspace files required to run the desktop app
   - `apps/desktop/` app shell
   - `packages/python-sidecar/` client package
   - `sidecar/server.py` and supporting Python sidecar files
   - initial desktop migration file(s)

2. Runtime outputs
   - a local desktop data directory containing a SQLite database
   - onboarding settings persisted in that database
   - sidecar runtime logs or equivalent inspectable process evidence

3. UX outputs
   - onboarding screen when onboarding is incomplete
   - dashboard shell when onboarding is complete
   - sidecar connected/disconnected status visible in the UI

## Required Commands and Operator Flows

Phase 1 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Run desktop app in development
   - `pnpm desktop:dev`

3. Run automated tests for desktop foundation
   - `pnpm desktop:test`

Phase 1 must support this operator flow:

1. Launch the app with a clean desktop data directory.
2. See onboarding instead of dashboard.
3. Enter or skip API keys according to the phase rules.
4. Choose a project root folder.
5. Run dependency check and see Python/FFmpeg status.
6. Complete onboarding.
7. Land on dashboard shell.
8. Confirm sidecar shows connected state.
9. Close the app cleanly and confirm settings persist on next launch.

## Dependencies, Credentials, and Environment Assumptions

- Desktop runtime is developed and verified on Windows first.
- Python sidecar uses the local Python interpreter in development unless the implementation explicitly documents another local strategy.
- The desktop app must support a repo-local data directory override for verification, for example through an env var such as `THOHAGO_DESKTOP_DATA_DIR`.
- Secrets required for later phases may be absent during Phase 1 verification.
- The implementation must not require live Gemini, Anthropic, OpenAI, Groq, or Naver access to prove the Phase 1 foundation.

## Acceptance Criteria

### A. Workspace and App Bootstrap

- `pnpm install` completes successfully from the repository root.
- `pnpm desktop:dev` launches the Electron desktop application.
- The renderer loads without a blank screen or fatal bootstrap exception.
- The application shell uses the new desktop workspace rather than ad hoc scripts only.

### B. Activation Gate

- When onboarding is incomplete, the app opens into onboarding instead of dashboard.
- When onboarding is complete, the app opens into dashboard instead of onboarding.
- Onboarding completion state is persisted and survives app restart.

### C. Onboarding Flow

- The onboarding wizard includes all required Phase 1 steps from this contract.
- The project folder selection is persisted.
- Dependency check surfaces Python and FFmpeg availability clearly.
- The API key step persists entered values through the main process only.
- The UI makes it explicit when the user has chosen to proceed without a validated AI key for local foundation-only verification.

### D. Settings and Local Persistence

- A SQLite database is created under the configured desktop data directory.
- The initial migration set is applied automatically on first run.
- Onboarding-related settings are stored and can be inspected through the database.
- API-key values are not stored as plain renderer-managed text files.
- The persistence layer is owned by the main process or a dedicated backend layer, not by direct renderer filesystem access.

### E. Python Sidecar Lifecycle

- The Electron main process can start the Python sidecar.
- The sidecar responds successfully to `system.ping`.
- The sidecar can be shut down gracefully.
- The UI exposes sidecar status in a way that is visible during manual verification.
- Sidecar startup errors are surfaced clearly enough for a developer to diagnose them locally.

### F. Dashboard Shell

- After onboarding completes, the app routes to a dashboard shell.
- The dashboard shell does not need project CRUD yet, but it must be a real routed screen, not an empty placeholder window.
- The dashboard visibly shows enough desktop runtime state to prove the app is alive, at minimum app identity and sidecar status.

### G. Automated Verification

- `pnpm desktop:test` executes at least one automated test suite for the desktop foundation.
- Automated verification covers at least one of:
  - onboarding state gate behavior
  - settings persistence
  - sidecar ping lifecycle
  - migration bootstrap

### H. Local Inspectability

- A developer can point the app at a repo-local data directory and inspect the produced DB/log artifacts after a run.
- The app can be restarted against the same local data directory and recover the onboarding-complete state.

## Completion Evidence Required

Desktop Phase 1 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact runtime data directory path

2. Command evidence
   - exact `pnpm install` command/result
   - exact `pnpm desktop:dev` command/result
   - exact `pnpm desktop:test` command/result

3. Runtime artifact evidence
   - produced SQLite DB path
   - evidence that onboarding settings were persisted
   - evidence that sidecar ping succeeded
   - evidence that app restart preserved onboarding completion

4. Manual flow evidence
   - onboarding shown before completion
   - dashboard shown after completion
   - dependency check result captured
   - sidecar connected state captured

## Explicit Non-Completion Cases

Desktop Phase 1 is not complete if any of the following is true:

- the repository has a desktop spec but still no runnable desktop app
- the app boots but onboarding state is not persisted
- the sidecar process exists but no verified `system.ping` path is wired end-to-end
- the renderer writes secrets directly to disk without a main-process-controlled persistence layer
- the app only works with OS-specific hidden app-data paths and cannot produce inspectable local verification artifacts
- the dashboard route does not exist after onboarding
- the implementation requires live AI credentials to verify the foundation
- verification is based on screenshots or claims without commands and artifact paths

## Change Control

- This contract governs the first desktop implementation pass only.
- If Phase 1 implementation reveals a better command shape, persistence path, or onboarding gating approach, update this contract before treating the new behavior as done.
- This contract does not replace the existing `docs/v1/` web/Telegram history. It defines the desktop track going forward.
