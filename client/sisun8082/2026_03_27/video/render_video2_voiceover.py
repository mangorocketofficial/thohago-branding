from __future__ import annotations

import subprocess
import wave
from pathlib import Path

from google.cloud import texttospeech

from render_video2_from_spec import (
    CANVAS_H,
    FPS,
    VIDEO_DIR,
    build_ambient_bgm,
    concat_segments,
    load_spec,
    render_cut_segments,
    resolve_font,
    write_caption,
)


VOICE_NAME = "ko-KR-Neural2-A"
VOICE_SPEAKING_RATE = 1.0
CLOSING_TITLE_TEXT = "시선을 즐기다"
CLOSING_TITLE_START = 18.45
CLOSING_TITLE_RISE_END = 19.15
SCRIPT_ENTRIES = [
    {
        "speech": "필리핀에서 온 다섯 분이 예약하고 찾아온 서면 헤드스파.",
        "subtitle": "필리핀에서 온 다섯 분이,\n예약하고 찾아온 서면 헤드스파.",
    },
    {
        "speech": "도착하자마자 두피 진단을 받고,",
        "subtitle": "도착하자마자\n두피 진단을 받고,",
    },
    {
        "speech": "다섯 명이 함께 케어를 시작합니다.",
        "subtitle": "다섯 명이 함께\n케어를 시작합니다.",
    },
    {
        "speech": "캔들 향이 퍼지는 동안 두피 집중 케어가 이어지고,",
        "subtitle": "캔들 향이 퍼지는 동안\n두피 집중 케어가 이어지고,",
    },
    {
        "speech": "LED 테라피 단계에서 다들 너무 시원하다고 반응하죠.",
        "subtitle": "LED 테라피 단계에서\n다들 너무 시원하다고 반응하죠.",
    },
    {
        "speech": "여행 중 다시 찾고 싶은 곳, 시선을 즐기다에서 직접 느껴보세요.",
        "subtitle": "여행 중 다시 찾고 싶은 곳,\n시선을 즐기다에서 직접 느껴보세요.",
    },
]


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip().split("=")[1])


def format_srt_timestamp(seconds: float) -> str:
    millis_total = max(0, int(round(seconds * 1000.0)))
    hours = millis_total // 3_600_000
    minutes = (millis_total % 3_600_000) // 60_000
    secs = (millis_total % 60_000) // 1000
    millis = millis_total % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def ffmpeg_escape_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:")


def ffmpeg_escape_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace("%", r"\%")
        .replace("\n", r"\n")
    )


def write_voice_script(script_path: Path) -> None:
    script_path.write_text(
        "\n".join(entry["speech"] for entry in SCRIPT_ENTRIES) + "\n",
        encoding="utf-8",
    )


def trim_audio_segment(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-af",
        (
            "silenceremove="
            "start_periods=1:start_silence=0.05:start_threshold=-45dB:"
            "stop_periods=-1:stop_silence=0.12:stop_threshold=-45dB"
        ),
        str(output_path),
    ]
    run_command(cmd)


def concatenate_wavs(input_paths: list[Path], output_path: Path) -> None:
    if not input_paths:
        raise ValueError("No audio segments to concatenate")

    with wave.open(str(input_paths[0]), "rb") as first_in:
        params = first_in.getparams()
        frames = [first_in.readframes(first_in.getnframes())]

    for input_path in input_paths[1:]:
        with wave.open(str(input_path), "rb") as wav_in:
            current_params = wav_in.getparams()
            if (
                current_params.nchannels != params.nchannels
                or current_params.sampwidth != params.sampwidth
                or current_params.framerate != params.framerate
            ):
                raise ValueError(f"Mismatched WAV params for {input_path}")
            frames.append(wav_in.readframes(wav_in.getnframes()))

    with wave.open(str(output_path), "wb") as wav_out:
        wav_out.setparams(params)
        for frame_chunk in frames:
            wav_out.writeframes(frame_chunk)


