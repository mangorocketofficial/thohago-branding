# AI Marketing Content Service — Development Plan

> **Project codename**: Ddohago Content Engine
> **Version**: 1.0
> **Last updated**: 2026-03-27
> **Target market**: Korean beauty shops (head spas, hair salons, nail shops, skin care clinics)

---

## 1. Product overview

### 1.1 Problem

Beauty shop owners have compelling stories — loyal customers, unique techniques, memorable moments — but lack the time and skill to turn these into marketing content. Generic AI-generated content feels hollow because it misses the owner's real experience.

### 1.2 Solution

An AI-powered service that extracts real stories from owners through a 3-minute voice interview on Telegram, then automatically generates and publishes 4-platform content from a unified experience set built from interview + media. The product is delivered as a recurring monthly service with 12 interview/content sets, allowing feedback from each set to improve the next one.

### 1.3 Core value proposition

| Metric | Value |
|--------|-------|
| Owner effort | Send photos + 3 voice memos (~3 min total) |
| Service cadence | 12 interview/content sets per month |
| Output | 4 platform contents generated and published from one experience set |
| Content quality | Real stories, not generic AI copy |
| Revision required | None — no per-post revision; feedback is applied to the next set |

### 1.4 Key differentiator

The AI interviews the owner using the original media itself as context through a multimodal model, producing questions that draw out specific stories rather than asking generic marketing questions. The resulting content is built from a structured experience set where interview + media reinforce each other. When the media supports a clear flow, the output becomes narrative; when it does not, the system reorganizes the material around key moments, differentiators, and customer reactions — not text with decorative photos attached.

### 1.5 Service model

This is not a revision-heavy content agency workflow. It is an operating system for recurring content production.

- Each month consists of 12 interview/content sets
- Each set uses the owner's own voice + media as the source material
- Published content is not revised post hoc for tone, wording, or structure
- Feedback from each set is accumulated and applied to subsequent sets
- The first week functions as a calibration period; after that, quality should improve quickly as the system learns the shop's preferences

### 1.6 Multi-shop operating model

The service must support multiple client shops from the beginning.

- Each client shop is assigned a dedicated Telegram room or 1:1 bot chat
- Each client receives a unique Telegram deep link for first-time onboarding
- Each Telegram conversation maps to one shop profile in the backend
- Each shop stores its own publishing targets and credentials references
- Session artifacts, feedback history, and content history are isolated per shop
- The bot/customer conversation log is stored per session for operator review
- The backend should be multi-tenant by design even if the early MVP is verified with only one live shop

---

## 2. System architecture overview

```
┌─────────────────────────────────────────────────────────┐
│  TELEGRAM BOT (Frontend)                                │
│                                                         │
│  Photos/Videos → MM LLM Preflight → 3-Turn Interview → STT │
└──────────────────────┬──────────────────────────────────┘
                       │ Content Bundle
                       ▼
┌─────────────────────────────────────────────────────────┐
│  BACKEND PIPELINE                                       │
│                                                         │
│  LLM Content Gen → Edit Spec JSON → Python CLI Render  │
│       │                                                 │
│       ▼                                                 │
│  Auto Publish → Post-Notification → Feedback Survey     │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Frontend — Telegram bot

### 3.1 Media input

The owner sends photos and optional videos to the Telegram bot. No special instructions needed — just send what they have from today's session.

Each shop operates through its own Telegram room or dedicated 1:1 bot chat. The backend resolves that conversation to a shop record before starting intake.
The bot/customer conversation itself is also persisted as part of the session artifact set so operators can inspect what was asked and answered later.

**Onboarding flow:**
- The owner receives a unique deep link such as `t.me/<bot_username>?start=<invite_token>`
- On first contact, the bot resolves `invite_token -> shop_id`
- The backend stores `telegram_chat_id -> shop_id`
- After that, the owner can continue using the same 1:1 bot chat without repeating setup

**Accepted inputs:**
- Photos: 1–10 images (JPEG/PNG, any resolution)
- Videos: 0–5 clips (MP4/MOV, any orientation)
- All media is stored temporarily for pipeline processing

### 3.2 Multimodal media preflight (parallel, immediate)

The moment media is received, a multimodal LLM reviews the original photos/videos before the first interview question is sent. There is no separate Vision-to-text extraction stage. The model sees the actual media and produces a structured `media_preflight.json` artifact for the interview pipeline.

**Preflight outputs:**
- Industry/shop context hypothesis
- Best-fit experience order (timeline if clear, otherwise grouped key moments)
- Key visual evidence worth using in questions and content
- Atmosphere/mood cues
- Candidate differentiators visible in media
- Representative media items for later reuse in Turn 2/Turn 3 prompts
- Video orientation, scene type, duration, and reels eligibility

**Why this structure:**
- Direct media input preserves visual context that would be lost in text-only extraction
- The same model can reason about sequence, atmosphere, and question opportunities in one call
- Later interview turns can reuse the structured preflight artifact instead of recomputing everything from scratch

### 3.3 Interview flow — 3 turns

The interview is designed around one principle: **the owner knows what matters, the AI helps them articulate it.**

No turn exceeds 1 minute of voice recording. Total interview time target is under 3 minutes.

#### Turn 1 — Common opening (fixed question)

```
"이번 포스팅에 대해 이야기해볼까요?
 어떤 상황이었고, 무엇이 가장 인상깊으셨나요?"
