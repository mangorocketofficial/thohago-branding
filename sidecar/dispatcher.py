from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from copy import deepcopy
import mimetypes
from pathlib import Path
import platform
import sys

from thohago.instagram_publish import InstagramGraphPublisher, InstagramPublishError
from thohago.threads_publish import ThreadsPublisher, ThreadsPublishError


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Dispatcher:
    start_time: str
    project_root: str
    python_executable: str
    shutdown_requested: bool = False

    def handle(self, method: str, params: dict | None) -> dict:
        params = params or {}

        if method == "system.ping":
            return {
                "ok": True,
                "message": "pong",
                "now": _utc_now(),
            }

        if method == "system.status":
            return {
                "ok": True,
                "project_root": self.project_root,
                "python_executable": self.python_executable,
                "platform": platform.platform(),
                "started_at": self.start_time,
                "shutdown_requested": self.shutdown_requested,
            }

        if method == "system.shutdown":
            self.shutdown_requested = True
            return {
                "ok": True,
                "message": "shutdown acknowledged",
            }

        if method == "interview.build_preflight":
            return build_media_preflight(params)

        if method == "interview.plan_turn":
            return plan_turn(params)

        if method == "content.compose_blog":
            return compose_blog(params)

        if method == "content.generate_carousel_spec":
            return generate_carousel_spec(params)

        if method == "content.generate_video_spec":
            return generate_video_spec(params)

        if method == "content.generate_thread":
            return generate_thread(params)

        if method == "content.regenerate_blog":
            return regenerate_blog(params)

        if method == "content.regenerate_carousel":
            return regenerate_carousel(params)

        if method == "content.regenerate_video":
            return regenerate_video(params)

        if method == "content.regenerate_thread":
            return regenerate_thread(params)

        if method == "publish.naver_blog":
            return publish_naver_blog(params)

        if method == "publish.instagram_carousel":
            return publish_instagram_carousel(params)

        if method == "publish.instagram_reels":
            return publish_instagram_reels(params)

        if method == "publish.threads":
            return publish_threads(params)

        if method == "publish.validate_instagram":
            return validate_instagram_publish(params)

        if method == "publish.validate_threads":
            return validate_threads_publish(params)

        if method == "publish.validate_naver":
            return validate_naver_publish(params)

        raise KeyError(f"unknown method: {method}")


def build_media_preflight(params: dict) -> dict:
    media_items = params.get("media_items") or []
    if not media_items:
        return {
            "ok": True,
            "summary": "No media imported yet.",
            "photo_count": 0,
            "video_count": 0,
            "hero_suggestion_id": None,
            "experience_sequence": [],
            "notes": ["Import at least one photo to unlock interview planning."],
        }

    ordered = sorted(
        media_items,
        key=lambda item: (
            int(item.get("experience_order") or 0),
            str(item.get("file_name") or item.get("id") or ""),
        ),
    )
    photo_count = sum(1 for item in ordered if item.get("kind") == "photo")
    video_count = sum(1 for item in ordered if item.get("kind") == "video")
    hero = next((item for item in ordered if item.get("is_hero")), None)
    hero = hero or next((item for item in ordered if item.get("kind") == "photo"), None)
    hero = hero or ordered[0]

    experience_sequence = []
    for index, item in enumerate(ordered, start=1):
        guessed_mime, _ = mimetypes.guess_type(item.get("file_name") or "")
        experience_sequence.append(
            {
                "index": index,
                "media_id": item.get("id"),
                "kind": item.get("kind"),
                "file_name": item.get("file_name"),
                "role": guess_media_role(index, item, hero),
                "mime_type": item.get("mime_type") or guessed_mime,
            }
        )

    summary_parts = [
        f"{photo_count} photo{'s' if photo_count != 1 else ''}",
        f"{video_count} video{'s' if video_count != 1 else ''}",
    ]
    return {
        "ok": True,
        "summary": (
            f"Imported {', '.join(summary_parts)}. "
            f"Representative asset: {hero.get('file_name') or hero.get('id')}."
        ),
        "photo_count": photo_count,
        "video_count": video_count,
        "photoCount": photo_count,
        "videoCount": video_count,
        "hero_suggestion_id": hero.get("id"),
        "heroSuggestionId": hero.get("id"),
        "experience_sequence": experience_sequence,
        "experienceSequence": experience_sequence,
        "notes": build_preflight_notes(photo_count, video_count, hero, experience_sequence),
    }


