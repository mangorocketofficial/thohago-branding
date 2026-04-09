from __future__ import annotations

import unittest
from pathlib import Path

from thohago.content import BlogComposer
from thohago.models import MediaAsset, PlannerOutput, PublishConfig, ShopConfig, TranscriptArtifact


class FakeGeminiClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict] = []

    def generate_content(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": self.text},
                        ]
                    }
                }
            ]
        }


class FailingGeminiClient:
    def generate_content(self, **kwargs) -> dict:
        raise RuntimeError("gemini unavailable")


class BlogComposerTests(unittest.TestCase):
    def test_compose_uses_gemini_writer_prompt_based_on_interview_source(self) -> None:
        fake_client = FakeGeminiClient("<h2>새로운 블로그 글</h2><p>인터뷰를 재가공한 본문입니다.</p>")
        composer = BlogComposer(gemini_client=fake_client)

        result = composer.compose(
            shop=self._shop(),
            photos=self._photos(),
            transcripts=self._transcripts(),
            turn2_planner=self._turn2_planner(),
            turn3_planner=self._turn3_planner(),
            structure_mode="narrative_flow",
        )

        self.assertEqual(result, "<h2>새로운 블로그 글</h2><p>인터뷰를 재가공한 본문입니다.</p>")
        self.assertEqual(len(fake_client.calls), 1)
        call = fake_client.calls[0]
        self.assertEqual(call["response_mime_type"], "text/plain")
        self.assertEqual(call["temperature"], 0.8)
        self.assertIn("new blog article from the owner's interview", call["system_instruction"])

        prompt = call["user_parts"][0]["text"]
        self.assertIn("원본 소스는 반드시 사장님 인터뷰입니다.", prompt)
        self.assertIn("인터뷰를 그대로 복붙하거나 순서만 바꾸지 말고", prompt)
        self.assertIn("첫 번째 인터뷰 답변", prompt)
        self.assertIn("두 번째 인터뷰 답변", prompt)
        self.assertIn("세 번째 인터뷰 답변", prompt)
        self.assertIn("상담 데스크", prompt)
        self.assertIn("사장님 시선", prompt)

    def test_compose_falls_back_to_template_when_gemini_fails(self) -> None:
        composer = BlogComposer(gemini_client=FailingGeminiClient())

        result = composer.compose(
            shop=self._shop(),
            photos=self._photos(),
            transcripts=self._transcripts(),
            turn2_planner=self._turn2_planner(),
            turn3_planner=self._turn3_planner(),
            structure_mode="narrative_flow",
        )

        self.assertIn("첫 번째 인터뷰 답변", result)
        self.assertIn("두 번째 인터뷰 답변", result)
        self.assertIn("세 번째 인터뷰 답변", result)
        self.assertIn("경험 노트", result)

    def _shop(self) -> ShopConfig:
        return ShopConfig(
            shop_id="demo_shop_2",
            display_name="Demo Shop 2",
            invite_tokens=[],
            telegram_chat_ids=[],
            publish=PublishConfig(provider="mock_naver", targets=["naver_blog"]),
            media_hints=["상담 데스크", "제품 진열대"],
            profile={
                "business_type": "헤드 스파",
                "location": "부산 수영구",
                "key_services": ["두피 진단", "헤드 스파"],
                "one_liner": "편안한 휴식과 관리",
            },
        )

    def _photos(self) -> list[MediaAsset]:
        return [
            MediaAsset(
                media_id="photo_1",
                kind="photo",
                source_path=Path("raw/photo_01.jpg"),
                relative_source_path="raw/photo_01.jpg",
                experience_order=1,
                preflight_analysis={"scene": "consultation", "details": ["상담 데스크"], "mood": "calm"},
                selected_for_prompt=True,
            ),
            MediaAsset(
                media_id="photo_2",
                kind="photo",
                source_path=Path("raw/photo_02.jpg"),
                relative_source_path="raw/photo_02.jpg",
                experience_order=2,
                preflight_analysis={"scene": "result", "details": ["관리 직후"], "mood": "warm"},
                selected_for_prompt=True,
            ),
        ]

    def _transcripts(self) -> list[TranscriptArtifact]:
        return [
            TranscriptArtifact(turn_index=1, source_path=Path("turn1.txt"), transcript_text="첫 번째 인터뷰 답변"),
            TranscriptArtifact(turn_index=2, source_path=Path("turn2.txt"), transcript_text="두 번째 인터뷰 답변"),
            TranscriptArtifact(turn_index=3, source_path=Path("turn3.txt"), transcript_text="세 번째 인터뷰 답변"),
        ]

    def _turn2_planner(self) -> PlannerOutput:
        return PlannerOutput(
            turn_index=2,
            main_angle="처음 상담에서 안심감을 주는 경험",
            covered_elements=["상담", "안심감"],
            missing_elements=[],
            question_strategy="detail_deepening",
            next_question="두 번째 질문",
            evidence=["상담 데스크"],
        )

    def _turn3_planner(self) -> PlannerOutput:
        return PlannerOutput(
            turn_index=3,
            main_angle="사장님 시선의 정성",
            covered_elements=["정성", "분위기"],
            missing_elements=["재방문"],
            question_strategy="owner_perspective",
            next_question="세 번째 질문",
            evidence=["관리 직후"],
        )


if __name__ == "__main__":
    unittest.main()