```

This question is identical every time regardless of industry, photos, or context. The owner's answer reveals what they consider most important, which becomes the **main angle** for all content.

**Why fixed**: A consistent opening builds habit. The owner knows exactly what to expect and can start talking immediately without processing a new question.

**What the system does with the answer**: Extracts keywords and identifies the owner's chosen angle (e.g., "foreign tourists", "VIP customer", "new treatment launch", "busy weekend").

#### Turn 2 — Turn 1 answer + original media combined

The system uses one multimodal LLM call after STT completes. That call receives the original photos, the stored `media_preflight.json`, and the Turn 1 transcript, then returns a structured planner output plus the next question.

| Source | Example |
|--------|---------|
| Turn 1 keywords | "Philippines", "5 people", "reservation" |
| Direct media context | 2-person simultaneous treatment, LED dome, scalp analysis scene, candle ambiance |

**Question generation logic:**

```python
turn2_planner = multimodal_llm(
    system=INTERVIEW_SYSTEM_PROMPT,
    inputs={
        "photos": original_photos,
        "media_preflight": media_preflight_json,
        "turn1_transcript": turn1_transcript
    },
    output_schema={
        "main_angle": "string",
        "covered_elements": ["string"],
        "missing_elements": ["string"],
        "question_strategy": "string",
        "next_question": "string"
    }
)

turn2_question = turn2_planner["next_question"]
```

**Example output:**
```
"5분이 동시에 받으셨으면 반응이 장난 아니었을 것 같아요.
 시술 받으시면서 특별히 반응이 좋았던 순간이 있으세요?"
```

#### Turn 3 — Content gap filler

The system uses one more multimodal LLM call after Turn 2 STT completes. That call receives the original photos, `media_preflight.json`, and Turns 1-2 transcripts, then asks about the highest-value missing content element.

**Content element checklist:**

| Element | Detection method | Priority | Example question if missing |
|---------|-----------------|----------|-----------------------------|
| Entry channel | Keywords: SNS, booking site, referral, word-of-mouth | High | "이 고객분들이 어떻게 매장을 알고 찾아오셨어요?" |
| Differentiator | Keywords: only here, special, unique, our method | High | "다른 곳이 아닌 여기를 선택한 특별한 이유가 있을까요?" |
| Customer reaction | Emotion words: 좋았다, 감동, 놀랐다, 울었다 | Medium | "시술 받으실 때 기억에 남는 반응이나 에피소드 있으세요?" |
| Location advantage | Location terms: 역 근처, 거리, 접근성 | Low | "매장 위치적으로 고객분들에게 좋은 점이 있나요?" |

**Logic:**
```python
turn3_planner = multimodal_llm(
    system=INTERVIEW_SYSTEM_PROMPT,
    inputs={
        "photos": original_photos,
        "media_preflight": media_preflight_json,
        "turn1_transcript": turn1_transcript,
        "turn2_transcript": turn2_transcript
    }
)