def guess_media_role(index: int, item: dict, hero: dict) -> str:
    if item.get("id") == hero.get("id"):
        return "hero"
    if item.get("kind") == "video":
        return "motion"
    if index == 1:
        return "lead"
    return "supporting"


def build_preflight_notes(
    photo_count: int, video_count: int, hero: dict, experience_sequence: list[dict]
) -> list[str]:
    notes = [
        f"Start the interview by anchoring on {hero.get('file_name') or hero.get('id')}.",
        "Use the owner answers to fill in sensory detail, differentiators, and customer intent.",
    ]
    if photo_count == 1:
        notes.append("Only one photo is present, so Turn 2 should focus on depth rather than sequence.")
    if video_count:
        notes.append("At least one video is present, so later generation can emphasize motion or behind-the-scenes moments.")
    if len(experience_sequence) >= 3:
        notes.append("There are enough ordered assets to ask about progression or storytelling flow.")
    return notes


def plan_turn(params: dict) -> dict:
    turn_index = int(params.get("turn_index") or 0)
    preflight = params.get("preflight") or {}
    answers = params.get("answers") or []
    shop_display_name = params.get("shop_display_name") or "the business"
    hero_label = preflight.get("hero_suggestion_id") or "the main scene"

    if turn_index == 2:
        previous = (answers[0] if answers else "").strip()
        question = (
            f"{shop_display_name}의 핵심 장면으로 보이는 {hero_label}를 기준으로, "
            f"방금 답변에서 언급한 분위기나 서비스가 실제로 어떻게 진행되는지 한 단계 더 자세히 설명해 주세요."
        )
        return {
            "ok": True,
            "turn_index": 2,
            "turnIndex": 2,
            "strategy": "detail_deepening",
            "covered_elements": extract_keywords(previous),
            "coveredElements": extract_keywords(previous),
            "missing_elements": ["customer perspective", "specific process detail"],
            "missingElements": ["customer perspective", "specific process detail"],
            "next_question": question,
            "nextQuestion": question,
        }

    if turn_index == 3:
        previous = " ".join(answer.strip() for answer in answers if answer).strip()
        question = (
            f"좋습니다. 마지막으로 {shop_display_name}만의 차별점이나 사장님 관점에서 꼭 강조하고 싶은 한 문장을 말해 주세요."
        )
        return {
            "ok": True,
            "turn_index": 3,
            "turnIndex": 3,
            "strategy": "owner_perspective",
            "covered_elements": extract_keywords(previous),
            "coveredElements": extract_keywords(previous),
            "missing_elements": ["owner voice", "call-to-action seed"],
            "missingElements": ["owner voice", "call-to-action seed"],
            "next_question": question,
            "nextQuestion": question,
        }

    raise KeyError(f"unsupported turn index: {turn_index}")


def extract_keywords(text: str) -> list[str]:
    if not text:
        return []

    words = []
    for raw in text.replace(",", " ").replace(".", " ").split():
        clean = raw.strip()
        if len(clean) >= 2 and clean not in words:
            words.append(clean)
        if len(words) == 5:
            break
    return words


