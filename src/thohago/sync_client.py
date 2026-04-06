from __future__ import annotations

import io
import json
from pathlib import Path
import zipfile

import httpx


def list_sessions(*, base_url: str, token: str, stage: str | None = None) -> dict:
    with _client(base_url, token) as client:
        response = client.get("/api/sync/sessions", params={"stage": stage} if stage else None)
        response.raise_for_status()
        return response.json()


def pull_session(*, base_url: str, token: str, session_id: str, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with _client(base_url, token) as client:
        response = client.get(f"/api/sync/sessions/{session_id}/download")
        response.raise_for_status()
    zip_path = output_dir / f"{session_id}.zip"
    zip_path.write_bytes(response.content)
    extract_dir = output_dir / session_id
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content), mode="r") as archive:
        archive.extractall(extract_dir)
    return zip_path, extract_dir


def push_session(
    *,
    base_url: str,
    token: str,
    session_id: str,
    source_dir: Path,
    manifest_path: Path,
) -> dict:
    bundle_bytes = _build_bundle_bytes(source_dir=source_dir, manifest_path=manifest_path)
    manifest_json = json.loads(manifest_path.read_text(encoding="utf-8"))
    with _client(base_url, token) as client:
        response = client.post(
            f"/api/sync/sessions/{session_id}/upload",
            data={"manifest_json": json.dumps(manifest_json, ensure_ascii=False)},
            files={"bundle": ("preview_bundle.zip", bundle_bytes, "application/zip")},
        )
        response.raise_for_status()
        return response.json()


def _build_bundle_bytes(*, source_dir: Path, manifest_path: Path) -> bytes:
    buffer = io.BytesIO()
    manifest_resolved = manifest_path.resolve()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in source_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.resolve() == manifest_resolved:
                continue
            archive.write(path, arcname=path.relative_to(source_dir).as_posix())
    return buffer.getvalue()


def _client(base_url: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
