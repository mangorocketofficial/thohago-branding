"""Source-First Instagram Carousel Generator.

Pipeline:
1. Claude generates carousel narrative + slide-photo-text matching
2. Output instagram_carousel_edit_spec.json (same format as existing renderer)
3. Run existing render_instagram_carousel.py to produce slides

Same principle as shorts: provide maximum info, let Claude decide freely.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass

PROJ_ROOT = Path(__file__).resolve().parents[3]
INTERVIEW_PATH = PROJ_ROOT / "client" / "sisun8082" / "2026_03_27" / "interview" / "interview_transcripts.md"
PREFLIGHT_PATH = PROJ_ROOT / "runs" / "sisun8082" / "live_20260329T011849-20260329T011849Z" / "generated" / "media_preflight.json"
IMAGES_DIR = Path(__file__).resolve().parent / "images"
OUT_SPEC_PATH = IMAGES_DIR / "instagram_carousel_edit_spec.json"

PHOTOS = {
    "photo_01": IMAGES_DIR / "KakaoTalk_20260327_121540482.jpg",
    "photo_02": IMAGES_DIR / "KakaoTalk_20260327_121540482_01.jpg",
    "photo_03": IMAGES_DIR / "KakaoTalk_20260327_121540482_02.jpg",
    "photo_04": IMAGES_DIR / "KakaoTalk_20260327_121540482_03.jpg",
    "photo_05": IMAGES_DIR / "KakaoTalk_20260327_121540482_04.jpg",
}

PHOTO_FILENAMES = {
    "photo_01": "KakaoTalk_20260327_121540482.jpg",
    "photo_02": "KakaoTalk_20260327_121540482_01.jpg",
    "photo_03": "KakaoTalk_20260327_121540482_02.jpg",
    "photo_04": "KakaoTalk_20260327_121540482_03.jpg",
    "photo_05": "KakaoTalk_20260327_121540482_04.jpg",
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv(PROJ_ROOT / ".env")
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or anthropic is None:
        print("CLAUDE_API_KEY required")
        return 1

    # Load context
    interview_text = INTERVIEW_PATH.read_text(encoding="utf-8") if INTERVIEW_PATH.exists() else ""
    preflight = {}
    if PREFLIGHT_PATH.exists():
        preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))

    # Build photo descriptions + thumbnails for vision
    photo_descriptions = []
    image_parts = []
    for pid, path in PHOTOS.items():
        analysis = {}
        for p in preflight.get("photos", []):
            if p.get("media_id") == pid or p.get("media_id") == pid.replace("_0", "_"):
                analysis = p.get("preflight_analysis", {})
                break
        photo_descriptions.append(
            f"- {pid} ({PHOTO_FILENAMES[pid]}): {analysis.get('scene', '')}, {analysis.get('details', '')}, 분위기: {analysis.get('mood', '')}"
        )
        img = Image.open(path)
        img.thumbnail((600, 600))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=60)
        image_parts.append({"type": "text", "text": f"\n### {pid}:"})
        image_parts.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()},
        })

    prompt = f"""당신은 인스타그램 캐러셀 콘텐츠 기획자입니다.

아래 사진들과 인터뷰를 보고, 5장짜리 인스타그램 캐러셀을 기획해주세요.

## 사진 정보
{chr(10).join(photo_descriptions)}

## 인터뷰 원문 (샵 원장님 대화)
{interview_text}

## 샵 정보
- 이름: 시선을 즐기다 (Sisun8082 Head Spa)
- 위치: 부산 서면 점포카페거리

## 캐러셀 기획 지침

5장의 슬라이드가 하나의 이야기를 전달해야 합니다.
각 슬라이드는 사진 1장 + 텍스트 오버레이로 구성됩니다.

- 화자는 브랜드 시점 (저희 시선을 즐기다에서는...)
- 인터뷰 원문의 실제 표현을 활용
- 1장은 표지 (훅), 5장은 마무리 (CTA)
- 각 슬라이드별 사진을 자유롭게 선택
- headline은 짧고 임팩트 있게 (2줄 이내)
- subheadline은 보조 설명 (1줄)
- 인스타 캡션 + 해시태그도 함께 생성

## 출력 형식 (JSON만)

```json
{{
  "slides": [
    {{
      "order": 1,
      "photo_id": "photo_01",
      "role": "cover",
      "headline": "메인 텍스트",
      "subheadline": "보조 텍스트",
      "overlay_position": "top_center"
    }}
  ],
  "caption": "인스타그램 캡션 텍스트",
  "hashtags": ["#태그1", "#태그2"]
}}
```

overlay_position 선택지: top_center, bottom_center, center_left, bottom_left

