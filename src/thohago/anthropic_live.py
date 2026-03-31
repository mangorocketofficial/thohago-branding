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

    def plan_turn1(self, preflight: dict) -> PlannerOutput:
        response = self.client.create_message(
            system=(
                "You are a shop interview planner for any industry. "
                "Create exactly one short, natural Korean question. "
                "Return valid JSON only with keys: main_angle, covered_elements, "
                "missing_elements, question_strategy, next_question, evidence."
            ),
            content=[
                {
                    "type": "text",
                    "text": (
                        "Q1: Scene Anchor (첫 질문)\n\n"
                        "사진을 보고, 사장님이 '그날 있었던 일'을 처음부터 끝까지 "
                        "시간순으로 풀어놓게 만드는 질문을 1개 생성하세요.\n\n"
                        "## 질문 목표\n"
                        "- 누가 왔는지, 어떻게 오게 됐는지, 무슨 일이 있었는지의 전체 흐름 확보\n"
                        "- 사진에서 보이는 구체적 단서(인원수, 장면 등)를 질문에 포함\n\n"
                        "## 질문 형식 예시\n"
                        "- '이 사진 속 상황이 궁금해요! 이날 어떤 일이 있었는지 "
                        "처음부터 끝까지 쭉 들려주세요.'\n\n"
                        "## 금지\n"
                        "- '어떤 점이 특별했나요?' 같은 평가/판단 유도 질문\n"
                        "- '차별점이 뭔가요?' 같은 설명 유도 질문\n\n"
                        f"사진 분석:\n{json.dumps(preflight, ensure_ascii=False)}\n"
                    ),
                },
                *[self._image_content(path) for path in self._selected_photo_paths(preflight)],
            ],
            max_tokens=1200,
        )
        parsed = self._parse_json_text(response)
        return PlannerOutput(
            turn_index=1,
            main_angle=parsed.get("main_angle", ""),
            covered_elements=[],
            missing_elements=[],
            question_strategy="scene_anchor",
            next_question=parsed.get("next_question", ""),
            evidence=list(parsed.get("evidence", [])),
        )

    def plan_turn(self, turn_index: int, transcripts: list[str], preflight: dict) -> PlannerOutput:
        transcript_blob = "\n".join(
            f"Turn {index}: {text}" for index, text in enumerate(transcripts, start=1)
        )

        if turn_index == 2:
            system_msg = (
                "You are a shop interview planner for any industry. "
                "Create exactly one short, natural Korean follow-up question. "
                "Return valid JSON only with keys: main_angle, question_strategy, next_question, evidence."
            )
            user_text = (
                "Q2: Detail Deepening (묘사 심화)\n\n"
                "사장님의 Q1 답변을 읽고, 그 안에서 가장 묘사할 가치가 있는 "
                "'한 순간'을 찾아서 그 순간의 감각적 디테일을 끌어내는 질문을 생성하세요.\n\n"
                "## 순간 선택 기준 (우선순위)\n"
                "1. 사람 간 상호작용이 있는 순간\n"
                "2. 예상과 달랐던 순간\n"
                "3. 분위기가 전환된 순간\n\n"
                "## 금지\n"
                "- Q1에서 이미 나온 내용을 다시 물어보기\n"
                "- 다른 주제로 넘어가기 (같은 장면 안에 머물러야 함)\n"
                "- '차별점', '비교' 같은 설명 유도\n\n"
                f"Q1 답변:\n{transcript_blob}\n\n"
                f"사진 분석:\n{json.dumps(preflight, ensure_ascii=False)}\n"
            )
            strategy = "detail_deepening"
        else:
            system_msg = (
                "You are a shop interview planner for any industry. "
                "Create exactly one short, natural Korean follow-up question. "
                "Return valid JSON only with keys: main_angle, question_strategy, next_question, evidence."
            )
            user_text = (
                "Q3: Owner's Perspective (사장님의 시선)\n\n"
                "사장님의 Q1, Q2 답변을 읽고, 이 경험에 대한 사장님의 개인적인 "
                "시선과 의미를 끌어내는 질문을 생성하세요.\n\n"
                "## 질문 목표\n"
                "- '좋았습니다'가 아닌, 왜 기억에 남는지, 어떤 생각이 들었는지\n"
                "- 사장님의 일과 삶의 맥락에서 이 경험이 갖는 의미\n\n"
                "## 질문 형식 예시\n"
                "- '오래 운영하시면서 많은 손님을 만나셨잖아요. 이번 경험은 좀 달랐나요?'\n"
                "- '이분들이 다른 손님과 다르게 기억에 남는 이유가 있으세요?'\n\n"
                "## 금지\n"
                "- '보람이 있으셨나요?' 같은 예/아니오 질문\n"
                "- '앞으로의 계획' 같은 미래 질문\n"
                "- 가게 홍보/설명으로 빠지는 질문\n\n"
                f"Q1+Q2 답변:\n{transcript_blob}\n\n"
                f"사진 분석:\n{json.dumps(preflight, ensure_ascii=False)}\n"
            )
            strategy = "owner_perspective"

        response = self.client.create_message(
            system=system_msg,
            content=[
                {"type": "text", "text": user_text},
                *[self._image_content(path) for path in self._selected_photo_paths(preflight)],
            ],
            max_tokens=1200,
        )
        parsed = self._parse_json_text(response)
        return PlannerOutput(
            turn_index=turn_index,
            main_angle=parsed.get("main_angle", ""),
            covered_elements=[],
            missing_elements=[],
            question_strategy=strategy,
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
