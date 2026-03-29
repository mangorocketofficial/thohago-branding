from __future__ import annotations

import json
import math
import re
import subprocess
import unicodedata
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


CANVAS_W = 1080
CANVAS_H = 1920
FPS = 30
PROJECT_ROOT = Path(__file__).resolve().parents[4]
VIDEO_DIR = Path(__file__).resolve().parent
IMAGE_DIR = VIDEO_DIR.parent / "images"
FONT_ROOT = PROJECT_ROOT / "assets" / "font"

FONT_CANDIDATES = {
    "Pretendard-Bold": [
        Path(r"C:\Windows\Fonts\Pretendard-Bold.ttf"),
        Path(r"C:\Windows\Fonts\malgunbd.ttf"),
        Path(r"C:\Windows\Fonts\malgun.ttf"),
    ],
    "Pretendard-SemiBold": [
        Path(r"C:\Windows\Fonts\Pretendard-SemiBold.ttf"),
        Path(r"C:\Windows\Fonts\malgunbd.ttf"),
        Path(r"C:\Windows\Fonts\malgun.ttf"),
    ],
    "Pretendard-Medium": [
        Path(r"C:\Windows\Fonts\Pretendard-Medium.ttf"),
        Path(r"C:\Windows\Fonts\malgun.ttf"),
        Path(r"C:\Windows\Fonts\malgunbd.ttf"),
    ],
    "Cafe24Dangdanghae-v2.0": [
        FONT_ROOT / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0.ttf",
        FONT_ROOT / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0.otf",
    ],
    "Cafe24Ohsquare-v2.0": [
        FONT_ROOT / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf",
        FONT_ROOT / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.otf",
    ],
    "Cafe24Moyamoya-Regular-v1.0": [
        FONT_ROOT / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-Regular-v1.0.ttf",
        FONT_ROOT / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-Regular-v1.0.otf",
    ],
}


def load_spec(spec_path: Path) -> dict:
    return json.loads(spec_path.read_text(encoding="utf-8"))


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def resolve_source_path(file_name: str) -> Path:
    direct = Path(file_name)
    if direct.exists():
        return direct

    candidates = [
        VIDEO_DIR / file_name,
        IMAGE_DIR / file_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    for base in (VIDEO_DIR, IMAGE_DIR):
        matches = list(base.rglob(file_name))
        if matches:
            return matches[0]

    raise FileNotFoundError(f"Missing source file: {file_name}")


def resolve_font(font_name: str | None) -> Path:
    if not font_name:
        font_name = "Cafe24Ohsquare-v2.0"

    direct_path = Path(font_name)
    if direct_path.exists():
        return direct_path

    for candidate in FONT_CANDIDATES.get(font_name, []):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"No usable font found for {font_name}")


def parse_rgba(value: str | None) -> tuple[int, int, int, int] | None:
    if not value or value.lower() == "none":
        return None

    rgba_match = re.fullmatch(
        r"rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([0-9.]+)\s*\)",
        value,
    )
    if rgba_match:
        r, g, b, a = rgba_match.groups()
        alpha = max(0, min(255, round(float(a) * 255)))
        return int(r), int(g), int(b), alpha

    if value.startswith("#") and len(value) == 7:
        return (
            int(value[1:3], 16),
            int(value[3:5], 16),
            int(value[5:7], 16),
            255,
        )

    raise ValueError(f"Unsupported color format: {value}")


def strip_unreliable_emoji(text: str) -> str:
    cleaned: list[str] = []
    for char in text:
        if ord(char) >= 0x1F000:
            continue
        if unicodedata.category(char) == "So":
            continue
        cleaned.append(char)

    compact = "".join(cleaned)
    compact = re.sub(r"[ \t]{2,}", " ", compact)
    compact = re.sub(r" *\n *", "\n", compact)
    return compact.strip()


def even_int(value: float) -> int:
    rounded = max(2, int(round(value)))
    if rounded % 2:
        rounded += 1
    return rounded


