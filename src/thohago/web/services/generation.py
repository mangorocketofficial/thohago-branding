from __future__ import annotations

import html
import io
import json
import re
import zipfile
from pathlib import Path

from thohago.artifacts import write_json, write_text
from thohago.config import AppConfig
from thohago.content import BlogComposer
from thohago.models import MediaAsset, PlannerOutput, TranscriptArtifact
from thohago.web.repositories import SessionRecord, SessionRepository
from thohago.web.services.sessions import SessionService
from thohago.web.services.sync import SyncService


class ContentGenerationValidationError(ValueError):
    pass


class ContentGenerationService:
    def __init__(
        self,
        *,
        config: AppConfig,
        repository: SessionRepository,
        session_service: SessionService,
        sync_service: SyncService,
    ) -> None:
        self.config = config
        self.repository = repository
        self.session_service = session_service
        self.sync_service = sync_service
        self.blog_composer = BlogComposer()

    def generate_blog_preview(self, session: SessionRecord) -> SessionRecord:
        if session.stage not in {"awaiting_production", "revision_requested"}:
            raise ContentGenerationValidationError(f"Blog generation is not available from stage: {session.stage}")

        artifacts = self.session_service.artifacts_for_session(session)
        shop = self.session_service.get_shop(session)
        preflight = self._require_preflight(session)
        transcripts = self._load_transcripts(artifacts)
        if len(transcripts) < 3:
            raise ContentGenerationValidationError("Interview transcript is incomplete.")

        turn2_planner = self._load_planner(session.turn2_planner_json, turn_index=2)
        turn3_planner = self._load_planner(session.turn3_planner_json, turn_index=3)
        photos = self._build_media_assets(preflight.get("photos", []), expected_kind="photo")
        videos = self._build_media_assets(preflight.get("videos", []), expected_kind="video")
        structure_mode = str(preflight.get("structure_mode") or "key_moments")

        content_bundle = {
            "shop": {
                "shop_id": shop.shop_id,
                "display_name": shop.display_name,
                "publish_targets": shop.publish.targets,
            },
            "session": {
                "session_key": session.session_key,
                "session_id": session.id,
                "artifact_dir": str(artifacts.artifact_dir),
            },
            "photos": [asset.to_dict() for asset in photos],
            "videos": [asset.to_dict() for asset in videos],
            "media_preflight": preflight,
            "interview": {
                "turn1_question": session.turn1_question,
                "turn2_question": turn2_planner.next_question,
                "turn3_question": turn3_planner.next_question,
                "turn1_transcript": transcripts[0].transcript_text,
                "turn2_transcript": transcripts[1].transcript_text,
                "turn3_transcript": transcripts[2].transcript_text,
                "main_angle": turn2_planner.main_angle,
                "covered_elements": turn3_planner.covered_elements,
                "missing_elements": turn3_planner.missing_elements,
                "full_transcript_path": self._latest_full_transcript_path(artifacts).relative_to(artifacts.artifact_dir).as_posix(),
            },
            "structure_mode": structure_mode,
            "experience_sequence": preflight.get("experience_sequence", []),
            "instagram": {
                "carousel_photo_ids": [asset.media_id for asset in photos if asset.selected_for_prompt],
                "photo_count": len([asset for asset in photos if asset.selected_for_prompt]),
            },
        }
        content_bundle_path = artifacts.generated_dir / "content_bundle.json"
        write_json(content_bundle_path, content_bundle)
        self.repository.insert_session_artifact(
            session_id=session.id,
            artifact_type="content_bundle",
            relative_path=content_bundle_path.relative_to(artifacts.artifact_dir).as_posix(),
        )

        try:
            blog_source = self.blog_composer.compose(
                shop=shop,
                photos=photos,
                transcripts=transcripts,
                turn2_planner=turn2_planner,
                turn3_planner=turn3_planner,
                structure_mode=structure_mode,
                allow_fallback=False,
            )
        except Exception as exc:
            raise ContentGenerationValidationError(
                f"Gemini 블로그 생성에 실패했어요. 잠시 후 다시 시도하거나 API quota 상태를 확인해 주세요. ({exc})"
            ) from exc
        blog_source_path = artifacts.generated_dir / "naver_blog_article.md"
        write_text(blog_source_path, blog_source)
        self.repository.insert_session_artifact(
            session_id=session.id,
            artifact_type="blog_article",
            relative_path=blog_source_path.relative_to(artifacts.artifact_dir).as_posix(),
        )

        blog_html = self._render_blog_html_fragment(blog_source, title=shop.display_name)
        bundle_bytes = self._build_blog_preview_bundle(blog_html)
        manifest = {
            "session_id": session.id,
            "status": "preview_ready",
            "blog_html": "published/blog/index.html",
        }
        return self.sync_service.apply_preview_upload(session, manifest=manifest, bundle_bytes=bundle_bytes)

    def _require_preflight(self, session: SessionRecord) -> dict:
        if not session.preflight_json:
            raise ContentGenerationValidationError("Session preflight is missing.")
        return json.loads(session.preflight_json)

    def _load_planner(self, payload: str | None, *, turn_index: int) -> PlannerOutput:
        if not payload:
            raise ContentGenerationValidationError(f"Planner for turn {turn_index} is missing.")
        parsed = json.loads(payload)
        return PlannerOutput(
            turn_index=turn_index,
            main_angle=str(parsed.get("main_angle") or ""),
            covered_elements=[str(item) for item in parsed.get("covered_elements", [])],
            missing_elements=[str(item) for item in parsed.get("missing_elements", [])],
            question_strategy=str(parsed.get("question_strategy") or ""),
            next_question=str(parsed.get("next_question") or ""),
            evidence=[str(item) for item in parsed.get("evidence", [])],
        )

    def _latest_full_transcript_path(self, artifacts) -> Path:
        candidates = sorted(artifacts.generated_dir.glob("interview_full_transcript_*.json"))
        if not candidates:
            raise ContentGenerationValidationError("Full interview transcript is missing.")
        return candidates[-1]

    def _load_transcripts(self, artifacts) -> list[TranscriptArtifact]:
        transcript_path = self._latest_full_transcript_path(artifacts)
        payload = json.loads(transcript_path.read_text(encoding="utf-8"))
        transcripts: list[TranscriptArtifact] = []
        for turn in payload.get("turns", []):
            answer = str(turn.get("answer") or "").strip()
            if not answer:
                continue
            turn_index = int(turn.get("turn_index") or len(transcripts) + 1)
            source_relative_path = str(turn.get("answer_source_path") or f"generated/turn{turn_index}_answer.txt")
            transcripts.append(
                TranscriptArtifact(
                    turn_index=turn_index,
                    source_path=artifacts.artifact_dir / source_relative_path,
                    transcript_text=answer,
                )
            )
        return sorted(transcripts, key=lambda item: item.turn_index)

    def _build_media_assets(self, raw_assets: list[dict], *, expected_kind: str) -> list[MediaAsset]:
        assets: list[MediaAsset] = []
        for index, raw in enumerate(raw_assets, start=1):
            kind = str(raw.get("kind") or expected_kind)
            if kind != expected_kind:
                continue
            source_path = Path(str(raw.get("source_path") or ""))
            assets.append(
                MediaAsset(
                    media_id=str(raw.get("media_id") or f"{expected_kind}_{index}"),
                    kind=kind,
                    source_path=source_path,
                    relative_source_path=str(raw.get("relative_source_path") or source_path),
                    experience_order=int(raw.get("experience_order") or index),
                    preflight_analysis=dict(raw.get("preflight_analysis") or {}),
                    selected_for_prompt=bool(raw.get("selected_for_prompt")),
                    reels_eligible=bool(raw.get("reels_eligible")),
                    duration_sec=raw.get("duration_sec"),
                )
            )
        return assets

    def _build_blog_preview_bundle(self, blog_html: str) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("blog/index.html", blog_html.encode("utf-8"))
        return buffer.getvalue()

    def _render_blog_html_fragment(self, source: str, *, title: str) -> str:
        stripped = source.strip()
        if self._looks_like_html(stripped):
            return stripped

        blocks: list[str] = []
        paragraph_lines: list[str] = []
        list_items: list[str] = []

        def flush_paragraph() -> None:
            nonlocal paragraph_lines
            if paragraph_lines:
                text = "<br>".join(html.escape(line) for line in paragraph_lines)
                blocks.append(f"<p>{text}</p>")
                paragraph_lines = []

        def flush_list() -> None:
            nonlocal list_items
            if list_items:
                items = "".join(f"<li>{html.escape(item)}</li>" for item in list_items)
                blocks.append(f"<ul>{items}</ul>")
                list_items = []

        for raw_line in stripped.splitlines():
            line = raw_line.strip()
            if not line:
                flush_paragraph()
                flush_list()
                continue
            if line.startswith("### "):
                flush_paragraph()
                flush_list()
                blocks.append(f"<h3>{html.escape(line[4:])}</h3>")
                continue
            if line.startswith("## "):
                flush_paragraph()
                flush_list()
                blocks.append(f"<h2>{html.escape(line[3:])}</h2>")
                continue
            if line.startswith("# "):
                flush_paragraph()
                flush_list()
                blocks.append(f"<h1>{html.escape(line[2:])}</h1>")
                continue
            if line.startswith("- "):
                flush_paragraph()
                list_items.append(line[2:].strip())
                continue
            if line.startswith("#"):
                flush_paragraph()
                flush_list()
                blocks.append(f'<p class="hashtags">{html.escape(line)}</p>')
                continue
            paragraph_lines.append(line)

        flush_paragraph()
        flush_list()

        if not blocks:
            blocks.append(f"<p>{html.escape(title)}</p>")
        return "\n".join(blocks)

    def _looks_like_html(self, value: str) -> bool:
        return bool(re.search(r"<[a-zA-Z][^>]*>", value))
