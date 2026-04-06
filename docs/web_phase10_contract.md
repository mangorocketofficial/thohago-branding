# Web Phase 10 Contract

> Status: Active  
> Date: 2026-04-02  
> Reference: [web_phase9_contract.md](./web_phase9_contract.md)

## Goal

Fix the web runtime so interview planning uses the configured interview engine, while audio transcription remains independently configured.

For this phase, the intended production behavior is:

- photo interpretation / `media_preflight.json`: Claude
- `turn1`, `turn2`, `turn3` question generation: Claude
- live STT: Groq

## Business Outcome

The web customer flow should match the intended operator design instead of silently using Groq for both planning and STT.

## In Scope

1. Web interview engine selection
   - make `THOHAGO_DEFAULT_INTERVIEW_ENGINE` actually control the web planning engine
   - support explicit values for `claude`/`anthropic`, `groq`, `openai`, `heuristic`, and `auto`

2. Engine / STT separation
   - keep web planning engine selection independent from STT selection
   - preserve current web STT resolution path

3. Web planning flow
   - ensure upload preflight uses the selected planning engine
   - ensure turn1/turn2/turn3 planning uses the selected planning engine

4. Deployment config
   - update the deployed web server so the live runtime uses Claude for planning and Groq for STT

## Out of Scope

- Telegram bot engine routing
- content publishing engine changes
- UI redesign
- Redis / SSE infrastructure
- non-web deployment targets

## Acceptance Criteria

### A. Config Application

- `THOHAGO_DEFAULT_INTERVIEW_ENGINE` is applied by the web runtime.
- Explicit `claude` selection uses the Anthropic/Claude engine when a key is present.
- Explicit `groq`, `openai`, and `heuristic` selections are also respected.

### B. Planning vs STT Separation

- Web planning engine selection is independent from web transcription provider selection.
- Web STT can remain Groq while planning uses Claude.

### C. Planning Flow

- `media_preflight.json` is produced by the selected interview engine.
- turn1 question generation is produced by the selected interview engine.
- turn2/turn3 planner generation is produced by the selected interview engine unless fallback is triggered.

### D. Live Server

- Live server configuration uses Claude for planning.
- Live server configuration keeps Groq for STT.
- Live verification shows `media_preflight.json` comes from Anthropic mode rather than Groq mode.

## Completion Evidence Required

The verification record must include:

1. targeted automated test commands
2. full regression result
3. live server config evidence
4. live verification showing Anthropic planning mode for web preflight
5. pass/fail status for each acceptance group
