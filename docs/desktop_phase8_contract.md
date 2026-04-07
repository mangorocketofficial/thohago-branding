# Desktop Phase 8 Contract

> Status: Active  
> Date: 2026-04-07  
> Workflow: [v1/phase_workflow.md](./v1/phase_workflow.md)  
> Reference: [electron_app_spec.md](./electron_app_spec.md)  
> Depends On: [desktop_phase7_contract.md](./desktop_phase7_contract.md), [desktop_phase7_verification.md](./desktop_phase7_verification.md)

## Goal

Deliver live publishing credential integration and provider validation on top of the verified mock publish flow:

- store publishing credentials in the desktop app,
- expose live-provider validation from the publish route,
- persist validation results,
- surface live readiness or failure clearly after restart.

Desktop Phase 8 is intentionally scoped to credential integration and live validation readiness. It does not require successful real-world posting to external platforms in this phase.

The business outcome is that the desktop app no longer stops at mock publish only. It becomes a credential-aware publishing tool that can tell the operator whether Instagram/Threads/Naver live publishing is ready, missing, unsupported, or failing.

## Scope

### In Scope

1. Publish credential persistence
   - Persist live publishing credentials or notes in desktop settings.
   - Support at minimum:
     - Meta access token
     - Instagram business account id
     - Facebook page id
     - Instagram graph version
     - Threads access token
     - Threads user id
     - Naver live note or placeholder field

2. Publish route credential UI
   - Extend `#/project/:id/publish` with credential fields.
   - Allow saving updated publish credentials from the desktop UI.

3. Provider validation
   - Add validation actions for:
     - Instagram
     - Threads
     - Naver
   - Validation results must be structured and persisted.
   - Validation results may be:
     - `ok`
     - `missing`
     - `error`
     - `unsupported`

4. Readiness/status surfacing
   - The publish route must show credential presence and last validation result.
   - Validation status must survive restart.

5. Local verification support
   - Extend automated tests to cover credential persistence and validation behavior.
   - Extend smoke verification so phase 8 persists credential placeholders and confirms the publish route reflects them after restart.
   - Run direct live validation attempts where feasible in the current environment and record the real outcomes.

### Out of Scope

- Guaranteed successful live publishing to external platforms
- Real Naver Blog posting
- Production-ready Reels video upload
- Credential autofill from cloud secret managers

## Required Inputs

Desktop Phase 8 implementation must support:

- a project with generated/publishable content
- operator-entered publishing credentials

Contract note:

- Phase 8 verification may complete even if live credentials are invalid or expired, as long as the app surfaces the failure clearly and persists the validation result.

## Required Outputs

Desktop Phase 8 must produce:

1. Repository outputs
   - settings and publish-service changes for live credentials
   - publish route credential UI
   - provider validation methods

2. Runtime outputs
   - persisted credential presence/status
   - persisted provider validation results

3. Inspectable evidence
   - settings records for publish credentials
   - validation result records

## Required Commands and Operator Flows

Desktop Phase 8 must expose and document these commands or equivalent root-level commands:

1. Install
   - `pnpm install`

2. Desktop tests
   - `pnpm desktop:test`

3. Desktop smoke verification
   - `pnpm desktop:smoke`

Phase 8 must support this operator flow:

1. Open the publish route for a project.
2. Save live publishing credentials or placeholders.
3. Run Instagram validation.
4. Run Threads validation.
5. Run Naver validation.
6. Restart the app and confirm the saved credential presence and validation state remain visible.

## Dependencies, Credentials, and Environment Assumptions

- Windows remains the primary verification environment.
- Desktop Phase 7 functionality is already present and working.
- Existing local `.env` credentials may be used for direct manual validation evidence, but the desktop app itself must persist credentials through its own settings layer.

## Acceptance Criteria

### A. Credential Persistence

- The publish route allows saving live publishing credentials.
- Saved credential presence is reflected in the UI.
- Saved credential presence survives restart.

### B. Provider Validation

- Instagram validation executes and returns a structured result.
- Threads validation executes and returns a structured result.
- Naver validation executes and returns a structured result.
- Validation results are persisted and survive restart.

### C. Publish Route UX

- The publish route shows meaningful credential state.
- The publish route shows meaningful validation state.
- Mock publish actions remain available and are not broken by the new credential layer.

### D. Automated Verification

- `pnpm desktop:test` covers credential persistence or validation behavior.
- Clean `pnpm desktop:smoke` succeeds.
- Restart `pnpm desktop:smoke` confirms persisted credential state.

## Completion Evidence Required

Desktop Phase 8 is contract-verified only when the verification document contains:

1. Environment evidence
   - Windows environment used
   - Node, pnpm, and Python versions
   - exact desktop data directory used for verification

2. Command evidence
   - exact `pnpm desktop:test` command/result
   - exact phase 8 clean `pnpm desktop:smoke` command/result
   - exact phase 8 restart `pnpm desktop:smoke` command/result
   - any direct live validation command(s) executed

3. Artifact evidence
   - publish credential/validation persistence evidence

4. Flow evidence
   - evidence that credential fields were saved
   - evidence that provider validation results were surfaced
   - evidence that restart preserved the state

## Explicit Non-Completion Cases

- credential fields only exist in renderer state and are not persisted
- validation actions are dead buttons
- validation results are not stored
- restart loses credential or validation state

## Change Control

- Desktop Phase 8 is credential integration and live validation readiness only.
- If guaranteed real posting is pulled into this phase, update the contract first.