question = turn3_planner["next_question"]
```

### 3.4 Voice handling

| Setting | Value |
|---------|-------|
| Input format | Telegram voice message (OGG) or audio file (M4A) |
| Primary STT | OpenAI Whisper API (language: ko) |
| Fallback STT | Clova Speech API (better for Korean dialects, beauty jargon) |
| Expected duration | ~1 min per memo, ~3 min total |
| Max recording time | 2 min per turn (Telegram default) |

---

## 4. Backend — Content generation pipeline

### 4.1 Content bundle (pipeline input)

After the 3-turn interview completes, the backend receives:

```json
{
  "shop": {
    "shop_id": "sisun8082",
    "telegram_chat_id": "123456789",
    "publish_targets": ["naver_blog"]
  },
  "photos": [
    {
      "file_path": "...",
      "preflight_analysis": { "scene": "consultation", "details": [...] },
      "experience_order": 1
    }
  ],
  "videos": [
    {
      "file_path": "...",
      "preflight_analysis": { "scene": "treatment_mood", "orientation": "vertical" },
      "reels_eligible": true,
      "duration_sec": 13.3
    }
  ],
  "media_preflight": {
    "model_mode": "multimodal_direct",
    "representative_photo_ids": [5, 1, 3],
    "key_visual_evidence": ["LED dome", "candle ambiance", "dual chair"],
    "question_focus_candidates": ["customer reaction", "group booking context"]
  },
  "interview": {
    "turn1_transcript": "...",
    "turn2_transcript": "...",
    "turn3_transcript": "...",
    "main_angle": "Filipino tourists booked before arriving in Korea",
    "keywords": ["Philippines", "5 people", "K-beauty", "reservation"]
  },
  "structure_mode": "narrative_flow",
  "experience_sequence": [5, 1, 3, 4, 2]
}
```

### 4.2 Content generation order (sequential, blog-first)

Content is generated sequentially with the blog as the master document. All other platforms derive from the blog to maintain tone consistency and reduce LLM calls.

```
1. Naver Blog (master experience-set article)
       │
       ├──→ 2. Instagram caption + hashtags (blog condensed)
       ├──→ 3. Threads posts (blog hook + key points)
       ├──→ 4. Naver Place intro (blog info excerpt)
       └──→ 5. Reels edit spec JSON (blog key phrases + video analysis)
                 ↑ only if reels_eligible video exists
```

### 4.3 Naver Blog — Experience-set article

The blog is the richest content piece. Instead of forcing every post into a strict story arc, the system first decides how the interview + media should be packaged into one coherent experience set for the reader.

**Possible structure modes:**

| Mode | When used | Output shape |
|------|-----------|--------------|
| Narrative flow | Photos show a clear before/during/after progression | Reader follows the experience step by step |
| Key moments | Photos are not chronological but capture distinct highlights | Reader moves through memorable scenes, differentiators, and reactions |
| Proof points | Photos are sparse, repetitive, or result-heavy | Reader gets evidence of expertise, atmosphere, and customer response anchored to available media |

**Default structure:**
```
[Hook paragraph — main angle, no photo]
  ↓
[Experience block 1 — strongest opening photo + what was happening]
  ↓
[Experience block 2 — signature step / differentiator]
  ↓
[Experience block 3 — customer reaction / outcome / proof]
  ↓
[Optional additional blocks from remaining media]
  ↓
[Closing — shop info, location, CTA]
  ↓
[Hashtags — SEO-optimized for Naver search]
```

If `structure_mode == narrative_flow`, the blocks follow consultation → treatment → result.  
If `structure_mode == key_moments`, the blocks are ordered by importance and clarity, not time.  
If `structure_mode == proof_points`, the blocks group evidence around expertise, atmosphere, and customer response.

**Experience-set assembly logic:**
```python
if supports_clear_timeline(photos):
    structure_mode = "narrative_flow"
elif has_distinct_moments(photos):
    structure_mode = "key_moments"
else:
    structure_mode = "proof_points"

for media_unit in ordered_experience_sequence:
    section = LLM(
        system="Write a blog section in friendly shop-owner tone. 
                Use the interview as the spine and the media as evidence.
                If the sequence is chronological, make it feel like a flow.
                If not, organize it around key moments, differentiators,
                and customer reactions.",
        context={
            "structure_mode": structure_mode,
            "media_analysis": media_unit.preflight_analysis,
            "interview_transcripts": all_transcripts,
            "main_angle": content_bundle.main_angle,
            "previous_sections": sections_so_far
        }
    )
