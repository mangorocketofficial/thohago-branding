"""Blog content generation using Claude AI.

Two-layer design:
1. Shop profile (static, registered once) — who/where/what
2. Post type detection (per interview) — episode/service-intro/seasonal

Claude's role: EDITOR, not writer. Structure the owner's words, don't rewrite them.
"""
from __future__ import annotations

import json
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


class BlogComposer:
    def compose(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
        structure_mode: str,
    ) -> str:
        try:
            return self._compose_with_ai(shop, photos, transcripts, turn2_planner, turn3_planner, structure_mode)
        except Exception as exc:
            print(f"[BlogComposer] AI generation failed ({exc}), falling back to template")
            return self._compose_template(shop, photos, transcripts, turn2_planner, turn3_planner, structure_mode)

    def _build_profile_block(self, shop: ShopConfig) -> str:
        profile = getattr(shop, "profile", None) or {}
        if not profile:
            return f"- 이름: {shop.display_name}"
        lines = [f"- 이름: {shop.display_name}"]
        if profile.get("business_type"):
            lines.append(f"- 업종: {profile['business_type']}")
        if profile.get("location"):
            lines.append(f"- 위치: {profile['location']}")
        if profile.get("key_services"):
            lines.append(f"- 핵심 서비스: {', '.join(profile['key_services'])}")
        if profile.get("booking_info"):
            lines.append(f"- 예약/이용: {profile['booking_info']}")
        if profile.get("one_liner"):
            lines.append(f"- 한줄 소개: {profile['one_liner']}")
        return "\n".join(lines)

    def _compose_with_ai(
        self,
        shop: ShopConfig,
        photos: list[MediaAsset],
        transcripts: list[TranscriptArtifact],
        turn2_planner: PlannerOutput,
        turn3_planner: PlannerOutput,
        structure_mode: str,
    ) -> str:
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
        api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or anthropic is None:
            raise RuntimeError("CLAUDE_API_KEY required for AI blog generation")

        photo_info = []
        for asset in photos:
            analysis = asset.preflight_analysis
            photo_info.append(
                f"- {asset.media_id} (순서 {asset.experience_order}): "
                f"장면={analysis.get('scene', '')}, "
                f"디테일={analysis.get('details', '')}, "
                f"분위기={analysis.get('mood', '')}"
            )

        interview_qa = []
        for t in transcripts:
            interview_qa.append(f"[답변 {t.turn_index}]\n{t.transcript_text}")

        profile_block = self._build_profile_block(shop)

        prompt = f"""당신은 블로그 **편집자**입니다. 작가가 아닙니다.
사장님이 말한 내용을 블로그 형식으로 **정리**하는 것이 목적입니다.

## 샵 프로필 (시스템 등록 정보)
{profile_block}

## 이번 글의 핵심 angle
{turn2_planner.main_angle}

## 사진 정보
{chr(10).join(photo_info)}

## 사장님 인터뷰 원문 (이것이 글의 재료입니다)
{chr(10).join(interview_qa)}

---

## 1단계: 글 유형 판단 (먼저 판단하고 구조를 결정하세요)

인터뷰 내용을 보고 아래 중 어떤 유형인지 먼저 판단하세요:

### 에피소드형: 특정 손님, 특정 사건 중심
- 구조: 상황 설정 -> 구체적 장면/디테일 -> 사장님 감상
- 샵 프로필 정보는 글 하단에 간략히 붙이기
- 예: "필리핀 손님 5명이 왔다", "단골 고객이 감동받은 사연"

### 서비스 소개형: 코스, 시술, 메뉴 설명 중심
- 구조: 뭘 해주는 곳인지 -> 뭐가 다른지 -> 이용 방법
- 샵 프로필 정보를 본문에 자연스럽게 포함
- 예: "우리 샵 코스 소개", "신메뉴 출시"

### 시즌/이벤트형: 특정 시기, 프로모션 중심
- 구조: 시즌 맥락 -> 이벤트 내용 -> 참여 방법
- 샵 프로필 정보를 본문에 자연스럽게 포함
- 예: "크리스마스 이벤트", "여름 시즌 한정"

## 2단계: 편집 규칙

### 반드시 지킬 것
- 사장님의 원문 표현을 최대한 그대로 사용
- 유형에 맞는 구조로 재배치 (인터뷰 순서를 그대로 따르지 마세요!)
- 사진을 적절한 위치에 배치
- 화자는 사장님 본인
- 인터뷰 목적이나 메타 발언은 제외

### 절대 하지 말 것
- 없던 감정이나 감탄사 추가 금지
- 이모지 금지
- 원문에 없는 내용 창작 금지
- 문장을 예쁘게 다듬으려고 하지 마세요
- 매번 "안녕하세요 OO를 운영하고 있는..."으로 시작하지 마세요

### 볼드/색상 사용 기준
- 볼드: 사장님이 강조한 핵심 표현에만
- 색상: 가게 이름, 핵심 서비스명에만 최소한으로
- 해시태그 포함

## 출력 형식

네이버 블로그 HTML:
- 사진: `<div class="photo-placeholder" data-photo-id="photo_1">사진 설명</div>`
- 볼드: `<b>텍스트</b>`
- 색상: `<span style="color:#FF6B6B">텍스트</span>`
- 제목: `<h2>제목</h2>`
- 구분선: `<hr>`
- 해시태그: `<p class="hashtags">#태그1 #태그2</p>`

HTML만 출력. 코드블록이나 설명 없이."""

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

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
            f"# {shop.display_name} 경험 세트 기록",
            "",
            f"이번 포스팅의 핵심은 {main_angle}입니다.",
            "사진과 실제 상담 내용을 바탕으로 손님이 어떤 흐름으로 경험했는지 정리했습니다.",
            "",
        ]
        for asset, transcript in zip(photos, transcripts, strict=False):
            lines.extend(
                [
                    f"## {asset.preflight_analysis['scene'].replace('_', ' ').title()}",
                    f"사진 포인트: {', '.join(asset.preflight_analysis.get('details', []))}",
                    transcript.transcript_text,
                    "",
                ]
            )
        lines.extend(
            [
                "## 마무리",
                f"이번 글은 `{structure_mode}` 구조로 정리했고, 다음 세트에서는 `{turn3_planner.question_strategy}` 방향의 피드백을 더 반영할 수 있습니다.",
                "",
                f"#헤드스파 #{shop.shop_id} #맞춤관리 #고객경험",
                "",
            ]
        )
        return "\n".join(lines)
