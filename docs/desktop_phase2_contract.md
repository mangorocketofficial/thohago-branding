# Desktop Phase 2 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase1_contract.md](./desktop_phase1_contract.md), [desktop_phase1_verification.md](./desktop_phase1_verification.md)

## Goal

Deliver the first usable project workflow on top of the verified desktop foundation:

- create a project,
- import media into a project-owned folder,
- run deterministic media preflight through the Python sidecar,
- complete a 3-turn text-first interview,
- persist the resulting project/interview state for later generation phases.

Desktop Phase 2 maps to the "Phase B: Project + Interview" portion of the Electron app spec, but it intentionally narrows the interview to a text-first, locally verifiable flow. Microphone capture and live STT are deferred until a later phase.

The business outcome for this phase is that the desktop app stops being only a shell and becomes a working local operator tool for setting up one business project and finishing the structured interview that later generation depends on.

## Scope

### In Scope

1. Project data model and persistence
   - Add desktop tables needed for projects, media assets, and interview sessions.
   - Persist project identity, local project folder path, project status, media order, representative photo, and interview state.

2. Dashboard project flow
   - Show project list on the dashboard.
   - Add a real `#/project/new` flow for project creation.
   - Add a real `#/project/:id` project view route.

3. Project creation
   - Create a project from desktop UI fields at minimum:
     - internal project name
     - shop display name
     - short business summary or notes
   - Create a project-owned folder under the configured onboarding project root.
   - Persist a project manifest that is inspectable from disk.

4. Media import baseline
   - Import local photos/videos into the project-owned media folder.
   - Support the contract verification range of:
     - photos: 1 to 10
     - videos: 0 to 2
   - Persist imported media metadata and stable media IDs.
   - Allow the user to adjust media order and set one representative media asset.

5. Deterministic media preflight
   - Use the Python sidecar to build a deterministic local preflight result from imported media metadata.
   - Persist the latest preflight result in the database and as an inspectable project artifact.
   - Surface the preflight summary in the project view.

6. Text-first 3-turn interview
   - Add a real `#/project/:id/interview` route.
   - Start an interview session from the project view once media exists.
   - Turn 1 is a fixed opening question.
   - Turn 2 and Turn 3 are generated through the Python sidecar from the stored preflight and prior answers.
   - Users answer through text input.
   - Persist interview questions, answers, session status, and latest planner outputs.

7. Inspectable project artifacts
   - Write project-level JSON artifacts that make the state inspectable without querying the database only.
   - At minimum:
     - `project.json`
     - `preflight/media_preflight.json`
     - `interview/interview_session.json`

8. Local verification support
   - Extend the smoke/automation path so Desktop Phase 2 can be verified without manual clicking.
   - The smoke flow must exercise project creation, media import, preflight, and all 3 interview turns.

### Out of Scope

- Microphone recording with `MediaRecorder`
- Waveform visualization
- Voice-to-text / STT
- AI-powered content generation
- Rendering blog/carousel/video/thread outputs
- Publishing
- Regeneration
- Billing
- Multi-user synchronization or cloud persistence

## Required Inputs

Desktop Phase 2 implementation must support these operator inputs:

- the verified Desktop Phase 1 runtime
- one onboarded desktop data directory
- project name
- shop display name
- optional summary/notes
- local media file paths
- three text answers for the interview

Contract note:

- Live AI credentials are not required for Desktop Phase 2 verification.
- Phase 2 uses deterministic local turn planning and preflight so verification remains reproducible.

## Required Outputs

Desktop Phase 2 must produce:

1. Repository outputs
   - project/interview migration file(s)
   - project/interview desktop routes and UI components
   - main-process services or equivalent modules for project and interview state
   - sidecar methods for media preflight and interview turn planning

2. Runtime outputs
   - persisted project records in the desktop DB
   - persisted media asset records
   - persisted interview session records
   - project-owned media copies under the configured project root

