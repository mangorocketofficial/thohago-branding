"""Source-First shorts renderer (v3).

Pipeline:
1. Gather all source info (photos, videos, interview transcripts)
2. Claude writes ONE free narrative (no beat structure given)
3. Claude matches each sentence to the best source(s)
4. TTS at natural speed → sentence durations drive timeline
5. Render: segments → overlays → subtitles → voiceover → final
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from google.cloud import texttospeech

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass

PROJ_ROOT = Path(__file__).resolve().parents[4]
INTERVIEW_PATH = PROJ_ROOT / "client" / "sisun8082" / "2026_03_27" / "interview" / "interview_transcripts.md"
PREFLIGHT_PATH = PROJ_ROOT / "runs" / "sisun8082" / "live_20260329T011849-20260329T011849Z" / "generated" / "media_preflight.json"
OUT_DIR = Path(__file__).resolve().parent / "render_output"
OUT_VIDEO = OUT_DIR / "shorts_render.mp4"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

FONT_PATH = PROJ_ROOT / "assets" / "font" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0.ttf"
SUBTITLE_FONT_PATH = PROJ_ROOT / "assets" / "font" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf"
TEXT_COLOR = "#FFEE59"

TTS_VOICE_NAME = "ko-KR-Chirp3-HD-Achernar"
TTS_SPEAKING_RATE = 1.1

PHOTO_MAP = {
    "photo_01": "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482.jpg",
    "photo_02": "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_01.jpg",
    "photo_03": "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_02.jpg",
    "photo_04": "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_03.jpg",
    "photo_05": "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_04.jpg",
}
VIDEO_MAP = {
    "video_01": {"path": "client/sisun8082/2026_03_27/video/KakaoTalk_20260327_121601750.mp4", "duration": 13.3, "orientation": "vertical"},
    "video_02": {"path": "KakaoTalk_20260329_151012818.mp4", "duration": 7.0, "orientation": "near_vertical", "pan": ""},
}


def resolve_path(rel: str) -> Path:
    p = PROJ_ROOT / rel
    if p.exists():
        return p
    raise FileNotFoundError(f"Source not found: {p}")


def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip())


# ==================== PHASE 1: NARRATIVE SCRIPT ====================

def generate_narrative_and_matching(preflight: dict, interview_text: str) -> dict:
    """Ask Claude to write a free narrative and match sources to each sentence."""
    load_dotenv(PROJ_ROOT / ".env")
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or anthropic is None:
        raise RuntimeError("CLAUDE_API_KEY required")

    # Build source descriptions
    photo_descriptions = []
    for photo in preflight.get("photos", []):
        mid = photo["media_id"]
        analysis = photo.get("preflight_analysis", {})
        photo_descriptions.append(
            f"  - {mid}: {analysis.get('scene', '')}, 디테일: {', '.join(analysis.get('details', []))}, 분위기: {analysis.get('mood', '')}"
        )

    video_descriptions = []
    for vid_id, vid_info in VIDEO_MAP.items():
        video_descriptions.append(
            f"  - {vid_id}: {vid_info['duration']:.1f}초, {vid_info['orientation']} 영상"
        )

    prompt = f"""당신은 숏폼 영상 내레이션 작가입니다.

아래 소스들을 보고, 하나의 자연스러운 이야기를 만들어주세요.

## 사용 가능한 소스

### 사진 (정지 이미지)
{chr(10).join(photo_descriptions)}

### 영상
{chr(10).join(video_descriptions)}

## 인터뷰 전사 (원본 대화)
{interview_text}

## 배경 정보
- 샵 이름: 시선을 즐기다
- 위치: 부산 서면 핫플레이스 카페거리 한복판
- 상황: 필리핀 관광객 5명이 한국 오기 전부터 예약하고 방문해서 헤드스파를 받은 경험

## 작성 지침

하나의 이야기를 쓰세요. 누군가에게 "이런 일이 있었어"라고 자연스럽게 말해주는 것처럼요.

- 전체 5~6문장 (절대 7문장 이상 쓰지 마세요)
- 각 문장은 20~35자 이내로 짧게
- 소스에 보이는 실제 장면들을 자연스럽게 녹여내세요
- 인터뷰에서 나온 실제 표현("K-뷰티는 최고다", "너무 시원했다" 등)을 살리세요
- "헤어 관리"라는 표현을 사용하세요 ("머리를 감아주는" 금지)
- 마지막 문장은 '시선을 즐기다'를 자연스럽게 포함한 클로징
- 편안한 해요체
- 전체를 소리내어 읽었을 때 20~25초 분량 (매우 중요!)

