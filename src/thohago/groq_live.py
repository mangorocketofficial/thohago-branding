from __future__ import annotations

import base64
import json
import mimetypes
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from thohago.heuristics import extract_keywords
from thohago.models import MediaAsset, PlannerOutput, ShopConfig, TranscriptProviderResult


class GroqApiClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.user_agent = "thohago-phase1/0.1 (+https://local.dev)"

    def chat_completion(self, payload: dict) -> dict:
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))

    def audio_transcription(self, file_path: Path, model: str, language: str = "ko") -> dict:
        boundary = f"----thohago-{uuid.uuid4().hex}"
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = bytearray()

        def add_field(name: str, value: str) -> None:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(value.encode("utf-8"))
            body.extend(b"\r\n")

        add_field("model", model)
        add_field("language", language)
        add_field("response_format", "verbose_json")

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        request = Request(
            f"{self.base_url}/audio/transcriptions",
            data=bytes(body),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": self.user_agent,
            },
        )
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))


class GroqTranscriptionProvider:
    def __init__(self, client: GroqApiClient, model: str) -> None:
        self.client = client
        self.model = model

    def transcribe_audio(self, audio_path: Path, language: str = "ko") -> TranscriptProviderResult:
        payload = self.client.audio_transcription(audio_path, model=self.model, language=language)
        return TranscriptProviderResult(text=(payload.get("text") or "").strip(), metadata=payload)


class GroqMultimodalInterviewEngine:
    def __init__(self, client: GroqApiClient, model: str) -> None:
        self.client = client
        self.model = model

    def build_preflight(self, shop: ShopConfig, photos: list[Path], videos: list[Path]) -> tuple[dict, list[MediaAsset], list[MediaAsset]]:
        selected_photos = photos[:5]
        response = self.client.chat_completion(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You analyze beauty-shop session photos for a content pipeline. "
                            "Return JSON only. Decide a structure_mode, best-fit experience ordering, "
                            "key visual evidence, and compact per-photo annotations useful for interview planning."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analyze these photos for a Korean beauty shop marketing interview.\n"
                                    "Return JSON with keys: structure_mode, key_visual_evidence, "
                                    "question_focus_candidates, photo_annotations.\n"
                                    "photo_annotations must be an array of objects with: "
                                    "photo_index, scene, details, mood, selected_for_prompt.\n"
                                    f"Shop hints: {', '.join(shop.media_hints) if shop.media_hints else 'none'}"
                                ),
                            },
                            *[self._image_message(path) for path in selected_photos],
                        ],
                    },
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }
        )
        raw_text = response["choices"][0]["message"]["content"]
        parsed = json.loads(raw_text)

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

        experience_sequence = [asset.media_id for asset in photo_assets]
        preflight = {
            "model_mode": f"groq_chat_completions:{self.model}",
            "structure_mode": parsed.get("structure_mode", "key_moments"),
            "experience_sequence": experience_sequence,
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
        prompt_photo_paths = self._selected_photo_paths(preflight)
        transcript_blob = "\n".join(
            f"Turn {index}: {text}" for index, text in enumerate(transcripts, start=1)
        )
        response = self.client.chat_completion(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Korean beauty-shop interview planner. "
                            "You must create one short, natural Korean follow-up question. "
                            "Return JSON only with keys: main_angle, covered_elements, missing_elements, "
                            "question_strategy, next_question, evidence."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"Current turn to generate: Turn {turn_index}\n"
                                    f"Interview transcripts so far:\n{transcript_blob}\n\n"
                                    f"Media preflight summary:\n{json.dumps(preflight, ensure_ascii=False)}\n\n"
                                    "Make the next question concrete and short. Ask about the highest-value missing element. "
                                    "Keep it answerable in under one minute."
                                ),
                            },
                            *[self._image_message(path) for path in prompt_photo_paths],
                        ],
                    },
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            }
        )
        parsed = json.loads(response["choices"][0]["message"]["content"])
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

    def _image_message(self, path: Path) -> dict:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{encoded}"},
        }

    def _selected_photo_paths(self, preflight: dict) -> list[Path]:
        selected_ids = set(preflight.get("representative_photo_ids", []))
        results: list[Path] = []
        for item in preflight.get("photos", []):
            if item.get("media_id") in selected_ids:
                results.append(Path(item["source_path"]))
        return results[:5]
