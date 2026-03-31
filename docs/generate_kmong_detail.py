"""Generate Kmong service detail image (single tall vertical image).

Layout:
1. Header: service title + one-liner
2. Case 1: 헤드스파 캐러셀 5장
3. Case 2: 이자카야 단일 피드
4. Case 3: 잭프루트 단일 피드
5. Process: 5-step workflow
6. CTA: price/contact
"""
from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")

PROJ_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = PROJ_ROOT / "docs" / "kmong_detail_image.jpg"

# Fonts
FONT_TITLE = PROJ_ROOT / "assets" / "font" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0" / "Cafe24Dangdanghae-v2.0.ttf"
FONT_BODY = PROJ_ROOT / "assets" / "font" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf"

# Canvas
W = 860
PAD = 40
BG_COLOR = (255, 255, 255)
ACCENT = (255, 107, 107)  # #FF6B6B
DARK = (34, 34, 34)
GRAY = (120, 120, 120)
YELLOW = (255, 238, 89)

# Source images
CAROUSEL_DIR = PROJ_ROOT / "client" / "sisun8082" / "2026_03_27" / "images" / "carousel_output"
CAROUSEL_FILES = [
    CAROUSEL_DIR / "slide_01_KakaoTalk_20260327_121540482.jpg",
    CAROUSEL_DIR / "slide_02_KakaoTalk_20260327_121540482_01.jpg",
    CAROUSEL_DIR / "slide_03_KakaoTalk_20260327_121540482_02.jpg",
    CAROUSEL_DIR / "slide_04_KakaoTalk_20260327_121540482_03.jpg",
    CAROUSEL_DIR / "slide_05_KakaoTalk_20260327_121540482_04.jpg",
]
URAMACHI_POST = PROJ_ROOT / "runs" / "uramachi_sakaba" / "live_20260330T033330-20260330T033330Z" / "generated" / "insta_post" / "insta_post.jpg"
THOHAGO_POST = PROJ_ROOT / "runs" / "thohago_test" / "live_20260330T043229-20260330T043229Z" / "generated" / "insta_post" / "insta_post.jpg"


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def draw_centered_text(draw: ImageDraw.Draw, y: int, text: str, font: ImageFont.FreeTypeFont, fill: tuple) -> int:
    lines = text.split("\n")
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        x = (W - lw) // 2
        draw.text((x, y), line, font=font, fill=fill)
        y += lh + 8
    return y


def draw_section_label(draw: ImageDraw.Draw, y: int, label: str, font: ImageFont.FreeTypeFont) -> int:
    # Accent bar + label
    bar_w = 4
    bb = draw.textbbox((0, 0), label, font=font)
    lh = bb[3] - bb[1]
    draw.rectangle([(PAD, y), (PAD + bar_w, y + lh)], fill=ACCENT)
    draw.text((PAD + 16, y), label, font=font, fill=DARK)
    return y + lh + 20


def paste_image_centered(canvas: Image.Image, img: Image.Image, y: int, max_w: int, max_h: int) -> int:
    img_copy = img.copy()
    img_copy.thumbnail((max_w, max_h), Image.LANCZOS)
    x = (W - img_copy.width) // 2
    canvas.paste(img_copy, (x, y))
    return y + img_copy.height + 16