def compose_blog(params: dict) -> dict:
    bundle = params.get("bundle") or {}
    profile = bundle.get("generationProfile") or {}
    interview = bundle.get("interview") or {}
    emphasis = profile.get("emphasisPoint") or bundle.get("summary") or "signature experience"
    title = f"{bundle.get('shopDisplayName', 'Shop')} | {emphasis}"

    sections = [
        {
            "sectionId": "intro",
            "heading": "What guests notice first",
            "body": interview.get("turn1Answer")
            or f"The first impression centers on {emphasis}.",
        },
        {
            "sectionId": "experience",
            "heading": "How the experience unfolds",
            "body": interview.get("turn2Answer")
            or "The visit unfolds in a calm, structured sequence from consultation to finish.",
        },
        {
            "sectionId": "owner_voice",
            "heading": "Owner perspective",
            "body": interview.get("turn3Answer")
            or "The owner perspective highlights what makes the experience distinct and memorable.",
        },
    ]

    return {
        "version": "1.0",
        "type": "blog_spec",
        "title": title,
        "sections": sections,
        "hashtags": normalize_hashtags(profile.get("mustIncludeKeywords") or []),
        "metadata": {
            "tone": profile.get("tone") or "friendly",
            "contentLength": profile.get("contentLength") or "standard",
            "industry": profile.get("industry") or "",
        },
    }


def generate_carousel_spec(params: dict) -> dict:
    bundle = params.get("bundle") or {}
    profile = bundle.get("generationProfile") or {}
    media_assets = bundle.get("mediaAssets") or []
    emphasis = profile.get("emphasisPoint") or "signature experience"

    slides = []
    for index, asset in enumerate(media_assets[:5], start=1):
        slides.append(
            {
                "slideId": f"slide_{index:02d}",
                "mediaId": asset.get("id"),
                "fileName": asset.get("fileName"),
                "headline": build_slide_headline(index, emphasis, bundle),
                "subheadline": build_slide_subheadline(index, bundle),
                "role": "hero" if asset.get("isHero") else "supporting",
            }
        )

    return {
        "version": "1.0",
        "type": "carousel_spec",
        "slides": slides,
        "caption": {
            "primary": f"{bundle.get('shopDisplayName', 'This shop')} focuses on {emphasis}.",
            "cta": build_cta(bundle),
        },
        "hashtags": normalize_hashtags(profile.get("mustIncludeKeywords") or []),
    }


def generate_video_spec(params: dict) -> dict:
    bundle = params.get("bundle") or {}
    profile = bundle.get("generationProfile") or {}
    media_assets = bundle.get("mediaAssets") or []
    target_duration = {"short": 18, "standard": 24, "long": 32}.get(
        profile.get("contentLength") or "standard", 24
    )

    timeline = []
    current_start = 0.0
    clip_duration = max(4.0, round(target_duration / max(1, len(media_assets[:5])), 1))
    for index, asset in enumerate(media_assets[:5], start=1):
        timeline.append(
            {
                "clipId": f"clip_{index:02d}",
                "mediaId": asset.get("id"),
                "assetType": asset.get("kind"),
                "sourcePath": asset.get("filePath"),
                "startSec": current_start,
                "endSec": round(current_start + clip_duration, 1),
                "durationSec": clip_duration,
                "motion": "pan_zoom" if asset.get("kind") == "photo" else "trim",
            }
        )
        current_start = round(current_start + clip_duration, 1)

    voiceover_lines = [
        bundle.get("interview", {}).get("turn1Answer"),
        bundle.get("interview", {}).get("turn2Answer"),
        bundle.get("interview", {}).get("turn3Answer"),
    ]
    voiceover_lines = [line for line in voiceover_lines if line]

    return {
        "version": "1.0",
        "type": "video_spec",
        "source": {
            "projectId": bundle.get("projectId"),
            "shopDisplayName": bundle.get("shopDisplayName"),
            "targetDurationSec": target_duration,
        },
        "timeline": timeline,
        "textOverlays": [
            {
                "textId": "overlay_intro",
                "text": bundle.get("generationProfile", {}).get("emphasisPoint")
                or bundle.get("shopDisplayName"),
                "startSec": 0,
                "endSec": min(target_duration, 4),
                "position": "center",
            }
        ],
        "voiceover": {
            "mode": "narration",
            "scriptBlocks": [
                {"order": index + 1, "text": line}
                for index, line in enumerate(voiceover_lines)
            ],
        },
        "export": {
            "aspectRatio": "9:16",
            "resolution": "1080x1920",
            "fps": 30,
        },
    }


