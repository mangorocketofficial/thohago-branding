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

import httpx
from fastapi.testclient import TestClient
import uvicorn

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class WebPhase6Tests(unittest.TestCase):
    def test_interview_page_includes_voice_controls_and_sse_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase6_ui")
            response = client.get(f"/s/{session.customer_token}/interview")
            self.assertEqual(response.status_code, 200)
            self.assertIn("chat-composer-shell", response.text)
            self.assertIn("composer-field", response.text)
            self.assertIn("composer-inline-actions", response.text)
            self.assertIn("composer-mic-button", response.text)
            self.assertIn("composer-field-indicator", response.text)
            self.assertIn("start-recording", response.text)
            self.assertIn("stop-recording", response.text)
            self.assertIn("/events", response.text)
            self.assertIn("recorder.js", response.text)
            self.assertNotIn("말로 답변하기", response.text)
            self.assertNotIn("직접 입력하기", response.text)

    def test_record_audio_stores_file_and_sets_pending_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase6_record")
            response = client.post(
                f"/s/{session.customer_token}/interview/record",
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
            media_files = app.state.runtime.session_repository.list_media_files(updated.id, role="interview_turn1")
            self.assertEqual(len(media_files), 1)
            self.assertEqual(media_files[0].kind, "audio")

    def test_sse_emits_transcribing_and_transcript_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase6_sse")
            with self._run_live_server(app) as base_url:
                events = self._collect_sse_events(
                    base_url=base_url,
                    customer_token=session.customer_token,
                    trigger=lambda: self._post_audio(base_url, session.customer_token, b"voice", "audio/webm"),
                )
            event_names = [event[0] for event in events]
            self.assertEqual(event_names[:2], ["transcribing", "transcript_ready"])
            self.assertIn("[stub transcript]", events[1][1]["text"])

    def test_sse_emits_transcript_failed_when_transcriber_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase6_fail")

            class FailingTranscriber:
                def transcribe_audio(self, audio_path: Path, language: str = "ko"):
                    raise RuntimeError("forced transcription failure")

            app.state.runtime.transcriber = FailingTranscriber()
            app.state.runtime.interview_service.transcriber = app.state.runtime.transcriber

            with self._run_live_server(app) as base_url:
                events = self._collect_sse_events(
                    base_url=base_url,
                    customer_token=session.customer_token,
                    trigger=lambda: self._post_audio(base_url, session.customer_token, b"voice", "audio/webm", expect_error=True),
                )
            event_names = [event[0] for event in events]
            self.assertEqual(event_names[:2], ["transcribing", "transcript_failed"])
            self.assertIn("forced transcription failure", events[1][1]["error"])

    def test_voice_answer_can_be_confirmed_through_existing_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase6_confirm")
            record = client.post(
                f"/s/{session.customer_token}/interview/record",
                files={"audio": ("turn1.webm", b"fake-audio-bytes", "audio/webm")},
            )
            self.assertEqual(record.status_code, 202)

            confirm = client.post(
                f"/s/{session.customer_token}/interview/confirm",
                follow_redirects=False,
            )
            self.assertEqual(confirm.status_code, 303)
            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_turn2_answer")

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            transcript_json_path = artifacts.transcripts_dir / "turn1_transcript.json"
            self.assertTrue(transcript_json_path.exists())
            transcript_payload = json.loads(transcript_json_path.read_text(encoding="utf-8"))
            self.assertTrue(str(transcript_payload["source_path"]).endswith("turn1_audio.webm"))

    def _post_audio(self, base_url: str, customer_token: str, payload: bytes, content_type: str, expect_error: bool = False) -> None:
        with httpx.Client(base_url=base_url, timeout=30) as client:
            response = client.post(
                f"/s/{customer_token}/interview/record",
                files={"audio": ("turn_audio.webm", payload, content_type)},
            )
            if expect_error:
                self.assertEqual(response.status_code, 502)
            else:
                self.assertEqual(response.status_code, 202)

    def _collect_sse_events(self, *, base_url: str, customer_token: str, trigger) -> list[tuple[str, dict]]:
        events: list[tuple[str, dict]] = []

        def run_trigger():
            time.sleep(0.2)
            trigger()

        trigger_thread = threading.Thread(target=run_trigger, daemon=True)
        trigger_thread.start()

        with httpx.Client(base_url=base_url, timeout=30) as client:
            with client.stream("GET", f"/s/{customer_token}/events") as response:
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
            "THOHAGO_ADMIN_USERNAME": "phase6-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase6-password",
            "THOHAGO_SYNC_API_TOKEN": "phase6-sync-token",
            "THOHAGO_WEB_STT_MODE": "stub",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
