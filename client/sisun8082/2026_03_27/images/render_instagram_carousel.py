from __future__ import annotations

import json
import math
import re
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[4]
FONT_ROOT = PROJECT_ROOT / "assets" / "font"
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "carousel_output"

FONT_CANDIDATES = {
    "Cafe24Moyamoya-Regular-v1.0": [
        FONT_ROOT / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-Regular-v1.0.ttf",
        FONT_ROOT / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-v1.0" / "Cafe24Moyamoya-Regular-v1.0.otf",
    ],
    "Cafe24Ohsquare-v2.0": [
        FONT_ROOT / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.ttf",
        FONT_ROOT / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0" / "Cafe24Ohsquare-v2.0.otf",
    ],
}


def load_spec(spec_path: Path) -> dict:
    return json.loads(spec_path.read_text(encoding="utf-8"))


def resolve_font(font_name: str) -> Path:
    direct_path = Path(font_name)
    if direct_path.exists():
        return direct_path
    for candidate in FONT_CANDIDATES.get(font_name, []):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No usable font found for {font_name}")


def parse_color(value: str) -> tuple[int, int, int, int]:
    if value.startswith("rgba("):
        rgba_match = re.fullmatch(
            r"rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([0-9.]+)\s*\)",
            value,
        )
        if not rgba_match:
            raise ValueError(f"Invalid rgba value: {value}")
        red, green, blue, alpha = rgba_match.groups()
        return int(red), int(green), int(blue), max(0, min(255, round(float(alpha) * 255)))
    rgb = ImageColor.getrgb(value)
    return rgb[0], rgb[1], rgb[2], 255


def crop_cover(image: Image.Image, target_size: tuple[int, int], anchor: str) -> Image.Image:
    target_width, target_height = target_size
    source_width, source_height = image.size
    target_ratio = target_width / target_height
    source_ratio = source_width / source_height

    if source_ratio > target_ratio:
        crop_height = source_height
        crop_width = int(round(crop_height * target_ratio))
    else:
        crop_width = source_width
        crop_height = int(round(crop_width / target_ratio))

    if "left" in anchor:
        left = 0
    elif "right" in anchor:
        left = source_width - crop_width
    else:
        left = (source_width - crop_width) // 2

    if "top" in anchor:
        top = 0
    elif "bottom" in anchor:
        top = source_height - crop_height
    else:
        top = (source_height - crop_height) // 2

    left = max(0, min(left, source_width - crop_width))
    top = max(0, min(top, source_height - crop_height))
    cropped = image.crop((left, top, left + crop_width, top + crop_height))
    return cropped.resize(target_size, Image.Resampling.LANCZOS)


def enhance_base(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Contrast(image).enhance(1.05)
    image = ImageEnhance.Color(image).enhance(1.04)
    image = ImageEnhance.Sharpness(image).enhance(1.05)
    return image


def add_readability_gradient(image: Image.Image, overlay_position: str) -> Image.Image:
    width, height = image.size
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = gradient.load()

    for y in range(height):
        alpha = 0
        if overlay_position.startswith("top"):
            alpha = int(max(0, 120 * (1 - (y / (height * 0.42)))))
        elif overlay_position.startswith("bottom"):
            distance = (height - y) / (height * 0.42)
            alpha = int(max(0, 120 * (1 - distance)))
        elif overlay_position.startswith("center"):
            center_dist = abs((y / height) - 0.55)
            alpha = int(max(0, 70 * (1 - min(1.0, center_dist / 0.22))))

        for x in range(width):
            pixels[x, y] = (6, 12, 20, alpha)

    return Image.alpha_composite(image.convert("RGBA"), gradient)


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, stroke_width: int) -> tuple[int, int, int, int]:
    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        spacing=max(8, int(font.size * 0.18)),
        align="left",
        stroke_width=stroke_width,
    )
    return (
        math.floor(bbox[0]),
        math.floor(bbox[1]),
        math.ceil(bbox[2]),
        math.ceil(bbox[3]),
    )


def compute_box_position(
    image_size: tuple[int, int],
    box_size: tuple[int, int],
    position: str,
    safe_zone: dict,
) -> tuple[int, int, str]:
    image_width, image_height = image_size
    box_width, box_height = box_size
    left_margin = round(image_width * (safe_zone["left_percent"] / 100))
    right_margin = round(image_width * (safe_zone["right_percent"] / 100))
    top_margin = round(image_height * (safe_zone["top_percent"] / 100))
    bottom_margin = round(image_height * (safe_zone["bottom_percent"] / 100))

    align = "center"
    if "left" in position:
        align = "left"

    if position.startswith("top"):
        y = top_margin
    elif position.startswith("bottom"):
        y = image_height - bottom_margin - box_height
    else:
        y = (image_height - box_height) // 2

    if "left" in position:
        x = left_margin
    elif "right" in position:
        x = image_width - right_margin - box_width
    else:
        x = (image_width - box_width) // 2

    return x, y, align