def generate_thread(params: dict) -> dict:
    bundle = params.get("bundle") or {}
    profile = bundle.get("generationProfile") or {}
    interview = bundle.get("interview") or {}

    return {
        "version": "1.0",
        "type": "thread_spec",
        "mainPost": f"{bundle.get('shopDisplayName', 'This shop')} is built around {profile.get('emphasisPoint') or 'a distinct customer experience'}.",
        "reply1": interview.get("turn2Answer")
        or "The experience is designed to feel intentional from the first step to the last.",
        "reply2": interview.get("turn3Answer")
        or build_cta(bundle),
        "hashtags": normalize_hashtags(profile.get("mustIncludeKeywords") or []),
        "attachedMediaIds": [profile.get("representativeMediaAssetId")]
        if profile.get("representativeMediaAssetId")
        else [],
    }


def normalize_hashtags(values: list[str]) -> list[str]:
    tags = []
    for value in values[:5]:
        cleaned = str(value).strip().replace(" ", "_")
        if not cleaned:
            continue
        if not cleaned.startswith("#"):
            cleaned = "#" + cleaned
        tags.append(cleaned)
    return tags


def build_slide_headline(index: int, emphasis: str, bundle: dict) -> str:
    if index == 1:
        return bundle.get("shopDisplayName", "Featured story")
    if index == 2:
        return "What stands out"
    if index == 3:
        return "How it feels"
    return emphasis[:60]


def build_slide_subheadline(index: int, bundle: dict) -> str:
    interview = bundle.get("interview") or {}
    mapping = {
        1: interview.get("turn1Answer"),
        2: interview.get("turn2Answer"),
        3: interview.get("turn3Answer"),
    }
    value = mapping.get(index)
    if value:
        return value
    return "Generated from the interview and project media."


def build_cta(bundle: dict) -> str:
    return f"Use this as the next draft for {bundle.get('shopDisplayName', 'your business')}."


def regenerate_blog(params: dict) -> dict:
    spec = deepcopy(params.get("current_spec") or {})
    mode = ((params.get("regeneration_directive") or {}).get("mode") or "regenerate").strip()
    spec["title"] = transform_text(spec.get("title") or "", mode, "title")
    for section in spec.get("sections", []):
        section["body"] = transform_text(section.get("body") or "", mode, "body")
    metadata = spec.get("metadata") or {}
    metadata["regenerationMode"] = mode
    metadata["tone"] = transform_tone(metadata.get("tone") or "friendly", mode)
    spec["metadata"] = metadata
    spec["hashtags"] = transform_hashtags(spec.get("hashtags") or [], mode)
    return spec


def regenerate_carousel(params: dict) -> dict:
    spec = deepcopy(params.get("current_spec") or {})
    mode = ((params.get("regeneration_directive") or {}).get("mode") or "regenerate").strip()
    for slide in spec.get("slides", []):
        slide["headline"] = transform_text(slide.get("headline") or "", mode, "headline")
        slide["subheadline"] = transform_text(
            slide.get("subheadline") or "", mode, "subheadline"
        )
    caption = spec.get("caption") or {}
    caption["primary"] = transform_text(caption.get("primary") or "", mode, "body")
    caption["cta"] = transform_text(caption.get("cta") or "", mode, "cta")
    spec["caption"] = caption
    spec["hashtags"] = transform_hashtags(spec.get("hashtags") or [], mode)
    return spec


def regenerate_video(params: dict) -> dict:
    spec = deepcopy(params.get("current_spec") or {})
    mode = ((params.get("regeneration_directive") or {}).get("mode") or "regenerate").strip()
    for overlay in spec.get("textOverlays", []):
        overlay["text"] = transform_text(overlay.get("text") or "", mode, "headline")
    voiceover = spec.get("voiceover") or {}
    for block in voiceover.get("scriptBlocks", []):
        block["text"] = transform_text(block.get("text") or "", mode, "body")
    spec["voiceover"] = voiceover
    source = spec.get("source") or {}
    current_duration = int(source.get("targetDurationSec") or 24)
    if mode == "length_shorter":
        source["targetDurationSec"] = max(12, current_duration - 6)
    elif mode == "length_longer":
        source["targetDurationSec"] = current_duration + 6
    spec["source"] = source
    return spec


