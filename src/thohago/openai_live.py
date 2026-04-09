from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from urllib.request import Request, urlopen

from thohago.heuristics import extract_keywords
from thohago.models import MediaAsset, PlannerOutput, ShopConfig


class OpenAIChatCompletionsClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.user_agent = "thohago-phase1/0.1 (+https://local.dev)"

    def create_completion(self, system: str, user_content: list[dict], max_tokens: int = 1200) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        request = Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        with urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))


class OpenAIMultimodalInterviewEngine:
    def __init__(self, client: OpenAIChatCompletionsClient) -> None:
        self.client = client

    def build_preflight(self, shop: ShopConfig, photos: list[Path], videos: list[Path]) -> tuple[dict, list[MediaAsset], list[MediaAsset]]:
        selected_photos = photos[:5]
        response = self.client.create_completion(
            system=(
                "You analyze beauty-shop session photos for a Korean content pipeline. "
                "Return valid JSON only."
            ),
            user_content=[
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
        parsed = json.loads(response["choices"][0]["message"]["content"])
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
            "model_mode": f"openai_chat_completions:{self.client.model}",
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
        response = self.client.create_completion(
            system="You are a shop interview planner for any industry. Create one short, natural Korean question. Return valid JSON with keys: main_angle, question_strategy, next_question, evidence.",
            user_content=[
                {"type": "text", "text": (
                    "Q1: Scene Anchor\n\n"
                    "사진을 보고, 사장님이 '그날 있었던 일'을 처음부터 끝까지 풀어놓게 만드는 질문을 1개 생성하세요.\n"
                    "사진에서 보이는 구체적 단서를 질문에 포함하세요.\n"
                    "평가/판단 유도 질문 금지. 설명 유도 질문 금지.\n\n"
                    "화자 규칙:\n"
                    "- 인터뷰 대상은 사장님입니다.\n"
                    "- 사장님이 직접 보거나 들었거나 기억하는 장면만 답할 수 있어야 합니다.\n"
                    "- 고객의 마음속 감정이나 생각을 단정해서 직접 묻지 마세요.\n\n"
                    f"사진 분석:\n{json.dumps(preflight, ensure_ascii=False)}\n"
                )},
                *[self._image_content(path) for path in self._selected_photo_paths(preflight)],
            ],
            max_tokens=1200,
        )
        parsed = json.loads(response["choices"][0]["message"]["content"])
        return PlannerOutput(turn_index=1, main_angle=parsed.get("main_angle", ""), covered_elements=[], missing_elements=[], question_strategy="scene_anchor", next_question=parsed.get("next_question", ""), evidence=list(parsed.get("evidence", [])))

    def plan_turn(self, turn_index: int, transcripts: list[str], preflight: dict) -> PlannerOutput:
        transcript_blob = "\n".join(f"Turn {i}: {t}" for i, t in enumerate(transcripts, 1))
        if turn_index == 2:
            user_text = (
                "Q2: Detail Deepening\n\nQ1 답변에서 가장 묘사할 가치가 있는 '한 순간'을 찾아 감각적 디테일을 끌어내는 질문을 생성하세요.\n"
                "같은 장면 안에 머물러야 합니다. 다른 주제로 넘어가기 금지.\n\n"
                "화자 규칙:\n"
                "- 인터뷰 대상은 사장님입니다.\n"
                "- 사장님이 직접 본 고객 반응, 표정, 대화, 행동, 혹은 사장님이 직접 신경 쓴 포인트만 물어야 합니다.\n"
                "- 고객이 어떤 느낌이었는지, 무슨 생각을 했는지처럼 고객 내면 상태를 직접 묻지 마세요.\n"
                "- 고객 감정이 필요하면 '사장님이 보시기에 고객 반응은 어땠나요?'처럼 관찰 가능한 방식으로만 물으세요.\n\n"
                f"Q1 답변:\n{transcript_blob}\n\n사진 분석:\n{json.dumps(preflight, ensure_ascii=False)}\n"
            )
            strategy = "detail_deepening"
        else:
            user_text = (
                "Q3: Owner's Perspective\n\nQ1+Q2 답변을 읽고, 이 경험에 대한 사장님의 개인적 시선과 의미를 끌어내는 질문을 생성하세요.\n"
                "예/아니오 질문 금지. 미래 질문 금지. 홍보/설명 유도 금지.\n\n"
                "화자 규칙:\n"
                "- 인터뷰 대상은 사장님입니다.\n"
                "- 사장님 본인의 생각, 판단, 운영 철학, 기억을 묻는 질문이어야 합니다.\n"
                "- 고객의 속마음이나 감정을 대신 추측하게 만들지 마세요.\n\n"
                f"Q1+Q2 답변:\n{transcript_blob}\n\n사진 분석:\n{json.dumps(preflight, ensure_ascii=False)}\n"
            )
            strategy = "owner_perspective"
        response = self.client.create_completion(
            system="You are a shop interview planner for any industry. Create one short, natural Korean follow-up question. Return valid JSON with keys: main_angle, question_strategy, next_question, evidence.",
            user_content=[
                {"type": "text", "text": user_text},
                *[self._image_content(path) for path in self._selected_photo_paths(preflight)],
            ],
            max_tokens=1200,
        )
        parsed = json.loads(response["choices"][0]["message"]["content"])
        return PlannerOutput(turn_index=turn_index, main_angle=parsed.get("main_angle", ""), covered_elements=[], missing_elements=[], question_strategy=strategy, next_question=parsed.get("next_question", ""), evidence=list(parsed.get("evidence", [])))

    def build_turn_question_artifact(self, planner: PlannerOutput) -> dict:
        payload = planner.to_dict()
        payload["keywords"] = extract_keywords(planner.main_angle)
        return payload

    def _image_content(self, path: Path) -> dict:
        media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}",
            },
        }

    def _selected_photo_paths(self, preflight: dict) -> list[Path]:
        selected_ids = set(preflight.get("representative_photo_ids", []))
        results: list[Path] = []
        for item in preflight.get("photos", []):
            if item.get("media_id") in selected_ids:
                results.append(Path(item["source_path"]))
        return results[:5]