```

**Tone:** Friendly neighborhood shop owner (친근한 동네 사장님 톤). Uses casual sentence endings, occasional ㅎㅎ/ㅋㅋ, emoticons sparingly.

### 4.4 Instagram — Carousel post

**Photo order:** Same as blog experience sequence.

**Caption:** Condensed from blog. Structure:
```
[Hook line — main angle, 1-2 lines]
[Customer reaction quote, 1-2 lines]
[Key differentiators, bullet style]
[Location + CTA]
[Hashtags — 15 tags, mix of search-volume and niche]
```

**Hashtag strategy:**
- Search volume tags (5): #서면헤드스파 #부산헤드스파 #헤드스파추천 etc.
- Context tags (5): #외국인반응 #K뷰티 #부산관광코스 etc.
- Brand tags (3): #시선을즐기다 #매장명 etc.
- English tags (2): #headspakorea #busantrip (foreign search capture)

### 4.5 Threads — Hook + reply thread

```
Post 1 (Hook):
  Main angle in 2-3 punchy sentences. Designed to stop scrolling.

Post 2 (Reply):
  Story details — customer reaction, what made it special.

Post 3 (Reply):
  Shop info — location, key features, soft CTA.
```

### 4.6 Naver Place — Intro text

Information-focused excerpt from the blog. No casual tone — slightly more professional. Emphasizes: what the shop does, key differentiator, location convenience, group/individual capacity.

### 4.7 Instagram Reels — Edit spec JSON

Only generated when a reels-eligible video exists in the content bundle.

**JSON structure:**
```json
{
  "source": {
    "file": "video.mp4",
    "duration_sec": 13.3,
    "orientation": "vertical"
  },
  "video_analysis": {
    "scene_type": "single_take_slow_pan",
    "color_transitions": [
      { "time": "0.0-4.0", "color": "blue" },
      { "time": "4.0-8.0", "color": "white" },
      { "time": "8.0-13.3", "color": "green" }
    ]
  },
  "edit_spec": {
    "audio": {
      "original_audio": "mute",
      "bgm": { "mood": "lo-fi_chill_ambient", "volume": 0.6 }
    },
    "text_overlays": [
      {
        "text": "Hook text from interview",
        "start_sec": 0.0,
        "end_sec": 4.0,
        "position": "top_center",
        "animation": "fade_up",
        "style": { "font_size": 42, "stroke": true }
      },
      {
        "text": "Customer reaction quote",
        "start_sec": 4.5,
        "end_sec": 8.0,
        "position": "center",
        "animation": "typewriter"
      },
      {
        "text": "Location + shop name CTA",
        "start_sec": 9.0,
        "end_sec": 13.3,
        "position": "bottom_center",
        "animation": "slide_up"
      }
    ],
    "effects": [
      { "type": "color_grade", "preset": "warm_lift" },
      { "type": "vignette", "intensity": 0.2 },
      { "type": "fade_in", "duration_sec": 0.8 },
      { "type": "fade_out", "duration_sec": 1.5 }
    ],
    "caption": "Instagram reels caption text + hashtags"
  },
  "rendering_notes": {
    "text_safe_zone": "top 15%, bottom 20%, right 15% avoid (IG UI overlap)",
    "export": { "codec": "h264", "bitrate": "8M", "fps": 30 }
  }
}
```

---

## 5. Media editing pipeline

### 5.1 Architecture: LLM spec → Python CLI execution

The LLM generates edit specifications as JSON. A Python CLI tool reads the JSON and executes the edits. This cleanly separates context judgment (LLM) from precise execution (code).

```
LLM → Edit Spec JSON → Python CLI → Rendered output
```

### 5.2 Photo processing (Pillow)

| Operation | Tool | When |
|-----------|------|------|
| Resize for platform | Pillow | All photos, per-platform specs |
| Watermark/logo overlay | Pillow | If shop has branding assets |
| Carousel numbering | Pillow | Instagram carousel if needed |

### 5.3 Video processing (FFmpeg)

| Operation | FFmpeg filter | When |
|-----------|--------------|------|
| Text overlay | `drawtext` | All reels |
| Text animation (fade, slide) | `drawtext` + `enable` timing | Per edit spec |
| Color grading | `colorbalance`, `curves` | Per edit spec |
| Vignette | `vignette` | Per edit spec |
| Fade in/out | `fade` | Per edit spec |
| BGM mix | `amix` + volume filter | All reels (original audio muted) |
| Export | h264, 9:16, 30fps | All reels |

### 5.4 JSON-to-FFmpeg conversion example

```python
def build_ffmpeg_command(spec: dict) -> str:
    filters = []
    
    # Text overlays
    for overlay in spec["text_overlays"]:
        filters.append(
            f"drawtext=text='{overlay['text']}':"
            f"fontsize={overlay['style']['font_size']}:"
            f"fontcolor=white:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=h*{overlay['y_offset']}:"
            f"enable='between(t,{overlay['start_sec']},{overlay['end_sec']})'"
        )
    
    # Color grade
    if spec.get("color_grade"):
        filters.append("colorbalance=rs=0.1:gs=0.05:bs=-0.05")
    
    # Vignette
    if spec.get("vignette"):
        filters.append(f"vignette=PI/{spec['vignette']['intensity']}")
    
    return f"ffmpeg -i input.mp4 -vf \"{','.join(filters)}\" output.mp4"