그리고 각 문장마다 **화면에 보여줄 소스**를 지정해주세요.
한 문장에 소스 1~2개. 소스 ID는 반드시 photo_01~photo_05, video_01~video_02 형식으로.

## 출력 형식 (JSON만, 다른 텍스트 없이)

```json
{{
  "full_narrative": "전체 이야기 (하나의 연결된 텍스트)",
  "sentences": [
    {{
      "index": 1,
      "text": "첫 번째 문장",
      "sources": ["video_02", "photo_01"],
      "overlay_text": "화면에 짧게 표시할 핵심 (8자 이내)"
    }},
    {{
      "index": 2,
      "text": "두 번째 문장",
      "sources": ["photo_02"],
      "overlay_text": "핵심 텍스트"
    }}
  ]
}}
```"""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


# ==================== PHASE 2: TTS ====================

def synthesize_google_tts(text: str, output_mp3: Path) -> None:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="ko-KR", name=TTS_VOICE_NAME)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=TTS_SPEAKING_RATE)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    output_mp3.write_bytes(response.audio_content)


def generate_all_tts(sentences: list[dict], voice_dir: Path) -> list[dict]:
    voice_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for sent in sentences:
        idx = sent["index"]
        text = sent["text"]
        mp3 = voice_dir / f"s{idx:02d}.mp3"
        wav = voice_dir / f"s{idx:02d}.wav"
        print(f"    TTS s{idx:02d}: {text[:50]}...")
        synthesize_google_tts(text, mp3)
        subprocess.run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "44100", "-ac", "1", str(wav)],
                       check=True, capture_output=True)
        dur = get_audio_duration(wav)
        results.append({**sent, "wav_path": wav, "tts_duration_sec": round(dur, 2)})
        print(f"           -> {dur:.2f}s")
    return results


# ==================== PHASE 3: BUILD TIMELINE ====================

def normalize_source_id(source_id: str) -> str:
    """Normalize source IDs like 'photo_1' -> 'photo_01'."""
    for prefix in ("photo_", "video_"):
        if source_id.startswith(prefix):
            num = source_id[len(prefix):]
            return f"{prefix}{int(num):02d}"
    return source_id


def build_timeline_from_sentences(sentences: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Build clips, overlays, subtitles from sentence-level source matching."""
    # Normalize all source IDs
    all_known = set(PHOTO_MAP.keys()) | set(VIDEO_MAP.keys())
    for sent in sentences:
        sent["sources"] = [normalize_source_id(s) for s in sent.get("sources", [])]
        sent["sources"] = [s for s in sent["sources"] if s in all_known]
        if not sent["sources"]:
            sent["sources"] = ["photo_01"]

    clips = []
    overlays = []
    subtitles = []
    clip_idx = 1
    timeline_pos = 0.0

    for sent in sentences:
        idx = sent["index"]
        dur = sent["tts_duration_sec"]
        sources = sent.get("sources", [])
        overlay_text = sent.get("overlay_text", "")

        if not sources:
            sources = ["photo_01"]  # fallback

        # Distribute duration across sources
        per_source_dur = round(dur / len(sources), 3)

        for si, source_id in enumerate(sources):
            is_photo = source_id.startswith("photo")
            clip_dur = per_source_dur
            # Last source in sentence gets remaining time to avoid rounding gaps
            if si == len(sources) - 1:
                clip_dur = round(dur - per_source_dur * si, 3)

            clip = {
                "clip_id": f"c{clip_idx:02d}",
                "sentence_index": idx,
                "asset_type": "photo" if is_photo else "video",
                "asset_id": source_id,
                "start_sec": round(timeline_pos, 3),
                "end_sec": round(timeline_pos + clip_dur, 3),
                "duration_sec": clip_dur,
            }

            if is_photo:
                clip["processing"] = {"method": "ken_burns", "scale_from": 1.0, "scale_to": 1.06}
            else:
                vid_info = VIDEO_MAP.get(source_id, {})
                ori = vid_info.get("orientation", "vertical")
                if ori == "horizontal":
                    method = "horizontal_to_vertical"
                elif ori == "near_vertical":
                    method = "near_vertical"
                else:
                    method = "native_vertical"
                proc = {"method": method}
                if vid_info.get("pan"):
                    proc["pan"] = vid_info["pan"]
                clip["processing"] = proc
                # Simple trim: use first available portion
                clip["source_in_sec"] = 0
                clip["source_out_sec"] = min(clip_dur, vid_info.get("duration", clip_dur))

            clips.append(clip)
            timeline_pos += clip_dur
            clip_idx += 1

        # Overlay
        if overlay_text:
            overlays.append({
                "text_id": f"t{idx:02d}",
                "text": overlay_text,
                "start_sec": round(sent["_start_sec"] + 0.2, 2),
                "end_sec": round(sent["_start_sec"] + min(dur * 0.8, dur - 0.3), 2),
                "kind": "hook" if idx == 1 else ("cta" if idx == len(sentences) else "supporting"),
                "position": "center" if idx <= 1 else "bottom_center",
            })

        # Subtitle
        subtitles.append({
            "index": idx,
            "text": sent["text"],
            "start_sec": round(sent["_start_sec"], 2),
            "end_sec": round(sent["_start_sec"] + dur, 2),
        })

    return clips, overlays, subtitles


