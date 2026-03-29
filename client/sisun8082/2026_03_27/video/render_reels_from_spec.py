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


def resolve_font(font_name: str) -> Path:
    direct_path = Path(font_name)
    if direct_path.exists():
        return direct_path
    for candidate in FONT_CANDIDATES.get(font_name, []):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No usable font found for {font_name}")


def parse_rgba(value: str) -> tuple[int, int, int, int] | None:
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


def render_text_image(text: str, style: dict, output_path: Path) -> dict:
    font_path = resolve_font(style["font"])
    font_size = int(style["font_size"])
    stroke_width = int(round(style.get("stroke_width", 0)))
    fill = parse_rgba(style["color"]) or (255, 255, 255, 255)
    stroke_fill = parse_rgba(style.get("stroke_color", "#000000")) or (0, 0, 0, 255)
    background_fill = parse_rgba(style.get("background", "none"))
    padding = int(round(style.get("background_padding", 0)))
    radius = int(round(style.get("background_radius", 0)))
    line_spacing = max(8, int(font_size * 0.2))

    safe_text = strip_unreliable_emoji(text)
    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    line_font_sizes = style.get("line_font_sizes")

    if line_font_sizes:
        lines = safe_text.splitlines() or [safe_text]
        normalized_sizes = [int(round(size)) for size in line_font_sizes]
        if not normalized_sizes:
            normalized_sizes = [font_size]
        if len(normalized_sizes) < len(lines):
            normalized_sizes.extend([normalized_sizes[-1]] * (len(lines) - len(normalized_sizes)))
        fonts = [ImageFont.truetype(str(font_path), normalized_sizes[idx]) for idx in range(len(lines))]
        line_spacing = max(8, int(max(normalized_sizes) * 0.18))

        metrics = []
        content_w = 0
        content_h = 0
        for idx, line in enumerate(lines):
            bbox = probe_draw.textbbox((0, 0), line, font=fonts[idx], stroke_width=stroke_width)
            line_w = math.ceil(bbox[2] - bbox[0])
            line_h = math.ceil(bbox[3] - bbox[1])
            metrics.append((line, fonts[idx], bbox, line_w, line_h))
            content_w = max(content_w, line_w)
            content_h += line_h
            if idx < len(lines) - 1:
                content_h += line_spacing

        image_w = int(content_w + (padding * 2))
        image_h = int(content_h + (padding * 2))

        image = Image.new("RGBA", (image_w, image_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        if background_fill:
            draw.rounded_rectangle(
                (0, 0, image_w - 1, image_h - 1),
                radius=radius,
                fill=background_fill,
            )

        current_y = padding
        for idx, (line, line_font, bbox, line_w, line_h) in enumerate(metrics):
            x = padding + ((content_w - line_w) / 2.0) - bbox[0]
            y = current_y - bbox[1]
            draw.text(
                (x, y),
                line,
                font=line_font,
                fill=fill,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
            )
            current_y += line_h
            if idx < len(metrics) - 1:
                current_y += line_spacing

        image.save(output_path)
        return {"path": output_path, "width": image_w, "height": image_h, "rendered_text": safe_text}

    font = ImageFont.truetype(str(font_path), font_size)
    bbox = probe_draw.multiline_textbbox(
        (0, 0),
        safe_text,
        font=font,
        spacing=line_spacing,
        align="center",
        stroke_width=stroke_width,
    )
    text_w = math.ceil(bbox[2] - bbox[0])
    text_h = math.ceil(bbox[3] - bbox[1])
    image_w = int(text_w + (padding * 2))
    image_h = int(text_h + (padding * 2))

    image = Image.new("RGBA", (image_w, image_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if background_fill:
        draw.rounded_rectangle(
            (0, 0, image_w - 1, image_h - 1),
            radius=radius,
            fill=background_fill,
        )

    draw.multiline_text(
        (padding - bbox[0], padding - bbox[1]),
        safe_text,
        font=font,
        fill=fill,
        spacing=line_spacing,
        align="center",
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    image.save(output_path)
    return {"path": output_path, "width": image_w, "height": image_h, "rendered_text": safe_text}


def position_for_overlay(position: str, y_percent: float, width: int, height: int) -> tuple[int, int]:
    x = (CANVAS_W - width) // 2
    y_center = CANVAS_H * (y_percent / 100.0)
    y = round(y_center - (height / 2))
    return x, y


def write_caption(caption_text: str, output_path: Path) -> None:
    output_path.write_text(caption_text.rstrip() + "\n", encoding="utf-8")


def build_ambient_bgm(duration_sec: float, output_path: Path, volume: float, fade_in_sec: float, fade_out_sec: float) -> None:
    sample_rate = 44100
    sample_count = max(1, int(round(duration_sec * sample_rate)))
    t = np.linspace(0.0, duration_sec, sample_count, endpoint=False, dtype=np.float64)
    audio = np.zeros_like(t)
    rng = np.random.default_rng(42)

    segments = [
        (0.0, min(duration_sec, 4.4), [220.0, 277.18, 329.63]),
        (min(duration_sec, 4.4), min(duration_sec, 8.8), [196.0, 246.94, 293.66]),
        (min(duration_sec, 8.8), duration_sec, [207.65, 261.63, 311.13]),
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


def filter_escape(path: Path) -> str:
    return str(path).replace("\\", "/")


def run_ffmpeg(
    source_video: Path,
    bgm_path: Path,
    hook: dict,
    reaction: dict,
    cta: dict,
    duration_sec: float,
    output_path: Path,
) -> None:
    hook_x, hook_y = position_for_overlay("top_center", 15, hook["width"], hook["height"])
    reaction_x, reaction_y = position_for_overlay("center", 60, reaction["width"], reaction["height"])
    cta_x, cta_y = position_for_overlay("bottom_center", 78, cta["width"], cta["height"])

    fade_out_start = max(0.0, duration_sec - 1.5)
    bgm_fade_out_start = max(0.0, duration_sec - 2.0)
    hook_exit_start = 4.0 - 0.3
    reaction_exit_start = 8.0 - 0.3

    filter_lines = [
        f"[0:v]fps={FPS},scale={CANVAS_W}:{CANVAS_H},setsar=1,"
        "eq=brightness=0.03:saturation=1.08:contrast=1.04:gamma=1.02,"
        "vignette=PI/6:eval=frame,"
        f"fade=t=in:st=0:d=0.8,fade=t=out:st={fade_out_start:.3f}:d=1.5[base]",
        f"[2:v]format=rgba,fade=t=in:st=0:d=0.4:alpha=1,"
        f"fade=t=out:st={hook_exit_start:.3f}:d=0.3:alpha=1[hookimg]",
        f"[base][hookimg]overlay=x={hook_x}:"
        f"y='if(lt(t,0.4),{hook_y}+40*(1-(t/0.4)),{hook_y})':"
        "eval=frame:enable='between(t,0,4.0)'[v1]",
        "[3:v]format=rgba,"
        "crop=w='if(lt(t,4.5),2,if(lt(t,5.1),max(2,iw*(t-4.5)/0.6),iw))':"
        "h=ih:x=0:y=0,"
        f"fade=t=out:st={reaction_exit_start:.3f}:d=0.3:alpha=1[reactimg]",
        f"[v1][reactimg]overlay=x={reaction_x}:y={reaction_y}:"
        "eval=frame:enable='between(t,4.5,8.0)'[v2]",
        "[4:v]format=rgba,fade=t=in:st=9.0:d=0.4:alpha=1[ctaimg]",
        f"[v2][ctaimg]overlay=x={cta_x}:"
        f"y='if(lt(t,9.0),{cta_y}+40,if(lt(t,9.4),{cta_y}+40*(1-((t-9.0)/0.4)),{cta_y}))':"
        "eval=frame:enable='between(t,9.0,"
        f"{duration_sec:.3f})'[vout]",
        f"[1:a]atrim=0:{duration_sec:.3f},afade=t=in:st=0:d=1.0,"
        f"afade=t=out:st={bgm_fade_out_start:.3f}:d=2.0[aout]",
    ]
    filter_complex = ";".join(filter_lines)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_video),
        "-i",
        str(bgm_path),
        "-framerate",
        str(FPS),
        "-loop",
        "1",
        "-i",
        filter_escape(Path(hook["path"])),
        "-framerate",
        str(FPS),
        "-loop",
        "1",
        "-i",
        filter_escape(Path(reaction["path"])),
        "-framerate",
        str(FPS),
        "-loop",
        "1",
        "-i",
        filter_escape(Path(cta["path"])),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
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
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    workdir = Path(__file__).resolve().parent
    spec_path = workdir / "reels_edit_spec.json"
    spec = load_spec(spec_path)

    source_video = workdir / spec["source"]["file"]
    duration_sec = float(spec["edit_spec"]["total_duration_sec"])
    output_stem = source_video.stem + "_reels_edit"
    output_video = workdir / f"{output_stem}.mp4"
    caption_file = workdir / f"{output_stem}_caption.txt"
    assets_dir = workdir / f"{output_stem}_assets"
    assets_dir.mkdir(exist_ok=True)

    overlays = spec["edit_spec"]["text_overlays"]
    hook = render_text_image(overlays[0]["text"], overlays[0]["style"], assets_dir / "hook.png")
    reaction = render_text_image(overlays[1]["text"], overlays[1]["style"], assets_dir / "reaction.png")
    cta = render_text_image(overlays[2]["text"], overlays[2]["style"], assets_dir / "cta.png")

    audio_spec = spec["edit_spec"]["audio"]["bgm"]
    bgm_path = assets_dir / "ambient_bgm.wav"
    build_ambient_bgm(
        duration_sec=duration_sec,
        output_path=bgm_path,
        volume=float(audio_spec["volume"]),
        fade_in_sec=float(audio_spec["fade_in_sec"]),
        fade_out_sec=float(audio_spec["fade_out_sec"]),
    )

    write_caption(spec["edit_spec"]["caption"]["text"], caption_file)
    run_ffmpeg(source_video, bgm_path, hook, reaction, cta, duration_sec, output_video)

    print(f"Rendered video: {output_video}")
    print(f"Caption file: {caption_file}")
    print(f"Assets dir: {assets_dir}")


if __name__ == "__main__":
    main()
