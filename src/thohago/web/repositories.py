from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Row

from thohago.web.database import connect_database


_UNSET = object()


@dataclass(slots=True)
class SessionRecord:
    id: str
    shop_id: str
    session_key: str
    customer_token: str
    stage: str
    artifact_dir: str
    pending_answer: str | None
    preflight_json: str | None
    turn1_question: str | None
    turn2_planner_json: str | None
    turn3_planner_json: str | None
    created_at: str
    updated_at: str
    interview_completed_at: str | None
    production_completed_at: str | None
    approved_at: str | None


@dataclass(slots=True)
class MediaFileRecord:
    id: int
    session_id: str
    kind: str
    role: str
    filename: str
    relative_path: str
    mime_type: str | None
    file_size: int | None
    duration_sec: float | None
    created_at: str


@dataclass(slots=True)
class SessionArtifactRecord:
    id: int
    session_id: str
    artifact_type: str
    relative_path: str
    metadata_json: str | None
    created_at: str


@dataclass(slots=True)
class SessionMessageRecord:
    id: int
    session_id: str
    sender: str
    message_type: str
    turn_index: int | None
    text: str | None
    relative_path: str | None
    metadata_json: str | None
    created_at: str


@dataclass(slots=True)
class SessionEventRecord:
    id: int
    session_id: str
    event_type: str
    data_json: str
    created_at: str


class SessionRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def create_session(
        self,
        *,
        session_id: str,
        shop_id: str,
        session_key: str,
        customer_token: str,
        stage: str,
        artifact_dir: str,
    ) -> SessionRecord:
        now = datetime.now(UTC).isoformat()
        connection = connect_database(self.database_path)
        try:
            connection.execute(
                """
                INSERT INTO sessions(
                    id,
                    shop_id,
                    session_key,
                    customer_token,
                    stage,
                    artifact_dir,
                    pending_answer,
                    preflight_json,
                    turn1_question,
                    turn2_planner_json,
                    turn3_planner_json,
                    created_at,
                    updated_at,
                    interview_completed_at,
                    production_completed_at,
                    approved_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?, NULL, NULL, NULL)
                """,
                (
                    session_id,
                    shop_id,
                    session_key,
                    customer_token,
                    stage,
                    artifact_dir,
                    now,
                    now,
                ),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RuntimeError(f"failed to create session row for {session_id}")
        return self._row_to_session(row)

    def get_by_customer_token(self, customer_token: str) -> SessionRecord | None:
        connection = connect_database(self.database_path)
        try:
            row = connection.execute(
                "SELECT * FROM sessions WHERE customer_token = ?",
                (customer_token,),
            ).fetchone()
        finally:
            connection.close()
        return self._row_to_session(row) if row is not None else None

    def get_by_id(self, session_id: str) -> SessionRecord | None:
        connection = connect_database(self.database_path)
        try:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        finally:
            connection.close()
        return self._row_to_session(row) if row is not None else None

    def list_sessions(self, *, limit: int = 50) -> list[SessionRecord]:
        connection = connect_database(self.database_path)
        try:
            rows = connection.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            connection.close()
        return [self._row_to_session(row) for row in rows]

    def update_session_after_preflight(
        self,
        *,
        session_id: str,
        stage: str,
        preflight_json: str,
        turn1_question: str,
    ) -> SessionRecord:
        now = datetime.now(UTC).isoformat()
        connection = connect_database(self.database_path)
        try:
            connection.execute(
                """
                UPDATE sessions
                SET stage = ?, preflight_json = ?, turn1_question = ?, updated_at = ?
                WHERE id = ?
                """,
                (stage, preflight_json, turn1_question, now, session_id),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RuntimeError(f"failed to update session row for {session_id}")
        return self._row_to_session(row)

    def update_session_fields(
        self,
        session_id: str,
        *,
        stage: str | None = None,
        pending_answer: str | None | object = _UNSET,
        preflight_json: str | None | object = _UNSET,
        turn1_question: str | None | object = _UNSET,
        turn2_planner_json: str | None | object = _UNSET,
        turn3_planner_json: str | None | object = _UNSET,
        interview_completed_at: str | None | object = _UNSET,
        production_completed_at: str | None | object = _UNSET,
        approved_at: str | None | object = _UNSET,
    ) -> SessionRecord:
        updates: list[str] = []
        values: list[object] = []
        if stage is not None:
            updates.append("stage = ?")
            values.append(stage)
        if pending_answer is not _UNSET:
            updates.append("pending_answer = ?")
            values.append(pending_answer)
        if preflight_json is not _UNSET:
            updates.append("preflight_json = ?")
            values.append(preflight_json)
        if turn1_question is not _UNSET:
            updates.append("turn1_question = ?")
            values.append(turn1_question)
        if turn2_planner_json is not _UNSET:
            updates.append("turn2_planner_json = ?")
            values.append(turn2_planner_json)
        if turn3_planner_json is not _UNSET:
            updates.append("turn3_planner_json = ?")
            values.append(turn3_planner_json)
        if interview_completed_at is not _UNSET:
            updates.append("interview_completed_at = ?")
            values.append(interview_completed_at)
        if production_completed_at is not _UNSET:
            updates.append("production_completed_at = ?")
            values.append(production_completed_at)
        if approved_at is not _UNSET:
            updates.append("approved_at = ?")
            values.append(approved_at)
        updates.append("updated_at = ?")
        values.append(datetime.now(UTC).isoformat())
        values.append(session_id)

        connection = connect_database(self.database_path)
        try:
            connection.execute(
                f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
                tuple(values),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RuntimeError(f"failed to update session row for {session_id}")
        return self._row_to_session(row)

    def insert_media_file(
        self,
        *,
        session_id: str,
        kind: str,
        role: str,
        filename: str,
        relative_path: str,
        mime_type: str | None,
        file_size: int | None,
        duration_sec: float | None = None,
    ) -> MediaFileRecord:
        connection = connect_database(self.database_path)
        try:
            cursor = connection.execute(
                """
                INSERT INTO media_files(
                    session_id,
                    kind,
                    role,
                    filename,
                    relative_path,
                    mime_type,
                    file_size,
                    duration_sec
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    kind,
                    role,
                    filename,
                    relative_path,
                    mime_type,
                    file_size,
                    duration_sec,
                ),
            )
            media_file_id = int(cursor.lastrowid)
            connection.commit()
            row = connection.execute("SELECT * FROM media_files WHERE id = ?", (media_file_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RuntimeError(f"failed to insert media_file row for {session_id}")
        return self._row_to_media_file(row)

    def list_media_files(self, session_id: str, *, role: str | None = None) -> list[MediaFileRecord]:
        connection = connect_database(self.database_path)
        try:
            if role is None:
                rows = connection.execute(
                    "SELECT * FROM media_files WHERE session_id = ? ORDER BY id ASC",
                    (session_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM media_files WHERE session_id = ? AND role = ? ORDER BY id ASC",
                    (session_id, role),
                ).fetchall()
        finally:
            connection.close()
        return [self._row_to_media_file(row) for row in rows]

    def get_media_file(self, media_file_id: int, *, session_id: str) -> MediaFileRecord | None:
        connection = connect_database(self.database_path)
        try:
            row = connection.execute(
                "SELECT * FROM media_files WHERE id = ? AND session_id = ?",
                (media_file_id, session_id),
            ).fetchone()
        finally:
            connection.close()
        return self._row_to_media_file(row) if row is not None else None

    def delete_media_file(self, media_file_id: int, *, session_id: str) -> None:
        connection = connect_database(self.database_path)
        try:
            connection.execute(
                "DELETE FROM media_files WHERE id = ? AND session_id = ?",
                (media_file_id, session_id),
            )
            connection.commit()
        finally:
            connection.close()

    def insert_session_message(
        self,
        *,
        session_id: str,
        sender: str,
        message_type: str,
        text: str | None = None,
        turn_index: int | None = None,
        relative_path: str | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        connection = connect_database(self.database_path)
        try:
            connection.execute(
                """
                INSERT INTO session_messages(
                    session_id,
                    sender,
                    message_type,
                    turn_index,
                    text,
                    relative_path,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    sender,
                    message_type,
                    turn_index,
                    text,
                    relative_path,
                    json.dumps(metadata_json, ensure_ascii=False) if metadata_json is not None else None,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def list_session_messages(self, session_id: str, *, limit: int | None = None) -> list[SessionMessageRecord]:
        connection = connect_database(self.database_path)
        try:
            if limit is None:
                rows = connection.execute(
                    "SELECT * FROM session_messages WHERE session_id = ? ORDER BY id ASC",
                    (session_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM session_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
        finally:
            connection.close()
        return [self._row_to_session_message(row) for row in rows]

    def insert_session_artifact(
        self,
        *,
        session_id: str,
        artifact_type: str,
        relative_path: str,
        metadata_json: dict | None = None,
    ) -> SessionArtifactRecord:
        connection = connect_database(self.database_path)
        try:
            cursor = connection.execute(
                """
                INSERT INTO session_artifacts(
                    session_id,
                    artifact_type,
                    relative_path,
                    metadata_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    artifact_type,
                    relative_path,
                    json.dumps(metadata_json, ensure_ascii=False) if metadata_json is not None else None,
                ),
            )
            artifact_id = int(cursor.lastrowid)
            connection.commit()
            row = connection.execute(
                "SELECT * FROM session_artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RuntimeError(f"failed to insert session_artifact row for {session_id}")
        return self._row_to_session_artifact(row)

    def list_session_artifacts(self, session_id: str) -> list[SessionArtifactRecord]:
        connection = connect_database(self.database_path)
        try:
            rows = connection.execute(
                "SELECT * FROM session_artifacts WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        finally:
            connection.close()
        return [self._row_to_session_artifact(row) for row in rows]

    def insert_session_event(
        self,
        *,
        session_id: str,
        event_type: str,
        data: dict,
    ) -> SessionEventRecord:
        connection = connect_database(self.database_path)
        try:
            cursor = connection.execute(
                """
                INSERT INTO session_events(
                    session_id,
                    event_type,
                    data_json
                ) VALUES (?, ?, ?)
                """,
                (
                    session_id,
                    event_type,
                    json.dumps(data, ensure_ascii=False),
                ),
            )
            event_id = int(cursor.lastrowid)
            connection.commit()
            row = connection.execute("SELECT * FROM session_events WHERE id = ?", (event_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            raise RuntimeError(f"failed to insert session_event row for {session_id}")
        return self._row_to_session_event(row)

    def list_session_events_after(self, session_id: str, after_id: int, *, limit: int = 200) -> list[SessionEventRecord]:
        connection = connect_database(self.database_path)
        try:
            rows = connection.execute(
                """
                SELECT * FROM session_events
                WHERE session_id = ? AND id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (session_id, after_id, limit),
            ).fetchall()
        finally:
            connection.close()
        return [self._row_to_session_event(row) for row in rows]

    def _row_to_session(self, row: Row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            shop_id=row["shop_id"],
            session_key=row["session_key"],
            customer_token=row["customer_token"],
            stage=row["stage"],
            artifact_dir=row["artifact_dir"],
            pending_answer=row["pending_answer"],
            preflight_json=row["preflight_json"],
            turn1_question=row["turn1_question"],
            turn2_planner_json=row["turn2_planner_json"],
            turn3_planner_json=row["turn3_planner_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            interview_completed_at=row["interview_completed_at"],
            production_completed_at=row["production_completed_at"],
            approved_at=row["approved_at"],
        )

    def _row_to_media_file(self, row: Row) -> MediaFileRecord:
        return MediaFileRecord(
            id=row["id"],
            session_id=row["session_id"],
            kind=row["kind"],
            role=row["role"],
            filename=row["filename"],
            relative_path=row["relative_path"],
            mime_type=row["mime_type"],
            file_size=row["file_size"],
            duration_sec=row["duration_sec"],
            created_at=row["created_at"],
        )

    def _row_to_session_artifact(self, row: Row) -> SessionArtifactRecord:
        return SessionArtifactRecord(
            id=row["id"],
            session_id=row["session_id"],
            artifact_type=row["artifact_type"],
            relative_path=row["relative_path"],
            metadata_json=row["metadata_json"],
            created_at=row["created_at"],
        )

    def _row_to_session_message(self, row: Row) -> SessionMessageRecord:
        return SessionMessageRecord(
            id=row["id"],
            session_id=row["session_id"],
            sender=row["sender"],
            message_type=row["message_type"],
            turn_index=row["turn_index"],
            text=row["text"],
            relative_path=row["relative_path"],
            metadata_json=row["metadata_json"],
            created_at=row["created_at"],
        )

    def _row_to_session_event(self, row: Row) -> SessionEventRecord:
        return SessionEventRecord(
            id=row["id"],
            session_id=row["session_id"],
            event_type=row["event_type"],
            data_json=row["data_json"],
            created_at=row["created_at"],
        )
