from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SHORTS_DIR = Path(__file__).resolve().parent
VIDEO_DIR = SHORTS_DIR.parent / "video"


MOTION_TO_EFFECT = {
    "slow_push_in": "zoom_in",
    "slow_pan_right": "zoom_in_slow",
    "subtle_pan_up": "zoom_in_slow",
    "slow_pull_out": "zoom_out",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_to_video_dir(path_text: str) -> str:
    path = (ROOT / path_text).resolve()
    try:
        return str(path.relative_to(VIDEO_DIR))
    except ValueError:
        return str(path)


STYLE_PRESET_MAP = {
    "hook_bold": {
        "line_1": {
            "font": "Cafe24Dangdanghae-v2.0",
            "font_size": 50,
            "font_weight": "bold",
            "color": "#FFEE59",
            "stroke_color": "#07111D",
            "stroke_width": 3,
        },
        "line_2": {
            "font": "Cafe24Dangdanghae-v2.0",
            "font_size": 42,
            "font_weight": "bold",
            "color": "#FFEE59",
            "stroke_color": "#07111D",
            "stroke_width": 3,
        },
    },
    "label_minimal": {
        "line_1": {
            "font": "Cafe24Ohsquare-v2.0",
            "font_size": 34,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "stroke_color": "#0F1115",
            "stroke_width": 2,
        }
    },
    "supporting_soft": {
        "line_1": {
            "font": "Cafe24Ohsquare-v2.0",
            "font_size": 38,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "stroke_color": "#221133",
            "stroke_width": 2,
        },
        "line_2": {
            "font": "Cafe24Ohsquare-v2.0",
            "font_size": 34,
            "font_weight": "bold",
            "color": "#D9FFF6",
            "stroke_color": "#221133",
            "stroke_width": 2,
        },
    },
    "quote_soft": {
        "line_1": {
            "font": "Cafe24Dangdanghae-v2.0",
            "font_size": 46,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "stroke_color": "#1A0E22",
            "stroke_width": 3,
        },
        "line_2": {
            "font": "Cafe24Ohsquare-v2.0",
            "font_size": 34,
            "font_weight": "bold",
            "color": "#FFF4C2",
            "stroke_color": "#1A0E22",
            "stroke_width": 2,
        },
    },
    "cta_clean": {
        "line_1": {
            "font": "Cafe24Ohsquare-v2.0",
            "font_size": 40,
            "font_weight": "bold",
            "color": "#B9FFF2",
            "stroke_color": "#062E2B",
            "stroke_width": 2,
        },
        "line_2": {
            "font": "Cafe24Ohsquare-v2.0",
            "font_size": 34,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "stroke_color": "#062E2B",
            "stroke_width": 2,
        },
    },
}


def overlay_style(style_preset: str, kind: str) -> dict:
    preset = STYLE_PRESET_MAP.get(style_preset)
    if preset:
        return preset

    if kind == "hook":
        return {
            "line_1": {
                "font": "Cafe24Dangdanghae-v2.0",
                "font_size": 50,
                "font_weight": "bold",
                "color": "#FFEE59",
                "stroke_color": "#07111D",
                "stroke_width": 3,
            },
            "line_2": {
                "font": "Cafe24Dangdanghae-v2.0",
                "font_size": 42,
                "font_weight": "bold",
                "color": "#FFEE59",
                "stroke_color": "#07111D",
                "stroke_width": 3,
            },
        }
    if kind == "cta":
        return {
            "line_1": {
                "font": "Cafe24Ohsquare-v2.0",
                "font_size": 40,
                "font_weight": "bold",
                "color": "#B9FFF2",
                "stroke_color": "#062E2B",
                "stroke_width": 2,
            },
            "line_2": {
                "font": "Cafe24Ohsquare-v2.0",
                "font_size": 34,
                "font_weight": "bold",
                "color": "#FFFFFF",
                "stroke_color": "#062E2B",
                "stroke_width": 2,
            },
        }
    return {
        "line_1": {
            "font": "Cafe24Ohsquare-v2.0",
            "font_size": 44,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "stroke_color": "#221133",
            "stroke_width": 2.5,
        }
    }


def overlay_position(position_name: str, kind: str) -> dict:
    if position_name == "center":
        return {"anchor": "center", "y_percent": 57}
    if position_name == "top_center":
        return {"anchor": "top_center", "line_1_y_percent": 12, "line_2_y_percent": 16, "line_gap_px": 42}
    if position_name == "bottom_center":
        return {"anchor": "bottom_center", "line_1_y_percent": 74, "line_2_y_percent": 79, "line_gap_px": 36}
    if kind == "hook":
        return {"anchor": "top_center", "line_1_y_percent": 12, "line_2_y_percent": 16, "line_gap_px": 42}
    if kind == "cta":
        return {"anchor": "bottom_center", "line_1_y_percent": 74, "line_2_y_percent": 79, "line_gap_px": 36}
    return {"anchor": "center", "y_percent": 57}


def overlay_animation(kind: str, start_sec: float, end_sec: float) -> dict:
    if kind == "hook":
        return {
            "line_1_fade_in_start": start_sec,
            "line_1_fade_in_end": start_sec + 0.4,
            "line_2_fade_in_start": start_sec + 0.2,
            "line_2_fade_in_end": start_sec + 0.6,
            "fade_out_start": max(start_sec, end_sec - 0.35),
            "fade_out_end": end_sec,
            "type": "fade_in_up_staggered",
        }
    if kind == "cta":
        return {
            "line_1_fade_in_start": start_sec,
            "line_1_fade_in_end": start_sec + 0.4,
            "line_2_fade_in_start": start_sec + 0.2,
            "line_2_fade_in_end": start_sec + 0.6,
            "fade_out": "none",
            "type": "slide_up_staggered",
        }
    return {
        "fade_in_start": start_sec,
        "fade_in_end": start_sec + 0.4,
        "fade_out_start": max(start_sec, end_sec - 0.35),
        "fade_out_end": end_sec,
        "type": "fade_in_out",
    }


def split_lines(text: str) -> tuple[str, str | None]:
    words = text.split()
    if len(words) <= 4:
        return text, None
    pivot = max(1, len(words) // 2)
    return " ".join(words[:pivot]), " ".join(words[pivot:])


def build_overlay_usage(render_spec: dict) -> dict[str, list[int]]:
    usage: dict[str, list[int]] = {}
    for cut_number, clip in enumerate(render_spec["timeline"], start=1):
        for caption_id in clip.get("caption_ids", []):
            usage.setdefault(caption_id, []).append(cut_number)
    return usage


def build_legacy_overlay(item: dict, linked_cut_numbers: list[int]) -> dict:
    line_1, line_2 = split_lines(item["text"])
    kind = item["kind"]
    return {
        "id": item["text_id"],
        "text_line_1": line_1,
        "text_line_2": line_2,
        "start_sec": item["start_sec"],
        "end_sec": item["end_sec"],
        "appears_during_cut": linked_cut_numbers[0] if linked_cut_numbers else None,
        "linked_cut_numbers": linked_cut_numbers,
        "purpose": kind,
        "position": overlay_position(item.get("position", "center"), kind),
        "style": overlay_style(item.get("style_preset", ""), kind),
        "animation": overlay_animation(kind, float(item["start_sec"]), float(item["end_sec"])),
    }


def build_legacy_cut(index: int, item: dict) -> dict:
    processing: dict
    if item["asset_type"] == "photo":
        preset = item["motion"].get("preset", "slow_push_in")
        processing = {
            "method": "ken_burns",
            "effect": MOTION_TO_EFFECT.get(preset, "zoom_in"),
            "scale_from": item["motion"].get("scale_from"),
            "scale_to": item["motion"].get("scale_to"),
            "anchor": item["motion"].get("anchor", "center"),
        }
    else:
        method = "horizontal_to_vertical" if item["motion"].get("type") == "crop_reframe" else "direct_use"
        processing = {"method": method}
        if method == "horizontal_to_vertical":
            processing.update(
                {
                    "background": "blur_of_original",
                    "blur_sigma": 40,
                    "brightness_adjust": -0.1,
                    "foreground_position": "center",
                }
            )
        else:
            processing.update({"scale": "fit_to_1080x1920", "pad_if_needed": True})

    cut = {
        "cut_number": index,
        "label": item["beat_id"],
        "source_id": item["asset_id"],
        "source_type": item["asset_type"],
        "start_sec": item["start_sec"],
        "end_sec": item["end_sec"],
        "duration_sec": item["duration_sec"],
        "narrative_role": item["beat_id"],
        "processing": processing,
    }
    trim = item.get("trim", {})
    if item["asset_type"] == "video":
        cut["source_trim"] = {
            "trim_start_sec": trim.get("source_in_sec", 0.0),
            "trim_end_sec": trim.get("source_out_sec", item["duration_sec"]),
        }
    else:
        cut["crop"] = {
            "input_resolution": "unknown",
            "output_resolution": "1080x1920",
            "method": "center_crop_after_scale",
            "scale_first": "1200x2134",
        }
    return cut


def convert_render_spec_to_legacy(
    render_spec: dict,
    beat_sheet: dict,
    story_map: dict,
    *,
    output_filename: str,
) -> dict:
    overlay_usage = build_overlay_usage(render_spec)

    asset_meta: dict[str, dict] = {}
    for clip in render_spec["timeline"]:
        asset_meta[clip["asset_id"]] = {
            "file": relative_to_video_dir(clip["source_path"]),
            "kind": clip["asset_type"],
        }

    photos = []
    videos = []
    for asset_id, meta in asset_meta.items():
        if meta["kind"] == "photo":
            photos.append(
                {
                    "id": asset_id,
                    "file": meta["file"],
                    "resolution": "unknown",
                    "orientation": "vertical",
                    "description": story_map["source"]["asset_aliases"].get(asset_id.replace("photo_", "photo_0"), asset_id),
                }
            )
        else:
            orientation = "vertical" if "121601750" in meta["file"] else "horizontal"
            duration = 13.308 if "121601750" in meta["file"] else 7.035
            videos.append(
                {
                    "id": asset_id,
                    "file": meta["file"],
                    "resolution": "1080x1920" if orientation == "vertical" else "1920x1080",
                    "orientation": orientation,
                    "duration_sec": duration,
                    "description": story_map["source"]["asset_aliases"].get(asset_id, asset_id),
                    "has_audio": True,
                    "audio_usable": False,
                    "audio_note": "mute 처리 후 BGM/voiceover 사용",
                }
            )

    overlay_lookup = {item["text_id"]: item for item in render_spec["text_overlays"]}
    ordered_overlay_ids: list[str] = []
    for clip in render_spec["timeline"]:
        for caption_id in clip.get("caption_ids", []):
            if caption_id in overlay_lookup and caption_id not in ordered_overlay_ids:
                ordered_overlay_ids.append(caption_id)
    for item in render_spec["text_overlays"]:
        if item["text_id"] not in ordered_overlay_ids:
            ordered_overlay_ids.append(item["text_id"])

    legacy = {
        "version": "1.0",
        "type": "reels_cut_edit_spec",
        "created_at": "2026-03-29",
        "project": "shorts_test_blog_translation",
        "output": {
            "filename": output_filename,
            "resolution": "1080x1920",
            "aspect_ratio": "9:16",
            "fps": render_spec["export"]["fps"],
            "codec": render_spec["export"]["codec"],
            "bitrate": render_spec["export"]["video_bitrate"],
            "total_duration_sec": render_spec["source"]["target_duration_sec"],
        },
        "narrative": {
            "main_angle": beat_sheet["source"]["main_angle"],
            "story_arc": "hook -> setup -> proof -> reaction -> cta",
            "target_audience": "부산 여행객, 외국인 고객, 서면 상권 콘텐츠 소비자",
            "tone": beat_sheet["editorial"]["visual_style"],
        },
        "sources": {
            "photos": photos,
            "videos": videos,
        },
        "cuts": [build_legacy_cut(index, clip) for index, clip in enumerate(render_spec["timeline"], start=1)],
        "text_overlays": [
            build_legacy_overlay(overlay_lookup[overlay_id], overlay_usage.get(overlay_id, []))
            for overlay_id in ordered_overlay_ids
        ],
        "voiceover": render_spec.get("voiceover", {}),
        "global_effects": {
            "fade_in": {"type": "from_black", "duration_sec": 0.8, "start_sec": 0.0},
            "fade_out": {
                "type": "to_black",
                "duration_sec": 1.5,
                "start_sec": max(0.0, float(render_spec["source"]["target_duration_sec"]) - 1.5),
            },
        },
        "audio": {
            "original_audio": "mute_all",
            "mute_reason": "원본 현장음 대신 BGM과 voiceover 중심 구성",
            "bgm": {
                "required": True,
                "mood": render_spec["audio"]["bgm"]["mood"],
                "tempo": "60-80 BPM",
                "style_references": ["lo-fi spa beats", "ambient piano", "soft electronic"],
                "volume": render_spec["audio"]["bgm"]["volume"],
                "fade_in_sec": 1.0,
                "fade_out_sec": 2.0,
                "license": "royalty-free required",
                "note": "현재 테스트용 합성 BGM 생성",
            },
        },
        "instagram_reels_safe_zone": {
            "top_avoid_percent": render_spec["visual_effects"]["safe_zone"]["top_pct"],
            "bottom_avoid_percent": render_spec["visual_effects"]["safe_zone"]["bottom_pct"],
            "right_avoid_percent": 15,
            "note": "플랫폼 UI 겹침 방지",
        },
        "caption": {
            "platform": "instagram_reels",
            "text": "\n".join(
                [
                    beat_sheet["source"]["main_angle"],
                    "필리핀 손님 5명이 한국 오기 전부터 예약하고 받은 서면 헤드스파 경험.",
                    "#서면헤드스파 #부산헤드스파 #K뷰티 #부산여행 #시선을즐기다",
                ]
            ),
        },
        "production_notes": {
            "font": "Cafe24Dangdanghae / Cafe24Ohsquare 사용",
            "text_readability": "모든 text_overlays를 유지하고 caption_ids로 컷과 연결",
            "color_grade": render_spec["visual_effects"]["color_grade"]["preset"],
            "transition": "hard_cut + soft_push + fade 혼합",
        },
    }
    return legacy


def write_legacy_outputs(
    render_spec_path: Path,
    beat_sheet_path: Path,
    story_map_path: Path,
    output_path: Path,
) -> dict:
    render_spec = load_json(render_spec_path)
    beat_sheet = load_json(beat_sheet_path)
    story_map = load_json(story_map_path)

    legacy = convert_render_spec_to_legacy(
        render_spec,
        beat_sheet,
        story_map,
        output_filename=f"{SHORTS_DIR.name}_render.mp4",
    )

    output_path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")

    voiceover_script = SHORTS_DIR / "shorts_voiceover_script.txt"
    caption = VIDEO_DIR / "shorts_test_render_caption.txt"
    caption.write_text(legacy["caption"]["text"] + "\n", encoding="utf-8")
    if legacy.get("voiceover", {}).get("script_blocks"):
        voiceover_script.write_text(
            "\n".join(block["text"] for block in legacy["voiceover"]["script_blocks"]) + "\n",
            encoding="utf-8",
        )

    print(f"Wrote legacy spec: {output_path}")
    print(f"Voiceover script: {voiceover_script}")
    print(f"Caption draft: {caption}")
    return legacy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-spec", default=str(SHORTS_DIR / "shorts_render_spec.json"))
    parser.add_argument("--beat-sheet", default=str(SHORTS_DIR / "shorts_beat_sheet.json"))
    parser.add_argument("--story-map", default=str(SHORTS_DIR / "blog_story_map.json"))
    parser.add_argument("--output", default=str(VIDEO_DIR / "shorts_test_legacy_spec.json"))
    args = parser.parse_args()

    write_legacy_outputs(
        render_spec_path=Path(args.render_spec).resolve(),
        beat_sheet_path=Path(args.beat_sheet).resolve(),
        story_map_path=Path(args.story_map).resolve(),
        output_path=Path(args.output).resolve(),
    )


if __name__ == "__main__":
    main()
