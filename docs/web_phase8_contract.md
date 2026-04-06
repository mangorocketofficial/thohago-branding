# Web Phase 8 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_phase6_contract.md](./web_phase6_contract.md)

## Goal

Harden the current SSE implementation so reconnecting clients can replay missed events from durable storage.

This phase turns the current best-effort in-memory SSE channel into a replayable session event stream:

- persist SSE events in SQLite
- include event ids in server-sent events
- replay missed events on reconnect using `Last-Event-ID`
- publish durable `preview_ready` events when preview upload completes
- let the waiting page react to `preview_ready` without relying only on timed refresh

## Business Outcome

If a customer temporarily loses connection during voice transcription or while waiting for preview, reconnecting the same page should recover missed session events instead of silently losing them.

## In Scope

1. Durable session event storage
   - add a persistent event table for session SSE events
   - store `event_type`, payload, and monotonic event id

2. Event bus hardening
   - event publication writes to persistent storage first
   - in-memory fanout still pushes to live subscribers

3. SSE reconnect semantics
   - SSE responses include `id:` fields
   - SSE endpoint reads `Last-Event-ID`
   - SSE endpoint replays missed events after the provided id

4. Preview-ready durable event
   - preview upload publishes `preview_ready`
   - reconnecting waiting-page clients can receive the missed event

5. Waiting page live handoff
   - waiting page opens an SSE connection
   - `preview_ready` redirects the customer to preview immediately
   - existing timed refresh may remain as a fallback

## Out of Scope

- cross-process Redis pub/sub
- event retention cleanup jobs
- per-event acknowledgements beyond `Last-Event-ID`
- replay for every historical event since session creation without client-provided cursor
- admin notification UI

## Required Inputs

- an existing session id
- published event payloads for transcription or preview-ready events
- reconnecting client request with or without `Last-Event-ID`

## Required Outputs

For this phase, the implementation must produce:

- one durable session event row per published SSE event
- SSE responses with `id:` fields
- replay of missed events after `Last-Event-ID`
- waiting-page redirect on `preview_ready`

## Acceptance Criteria

### A. Durable Event Storage

- Published session events are written to SQLite.
- Stored events can be queried by session and ordered id.

### B. Live SSE Stream

- SSE stream still delivers live events to connected clients.
- SSE frames include `id:` for each event.

### C. Replay On Reconnect

- When a client reconnects with `Last-Event-ID`, the server replays newer missed events.
- Replayed events preserve original ordering.

### D. Preview-Ready Event

- Preview upload publishes a durable `preview_ready` event.
- Waiting-page clients can receive `preview_ready` over SSE.

### E. Waiting Page UX

- Waiting page still renders normally without SSE.
- Waiting page redirects to preview when `preview_ready` is received.

## Operator Flows Required

1. Prepare a waiting session
2. Connect to the SSE stream
3. Trigger `preview_ready`
4. Reconnect with a prior event id and verify replay
5. Confirm waiting page contains live redirect wiring

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Existing SQLite runtime and sync preview flow from earlier phases
- Verification may use local uvicorn server instances

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. automated test command(s)
3. manual verification commands or scripted flows
4. pass/fail status for each acceptance group
5. evidence of stored durable events in SQLite
6. evidence of `id:` fields in SSE output or replayed event ordering
7. evidence that waiting page contains live preview-ready redirect wiring

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- events are still only in memory
- SSE frames omit event ids
- reconnecting clients cannot replay missed events
- preview upload does not publish `preview_ready`
- waiting page has no live redirect behavior
