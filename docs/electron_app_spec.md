# Thohago Desktop App -- Electron Application Specification

## 1. Executive Summary

Thohago is pivoting from a B2B agency service (Telegram bot + web admin) to a B2C self-service content creation tool focused on guided, interview-based generation. Users upload photos/videos, conduct a 3-turn AI interview, configure a compact generation profile, and the system generates multi-platform content: Naver blog posts, Instagram carousels, Instagram Reels/Shorts videos, and Threads post chains.

The desktop application is built on electron-backend-starter (Electron 35 + React 19 + TypeScript + Vite 6), reusing its plugin architecture, SQLite database layer, IPC bridge, onboarding flow, and billing stubs. The existing Thohago Python pipeline (interview engine, content composers, PIL/FFmpeg renderers, publishing clients) runs as a Python sidecar process communicating over stdio JSON-RPC.

The key differentiator for V1 is a guided generation workflow rather than a freeform editor. Before generation, users set structured controls such as tone, content length, emphasis point, required keywords, excluded phrases, photo priority, and representative photo. After generation, users can run bounded regeneration actions such as regenerate, tone shift, shorter/longer, more premium, and stronger CTA. Internally, each content piece is still represented as a JSON spec, but users do not edit the spec directly in MVP. The goal is to consistently produce outputs that feel 70-80% ready to publish with minimal user effort.

- Target platforms: Windows (primary), macOS (secondary).
- Target users: Korean small business owners (shops, restaurants, salons).
- Primary AI provider: Google Gemini (free tier). Fallback: Anthropic Claude, OpenAI GPT.

---

## 2. Tech Stack

### Reused from electron-backend-starter (as-is or with minor modifications)

| Component | Source | Modification |
|---|---|---|
| Electron 35 + electron-vite | apps/desktop | As-is |
| React 19 + Zustand | apps/desktop/src/renderer | As-is |
| Plugin system (StarterPlugin interface) | packages/plugin-api | As-is |
| IPC bridge (plugin:{id}:{action}) | packages/ipc-bridge | As-is |
| SQLite + migration system | apps/backend (Node 22 built-in) | Extend with Thohago tables |
| Hash-based router | Renderer | Add Thohago routes |
| Onboarding wizard | Existing plugin | Replace steps with Thohago onboarding |
| Toss Payments billing | Existing plugin | Keep as stub for MVP |
| pnpm monorepo structure | Root | As-is |

### New additions

| Component | Purpose |
|---|---|
| Python 3.12 sidecar | Runs Thohago pipeline (interview, content gen, rendering) |
| python-sidecar package | TypeScript wrapper for stdio JSON-RPC communication |
| Google Gemini SDK (Python) | Primary AI provider for interview + content generation |
| FFmpeg binary (bundled) | Video rendering for Reels/Shorts |
| Pillow (Python) | Carousel image rendering |
| Google Cloud TTS (Python) | Voiceover for video content |
| Cafe24 fonts (bundled) | Korean typography for rendered content |
| MediaRecorder API | Voice recording during interview |
| Web Audio API | Audio visualization during recording |

### Removed / replaced from starter

| Starter Component | Replaced With |
|---|---|
| Writing panel plugin | Thohago content generation/review plugins |
| Prompt template system | Thohago interview engine + content composers |
| Naver posting service | Thohago multi-platform publisher |
| Blog ID onboarding step | Thohago project folder + API key onboarding |

---

## 3. Plugin Architecture

Each major feature is a standalone plugin following the StarterPlugin interface with main/preload/renderer layers. Plugins communicate through the IPC bridge using plugin:{id}:{action} channels.

### Plugin Registry (config/plugins.config.ts)

```
thohago-onboarding       # API key setup, project folder, first-run wizard
thohago-sidecar          # Python process lifecycle management
thohago-project          # Project CRUD, media upload, generation profile, dashboard
thohago-interview        # 3-turn AI interview (voice + text)
thohago-blog-review      # Naver blog generation, preview, regeneration
thohago-video-review     # Reels/Shorts generation, preview, regeneration
thohago-carousel-review  # Instagram carousel generation, preview, regeneration
thohago-thread-review    # Threads 3-post chain generation, preview, regeneration
thohago-publisher        # Multi-platform publishing (Naver, Instagram, Threads)
```

### Plugin Responsibilities

**thohago-onboarding**
- Main: Validates API keys, checks Python/FFmpeg availability
- Renderer: Step wizard UI (API key input, project folder picker, dependency check)
- Activation gate: Blocks app until onboarding complete

**thohago-project**
- Main: SQLite CRUD for projects, media file operations, generation profile persistence
- Renderer: Dashboard, project detail view, media upload dropzone, generation profile form
- IPC actions: create-project, list-projects, get-project, delete-project, import-media, save-generation-profile, get-generation-profile

**thohago-interview**
- Main: Coordinates with sidecar for interview engine, handles audio file I/O
- Renderer: Interview Q&A UI, voice recorder, turn progress indicator
- IPC actions: start-interview, submit-answer, get-question, record-audio, transcribe-audio

**thohago-blog-review**
- Main: Coordinates with sidecar for BlogComposer and regeneration presets, manages blog JSON spec
- Renderer: Blog preview, generation summary, regeneration toolbar, publish button
- IPC actions: generate-blog, regenerate-blog, get-blog-spec

**thohago-video-review**
- Main: Coordinates with sidecar for narrative generation, TTS, FFmpeg render, regeneration presets
- Renderer: Video timeline preview, rendered video player, generation summary, regeneration toolbar
- IPC actions: generate-video-spec, regenerate-video, render-video, get-render-status