def render_overlay_image(overlay: dict, output_path: Path) -> dict:
    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    lines: list[dict] = []

    for text_key, style_key in (("text_line_1", "line_1"), ("text_line_2", "line_2")):
        raw_text = overlay.get(text_key)
        style = overlay["style"].get(style_key)
        if not raw_text or not style:
            continue

        text = strip_unreliable_emoji(raw_text)
        font_path = resolve_font(style.get("font") or "Cafe24Ohsquare-v2.0")
        font_size = int(style["font_size"])
        stroke_width = int(round(style.get("stroke_width", 0)))
        font = ImageFont.truetype(str(font_path), font_size)
        fill = parse_rgba(style.get("color", "#FFFFFF")) or (255, 255, 255, 255)
        stroke_fill = parse_rgba(style.get("stroke_color", "#000000")) or (0, 0, 0, 255)

        bbox = probe_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        width = math.ceil(bbox[2] - bbox[0])
        height = math.ceil(bbox[3] - bbox[1])
        lines.append(
            {
                "text": text,
                "font": font,
                "stroke_width": stroke_width,
                "fill": fill,
                "stroke_fill": stroke_fill,
                "bbox": bbox,
                "width": width,
                "height": height,
            }
        )

    if not lines:
        raise ValueError(f"Overlay has no renderable text: {overlay['id']}")

    gap = int(round(overlay.get("position", {}).get("line_gap_px", 40)))
    canvas_w = max(line["width"] for line in lines)
    canvas_h = sum(line["height"] for line in lines) + max(0, len(lines) - 1) * gap

    image = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    current_y = 0
    for idx, line in enumerate(lines):
        x = (canvas_w - line["width"]) / 2.0 - line["bbox"][0]
        y = current_y - line["bbox"][1]
        draw.text(
            (x, y),
            line["text"],
            font=line["font"],
            fill=line["fill"],
            stroke_width=line["stroke_width"],
            stroke_fill=line["stroke_fill"],
        )
        current_y += line["height"]
        if idx < len(lines) - 1:
            current_y += gap

    image.save(output_path)
    return {"path": output_path, "width": canvas_w, "height": canvas_h}


