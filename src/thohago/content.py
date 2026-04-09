"""Gemini-based blog generation from owner interview transcripts."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from thohago.gemini_live import GeminiApiClient
from thohago.models import MediaAsset, PlannerOutput, ShopConfig, TranscriptArtifact

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        return None


class GeminiContentClient(Protocol):
    def generate_content(
        self,
        *,
        system_instruction: str,
        user_parts: list[dict],
        max_output_tokens: int = 1200,
        response_mime_type: str = "application/json",
        temperature: float = 0.3,
    ) -> dict: ...


class BlogComposer:
    def __init__(
        self,
        *,
        gemini_client: GeminiContentClient | None = None,
        gemini_model: str | None = None,
    ) -> None:
        self.gemini_client = gemini_client
        self.gemini_model = gemini_model

    def compose(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
        structure_mode: str,
        *,
        allow_fallback: bool = True,
    ) -> str:
        try:
            return self._compose_with_gemini(shop, photos, transcripts, turn2_planner, turn3_planner, structure_mode)
        except Exception as exc:
            if not allow_fallback:
                raise
            print(f"[BlogComposer] Gemini generation failed ({exc}), falling back to template")
            return self._compose_template(shop, photos, transcripts, turn2_planner, turn3_planner, structure_mode)

    def _compose_with_gemini(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
        structure_mode: str,
    ) -> str:
        client = self._resolve_gemini_client()
        response = client.generate_content(
            system_instruction=self._build_system_instruction(),
            user_parts=[
                {
                    "text": self._build_writer_brief(
                        shop=shop,
                        photos=photos,
                        transcripts=transcripts,
                        turn2_planner=turn2_planner,
                        turn3_planner=turn3_planner,
                        structure_mode=structure_mode,
                    )
                }
            ],
            max_output_tokens=3600,
            response_mime_type="text/plain",
            temperature=0.8,
        )
        return self._extract_text_response(response)

    def _resolve_gemini_client(self) -> GeminiContentClient:
        if self.gemini_client is not None:
            return self.gemini_client
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY required for Gemini blog generation")
        model = self.gemini_model or os.environ.get("THOHAGO_GEMINI_MODEL", "gemini-2.5-flash")
        return GeminiApiClient(api_key=api_key, model=model)

    def _extract_text_response(self, response: dict) -> str:
        candidates = response.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini response did not contain candidates: {response}")
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text.strip():
            raise RuntimeError(f"Gemini response did not contain text content: {response}")
        return text.strip()

    def _build_system_instruction(self) -> str:
        return (
            "You are a Korean blog writer for local business marketing. "
            "Write a new blog article from the owner's interview as the primary source material. "
            "The source of truth is limited to the interview, shop profile, and photo context provided. "
            "You must transform the interview into polished blog prose, not merely rearrange or paste the raw transcript. "
            "You may paraphrase, condense, expand transitions, and create a stronger reading flow, "
            "but you must not invent facts, prices, outcomes, customer feelings, or events not grounded in the provided source. "
            "Output HTML fragment only. Do not include markdown fences or explanations."
        )

    def _build_writer_brief(
        self,
        *,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
        structure_mode: str,
    ) -> str:
        profile_block = self._build_profile_block(shop)
        photo_block = self._build_photo_block(photos)
        interview_block = self._build_interview_block(transcripts)
        return (
            "원본 소스는 반드시 사장님 인터뷰입니다.\n"
            "인터뷰를 그대로 복붙하거나 순서만 바꾸지 말고, 블로그 독자가 읽기 좋은 새 글로 재창작하세요.\n"
            "다만 재창작은 문장과 구성의 수준에서만 허용되며, 사실과 뉘앙스는 반드시 인터뷰에 근거해야 합니다.\n"
            "인터뷰에 없는 사실, 가격, 효능, 후기, 고객 감정, 운영 정보는 새로 만들지 마세요.\n\n"
            f"[샵 프로필]\n{profile_block}\n\n"
            f"[이번 글의 메인 앵글]\n{turn2_planner.main_angle}\n\n"
            f"[구조 모드]\n{structure_mode}\n\n"
            f"[사진 컨텍스트]\n{photo_block}\n\n"
            f"[인터뷰 원문]\n{interview_block}\n\n"
            f"[보조 메모]\n- turn3 covered_elements: {', '.join(turn3_planner.covered_elements) or 'none'}\n"
            f"- turn3 missing_elements: {', '.join(turn3_planner.missing_elements) or 'none'}\n"
            f"- final perspective angle: {turn3_planner.question_strategy}\n\n"
            "[작성 목표]\n"
            "- 사장님이 블로그에 직접 올릴 수 있는 완성형 한국어 글을 작성하세요.\n"
            "- 인터뷰를 바탕으로 한 새로운 문장과 문단을 만드세요.\n"
            "- 도입부는 독자가 장면을 상상할 수 있게 시작하고, 중간은 경험과 포인트를 풀고, 마무리는 사장님 시선으로 정리하세요.\n"
            "- 사진은 자연스러운 위치에 2~4개 정도 배치하세요.\n\n"
            "[표현 규칙]\n"
            "- 기본 화자는 사장님이 독자에게 들려주듯 자연스럽고 따뜻한 톤입니다.\n"
            "- 인터뷰 원문을 그대로 길게 인용하지 마세요.\n"
            "- 고객 반응은 인터뷰나 관찰 정보에 나온 범위 안에서만 쓰세요.\n"
            "- 과장 광고 문구, 과도한 수식, 허위 Before/After 느낌의 표현은 금지합니다.\n\n"
            "[출력 포맷]\n"
            "- HTML fragment only\n"
            "- <h2>, <p>, <ul>, <b>, <span style=\"color:#A06C23\"> 정도만 사용\n"
            "- 사진 자리표시는 아래 형식을 정확히 사용\n"
            "  <div class=\"photo-placeholder\" data-photo-id=\"photo_1\">사진 설명</div>\n"
            "- 마지막에는 해시태그를 <p class=\"hashtags\">...</p> 형태로 넣으세요.\n"
        )

    def _build_profile_block(self, shop: ShopConfig) -> str:
        profile = getattr(shop, "profile", None) or {}
        if not profile:
            return f"- 상호명: {shop.display_name}"
        lines = [f"- 상호명: {shop.display_name}"]
        if profile.get("business_type"):
            lines.append(f"- 업종: {profile['business_type']}")
        if profile.get("location"):
            lines.append(f"- 위치: {profile['location']}")
        if profile.get("key_services"):
            lines.append(f"- 주요 서비스: {', '.join(profile['key_services'])}")
        if profile.get("booking_info"):
            lines.append(f"- 예약/이용 정보: {profile['booking_info']}")
        if profile.get("one_liner"):
            lines.append(f"- 한 줄 소개: {profile['one_liner']}")
        return "\n".join(lines)

    def _build_photo_block(self, photos: list[MediaAsset]) -> str:
        if not photos:
            return "- 사진 없음"
        lines: list[str] = []
        for asset in photos:
            analysis = asset.preflight_analysis
            details = analysis.get("details", [])
            detail_text = ", ".join(details) if isinstance(details, list) else str(details)
            lines.append(
                f"- {asset.media_id}: scene={analysis.get('scene', '')}, "
                f"details={detail_text}, mood={analysis.get('mood', '')}, "
                f"selected_for_prompt={asset.selected_for_prompt}"
            )
        return "\n".join(lines)

    def _build_interview_block(self, transcripts: list[TranscriptArtifact]) -> str:
        if not transcripts:
            return "- 인터뷰 없음"
        return "\n\n".join(
            f"[turn {transcript.turn_index}]\n{transcript.transcript_text}" for transcript in transcripts
        )

    def _compose_template(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
        structure_mode: str,
    ) -> str:
        main_angle = turn2_planner.main_angle
        lines = [
            f"# {shop.display_name} 경험 노트",
            "",
            f"이번 글의 중심 포인트는 {main_angle}입니다.",
            "인터뷰에서 나온 실제 이야기들을 바탕으로, 독자가 읽기 쉬운 흐름으로 다시 정리했습니다.",
            "",
        ]
        for index, transcript in enumerate(transcripts, start=1):
            asset = photos[index - 1] if index - 1 < len(photos) else None
            section_title = (
                asset.preflight_analysis["scene"].replace("_", " ").title()
                if asset is not None
                else f"Interview Turn {index}"
            )
            detail_text = ", ".join(asset.preflight_analysis.get("details", [])) if asset is not None else "인터뷰 핵심 포인트"
            lines.extend(
                [
                    f"## {section_title}",
                    f"사진 포인트: {detail_text}",
                    transcript.transcript_text,
                    "",
                ]
            )
        lines.extend(
            [
                "## 마무리",
                f"이번 글은 `{structure_mode}` 구조로 정리했고, 다음 세트에서는 `{turn3_planner.question_strategy}` 방향의 디테일을 더 살릴 수 있습니다.",
                "",
                f"#헤드스파 #{shop.shop_id} #고객경험 #사장님이야기",
                "",
            ]
        )
        return "\n".join(lines)