def write_srt(entries: list[dict], output_path: Path) -> None:
    blocks: list[str] = []
    for idx, entry in enumerate(entries, start=1):
        blocks.append(
            "\n".join(
                [
                    str(idx),
                    f"{format_srt_timestamp(entry['start'])} --> {format_srt_timestamp(entry['end'])}",
                    entry["text"],
                ]
            )
        )
    output_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def synthesize_google_voice(
    assets_dir: Path,
    total_duration: float,
    script_path: Path,
    voice_audio_path: Path,
    subtitle_path: Path,
) -> None:
    write_voice_script(script_path)

    client = texttospeech.TextToSpeechClient()
    segment_dir = assets_dir / "voice_segments"
    segment_dir.mkdir(exist_ok=True)

    segment_paths: list[Path] = []
    subtitle_entries: list[dict] = []

    for idx, entry in enumerate(SCRIPT_ENTRIES, start=1):
        mp3_path = segment_dir / f"segment_{idx:02d}.mp3"
        wav_path = segment_dir / f"segment_{idx:02d}.wav"

        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=entry["speech"]),
            voice=texttospeech.VoiceSelectionParams(
                language_code="ko-KR",
                name=VOICE_NAME,
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=VOICE_SPEAKING_RATE,
            ),
        )
        mp3_path.write_bytes(response.audio_content)
        trim_audio_segment(mp3_path, wav_path)

        duration = probe_duration(wav_path)
        segment_paths.append(wav_path)
        subtitle_entries.append({"text": entry["subtitle"], "duration": duration})

    raw_voice_path = assets_dir / "headspa_voiceover_raw.wav"
    concatenate_wavs(segment_paths, raw_voice_path)

    raw_total_duration = sum(entry["duration"] for entry in subtitle_entries)
    if raw_total_duration > total_duration + 0.5:
        raise ValueError(
            f"Voiceover script is too long at normal speed ({raw_total_duration:.2f}s > {total_duration:.2f}s)"
        )

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw_voice_path),
            str(voice_audio_path),
        ]
    )

    current_start = 0.0
    timed_entries: list[dict] = []
    for entry in subtitle_entries:
        timed_entries.append(
            {
                "start": current_start,
                "end": current_start + entry["duration"],
                "text": entry["text"],
            }
        )
        current_start += entry["duration"]

    write_srt(timed_entries, subtitle_path)


def hook_filters(spec: dict) -> list[str]:
    hook = spec["text_overlays"][0]
    font_path = ffmpeg_escape_path(resolve_font(hook["style"]["line_1"].get("font")))

    line_1 = hook["style"]["line_1"]
    line_2 = hook["style"]["line_2"]
    start_sec = float(hook["start_sec"])
    end_sec = float(hook["end_sec"])

    return [
        (
            "drawtext="
            f"fontfile='{font_path}':"
            f"text='{ffmpeg_escape_text(hook['text_line_1'])}':"
            f"fontsize={int(line_1['font_size'])}:"
            f"fontcolor={line_1['color']}:"
            f"borderw={int(line_1['stroke_width'])}:"
            f"bordercolor={line_1['stroke_color']}:"
            "x=(w-text_w)/2:"
            f"y={round(CANVAS_H * (hook['position']['line_1_y_percent'] / 100.0))}:"
            f"enable='between(t,{start_sec:.3f},{end_sec:.3f})'"
        ),
        (
            "drawtext="
            f"fontfile='{font_path}':"
            f"text='{ffmpeg_escape_text(hook['text_line_2'])}':"
            f"fontsize={int(line_2['font_size'])}:"
            f"fontcolor={line_2['color']}:"
            f"borderw={int(line_2['stroke_width'])}:"
            f"bordercolor={line_2['stroke_color']}:"
            "x=(w-text_w)/2:"
            f"y={round(CANVAS_H * (hook['position']['line_2_y_percent'] / 100.0))}:"
            f"enable='between(t,{start_sec:.3f},{end_sec:.3f})'"
        ),
    ]