# ==================== PHASE 4: RENDER ====================

def render_photo_segment(clip: dict, out_path: Path) -> None:
    src = resolve_path(PHOTO_MAP[clip["asset_id"]])
    dur = clip["duration_sec"]
    proc = clip.get("processing", {})
    sf, st = proc.get("scale_from", 1.0), proc.get("scale_to", 1.0)
    nf = max(int(dur * FPS), 1)
    z = f"{sf}+({st}-{sf})*on/{nf}"
    # Ken Burns + warm color grading + vignette
    vf = (
        f"scale=8000:-1,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={nf}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"setsar=1,"
        f"eq=saturation=1.1:brightness=0.03,"
        f"colorbalance=rs=0.04:gs=0.01:bs=-0.03:rm=0.03:gm=0.0:bm=-0.02,"
        f"vignette=PI/4"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(src),
        "-vf", vf,
        "-t", str(dur), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(out_path),
    ], check=True, capture_output=True)


def render_video_segment(clip: dict, out_path: Path) -> None:
    vid_info = VIDEO_MAP[clip["asset_id"]]
    src = resolve_path(vid_info["path"])
    dur = clip["duration_sec"]
    si = clip.get("source_in_sec", 0)
    so = clip.get("source_out_sec", si + dur)
    proc = clip.get("processing", {})
    orientation = proc.get("method", vid_info.get("orientation", ""))

    if orientation == "horizontal_to_vertical":
        pan_dir = proc.get("pan", "")
        if pan_dir == "left_to_right":
            vf = (
                f"scale=-1:{HEIGHT},"
                f"crop={WIDTH}:{HEIGHT}:'(iw-{WIDTH})*t/{dur}':0,"
                f"setsar=1"
            )
        elif pan_dir == "right_to_left":
            vf = (
                f"scale=-1:{HEIGHT},"
                f"crop={WIDTH}:{HEIGHT}:'(iw-{WIDTH})*(1-t/{dur})':0,"
                f"setsar=1"
            )
        else:
            vf = f"scale=-1:{HEIGHT},crop={WIDTH}:{HEIGHT}:(iw-{WIDTH})/2:0,setsar=1"
    elif orientation == "near_vertical":
        # 3:4 or similar aspect — blur background + centered original
        # [0:v] scaled+blurred as background, [0:v] scaled to fit as foreground
        vf = (
            f"split[bg][fg];"
            f"[bg]scale={WIDTH}:{HEIGHT},boxblur=20:5,setsar=1[bgout];"
            f"[fg]scale={WIDTH}:-1,setsar=1[fgout];"
            f"[bgout][fgout]overlay=0:(H-h)/2"
        )
        # Use filter_complex instead of -vf for split
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(si), "-to", str(so), "-i", str(src),
            "-filter_complex", vf,
            "-t", str(dur), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-an", "-pix_fmt", "yuv420p", str(out_path),
        ], check=True, capture_output=True)
        return
    else:
        vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(si), "-to", str(so), "-i", str(src),
        "-vf", vf, "-t", str(dur), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an", "-pix_fmt", "yuv420p", str(out_path),
    ], check=True, capture_output=True)


