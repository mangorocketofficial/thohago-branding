from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
import uvicorn

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class MobileV1Phase7Tests(unittest.TestCase):
    def test_app_interview_page_includes_voice_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_interview_ready_app_session(Path(tmp_dir))
            response = client.get(f"/app/session/{session.id}")
            self.assertEqual(response.status_code, 200)
            self.assertIn("voice-answer-panel", response.text)
            self.assertIn("composer-mic-button", response.text)
            self.assertIn("start-recording", response.text)
            self.assertIn("stop-recording", response.text)
            self.assertIn("/app/session/", response.text)
            self.assertIn("recorder.js", response.text)
            self.assertNotIn("자유 입력은 인터뷰 답변에서만 사용할 수 있어요.", response.text)

    def test_app_record_audio_stores_file_and_sets_pending_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_app_session(Path(tmp_dir))
            response = client.post(
                f"/app/session/{session.id}/interview/record",
                files={"audio": ("turn1.webm", b"fake-audio-bytes", "audio/webm")},
            )
            self.assertEqual(response.status_code, 202)
            payload = response.json()
            self.assertEqual(payload["stage"], "confirming_turn1")

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "confirming_turn1")
            self.assertIn("[stub transcript]", updated.pending_answer or "")

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            audio_path = artifacts.raw_dir / "turn1_audio.webm"
            self.assertTrue(audio_path.exists())

    def test_app_events_emit_transcribing_and_transcript_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _, app, session = self._prepare_interview_ready_app_session(Path(tmp_dir))
            with self._run_live_server(app) as base_url:
                events = self._collect_sse_events(
                    base_url=base_url,
                    session_id=session.id,
                    trigger=lambda: self._post_audio(base_url, session.id, b"voice", "audio/webm"),
                )
            event_names = [event[0] for event in events]
            self.assertEqual(event_names[:2], ["transcribing", "transcript_ready"])
            self.assertIn("[stub transcript]", events[1][1]["text"])

    def _post_audio(self, base_url: str, session_id: str, payload: bytes, content_type: str) -> None:
        with httpx.Client(base_url=base_url, timeout=30) as client:
            response = client.get("/app/sign-in/google", follow_redirects=False)
            cookies = response.cookies
            response = client.post(
                f"/app/session/{session_id}/interview/record",
                files={"audio": ("turn_audio.webm", payload, content_type)},
                cookies=cookies,
            )
            self.assertEqual(response.status_code, 202)

    def _collect_sse_events(self, *, base_url: str, session_id: str, trigger) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []

        def run_trigger():
            time.sleep(0.2)
            trigger()

        trigger_thread = threading.Thread(target=run_trigger, daemon=True)
        trigger_thread.start()

        with httpx.Client(base_url=base_url, timeout=30) as client:
            auth = client.get("/app/sign-in/google", follow_redirects=False)
            cookies = auth.cookies
            with client.stream("GET", f"/app/session/{session_id}/events", cookies=cookies) as response:
                current_event = None
                for raw_line in response.iter_lines():
                    if not raw_line or raw_line.startswith(":"):
                        continue
                    if raw_line.startswith("event: "):
                        current_event = raw_line.split(": ", 1)[1]
                    elif raw_line.startswith("data: "):
                        payload = json.loads(raw_line.split(": ", 1)[1])
                        events.append((current_event or "", payload))
                        if len(events) >= 2:
                            break
        trigger_thread.join(timeout=5)
        return events

    def _prepare_interview_ready_app_session(self, tmp_root: Path):
        env = self._web_env(tmp_root)
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        config = load_config()
        shops = load_shop_registry(config.shops_file)
        app = create_app(config=config, shops=shops)
        client = TestClient(app)

        client.get("/app/sign-in/google")
        created = client.post("/app/sessions/new", follow_redirects=False)
        session_id = created.headers["location"].rsplit("/", 1)[-1]
        sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))

        with sample_image.open("rb") as handle:
            client.post(
                f"/app/session/{session_id}/upload",
                files=[("media", (sample_image.name, handle, "image/jpeg"))],
            )
        finalize = client.post(f"/app/session/{session_id}/upload/complete", follow_redirects=False)
        self.assertEqual(finalize.status_code, 303)

        session = app.state.runtime.session_repository.get_by_id(session_id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_turn1_answer")
        return client, app, session

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
            "THOHAGO_WEB_BASE_URL": "https://mobile.thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase7-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase7-password",
            "THOHAGO_SYNC_API_TOKEN": "phase7-sync-token",
            "THOHAGO_WEB_STT_MODE": "stub",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
            "GEMINI_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