```

---

## 6. Publishing pipeline

### 6.1 Auto-publish (no approval step)

Content is published immediately after generation and rendering. No owner approval or per-post revision is required under normal operations.

**Rationale:**
- Content source is the owner's own photos and voice — low factual error risk
- The product is sold as 12 recurring sets per month, not as one-off handcrafted posts
- Feedback compounds across the month, so quality improves through repeated calibration
- "Published 80-point content" beats "unpublished perfect content" for revenue
- Once revisions are offered, they become an ongoing service expectation and destroy operational leverage

**Exception handling:**
- No revision for tone, wording, structure, or creative preference
- Feedback is applied to the next set, not the current published set
- Only operationally serious issues are handled immediately: factual error, privacy/sensitive info exposure, wrong media attachment, or posting to the wrong destination

### 6.2 Platform-specific upload

| Platform | Method | Auto-upload in MVP | Notes |
|----------|--------|-------------------|-------|
| Naver Blog | Custom upload tool (existing) | Yes | Owner's existing Naver blog account |
| Instagram carousel | Meta Graph API | Yes | Requires business account |
| Threads | Meta Threads API | Yes | Requires linked Instagram business account |
| Instagram Reels | Manual by owner | No | API requires app review; MVP uploads reels file to Telegram for owner to post manually |

### 6.3 Post-publish notification

After all auto-uploads complete, the Telegram bot sends a summary:

```
✅ 콘텐츠가 업로드되었습니다!

📝 네이버 블로그: [link]
📸 인스타그램: [link]
🧵 쓰레드: [link]
🎬 릴스 영상: [첨부파일 — 직접 업로드해주세요]

피드백 설문에 참여하시면 다음 세트부터 바로 반영됩니다 👇
[설문 시작하기]
```

---

## 7. Feedback survey system

### 7.1 Design principle

No per-post content revision exists. Instead, an optional feedback survey collects improvement signals for future content generation. The owner can take it or skip it — zero pressure.

The service is designed around repetition and learning:
- 12 sets are produced across the month
- The first week is a calibration period
- Feedback tunes tone, length, emphasis, and structure for later sets
- The system becomes more accurate over time without creating a revision queue

### 7.2 Survey flow (Telegram inline buttons)

```
Q1: "이번 콘텐츠 전체적으로 어떠셨어요?"
    [😍 매우 좋아요] [👍 괜찮아요] [😐 보통이에요] [👎 아쉬워요]

IF 👎 or 😐:
  Q2: "어떤 부분이 아쉬우셨어요?" (multi-select)
      [□ 글 톤/분위기] [□ 사진 순서] [□ 핵심 내용 누락] [□ 너무 길어요]

IF any selection:
  Q3: "다음 콘텐츠에 반영할게요! 혹시 한마디 더 있으시면 음성으로 남겨주세요."
      (optional voice memo — stored as future context)

ALWAYS:
  Q_final: "다음에 강조하고 싶은 포인트가 있으면 알려주세요!"
      [□ 시술 과정] [□ 고객 반응] [□ 가격/이벤트] [□ 매장 분위기] [□ 상관없어요]