def overlay_position(overlay: dict, meta: dict) -> tuple[int, int]:
    anchor = overlay["position"]["anchor"]
    x = max(0, (CANVAS_W - meta["width"]) // 2)

    if anchor == "center":
        y_center = CANVAS_H * (overlay["position"].get("y_percent", 50) / 100.0)
        y = round(y_center - (meta["height"] / 2))
    elif anchor == "top_center":
        y = round(CANVAS_H * (overlay["position"].get("line_1_y_percent", 10) / 100.0))
    elif anchor == "bottom_center":
        y = round(CANVAS_H * (overlay["position"].get("line_1_y_percent", 75) / 100.0))
    else:
        y = round((CANVAS_H - meta["height"]) / 2)

    y = max(0, min(CANVAS_H - meta["height"], y))
    return x, y


def write_caption(caption_text: str, output_path: Path) -> None:
    output_path.write_text(caption_text.rstrip() + "\n", encoding="utf-8")


def build_ambient_bgm(
    duration_sec: float,
    output_path: Path,
    volume: float,
    fade_in_sec: float,
    fade_out_sec: float,
) -> None:
    sample_rate = 44100
    sample_count = max(1, int(round(duration_sec * sample_rate)))
    t = np.linspace(0.0, duration_sec, sample_count, endpoint=False, dtype=np.float64)
    audio = np.zeros_like(t)
    rng = np.random.default_rng(42)

    segments = [
        (0.0, min(duration_sec, 6.5), [220.0, 277.18, 329.63]),
        (min(duration_sec, 6.5), min(duration_sec, 13.5), [196.0, 246.94, 293.66]),
        (min(duration_sec, 13.5), duration_sec, [207.65, 261.63, 311.13]),
    ]

    for start, end, notes in segments:
        if end <= start:
            continue
        mask = (t >= start) & (t < end)
        tt = t[mask] - start
        seg_len = max(1e-6, end - start)
        seg_env = np.sin(np.pi * np.clip(tt / seg_len, 0.0, 1.0)) ** 0.7

        chord = np.zeros_like(tt)
        for idx, freq in enumerate(notes):
            vibrato = 1.0 + (0.0015 * np.sin((2.0 * math.pi * 0.22 * tt) + idx))
            chord += np.sin((2.0 * math.pi * freq * vibrato * tt) + (idx * 0.6))

        bass = np.sin(2.0 * math.pi * (notes[0] / 2.0) * tt)
        noise = rng.normal(0.0, 1.0, size=tt.shape[0])
        kernel = np.ones(401, dtype=np.float64) / 401.0
        noise = np.convolve(noise, kernel, mode="same")

        audio[mask] += (0.11 * chord / len(notes) + 0.025 * bass + 0.004 * noise) * seg_env

    attack = min(sample_count, int(sample_rate * max(0.0, fade_in_sec)))
    release = min(sample_count, int(sample_rate * max(0.0, fade_out_sec)))
    envelope = np.ones_like(audio)
    if attack > 0:
        envelope[:attack] *= np.linspace(0.0, 1.0, attack)
    if release > 0:
        envelope[-release:] *= np.linspace(1.0, 0.0, release)

    audio *= envelope * float(volume)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = np.clip(audio / max(peak / 0.35, 1.0), -1.0, 1.0)
    stereo = np.column_stack([audio, audio * 0.97])
    pcm = (stereo * 32767.0).astype(np.int16)

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def ffprobe_video(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height:format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    duration = float(data["format"].get("duration") or 0.0)
    return {"width": int(stream["width"]), "height": int(stream["height"]), "duration": duration}


def build_photo_filter_complex(source_path: Path, duration_sec: float, effect: str) -> str:
    with Image.open(source_path) as image:
        orig_w, orig_h = image.size

    fit_ratio = min(CANVAS_W / orig_w, CANVAS_H / orig_h)
    fit_w = even_int(orig_w * fit_ratio)
    fit_h = even_int(orig_h * fit_ratio)

    if effect == "zoom_out":
        start_scale, end_scale = 1.00, 0.94
    elif effect == "zoom_in_slow":
        start_scale, end_scale = 0.94, 1.00
    elif effect == "pan_down":
        start_scale, end_scale = 0.98, 0.98
    else:
        start_scale, end_scale = 0.96, 1.00

    frame_span = max(1, int(round(duration_sec * FPS)) - 1)
    start_w = even_int(fit_w * start_scale)
    end_w = even_int(fit_w * end_scale)
    start_h = even_int(fit_h * start_scale)
    end_h = even_int(fit_h * end_scale)
    width_limited = fit_w >= fit_h

    if effect == "pan_down":
        y_offset = min(36, max(18, (CANVAS_H - start_h) // 10))
        y_expr = (
            f"((H-h)/2) + ({-y_offset} + ({y_offset * 2})*(n/{frame_span}))"
        )
    else:
        y_expr = "(H-h)/2"

    if width_limited:
        fg_scale = (
            "scale="
            f"w='floor(({start_w} + ({end_w - start_w})*(n/{frame_span}))/2)*2':"
            "h=-2:"
            "eval=frame"
        )
    else:
        fg_scale = (
            "scale="
            "w=-2:"
            f"h='floor(({start_h} + ({end_h - start_h})*(n/{frame_span}))/2)*2':"
            "eval=frame"
        )

    return (
        f"[0:v]fps={FPS},"
        f"scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=increase,"
        f"crop={CANVAS_W}:{CANVAS_H},"
        "boxblur=42:2,"
        "eq=brightness=-0.03:saturation=0.90[bg];"
        f"[0:v]fps={FPS},{fg_scale}[fg];"
        f"[bg][fg]overlay=x='(W-w)/2':y='{y_expr}':eval=frame,format=yuv420p[vout]"
    )


def render_photo_segment(source_path: Path, cut: dict, output_path: Path) -> None:
    duration_sec = float(cut["duration_sec"])
    effect = cut["processing"].get("effect", "zoom_in")
    filter_complex = build_photo_filter_complex(source_path, duration_sec, effect)

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(FPS),
        "-t",
        f"{duration_sec:.3f}",
        "-i",
        str(source_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(FPS),
        str(output_path),
    ]
    run_command(cmd)


def render_video_segment(source_path: Path, cut: dict, output_path: Path) -> None:
    duration_sec = float(cut["duration_sec"])
    trim = cut.get("source_trim") or {}
    trim_start = float(trim.get("trim_start_sec", 0.0))
    trim_end = trim.get("trim_end_sec")
    trim_duration = float(trim_end) - trim_start if trim_end is not None else duration_sec
    trim_duration = max(duration_sec, trim_duration)

    method = cut["processing"]["method"]
    if method == "horizontal_to_vertical":
        brightness = float(cut["processing"].get("brightness_adjust", -0.1))
        filter_complex = (
            f"[0:v]fps={FPS},"
            f"scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=increase,"
            f"crop={CANVAS_W}:{CANVAS_H},"
            "boxblur=36:2,"
            f"eq=brightness={brightness:.3f}:saturation=0.95[bg];"
            f"[0:v]fps={FPS},"
            f"scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[vout]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{trim_start:.3f}",
            "-t",
            f"{trim_duration:.3f}",
            "-i",
            str(source_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(output_path),
        ]
    else:
        filter_chain = (
            f"fps={FPS},"
            f"scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=increase,"
            f"crop={CANVAS_W}:{CANVAS_H},"
            "format=yuv420p"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{trim_start:.3f}",
            "-t",
            f"{trim_duration:.3f}",
            "-i",
            str(source_path),
            "-vf",
            filter_chain,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(output_path),
        ]

    run_command(cmd)


def render_cut_segments(spec: dict, segments_dir: Path) -> list[Path]:
    source_lookup: dict[str, dict] = {}
    for photo in spec["sources"]["photos"]:
        source_lookup[photo["id"]] = {"type": "photo", "path": resolve_source_path(photo["file"])}
    for video in spec["sources"]["videos"]:
        source_lookup[video["id"]] = {"type": "video", "path": resolve_source_path(video["file"])}

    segments: list[Path] = []
    for cut in spec["cuts"]:
        output_path = segments_dir / f"cut_{int(cut['cut_number']):02d}.mp4"
        source_info = source_lookup[cut["source_id"]]
        if cut["source_type"] == "photo":
            render_photo_segment(source_info["path"], cut, output_path)
        else:
            render_video_segment(source_info["path"], cut, output_path)
        segments.append(output_path)
    return segments


def write_concat_list(segments: list[Path], output_path: Path) -> None:
    lines = []
    for segment in segments:
        safe_path = segment.resolve().as_posix().replace("'", r"'\''")
        lines.append(f"file '{safe_path}'")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def concat_segments(segments: list[Path], output_path: Path) -> None:
    list_path = output_path.with_suffix(".txt")
    write_concat_list(segments, list_path)

    copy_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(output_path),
    ]
    try:
        run_command(copy_cmd)
        return
    except subprocess.CalledProcessError:
        pass

    reencode_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-an",
        "-vf",
        f"fps={FPS},format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(FPS),
        str(output_path),
    ]
    run_command(reencode_cmd)


def animation_durations(overlay: dict) -> tuple[float, float]:
    animation = overlay.get("animation", {})
    if "fade_in_start" in animation and "fade_in_end" in animation:
        fade_in = max(0.0, float(animation["fade_in_end"]) - float(animation["fade_in_start"]))
    elif "line_1_fade_in_start" in animation and "line_2_fade_in_end" in animation:
        fade_in = max(0.0, float(animation["line_2_fade_in_end"]) - float(animation["line_1_fade_in_start"]))
    elif "line_1_fade_in_start" in animation and "line_1_fade_in_end" in animation:
        fade_in = max(0.0, float(animation["line_1_fade_in_end"]) - float(animation["line_1_fade_in_start"]))
    else:
        fade_in = 0.4

    if "fade_out_start" in animation and "fade_out_end" in animation:
        fade_out = max(0.0, float(animation["fade_out_end"]) - float(animation["fade_out_start"]))
    elif animation.get("fade_out") == "none":
        fade_out = 0.0
    else:
        fade_out = 0.4

    return fade_in, fade_out


def overlay_stream_filter(input_index: int, label: str, overlay: dict) -> str:
    start_sec = float(overlay["start_sec"])
    end_sec = float(overlay["end_sec"])
    fade_in_sec, fade_out_sec = animation_durations(overlay)

    steps = [
        f"[{input_index}:v]fps={FPS}",
        "format=rgba",
        f"setpts=PTS-STARTPTS+{start_sec:.3f}/TB",
    ]
    if fade_in_sec > 0:
        steps.append(f"fade=t=in:st={start_sec:.3f}:d={fade_in_sec:.3f}:alpha=1")
    if fade_out_sec > 0:
        steps.append(f"fade=t=out:st={end_sec - fade_out_sec:.3f}:d={fade_out_sec:.3f}:alpha=1")
    return ",".join(steps) + f"[{label}]"


def overlay_y_expression(overlay: dict, y: int) -> str:
    start_sec = float(overlay["start_sec"])
    fade_in_sec, _ = animation_durations(overlay)

    if overlay["id"] == "hook":
        motion = 30
        return (
            f"if(lt(t,{start_sec + max(fade_in_sec, 0.001):.3f}),"
            f"{y}+{motion}*(1-((t-{start_sec:.3f})/{max(fade_in_sec, 0.001):.3f})),"
            f"{y})"
        )
    if overlay["id"] == "cta":
        motion = 32
        return (
            f"if(lt(t,{start_sec + max(fade_in_sec, 0.001):.3f}),"
            f"{y}+{motion}*(1-((t-{start_sec:.3f})/{max(fade_in_sec, 0.001):.3f})),"
            f"{y})"
        )
    return f"{y}"


def render_final_video(
    base_video: Path,
    bgm_path: Path,
    overlays: list[tuple[dict, dict]],
    output_video: Path,
    total_duration_sec: float,
) -> None:
    filter_lines = [
        f"[0:v]fps={FPS},"
        "eq=brightness=0.02:saturation=1.04:contrast=1.03:gamma=1.01,"
        f"fade=t=in:st=0:d=0.8,"
        f"fade=t=out:st={max(0.0, total_duration_sec - 1.5):.3f}:d=1.5[base]",
    ]

    current_label = "base"
    for offset, (overlay, meta) in enumerate(overlays, start=2):
        stream_label = f"overlaysrc{offset}"
        out_label = f"v{offset}"
        x, y = overlay_position(overlay, meta)
        filter_lines.append(overlay_stream_filter(offset, stream_label, overlay))
        filter_lines.append(
            f"[{current_label}][{stream_label}]overlay="
            f"x={x}:y='{overlay_y_expression(overlay, y)}':"
            "repeatlast=0:eof_action=pass:"
            f"eval=frame[{out_label}]"
        )
        current_label = out_label

    audio_spec = overlays[0][0]
    del audio_spec

    filter_lines.append(
        f"[1:a]atrim=0:{total_duration_sec:.3f},"
        "afade=t=in:st=0:d=1.0,"
        f"afade=t=out:st={max(0.0, total_duration_sec - 2.0):.3f}:d=2.0[aout]"
    )
    filter_complex = ";".join(filter_lines)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(base_video),
        "-i",
        str(bgm_path),
    ]
    for overlay, meta in overlays:
        duration_sec = max(0.1, float(overlay["end_sec"]) - float(overlay["start_sec"]))
        cmd.extend(
            [
                "-framerate",
                str(FPS),
                "-loop",
                "1",
                "-t",
                f"{duration_sec:.3f}",
                "-i",
                str(meta["path"]),
            ]
        )

    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            f"[{current_label}]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-b:v",
            "8M",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            f"{total_duration_sec:.3f}",
            str(output_video),
        ]
    )
    run_command(cmd)


