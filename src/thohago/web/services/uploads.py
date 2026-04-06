from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from fastapi import UploadFile

from thohago.artifacts import append_chat_log, write_json, write_text
from thohago.config import AppConfig
from thohago.interview_engine import HeuristicMultimodalInterviewEngine, TURN1_QUESTION_FALLBACK
from thohago.models import PlannerOutput
from thohago.web.config import WebConfig
from thohago.web.repositories import MediaFileRecord, SessionRecord, SessionRepository
from thohago.web.services.pipeline_runtime import resolve_pipeline
from thohago.web.services.question_quality import question_looks_invalid
from thohago.web.services.sessions import SessionService


class UploadValidationError(ValueError):
    pass


class UploadService:
    def __init__(
        self,
        *,
        config: AppConfig,
        web_config: WebConfig,
        repository: SessionRepository,
        session_service: SessionService,
    ) -> None:
        self.config = config
        self.web_config = web_config
        self.repository = repository
        self.session_service = session_service

    def list_active_uploads(self, session: SessionRecord) -> list[MediaFileRecord]:
        return self.repository.list_media_files(session.id, role="upload")

    async def save_uploads(self, session: SessionRecord, uploads: list[UploadFile]) -> list[MediaFileRecord]:
        self._ensure_collecting_media(session)
        if not uploads:
            raise UploadValidationError("파일을 선택해 주세요.")

        active_uploads = self.list_active_uploads(session)
        planned_kinds: list[str] = []
        for upload in uploads:
            if not upload.filename:
                raise UploadValidationError("선택한 파일 중 이름이 없는 파일이 있어요.")
            planned_kinds.append(self._detect_upload_kind(upload))

        self._validate_upload_batch(active_uploads=active_uploads, planned_kinds=planned_kinds)

        saved_records: list[MediaFileRecord] = []
        for upload in uploads:
            saved_records.append(await self._save_single_upload(session, upload))
        return saved_records

    async def _save_single_upload(self, session: SessionRecord, upload: UploadFile) -> MediaFileRecord:
        self._ensure_collecting_media(session)
        if not upload.filename:
            raise UploadValidationError("파일을 선택해 주세요.")

        kind = self._detect_upload_kind(upload)
        active_uploads = self.list_active_uploads(session)
        self._validate_upload_slot(kind=kind, active_uploads=active_uploads)

        artifacts = self.session_service.artifacts_for_session(session)
        index = self._next_available_index(kind, active_uploads)
        suffix = self._resolve_suffix(upload.filename, upload.content_type)
        filename = f"{kind}_{index:02d}{suffix}"
        destination = artifacts.raw_dir / filename

        payload = await upload.read()
        destination.write_bytes(payload)
        relative_path = destination.relative_to(artifacts.artifact_dir).as_posix()
        mime_type = upload.content_type or mimetypes.guess_type(destination.name)[0]

        record = self.repository.insert_media_file(
            session_id=session.id,
            kind=kind,
            role="upload",
            filename=filename,
            relative_path=relative_path,
            mime_type=mime_type,
            file_size=len(payload),
        )
        self.repository.insert_session_message(
            session_id=session.id,
            sender="customer",
            message_type=kind,
            relative_path=relative_path,
            metadata_json={"action": "upload", "filename": filename},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=session.id,
            shop_id=session.shop_id,
            sender="user",
            message_type=kind,
            file_paths=[str(destination)],
            metadata={"action": "upload"},
        )
        self.session_service.write_session_metadata(session)
        return record

    def delete_upload(self, session: SessionRecord, media_file_id: int) -> None:
        self._ensure_collecting_media(session)
        record = self.repository.get_media_file(media_file_id, session_id=session.id)
        if record is None:
            raise UploadValidationError("업로드된 파일을 찾을 수 없어요.")

        artifacts = self.session_service.artifacts_for_session(session)
        target_path = artifacts.artifact_dir / record.relative_path
        if target_path.exists():
            target_path.unlink()
        self.repository.delete_media_file(media_file_id, session_id=session.id)
        self.repository.insert_session_message(
            session_id=session.id,
            sender="customer",
            message_type="status",
            text=f"Deleted {record.kind} upload",
            relative_path=record.relative_path,
            metadata_json={"action": "delete", "media_file_id": media_file_id},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=session.id,
            shop_id=session.shop_id,
            sender="user",
            message_type="status",
            text=f"Deleted upload: {record.filename}",
            file_paths=[str(target_path)],
            metadata={"action": "delete"},
        )
        self.session_service.write_session_metadata(session)

    def finalize_uploads(self, session: SessionRecord) -> SessionRecord:
        self._ensure_collecting_media(session)
        artifacts = self.session_service.artifacts_for_session(session)
        shop = self.session_service.get_shop(session)
        active_uploads = self.list_active_uploads(session)
        photo_paths = [artifacts.artifact_dir / media.relative_path for media in active_uploads if media.kind == "photo"]
        video_paths = [artifacts.artifact_dir / media.relative_path for media in active_uploads if media.kind == "video"]
        if not photo_paths:
            raise UploadValidationError("사진을 한 장 이상 업로드해 주세요.")

        pipeline, engine = self._resolve_pipeline_and_engine()
        preflight, _, _, _ = pipeline.prepare_media_artifacts(
            artifacts=artifacts,
            shop=shop,
            photos=photo_paths,
            videos=video_paths,
        )
        planner = self._plan_turn1(engine=engine, preflight=preflight)
        question_payload = engine.build_turn_question_artifact(planner)
        question_path = artifacts.prompts_dir / "turn1_question.txt"
        planner_path = artifacts.prompts_dir / "turn1_planner.json"
        write_text(question_path, planner.next_question)
        write_json(planner_path, question_payload)

        updated_session = self.repository.update_session_after_preflight(
            session_id=session.id,
            stage="awaiting_turn1_answer",
            preflight_json=json.dumps(preflight, ensure_ascii=False),
            turn1_question=planner.next_question,
        )
        self.repository.insert_session_message(
            session_id=session.id,
            sender="system",
            message_type="text",
            turn_index=1,
            text=planner.next_question,
            metadata_json={"question_strategy": planner.question_strategy},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=updated_session.id,
            shop_id=updated_session.shop_id,
            sender="bot",
            message_type="text",
            text=planner.next_question,
            metadata={"turn_index": 1, "planner_path": str(planner_path)},
        )
        self.session_service.write_session_metadata(updated_session)
        return updated_session

    def _plan_turn1(self, *, engine, preflight: dict) -> PlannerOutput:
        try:
            planner = engine.plan_turn1(preflight)
        except Exception:
            fallback_engine = HeuristicMultimodalInterviewEngine()
            planner = fallback_engine.plan_turn1(preflight)
            engine = fallback_engine
        if not planner.next_question.strip() or question_looks_invalid(planner.next_question):
            return PlannerOutput(
                turn_index=1,
                main_angle="",
                covered_elements=[],
                missing_elements=[],
                question_strategy="scene_anchor",
                next_question=TURN1_QUESTION_FALLBACK,
                evidence=[],
            )
        return planner

    def _resolve_pipeline_and_engine(self):
        return resolve_pipeline(self.config)

    def _ensure_collecting_media(self, session: SessionRecord) -> None:
        if session.stage != "collecting_media":
            raise UploadValidationError("업로드 단계에서만 파일을 변경할 수 있어요.")

    def _detect_upload_kind(self, upload: UploadFile) -> str:
        content_type = (upload.content_type or "").lower()
        suffix = Path(upload.filename or "").suffix.lower()
        if content_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
            return "photo"
        if content_type.startswith("video/") or suffix in {".mp4", ".mov", ".m4v", ".webm"}:
            return "video"
        raise UploadValidationError("지원하지 않는 파일 형식이에요. 사진 또는 영상을 선택해 주세요.")

    def _validate_upload_slot(self, *, kind: str, active_uploads: list[MediaFileRecord]) -> None:
        photo_count = sum(item.kind == "photo" for item in active_uploads)
        video_count = sum(item.kind == "video" for item in active_uploads)
        if kind == "photo" and photo_count >= self.web_config.max_upload_photos:
            raise UploadValidationError(f"사진은 최대 {self.web_config.max_upload_photos}장까지 업로드할 수 있어요.")
        if kind == "video" and video_count >= self.web_config.max_upload_videos:
            raise UploadValidationError(f"영상은 최대 {self.web_config.max_upload_videos}개까지 업로드할 수 있어요.")

    def _validate_upload_batch(self, *, active_uploads: list[MediaFileRecord], planned_kinds: list[str]) -> None:
        photo_count = sum(item.kind == "photo" for item in active_uploads)
        video_count = sum(item.kind == "video" for item in active_uploads)
        photo_count += sum(kind == "photo" for kind in planned_kinds)
        video_count += sum(kind == "video" for kind in planned_kinds)
        if photo_count > self.web_config.max_upload_photos:
            raise UploadValidationError(f"사진은 최대 {self.web_config.max_upload_photos}장까지 업로드할 수 있어요.")
        if video_count > self.web_config.max_upload_videos:
            raise UploadValidationError(f"영상은 최대 {self.web_config.max_upload_videos}개까지 업로드할 수 있어요.")

    def _next_available_index(self, kind: str, active_uploads: list[MediaFileRecord]) -> int:
        used: set[int] = set()
        for item in active_uploads:
            if item.kind != kind:
                continue
            stem = Path(item.filename).stem
            try:
                used.add(int(stem.split("_")[-1]))
            except ValueError:
                continue
        candidate = 1
        while candidate in used:
            candidate += 1
        return candidate

    def _resolve_suffix(self, filename: str, content_type: str | None) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix and len(suffix) <= 6:
            return suffix
        guessed = mimetypes.guess_extension(content_type or "")
        return guessed or ".bin"
