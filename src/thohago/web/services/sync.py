from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import zipfile

from thohago.artifacts import append_chat_log, write_json
from thohago.config import AppConfig
from thohago.web.event_bus import SessionEventBus
from thohago.web.repositories import SessionRecord, SessionRepository
from thohago.web.services.sessions import SessionService


class SyncValidationError(ValueError):
    pass


@dataclass(slots=True)
class PreviewContext:
    manifest: dict
    manifest_path: Path
    blog_html_content: str | None
    thread_text_content: str | None
    shorts_video_path: str | None
    carousel_image_paths: list[str]


class SyncService:
    def __init__(
        self,
        *,
        config: AppConfig,
        repository: SessionRepository,
        session_service: SessionService,
        event_bus: SessionEventBus,
    ) -> None:
        self.config = config
        self.repository = repository
        self.session_service = session_service
        self.event_bus = event_bus

    def list_sessions(self, *, stage: str | None = None) -> list[SessionRecord]:
        sessions = self.repository.list_sessions(limit=200)
        if stage is None:
            return sessions
        return [session for session in sessions if session.stage == stage]

    def build_download_zip(self, session: SessionRecord) -> bytes:
        artifacts = self.session_service.artifacts_for_session(session)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in artifacts.artifact_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(artifacts.artifact_dir).as_posix())
        return buffer.getvalue()

    def build_customer_delivery_zip(self, session: SessionRecord) -> bytes:
        artifacts = self.session_service.artifacts_for_session(session)
        if not artifacts.published_dir.exists():
            raise SyncValidationError("전달 가능한 결과 파일이 아직 준비되지 않았어요.")

        published_files = [path for path in artifacts.published_dir.rglob("*") if path.is_file()]
        if not published_files:
            raise SyncValidationError("전달 가능한 결과 파일이 아직 준비되지 않았어요.")

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in published_files:
                archive.write(path, arcname=path.relative_to(artifacts.artifact_dir).as_posix())
        return buffer.getvalue()

    def apply_preview_upload(self, session: SessionRecord, *, manifest: dict, bundle_bytes: bytes) -> SessionRecord:
        if session.stage not in {"awaiting_production", "revision_requested", "awaiting_approval"}:
            raise SyncValidationError(f"Session is not ready for preview upload: {session.stage}")
        if manifest.get("session_id") not in {None, session.id}:
            raise SyncValidationError("Manifest session_id does not match the target session.")

        artifacts = self.session_service.artifacts_for_session(session)
        extracted_paths = self._extract_preview_bundle(artifacts.artifact_dir, bundle_bytes)
        normalized_manifest = self._normalize_manifest(manifest)
        manifest_path = artifacts.published_dir / "manifest.json"
        write_json(manifest_path, normalized_manifest)

        self.repository.insert_session_artifact(
            session_id=session.id,
            artifact_type="manifest",
            relative_path=manifest_path.relative_to(artifacts.artifact_dir).as_posix(),
            metadata_json={"status": normalized_manifest.get("status", "preview_ready")},
        )

        for artifact_type, relative_path in self._artifact_entries_from_manifest(normalized_manifest):
            target_path = artifacts.artifact_dir / relative_path
            if not target_path.exists():
                raise SyncValidationError(f"Manifest references missing preview file: {relative_path}")
            self.repository.insert_session_artifact(
                session_id=session.id,
                artifact_type=artifact_type,
                relative_path=relative_path,
            )

        updated = self.repository.update_session_fields(
            session.id,
            stage="awaiting_approval",
            production_completed_at=datetime.now(UTC).isoformat(),
        )
        self.repository.insert_session_message(
            session_id=updated.id,
            sender="system",
            message_type="status",
            text="미리보기가 준비되었어요. 확인 후 승인하거나 수정 요청을 남겨주세요.",
            metadata_json={"stage": updated.stage, "extracted_count": len(extracted_paths)},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=updated.id,
            shop_id=updated.shop_id,
            sender="bot",
            message_type="text",
            text="미리보기가 준비되었어요. 확인 후 승인하거나 수정 요청을 남겨주세요.",
            metadata={"stage": updated.stage},
        )
        self.event_bus.publish(
            updated.id,
            "preview_ready",
            {"url": f"/s/{updated.customer_token}/preview"},
        )
        self.session_service.write_session_metadata(updated)
        return updated

    def approve_preview(self, session: SessionRecord) -> SessionRecord:
        if session.stage not in {"awaiting_approval", "revision_requested"}:
            raise SyncValidationError(f"Session cannot be approved from stage: {session.stage}")
        updated = self.repository.update_session_fields(
            session.id,
            stage="approved",
            approved_at=datetime.now(UTC).isoformat(),
        )
        self._record_customer_decision(updated, action="approve", text="미리보기를 승인했어요.")
        return updated

    def request_revision(self, session: SessionRecord) -> SessionRecord:
        if session.stage not in {"awaiting_approval", "revision_requested"}:
            raise SyncValidationError(f"Session cannot request revision from stage: {session.stage}")
        updated = self.repository.update_session_fields(session.id, stage="revision_requested")
        self._record_customer_decision(updated, action="revision", text="미리보기 수정 요청을 남겼어요.")
        return updated

    def load_preview_context(self, session: SessionRecord) -> PreviewContext:
        artifacts = self.session_service.artifacts_for_session(session)
        manifest_path = artifacts.published_dir / "manifest.json"
        if not manifest_path.exists():
            raise SyncValidationError("Preview manifest is missing.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        blog_html_content = None
        thread_text_content = None
        blog_html_path = manifest.get("blog_html")
        thread_text_path = manifest.get("thread_text")
        if isinstance(blog_html_path, str):
            blog_path = artifacts.artifact_dir / blog_html_path
            if blog_path.exists():
                blog_html_content = blog_path.read_text(encoding="utf-8", errors="ignore")
        if isinstance(thread_text_path, str):
            thread_path = artifacts.artifact_dir / thread_text_path
            if thread_path.exists():
                thread_text_content = thread_path.read_text(encoding="utf-8", errors="ignore")
        carousel_paths = [item for item in manifest.get("carousel_images", []) if isinstance(item, str)]
        shorts_video = manifest.get("shorts_video") if isinstance(manifest.get("shorts_video"), str) else None
        return PreviewContext(
            manifest=manifest,
            manifest_path=manifest_path,
            blog_html_content=blog_html_content,
            thread_text_content=thread_text_content,
            shorts_video_path=shorts_video,
            carousel_image_paths=carousel_paths,
        )

    def resolve_customer_file(self, session: SessionRecord, relative_path: str) -> Path:
        artifacts = self.session_service.artifacts_for_session(session)
        normalized = self._normalize_relative_path(relative_path, require_published_prefix=True)
        candidate = artifacts.artifact_dir / normalized
        if not candidate.exists():
            raise SyncValidationError(f"Artifact not found: {relative_path}")
        return candidate

    def _record_customer_decision(self, session: SessionRecord, *, action: str, text: str) -> None:
        artifacts = self.session_service.artifacts_for_session(session)
        self.repository.insert_session_message(
            session_id=session.id,
            sender="customer",
            message_type="status",
            text=text,
            metadata_json={"action": action, "stage": session.stage},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=session.id,
            shop_id=session.shop_id,
            sender="user",
            message_type="status",
            text=text,
            metadata={"action": action, "stage": session.stage},
        )
        self.session_service.write_session_metadata(session)

    def _extract_preview_bundle(self, artifact_dir: Path, bundle_bytes: bytes) -> list[str]:
        extracted: list[str] = []
        with zipfile.ZipFile(io.BytesIO(bundle_bytes), mode="r") as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                normalized = self._normalize_relative_path(member.filename, require_published_prefix=False)
                if normalized.startswith("published/"):
                    target_relative = normalized
                else:
                    target_relative = f"published/{normalized}"
                target_path = artifact_dir / target_relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(archive.read(member))
                extracted.append(target_relative)
        if not extracted:
            raise SyncValidationError("Preview bundle is empty.")
        return extracted

    def _normalize_manifest(self, manifest: dict) -> dict:
        normalized = dict(manifest)
        normalized["status"] = manifest.get("status", "preview_ready")
        for key in ("shorts_video", "blog_html", "thread_text"):
            value = normalized.get(key)
            if isinstance(value, str) and value:
                normalized[key] = self._normalize_relative_path(value, require_published_prefix=False)
                if not normalized[key].startswith("published/"):
                    normalized[key] = f"published/{normalized[key]}"
        carousel_images = []
        for item in normalized.get("carousel_images", []):
            if isinstance(item, str) and item:
                relative = self._normalize_relative_path(item, require_published_prefix=False)
                if not relative.startswith("published/"):
                    relative = f"published/{relative}"
                carousel_images.append(relative)
        normalized["carousel_images"] = carousel_images
        return normalized

    def _artifact_entries_from_manifest(self, manifest: dict) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        if isinstance(manifest.get("shorts_video"), str):
            items.append(("shorts_video", manifest["shorts_video"]))
        if isinstance(manifest.get("blog_html"), str):
            items.append(("blog_html", manifest["blog_html"]))
        if isinstance(manifest.get("thread_text"), str):
            items.append(("thread_text", manifest["thread_text"]))
        for path in manifest.get("carousel_images", []):
            if isinstance(path, str):
                items.append(("carousel_image", path))
        return items

    def _normalize_relative_path(self, raw_path: str, *, require_published_prefix: bool) -> str:
        normalized = PurePosixPath(raw_path.replace("\\", "/")).as_posix().lstrip("/")
        if not normalized or ".." in PurePosixPath(normalized).parts:
            raise SyncValidationError(f"Invalid relative path: {raw_path}")
        if require_published_prefix and not normalized.startswith("published/"):
            raise SyncValidationError(f"Customer file path must stay inside published/: {raw_path}")
        return normalized
