"""Instagram caption generator using Claude AI.

Generates short, engaging captions for Instagram carousel posts
based on the same interview data used for blog articles.
"""
from __future__ import annotations

import os
from pathlib import Path

from thohago.models import MediaAsset, PlannerOutput, ShopConfig, TranscriptArtifact

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass


class InstagramCaptionComposer:
    """Generate Instagram carousel captions from interview data."""

    def compose(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
    ) -> str:
        try:
            return self._compose_with_ai(shop, photos, transcripts, turn2_planner, turn3_planner)
        except Exception as exc:
            print(f"[InstagramCaptionComposer] AI failed ({exc}), using template")
            return self._compose_template(shop, photos, transcripts, turn2_planner)

    def _compose_with_ai(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
    ) -> str:
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
        api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or anthropic is None:
            raise RuntimeError("CLAUDE_API_KEY required")

        profile = getattr(shop, "profile", None) or {}
        profile_lines = [f"- 이름: {shop.display_name}"]
        if profile.get("business_type"):
            profile_lines.append(f"- 업종: {profile['business_type']}")
        if profile.get("location"):
            profile_lines.append(f"- 위치: {profile['location']}")
        if profile.get("key_services"):
            profile_lines.append(f"- 핵심 서비스: {', '.join(profile['key_services'])}")

        interview_text = "\n".join(
            f"[답변 {t.turn_index}]\n{t.transcript_text}" for t in transcripts
        )

        prompt = f"""인스타그램 캐러셀 게시물의 캡션을 작성해주세요.

## 샵 정보
{chr(10).join(profile_lines)}

## 이번 포스팅 핵심
{turn2_planner.main_angle}

## 사장님 인터뷰 원문
{interview_text}

## 캡션 작성 규칙

1. **분량**: 3~5줄 (150자 내외). 인스타그램은 짧고 임팩트 있게.
2. **톤**: 사장님 본인이 쓴 것처럼 자연스럽고 따뜻하게
3. **구조**:
   - 첫 줄: 눈길 끄는 한 문장 (인터뷰에서 가장 인상적인 포인트)
   - 중간: 핵심 내용 1~2문장
   - 마지막: 방문 유도 또는 간단한 마무리
4. **해시태그**: 캡션 끝에 관련 해시태그 7~15개
   - 업종 관련, 지역 관련, 서비스 관련 혼합
5. **금지사항**:
   - 이모지 과다 사용 금지 (최대 2~3개)
   - 원문에 없는 내용 창작 금지
   - "안녕하세요" 시작 금지

캡션만 출력. 설명이나 코드블록 없이."""

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def _compose_template(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
    ) -> str:
        """Simple template fallback when AI is unavailable."""
        lines = [
            turn2_planner.main_angle,
            "",
        ]
        # Use first transcript snippet
        if transcripts:
            snippet = transcripts[0].transcript_text[:100]
            if len(transcripts[0].transcript_text) > 100:
                snippet += "..."
            lines.append(f'"{snippet}"')
            lines.append("")

        profile = getattr(shop, "profile", None) or {}
        tags = [f"#{shop.display_name.replace(' ', '')}", f"#{shop.shop_id}"]
        if profile.get("business_type"):
            tags.append(f"#{profile['business_type']}")
        if profile.get("location"):
            tags.append(f"#{profile['location']}")
        for hint in shop.media_hints[:3]:
            tags.append(f"#{hint.replace(' ', '')}")
        lines.append(" ".join(tags))

        return "\n".join(lines)
