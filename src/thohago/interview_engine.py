from __future__ import annotations

from pathlib import Path
from typing import Iterable

from thohago.heuristics import (
    detect_main_angle,
    extract_keywords,
)
from thohago.models import MediaAsset, PlannerOutput, ShopConfig


TURN1_QUESTION_FALLBACK = "이 사진 속 상황이 궁금해요! 이날 어떤 일이 있었는지 처음부터 끝까지 쭉 들려주세요."


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

    def plan_turn1(self, preflight: dict) -> PlannerOutput:
        """Q1: Scene Anchor — heuristic fallback."""
        photos = preflight.get("photos", [])
        selected = [p for p in photos if p.get("selected_for_prompt")]
        anchor = selected[0] if selected else (photos[0] if photos else None)
        if anchor:
            details = anchor.get("preflight_analysis", {}).get("details", [])
            clue = details[0] if isinstance(details, list) and details else str(details) if details else ""
        else:
            clue = ""

        if clue:
            question = f"사진에서 {clue} 장면이 보이는데요, 이날 어떤 일이 있었는지 처음부터 끝까지 쭉 들려주세요."
        else:
            question = TURN1_QUESTION_FALLBACK

        return PlannerOutput(
            turn_index=1, main_angle="", covered_elements=[], missing_elements=[],
            question_strategy="scene_anchor", next_question=question,
            evidence=list(preflight.get("key_visual_evidence", []))[:2],
        )

    def plan_turn(self, turn_index: int, transcripts: Iterable[str], preflight: dict) -> PlannerOutput:
        """Q2: Detail Deepening / Q3: Owner's Perspective — heuristic fallback."""
        transcript_text = " ".join(transcripts)
        main_angle = detect_main_angle(transcript_text)
        evidence = list(preflight.get("key_visual_evidence", []))[:2]

        if turn_index == 2:
            question = "방금 말씀하신 장면에서 가장 기억에 남는 순간이 있다면, 그때 분위기나 반응을 좀 더 자세히 들려주세요."
            strategy = "detail_deepening"
        else:
            question = "이런 경험들을 하시면서 사장님 개인적으로 어떤 생각이 드셨어요?"
            strategy = "owner_perspective"

        return PlannerOutput(
            turn_index=turn_index, main_angle=main_angle, covered_elements=[], missing_elements=[],
            question_strategy=strategy, next_question=question, evidence=evidence,
        )

    def build_turn_question_artifact(self, planner: PlannerOutput) -> dict:
        payload = planner.to_dict()
        payload["keywords"] = extract_keywords(planner.main_angle)
        return payload