3. Inspectable filesystem artifacts
   - `project.json`
   - `preflight/media_preflight.json`
   - `interview/interview_session.json`

## Required Commands and Operator Flows

Desktop Phase 2 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

Phase 2 must support this operator flow:

1. Launch the app with an onboarded local data directory.
2. Create a new project.
3. Land on the project detail screen.
4. Import local media files.
5. Confirm imported media is copied into the project folder.
6. Adjust order or representative media if needed.
7. Run or refresh media preflight.
8. Start interview.
9. Submit three text answers.
10. Return to project view with interview marked complete.
11. Restart the app and confirm the project and interview state persist.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Python sidecar continues to run through the local Python interpreter in development.
- The desktop data directory override from Phase 1 remains available and is used for verification.
- Verification may use checked-in local media fixtures already present in this repository.
- No live provider keys are required to contract-verify Phase 2.

## Acceptance Criteria

### A. Project CRUD Baseline

- A user can create a project from the desktop UI.
- The project appears on the dashboard after creation.
- The project can be reopened from the dashboard after app restart.
- The project has a dedicated project-owned folder under the configured onboarding project root.

### B. Media Import

- The app can import at least 1 photo into a project without manual file copying.
- Imported files are copied into the project media folder.
- Media metadata is stored in the desktop DB with stable IDs and order.
- The user can mark one media asset as the representative asset.

### C. Media Preflight

- The app can call the Python sidecar to build media preflight for an imported project.
- Preflight output is persisted both in the DB path and as `preflight/media_preflight.json`.
- The project view surfaces the preflight summary.

### D. Interview Session

- A user can start a 3-turn interview from the project view.
- Turn 1 is fixed.
- Turn 2 and Turn 3 are generated from the sidecar using the stored preflight and previous answers.
- Text answers are persisted after each turn.
- Interview completion is visible in the UI and stored in persistence.

### E. Inspectable Artifacts

- `project.json` exists under the project folder.
- `preflight/media_preflight.json` exists after preflight.
- `interview/interview_session.json` exists after interview start and updates as answers are submitted.

### F. Route and UI Coverage

- `#/project/new` is a real route.
- `#/project/:id` is a real route.
- `#/project/:id/interview` is a real route.
- Dashboard, project view, and interview view each render meaningful state rather than placeholder-only text.

### G. Automated Verification

- `pnpm desktop:test` covers at least one project/interview persistence behavior and one sidecar planning/preflight behavior.
- `pnpm desktop:smoke` completes successfully against a repo-local data directory.
- Smoke verification covers project creation, media import, preflight, and three submitted interview answers.

### H. Persistence After Restart

- After the Phase 2 smoke or manual flow completes, restarting the app against the same data directory preserves:
  - project list
  - selected representative media
  - latest preflight
  - completed interview state

## Completion Evidence Required

Desktop Phase 2 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for Phase 2 verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact `pnpm desktop:smoke` command/result

3. Artifact evidence
   - desktop DB path
   - project folder path
   - copied media file path(s)
   - `project.json`
   - `preflight/media_preflight.json`
   - `interview/interview_session.json`

4. Flow evidence
   - evidence that a project was created
   - evidence that media import completed
   - evidence that preflight completed
   - evidence that all 3 turns were answered
   - evidence that the project/interview state persisted after restart

## Explicit Non-Completion Cases

Desktop Phase 2 is not complete if any of the following is true:

- the app still has no real project creation flow
- media must be copied manually into project folders outside the app flow
- no project-owned artifact folder exists
- preflight is only mocked in UI and not wired through the sidecar
- interview questions exist only in renderer state and are not persisted
- the interview cannot be resumed or inspected after restart
- verification skips the 3-turn interview or does not record artifact paths

## Change Control

- Desktop Phase 2 is the first project/interview pass for the desktop track.
- If voice capture or STT is pulled earlier, the contract must be updated first.
- If the deterministic local preflight/turn planner is replaced by a live AI path, the contract must be updated before verification.
