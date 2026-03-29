from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thohago.models import SessionArtifacts, ShopConfig


def create_session_artifacts(artifact_root: Path, shop: ShopConfig, session_key: str) -> SessionArtifacts:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    session_id = f"{session_key}-{timestamp}"
    artifact_dir = artifact_root / shop.shop_id / session_id
    raw_dir = artifact_dir / "raw"
    prompts_dir = artifact_dir / "planners"
    transcripts_dir = artifact_dir / "transcripts"
    generated_dir = artifact_dir / "generated"
    published_dir = artifact_dir / "published"
    for directory in (artifact_dir, raw_dir, prompts_dir, transcripts_dir, generated_dir, published_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return SessionArtifacts(
        shop=shop,
        session_key=session_key,
        session_id=session_id,
        artifact_dir=artifact_dir,
        chat_log_path=artifact_dir / "chat_log.jsonl",
        raw_dir=raw_dir,
        prompts_dir=prompts_dir,
        transcripts_dir=transcripts_dir,
        generated_dir=generated_dir,
        published_dir=published_dir,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_chat_log(
    chat_log_path: Path,
    *,
    session_id: str,
    shop_id: str,
    sender: str,
    message_type: str,
    text: str | None = None,
    file_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    append_jsonl(
        chat_log_path,
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": session_id,
            "shop_id": shop_id,
            "sender": sender,
            "message_type": message_type,
            "text": text,
            "file_paths": file_paths or [],
            "metadata": metadata or {},
        },
    )
