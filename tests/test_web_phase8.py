from __future__ import annotations

import json
import os
import socket
import threading
import time
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import io
import zipfile

import httpx
from fastapi.testclient import TestClient
import uvicorn

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class WebPhase8Tests(unittest.TestCase):
    def test_transcript_events_are_stored_durably(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase8_store")
            response = client.post(
                f"/s/{session.customer_token}/interview/record",
                files={"audio": ("turn1.webm", b"voice", "audio/webm")},
            )
            self.assertEqual(response.status_code, 202)
            events = app.state.runtime.session_repository.list_session_events_after(session.id, 0)
            self.assertEqual([event.event_type for event in events[:2]], ["transcribing", "transcript_ready"])
            self.assertLess(events[0].id, events[1].id)

    def test_sse_replays_events_after_last_event_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase8_replay")
            client.post(
                f"/s/{session.customer_token}/interview/record",
                files={"audio": ("turn1.webm", b"voice", "audio/webm")},
            )
            stored = app.state.runtime.session_repository.list_session_events_after(session.id, 0)
            first_event_id = stored[0].id

            with self._run_live_server(app) as base_url:
                replayed = self._collect_sse_events(
                    base_url=base_url,
                    customer_token=session.customer_token,
                    last_event_id=first_event_id,
                    stop_after=1,
                )
            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0][0], "transcript_ready")
            self.assertEqual(replayed[0][1]["id"], stored[1].id)

    def test_preview_upload_publishes_durable_preview_ready_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase8_preview")
            source_dir, manifest_path = self._build_preview_source(Path(tmp_dir))
            bundle = io.BytesIO()
            with zipfile.ZipFile(bundle, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in source_dir.rglob("*"):
                    if path.is_file():
                        archive.write(path, arcname=path.relative_to(source_dir).as_posix())

            response = client.post(
                f"/api/sync/sessions/{session.id}/upload",
                headers={"Authorization": "Bearer phase8-sync-token"},
                data={"manifest_json": manifest_path.read_text(encoding="utf-8")},
                files={"bundle": ("preview_bundle.zip", bundle.getvalue(), "application/zip")},
            )
            self.assertEqual(response.status_code, 200)

            stored = app.state.runtime.session_repository.list_session_events_after(session.id, 0)
            self.assertEqual(stored[-1].event_type, "preview_ready")

            with self._run_live_server(app) as base_url:
                replayed = self._collect_sse_events(
                    base_url=base_url,
                    customer_token=session.customer_token,
                    last_event_id=0,
                    stop_after=1,
                )
            self.assertEqual(replayed[0][0], "preview_ready")
            self.assertIn("/preview", replayed[0][1]["data"]["url"])

    def test_waiting_page_contains_preview_ready_listener(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase8_wait")
            response = client.get(f"/s/{session.customer_token}/waiting")
            self.assertEqual(response.status_code, 200)
            self.assertIn("/events", response.text)
            self.assertIn('addEventListener("preview_ready"', response.text)
            self.assertIn("SSE 이벤트가 오면 미리보기 화면으로 바로 이동합니다.", response.text)

    def _collect_sse_events(
        self,
        *,
        base_url: str,
        customer_token: str,
        last_event_id: int,
        stop_after: int,
    ) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []
        with httpx.Client(base_url=base_url, timeout=30) as client:
            with client.stream(
                "GET",
                f"/s/{customer_token}/events",
                headers={"Last-Event-ID": str(last_event_id)},
            ) as response:
                current_event = None
                current_id = None
                for raw_line in response.iter_lines():
                    if not raw_line or raw_line.startswith(":"):
                        continue
                    if raw_line.startswith("id: "):
                        current_id = int(raw_line.split(": ", 1)[1])
                    elif raw_line.startswith("event: "):
                        current_event = raw_line.split(": ", 1)[1]
                    elif raw_line.startswith("data: "):
                        payload = json.loads(raw_line.split(": ", 1)[1])
                        events.append((current_event or "", {"id": current_id, "data": payload}))
                        if len(events) >= stop_after:
                            break
        return events

    def _prepare_interview_ready_session(self, tmp_root: Path, session_key: str):
        env = self._web_env(tmp_root)
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        config = load_config()
        shops = load_shop_registry(config.shops_file)
        app = create_app(config=config, shops=shops)
        client = TestClient(app)
        sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))

        created = app.state.runtime.session_service.create_session(shop_id="sisun8082", session_key=session_key)
        with sample_image.open("rb") as handle:
            client.post(
                f"/s/{created.session.customer_token}/upload",
                files={"media": (sample_image.name, handle, "image/jpeg")},
            )
        client.post(f"/s/{created.session.customer_token}/upload/done", follow_redirects=False)
        session = app.state.runtime.session_repository.get_by_id(created.session.id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_turn1_answer")
        return client, app, session

    def _prepare_awaiting_production_session(self, tmp_root: Path, session_key: str):
        client, app, session = self._prepare_interview_ready_session(tmp_root, session_key)
        for answer in ["첫 번째 답변", "두 번째 답변", "세 번째 답변"]:
            client.post(
                f"/s/{session.customer_token}/interview/submit",
                data={"answer_text": answer},
                follow_redirects=False,
            )
            client.post(f"/s/{session.customer_token}/interview/confirm", follow_redirects=False)
            session = app.state.runtime.session_repository.get_by_id(session.id)
            assert session is not None
        self.assertEqual(session.stage, "awaiting_production")
        return client, app, session

    def _build_preview_source(self, tmp_root: Path) -> tuple[Path, Path]:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))
        source_dir = tmp_root / "preview_source"
        (source_dir / "shorts").mkdir(parents=True, exist_ok=True)
        (source_dir / "blog").mkdir(parents=True, exist_ok=True)
        (source_dir / "threads").mkdir(parents=True, exist_ok=True)
        (source_dir / "carousel").mkdir(parents=True, exist_ok=True)
        (source_dir / "shorts" / "preview.mp4").write_bytes(b"fake-mp4-bytes")
        (source_dir / "blog" / "index.html").write_text("<article><h1>Phase 8 Blog Preview</h1></article>", encoding="utf-8")
        (source_dir / "threads" / "thread.txt").write_text("Phase 8 thread preview", encoding="utf-8")
        (source_dir / "carousel" / "slide_01.jpg").write_bytes(sample_image.read_bytes())
        manifest_path = tmp_root / "preview_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "preview_ready",
                    "shorts_video": "published/shorts/preview.mp4",
                    "blog_html": "published/blog/index.html",
                    "thread_text": "published/threads/thread.txt",
                    "carousel_images": ["published/carousel/slide_01.jpg"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return source_dir, manifest_path

    @contextmanager
    def _run_live_server(self, app):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()
        server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        try:
            yield f"http://{host}:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)

    def _web_env(self, tmp_root: Path) -> dict[str, str]:
        return {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase8-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase8-password",
            "THOHAGO_SYNC_API_TOKEN": "phase8-sync-token",
            "THOHAGO_WEB_STT_MODE": "stub",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