def draw_overlay(image: Image.Image, slide: dict, design_system: dict) -> Image.Image:
    image = image.convert("RGBA")
    image = add_readability_gradient(image, slide["overlay_position"])
    draw = ImageDraw.Draw(image)
    style = slide["text_style"]
    defaults = design_system["overlay_style_defaults"]
    safe_zone = design_system["safe_zone"]

    headline_font = ImageFont.truetype(
        str(resolve_font(style["headline_font"])),
        int(style["headline_font_size"]),
    )
    subheadline_font = ImageFont.truetype(
        str(resolve_font(style["subheadline_font"])),
        int(style["subheadline_font_size"]),
    )
    stroke_color = parse_color(design_system["colors"]["stroke"])
    background_color = parse_color(style["background"])
    headline_color = parse_color(style["headline_color"])
    subheadline_color = parse_color(style["subheadline_color"])
    stroke_width = int(defaults["stroke_width"])
    padding = int(defaults["background_padding"])
    radius = int(defaults["background_radius"])
    gap = 12

    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    headline_bbox = text_bbox(probe_draw, slide["headline"], headline_font, stroke_width)
    subheadline_bbox = text_bbox(probe_draw, slide["subheadline"], subheadline_font, stroke_width)
    headline_width = headline_bbox[2] - headline_bbox[0]
    headline_height = headline_bbox[3] - headline_bbox[1]
    subheadline_width = subheadline_bbox[2] - subheadline_bbox[0]
    subheadline_height = subheadline_bbox[3] - subheadline_bbox[1]
    box_width = max(headline_width, subheadline_width) + (padding * 2)
    box_height = headline_height + gap + subheadline_height + (padding * 2)

    box_x, box_y, align = compute_box_position(image.size, (box_width, box_height), slide["overlay_position"], safe_zone)
    draw.rounded_rectangle(
        (box_x, box_y, box_x + box_width, box_y + box_height),
        radius=radius,
        fill=background_color,
    )

    if align == "center":
        headline_text_x = box_x + ((box_width - headline_width) / 2) - headline_bbox[0]
        subheadline_text_x = box_x + ((box_width - subheadline_width) / 2) - subheadline_bbox[0]
    else:
        headline_text_x = box_x + padding - headline_bbox[0]
        subheadline_text_x = box_x + padding - subheadline_bbox[0]

    headline_text_y = box_y + padding - headline_bbox[1]
    subheadline_text_y = box_y + padding + headline_height + gap - subheadline_bbox[1]

    draw.multiline_text(
        (headline_text_x, headline_text_y),
        slide["headline"],
        font=headline_font,
        fill=headline_color,
        spacing=max(8, int(headline_font.size * 0.18)),
        align=align,
        stroke_width=stroke_width,
        stroke_fill=stroke_color,
    )
    draw.multiline_text(
        (subheadline_text_x, subheadline_text_y),
        slide["subheadline"],
        font=subheadline_font,
        fill=subheadline_color,
        spacing=max(6, int(subheadline_font.size * 0.18)),
        align=align,
        stroke_width=2,
        stroke_fill=stroke_color,
    )
    return image


def save_jpeg(image: Image.Image, output_path: Path, quality: int) -> None:
    rgb_image = image.convert("RGB")
    rgb_image = rgb_image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=2))
    rgb_image.save(output_path, format="JPEG", quality=quality, optimize=True)


def render_slides(spec: dict) -> list[Path]:
    source_directory = Path(spec["source"]["directory"])
    design_system = spec["design_system"]
    target_width, target_height = [int(part) for part in design_system["target_resolution"].split("x")]
    OUTPUT_DIR.mkdir(exist_ok=True)

    rendered_paths: list[Path] = []
    for slide in spec["slides"]:
        source_path = source_directory / slide["source_file"]
        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image = crop_cover(image, (target_width, target_height), slide["crop_anchor"])
            image = enhance_base(image)
            image = draw_overlay(image, slide, design_system)

        output_name = f"slide_{slide['order']:02d}_{Path(slide['source_file']).stem}.jpg"
        output_path = OUTPUT_DIR / output_name
        save_jpeg(image, output_path, int(spec["rendering_notes"]["jpeg_quality"]))
        rendered_paths.append(output_path)

    return rendered_paths


def write_caption_files(spec: dict) -> tuple[Path, Path]:
    hashtags = " ".join(spec["hashtags"]).strip()
    caption_text = (
        spec["caption"]["primary"].rstrip()
        + "\n\n"
        + spec["caption"]["cta"].rstrip()
        + "\n\n"
        + hashtags
        + "\n"
    )
    caption_path = OUTPUT_DIR / spec["rendering_notes"]["caption_file_name"]
    hashtags_path = OUTPUT_DIR / "instagram_carousel_hashtags.txt"
    caption_path.write_text(caption_text, encoding="utf-8")
    hashtags_path.write_text(hashtags + "\n", encoding="utf-8")
    return caption_path, hashtags_path


def write_manifest(spec: dict, rendered_paths: list[Path]) -> Path:
    manifest = {
        "set_name": spec["set_name"],
        "output_dir": str(OUTPUT_DIR),
        "slides": [
            {
                "order": slide["order"],
                "source_file": slide["source_file"],
                "output_file": path.name,
                "headline": slide["headline"],
                "subheadline": slide["subheadline"],
            }
            for slide, path in zip(spec["slides"], rendered_paths)
        ],
    }
    manifest_path = OUTPUT_DIR / "carousel_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def main() -> None:
    spec_path = SCRIPT_DIR / "instagram_carousel_edit_spec.json"
    spec = load_spec(spec_path)
    rendered_paths = render_slides(spec)
    caption_path, hashtags_path = write_caption_files(spec)
    manifest_path = write_manifest(spec, rendered_paths)

    print(f"Output dir: {OUTPUT_DIR}")
    for path in rendered_paths:
        print(path.name)
    print(f"Caption: {caption_path.name}")
    print(f"Hashtags: {hashtags_path.name}")
    print(f"Manifest: {manifest_path.name}")


if __name__ == "__main__":
    main()