def closing_title_filters() -> list[str]:
    font_path = ffmpeg_escape_path(resolve_font("Cafe24Dangdanghae-v2.0"))
    alpha_expr = (
        f"if(lt(t,{CLOSING_TITLE_START:.3f}),0,"
        f"if(lt(t,{CLOSING_TITLE_RISE_END:.3f}),"
        f"(t-{CLOSING_TITLE_START:.3f})/{CLOSING_TITLE_RISE_END - CLOSING_TITLE_START:.3f},1))"
    )
    y_expr = (
        f"(h-text_h)/2 + if(lt(t,{CLOSING_TITLE_RISE_END:.3f}),"
        f"18*(1-((t-{CLOSING_TITLE_START:.3f})/{CLOSING_TITLE_RISE_END - CLOSING_TITLE_START:.3f})),0)"
    )
    enable_expr = f"between(t,{CLOSING_TITLE_START:.3f},21.000)"

    return [
        (
            "drawtext="
            f"fontfile='{font_path}':"
            f"text='{ffmpeg_escape_text(CLOSING_TITLE_TEXT)}':"
            "fontsize=108:"
            "fontcolor=#FFEE59:"
            f"alpha='0.22*({alpha_expr})':"
            "x=(w-text_w)/2:"
            f"y='{y_expr}':"
            f"enable='{enable_expr}'"
        ),
        (
            "drawtext="
            f"fontfile='{font_path}':"
            f"text='{ffmpeg_escape_text(CLOSING_TITLE_TEXT)}':"
            "fontsize=86:"
            "fontcolor=#FFEE59:"
            "borderw=3:"
            "bordercolor=#000000:"
            "shadowcolor=black@0.35:"
            "shadowx=0:"
            "shadowy=6:"
            f"alpha='{alpha_expr}':"
            "x=(w-text_w)/2:"
            f"y='{y_expr}':"
            f"enable='{enable_expr}'"
        ),
    ]


def subtitle_filters(subtitles: list[dict]) -> list[str]:
    font_path = ffmpeg_escape_path(resolve_font("Cafe24Ohsquare-v2.0"))
    filters: list[str] = []

    for entry in subtitles:
        lines = entry["text"].splitlines() or [entry["text"]]
        if len(lines) == 1:
            y_positions = ["h-text_h-380"]
        else:
            y_positions = ["h-430", "h-370"]

        for idx, line in enumerate(lines[:2]):
            filters.append(
                (
                    "drawtext="
                    f"fontfile='{font_path}':"
                    f"text='{ffmpeg_escape_text(line)}':"
                    "fontsize=38:"
                    "fontcolor=#FFFFFF:"
                    "borderw=3:"
                    "bordercolor=#000000:"
                    "box=1:"
                    "boxcolor=black@0.35:"
                    "boxborderw=18:"
                    "x=(w-text_w)/2:"
                    f"y={y_positions[min(idx, len(y_positions) - 1)]}:"
                    f"enable='between(t,{entry['start']:.3f},{entry['end']:.3f})'"
                )
            )

    return filters


def parse_srt(subtitle_path: Path) -> list[dict]:
    content = subtitle_path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    blocks = [block for block in content.split("\n\n") if block.strip()]
    entries: list[dict] = []

    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue

        start_raw, end_raw = lines[1].split(" --> ")
        text = "\n".join(lines[2:])

        entries.append(
            {
                "start": parse_timecode(start_raw),
                "end": parse_timecode(end_raw),
                "text": text,
            }
        )

    return entries


def parse_timecode(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + (int(millis) / 1000.0)
    )


