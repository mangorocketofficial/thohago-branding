# Thohago Web Migration Specification v2

## From Telegram Bot to FastAPI + HTMX Server-Rendered Web Intake

**Date:** 2026-04-01  
**Status:** Draft v2  
**Author:** Thohago Engineering

---

## 1. Summary

Replace the customer-facing Telegram Bot flow with a server-rendered mobile web app opened from a KakaoTalk link.

The v1 draft had the right product direction, but several assumptions were too loose to implement safely:

- it treated SQLite as a full replacement for the existing artifact tree
- it assumed zero orchestration changes while also splitting server intake and local production
- it mixed customer access, admin access, and sync API access without a concrete auth boundary
- it used SSE for too many responsibilities

This v2 spec locks the architecture around the current codebase so implementation can start immediately.

### Primary goal

Customers should be able to:

1. open a KakaoTalk link
2. upload media
3. complete a 3-turn voice or text interview
4. leave the page

with no install and no account creation.

### Product goal for MVP

Deliver a working loop:

1. operator creates a session link
2. customer uploads media and completes interview
3. local workstation pulls the intake bundle
4. operator produces content locally
5. local workstation pushes preview artifacts
6. customer opens the same link and approves or requests revision

### Non-goals for MVP

- rewriting the interview engines or content engines
- moving shop configuration fully into a database
- building a full admin dashboard before customer flow works
- adding customer accounts or password login
- guaranteeing push notifications after the customer closes the page
- adding Redis, Postgres, or chunked uploads on day one

---

## 2. Locked Decisions

These are implementation decisions, not suggestions.

### 2.1 Source of truth

- `runs/<shop_id>/<session_id>/` remains the canonical artifact store
- SQLite is a runtime index and state store, not a replacement for artifact files
- the server always writes artifacts in the same directory structure the current tooling expects

Rationale: the current code already depends on artifact directories, transcript files, planner files, and `chat_log.jsonl`. Replacing that all at once would create unnecessary migration risk.

### 2.2 Shop registry

- shop definitions remain file-based in `config/shops*.json` for MVP
- SQLite does not own shop CRUD in MVP
- session creation validates `shop_id` against the loaded registry at runtime

Rationale: the current runtime already loads shops from JSON and uses them for profile, publish targets, and media hints. Moving shops to DB can happen later.

### 2.3 Reuse boundary

The following modules are treated as reusable core logic:

- `src/thohago/interview_engine.py`
- `src/thohago/groq_live.py`
- `src/thohago/openai_live.py`
- `src/thohago/anthropic_live.py`
- `src/thohago/content.py`
- `src/thohago/models.py`
- `src/thohago/artifacts.py`

The following modules will change because they are orchestration layers:

- `src/thohago/cli.py`
- new `src/thohago/web/*`
- optional small adapters around session creation, sync, and auth

### 2.4 Session access model

- customer access uses a single opaque URL token: `/s/<customer_token>`
- admin and sync access are separate from customer tokens
- there is no customer login, cookie dependency, or account system

### 2.5 Operator auth model

MVP uses two simple, explicit auth mechanisms:

- admin UI: HTTP Basic auth from environment variables
- sync API: Bearer token from environment variables

Customer tokens must never grant access to admin or sync endpoints.

### 2.6 SSE scope

SSE is useful, but only for live UX.

MVP SSE responsibilities:

- STT progress and transcript-ready events during voice recording
- optional online-only status hint when preview becomes available

MVP SSE does **not** guarantee event replay after disconnect.

Reconnect strategy:

- on reconnect or page refresh, the server renders the current page from SQLite state plus artifact files
- SSE is treated as best-effort enhancement, not as the authoritative state channel

### 2.7 Upload policy

MVP upload limits are intentionally narrow:

- photos: up to 5
- videos: up to 1
- video duration: up to 60 seconds

Customer may delete and re-upload before pressing "Next".

Rationale: the current preflight logic already centers on a small representative photo set. Hard limits are simpler and reduce mobile upload edge cases.

### 2.8 Turn progression

The server runs only intake-time work:

- media preflight
- turn question planning
- transcript artifact writing
- intake bundle export

The server does **not** run final content generation after turn 3 in MVP.

After turn 3:

- session stage becomes `awaiting_production`
- server writes an `intake_bundle.json`
- local workstation takes over via sync CLI

---

## 3. Current Code Constraints

The current implementation already tells us what must be preserved.

### 3.1 Artifact contract already exists

Current code writes and reads:

- `chat_log.jsonl`
- `raw/`
- `planners/`
- `transcripts/`
- `generated/`
- `published/`