def main() -> int:
    # Pre-calculate total height
    # Rough estimate: header 300 + case1 (label + 3rows of 2) ~1100 + case2 ~700 + case3 ~700 + process ~500 + cta ~300
    total_h = 4000
    canvas = Image.new("RGB", (W, total_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    y = 0

    # ===== HEADER =====
    # Background accent strip
    draw.rectangle([(0, 0), (W, 280)], fill=(34, 34, 34))
    title_font = load_font(FONT_TITLE, 36)
    subtitle_font = load_font(FONT_BODY, 18)

    y = 50
    y = draw_centered_text(draw, y, "사장님의 진짜 이야기를\n4가지 콘텐츠로 만들어 드립니다", title_font, YELLOW)
    y += 16
    y = draw_centered_text(draw, y, "사진 보내고 5분 인터뷰하면\n블로그 / 릴스 / 인스타 피드 / 쓰레드까지", subtitle_font, (200, 200, 200))
    y = 300

    # ===== CASE 1: 헤드스파 캐러셀 =====
    section_font = load_font(FONT_BODY, 22)
    label_font = load_font(FONT_BODY, 14)
    y = draw_section_label(draw, y, "CASE 1  |  뷰티샵 인스타 캐러셀 (5장)", section_font)

    # 2 images side by side (slide 1 + 2 only)
    thumb_w = (W - PAD * 3) // 2
    thumb_h = int(thumb_w * 1350 / 1080)
    for i, path in enumerate(CAROUSEL_FILES[:2]):
        if not path.exists():
            continue
        img = Image.open(path)
        img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
        x = PAD + i * (thumb_w + PAD)
        canvas.paste(img, (x, y))
    y += thumb_h + 20

    # ===== CASE 2 + CASE 3: 나란히 한 줄 =====
    y = draw_section_label(draw, y, "CASE 2  |  이자카야          CASE 3  |  농장", section_font)
    side_w = (W - PAD * 3) // 2
    side_h = int(side_w * 1350 / 1080)
    if URAMACHI_POST.exists():
        img = Image.open(URAMACHI_POST)
        img.thumbnail((side_w, side_h), Image.LANCZOS)
        canvas.paste(img, (PAD, y))
    if THOHAGO_POST.exists():
        img = Image.open(THOHAGO_POST)
        img.thumbnail((side_w, side_h), Image.LANCZOS)
        canvas.paste(img, (PAD + side_w + PAD, y))
    y += side_h + 20

    # ===== PROCESS =====
    draw.rectangle([(0, y), (W, y + 4)], fill=ACCENT)
    y += 24
    y = draw_section_label(draw, y, "진행 과정", section_font)

    process_font = load_font(FONT_BODY, 16)
    steps = [
        ("STEP 1", "사진/영상 보내기", "텔레그램으로 사진(최대 5장), 영상 전송"),
        ("STEP 2", "5분 인터뷰", "사진 기반 맞춤 질문 3개에 음성/텍스트 답변"),
        ("STEP 3", "콘텐츠 생성", "AI가 4가지 콘텐츠를 자동 제작"),
        ("STEP 4", "확인 및 수정", "미리보기 확인 후 수정 요청 가능"),
        ("STEP 5", "전달", "최종 승인 후 모든 파일 전달"),
    ]
    step_label_font = load_font(FONT_BODY, 14)
    for step_num, step_title, step_desc in steps:
        # Step number circle
        draw.ellipse([(PAD, y), (PAD + 28, y + 28)], fill=ACCENT)
        num_bb = draw.textbbox((0, 0), step_num[-1], font=step_label_font)
        num_w = num_bb[2] - num_bb[0]
        draw.text((PAD + 14 - num_w // 2, y + 4), step_num[-1], font=step_label_font, fill=(255, 255, 255))
        # Title + desc
        draw.text((PAD + 40, y), step_title, font=process_font, fill=DARK)
        draw.text((PAD + 40, y + 24), step_desc, font=label_font, fill=GRAY)
        y += 56
    y += 20

    # ===== CTA =====
    draw.rectangle([(0, y), (W, y + 160)], fill=(34, 34, 34))
    cta_font = load_font(FONT_BODY, 20)
    cta_sub = load_font(FONT_BODY, 14)
    y += 30
    y = draw_centered_text(draw, y, "사장님의 이야기를 콘텐츠로 만들어보세요", cta_font, YELLOW)
    y += 8
    y = draw_centered_text(draw, y, "문의는 크몽 메시지로 편하게 보내주세요", cta_sub, (180, 180, 180))
    y += 40

    # Crop to actual content height
    canvas = canvas.crop((0, 0, W, y))
    canvas.save(str(OUT_PATH), "JPEG", quality=92)
    print(f"Saved: {OUT_PATH}")
    print(f"Size: {W}x{y}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
