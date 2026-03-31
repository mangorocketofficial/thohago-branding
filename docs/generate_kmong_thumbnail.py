"""Generate Kmong service thumbnail (652x488)."""
from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

PROJ_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = PROJ_ROOT / "docs" / "kmong_thumbnail.jpg"

FONT_TITLE = PROJ_ROOT / "assets" / "font" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0.ttf"
FONT_BODY = PROJ_ROOT / "assets" / "font" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf"

W, H = 652, 488
BG = (24, 24, 32)
YELLOW = (255, 238, 89)
WHITE = (255, 255, 255)
ACCENT = (255, 107, 107)


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def main() -> int:
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    title_font = ImageFont.truetype(str(FONT_TITLE), 56)
    sub_font = ImageFont.truetype(str(FONT_BODY), 26)
    tag_font = ImageFont.truetype(str(FONT_BODY), 20)

    # Pre-measure all content heights for vertical centering
    title_lines = ["사장님의 진짜 이야기를", "4가지 콘텐츠로"]
    title_heights = [text_size(draw, l, title_font)[1] for l in title_lines]
    title_gap = 12
    title_block_h = sum(title_heights) + title_gap * (len(title_lines) - 1)

    sub_text = "사진 보내고  5분 인터뷰하면  끝"
    sub_w, sub_h = text_size(draw, sub_text, sub_font)

    tags = ["블로그", "릴스", "인스타 피드", "쓰레드"]
    pill_h = 40
    tag_gap = 12

    gap_title_sub = 24
    gap_sub_tags = 28

    total_content_h = title_block_h + gap_title_sub + sub_h + gap_sub_tags + pill_h
    y = (H - total_content_h) // 2

    # Draw title lines (centered)
    for i, line in enumerate(title_lines):
        lw, lh = text_size(draw, line, title_font)
        x = (W - lw) // 2
        draw.text((x, y), line, font=title_font, fill=YELLOW)
        y += lh + title_gap
    y -= title_gap  # remove last gap
    y += gap_title_sub

    # Draw subtitle (centered)
    x = (W - sub_w) // 2
    draw.text((x, y), sub_text, font=sub_font, fill=WHITE)
    y += sub_h + gap_sub_tags

    # Draw tag pills (centered row)
    pill_pad_x = 12
    tag_widths = [text_size(draw, t, tag_font)[0] for t in tags]
    pill_widths = [tw + pill_pad_x * 2 for tw in tag_widths]
    total_pills_w = sum(pill_widths) + tag_gap * (len(tags) - 1)
    tx = (W - total_pills_w) // 2

    for i, tag in enumerate(tags):
        pw = pill_widths[i]
        draw.rounded_rectangle([(tx, y), (tx + pw, y + pill_h)], radius=15, fill=ACCENT)
        tw, th = text_size(draw, tag, tag_font)
        draw.text((tx + (pw - tw) // 2, y + (pill_h - th) // 2), tag, font=tag_font, fill=WHITE)
        tx += pw + tag_gap

    canvas.save(str(OUT_PATH), "JPEG", quality=95)
    print(f"Saved: {OUT_PATH}")
    print(f"Size: {W}x{H}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
