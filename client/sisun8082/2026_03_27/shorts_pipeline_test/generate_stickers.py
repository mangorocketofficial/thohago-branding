"""Generate sticker/emoji placement plan using Claude vision."""
from __future__ import annotations

import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

import anthropic
from dotenv import load_dotenv

PROJ_ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent / "render_output"

PHOTOS = {
    "photo_01": PROJ_ROOT / "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482.jpg",
    "photo_02": PROJ_ROOT / "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_01.jpg",
    "photo_03": PROJ_ROOT / "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_02.jpg",
    "photo_04": PROJ_ROOT / "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_03.jpg",
    "photo_05": PROJ_ROOT / "client/sisun8082/2026_03_27/images/KakaoTalk_20260327_121540482_04.jpg",
}


def main() -> int:
    load_dotenv(PROJ_ROOT / ".env")
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    # Build image content (thumbnailed for token efficiency)
    image_parts = []
    for pid, path in PHOTOS.items():
        img = Image.open(path)
        img.thumbnail((800, 800))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=70)
        b64 = base64.b64encode(buf.getvalue()).decode()
        image_parts.append({"type": "text", "text": f"\n### {pid}:"})
        image_parts.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })

    prompt = (
        "이 사진들은 숏폼 영상(1080x1920 세로)에서 사용됩니다.\n\n"
        "각 사진에 이모지 스티커를 1~2개 배치하고 싶어요.\n"
        "사진은 센터 크롭으로 1080x1920에 맞춰지고 Ken Burns 줌이 적용됩니다.\n\n"
        "각 사진을 보고:\n"
        "1. 어울리는 유니코드 이모지\n"
        "2. 1080x1920 캔버스 기준 x, y 좌표\n"
        "3. 크기(픽셀)\n"
        "4. 이유\n\n"
        "주의:\n"
        "- 장면 분위기를 강화하는 용도 (과하지 않게)\n"
        "- 화면 중앙 영역(y=800~1100)과 하단 20%(y>1536)는 텍스트 영역이므로 피할 것\n"
        "- 상단 좌우 코너(y=100~400) 또는 중상단 영역이 적합\n"
        "- 사진당 최대 2개\n"
        "- 좌표는 1080x1920 기준 (좌상단 0,0)\n\n"
        "JSON만 답하세요. 다른 텍스트 없이:\n"
        '{"stickers": [{"photo_id": "photo_01", "emoji": "이모지문자", '
        '"x": 800, "y": 300, "size": 80, "reason": "이유"}, ...]}'
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, *image_parts]}],
    )

    text = response.content[0].text.strip()
    # Strip markdown fences
    if "```" in text:
        lines = text.split("\n")
        clean = []
        inside = False
        for line in lines:
            if line.strip().startswith("```"):
                inside = not inside
                continue
            if inside or not text.startswith("```"):
                clean.append(line)
        text = "\n".join(clean).strip()
        if not text:
            text = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()

    result = json.loads(text)

    out_path = OUT_DIR / "sticker_plan.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print with utf-8 encoding
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