```

### 7.3 Feedback data usage

Feedback is stored per-shop and used as context in future content generation:

```python
shop_profile = {
    "preferred_tone": "casual",       # derived from Q2 feedback history
    "preferred_length": "medium",      # derived from Q2 feedback history
    "emphasis_preference": "고객 반응", # derived from Q_final history
    "calibration_stage": "week_1",     # early sets vs stabilized pattern
    "sets_completed_this_month": 3,
    "satisfaction_history": [5, 4, 5, 3, 4],
    "custom_notes": ["사장님 prefers shorter blog posts"]
}
```

This profile is injected into the LLM system prompt for future content generation, creating a learning loop without requiring per-content revision. The goal is not to perfect one post through edits, but to make the next 9-11 sets progressively better.

---

## 8. Tech stack

### 8.1 Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| Bot framework | python-telegram-bot | Async, webhook mode |
| Server | VPS or cloud function | Stateless processing |
| Queue | Redis or cloud task queue | Media processing jobs |
| Storage | S3-compatible | Photos, videos, generated content |
| Database | PostgreSQL | Shops, chat mappings, integration configs, feedback, content history |

### 8.1.1 Multi-shop backend foundation

- `shops` table or registry: stable `shop_id`, shop metadata, content preferences
- `shop_invite_tokens`: valid deep-link onboarding tokens
- `telegram_chat_mappings`: maps one Telegram room/chat to one shop
- `shop_integrations`: per-shop Naver/Meta credentials references and publish targets
- `shop_sessions`: one row per content run with shop ownership
- `chat_logs`: session-scoped record of bot/customer messages and attached media
- Artifact storage layout: namespaced by `shop_id/session_id`

### 8.2 AI services

| Service | Provider | Purpose |
|---------|----------|---------|
| Multimodal interview engine | Claude / GPT-4o-class multimodal model | Direct image understanding, media preflight, Turn 2/3 question generation |
| STT | OpenAI Whisper API | Voice transcription (Korean) |
| STT fallback | Clova Speech API | Korean dialect/jargon accuracy |
| Content LLM | Claude Sonnet / GPT-4o | Blog/article generation and platform derivations |
| Edit spec LLM | Same as content LLM | JSON edit spec generation |

### 8.3 Media processing

| Tool | Purpose |
|------|---------|
| Pillow | Photo resize, watermark, carousel prep |
| FFmpeg | Video text overlay, transitions, BGM, export |
| python-pptx | Not needed (no presentation output) |

### 8.4 Publishing APIs

| Platform | API | Auth |
|----------|-----|------|
| Naver Blog | Custom tool (Playwright-based) | Naver account cookies |
| Instagram | Meta Graph API v21+ | Business account + app token |
| Threads | Meta Threads API | Linked IG business account |
| Reels | Manual (MVP) | N/A |

---

## 9. Data flow — Complete sequence

```
1.  Owner sends 5 photos + 1 video to Telegram bot
2.  Bot acknowledges: "사진 잘 받았습니다! 분석 중..."
3.  Multimodal LLM preflight reviews all media (parallel, ~5 sec)
      → Photo sequence: [photo5, photo1, photo3, photo4, photo2]
      → Video reels eligible: true (vertical, 13s, mood shot)
      → Industry: head spa
      → Key visual evidence: LED dome, scalp analysis, candle, eye mask, dual chair
