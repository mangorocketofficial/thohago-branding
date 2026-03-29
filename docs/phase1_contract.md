# Phase 1 Contract

> Status: Active  
> Date: 2026-03-27  
> Reference: [development_plan.md](./development_plan.md)

## Goal

Deliver the Phase 1 core pipeline for one shop session inside a multi-shop-capable backend foundation:

- collect session inputs,
- turn owner media + interview into a normalized experience set,
- generate a Naver blog article draft,
- publish the article to Naver Blog,
- store enough artifacts to replay and verify the run later.

This phase is the foundation for the recurring 12-set monthly service. It must support both real Telegram intake and deterministic local replay for verification, and it must not assume that only one shop exists in the system.

## Phase 1 Scope

### In Scope

1. Shop registry and tenant foundation
   - Register shops with a stable `shop_id`
   - Support invite/deep-link tokens that bind a Telegram room/chat to exactly one shop on first contact
   - Persist the resulting Telegram chat-to-shop mapping after onboarding
   - Store shop-scoped publishing configuration and integration credentials references
   - Isolate session artifacts and pipeline state by shop

2. Telegram intake for one shop session
   - Receive photos, optional videos, and voice messages
   - Group them into a single session for one registered shop
   - Persist raw inputs to disk

3. Multimodal media preflight
   - Send original photos/videos directly to a multimodal LLM
   - Produce a best-fit experience sequence
   - Produce structured `media_preflight.json` for downstream interview/content generation

4. STT
   - Transcribe each owner voice answer
   - Persist transcript text and machine-readable transcript metadata

5. 3-turn interview orchestration
   - Fixed Turn 1 question
   - Generated Turn 2 follow-up from original media + `media_preflight.json` + Turn 1 transcript
   - Generated Turn 3 gap-filler question from original media + `media_preflight.json` + Turns 1-2 transcripts
   - Persist structured planner artifacts for Turn 2 and Turn 3

6. Content bundle generation
   - Build a normalized `content_bundle.json`
   - Decide `structure_mode` for the article

7. Blog generation
   - Generate one Naver blog article from the experience set
   - Persist the generated article in a local artifact directory

8. Naver Blog publishing integration
   - Provide a publish path that can post the generated article to Naver Blog
   - Resolve the correct target account/config from the shop record
   - Return the published URL on success

9. Replayable execution
   - Provide a non-Telegram replay path that runs the same pipeline from a local session directory
   - Replay mode must be good enough for deterministic contract verification

### Out of Scope

- Instagram generation or publishing
- Threads generation or publishing
- Naver Place generation
- Reels rendering or delivery
- Feedback survey UI
- Auto-revision or approval workflow
- High-scale multi-shop concurrency, worker pools, or production-grade scaling
- Billing, subscription management, or admin dashboards

## Required Session Inputs

Phase 1 must support these inputs:

- Photos: 1 to 10
- Videos: 0 to 2
- Voice answers: exactly 3 interview turns

The implementation may accept more internally, but verification only depends on the contract range above.

## Required Outputs

For every completed session, the pipeline must produce a session artifact directory containing at minimum:

- shop/session metadata
- `chat_log.jsonl`
- raw media files
- transcript files for each turn
- `media_preflight.json`
- `turn2_planner.json`
- `turn3_planner.json`
- `content_bundle.json`
- generated blog article in Markdown or HTML
- publish result metadata

## Required Entry Points

Phase 1 implementation must expose both flows below:

1. Telegram flow
   - Start the bot
   - Resolve the shop from either an existing chat binding or a valid `/start <token>` onboarding flow
   - Receive owner inputs
   - Execute the full Phase 1 pipeline

2. Local replay flow
   - Run the same normalized pipeline from an existing local session directory
   - Produce the same artifact shape as the Telegram flow after intake

The exact internal architecture is flexible, but both flows must converge into one shared pipeline after ingestion.

## Phase 1 Design Constraints

- Question generation after each STT step should require one multimodal LLM call, not a chained Vision-to-text step plus a separate text-only question step.
- The system must preserve direct access to original media for Turn 2 and Turn 3 planning.
- Structured planner artifacts must be persisted even though the user only sees the final question text.

## Acceptance Criteria

### A. Shop Foundation

- The system can resolve an incoming Telegram chat/room to a registered `shop_id`.
- The system can bind a previously unknown Telegram chat/room to a shop through a valid `/start <token>` onboarding flow.
- The resulting chat-to-shop mapping is persisted for later messages.
- Shop-scoped publish configuration is loaded through a shop registry/config layer, not hardcoded in the pipeline.
- Session artifacts are namespaced by `shop_id` and `session_id`.
- The implementation can support more than one shop record without code changes.