JSON만 출력하세요."""

    print("Generating carousel spec via Claude...")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, *image_parts]}],
    )

    text = response.content[0].text.strip()
    if "```" in text:
        lines = text.split("\n")
        clean = []
        inside = False
        for line in lines:
            if line.strip().startswith("```"):
                inside = not inside
                continue
            if inside:
                clean.append(line)
        text = "\n".join(clean).strip()
    if not text:
        text = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()

    result = json.loads(text)

    # Build full edit spec in existing renderer format
    design_system = {
        "target_resolution": "1080x1350",
        "aspect_ratio": "4:5",
        "crop_mode": "cover_after_exif_normalize",
        "safe_zone": {"top_percent": 12, "bottom_percent": 14, "left_percent": 8, "right_percent": 8},
        "fonts": {
            "headline": "Cafe24Moyamoya-Regular-v1.0",
            "body": "Cafe24Ohsquare-v2.0"
        },
        "colors": {
            "primary_highlight": "#FFEE59",
            "primary_text": "#FFFFFF",
            "stroke": "#07111D",
            "panel": "rgba(5,17,34,0.72)",
            "panel_soft": "rgba(5,17,34,0.52)"
        },
        "overlay_style_defaults": {
            "headline_font_size": 62,
            "body_font_size": 34,
            "stroke_width": 3,
            "background_padding": 20,
            "background_radius": 18
        }
    }

    # Style per slide role
    style_map = {
        "cover": {
            "headline_font": "Cafe24Moyamoya-Regular-v1.0",
            "headline_font_size": 62,
            "headline_color": "#FFEE59",
            "subheadline_font": "Cafe24Ohsquare-v2.0",
            "subheadline_font_size": 26,
            "subheadline_color": "#FFFFFF",
            "background": "rgba(5,17,34,0.72)",
        },
        "context": {
            "headline_font": "Cafe24Ohsquare-v2.0",
            "headline_font_size": 50,
            "headline_color": "#FFFFFF",
            "subheadline_font": "Cafe24Ohsquare-v2.0",
            "subheadline_font_size": 26,
            "subheadline_color": "#FFEE59",
            "background": "rgba(5,17,34,0.58)",
        },
        "social_proof": {
            "headline_font": "Cafe24Ohsquare-v2.0",
            "headline_font_size": 58,
            "headline_color": "#FFEE59",
            "subheadline_font": "Cafe24Ohsquare-v2.0",
            "subheadline_font_size": 28,
            "subheadline_color": "#FFFFFF",
            "background": "rgba(35,14,58,0.30)",
        },
        "cta": {
            "headline_font": "Cafe24Ohsquare-v2.0",
            "headline_font_size": 50,
            "headline_color": "#FFFFFF",
            "subheadline_font": "Cafe24Ohsquare-v2.0",
            "subheadline_font_size": 24,
            "subheadline_color": "#B9FFF2",
            "background": "rgba(7,62,56,0.64)",
        },
    }
    default_style = style_map["context"]

    slides_spec = []
    for slide in result["slides"]:
        pid = slide["photo_id"].replace("photo_", "photo_0") if len(slide["photo_id"].split("_")[1]) == 1 else slide["photo_id"]
        filename = PHOTO_FILENAMES.get(pid, PHOTO_FILENAMES.get(slide["photo_id"], ""))
        role = slide.get("role", "context")
        style = style_map.get(role, default_style)

        slides_spec.append({
            "order": slide["order"],
            "source_file": filename,
            "role": role,
            "crop_anchor": "center",
            "headline": slide["headline"],
            "subheadline": slide.get("subheadline", ""),
            "overlay_position": slide.get("overlay_position", "bottom_center"),
            "overlay_variant": role,
            "text_style": style,
        })

    full_spec = {
        "version": "2.0",
        "type": "instagram_carousel_edit_spec",
        "pipeline_mode": "source_first",
        "project": "sisun8082",
        "set_name": "sisun8082_carousel",
        "source": {
            "directory": str(IMAGES_DIR),
            "image_count": 5,
            "normalize_exif_orientation": True,
            "exif_orientation_expected": 6,
            "original_resolution": "4000x3000",
            "effective_orientation_after_normalize": "3000x4000 portrait",
            "target_platform": "instagram_feed_carousel",
        },
        "design_system": design_system,
        "slides": slides_spec,
        "caption": {
            "primary": result.get("caption", ""),
            "cta": "",
        },
        "hashtags": result.get("hashtags", []),
        "rendering_notes": {
            "output_format": "jpg",
            "jpeg_quality": 92,
            "sharpen_after_resize": True,
            "caption_file_name": "instagram_carousel_caption.txt",
            "hashtags_join_style": "space_separated_single_line",
        },
    }

    OUT_SPEC_PATH.write_text(json.dumps(full_spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSpec saved: {OUT_SPEC_PATH}")

    # Print summary
    for s in slides_spec:
        print(f"  Slide {s['order']}: [{s['role']}] {s['headline'][:30]}... -> {s['source_file']}")

    print(f"\nCaption: {result.get('caption', '')[:80]}...")
    print(f"Hashtags: {' '.join(result.get('hashtags', [])[:5])}...")

    print(f"\nNow run the renderer:")
    print(f"  cd {IMAGES_DIR}")
    print(f"  python render_instagram_carousel.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
