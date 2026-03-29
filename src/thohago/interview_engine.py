from __future__ import annotations

from pathlib import Path
from typing import Iterable

from thohago.heuristics import (
    choose_missing_elements,
    choose_question_strategy,
    detect_elements,
    detect_main_angle,
    extract_keywords,
    score_specificity,
)
from thohago.models import MediaAsset, PlannerOutput, ShopConfig


TURN1_QUESTION = "이번 포스팅에 대해 이야기해볼까요? 어떤 상황이었고, 무엇이 가장 인상깊으셨나요?"


class HeuristicMultimodalInterviewEngine:
    """Deterministic stand-in for the multimodal interview engine during replay verification."""

    def build_preflight(self, shop: ShopConfig, photos: list[Path], videos: list[Path]) -> tuple[dict, list[MediaAsset], list[MediaAsset]]:
        ordered_photos = sorted(photos, key=lambda path: path.name)
        photo_assets: list[MediaAsset] = []
        scenes = ["arrival", "consultation", "signature_step", "result", "detail"]
        for index, path in enumerate(ordered_photos, start=1):
            scene = scenes[min(index - 1, len(scenes) - 1)]
            detail = shop.media_hints[min(index - 1, len(shop.media_hints) - 1)] if shop.media_hints else "captured service atmosphere"
            photo_assets.append(
                MediaAsset(
                    media_id=f"photo_{index}",
                    kind="photo",
                    source_path=path,
                    relative_source_path=str(path),
                    experience_order=index,
                    preflight_analysis={
                        "scene": scene,
                        "details": [detail],
                        "mood": "relaxing" if "candle" in detail.lower() else "professional",
                    },
                    selected_for_prompt=index <= 3,
                )
            )

        ordered_videos = sorted(videos, key=lambda path: path.name)
        video_assets: list[MediaAsset] = []
        for index, path in enumerate(ordered_videos, start=1):
            video_assets.append(
                MediaAsset(
                    media_id=f"video_{index}",
                    kind="video",
                    source_path=path,
                    relative_source_path=str(path),
                    experience_order=index,
                    preflight_analysis={
                        "scene": "treatment_mood",
                        "orientation": "vertical",
                        "details": ["service mood clip"],
                    },
                    selected_for_prompt=index == 1,
                    reels_eligible=True,
                    duration_sec=13.3,
                )
            )

        preflight = {
            "model_mode": "heuristic_multimodal_replay",
            "experience_sequence": [asset.media_id for asset in photo_assets],
            "structure_mode": "narrative_flow" if len(photo_assets) >= 3 else "key_moments",
            "representative_photo_ids": [asset.media_id for asset in photo_assets if asset.selected_for_prompt],
            "key_visual_evidence": list(shop.media_hints) or ["service atmosphere", "customer relaxation"],
            "question_focus_candidates": ["customer reaction", "differentiator", "entry_channel"],
            "photos": [asset.to_dict() for asset in photo_assets],
            "videos": [asset.to_dict() for asset in video_assets],
        }
        return preflight, photo_assets, video_assets

    def plan_turn(
        self,
        turn_index: int,
        transcripts: Iterable[str],
        preflight: dict,
    ) -> PlannerOutput:
        transcript_text = " ".join(transcripts)
        main_angle = detect_main_angle(transcript_text)
        covered_elements = detect_elements(transcript_text)
        missing_elements = choose_missing_elements(covered_elements)
        specificity_score = score_specificity(transcript_text)
        strategy = choose_question_strategy(turn_index, covered_elements, specificity_score)
        evidence = list(preflight.get("key_visual_evidence", []))[:2]
        next_question = self._render_question(strategy, main_angle, evidence)
        return PlannerOutput(
            turn_index=turn_index,
            main_angle=main_angle,
            covered_elements=covered_elements,
            missing_elements=missing_elements,
            question_strategy=strategy,
            next_question=next_question,
            evidence=evidence,
        )

    def _render_question(self, strategy: str, main_angle: str, evidence: list[str]) -> str:
        clue = evidence[0] if evidence else "사진 속 분위기"
        if strategy == "reaction_probe":
            return f"사진에서 {clue} 장면이 인상적인데요, 그 순간 고객분들이 가장 좋다고 반응하셨던 포인트는 뭐였어요?"
        if strategy == "differentiator_probe":
            return f"사진처럼 {clue}가 보이는데, 다른 곳이 아니라 여기만의 차별점은 뭐라고 설명하시겠어요?"
        if strategy == "entry_channel_probe":
            return "이번 고객분들은 어떻게 매장을 알고 예약까지 하시게 됐어요?"
        if strategy == "location_probe":
            return "매장 위치나 동선 때문에 고객분들이 편하게 느끼는 포인트가 있었나요?"
        return f"{main_angle}라는 이야기가 이미 좋은데요, 사진의 {clue} 장면에서 실제 분위기는 어땠는지 더 들려주실 수 있을까요?"

    def build_turn_question_artifact(self, planner: PlannerOutput) -> dict:
        payload = planner.to_dict()
        payload["keywords"] = extract_keywords(planner.main_angle)
        return payload