### B. Session Intake

- A single shop session can be created and completed without manual file copying.
- Raw assets are stored under a predictable session directory.
- The system can distinguish one session from another by shop/chat and timestamp or session id.
- Bot/customer messages for the session are persisted in a readable chat log artifact.

### C. Interview Orchestration

- Turn 1 is always the fixed opening question from the product spec.
- Turn 2 is generated in one multimodal LLM call from original media + `media_preflight.json` + Turn 1 transcript.
- Turn 3 is generated in one multimodal LLM call from original media + `media_preflight.json` + Turns 1-2 transcripts.
- Each asked question is persisted as an artifact.
- Each planner output records at minimum the chosen question strategy, covered elements, missing elements, and final `next_question`.

### D. Transcription

- Each of the 3 voice turns is transcribed successfully.
- The pipeline stores both human-readable transcript text and machine-readable metadata.
- Transcription failures are surfaced clearly in logs and session status.

### E. Multimodal Media Preflight

- The system stores one `media_preflight.json` per completed session.
- `media_preflight.json` is produced from original media, not from a separate lossy Vision-to-text stage.
- The pipeline produces `experience_sequence` and `structure_mode`.
- If chronological narrative is weak, the pipeline may choose `key_moments` or `proof_points`.

### F. Content Bundle

- One `content_bundle.json` is produced per completed session.
- The bundle contains shop/session identity, normalized media references, `media_preflight` results, interview transcripts, main angle, structure mode, and ordered experience sequence.

### G. Blog Generation

- One blog article is generated from the completed content bundle.
- The article follows the experience-set approach from the product spec.
- The article is stored locally before publish is attempted.

### H. Naver Publish

- The system can attempt Naver Blog publish from the generated article artifact.
- The publish step uses the correct shop-scoped target configuration.
- On success, it stores the final post URL.
- On failure, it stores a machine-readable error result and does not silently discard the generated article.

### I. Replay Verification

- A local replay command can run Phase 1 against a prepared session directory in this repository.
- Replay output is sufficient to verify article generation even when Telegram intake is not used.

## Non-Functional Requirements

- Configuration must come from environment variables or a checked-in example env file, not hardcoded secrets.
- Shop-scoped settings must be resolved through data or config files, not single-shop constants embedded in pipeline logic.
- Logs must make it possible to identify which phase step failed.
- Session artifacts must be organized so one session can be inspected without reading unrelated runs.
- Operators must be able to inspect the bot/customer conversation for a single session without querying Telegram again.
- The code must be runnable on the current Windows-based development environment.

## Credentials and External Dependencies

Phase 1 may require these credentials depending on provider choice:

- Telegram bot token
- Multimodal LLM API key
- STT API key if separate from LLM provider
- Shop-scoped Naver Blog publishing credentials/cookies
- Shop-scoped Meta credentials in the future, even if unused in Phase 1

Contract note:

- Replay verification must not depend on Telegram.
- Full phase completion still requires one live end-to-end verification with valid Telegram and Naver credentials.

## Completion Evidence Required

Phase 1 is considered contract-verified only when the verification document contains:

1. Local replay evidence
   - exact command executed
   - artifact directory path
   - generated `chat_log.jsonl`
   - generated `media_preflight.json`
   - generated `turn2_planner.json`
   - generated `turn3_planner.json`
   - generated `content_bundle.json`
   - generated blog article file
   - evidence of resolved `shop_id`

2. Live integration evidence
   - evidence that a Telegram chat/room resolved to the correct registered shop
   - evidence that `/start <token>` onboarding binds the chat to the correct shop, or equivalent proof that the binding already exists
   - evidence that Telegram intake completed
   - evidence that 3 voice turns were transcribed
   - evidence that Naver publish succeeded or failed with a captured machine-readable result
   - if publish succeeded, the resulting post URL

3. Test evidence
   - automated test command(s) executed
   - pass/fail result

## Explicit Non-Completion Cases

Phase 1 is not done if any of the following is true:

- the bot intake works but replay does not exist
- deep-link onboarding is missing and new chats cannot be bound to a shop
- the bot/customer conversation for a session is not persisted as an inspectable artifact
- the pipeline requires a separate Vision-to-text stage to generate Turn 2 or Turn 3 questions
- the pipeline hardcodes a single shop's publish target or credentials
- article generation works but artifacts are not persisted
- the Naver publish step is missing entirely
- logs are too weak to determine which phase step failed
- verification relies on manual hand-waving instead of recorded evidence
