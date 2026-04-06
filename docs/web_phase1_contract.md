# Web Phase 1 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_migration_spec.md](./web_migration_spec.md)

## Goal

Deliver the Phase 1 web foundation for the Telegram-to-web migration:

- create customer web sessions for existing shops
- persist session state in SQLite
- create the canonical artifact directory for each session
- expose a minimal FastAPI app that can resolve a customer token and route the customer to the correct page
- expose a minimal authenticated admin flow to create and inspect sessions

This phase is a foundation phase only. It does not include file upload, interview capture, STT, or preview rendering.

## Business Outcome

An operator must be able to create a valid customer session link for an existing shop and verify that the link resolves to a real session in the web runtime.

## In Scope

1. Web runtime foundation
   - `src/thohago/web/` package exists
   - FastAPI app factory exists
   - route modules exist for customer and admin surfaces
   - base template and minimum page templates exist

2. Web configuration
   - config supports web database path
   - config supports web base URL
   - config supports admin credentials
   - config supports sync API token
   - config supports Phase 1 upload policy defaults for later phases

3. SQLite runtime foundation
   - a lightweight database initialization path exists
   - Phase 1 tables exist for sessions, media files, session messages, and session artifacts

4. Session creation and persistence
   - operator can create a session for an existing `shop_id`
   - session creation writes a DB row and an artifact directory
   - session creation writes `session_metadata.json`
   - session creation generates a unique customer token

5. Customer token routing
   - `GET /s/<customer_token>` resolves the session
   - the session landing route redirects based on stage
   - `collecting_media` resolves to an upload placeholder page

6. Minimal admin surface
   - admin routes are protected with HTTP Basic auth
   - operator can list sessions
   - operator can create a session from the admin surface for an existing shop

7. CLI support
   - CLI provides a database initialization command
   - CLI provides a session creation command for an existing shop

## Out of Scope

- customer media upload handling
- customer media deletion
- media preflight
- interview recording or text answer submission
- STT
- planner generation
- `intake_bundle.json`
- sync pull/push endpoints
- preview rendering
- approval or revision flow
- full admin dashboard beyond session list/create
- running a production ASGI server from CLI

## Required Inputs

- valid `shop_id` from the existing JSON shop registry
- configured artifact root path
- configured SQLite database path
- configured web base URL

## Required Outputs

For every created web session, the implementation must produce:

- one row in `sessions`
- one artifact directory under `runs/<shop_id>/<session_id>/`
- one `session_metadata.json` file
- one customer URL derived from `THOHAGO_WEB_BASE_URL` and the generated token

## Acceptance Criteria

### A. Web Package Foundation

- `src/thohago/web/` exists and is importable.
- The app factory can build a FastAPI app without starting an external server.
- Customer and admin route modules are mounted by the app factory.

### B. Config and Database

- `load_config()` returns web-specific settings required by this phase.
- A database initialization path can create the required SQLite schema from an empty file.
- The schema contains `sessions`, `media_files`, `session_messages`, and `session_artifacts`.

### C. Session Creation

- A session can be created for a registered `shop_id` without manual file creation.
- Session creation fails clearly for an unknown `shop_id`.
- Session creation writes `session_metadata.json` into the new artifact directory.
- The created session starts in `collecting_media`.
- The returned customer URL contains the generated customer token.

### D. Customer Routing

- `GET /s/<customer_token>` returns a redirect for a known session.
- A `collecting_media` session redirects to `/s/<customer_token>/upload`.
- `GET /s/<customer_token>/upload` renders a real HTML page with session/shop context.
- Unknown customer tokens return a 404 response.

### E. Admin Routing

- Admin routes require HTTP Basic auth.
- Authenticated admin users can load the session list page.
- Authenticated admin users can create a session for a valid `shop_id`.

### F. CLI Entry Points

- A CLI command can initialize the web database.
- A CLI command can create a web session and print the resulting identifiers and customer URL.

## Operator Flows Required

The phase is only complete if these flows exist and can be verified:

1. CLI flow
   - initialize DB
   - create session for `sisun8082`
   - capture printed customer URL

2. App flow
   - open the customer URL path in the FastAPI app
   - verify redirect to the upload placeholder page

3. Admin flow
   - access `/admin/sessions` without credentials and observe rejection
   - access `/admin/sessions` with credentials and observe session list
   - create a session through the admin surface

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Shop registry source: checked-in JSON config
- Secrets:
  - `THOHAGO_ADMIN_USERNAME`
  - `THOHAGO_ADMIN_PASSWORD`
  - `THOHAGO_SYNC_API_TOKEN`
- FastAPI and Jinja2 are available in the environment

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. exact commands executed
3. exact test command executed
4. pass/fail status for every acceptance criterion group
5. generated DB file path
6. generated artifact directory path
7. generated `session_metadata.json` path
8. printed customer URL evidence
9. evidence that customer landing redirects to upload
10. evidence that admin auth rejects unauthenticated access

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- session creation exists only in memory and does not persist to SQLite
- artifact directories are not created during session creation
- the customer token route does not resolve sessions
- admin routes are left unauthenticated
- the CLI cannot create a real session
- verification does not include concrete command and artifact evidence
