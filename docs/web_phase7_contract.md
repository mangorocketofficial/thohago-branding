# Web Phase 7 Contract

> Status: Active  
> Date: 2026-04-01  
> Reference: [web_phase6_contract.md](./web_phase6_contract.md)

## Goal

Perform a real live Groq STT verification against the web interview voice path and a known audio sample.

This phase is different from the previous voice/STT/SSE augmentation phase:

- previous phase verified the end-to-end voice flow in stub mode
- this phase verifies the real external Groq STT provider path

## Business Outcome

The team must have explicit evidence that the production STT provider path is either:

1. working end-to-end with a real `GROQ_API_KEY`, or
2. blocked for a concrete operational reason that is recorded in the verification document

## In Scope

1. Live STT verification harness
   - one command or script can run a live Groq transcription against a sample audio file
   - the command fails clearly when `GROQ_API_KEY` is missing
   - the command prints enough structured output to capture verification evidence

2. Sample-audio selection for verification
   - verification uses a checked-in interview audio sample already present in the repository
   - the sample path is recorded in the verification document

3. Verification documentation
   - record the environment state
   - record whether `GROQ_API_KEY` was available
   - if available, record live transcription results
   - if unavailable, record the exact blocker

## Out of Scope

- replacing the current STT provider
- changing the production interview flow
- adding a second STT vendor
- UI changes unrelated to verification
- faking a successful live verification without credentials

## Required Inputs

- a real `GROQ_API_KEY` in the environment for full verification
- one checked-in audio sample file
- current codebase with Web Phase 6 voice path already implemented

## Required Outputs

For this phase to be fully verified, the implementation must produce:

- a live verification command or script
- a transcription result from the real Groq STT API
- recorded verification evidence in `docs/`

If credentials are missing, the phase must still produce:

- the verification harness
- a clear blocked verification record

## Acceptance Criteria

### A. Verification Harness

- A dedicated verification entry point exists for live Groq STT checks.
- The harness accepts an audio file path.
- The harness fails clearly when `GROQ_API_KEY` is missing.

### B. Live Provider Path

- When `GROQ_API_KEY` is present, the harness uses the real Groq transcription provider.
- The harness returns non-empty transcript text for the sample file.
- The harness records provider metadata or response context sufficient for debugging.

### C. Verification Record

- The verification document records the exact command used.
- The verification document records the sample audio path.
- The verification document records whether the run was blocked or successful.
- If blocked, the blocker is explicit and concrete.

## Operator Flows Required

1. Choose a checked-in audio sample
2. Run the live Groq STT verification command
3. Record the result or blocker in the verification document

## Environment and Dependency Assumptions

- OS: current Windows development machine
- Python: current local interpreter
- Network access is available
- `GROQ_API_KEY` may or may not be present

## Completion Evidence Required

The verification document must include:

1. exact contract date/version
2. exact command executed
3. exact sample audio path
4. whether `GROQ_API_KEY` was available
5. if available, the transcript text length and a short transcript excerpt
6. if unavailable, the exact blocker
7. automated test command(s) for the verification harness itself

## Explicit Non-Completion Cases

This phase is not complete if any of the following is true:

- no dedicated live verification harness exists
- the verification document omits whether `GROQ_API_KEY` was present
- the result is described vaguely instead of as a concrete success or blocker
