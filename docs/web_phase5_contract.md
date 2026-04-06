# Web Phase 5 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_migration_spec.md](./web_migration_spec.md)

## Goal

Deliver the Phase 5 admin usability and polish layer for the web migration:

- add a real admin session detail page
- separate session creation into a dedicated admin page
- improve waiting and preview handoff UX
- add an optional PWA shell with manifest and offline fallback
- improve baseline mobile and operator readability without changing core workflow states

## Business Outcome

Operators should no longer need to inspect the database or artifact directories manually to understand session status. Customers should have a clearer waiting-state experience, and the app should expose a minimal installable/offline-capable shell.

## In Scope

1. Admin session list polish
   - session list shows stage and links into session detail
   - list remains protected by HTTP Basic auth

2. Admin session detail
   - `GET /admin/sessions/<session_id>` renders a real detail page
   - page shows session identity, stage, key timestamps, customer link, and preview/complete links when relevant
   - page shows recent message history from `session_messages`
   - page shows artifact records from `session_artifacts`

3. Admin session creation page
   - `GET /admin/sessions/new` renders a dedicated create-session page
   - page creates a session for an existing `shop_id`
   - successful creation surfaces the created customer URL clearly

4. Waiting page polish
   - waiting page explains that production is in progress
   - waiting page includes a preview-ready online hint
   - waiting page auto-checks the customer landing route on an interval and transitions naturally once preview is available

5. PWA shell
   - app serves a manifest route
   - app serves a root-scoped service worker route
   - app serves a customer-visible offline fallback page
   - base layout registers the service worker and links the manifest

6. Mobile polish and operator readability
   - admin and customer layouts remain readable on narrow widths
   - tables or dense admin content are wrapped for mobile scanning
   - common status/section styling is improved where needed

## Out of Scope

- new business workflow states
- admin edit flows beyond session creation
- shop CRUD
- server-sent events
- push notifications
- third-party publishing
- advanced PWA install prompts, icon generation, or background sync

## Required Inputs

- existing sessions across multiple stages
- session messages written by earlier phases
- session artifacts written by earlier phases
- valid admin credentials

## Required Outputs

For this phase, the implementation must produce:

- a working admin detail page
- a working admin create page
- a waiting page with automatic re-check behavior
- a manifest route, service worker route, and offline page

## Acceptance Criteria

### A. Admin Session List

- `GET /admin/sessions` remains authenticated.
- The session list page includes links to session detail pages.
- The session list page still supports creating sessions for existing shops.

### B. Admin Session Detail

- `GET /admin/sessions/<session_id>` renders a real HTML page.
- The page shows session id, shop id, stage, and customer URL.
- The page shows session message history.
- The page shows artifact records when artifacts exist.

### C. Admin Session Creation Page

- `GET /admin/sessions/new` renders a real HTML page.
- Admin can create a session from the dedicated page.
- Successful creation displays the created customer URL.

### D. Waiting Page Polish

- `GET /s/<customer_token>/waiting` renders a real HTML page for `awaiting_production`.
- The page includes wording that preview will appear when ready.
- The page includes an automatic re-check mechanism pointing back to the landing route.

### E. PWA Shell

- `GET /manifest.webmanifest` returns manifest JSON.
- `GET /sw.js` returns JavaScript service worker content.
- `GET /offline` returns a real HTML offline fallback page.
- Base layout links the manifest and registers the service worker.

### F. Mobile and UX Polish

- Admin pages remain readable on narrow widths.
- Customer pages continue rendering correctly after the layout changes.
- No existing web-phase automated tests regress.

## Operator Flows Required

1. Open admin session list
2. Open admin create page and create a new session
3. Open an existing session detail page with message/artifact history
4. Open a customer waiting page and confirm the auto-check hint exists
5. Load manifest, service worker, and offline fallback routes

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Existing artifact root and SQLite runtime from earlier web phases
- No additional external APIs are required for verification

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. automated test command(s)
3. manual verification commands or scripted flows
4. pass/fail status for each acceptance group
5. evidence that admin detail shows message and artifact data
6. evidence that waiting page contains the auto-check hint
7. evidence that manifest, service worker, and offline routes are reachable

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- admin detail page is missing
- dedicated create page is missing
- waiting page still behaves like a plain placeholder
- PWA routes are missing or base layout does not reference them
- earlier web-phase tests regress after UI or route changes