def render_overlay_png(text: str, kind: str, position: str, out_path: Path) -> None:
    from PIL import ImageFilter

    fontsize = 100 if kind == "hook" else (80 if kind == "cta" else 72)
    font = ImageFont.truetype(str(FONT_PATH), fontsize)
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = text.split("\n")
    bbs = [draw.textbbox((0, 0), l, font=font) for l in lines]
    lhs = [b[3] - b[1] for b in bbs]
    lws = [b[2] - b[0] for b in bbs]
    th = sum(lhs) + (len(lines) - 1) * 16
    ys = HEIGHT - int(HEIGHT * 0.28) - th if position == "bottom_center" else (HEIGHT - th) // 2
    color = tuple(int(TEXT_COLOR.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # Layer 1: Soft shadow (blurred black text offset down)
    shadow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    y = ys + 4  # offset down
    for i, line in enumerate(lines):
        x = (WIDTH - lws[i]) // 2 + 2  # offset right
        shadow_draw.text((x, y), line, font=font, fill=(0, 0, 0, 180))
        y += lhs[i] + 16
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img, shadow_layer)

    # Layer 2: Glow (blurred colored text)
    glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    y = ys
    for i, line in enumerate(lines):
        x = (WIDTH - lws[i]) // 2
        glow_draw.text((x, y), line, font=font, fill=(*color, 100))
        y += lhs[i] + 16
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=12))
    img = Image.alpha_composite(img, glow_layer)

    # Layer 3: Crisp main text with thin outline
    main_draw = ImageDraw.Draw(img)
    y = ys
    for i, line in enumerate(lines):
        x = (WIDTH - lws[i]) // 2
        # Thin outline
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx*dx + dy*dy <= 4:
                    main_draw.text((x+dx, y+dy), line, font=font, fill=(0, 0, 0, 160))
        main_draw.text((x, y), line, font=font, fill=(*color, 255))
        y += lhs[i] + 16

    img.save(str(out_path), "PNG")


def split_at_midpoint(text: str) -> list[str]:
    """Split text into 2 lines at the space closest to the midpoint."""
    if " " not in text:
        return [text]
    mid = len(text) // 2
    # Find the closest space to the midpoint
    left = text.rfind(" ", 0, mid + 1)
    right = text.find(" ", mid)
    if left == -1:
        split_pos = right
    elif right == -1:
        split_pos = left
    else:
        split_pos = left if (mid - left) <= (right - mid) else right
    return [text[:split_pos].strip(), text[split_pos:].strip()]