This contract must remain intact because it is the lowest-risk bridge between the old bot flow and the new web flow.

### 3.2 Telegram logic is not the core product logic

Telegram-specific concerns can be removed:

- Bot API polling
- Telegram file download
- inline button transport
- chat-id session binding

But the following behavioral logic should be preserved:

- stage transitions
- fallback interview engine selection
- transcript confirmation flow
- planner generation after confirmed answers
- artifact writing and chat log append

### 3.3 Session completion is currently too eager

The Telegram implementation calls `finalize_session()` after the third confirmed answer.

That behavior is incompatible with the target architecture because local production is supposed to happen later on a workstation.

Therefore:

- web intake flow must stop before `finalize_session()`
- local production flow owns rendered output generation
- `published/` becomes the place where pushed preview artifacts land

---

## 4. Target Architecture

### 4.1 High-level architecture

```text
Customer phone
  -> HTTPS -> FastAPI web server
               - Jinja2 templates
               - HTMX partials
               - SSE for live STT UX
               - SQLite session index
               - runs/ artifact storage
               - shop registry loaded from JSON

Local workstation
  -> Bearer-auth sync API
               - list awaiting production sessions
               - download intake bundle zip
               - upload preview artifacts + manifest

Operator browser
  -> HTTP Basic admin UI
               - session list
               - session detail
               - create link for existing shop
```

### 4.2 Canonical runtime responsibilities

#### Server responsibilities

- serve customer pages
- accept uploads and interview input
- write artifacts to `runs/`
- store session metadata in SQLite
- serve preview and approval pages
- expose sync API for workstation pull/push

#### Local workstation responsibilities

- pull intake bundle
- run existing local production scripts
- upload preview artifacts and manifest

#### Deferred responsibilities

- Kakao Alimtalk or SMS
- one-click publish to third-party platforms from the server
- full shop CRUD UI

---

## 5. Session Model

### 5.1 Session identifiers

- `session_id`: canonical internal identifier and artifact folder name
- `session_key`: human-readable date-oriented label used by operators
- `customer_token`: opaque token embedded in customer URL

Recommended mapping:

- `session_id = <session_key>-<timestamp>Z`
- `artifact_dir = runs/<shop_id>/<session_id>/`

This matches the current artifact generator pattern.

### 5.2 Session stages

The stage model should remain intentionally close to the existing Telegram flow:

```text
collecting_media
  -> awaiting_turn1_answer
  -> confirming_turn1
  -> awaiting_turn2_answer
  -> confirming_turn2
  -> awaiting_turn3_answer
  -> confirming_turn3
  -> awaiting_production
  -> awaiting_approval
  -> revision_requested
  -> approved
  -> completed
```

Additional non-customer-facing status fields may exist, but the stage names above are the canonical external workflow states.

### 5.3 Resume behavior

Refreshing or reopening the same customer link must:

- look up the session by `customer_token`
- inspect current stage
- redirect to the correct page

Rules:

- `collecting_media` -> upload page
- `awaiting_turn*` or `confirming_turn*` -> interview page
- `awaiting_production` -> waiting page
- `awaiting_approval` or `revision_requested` -> preview page
- `approved` or `completed` -> completion page

---

## 6. Artifact Contract

### 6.1 Required artifact tree

For each session, the server writes:

```text
runs/<shop_id>/<session_id>/
  chat_log.jsonl
  session_metadata.json
  raw/
    photo_01.jpg
    photo_02.jpg
    video_01.mp4
    turn1_audio.webm
    turn2_audio.webm
    turn3_audio.webm
  planners/
    turn1_question.txt
    turn1_planner.json          # optional when generated by engine
    turn2_question.txt
    turn2_planner.json
    turn3_question.txt
    turn3_planner.json
  transcripts/
    turn1_transcript.txt
    turn1_transcript.json
    turn2_transcript.txt
    turn2_transcript.json
    turn3_transcript.txt
    turn3_transcript.json
  generated/
    media_preflight.json
    intake_bundle.json
  published/
    manifest.json
    shorts/
    carousel/
    blog/
    threads/
```

### 6.2 New file introduced by v2: `generated/intake_bundle.json`

The web server writes `intake_bundle.json` after turn 3 is confirmed.

Purpose:

- create a stable download target for local production
- avoid calling `finalize_session()` on the server
- give the workstation all confirmed intake inputs in one place

Minimum payload:

```json
{
  "shop_id": "sisun8082",
  "session_id": "live_20260401T090000-20260401T090000Z",
  "session_key": "live_20260401T090000",
  "stage": "awaiting_production",
  "artifact_dir": "runs/sisun8082/live_20260401T090000-20260401T090000Z",
  "preflight_path": "generated/media_preflight.json",
  "turn1_question_path": "planners/turn1_question.txt",
  "turn2_planner_path": "planners/turn2_planner.json",
  "turn3_planner_path": "planners/turn3_planner.json",
  "transcript_paths": [
    "transcripts/turn1_transcript.json",
    "transcripts/turn2_transcript.json",
    "transcripts/turn3_transcript.json"
  ],
  "raw_media": [
    "raw/photo_01.jpg",
    "raw/photo_02.jpg",
    "raw/video_01.mp4"
  ]
}
```

### 6.3 Published artifact manifest

The workstation uploads preview outputs together with `published/manifest.json`.

Minimum manifest fields:

```json
{
  "session_id": "live_20260401T090000-20260401T090000Z",
  "status": "preview_ready",
  "shorts_video": "published/shorts/shorts_render.mp4",
  "blog_html": "published/blog/index.html",
  "thread_text": "published/threads/thread.txt",
  "carousel_images": [
    "published/carousel/slide_01.jpg",
    "published/carousel/slide_02.jpg"
  ]
}
```

The server records each uploaded artifact in SQLite and renders the preview page from this manifest.

---

## 7. Data Model

SQLite stores runtime state and query-friendly metadata.

### 7.1 `sessions`

```sql
CREATE TABLE sessions (
    id                TEXT PRIMARY KEY,
    shop_id           TEXT NOT NULL,
    session_key       TEXT NOT NULL,
    customer_token    TEXT NOT NULL UNIQUE,
    stage             TEXT NOT NULL,
    artifact_dir      TEXT NOT NULL,
    pending_answer    TEXT,
    preflight_json    TEXT,
    turn1_question    TEXT,
    turn2_planner_json TEXT,
    turn3_planner_json TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
    interview_completed_at TEXT,
    production_completed_at TEXT,
    approved_at       TEXT
);
```

Notes:

- `artifact_dir` stores a relative path under the configured artifact root
- JSON blobs here are indexes and snapshots, not replacements for artifact files

### 7.2 `media_files`

```sql
CREATE TABLE media_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    kind            TEXT NOT NULL,          -- photo | video | audio
    role            TEXT NOT NULL,          -- upload | interview_turn1 | interview_turn2 | interview_turn3
    filename        TEXT NOT NULL,
    relative_path   TEXT NOT NULL,
    mime_type       TEXT,
    file_size       INTEGER,
    duration_sec    REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);
```

### 7.3 `session_messages`

```sql
CREATE TABLE session_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    sender          TEXT NOT NULL,          -- customer | system | operator
    message_type    TEXT NOT NULL,          -- text | photo | video | audio | status
    turn_index      INTEGER,
    text            TEXT,
    relative_path   TEXT,
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);
```

Purpose:

- support admin/session history
- preserve a DB query surface without replacing `chat_log.jsonl`

### 7.4 `session_artifacts`

```sql
CREATE TABLE session_artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    artifact_type   TEXT NOT NULL,          -- intake_bundle | shorts_video | blog_html | thread_text | carousel_image | manifest
    relative_path   TEXT NOT NULL,
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);
```

### 7.5 What is intentionally not in SQLite for MVP

- binary file contents
- full shop registry ownership
- guaranteed SSE replay queue

---

## 8. HTTP Surface

### 8.1 Customer routes

```text
GET  /s/<customer_token>                    session landing; redirect by stage
GET  /s/<customer_token>/upload             upload page
POST /s/<customer_token>/upload             receive one media file; return updated grid partial
POST /s/<customer_token>/upload/delete      remove one uploaded file before finalize
POST /s/<customer_token>/upload/done        validate limits, run preflight, prepare turn 1

GET  /s/<customer_token>/interview          interview page
POST /s/<customer_token>/interview/record   receive audio blob, start STT, return loading partial
POST /s/<customer_token>/interview/submit   save pending text answer from text input
POST /s/<customer_token>/interview/confirm  confirm pending answer and advance turn
POST /s/<customer_token>/interview/retry    clear pending answer and stay on current turn

GET  /s/<customer_token>/waiting            waiting page for `awaiting_production`
GET  /s/<customer_token>/preview            preview page for `awaiting_approval` and `revision_requested`
POST /s/<customer_token>/approval           approve or request revision
GET  /s/<customer_token>/complete           final completion page

GET  /s/<customer_token>/events             SSE stream
```

### 8.2 Admin routes

These are authenticated with HTTP Basic.

