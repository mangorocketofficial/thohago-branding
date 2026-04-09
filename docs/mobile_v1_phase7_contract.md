# Mobile_V1 Phase 7 Contract

> Status: Active  
> Date: 2026-04-08  
> Workflow: [phase_workflow.md](./phase_workflow.md)  
> Reference: [mobile_saas_architecture.md](./mobile_saas_architecture.md)  
> Reference: [mobile_v1_phase6_verification.md](./mobile_v1_phase6_verification.md)  
> Reference: [web_phase6.py](../tests/test_web_phase6.py)

---

## 1. Goal

Deliver app-side interview voice recording and automatic transcription inside the unified `Mobile_V1` chat shell.

This phase must extend the app-side interview screen so that a customer can tap a microphone icon inside the answer composer, record a voice answer, and receive automatic transcript insertion without leaving `/app/session/:sessionId`.

The phase must:

- place a microphone control inside the app-side interview textarea area
- support app-side interview audio upload and transcription
- surface live transcription state through the app shell
- reuse the existing transcription runtime with Groq Whisper when configured
- keep the existing text-answer flow available

---

## 2. Business Outcome

At the end of Phase 7:

- the app-side interview composer supports both text and voice input
- the voice flow works from `/app/session/:sessionId` rather than the legacy token route
- a recorded answer is automatically transcribed and moved into the existing confirm flow
- the customer sees a clear recording/transcribing status inside the chat shell

---

## 3. In Scope

### 3.1 App-Side Interview Composer Update

- remove the helper text `자유 입력은 인터뷰 답변에서만 사용할 수 있어요.`
- place a microphone button inside the app-side interview textarea area
- show recording and transcription status inline in the app-side composer

### 3.2 App-Side Audio Recording Flow

- add app-side interview record route under `/app/session/:sessionId`
- add app-side event stream route for interview transcription events
- reuse the existing `recorder.js` behavior where compatible
- keep the customer inside the app shell throughout the flow

### 3.3 Automatic Transcription

- app-side recording must write the audio file to the existing session artifact runtime
- app-side recording must invoke the current transcription provider runtime
- when `THOHAGO_WEB_STT_MODE=groq`, the app-side route must use Groq Whisper via the existing provider path
- once transcription is ready, the transcript must populate the existing confirm flow

### 3.4 Workflow Compatibility

- keep text submission working
- keep retry and confirm behavior working
- keep interview progression working for turn 1, turn 2, and turn 3

---

## 4. Out Of Scope

- changing the core interview question logic
- changing upload, preview, approval, or delivery flows
- final download UX redesign
- real auth and billing integration
- mobile-native app packaging

---

## 5. Required Inputs

The implementation may assume:

- the existing FastAPI + Jinja2 + static CSS + JS stack remains in use
- the current unified app shell from Phase 6 is already verified
- existing interview recording, event bus, and transcription runtime are available from the legacy customer flow
- the current transcription runtime may be `stub` in tests and `groq` in real usage

---

## 6. Required Outputs

Phase 7 must produce:

1. App-shell outputs
   - microphone icon inside the app-side interview composer
   - app-side recording/transcription status UX

2. Routing outputs
   - app-side interview record route
   - app-side interview events route

3. Verification outputs
   - Phase 7 verification document
   - command evidence
   - route/event evidence

---

## 7. Acceptance Criteria

### A. Composer UI

- the app-side interview composer includes a microphone button inside the textarea area
- the removed helper copy no longer appears
- recording/transcription state is visible in Korean

### B. Recording Flow

- app-side audio POST writes an interview audio file
- app-side audio POST moves the session into confirm state
- app-side audio flow stays under `/app/session/:sessionId`

### C. Event Flow

- app-side events stream emits `transcribing`
- app-side events stream emits `transcript_ready`
- transcription failures emit `transcript_failed`

### D. Interview Compatibility

- transcribed answers can still be confirmed through the existing interview flow
- turn progression continues to work after voice input

### E. Runtime Compatibility

- the app-side voice flow uses the configured transcription runtime
- Groq Whisper remains the live transcription path when `THOHAGO_WEB_STT_MODE=groq`

---

## 8. Required Commands And Operator Flows

Phase 7 must support and document these commands or equivalent commands:

1. Install dependencies
2. Run local web app
3. Run Phase 7 tests
4. Run key mobile regression checks
5. Operator verification flow:
   - sign in through the stub path
   - create or open an interview-ready app session
   - record one audio answer from the app-side interview composer
   - confirm transcript-ready state
   - confirm the answer can move into the existing confirm flow

Exact command strings will be captured in the verification document after implementation.

---

## 9. Dependencies, Credentials, And Environment Assumptions

- current repository branch: `mobile-web-pivot`
- FastAPI application remains the delivery surface
- existing recorder JavaScript may be reused
- tests may use stub transcription
- live usage may use Groq Whisper via existing runtime configuration

---

## 10. Completion Evidence Required

Phase 7 is only verified when the verification document includes:

1. Environment evidence
2. Exact Phase 7 test command
3. App-side record route evidence
4. App-side event stream evidence
5. Confirm-flow evidence after voice transcription

---

## 11. Explicit Non-Completion Cases

Phase 7 is **not** complete if:

- the app-side interview UI still has no working microphone control
- the app-side recording route is missing
- transcription only works through the legacy `/s/<customer_token>` route
- voice input breaks the existing confirm/retry flow

---

## 12. Change Control

- If implementation expands into new interview logic, update this contract first.
- If implementation changes route structure beyond app-side voice input, update this contract first.
- Verification may not silently expand the scope after implementation.