4.  Bot sends Turn 1 question (voice expected)
5.  Owner sends ~1 min voice memo
6.  Whisper transcribes → "필리핀에서 5명이 관광 오면서..."
7.  Multimodal LLM call: original photos + media_preflight + Turn 1 transcript → Turn 2 planner JSON
8.  Bot sends Turn 2 question
9.  Owner sends ~1 min voice memo
10. Whisper transcribes → "한류 열풍 때문에 K-뷰티를..."
11. Multimodal LLM call: original photos + media_preflight + Turns 1-2 transcripts → Turn 3 planner JSON
12. Bot sends Turn 3 question about differentiator
13. Owner sends ~1 min voice memo
14. Whisper transcribes → "두피검사 후 맞춤 코스 추천..."
15. Bot: "인터뷰 완료! 콘텐츠 제작 중입니다. 약 3-5분 소요됩니다."
16. Backend assembles content bundle
17. LLM generates blog (narrative flow, key moments, or proof-point structure)
18. LLM derives: Instagram caption, Threads posts, Naver Place intro
19. LLM generates reels edit spec JSON
20. Python CLI renders reels video (FFmpeg)
21. Auto-publish: Naver Blog, Instagram carousel, Threads
22. Bot sends completion notification with links
23. Bot attaches rendered reels video for manual upload
24. Bot offers optional feedback survey
25. (Optional) Owner completes survey → stored in shop profile
```

---

## 10. MVP scope and phasing

### Phase 1 — Core pipeline (Week 1-4)

- [ ] Telegram bot setup (photo/video/voice receive)
- [ ] Multimodal media preflight integration (direct media input + experience sequence sort)
- [ ] Whisper STT integration
- [ ] 3-turn interview flow with multimodal question generation
- [ ] Blog content generation (experience-set article)
- [ ] Naver Blog auto-upload

### Phase 2 — Multi-platform (Week 5-6)

- [ ] Instagram caption + hashtag generation
- [ ] Threads post generation
- [ ] Naver Place intro generation
- [ ] Meta Graph API integration (Instagram carousel upload)
- [ ] Meta Threads API integration

### Phase 3 — Reels + feedback (Week 7-8)

- [ ] Video reels eligibility check
- [ ] Reels edit spec JSON generation
- [ ] FFmpeg rendering pipeline
- [ ] Reels file delivery via Telegram (manual upload)
- [ ] Feedback survey system
- [ ] Shop profile learning loop

### Phase 4 — Optimization (Week 9+)

- [ ] Content quality scoring (automated)
- [ ] A/B test different blog tones
- [ ] Batch processing (multiple posts per session)
- [ ] Reels auto-upload when API access approved
- [ ] Multi-language support (English captions for foreign tourist angle)

---

## 11. Key design decisions log

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Interview Turn 1 | Fixed common question | Builds habit, lets owner set the angle |
| Interview Turn 2 | Answer + photo combined | Merges owner intent with visual context |
| Interview Turn 3 | Gap filler | Ensures minimum content material |
| Media understanding | Direct multimodal input, not separate Vision-to-text extraction | Preserves visual context for better questions |
| Content revision | No per-post revision; feedback rolls into the next set | Protects operating leverage and reinforces the product model |
| Post-publish feedback | Optional survey | Learning loop without blocking publish |
| Service cadence | 12 sets per month | Repetition gives the system enough data to calibrate quickly |
| Tenant model | Multi-tenant backend with shop-scoped isolation | Needed for multiple clients, credentials, and publishing targets |
| Conversation visibility | Persist bot/customer chat logs per session | Needed for QA, support, and later prompt tuning |
| Content generation order | Blog first, others derived | Tone consistency, fewer LLM calls |
| Core content structure | Experience set first, narrative when supported | Handles both chronological and non-chronological media |
| Reels approach | Single clip + text overlay | Owners don't shoot "reels-ready" footage |
| Reels upload (MVP) | Manual via Telegram file | Meta Reels API requires app review |
| Approval flow | None — auto-publish | Owner's own words = low factual risk, and approval breaks the recurring model |
| Photo ordering | Multimodal preflight builds best-fit experience sequence | Timeline when possible, key moments when not |
| Edit execution | LLM JSON spec → Python CLI | Separates judgment from execution |

---

## 12. Risk mitigation

| Risk | Mitigation |
|------|-----------|
| STT accuracy (Korean dialects) | Whisper primary + Clova Speech fallback |
| Owner sends low-quality photos | Multimodal preflight flags unusable media; bot asks for replacements or falls back to interview-led structure |
| Owner gives very short answers | Turn 3 gap filler compensates; minimum 3-element check |
| Early sets miss the preferred tone | Use week-1 feedback as calibration and improve subsequent sets rather than revising the current one |
| Photos do not support clear narrative flow | Switch to key-moments or proof-point structure using interview as the primary spine |
| Question quality drops because media is over-compressed into text | Send original media directly to the multimodal model for Turn 2/Turn 3 planning |
| Credentials or publish targets get mixed across shops | Resolve all publishing actions through shop-scoped config and chat-to-shop mapping |
| Meta API rate limits | Queue-based publishing with retry logic |
| Naver Blog upload blocked | Cookie refresh automation; alert owner if manual login needed |
| Content sounds too generic | Experience-set structure forces each section to anchor to media evidence or customer detail |
| Clients expect live revisions | Position the service clearly as feedback-driven monthly production, not per-post editing |
| Owner never does feedback | Survey is optional; system works without it |

---

*End of document*
