from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
import mimetypes
from pathlib import Path

from thohago.artifacts import append_chat_log, write_json, write_text
from thohago.config import AppConfig
from thohago.interview_engine import HeuristicMultimodalInterviewEngine
from thohago.models import PlannerOutput
from thohago.web.event_bus import SessionEventBus
from thohago.web.repositories import SessionRecord, SessionRepository
from thohago.web.services.pipeline_runtime import resolve_pipeline
from thohago.web.services.question_quality import question_looks_invalid
from thohago.web.services.sessions import SessionService


class InterviewValidationError(ValueError):
    pass


class InterviewTranscriptionError(RuntimeError):
    pass


@dataclass(slots=True)
class InterviewView:
    turn_index: int
    question: str
    is_confirming: bool
    pending_answer: str | None


class InterviewService:
    def __init__(
        self,
        *,
        config: AppConfig,
        repository: SessionRepository,
        session_service: SessionService,
        event_bus: SessionEventBus,
        transcriber: object,
    ) -> None:
        self.config = config
        self.repository = repository
        self.session_service = session_service
        self.event_bus = event_bus
        self.transcriber = transcriber

    def build_view(self, session: SessionRecord) -> InterviewView:
        turn_index = self._stage_to_turn_index(session.stage)
        return InterviewView(
            turn_index=turn_index,
            question=self._question_for_turn(session, turn_index),
            is_confirming=session.stage.startswith("confirming_turn"),
            pending_answer=session.pending_answer,
        )

    def submit_text_answer(self, session: SessionRecord, text: str) -> SessionRecord:
        cleaned = text.strip()
        if not cleaned:
            raise InterviewValidationError("Answer text is required.")
        if session.stage.startswith("confirming_turn"):
            turn_index = self._stage_to_turn_index(session.stage)
            return self.repository.update_session_fields(
                session.id,
                stage=f"confirming_turn{turn_index}",
                pending_answer=cleaned,
            )
        if not session.stage.startswith("awaiting_turn"):
            raise InterviewValidationError("This session is not waiting for an interview answer.")
        turn_index = self._stage_to_turn_index(session.stage)
        return self.repository.update_session_fields(
            session.id,
            stage=f"confirming_turn{turn_index}",
            pending_answer=cleaned,
        )

    def retry_pending_answer(self, session: SessionRecord) -> SessionRecord:
        if not session.stage.startswith("confirming_turn"):
            raise InterviewValidationError("There is no pending answer to retry.")
        turn_index = self._stage_to_turn_index(session.stage)
        return self.repository.update_session_fields(
            session.id,
            stage=f"awaiting_turn{turn_index}_answer",
            pending_answer=None,
        )

    async def record_audio(
        self,
        session: SessionRecord,
        *,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> SessionRecord:
        if not audio_bytes:
            raise InterviewValidationError("Audio upload is empty.")
        turn_index = self._recordable_turn_index(session.stage)
        artifacts = self.session_service.artifacts_for_session(session)
        suffix = self._audio_suffix(filename, content_type)
        audio_path = artifacts.raw_dir / f"turn{turn_index}_audio{suffix}"
        audio_path.write_bytes(audio_bytes)
        relative_path = audio_path.relative_to(artifacts.artifact_dir).as_posix()

        self.repository.insert_media_file(
            session_id=session.id,
            kind="audio",
            role=f"interview_turn{turn_index}",
            filename=audio_path.name,
            relative_path=relative_path,
            mime_type=content_type or mimetypes.guess_type(audio_path.name)[0],
            file_size=len(audio_bytes),
        )
        self.repository.insert_session_message(
            session_id=session.id,
            sender="customer",
            message_type="audio",
            turn_index=turn_index,
            relative_path=relative_path,
            metadata_json={"action": "record"},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=session.id,
            shop_id=session.shop_id,
            sender="user",
            message_type="audio",
            file_paths=[str(audio_path)],
            metadata={"turn_index": turn_index},
        )
        self.session_service.write_session_metadata(session)

        self.event_bus.publish(session.id, "transcribing", {"turn": turn_index})
        try:
            if not hasattr(self.transcriber, "transcribe_audio"):
                raise InterviewTranscriptionError("Configured transcription provider does not support live audio.")
            result = self.transcriber.transcribe_audio(audio_path, language="ko")
        except Exception as exc:
            self.event_bus.publish(session.id, "transcript_failed", {"turn": turn_index, "error": str(exc)})
            raise InterviewTranscriptionError(str(exc)) from exc

        updated = self.repository.update_session_fields(
            session.id,
            stage=f"confirming_turn{turn_index}",
            pending_answer=result.text.strip(),
        )
        self.event_bus.publish(
            session.id,
            "transcript_ready",
            {
                "turn": turn_index,
                "text": updated.pending_answer or "",
            },
        )
        return updated

    def confirm_pending_answer(self, session: SessionRecord) -> SessionRecord:
        if not session.stage.startswith("confirming_turn"):
            raise InterviewValidationError("There is no pending answer to confirm.")

        turn_index = self._stage_to_turn_index(session.stage)
        text = (session.pending_answer or "").strip()
        if not text:
            raise InterviewValidationError("Pending answer is empty.")

        artifacts = self.session_service.artifacts_for_session(session)
        pipeline, _ = resolve_pipeline(self.config)
        preflight = self._require_preflight(session)

        source_path = self._source_path_for_turn(session, turn_index, artifacts)
        if source_path.suffix == ".txt":
            write_text(source_path, text)
        transcript_artifact = pipeline.write_transcript_artifact(
            artifacts=artifacts,
            turn_index=turn_index,
            source_path=source_path,
            transcript_text=text,
        )

        self.repository.insert_session_message(
            session_id=session.id,
            sender="customer",
            message_type="text",
            turn_index=turn_index,
            text=text,
            relative_path=source_path.relative_to(artifacts.artifact_dir).as_posix(),
            metadata_json={"confirmed": True},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=session.id,
            shop_id=session.shop_id,
            sender="user",
            message_type="text",
            text=text,
            metadata={"turn_index": turn_index},
        )

        if turn_index == 1:
            planner, planner_path = pipeline.build_turn_planner(
                artifacts=artifacts,
                turn_index=2,
                transcripts=[text],
                preflight=preflight,
            )
            if question_looks_invalid(planner.next_question):
                fallback_engine = HeuristicMultimodalInterviewEngine()
                planner = fallback_engine.plan_turn(2, [text], preflight)
                planner_path = artifacts.prompts_dir / "turn2_planner.json"
                write_json(planner_path, fallback_engine.build_turn_question_artifact(planner))
                write_text(artifacts.prompts_dir / "turn2_question.txt", planner.next_question)
            updated = self.repository.update_session_fields(
                session.id,
                stage="awaiting_turn2_answer",
                pending_answer=None,
                turn2_planner_json=json.dumps(planner.to_dict(), ensure_ascii=False),
            )
            self._record_system_question(
                session=updated,
                turn_index=2,
                question=planner.next_question,
                planner_path=planner_path,
            )
            self.session_service.write_session_metadata(updated)
            return updated

        if turn_index == 2:
            transcript_texts = self._transcript_texts_for_turns(artifacts, count=2)
            planner, planner_path = pipeline.build_turn_planner(
                artifacts=artifacts,
                turn_index=3,
                transcripts=transcript_texts,
                preflight=preflight,
            )
            if question_looks_invalid(planner.next_question):
                fallback_engine = HeuristicMultimodalInterviewEngine()
                planner = fallback_engine.plan_turn(3, transcript_texts, preflight)
                planner_path = artifacts.prompts_dir / "turn3_planner.json"
                write_json(planner_path, fallback_engine.build_turn_question_artifact(planner))
                write_text(artifacts.prompts_dir / "turn3_question.txt", planner.next_question)
            updated = self.repository.update_session_fields(
                session.id,
                stage="awaiting_turn3_answer",
                pending_answer=None,
                turn3_planner_json=json.dumps(planner.to_dict(), ensure_ascii=False),
            )
            self._record_system_question(
                session=updated,
                turn_index=3,
                question=planner.next_question,
                planner_path=planner_path,
            )
            self.session_service.write_session_metadata(updated)
            return updated

        intake_bundle_path = self._write_intake_bundle(session)
        updated = self.repository.update_session_fields(
            session.id,
            stage="awaiting_production",
            pending_answer=None,
            interview_completed_at=datetime.now(UTC).isoformat(),
        )
        self.repository.insert_session_artifact(
            session_id=updated.id,
            artifact_type="intake_bundle",
            relative_path=intake_bundle_path.relative_to(artifacts.artifact_dir).as_posix(),
            metadata_json={"stage": updated.stage},
        )
        self.repository.insert_session_message(
            session_id=updated.id,
            sender="system",
            message_type="status",
            text="인터뷰가 끝났어요. 이제 제작 준비가 시작됩니다.",
            metadata_json={"stage": updated.stage},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=updated.id,
            shop_id=updated.shop_id,
            sender="bot",
            message_type="text",
            text="인터뷰가 끝났어요. 이제 제작 준비가 시작됩니다.",
            metadata={"stage": updated.stage},
        )
        self.session_service.write_session_metadata(updated)
        return updated

    def _question_for_turn(self, session: SessionRecord, turn_index: int) -> str:
        if turn_index == 1:
            return session.turn1_question or "Turn 1 question is missing."
        if turn_index == 2:
            return self._planner_question(session.turn2_planner_json)
        if turn_index == 3:
            return self._planner_question(session.turn3_planner_json)
        raise InterviewValidationError(f"Unsupported turn index: {turn_index}")

    def _planner_question(self, payload: str | None) -> str:
        if not payload:
            return "Planner question is missing."
        parsed = json.loads(payload)
        return str(parsed.get("next_question") or "Planner question is missing.")

    def _record_system_question(
        self,
        *,
        session: SessionRecord,
        turn_index: int,
        question: str,
        planner_path: Path,
    ) -> None:
        artifacts = self.session_service.artifacts_for_session(session)
        self.repository.insert_session_message(
            session_id=session.id,
            sender="system",
            message_type="text",
            turn_index=turn_index,
            text=question,
            metadata_json={"planner_path": planner_path.relative_to(artifacts.artifact_dir).as_posix()},
        )
        append_chat_log(
            artifacts.chat_log_path,
            session_id=session.id,
            shop_id=session.shop_id,
            sender="bot",
            message_type="text",
            text=question,
            metadata={"turn_index": turn_index, "planner_path": str(planner_path)},
        )

    def _transcript_texts_for_turns(self, artifacts, *, count: int) -> list[str]:
        texts: list[str] = []
        for turn_index in range(1, count + 1):
            transcript_path = artifacts.transcripts_dir / f"turn{turn_index}_transcript.txt"
            texts.append(transcript_path.read_text(encoding="utf-8"))
        return texts

    def _require_preflight(self, session: SessionRecord) -> dict:
        if not session.preflight_json:
            raise InterviewValidationError("Session preflight is missing.")
        return json.loads(session.preflight_json)

    def _write_intake_bundle(self, session: SessionRecord) -> Path:
        artifacts = self.session_service.artifacts_for_session(session)
        active_uploads = self.repository.list_media_files(session.id, role="upload")
        bundle = {
            "shop_id": session.shop_id,
            "session_id": session.id,
            "session_key": session.session_key,
            "stage": "awaiting_production",
            "artifact_dir": session.artifact_dir,
            "preflight_path": "generated/media_preflight.json",
            "turn1_question_path": "planners/turn1_question.txt",
            "turn2_planner_path": "planners/turn2_planner.json",
            "turn3_planner_path": "planners/turn3_planner.json",
            "transcript_paths": [
                "transcripts/turn1_transcript.json",
                "transcripts/turn2_transcript.json",
                "transcripts/turn3_transcript.json",
            ],
            "raw_media": [media.relative_path for media in active_uploads],
        }
        output_path = artifacts.generated_dir / "intake_bundle.json"
        write_json(output_path, bundle)
        return output_path

    def _source_path_for_turn(self, session: SessionRecord, turn_index: int, artifacts) -> Path:
        audio_records = self.repository.list_media_files(session.id, role=f"interview_turn{turn_index}")
        if audio_records:
            return artifacts.artifact_dir / audio_records[-1].relative_path
        return artifacts.transcripts_dir / f"turn{turn_index}_live_input.txt"

    def _stage_to_turn_index(self, stage: str) -> int:
        mapping = {
            "awaiting_turn1_answer": 1,
            "confirming_turn1": 1,
            "awaiting_turn2_answer": 2,
            "confirming_turn2": 2,
            "awaiting_turn3_answer": 3,
            "confirming_turn3": 3,
        }
        if stage not in mapping:
            raise InterviewValidationError(f"Session is not in an interview stage: {stage}")
        return mapping[stage]

    def _recordable_turn_index(self, stage: str) -> int:
        if stage.startswith("awaiting_turn") or stage.startswith("confirming_turn"):
            return self._stage_to_turn_index(stage)
        raise InterviewValidationError(f"Session is not ready for audio recording: {stage}")

    def _audio_suffix(self, filename: str | None, content_type: str | None) -> str:
        suffix = Path(filename or "").suffix.lower()
        if suffix:
            return suffix
        guessed = mimetypes.guess_extension(content_type or "")
        return guessed or ".webm"