def render_subtitle_png(text: str, out_path: Path) -> None:
    fontsize = 44
    font = ImageFont.truetype(str(SUBTITLE_FONT_PATH), fontsize)
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Check if single line fits
    bb = draw.textbbox((0, 0), text, font=font)
    if bb[2] - bb[0] <= WIDTH - 120:
        wrapped = [text]
    else:
        wrapped = split_at_midpoint(text)
    lhs = [draw.textbbox((0, 0), l, font=font) for l in wrapped]
    th = sum(b[3] - b[1] for b in lhs) + (len(wrapped) - 1) * 8
    pad = 16
    bt = HEIGHT - int(HEIGHT * 0.12) - th - pad
    bb2 = HEIGHT - int(HEIGHT * 0.12) + pad
    bg = Image.new("RGBA", (WIDTH, bb2 - bt), (0, 0, 0, 160))
    img.paste(bg, (0, bt), bg)
    y = bt + pad
    for i, line in enumerate(wrapped):
        lw = lhs[i][2] - lhs[i][0]
        draw.text(((WIDTH - lw) // 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += lhs[i][3] - lhs[i][1] + 8
    img.save(str(out_path), "PNG")


def render_sticker_png(emoji_char: str, x: int, y: int, size: int, out_path: Path) -> None:
    """Render a single emoji as a transparent PNG at specified coordinates."""
    # Try platform emoji fonts
    emoji_font = None
    emoji_font_candidates = [
        Path(r"C:\Windows\Fonts\seguiemj.ttf"),  # Windows Segoe UI Emoji
        Path(r"C:\Windows\Fonts\segmdl2.ttf"),
    ]
    for fp in emoji_font_candidates:
        if fp.exists():
            try:
                emoji_font = ImageFont.truetype(str(fp), size)
                break
            except Exception:
                continue

    if emoji_font is None:
        # Fallback: use default font
        emoji_font = ImageFont.truetype(str(FONT_PATH), size)

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Center the emoji on the specified coordinate
    bb = draw.textbbox((0, 0), emoji_char, font=emoji_font)
    ew, eh = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((x - ew // 2, y - eh // 2), emoji_char, font=emoji_font, fill=(255, 255, 255, 255))

    img.save(str(out_path), "PNG")


def load_sticker_plan() -> list[dict]:
    """Load sticker placement plan if it exists."""
    plan_path = OUT_DIR / "sticker_plan.json"
    if plan_path.exists():
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        return data.get("stickers", [])
    return []


def build_voiceover_track(sentences: list[dict], voice_dir: Path, total_dur: float) -> Path:
    silence = voice_dir / "silence_base.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(total_dur), str(silence),
    ], check=True, capture_output=True)
    combined = silence
    for i, sent in enumerate(sentences):
        out = voice_dir / f"combined_{i}.wav"
        delay = int(sent["_start_sec"] * 1000)
        subprocess.run([
            "ffmpeg", "-y", "-i", str(combined), "-i", str(sent["wav_path"]),
            "-filter_complex", f"[1:a]adelay={delay}|{delay}[d];[0:a][d]amix=inputs=2:duration=first:normalize=0",
            "-ar", "44100", "-ac", "1", str(out),
        ], check=True, capture_output=True)
        combined = out
    return combined


# ==================== MAIN ====================

def main() -> int:
    rerender = "--rerender" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    script_path = OUT_DIR / "narrative_script.json"

    if rerender and script_path.exists():
        # ---- RERENDER: Skip script generation, use existing ----
        print("Phase 1: Loading existing narrative_script.json (--rerender mode)")
        script = json.loads(script_path.read_text(encoding="utf-8"))
    else:
        # ---- PHASE 1: Generate narrative + source matching ----
        print("Phase 1: Generating narrative script via Claude...")
        preflight = {}
        if PREFLIGHT_PATH.exists():
            preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
        interview_text = INTERVIEW_PATH.read_text(encoding="utf-8") if INTERVIEW_PATH.exists() else ""
        script = generate_narrative_and_matching(preflight, interview_text)
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"    Narrative: {script['full_narrative'][:80]}...")
    for s in script["sentences"]:
        print(f"    s{s['index']:02d}: {s['text'][:50]}... -> {s['sources']}")

    # ---- PHASE 2: TTS for each sentence ----
    print("\nPhase 2: Generating TTS (Google Cloud, {:.1f}x)...".format(TTS_SPEAKING_RATE))
    voice_dir = OUT_DIR / "voice"
    sentences = generate_all_tts(script["sentences"], voice_dir)

    # Calculate timeline positions
    pos = 0.0
    for sent in sentences:
        sent["_start_sec"] = round(pos, 3)
        pos += sent["tts_duration_sec"]
    total_tts = round(pos, 2)

    print(f"\n  Total TTS duration: {total_tts:.2f}s")

    # ---- PHASE 3: Build timeline ----
    print("\nPhase 3: Building timeline...")
    clips, overlays, subtitles = build_timeline_from_sentences(sentences)
    print(f"    {len(clips)} clips, {len(overlays)} overlays, {len(subtitles)} subtitles")

    # Save spec
    with open(OUT_DIR / "generated_render_spec.json", "w", encoding="utf-8") as f:
        json.dump({
            "pipeline_mode": "source_first_v3",
            "full_narrative": script["full_narrative"],
            "total_duration_sec": total_tts,
            "sentences": [{
                "index": s["index"], "text": s["text"],
                "sources": s["sources"], "tts_duration_sec": s["tts_duration_sec"],
                "start_sec": s["_start_sec"],
            } for s in sentences],
            "timeline": clips, "text_overlays": overlays, "subtitles": subtitles,
        }, f, ensure_ascii=False, indent=2)

    # ---- PHASE 4: Render segments ----
    print("\nPhase 4: Rendering clip segments...")
    segments_dir = OUT_DIR / "segments"
    segments_dir.mkdir(exist_ok=True)
    segment_paths = []
    for clip in clips:
        seg = segments_dir / f"{clip['clip_id']}.mp4"
        print(f"    {clip['clip_id']} ({clip['asset_type']}, {clip['duration_sec']:.2f}s) -> {clip['asset_id']}")
        if clip["asset_type"] == "photo":
            render_photo_segment(clip, seg)
        else:
            render_video_segment(clip, seg)
        segment_paths.append(seg)

    # Concatenate (hard cut)
    concat_raw = OUT_DIR / "concat_raw.mp4"
    concat_list = segments_dir / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in segment_paths:
            f.write(f"file '{p.as_posix()}'\n")
    print("    Concatenating...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(concat_raw),
    ], check=True, capture_output=True)

    # Ensure video >= TTS duration
    video_dur = get_audio_duration(concat_raw)
    if video_dur < total_tts - 0.1:
        pad = total_tts - video_dur
        print(f"    Padding video {video_dur:.1f}s -> {total_tts:.1f}s (+{pad:.1f}s freeze)")
        padded = OUT_DIR / "concat_padded.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(concat_raw),
            "-vf", f"tpad=stop_mode=clone:stop_duration={pad}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(padded),
        ], check=True, capture_output=True)
        concat_raw.unlink(missing_ok=True)
        concat_raw = padded

    # ---- PHASE 5: Composite overlays ----
    print("\nPhase 5: Compositing overlays...")
    overlay_dir = OUT_DIR / "overlay_pngs"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    subtitle_dir = OUT_DIR / "subtitles"
    subtitle_dir.mkdir(parents=True, exist_ok=True)

    all_items = []

    # Stickers (from sticker_plan.json)
    sticker_plan = load_sticker_plan()
    if sticker_plan:
        sticker_dir = OUT_DIR / "sticker_pngs"
        sticker_dir.mkdir(parents=True, exist_ok=True)
        # Map photo_id to clip timing
        photo_clip_times = {}
        for clip in clips:
            if clip["asset_type"] == "photo":
                pid = clip["asset_id"]
                if pid not in photo_clip_times:
                    photo_clip_times[pid] = {"start": clip["start_sec"], "end": clip["end_sec"]}
                else:
                    # Extend if same photo used in multiple clips
                    photo_clip_times[pid]["end"] = max(photo_clip_times[pid]["end"], clip["end_sec"])

        for si, sticker in enumerate(sticker_plan):
            pid = normalize_source_id(sticker["photo_id"])
            if pid not in photo_clip_times:
                continue
            timing = photo_clip_times[pid]
            png = sticker_dir / f"sticker_{si:02d}.png"
            render_sticker_png(sticker["emoji"], sticker["x"], sticker["y"], sticker.get("size", 80), png)
            all_items.append({"start_sec": timing["start"], "end_sec": timing["end"], "png": png})
        print(f"    {len([s for s in sticker_plan if normalize_source_id(s['photo_id']) in photo_clip_times])} stickers loaded")

    # Text overlays
    for ov in overlays:
        png = overlay_dir / f"{ov['text_id']}.png"
        render_overlay_png(ov["text"], ov["kind"], ov["position"], png)
        all_items.append({"start_sec": ov["start_sec"], "end_sec": ov["end_sec"], "png": png})

    # Subtitles
    for sub in subtitles:
        png = subtitle_dir / f"sub_s{sub['index']:02d}.png"
        render_subtitle_png(sub["text"], png)
        all_items.append({"start_sec": sub["start_sec"], "end_sec": sub["end_sec"], "png": png})

    if all_items:
        inputs = ["-i", str(concat_raw)]
        for it in all_items:
            inputs.extend(["-i", str(it["png"])])
        parts = []
        prev = "0:v"
        for idx, it in enumerate(all_items):
            out = f"v{idx}"
            parts.append(f"[{prev}][{idx+1}:v]overlay=0:0:enable='between(t,{it['start_sec']},{it['end_sec']})'[{out}]")
            prev = out
        vwo = OUT_DIR / "with_overlays.mp4"
        subprocess.run([
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(parts),
            "-map", f"[{prev}]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(vwo),
        ], check=True, capture_output=True)
    else:
        vwo = concat_raw

    # ---- PHASE 6: Mux voiceover ----
    print("\nPhase 6: Muxing voiceover...")
    voice_track = build_voiceover_track(sentences, voice_dir, total_tts)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(vwo), "-i", str(voice_track),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0", str(OUT_VIDEO),
    ], check=True, capture_output=True)

    concat_raw.unlink(missing_ok=True)
    if vwo != concat_raw:
        vwo.unlink(missing_ok=True)

    actual_dur = get_audio_duration(OUT_VIDEO)
    print(f"\n{'='*50}")
    print(f"  Output: {OUT_VIDEO}")
    print(f"  Duration: {actual_dur:.1f}s")
    print(f"  TTS: Google Cloud ({TTS_VOICE_NAME}, {TTS_SPEAKING_RATE}x)")
    print(f"  Script: Claude free narrative ({len(sentences)} sentences)")
    print(f"  Clips: {len(clips)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
