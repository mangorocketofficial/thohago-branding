"""Test blog generation with Claude AI and create HTML preview."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from thohago.content import BlogComposer
from thohago.models import MediaAsset, PlannerOutput, ShopConfig, TranscriptArtifact

PROJ_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_PATH = PROJ_ROOT / "runs" / "sisun8082" / "live_20260329T005645-20260329T005645Z" / "generated" / "content_bundle.json"
INTERVIEW_PATH = PROJ_ROOT / "client" / "sisun8082" / "2026_03_27" / "interview" / "interview_transcripts.md"
OUT_DIR = Path(__file__).resolve().parent / "blog_preview"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load content bundle
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))

    # Reconstruct objects from bundle
    shop = ShopConfig(
        shop_id=bundle["shop"]["shop_id"],
        display_name=bundle["shop"]["display_name"],
        invite_tokens=[],
        telegram_chat_ids=[],
        publish=type("Pub", (), {"provider": "mock_naver", "targets": bundle["shop"]["publish_targets"]})(),
        media_hints=[],
        sample_sessions={},
    )

    photos = []
    for p in bundle["photos"]:
        photos.append(MediaAsset(
            media_id=p["media_id"],
            kind=p["kind"],
            source_path=Path(p["source_path"]),
            relative_source_path=p["relative_source_path"],
            experience_order=p["experience_order"],
            preflight_analysis=p["preflight_analysis"],
            selected_for_prompt=p["selected_for_prompt"],
        ))

    # Use full interview transcripts instead of short bundle transcripts
    interview_text = INTERVIEW_PATH.read_text(encoding="utf-8") if INTERVIEW_PATH.exists() else ""

    # Split interview into segments for richer transcripts
    transcripts = [
        TranscriptArtifact(turn_index=1, source_path=Path(""), transcript_text=bundle["interview"]["turn1_transcript"]),
        TranscriptArtifact(turn_index=2, source_path=Path(""), transcript_text=bundle["interview"]["turn2_transcript"]),
        TranscriptArtifact(turn_index=3, source_path=Path(""), transcript_text=bundle["interview"]["turn3_transcript"]),
    ]

    # Also provide full interview as extra context by appending to turn1
    if interview_text:
        transcripts[0] = TranscriptArtifact(
            turn_index=1,
            source_path=Path(""),
            transcript_text=interview_text,
        )

    turn2_planner = PlannerOutput(
        turn_index=2,
        main_angle=bundle["interview"]["main_angle"],
        covered_elements=bundle["interview"]["covered_elements"],
        missing_elements=bundle["interview"]["missing_elements"],
        question_strategy="",
        next_question="",
        evidence=[],
    )
    turn3_planner = PlannerOutput(
        turn_index=3,
        main_angle="",
        covered_elements=bundle["interview"]["covered_elements"],
        missing_elements=bundle["interview"]["missing_elements"],
        question_strategy="",
        next_question="",
        evidence=[],
    )

    # Generate blog
    sys.stdout.reconfigure(encoding="utf-8")
    print("Generating blog with Claude AI...")
    composer = BlogComposer()
    blog_html = composer.compose(
        shop=shop,
        photos=photos,
        transcripts=transcripts,
        turn2_planner=turn2_planner,
        turn3_planner=turn3_planner,
        structure_mode=bundle["structure_mode"],
    )

    # Save raw blog HTML
    raw_path = OUT_DIR / "blog_content.html"
    raw_path.write_text(blog_html, encoding="utf-8")
    print(f"Blog content saved: {raw_path}")

    # Wrap in preview HTML page
    preview_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{shop.display_name} - 블로그 미리보기</title>
    <style>
        body {{
            max-width: 720px;
            margin: 0 auto;
            padding: 20px;
            font-family: 'Noto Sans KR', -apple-system, sans-serif;
            line-height: 1.8;
            color: #333;
            background: #fafafa;
        }}
        .preview-banner {{
            background: #4a90d9;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 24px;
            font-size: 14px;
        }}
        .preview-banner b {{
            font-size: 16px;
        }}
        .blog-content {{
            background: white;
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .blog-content h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #eee;
            padding-bottom: 8px;
            margin-top: 32px;
        }}
        .blog-content blockquote {{
            border-left: 4px solid #FF6B6B;
            margin: 16px 0;
            padding: 12px 20px;
            background: #fff5f5;
            border-radius: 0 8px 8px 0;
            font-style: italic;
            color: #555;
        }}
        .blog-content .photo-placeholder {{
            background: #f0f0f0;
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 40px 20px;
            text-align: center;
            margin: 20px 0;
            color: #888;
            font-size: 14px;
        }}
        .blog-content .photo-placeholder::before {{
            content: "📷 ";
        }}
        .blog-content hr {{
            border: none;
            border-top: 1px solid #eee;
            margin: 24px 0;
        }}
        .blog-content .hashtags {{
            color: #4a90d9;
            font-size: 14px;
            margin-top: 24px;
        }}
        .blog-content b {{
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="preview-banner">
        <b>블로그 미리보기</b> | {shop.display_name} | 승인 대기 중
    </div>
    <div class="blog-content">
        {blog_html}
    </div>
</body>
</html>"""

    preview_path = OUT_DIR / "index.html"
    preview_path.write_text(preview_html, encoding="utf-8")
    print(f"Preview HTML saved: {preview_path}")
    print(f"\nOpen in browser: file:///{preview_path.as_posix()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