def main() -> None:
    spec_path = VIDEO_DIR / "video2.json"
    spec = load_spec(spec_path)

    output_filename = spec["output"]["filename"]
    total_duration_sec = float(spec["output"]["total_duration_sec"])
    output_video = VIDEO_DIR / output_filename
    caption_file = VIDEO_DIR / f"{Path(output_filename).stem}_caption.txt"
    assets_dir = VIDEO_DIR / f"{Path(output_filename).stem}_assets"
    overlays_dir = assets_dir / "overlays"
    segments_dir = assets_dir / "segments"
    assets_dir.mkdir(exist_ok=True)
    overlays_dir.mkdir(exist_ok=True)
    segments_dir.mkdir(exist_ok=True)

    overlay_metas: list[tuple[dict, dict]] = []
    for overlay in spec["text_overlays"]:
        meta = render_overlay_image(overlay, overlays_dir / f"{overlay['id']}.png")
        overlay_metas.append((overlay, meta))

    audio_spec = spec["audio"]["bgm"]
    bgm_path = assets_dir / "ambient_bgm.wav"
    build_ambient_bgm(
        duration_sec=total_duration_sec,
        output_path=bgm_path,
        volume=float(audio_spec["volume"]),
        fade_in_sec=float(audio_spec["fade_in_sec"]),
        fade_out_sec=float(audio_spec["fade_out_sec"]),
    )

    write_caption(spec["caption"]["text"], caption_file)

    segments = render_cut_segments(spec, segments_dir)
    base_video = assets_dir / "assembled_base.mp4"
    concat_segments(segments, base_video)
    render_final_video(base_video, bgm_path, overlay_metas, output_video, total_duration_sec)

    print(f"Rendered video: {output_video}")
    print(f"Caption file: {caption_file}")
    print(f"Assets dir: {assets_dir}")


if __name__ == "__main__":
    main()