def regenerate_thread(params: dict) -> dict:
    spec = deepcopy(params.get("current_spec") or {})
    mode = ((params.get("regeneration_directive") or {}).get("mode") or "regenerate").strip()
    spec["mainPost"] = transform_text(spec.get("mainPost") or "", mode, "body")
    spec["reply1"] = transform_text(spec.get("reply1") or "", mode, "body")
    spec["reply2"] = transform_text(spec.get("reply2") or "", mode, "cta")
    spec["hashtags"] = transform_hashtags(spec.get("hashtags") or [], mode)
    return spec


def transform_text(text: str, mode: str, field_kind: str) -> str:
    value = str(text or "").strip()
    if not value:
        value = "Generated text"

    if mode == "regenerate":
        return f"Alternate take: {value}"
    if mode == "tone_shift":
        return f"Warm tone: {value}"
    if mode == "length_shorter":
        parts = value.split()
        shortened = " ".join(parts[: min(len(parts), 8)])
        return shortened or value
    if mode == "length_longer":
        suffix = (
            " This version adds more concrete detail and pacing."
            if field_kind != "cta"
            else " Reserve a time to experience it in person."
        )
        return value + suffix
    if mode == "premium":
        return f"Premium focus: {value}"
    if mode == "cta_boost":
        suffix = (
            " Reserve now and make the experience part of your next visit."
            if field_kind == "cta"
            else " Book now to experience the difference firsthand."
        )
        return value + suffix
    return value


def transform_tone(current_tone: str, mode: str) -> str:
    tone = str(current_tone or "friendly")
    if mode == "tone_shift":
        order = ["friendly", "premium", "warm", "professional"]
        try:
            index = order.index(tone)
        except ValueError:
            index = 0
        return order[(index + 1) % len(order)]
    if mode == "premium":
        return "premium"
    return tone


def transform_hashtags(hashtags: list[str], mode: str) -> list[str]:
    tags = list(hashtags or [])
    if mode == "premium":
        if "#premium_edit" not in tags:
            tags.append("#premium_edit")
    if mode == "cta_boost":
        if "#book_now" not in tags:
            tags.append("#book_now")
    return tags


def publish_naver_blog(params: dict) -> dict:
    project_id = params.get("project_id") or "project"
    execution_mode = params.get("execution_mode") or "mock"
    if execution_mode == "live":
        spec = params.get("spec") or {}
        return {
            "provider": "naver_live",
            "status": "manual_ready",
            "message": "Naver Blog manual handoff package is ready.",
            "manual_handoff": {
                "project_id": project_id,
                "title": spec.get("title") or params.get("shop_display_name") or "Naver Blog Draft",
                "markdown": render_blog_markdown(spec),
                "hashtags": spec.get("hashtags") or [],
                "preview_artifact_path": params.get("preview_artifact_path"),
                "spec_artifact_path": params.get("spec_artifact_path"),
            },
        }
    return {
        "provider": "mock_naver",
        "status": "published",
        "url": f"mock://naver/{project_id}",
        "permalink": f"mock://naver/{project_id}",
    }


def publish_instagram_carousel(params: dict) -> dict:
    project_id = params.get("project_id") or "project"
    execution_mode = params.get("execution_mode") or "mock"
    if execution_mode == "live":
        token = params.get("graph_meta_access_token") or ""
        ig_user_id = params.get("instagram_business_account_id") or ""
        fb_page_id = params.get("facebook_page_id") or ""
        graph_version = params.get("instagram_graph_version") or "v23.0"
        image_paths = resolve_path_list(params.get("image_paths") or [])
        caption = params.get("caption") or ""

        if not token or not ig_user_id or not fb_page_id:
            return {
                "provider": "instagram_graph",
                "status": "missing",
                "message": "Instagram live publish credentials are incomplete.",
            }
        if not image_paths:
            return {
                "provider": "instagram_graph",
                "status": "missing_media",
                "message": "No local photo assets were available for Instagram live publish.",
            }

        try:
            publisher = InstagramGraphPublisher(
                access_token=token,
                ig_user_id=ig_user_id,
                fb_page_id=fb_page_id,
                graph_version=graph_version,
            )
            if len(image_paths) >= 2:
                result = publisher.publish_carousel(image_paths, caption)
            else:
                result = publisher.publish_single_image(image_paths[0], caption)
            result["execution_mode"] = "live"
            return result
        except InstagramPublishError as exc:
            return {
                "provider": "instagram_graph",
                "status": "error",
                "message": str(exc),
            }

    return {
        "provider": "mock_instagram",
        "status": "published",
        "permalink": f"mock://instagram/carousel/{project_id}",
        "ig_media_id": f"carousel_{project_id}",
    }


