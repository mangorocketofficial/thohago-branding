# Web Phase 4 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_migration_spec.md](./web_migration_spec.md)

## Goal

Deliver the sync bridge and preview flow for the web migration so that a session can move from `awaiting_production` to either `awaiting_approval`, `revision_requested`, or `approved`.

This phase must connect the completed intake flow to a local production workstation:

- authenticated sync API for listing and downloading sessions
- authenticated sync API for uploading preview artifacts and a manifest
- CLI commands for `list`, `pull`, and `push`
- customer preview page that renders uploaded artifacts
- approval and revision request flow from the customer link

## Business Outcome

After a customer finishes the interview, an operator must be able to pull the intake package to a local machine, produce preview artifacts, push them back to the server, and have the customer approve or request revision from the same link.

## Scope Decision

This phase focuses on the bridge between completed intake and customer preview.

Out of the broader future publishing workflow, the following remain deferred:

- direct third-party publish from the server
- operator messaging over SSE
- admin dashboard detail pages beyond existing minimal surfaces

## In Scope

1. Sync API auth
   - sync API routes require Bearer token auth
   - unauthenticated sync requests are rejected

2. Sync session listing
   - API can list sessions by stage
   - CLI can list sessions for a requested stage

3. Sync download
   - API can return a zip of a session artifact directory
   - CLI can download and extract the session zip locally

4. Sync upload
   - API can accept a preview bundle zip plus manifest JSON
   - uploaded files are unpacked into `published/`
   - `published/manifest.json` is written
   - uploaded preview artifacts are indexed in `session_artifacts`
   - session stage changes to `awaiting_approval`

5. Preview page
   - customer preview page renders from the uploaded manifest
   - preview page can show video, blog HTML, thread text, and carousel image assets when present

6. Approval flow
   - customer can approve preview content
   - customer can request revision
   - approve changes stage to `approved`
   - revision request changes stage to `revision_requested`

## Out of Scope

- platform publishing to Naver/Instagram/Threads
- notification delivery after preview becomes available
- SSE
- admin-driven revision notes UI
- rich preview styling beyond necessary functional rendering
- chunked sync uploads

## Required Inputs

- a valid session already in `awaiting_production`
- an authenticated sync client
- a manifest describing preview artifacts
- a preview bundle archive containing files referenced by the manifest

## Required Outputs

For a successful preview push, the implementation must produce:

- files under `published/`
- `published/manifest.json`
- `session_artifacts` rows for the manifest and pushed preview assets
- updated `session_metadata.json`
- a session row whose stage is `awaiting_approval`

For approval flow, the implementation must additionally produce:

- updated `sessions.stage`
- updated `session_messages`
- updated `chat_log.jsonl`

## Acceptance Criteria

### A. Sync Auth

- `GET /api/sync/sessions` rejects requests without a valid Bearer token.
- `GET /api/sync/sessions` succeeds with a valid Bearer token.

### B. Sync List

- API can list `awaiting_production` sessions.
- API can list `revision_requested` sessions when requested by stage.
- CLI can list sessions from the sync API.

### C. Sync Download

- API can download a zip of a session artifact directory.
- The zip contains `generated/intake_bundle.json` for a completed intake session.
- CLI can pull and extract the session zip locally.

### D. Sync Upload

- API can accept a preview bundle upload with manifest JSON.
- Upload writes files under `published/`.
- Upload writes `published/manifest.json`.
- Upload records `session_artifacts` for the pushed assets.
- Upload changes session stage to `awaiting_approval`.
- CLI can push a local preview directory plus manifest to the sync API.

### E. Preview Page

- `GET /s/<customer_token>/preview` renders a real HTML page for `awaiting_approval`.
- Preview page renders manifest-driven sections for at least one uploaded preview asset.
- Session landing redirects to `/s/<customer_token>/preview` for `awaiting_approval`.

### F. Approval and Revision

- `POST /s/<customer_token>/approval` with approve changes stage to `approved`.
- `POST /s/<customer_token>/approval` with revision changes stage to `revision_requested`.
- Session landing redirects to `/s/<customer_token>/complete` for `approved`.
- Session landing redirects back to `/s/<customer_token>/preview` for `revision_requested`.

## Operator Flows Required

1. Prepare a session in `awaiting_production`
2. List the session through sync API or CLI
3. Pull the session locally
4. Push a preview bundle and manifest back to the server
5. Open the customer preview page
6. Approve once and request revision once on separate sessions or separate checks

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Existing artifact root and SQLite runtime from Web Phase 3
- Local verification may use a lightweight local ASGI server instance
- Preview bundle files can be simple local fixtures; real rendered media is not required for verification

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. automated test command(s)
3. manual verification commands or scripted flows
4. produced artifact paths for:
   - pulled intake bundle
   - pushed `published/manifest.json`
   - at least one pushed preview asset
5. pass/fail status for each acceptance group
6. evidence that preview push changes stage to `awaiting_approval`
7. evidence that approval and revision actions update stage correctly
8. evidence that CLI `list`, `pull`, and `push` work against the sync API

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- sync API is left unauthenticated
- list works but download or upload is missing
- CLI exists but does not actually call the sync API
- preview assets are uploaded but preview page still shows only a placeholder
- approval or revision request does not change session stage
- session landing does not redirect to preview or complete according to state
