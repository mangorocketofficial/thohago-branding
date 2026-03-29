from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from urllib.request import Request, urlopen

from thohago.heuristics import extract_keywords
from thohago.models import MediaAsset, PlannerOutput, ShopConfig


class AnthropicApiClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"

    def create_message(self, system: str, content: list[dict], max_tokens: int = 1200) -> dict:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": content}],
        }
        request = Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))


class AnthropicMultimodalInterviewEngine:
    def __init__(self, client: AnthropicApiClient) -> None:
        self.client = client

    def build_preflight(self, shop: ShopConfig, photos: list[Path], videos: list[Path]) -> tuple[dict, list[MediaAsset], list[MediaAsset]]:
        selected_photos = photos[:5]
        response = self.client.create_message(
            system=(
                "You analyze beauty-shop session photos for a Korean content pipeline. "
                "Return valid JSON only. No markdown fences, no prose."
            ),
            content=[
                {
                    "type": "text",
                    "text": (
                        "Analyze these beauty-shop session photos.\n"
                        "Return JSON with keys: structure_mode, key_visual_evidence, "
                        "question_focus_candidates, photo_annotations.\n"
                        "photo_annotations must be an array of objects with keys: "
                        "photo_index, scene, details, mood, selected_for_prompt.\n"
                        f"Shop hints: {', '.join(shop.media_hints) if shop.media_hints else 'none'}"
                    ),
                },
                *[self._image_content(path) for path in selected_photos],
            ],
            max_tokens=1400,
        )
        parsed = self._parse_json_text(response)
        annotations = {item["photo_index"]: item for item in parsed.get("photo_annotations", []) if isinstance(item, dict)}

        photo_assets: list[MediaAsset] = []
        for index, path in enumerate(photos, start=1):
            annotation = annotations.get(index, {})
            photo_assets.append(
                MediaAsset(
                    media_id=f"photo_{index}",
                    kind="photo",
                    source_path=path,
                    relative_source_path=str(path),
                    experience_order=index,
                    preflight_analysis={
                        "scene": annotation.get("scene", "key_moment"),
                        "details": annotation.get("details", shop.media_hints[:1] or ["service photo"]),
                        "mood": annotation.get("mood", "professional"),
                    },
                    selected_for_prompt=bool(annotation.get("selected_for_prompt", index <= 3)),
                )
            )

        video_assets: list[MediaAsset] = []
        for index, path in enumerate(videos, start=1):
            video_assets.append(
                MediaAsset(
                    media_id=f"video_{index}",
                    kind="video",
                    source_path=path,
                    relative_source_path=str(path),
                    experience_order=index,
                    preflight_analysis={
                        "scene": "video_clip",
                        "details": ["uploaded video clip"],
                        "orientation": "unknown",
                    },
                    selected_for_prompt=False,
                    reels_eligible=False,
                    duration_sec=None,
                )
            )

        preflight = {
            "model_mode": f"anthropic_messages:{self.client.model}",
            "structure_mode": parsed.get("structure_mode", "key_moments"),
            "experience_sequence": [asset.media_id for asset in photo_assets],
            "representative_photo_ids": [asset.media_id for asset in photo_assets if asset.selected_for_prompt],
            "key_visual_evidence": parsed.get("key_visual_evidence", shop.media_hints or []),
            "question_focus_candidates": parsed.get(
                "question_focus_candidates",
                ["customer reaction", "differentiator", "entry_channel"],
            ),
            "photos": [asset.to_dict() for asset in photo_assets],
            "videos": [asset.to_dict() for asset in video_assets],
        }
        return preflight, photo_assets, video_assets

    def plan_turn(self, turn_index: int, transcripts: list[str], preflight: dict) -> PlannerOutput:
        transcript_blob = "\n".join(
            f"Turn {index}: {text}" for index, text in enumerate(transcripts, start=1)
        )
        response = self.client.create_message(
            system=(
                "You are a Korean beauty-shop interview planner. "
                "Create exactly one short, natural Korean follow-up question. "
                "Return valid JSON only with keys: main_angle, covered_elements, "
                "missing_elements, question_strategy, next_question, evidence."
            ),
            content=[
                {
                    "type": "text",
                    "text": (
                        f"Generate Turn {turn_index}.\n"
                        f"Interview transcripts so far:\n{transcript_blob}\n\n"
                        f"Media preflight summary:\n{json.dumps(preflight, ensure_ascii=False)}\n\n"
                        "Use the images as context. Ask about the highest-value missing element. "
                        "The question must be answerable in under one minute."
                    ),
                },
                *[self._image_content(path) for path in self._selected_photo_paths(preflight)],
            ],
            max_tokens=1200,
        )
        parsed = self._parse_json_text(response)
        return PlannerOutput(
            turn_index=turn_index,
            main_angle=parsed.get("main_angle", ""),
            covered_elements=list(parsed.get("covered_elements", [])),
            missing_elements=list(parsed.get("missing_elements", [])),
            question_strategy=parsed.get("question_strategy", "follow_up"),
            next_question=parsed.get("next_question", ""),
            evidence=list(parsed.get("evidence", [])),
        )

    def build_turn_question_artifact(self, planner: PlannerOutput) -> dict:
        payload = planner.to_dict()
        payload["keywords"] = extract_keywords(planner.main_angle)
        return payload

    def _image_content(self, path: Path) -> dict:
        media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            },
        }

    def _selected_photo_paths(self, preflight: dict) -> list[Path]:
        selected_ids = set(preflight.get("representative_photo_ids", []))
        results: list[Path] = []
        for item in preflight.get("photos", []):
            if item.get("media_id") in selected_ids:
                results.append(Path(item["source_path"]))
        return results[:5]

    def _parse_json_text(self, response: dict) -> dict:
        blocks = response.get("content", [])
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