```text
GET  /admin/sessions                        session list
GET  /admin/sessions/<session_id>           session detail
POST /admin/sessions                        create session for an existing `shop_id`
```

Shop CRUD is out of scope for MVP.

### 8.3 Sync API routes

These are authenticated with a Bearer token.

```text
GET  /api/sync/sessions?stage=awaiting_production
GET  /api/sync/sessions/<session_id>/download
POST /api/sync/sessions/<session_id>/upload
```

`download` returns a zip of the full session artifact directory.  
`upload` accepts multipart files plus a manifest.

---

## 9. Customer Flow

### 9.1 Upload step

1. Customer opens `/s/<customer_token>`.
2. Server redirects to `/upload` for `collecting_media`.
3. Customer uploads up to 5 photos and optionally 1 short video.
4. Each upload is saved immediately into `raw/` and indexed in SQLite.
5. Customer may delete an upload before pressing "Next".
6. On `upload/done`, the server:
   - validates limits
   - loads shop config from JSON registry
   - runs `prepare_media_artifacts()`
   - writes `generated/media_preflight.json`
   - chooses turn 1 question
   - stores session snapshots in SQLite
   - moves stage to `awaiting_turn1_answer`

### 9.2 Turn 1 question generation

For MVP:

- preferred path: call `engine.plan_turn1(preflight)` when available
- fallback path: use the existing fallback question text from `interview_engine.py`

The chosen question is written to:

- `planners/turn1_question.txt`
- optionally `planners/turn1_planner.json`

### 9.3 Interview step

Customer can answer either by:

- recording audio
- typing text directly

Voice path:

1. browser records `.webm`
2. `POST /interview/record` saves `raw/turnN_audio.webm`
3. server publishes an SSE `transcribing` event
4. STT runs asynchronously
5. server stores pending text and publishes `transcript_ready`
6. page swaps in confirm/retry UI

Text path:

1. customer types answer
2. `POST /interview/submit` stores pending text
3. server returns confirm/retry partial directly

Confirm path:

1. `POST /interview/confirm`
2. server writes transcript artifacts
3. server appends chat log and DB message row
4. server generates next planner if turn < 3
5. server returns the next interview partial directly

Retry path:

- pending answer is cleared
- customer stays on the same turn

### 9.4 Turn 3 completion

On confirmed turn 3:

1. write transcript artifacts
2. write `generated/intake_bundle.json`
3. mark session `awaiting_production`
4. show waiting page

The customer is done at this point until preview is uploaded later.

### 9.5 Preview and approval step

After workstation push:

1. server stores uploaded preview files under `published/`
2. server records `session_artifacts`
3. stage becomes `awaiting_approval`
4. customer reopening the same link lands on `/preview`

Approval options:

- approve -> stage `approved`
- request revision -> stage `revision_requested`

Whether `approved` immediately becomes `completed` is a product decision. For MVP, both are acceptable as long as the user sees a clear terminal page.

---

## 10. SSE Design

### 10.1 Principle

SSE is for responsive UX, not durable state.

### 10.2 Required event types for MVP

| Event | Trigger | Payload | Client behavior |
|------|---------|---------|-----------------|
| `transcribing` | audio upload accepted | `{}` | show loading indicator |
| `transcript_ready` | STT success | `{"text": "..."}` | swap in transcript confirm UI |
| `transcript_failed` | STT failed | `{"error": "..."}` | show fallback text input |
| `preview_ready` | workstation push completed while customer page is open | `{"url": "/s/<token>/preview"}` | show "preview ready" link |

### 10.3 Explicitly out of scope for MVP

- replay missed SSE events from DB
- using SSE for all turn advancement
- multi-node pub/sub

Turn advancement should use normal HTMX request/response, which is simpler and more reliable than building a full event replay system up front.

---

## 11. Auth and Security

### 11.1 Customer tokens

- long random URL-safe tokens
- stored hashed or stored raw only if operationally necessary
- enough entropy to resist guessing
- not reused between sessions

### 11.2 Admin auth

Environment variables:

- `THOHAGO_ADMIN_USERNAME`
- `THOHAGO_ADMIN_PASSWORD`

### 11.3 Sync API auth

Environment variable:

- `THOHAGO_SYNC_API_TOKEN`

Workstation CLI sends:

```http
Authorization: Bearer <token>
```

### 11.4 File handling rules

- never trust client filename for final path generation
- derive safe server filenames
- validate MIME type and extension
- enforce max upload size server-side
- reject path traversal in sync uploads

### 11.5 Operational rule

Customer endpoints, admin endpoints, and sync endpoints must use different authorization paths and must not share cookies or tokens.

---