def publish_instagram_reels(params: dict) -> dict:
    project_id = params.get("project_id") or "project"
    execution_mode = params.get("execution_mode") or "mock"
    if execution_mode == "live":
        return {
            "provider": "instagram_graph",
            "status": "manual_ready",
            "message": "Instagram Reels manual handoff package is ready.",
            "manual_handoff": {
                "project_id": project_id,
                "caption": params.get("caption") or "",
                "video_path": params.get("video_path"),
                "preview_artifact_path": params.get("preview_artifact_path"),
                "spec_artifact_path": params.get("spec_artifact_path"),
                "timeline": (params.get("spec") or {}).get("timeline") or [],
            },
        }
    return {
        "provider": "mock_instagram",
        "status": "published",
        "permalink": f"mock://instagram/reels/{project_id}",
        "ig_media_id": f"reels_{project_id}",
    }


def publish_threads(params: dict) -> dict:
    project_id = params.get("project_id") or "project"
    execution_mode = params.get("execution_mode") or "mock"
    if execution_mode == "live":
        token = params.get("threads_access_token") or ""
        threads_user_id = params.get("threads_user_id") or ""
        fb_page_id = params.get("facebook_page_id") or ""
        graph_version = params.get("instagram_graph_version") or "v23.0"
        image_paths = resolve_path_list(params.get("image_paths") or [])
        text = params.get("text") or ""

        if not token or not threads_user_id or not fb_page_id:
            return {
                "provider": "threads",
                "status": "missing",
                "message": "Threads live publish credentials are incomplete.",
            }

        try:
            publisher = ThreadsPublisher(
                access_token=token,
                threads_user_id=threads_user_id,
                fb_page_id=fb_page_id,
                graph_version=graph_version,
            )
            if len(image_paths) >= 2:
                result = publisher.publish_carousel(image_paths[:10], text)
            elif len(image_paths) == 1:
                result = publisher.publish_single_image(image_paths[0], text)
            else:
                result = publisher.publish_text(text)
            result["execution_mode"] = "live"
            return result
        except ThreadsPublishError as exc:
            return {
                "provider": "threads",
                "status": "error",
                "message": str(exc),
            }

    return {
        "provider": "mock_threads",
        "status": "published",
        "permalink": f"mock://threads/{project_id}",
        "threads_media_id": f"threads_{project_id}",
    }