**thohago-carousel-review**
- Main: Coordinates with sidecar for carousel spec generation, PIL render, regeneration presets
- Renderer: Slide gallery preview, selected slide detail, generation summary, regeneration toolbar
- IPC actions: generate-carousel-spec, regenerate-carousel, render-slides

**thohago-thread-review**
- Main: Coordinates with sidecar for Threads post chain generation and regeneration presets
- Renderer: 3-post preview, generation summary, regeneration toolbar
- IPC actions: generate-thread, regenerate-thread

**thohago-publisher**
- Main: Coordinates with sidecar for Naver, Instagram Graph API, Threads API calls
- Renderer: Platform selector, credential management, publish status dashboard
- IPC actions: publish-blog, publish-carousel, publish-reels, publish-thread, get-publish-status

**thohago-sidecar**
- Main: Spawns/manages Python process, stdio JSON-RPC transport, health checks
- Preload: Exposes sidecar status to renderer
- Renderer: Sidecar status indicator (connected/disconnected/error)
- IPC actions: sidecar-start, sidecar-stop, sidecar-status, sidecar-call

---

## 4. Python Sidecar Design

### Communication Protocol: stdio JSON-RPC 2.0

The Electron main process spawns a single long-lived Python process. Communication uses JSON-RPC 2.0 over stdin/stdout with newline-delimited JSON (NDJSON). stderr is reserved for Python logging (forwarded to Electron's logger).

Why stdio JSON-RPC (not HTTP, not raw IPC):
- No port conflicts on user machines
- No firewall issues
- Simpler than HTTP server lifecycle
- Proven pattern (LSP, MCP servers)
- Bidirectional: Python can send progress notifications

### TypeScript Client (packages/python-sidecar/)

```typescript
interface SidecarClient {
  start(): Promise<void>;
  stop(): Promise<void>;
  call<T>(method: string, params: Record<string, unknown>): Promise<T>;
  onNotification(handler: (method: string, params: unknown) => void): void;
}
```

### Python Server (sidecar/server.py)

The Python side implements a JSON-RPC dispatcher that routes method calls to the existing Thohago modules:

```
Method                          -> Python Module
------------------------------------------------------------
interview.build_preflight       -> interview_engine.build_preflight()
interview.plan_turn             -> interview_engine.plan_turn()
interview.transcribe            -> groq_live.audio_transcription() or whisper
content.compose_blog            -> content.BlogComposer.compose()
content.generate_carousel_spec  -> generators/carousel.py
content.generate_video_spec     -> generators/video.py
content.generate_thread         -> generators/thread.py
content.regenerate_blog         -> prompt_builder.py + content.BlogComposer.compose()
content.regenerate_carousel     -> prompt_builder.py + generators/carousel.py
content.regenerate_video        -> prompt_builder.py + generators/video.py
content.regenerate_thread       -> prompt_builder.py + generators/thread.py
render.carousel                 -> render_instagram_carousel.render_slides()
render.video                    -> render_from_spec FFmpeg pipeline
render.video_status             -> poll FFmpeg process progress
publish.naver_blog              -> publish module
publish.instagram_carousel      -> instagram_publish.InstagramGraphPublisher
publish.instagram_reels         -> instagram_publish (video variant)
publish.threads                 -> threads_publish.ThreadsPublisher
```

### Progress Notifications

For long-running operations (video rendering, AI generation), the Python sidecar sends JSON-RPC notifications:

```json
{"jsonrpc": "2.0", "method": "progress", "params": {"task_id": "render_001", "percent": 45, "message": "Encoding segment 3/7..."}}
```

### Python Process Lifecycle

1. Startup: Electron spawns `python -u sidecar/server.py --project-root <path>` on app launch
2. Health check: Electron sends system.ping every 10 seconds
3. Graceful shutdown: Electron sends system.shutdown, waits 5 seconds, then kills
4. Crash recovery: Auto-restart with exponential backoff (1s, 2s, 4s, max 30s)
5. Bundling: Python is bundled via PyInstaller for distribution (or user installs Python separately for MVP)

### Reuse of Existing Python Files

| File | Reuse Strategy |
|---|---|
| models.py | As-is -- data classes shared across sidecar |
| interview_engine.py | As-is -- HeuristicMultimodalInterviewEngine |
| anthropic_live.py | As-is -- AnthropicMultimodalInterviewEngine |
| groq_live.py | As-is -- GroqMultimodalInterviewEngine + STT |
| openai_live.py | As-is -- OpenAIMultimodalInterviewEngine |
| heuristics.py | As-is -- keyword extraction, angle detection |
| content.py | As-is -- BlogComposer |
| instagram_content.py | As-is -- InstagramCaptionComposer |
| threads_content.py | As-is -- ThreadsCaptionComposer |
| artifacts.py | As-is -- session artifact I/O |
| config.py | Modified -- read config from JSON-RPC params instead of .env |
| pipeline.py | Modified -- decompose into individual RPC-callable steps |
| transcription.py | As-is for file-based; add live audio transcription method |
| publish.py | As-is -- MockNaverPublisher + real publisher |
| instagram_publish.py | As-is -- InstagramGraphPublisher |
| threads_publish.py | As-is -- ThreadsPublisher |
| render_instagram_carousel.py | Extracted -- move from client dir to sidecar/renderers/ |
| render_from_spec.py | Extracted -- move from client dir to sidecar/renderers/ |
| generate_carousel.py | Extracted -- move AI generation logic to sidecar/generators/ |
| generate_thread.py | Extracted -- move AI generation logic to sidecar/generators/ |

New Python files:

| File | Purpose |
|---|---|
| sidecar/server.py | JSON-RPC stdio server entry point |
| sidecar/dispatcher.py | Method routing |
| sidecar/prompt_builder.py | Builds initial generation + regeneration prompts from structured controls |
| sidecar/gemini_client.py | Google Gemini API wrapper |
| sidecar/generators/__init__.py | Unified content generation interface |
| sidecar/renderers/__init__.py | Unified render interface |

---

## 5. Data Model

### SQLite Schema (extends starter's migration system)

```sql
-- Migration: 001_thohago_core.sql

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  shop_display_name TEXT NOT NULL,
  shop_profile JSON NOT NULL DEFAULT '{}',
  generation_profile JSON NOT NULL DEFAULT '{}',
  media_folder_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'created',
  -- status values: created | interviewing | ready_to_generate | generating | reviewing | published
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS media_assets (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  media_id TEXT NOT NULL,
  kind TEXT NOT NULL,          -- photo | video
  file_path TEXT NOT NULL,
  file_name TEXT NOT NULL,
  experience_order INTEGER NOT NULL DEFAULT 0,
  preflight_analysis JSON DEFAULT NULL,
  selected_for_prompt INTEGER NOT NULL DEFAULT 0,
  reels_eligible INTEGER NOT NULL DEFAULT 0,
  duration_sec REAL DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS interview_sessions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending',
  -- status values: pending | turn_1 | turn_2 | turn_3 | completed
  preflight JSON DEFAULT NULL,
  turn1_question TEXT DEFAULT NULL,
  turn1_answer TEXT DEFAULT NULL,
  turn1_audio_path TEXT DEFAULT NULL,
  turn2_question TEXT DEFAULT NULL,
  turn2_answer TEXT DEFAULT NULL,
  turn2_audio_path TEXT DEFAULT NULL,
  turn3_question TEXT DEFAULT NULL,
  turn3_answer TEXT DEFAULT NULL,
  turn3_audio_path TEXT DEFAULT NULL,
  planner_data JSON DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS content_specs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  content_type TEXT NOT NULL,  -- blog | carousel | video | thread
  spec JSON NOT NULL,
  generation_count INTEGER NOT NULL DEFAULT 0,
  last_generation_mode TEXT DEFAULT NULL,
  rendered_artifacts JSON DEFAULT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  -- status values: draft | rendering | ready | published
  publish_result JSON DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generation_runs (
  id TEXT PRIMARY KEY,
  content_spec_id TEXT NOT NULL REFERENCES content_specs(id) ON DELETE CASCADE,
  mode TEXT NOT NULL,
  -- mode values: initial | regenerate | tone_shift | length_shorter | length_longer | premium | cta_boost
  directive JSON NOT NULL DEFAULT '{}',
  prompt_snapshot JSON NOT NULL,
  output_spec JSON DEFAULT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  error_message TEXT DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Generation Profile (stored in `projects.generation_profile`)

```json
{
  "industry": "restaurant",
  "tone": "friendly",
  "content_length": "standard",
  "emphasis_point": "signature brunch set and cozy interior",
  "must_include_keywords": ["성수 브런치", "수제 잠봉뵈르"],
  "avoid_phrases": ["가성비 최고", "무조건 방문"],
  "photo_priority": ["photo_3", "photo_1", "photo_2"],
  "hero_photo_id": "photo_3"
}
```

### Regeneration Directives

The post-generation controls are bounded presets rather than freeform edits:

- `regenerate`: same profile, fresh attempt
- `tone_shift`: rerun with a different tone
- `length_shorter`: compress copy or duration
- `length_longer`: expand copy or duration
- `premium`: make the output feel more upscale and refined
- `cta_boost`: strengthen the closing call-to-action

### JSON Spec Formats

The JSON specs remain internal contracts between the generator, renderer, preview, and publisher. Users do not edit these specs directly in MVP.

#### Blog Spec (content_type = 'blog')

```json
{
  "version": "1.0",
  "type": "naver_blog_spec",
  "title": "Blog title",
  "sections": [
    {
      "section_id": "s01",
      "type": "text",
      "content_html": "<p>Body text...</p>",
      "photo_id": null
    },
    {
      "section_id": "s02",
      "type": "photo_with_text",
      "content_html": "<p>Photo description text...</p>",
      "photo_id": "photo_1"
    }
  ],
  "hashtags": ["#tag1", "#tag2"],
  "metadata": {
    "main_angle": "angle description",
    "structure_mode": "narrative_flow",
    "word_count": 850
  }
}
```

#### Carousel Spec (content_type = 'carousel')

Reuses the existing instagram_carousel_edit_spec.json format verbatim. This is the same format already consumed by render_instagram_carousel.py. Key structure:

- version, type, source (directory, image_count)
- design_system (target_resolution 1080x1350, aspect_ratio 4:5, safe_zone, fonts, colors, overlay_style_defaults)
- slides[] (order, source_file, role, crop_anchor, headline, subheadline, overlay_position, text_style)
- caption (primary, cta), hashtags[], rendering_notes

The existing spec at client/sisun8082/2026_03_27/images/instagram_carousel_edit_spec.json is the canonical reference for this format.

#### Video/Reels Spec (content_type = 'video')

Reuses the existing shorts_render_spec.json format documented in docs/shorts_render_spec_schema.md. Key structure:

- version, source (shop_id, session_id, target_duration_sec)
- timeline[] (clip_id, beat_id, asset_type, asset_id, source_path, start_sec, end_sec, duration_sec, trim, motion, transition_in, transition_out, caption_ids)
- text_overlays[] (text_id, kind, text, start_sec, end_sec, position, style_preset, animation_in, animation_out)
- voiceover (mode, script_blocks[], subtitle_mode, subtitle_style)
- audio (bgm, original_audio, mixing)
- visual_effects (color_grade, vignette, safe_zone)
- export (aspect_ratio 9:16, resolution 1080x1920, fps 30, codec h264)
- validation rules

The existing spec at client/sisun8082/2026_03_27/shorts_pipeline_test/shorts_render_spec.json is the canonical reference.

#### Thread Spec (content_type = 'thread')

```json
{
  "version": "1.0",
  "type": "threads_post_spec",
  "main_post": "Main post text",
  "reply_1": "Reply 1 text",
  "reply_2": "Reply 2 text with #hashtag1 #hashtag2",
  "attached_photos": {
    "main_post": ["photo_1"],
    "reply_1": [],
    "reply_2": []
  }
}
```

The existing output at client/sisun8082/2026_03_27/thread_output/thread_content.json is the canonical reference.

---

## 6. User Flow

```
[1. Dashboard]
    User sees project list (or empty state)
    -> "New Project" button

[2. Project Setup]
    Enter business name, profile info
    Select/create project folder
    -> "Upload Media" button

[3. Media Upload]
    Drag-drop photos + videos into dropzone
    System runs preflight analysis (sidecar call)
    User reorders photos, sets photo priority, chooses representative photo
    -> "Start Interview" button

[4. AI Interview (3 turns)]
    Turn 1: System asks scene-anchor question
            User responds via voice recording or text input
            System transcribes audio if voice mode
    Turn 2: System generates detail-deepening question (based on turn 1)
            User responds
    Turn 3: System generates owner-perspective question
            User responds
    -> Interview complete, "Configure Generation" button

[5. Generation Setup]
    User configures:
      - Industry
      - Tone
      - Content length
      - Emphasis point
      - Required keywords
      - Excluded phrases
      - Photo priority
      - Representative photo
    -> "Generate All Content" button

[6. Content Generation]
    System generates all 4 content types in parallel:
      - Blog article (HTML spec)
      - Carousel (5-slide JSON spec -> PIL renders preview thumbnails)
      - Video/Reels (timeline JSON spec -> FFmpeg renders video)
      - Threads (3-post chain)
    Progress bars for each content type
    -> All content ready, navigate to project review

[7. Review + Regeneration]
    Project view shows 4 content tabs: Blog | Carousel | Video | Thread
    Each tab has:
      Left panel: Content preview (rendered output)
      Right panel: Generation summary + regeneration controls
    Available actions:
      - Regenerate
      - Tone change
      - Shorter / Longer
      - More premium
      - Stronger CTA
    Each action rebuilds the full content spec and re-renders the preview
    -> "Publish" button per content type

[8. Publishing]
    Select which platforms to publish
    Confirm content and credentials
    Publish progress + result URLs
    -> Return to dashboard
```

---

## 7. UI Pages and Components

### Pages (hash routes)

| Route | Page | Description |
|---|---|---|
| #/ | Dashboard | Project grid/list, stats, New Project CTA |
| #/onboarding | Onboarding | API key wizard (activation gate) |
| #/project/new | New Project | Name, profile, folder picker |
| #/project/:id | Project View | Overview, progress, links to interview, generation setup, review tabs |
| #/project/:id/interview | Interview | Q&A-style interview UI with voice recorder |
| #/project/:id/generate | Generation Setup | Guided generation profile + Generate All CTA |
| #/project/:id/blog | Blog Review | Blog preview + regeneration controls |
| #/project/:id/carousel | Carousel Review | Slide gallery + regeneration controls |
| #/project/:id/video | Video Review | Video player + timeline + regeneration controls |
| #/project/:id/thread | Thread Review | 3-post preview + regeneration controls |
| #/project/:id/publish | Publish | Platform selector + publish status |
| #/settings | Settings | API keys, defaults, billing |

### Key Components

**Dashboard**: ProjectCard (thumbnail, name, status badge, last-edited), EmptyState (illustration + CTA), SidecarStatusBadge (green/red dot)

**Interview**: ChatBubble (question/answer messages), VoiceRecorder (record button, waveform, stop/retry), TextInput (multiline fallback), TurnIndicator (step 1/2/3)

**Generation Setup**: GenerationProfileForm (industry, tone, length, emphasis point, required keywords, excluded phrases), PhotoPriorityList (drag reorder), HeroPhotoPicker (representative photo), GenerateAllButton

**Review Controls** (shared across all content tabs): GenerationSummaryCard (current settings summary), RegenerationToolbar (regenerate, tone shift, shorter, longer, premium, CTA boost), GenerationRunList (history of attempts and outcomes)

**Content Previews**: BlogPreview (sandboxed iframe with HTML), CarouselSlideGallery (horizontal scroll of rendered slides), CarouselSlideDetail (single slide preview), VideoPlayer (HTML5 video for rendered .mp4), VideoTimeline (visual timeline bar), ThreadPreview (3 card mockups)

**Publishing**: PlatformCard (Naver/Instagram/Threads with status), CredentialForm (per-platform API entry), PublishProgress (step-by-step with result URLs)

---

## 8. Guided Generation and Regeneration Design

V1 removes freeform content editing and replaces it with structured control before generation plus bounded regeneration after generation.

### Architecture Flow

```
User clicks: "More premium"
    |
    v
[Electron Renderer] RegenerationToolbar component
    |
IPC: plugin:carousel-review:regenerate-carousel
    |
    v
[Electron Main] routes to sidecar
    |
JSON-RPC: content.regenerate_carousel
    |
    v
[Python Sidecar] prompt_builder.py + generators/carousel.py
    |
Builds prompt with:
  - Shop profile
  - Interview transcript and planner data
  - Generation profile
  - Available photos with priority + representative photo
  - Previous successful output summary (reference only)
  - Regeneration directive: { mode: "premium" }
    |
AI API call (Gemini primary, Claude fallback)
    |
Returns: a brand-new validated spec JSON
    |
    v
[Electron Main]
  - Validates returned spec
  - Stores a generation_runs record
  - Updates content_specs.spec + generation_count + last_generation_mode
  - Triggers render.carousel / render.video when needed
    |
    v
[Electron Renderer]
  - Updates preview
  - Updates generation history
  - Keeps publish action enabled only for the latest successful output
```

### Generation Profile Fields

Every project captures a structured generation profile before the first run:

- Industry
- Tone
- Content length
- Emphasis point
- Must-include keywords
- Excluded phrases
- Photo priority
- Representative photo

These controls are reused across all 4 content types, with content-specific prompt templates deciding how the fields map to blog structure, carousel headlines, video narrative, and thread copy.

### Regeneration Presets

After generation, each content type exposes bounded actions instead of freeform editing:

- `Regenerate`: same profile, fresh attempt
- `Tone Change`: rerun with a different tone preset
- `Shorter`: compress blog/thread copy or reduce video duration target
- `Longer`: expand blog/thread copy or increase video duration target
- `More Premium`: upscale phrasing, framing, and visual emphasis
- `CTA Boost`: strengthen call-to-action wording and placement

Each regeneration action creates a new full spec. The user never edits the JSON spec directly in MVP.

### Spec Validation

After AI returns a generated or regenerated spec, the sidecar validates:

- JSON schema compliance (required fields present, correct types)
- Reference integrity (photo_ids exist in project, source_paths valid)
- Constraint checking (carousel max 10 slides, video max 60s, thread max 500 chars per post)

If validation fails, the run is marked failed in `generation_runs`, the previous successful output remains active, and the UI offers retry.

### Re-render Behavior

- Carousel: full carousel spec regenerated, then all slides re-rendered
- Video: full spec regenerated, full FFmpeg render required (30-90 seconds)
- Blog: no sidecar rendering needed, preview updates from spec directly
- Thread: no sidecar rendering needed, preview updates from spec directly

---

## 9. Voice Recording and Transcription

### Recording Flow

1. User presses record button in Interview UI
2. Electron uses navigator.mediaDevices.getUserMedia({ audio: true })
3. MediaRecorder captures audio as WebM/Opus
4. Real-time Web Audio API AnalyserNode drives waveform visualization
5. On stop, audio Blob saved to project folder via IPC: plugin:interview:save-audio
6. Main process writes .webm file to {project_folder}/interview/turn{N}_audio.webm

### Transcription

Audio file sent to sidecar for transcription:

```
JSON-RPC: interview.transcribe
params: { "audio_path": "...", "language": "ko" }
```

The sidecar uses the existing groq_live.py GroqApiClient.audio_transcription() method (Whisper Large v3 on Groq, free tier). Fallback chain:

1. Groq Whisper (free, fast)
2. OpenAI Whisper API (paid fallback)
3. Google Speech-to-Text (if Gemini key available)

Users can skip voice recording and type answers directly. Text is sent as-is to the interview engine, bypassing transcription.

---

## 10. Content Generation Pipeline

After the 3-turn interview completes and the user finalizes the generation profile, all content types are generated in parallel. Each generation is a sidecar RPC call.

### Blog Generation

```
RPC: content.compose_blog
Input: { shop_profile, photos, transcripts, planner_data, generation_profile, regeneration_directive? }
Python: BlogComposer.compose() from content.py (reused as-is)
Output: Blog HTML string, then parsed into blog spec JSON sections
```

### Carousel Generation

```
RPC: content.generate_carousel_spec
Input: { shop_profile, photos (with base64 thumbnails), transcripts, preflight, generation_profile, regeneration_directive? }
Python: generate_carousel.py logic (extracted to sidecar/generators/carousel.py)
  - AI generates slide assignments + headlines + subheadlines
  - Sidecar builds full instagram_carousel_edit_spec.json with design_system defaults
Output: Complete carousel spec JSON (same format as existing spec)
```

### Video/Reels Generation

```
RPC: content.generate_video_spec
Input: { shop_profile, photos, videos, transcripts, preflight, generation_profile, regeneration_directive? }
Python: render_from_spec.py narrative generation logic (extracted to sidecar/generators/video.py)
  - Step 1: AI writes free narrative
  - Step 2: AI matches sentences to source photos/videos
  - Step 3: Generate TTS for each sentence (Google Cloud TTS)
  - Step 4: Build shorts_render_spec.json from TTS durations
Output: Complete video render spec JSON (same format as existing spec)
```

### Thread Generation

```
RPC: content.generate_thread
Input: { shop_profile, transcripts, blog_html_or_spec, generation_profile, regeneration_directive? }
Python: generate_thread.py logic (extracted to sidecar/generators/thread.py)
  - AI generates 3-post chain (main + 2 replies)
Output: Thread spec JSON { main_post, reply_1, reply_2, attached_photos }
```

### Regeneration Strategy

Initial generation and one-click regeneration share the same pipeline. A regeneration call reuses the interview data and generation profile, then applies a bounded directive:

- `regenerate`: no profile change, new attempt
- `tone_shift`: override tone only
- `length_shorter` / `length_longer`: adjust target word count or duration
- `premium`: push the prompt toward a more upscale, polished output
- `cta_boost`: make the closing invitation more action-oriented

### AI Provider Resolution

The sidecar uses the same fallback chain pattern as the existing pipeline_runtime.py:

1. Gemini (primary, free tier) -- new sidecar/gemini_client.py
2. Anthropic Claude -- existing anthropic_live.py
3. OpenAI GPT -- existing openai_live.py
4. Groq (for vision/STT only) -- existing groq_live.py

API keys passed from Electron via settings (stored in SQLite settings table, encrypted at rest).

---

## 11. Rendering Pipeline

### Carousel Rendering

```
RPC: render.carousel
Input: { spec: <carousel_spec_json>, project_folder: "..." }
Python: render_instagram_carousel.render_slides(spec) -- reused AS-IS
  1. For each slide: load image -> EXIF normalize -> crop_cover -> enhance -> draw_overlay
  2. Save as JPEG (quality 92) to {project_folder}/output/carousel/
  3. Write caption.txt and manifest.json
Output: { rendered_paths: ["slide_01.jpg", ...], manifest_path: "..." }
```

The existing renderer at client/sisun8082/2026_03_27/images/render_instagram_carousel.py handles: EXIF transpose, cover crop to 1080x1350, contrast/color/sharpness enhancement, readability gradient overlay, font loading (Cafe24Moyamoya + Cafe24Ohsquare), headline + subheadline text rendering with stroke, rounded-rectangle background panel, JPEG output with unsharp mask sharpening.

### Video Rendering

```
RPC: render.video
Input: { spec: <video_render_spec_json>, project_folder: "..." }
Python: render_from_spec.py pipeline -- reused with modifications
  1. Generate TTS audio files for each voiceover block (Google Cloud TTS, ko-KR-Chirp3-HD)
  2. Build FFmpeg filter chain from timeline spec
  3. Render segments: photos with Ken Burns motion, video clips with trim
  4. Apply text overlays with animation (fade_up, fade_in, slide_up)
  5. Mix voiceover + BGM + original audio per audio spec
  6. Encode final H.264 MP4 at 1080x1920 30fps
  7. Send progress notifications (percent, current segment)
Output: { video_path: "shorts_render.mp4", duration_sec: 24.0 }
```

### Blog Rendering

Blog content rendered directly in Electron renderer as HTML in a sandboxed iframe. Photo placeholders (div.photo-placeholder with data-photo-id) resolved to local file:// paths.

### Thread Rendering

Thread content is plain text. Rendered as styled card mockups in the Electron renderer (no sidecar rendering needed).

---

## 12. Publishing Pipeline

### Naver Blog

```
RPC: publish.naver_blog
Input: { blog_spec, shop_id, session_id }
Python: Uses publish.py -- currently MockNaverPublisher
  Future: Selenium-based or API-based Naver Blog posting
Output: { status: "published", url: "..." }
```

### Instagram Carousel

```
RPC: publish.instagram_carousel
Input: { rendered_slide_paths, caption, access_token, ig_user_id, fb_page_id }
Python: instagram_publish.InstagramGraphPublisher.publish_carousel() -- reused AS-IS
  1. Upload each slide to Facebook CDN (unpublished page photo)
  2. Create carousel item containers
  3. Create carousel container
  4. Wait for processing, then publish
Output: { status: "published", permalink: "...", ig_media_id: "..." }
```

### Instagram Reels

```
RPC: publish.instagram_reels
Input: { video_path, caption, access_token, ig_user_id }
Python: New method on InstagramGraphPublisher for video upload
Output: { status: "published", permalink: "...", ig_media_id: "..." }
```

### Threads

```
RPC: publish.threads
Input: { thread_spec, image_paths, threads_access_token, threads_user_id, fb_page_id }
Python: threads_publish.ThreadsPublisher -- reused AS-IS
  1. Publish main_post (text or image)
  2. Reply with reply_1
  3. Reply with reply_2
Output: { status: "published", permalink: "...", threads_media_id: "..." }
```

---

## 13. Onboarding Flow

The onboarding plugin acts as an activation gate (same pattern as starter). App is blocked until onboarding completes.

### Steps

**Step 1: Welcome** -- Language selection (Korean default), brief product intro.

**Step 2: AI API Key** -- Primary: Google Gemini API key (with link to free tier signup). Optional: Anthropic API key, OpenAI API key. Validation: test API call to verify key works.

**Step 3: Project Folder** -- Select default project storage location. Default: ~/Documents/Thohago/. Explanation: all projects, media, generated content stored here.

**Step 4: Dependency Check** -- Python 3.12+ availability. FFmpeg availability. If missing: download links and instructions (or bundled installer for distribution builds).

**Step 5: Ready** -- Summary of configuration. "Create Your First Project" CTA.

Settings stored in SQLite settings table: gemini_api_key (encrypted), anthropic_api_key (encrypted), openai_api_key (encrypted), groq_api_key (encrypted), project_root_path, onboarding_completed.

---

## 14. File Structure

```
thohago-desktop/
  package.json                              # pnpm workspace root
  pnpm-workspace.yaml
  apps/
    desktop/
      package.json
      electron.vite.config.ts
      src/
        main/
          index.ts                          # Electron main entry
          plugins/
            thohago-onboarding.main.ts
            thohago-sidecar.main.ts
            thohago-project.main.ts
            thohago-interview.main.ts
            thohago-blog-review.main.ts
            thohago-video-review.main.ts
            thohago-carousel-review.main.ts
            thohago-thread-review.main.ts
            thohago-publisher.main.ts
          services/
            sidecar-client.ts              # JSON-RPC stdio client
            database.ts                    # SQLite service
            settings.ts                    # Encrypted settings store
        preload/
          index.ts
          plugins/                         # Plugin preload layers
        renderer/
          index.html
          App.tsx
          router.tsx                       # Hash-based router
          stores/
            project.store.ts
            interview.store.ts
            content.store.ts
            sidecar.store.ts
          pages/
            Dashboard.tsx
            Onboarding.tsx
            ProjectNew.tsx
            ProjectView.tsx
            Interview.tsx
            GenerationSetup.tsx
            BlogReview.tsx
            CarouselReview.tsx
            VideoReview.tsx
            ThreadReview.tsx
            Publish.tsx
            Settings.tsx
          components/
            GenerationProfileForm.tsx
            PhotoPriorityList.tsx
            HeroPhotoPicker.tsx
            RegenerationToolbar.tsx
            GenerationRunList.tsx
            VoiceRecorder.tsx
            MediaGallery.tsx
            ProjectCard.tsx
            BlogPreview.tsx
            CarouselSlideGallery.tsx
            VideoPlayer.tsx
            VideoTimeline.tsx
            ThreadPreview.tsx
            SidecarStatusBadge.tsx
            GenerationSummaryCard.tsx
          plugins/                         # Plugin renderer layers
      resources/
        fonts/                             # Cafe24 font files
        icons/
  packages/
    plugin-api/                            # Reused from starter
    ipc-bridge/                            # Reused from starter
    python-sidecar/                        # NEW: TypeScript sidecar wrapper
      package.json
      src/
        client.ts                          # SidecarClient class
        protocol.ts                        # JSON-RPC types
        process-manager.ts                 # Spawn/kill/restart logic
      tests/
  sidecar/                                 # NEW: Python sidecar package
    pyproject.toml
    server.py                              # JSON-RPC stdio server entry
    dispatcher.py                          # Method routing
    prompt_builder.py                      # Guided generation/regeneration prompt builder
    gemini_client.py                       # Google Gemini API wrapper
    generators/
      __init__.py
      carousel.py                          # Extracted from generate_carousel.py
      video.py                             # Extracted from render_from_spec.py (gen)
      thread.py                            # Extracted from generate_thread.py
    renderers/
      __init__.py
      carousel_renderer.py                 # Extracted from render_instagram_carousel.py
      video_renderer.py                    # Extracted from render_from_spec.py (render)
    thohago/                               # Symlink or copy of src/thohago/*.py
      models.py
      interview_engine.py
      anthropic_live.py
      groq_live.py
      openai_live.py
      heuristics.py
      content.py
      instagram_content.py
      threads_content.py
      artifacts.py
      config.py                            # Modified for sidecar config injection
      publish.py
      instagram_publish.py
      threads_publish.py
  config/
    plugins.config.ts
  migrations/
    001_thohago_core.sql
  assets/
    font/                                  # Cafe24 fonts (from existing repo)
```

---

## 15. Implementation Phases

### Phase A: Foundation (Weeks 1-2)

Goal: Electron app boots, sidecar communicates, onboarding works.

Tasks:
1. Fork electron-backend-starter, remove unused writing-panel/naver plugins
2. Implement packages/python-sidecar/ (JSON-RPC stdio client + process manager)
3. Implement sidecar/server.py + dispatcher.py (Python JSON-RPC server with system.ping)
4. Copy existing Thohago Python modules into sidecar/thohago/
5. Implement thohago-onboarding plugin (API key wizard, project folder, dependency check)
6. Implement thohago-sidecar plugin (spawn/health-check/restart)
7. Create SQLite migration 001_thohago_core.sql
8. Verify: app boots -> onboarding -> sidecar connects -> dashboard shown

### Phase B: Project + Interview (Weeks 3-4)

Goal: User can create project, upload media, rank photos, and complete 3-turn interview.

Tasks:
1. Implement thohago-project plugin (CRUD, media upload, dashboard)
2. Implement Dashboard page with ProjectCard grid
3. Implement ProjectNew page with profile form + folder picker
4. Implement MediaGallery component with drag-drop upload
5. Add photo priority ordering + representative photo selection
6. Wire sidecar interview.build_preflight for media analysis
7. Implement thohago-interview plugin (turn state machine)
8. Implement Interview page with ChatBubble + TextInput
9. Implement VoiceRecorder component (MediaRecorder + waveform)
10. Wire sidecar interview.transcribe for audio to text
11. Wire sidecar interview.plan_turn for Q2/Q3 generation
12. Verify: create project -> upload photos -> rank media -> complete 3-turn interview

### Phase C: Content Generation (Weeks 5-6)

Goal: All 4 content types generated from interview data and a structured generation profile.

Tasks:
1. Extract generator logic from generate_carousel.py to sidecar/generators/carousel.py
2. Extract generator logic from render_from_spec.py to sidecar/generators/video.py
3. Extract generator logic from generate_thread.py to sidecar/generators/thread.py
4. Implement sidecar/gemini_client.py (Gemini as primary AI provider)
5. Implement GenerationSetup page + GenerationProfileForm
6. Persist generation_profile on the project record
7. Wire sidecar content.compose_blog using generation_profile
8. Wire sidecar content.generate_carousel_spec using generation_profile
9. Wire sidecar content.generate_video_spec using generation_profile
10. Wire sidecar content.generate_thread using generation_profile
11. Extract carousel renderer to sidecar/renderers/carousel_renderer.py
12. Extract video renderer to sidecar/renderers/video_renderer.py
13. Wire sidecar render.carousel and render.video with progress notifications
14. Implement generation progress UI in ProjectView
15. Verify: interview complete -> configure profile -> generate all 4 -> previews shown

### Phase D: Review + Regeneration (Weeks 7-8)

Goal: User can review each content type and improve it via bounded regeneration controls.

Tasks:
1. Implement sidecar/prompt_builder.py (generation/regeneration prompt builder + validator)
2. Implement RegenerationToolbar, GenerationRunList, GenerationSummaryCard
3. Implement BlogReview page (HTML preview + regeneration controls)
4. Implement BlogPreview component (sandboxed iframe)
5. Implement CarouselReview page (slide gallery + regeneration controls)
6. Implement CarouselSlideGallery + CarouselSlideDetail components
7. Implement VideoReview page (video player + timeline + regeneration controls)
8. Implement VideoPlayer + VideoTimeline components
9. Implement ThreadReview page (3-card preview + regeneration controls)
10. Wire regenerate -> full spec rebuild -> re-render -> preview update loop for all 4 types
11. Store generation_runs history + latest successful spec per content type
12. Verify: regenerate / tone shift / shorter / longer / premium / CTA boost works for all 4 types

### Phase E: Publishing + Polish (Weeks 9-10)

Goal: Publish to all platforms, polish UX, prepare for distribution.

Tasks:
1. Implement thohago-publisher plugin
2. Implement Publish page with platform cards + credential forms
3. Wire sidecar publish methods (Naver, Instagram, Threads)
4. Implement publish progress UI with result URLs
5. Add error handling throughout (network failures, AI rate limits, render errors)
6. Add Korean i18n for all UI strings
7. Implement Settings page (API key management, defaults)
8. Add keyboard shortcuts (Ctrl+Enter to generate/regenerate, Ctrl+S to save profile)
9. Bundle Python sidecar with PyInstaller for distribution
10. Bundle FFmpeg binary for distribution
11. Test on Windows 11, package with electron-builder
12. Verify: end-to-end from project creation to published content

---

## 16. Risk and Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| Prompt quality stalls at 70-80% only for some industries | High | Build per-industry prompt templates, keep a regression set of real projects, and tune generation_profile defaults with user feedback. |
| Python sidecar bundling complexity | High | Phase A: use system Python. Phase E: bundle with PyInstaller. Fallback: manual Python install instructions. |
| FFmpeg not installed on user machine | High | Bundle FFmpeg binary with app. For MVP, require user installation with clear instructions. |
| Gemini free tier rate limits | Medium | Exponential backoff + retry. Fall back to Anthropic/OpenAI. Cache successful generations. |
| AI returns invalid JSON spec | Medium | Strict schema validation after every AI call. Retry with fix-this-JSON prompt up to 2 times. Fall back to previous successful run. |
| No fine-grained editor in MVP frustrates users | Medium | Offer fast bounded regeneration actions, preserve previous successful runs, and make pre-generation controls clear and powerful. |
| Video rendering slow (30-90 sec) | Medium | Progress bar with segment-level updates. Allow reviewing or regenerating other content while video renders. |
| Large media files (4K photos, long videos) | Medium | Thumbnail generation on import. PIL resize before rendering. FFmpeg pre-transcode. |
| Voice recording quality varies | Low | Text input alternative. Whisper handles noise well. Show transcription for confirmation. |
| Google Cloud TTS requires service account | Medium | MVP: use gTTS (free, no auth). Later: guide user through GCP service account setup. |
| Windows path issues (backslashes) | Low | Use pathlib.Path consistently in Python. Normalize paths at sidecar boundary. |
| Electron app size (Python + FFmpeg) | Medium | Lazy-download Python/FFmpeg on first run. Show download progress in onboarding. |

---

## 17. Success Criteria

### MVP (Phase A-D complete)

- User can install and launch the app on Windows 11
- Onboarding wizard collects API keys and validates them
- User can create a project with business profile
- User can upload 3-10 photos and 0-2 videos
- User can complete 3-turn interview (voice or text)
- User can configure structured generation controls before the first run
- System generates all 4 content types (blog, carousel, video, thread)
- User can preview all generated content in the app
- User can regenerate each content type with bounded actions (tone, shorter/longer, premium, CTA boost)

### Full Product (Phase E complete)

- User can publish to Naver Blog
- User can publish carousel to Instagram
- User can publish Reels to Instagram
- User can publish 3-post chain to Threads
- All data stored locally (no cloud dependency except AI APIs)
- App works with Gemini free tier as sole AI provider
- End-to-end flow (create -> interview -> generate -> review/regenerate -> publish) under 15 minutes

### Quality Metrics

- Sidecar crash recovery: auto-restart within 5 seconds
- Carousel rendering: under 5 seconds for 5 slides
- Video rendering: under 120 seconds for 24-second video
- Non-video regeneration request to updated preview: under 15 seconds
- App startup to ready: under 8 seconds (sidecar connected)
