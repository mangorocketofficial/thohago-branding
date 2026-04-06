"""Threads caption generator using Claude AI.

Threads posts are shorter and more conversational than Instagram.
Max 500 characters recommended, no hashtag spam.
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


class ThreadsCaptionComposer:
    """Generate short, conversational Threads captions."""

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
            print(f"[ThreadsCaptionComposer] AI failed ({exc}), using template")
            return self._compose_template(shop, transcripts, turn2_planner)

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

        interview_text = "\n".join(
            f"[답변 {t.turn_index}]\n{t.transcript_text}" for t in transcripts
        )

        prompt = f"""Threads 게시물 캡션을 작성해주세요.

## 샵 정보
{chr(10).join(profile_lines)}

## 이번 포스팅 핵심
{turn2_planner.main_angle}

## 사장님 인터뷰 원문
{interview_text}

## Threads 캡션 규칙

1. **분량**: 2~3줄, 최대 300자. Threads는 짧고 캐주얼하게.
2. **톤**: 친구한테 얘기하듯 편하고 자연스럽게. 인스타보다 더 가볍게.
3. **구조**:
   - 인터뷰에서 가장 흥미로운 포인트 하나를 잡아서
   - 짧고 임팩트 있게 전달
   - 해시태그 없음 (Threads는 해시태그 문화가 아님)
4. **금지사항**:
   - 해시태그 금지
   - 이모지 과다 금지 (최대 1~2개)
   - 광고 느낌 금지
   - 원문에 없는 내용 창작 금지

캡션만 출력. 설명 없이."""

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def _compose_template(
        self,
        shop: ShopConfig,
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
    ) -> str:
        lines = [turn2_planner.main_angle]
        if transcripts:
            snippet = transcripts[0].transcript_text[:80]
            if len(transcripts[0].transcript_text) > 80:
                snippet += "..."
            lines.append(f'"{snippet}"')
        lines.append(f"- {shop.display_name}")
        return "\n".join(lines)
