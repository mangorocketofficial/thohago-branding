from __future__ import annotations

from thohago.models import MediaAsset, PlannerOutput, ShopConfig, TranscriptArtifact


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