## 12. Implementation Plan

This plan is ordered to produce a working loop as early as possible.

### Phase 1: Shared foundation

Goal: web runtime can create and resume sessions without touching production outputs.

Tasks:

1. add `src/thohago/web/` package with app factory, templates, static assets, and route modules
2. add SQLite initialization and lightweight migration script
3. add session repository and artifact-aware session service
4. add config for admin auth, sync token, web base URL, upload limits
5. add CLI support for session creation for existing shops

Deliverable:

- operator can create a customer session link
- customer link resolves to a real session record

### Phase 2: Upload flow

Goal: customer can upload media and reach turn 1.

Tasks:

1. build upload page and partials
2. save uploads into `raw/`
3. record `media_files` and `session_messages`
4. implement delete-before-finalize
5. run preflight on `upload/done`
6. write `media_preflight.json`
7. choose and persist turn 1 question

Deliverable:

- customer completes upload and enters interview step

### Phase 3: Interview flow

Goal: customer completes 3 turns by voice or text.

Tasks:

1. implement interview page and confirm/retry partials
2. add recorder JS for MediaRecorder
3. add SSE endpoint for STT events only
4. integrate STT provider
5. write transcript artifacts on confirm
6. generate turn 2 and turn 3 planners
7. export `intake_bundle.json` on turn 3
8. move stage to `awaiting_production`

Deliverable:

- full customer intake loop works end-to-end

### Phase 4: Sync bridge and preview

Goal: workstation can pull intake and push preview artifacts.

Tasks:

1. add sync API auth
2. add `thohago sync list`
3. add `thohago sync pull`
4. add `thohago sync push`
5. unpack pushed preview files into `published/`
6. store `manifest.json` and `session_artifacts`
7. render preview page
8. implement approval and revision request

Deliverable:

- end-to-end working loop from customer intake to preview approval

### Phase 5: Admin UI and polish

Goal: reduce operator friction after the core loop works.

Tasks:

1. add admin session list and detail pages
2. add admin session creation page for existing shops
3. add waiting page and preview-ready online hint
4. improve error states and mobile polish
5. add optional PWA manifest and offline shell

Deliverable:

- operator no longer needs CLI for routine session lookup

---

## 13. File Structure

```text
src/thohago/
  web/
    __init__.py
    app.py
    config.py
    database.py
    repositories.py
    services/
      sessions.py
      uploads.py
      interview.py
      sync.py
    routes/
      customer.py
      admin.py
      sync_api.py
      events.py
    templates/
      base.html
      upload.html
      interview.html
      waiting.html
      preview.html
      complete.html
      partials/
        upload_grid.html
        pending_answer.html
        interview_turn.html
        loading.html
    static/
      recorder.js
      app.css

  artifacts.py
  bot.py
  cli.py
  content.py
  models.py
  interview_engine.py
  groq_live.py
  openai_live.py
  anthropic_live.py
```

Notes:

- `bot.py` remains for reference during migration but is no longer the target runtime
- `repositories.py` and `services/*` are intentionally separate so web handlers stay thin

---

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Kakao in-app browser blocks or degrades microphone APIs | voice interview fails | text input is always visible; voice is enhancement, not the only path |
| Mobile upload timeout on large video | customer drop-off | cap video count and duration; enforce size limits; show per-file loading state |
| STT latency feels slow | customer confusion | immediate loading indicator via SSE; do not block entire page |
| Session resumes on wrong screen | broken customer flow | drive landing redirect from canonical session stage only |
| Artifact and DB drift | operator confusion | every stage change writes both DB update and artifact metadata update in one service method |
| Public sync endpoint abuse | data leak | separate Bearer token auth; never accept customer token on sync routes |
| Scope creep into full dashboard | delayed migration | keep admin UI minimal until sync loop works |

---

## 15. Success Criteria

- customer can complete upload + 3-turn interview from a KakaoTalk link
- same link resumes correctly after browser close or refresh
- voice path works on supported browsers and text fallback always works
- server writes artifact directories compatible with existing local workflow
- session reaches `awaiting_production` without calling final content generation on the server
- workstation can list, pull, and push sessions using authenticated sync APIs
- customer can open preview and approve or request revision from the same link
- customer tokens never grant admin or sync access
- no Redis or Postgres dependency is required for MVP

---

## 16. Deferred Items

These are intentionally deferred until after the MVP loop is live:

- shop CRUD in admin UI
- Kakao Alimtalk or SMS notifications
- guaranteed SSE replay and durable event queue
- chunked uploads
- Postgres migration
- automated third-party publish from the server
- multi-operator collaboration features