def resolve_path_list(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        candidate = Path(str(value))
        if candidate.exists() and candidate.is_file():
            paths.append(candidate)
    return paths


def render_blog_markdown(spec: dict) -> str:
    title = str(spec.get("title") or "Naver Blog Draft").strip()
    lines = [f"# {title}", ""]
    for section in spec.get("sections", []):
        heading = str(section.get("heading") or "").strip()
        body = str(section.get("body") or "").strip()
        if heading:
            lines.append(f"## {heading}")
        if body:
            lines.append(body)
        lines.append("")
    hashtags = spec.get("hashtags") or []
    if hashtags:
        lines.append(" ".join(str(tag) for tag in hashtags))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def validate_instagram_publish(params: dict) -> dict:
    token = params.get("graph_meta_access_token") or ""
    ig_user_id = params.get("instagram_business_account_id") or ""
    fb_page_id = params.get("facebook_page_id") or ""
    graph_version = params.get("instagram_graph_version") or "v23.0"
    if not token or not ig_user_id or not fb_page_id:
        return {
            "provider": "instagram",
            "status": "missing",
            "message": "Instagram live credentials are incomplete.",
        }
    try:
        InstagramGraphPublisher(
            access_token=token,
            ig_user_id=ig_user_id,
            fb_page_id=fb_page_id,
            graph_version=graph_version,
        ).validate_access()
        return {
            "provider": "instagram",
            "status": "ok",
            "message": "Instagram Graph credentials validated successfully.",
        }
    except InstagramPublishError as exc:
        return {
            "provider": "instagram",
            "status": "error",
            "message": str(exc),
        }


def validate_threads_publish(params: dict) -> dict:
    token = params.get("threads_access_token") or ""
    threads_user_id = params.get("threads_user_id") or ""
    fb_page_id = params.get("facebook_page_id") or ""
    graph_version = params.get("instagram_graph_version") or "v23.0"
    if not token or not threads_user_id or not fb_page_id:
        return {
            "provider": "threads",
            "status": "missing",
            "message": "Threads live credentials are incomplete.",
        }
    try:
        ThreadsPublisher(
            access_token=token,
            threads_user_id=threads_user_id,
            fb_page_id=fb_page_id,
            graph_version=graph_version,
        ).validate_access()
        return {
            "provider": "threads",
            "status": "ok",
            "message": "Threads credentials validated successfully.",
        }
    except ThreadsPublishError as exc:
        return {
            "provider": "threads",
            "status": "error",
            "message": str(exc),
        }


def validate_naver_publish(params: dict) -> dict:
    note = params.get("naver_live_note") or ""
    if note:
        return {
            "provider": "naver",
            "status": "unsupported",
            "message": "Naver live credential notes are saved, but live Naver publishing is not implemented in this phase.",
        }
    return {
        "provider": "naver",
        "status": "missing",
        "message": "No Naver live credential note is saved.",
    }


def plan_turn(params: dict) -> dict:
    turn_index = int(params.get("turn_index") or 0)
    preflight = params.get("preflight") or {}
    answers = params.get("answers") or []
    shop_display_name = params.get("shop_display_name") or "the business"
    hero_label = preflight.get("hero_suggestion_id") or "대표 장면"

    if turn_index == 2:
        previous = (answers[0] if answers else "").strip()
        question = (
            f"{shop_display_name}에서 대표적으로 보이는 {hero_label}를 기준으로, "
            "방금 답변에서 언급한 분위기나 서비스가 실제로 어떻게 진행되는지 더 자세히 설명해 주세요."
        )
        return {
            "ok": True,
            "turn_index": 2,
            "turnIndex": 2,
            "strategy": "detail_deepening",
            "covered_elements": extract_keywords(previous),
            "coveredElements": extract_keywords(previous),
            "missing_elements": ["customer perspective", "specific process detail"],
            "missingElements": ["customer perspective", "specific process detail"],
            "next_question": question,
            "nextQuestion": question,
        }

    if turn_index == 3:
        previous = " ".join(answer.strip() for answer in answers if answer).strip()
        question = (
            f"좋습니다. 마지막으로 {shop_display_name}만의 차별점이나 "
            "사장님이 고객에게 꼭 강조하고 싶은 한 문장을 말씀해 주세요."
        )
        return {
            "ok": True,
            "turn_index": 3,
            "turnIndex": 3,
            "strategy": "owner_perspective",
            "covered_elements": extract_keywords(previous),
            "coveredElements": extract_keywords(previous),
            "missing_elements": ["owner voice", "call-to-action seed"],
            "missingElements": ["owner voice", "call-to-action seed"],
            "next_question": question,
            "nextQuestion": question,
        }

    raise KeyError(f"unsupported turn index: {turn_index}")


def compose_blog(params: dict) -> dict:
    bundle = params.get("bundle") or {}
    profile = bundle.get("generationProfile") or {}
    interview = bundle.get("interview") or {}
    emphasis = profile.get("emphasisPoint") or bundle.get("summary") or "대표 경험"
    title = f"{bundle.get('shopDisplayName', '매장')} | {emphasis}"

    sections = [
        {
            "sectionId": "intro",
            "heading": "처음 방문했을 때 가장 먼저 느껴지는 점",
            "body": interview.get("turn1Answer")
            or f"첫인상은 {emphasis}를 중심으로 형성됩니다.",
        },
        {
            "sectionId": "experience",
            "heading": "서비스가 진행되는 방식",
            "body": interview.get("turn2Answer")
            or "상담부터 마무리까지 차분하고 구조적인 흐름으로 경험이 이어집니다.",
        },
        {
            "sectionId": "owner_voice",
            "heading": "운영자의 관점",
            "body": interview.get("turn3Answer")
            or "운영자의 시선에서 이 공간만의 차별점과 기억에 남는 포인트를 강조합니다.",
        },
    ]

    return {
        "version": "1.0",
        "type": "blog_spec",
        "title": title,
        "sections": sections,
        "hashtags": normalize_hashtags(profile.get("mustIncludeKeywords") or []),
        "metadata": {
            "tone": profile.get("tone") or "friendly",
            "contentLength": profile.get("contentLength") or "standard",
            "industry": profile.get("industry") or "",
        },
    }


def generate_thread(params: dict) -> dict:
    bundle = params.get("bundle") or {}
    profile = bundle.get("generationProfile") or {}
    interview = bundle.get("interview") or {}

    return {
        "version": "1.0",
        "type": "thread_spec",
        "mainPost": f"{bundle.get('shopDisplayName', '이 매장')}은 {profile.get('emphasisPoint') or '차별화된 고객 경험'}을 중심으로 운영됩니다.",
        "reply1": interview.get("turn2Answer")
        or "처음부터 끝까지 의도된 흐름이 느껴지도록 경험을 설계했습니다.",
        "reply2": interview.get("turn3Answer")
        or build_cta(bundle),
        "hashtags": normalize_hashtags(profile.get("mustIncludeKeywords") or []),
        "attachedMediaIds": [profile.get("representativeMediaAssetId")]
        if profile.get("representativeMediaAssetId")
        else [],
    }


def build_slide_headline(index: int, emphasis: str, bundle: dict) -> str:
    if index == 1:
        return bundle.get("shopDisplayName", "대표 스토리")
    if index == 2:
        return "눈에 띄는 포인트"
    if index == 3:
        return "느껴지는 분위기"
    return emphasis[:60]


def build_slide_subheadline(index: int, bundle: dict) -> str:
    interview = bundle.get("interview") or {}
    mapping = {
        1: interview.get("turn1Answer"),
        2: interview.get("turn2Answer"),
        3: interview.get("turn3Answer"),
    }
    value = mapping.get(index)
    if value:
        return value
    return "인터뷰와 프로젝트 미디어를 바탕으로 생성된 문장입니다."


def build_cta(bundle: dict) -> str:
    return f"{bundle.get('shopDisplayName', '이 매장')}의 다음 게시물 초안으로 바로 활용해 보세요."


def transform_text(text: str, mode: str, field_kind: str) -> str:
    value = str(text or "").strip()
    if not value:
        value = "생성된 문장"

    if mode == "regenerate":
        return f"다른 버전: {value}"
    if mode == "tone_shift":
        return f"톤을 바꾼 버전: {value}"
    if mode == "length_shorter":
        parts = value.split()
        shortened = " ".join(parts[: min(len(parts), 8)])
        return shortened or value
    if mode == "length_longer":
        suffix = (
            " 이 버전은 더 구체적인 디테일과 흐름을 추가했습니다."
            if field_kind != "cta"
            else " 직접 경험할 시간을 예약해 보세요."
        )
        return value + suffix
    if mode == "premium":
        return f"프리미엄 강조 버전: {value}"
    if mode == "cta_boost":
        suffix = (
            " 지금 예약하고 다음 방문의 특별한 경험으로 만들어 보세요."
            if field_kind == "cta"
            else " 지금 예약해서 직접 차이를 경험해 보세요."
        )
        return value + suffix
    return value


def build_dispatcher(project_root: str | None = None) -> Dispatcher:
    resolved_root = project_root or str(Path.cwd())
    return Dispatcher(
        start_time=_utc_now(),
        project_root=resolved_root,
        python_executable=sys.executable,
    )