def render_voiceover_video(
    base_video: Path,
    audio_path: Path,
    subtitle_path: Path,
    spec: dict,
    output_video: Path,
) -> None:
    total_duration = float(spec["output"]["total_duration_sec"])
    subtitles = parse_srt(subtitle_path)

    video_filters = [
        "fps=30",
        "eq=brightness=0.02:saturation=1.04:contrast=1.03:gamma=1.01",
        "fade=t=in:st=0:d=0.8",
        f"fade=t=out:st={max(0.0, total_duration - 1.5):.3f}:d=1.5",
    ]
    video_filters.extend(hook_filters(spec))
    video_filters.extend(subtitle_filters(subtitles))
    video_filters.extend(closing_title_filters())
    video_filter_chain = ",".join(video_filters)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(base_video),
        "-i",
        str(audio_path),
        "-vf",
        video_filter_chain,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
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
        f"{total_duration:.3f}",
        str(output_video),
    ]
    run_command(cmd)


def mix_voice_with_bgm(
    voice_path: Path,
    bgm_path: Path,
    total_duration: float,
    output_audio: Path,
) -> None:
    filter_complex = (
        f"[0:a]atrim=0:{total_duration:.3f},apad=whole_dur={total_duration:.3f},asetpts=N/SR/TB[voice];"
        f"[1:a]atrim=0:{total_duration:.3f},volume=0.13,"
        "afade=t=in:st=0:d=1.0,"
        f"afade=t=out:st={max(0.0, total_duration - 2.0):.3f}:d=2.0,"
        "asetpts=N/SR/TB[bgm];"
        "[voice][bgm]amix=inputs=2:duration=longest:normalize=0,"
        "aresample=async=1:first_pts=0[aout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(voice_path),
        "-i",
        str(bgm_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[aout]",
        "-t",
        f"{total_duration:.3f}",
        str(output_audio),
    ]
    run_command(cmd)


def main() -> None:
    spec = load_spec(VIDEO_DIR / "video2.json")
    output_video = VIDEO_DIR / spec["output"]["filename"]
    caption_file = VIDEO_DIR / f"{Path(spec['output']['filename']).stem}_caption.txt"
    assets_dir = VIDEO_DIR / f"{Path(spec['output']['filename']).stem}_assets"
    assets_dir.mkdir(exist_ok=True)
    segments_dir = assets_dir / "segments"
    segments_dir.mkdir(exist_ok=True)

    voice_script_path = assets_dir / "headspa_voice_script.txt"
    voice_audio_path = assets_dir / "headspa_voiceover.wav"
    subtitle_path = assets_dir / "headspa_voiceover.srt"
    bgm_path = assets_dir / "ambient_bgm.wav"
    mixed_audio_path = assets_dir / "headspa_mix.wav"
    base_video = assets_dir / "assembled_base.mp4"
    total_duration = float(spec["output"]["total_duration_sec"])

    synthesize_google_voice(
        assets_dir=assets_dir,
        total_duration=total_duration,
        script_path=voice_script_path,
        voice_audio_path=voice_audio_path,
        subtitle_path=subtitle_path,
    )

    build_ambient_bgm(
        duration_sec=total_duration,
        output_path=bgm_path,
        volume=float(spec["audio"]["bgm"]["volume"]),
        fade_in_sec=float(spec["audio"]["bgm"]["fade_in_sec"]),
        fade_out_sec=float(spec["audio"]["bgm"]["fade_out_sec"]),
    )

    mix_voice_with_bgm(
        voice_path=voice_audio_path,
        bgm_path=bgm_path,
        total_duration=total_duration,
        output_audio=mixed_audio_path,
    )

    write_caption(spec["caption"]["text"], caption_file)

    segments = render_cut_segments(spec, segments_dir)
    concat_segments(segments, base_video)
    render_voiceover_video(base_video, mixed_audio_path, subtitle_path, spec, output_video)

    print(f"Rendered video: {output_video}")
    print(f"Voice script: {voice_script_path}")
    print(f"Voice audio: {voice_audio_path}")
    print(f"Subtitle file: {subtitle_path}")


if __name__ == "__main__":
    main()
