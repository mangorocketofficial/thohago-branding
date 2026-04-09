from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class WebPhase2Tests(unittest.TestCase):
    def test_upload_persists_photo_and_indexes_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, sample_image = self._build_client(Path(tmp_dir))
            created = app.state.runtime.session_service.create_session(
                shop_id="sisun8082",
                session_key="web_phase2_upload",
            )

            with sample_image.open("rb") as handle:
                response = client.post(
                    f"/s/{created.session.customer_token}/upload",
                    files={"media": (sample_image.name, handle, "image/jpeg")},
                )
            self.assertEqual(response.status_code, 200)
            self.assertIn("photo_01.jpg", response.text)

            media_files = app.state.runtime.session_repository.list_media_files(created.session.id, role="upload")
            self.assertEqual(len(media_files), 1)
            self.assertEqual(media_files[0].kind, "photo")

            artifact_dir = Path(created.artifacts.artifact_dir)
            uploaded_path = artifact_dir / media_files[0].relative_path
            self.assertTrue(uploaded_path.exists())

            connection = sqlite3.connect(app.state.runtime.web_config.database_path)
            try:
                messages = connection.execute(
                    "SELECT sender, message_type, relative_path FROM session_messages WHERE session_id = ?",
                    (created.session.id,),
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0][0], "customer")
            self.assertEqual(messages[0][1], "photo")
            self.assertTrue((artifact_dir / "chat_log.jsonl").exists())
            self.assertIn('"message_type": "photo"', (artifact_dir / "chat_log.jsonl").read_text(encoding="utf-8"))

    def test_upload_accepts_multiple_files_in_one_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, sample_image = self._build_client(Path(tmp_dir))
            created = app.state.runtime.session_service.create_session(
                shop_id="sisun8082",
                session_key="web_phase2_multi_upload",
            )

            response = client.post(
                f"/s/{created.session.customer_token}/upload",
                files=[
                    ("media", (sample_image.name, sample_image.read_bytes(), "image/jpeg")),
                    ("media", ("clip.mp4", b"fake-video-bytes", "video/mp4")),
                ],
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("photo_01.jpg", response.text)
            self.assertIn("video_01.mp4", response.text)

            media_files = app.state.runtime.session_repository.list_media_files(created.session.id, role="upload")
            self.assertEqual(len(media_files), 2)
            self.assertEqual({item.kind for item in media_files}, {"photo", "video"})

    def test_delete_upload_removes_active_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, sample_image = self._build_client(Path(tmp_dir))
            created = app.state.runtime.session_service.create_session(
                shop_id="sisun8082",
                session_key="web_phase2_delete",
            )

            with sample_image.open("rb") as handle:
                client.post(
                    f"/s/{created.session.customer_token}/upload",
                    files={"media": (sample_image.name, handle, "image/jpeg")},
                )

            media_file = app.state.runtime.session_repository.list_media_files(created.session.id, role="upload")[0]
            artifact_dir = Path(created.artifacts.artifact_dir)
            uploaded_path = artifact_dir / media_file.relative_path
            self.assertTrue(uploaded_path.exists())

            response = client.post(
                f"/s/{created.session.customer_token}/upload/delete",
                data={"media_file_id": str(media_file.id)},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("아직 업로드한 파일이 없어요.", response.text)
            self.assertFalse(uploaded_path.exists())
            self.assertEqual(
                app.state.runtime.session_repository.list_media_files(created.session.id, role="upload"),
                [],
            )

    def test_upload_limit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, sample_image = self._build_client(Path(tmp_dir))
            created = app.state.runtime.session_service.create_session(
                shop_id="sisun8082",
                session_key="web_phase2_limit",
            )

            for _ in range(5):
                with sample_image.open("rb") as handle:
                    response = client.post(
                        f"/s/{created.session.customer_token}/upload",
                        files={"media": (sample_image.name, handle, "image/jpeg")},
                    )
                self.assertEqual(response.status_code, 200)

            with sample_image.open("rb") as handle:
                overflow = client.post(
                    f"/s/{created.session.customer_token}/upload",
                    files={"media": (sample_image.name, handle, "image/jpeg")},
                )
            self.assertEqual(overflow.status_code, 400)
            self.assertIn("사진은 최대 5장", overflow.text)

    def test_finalize_without_photo_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, _ = self._build_client(Path(tmp_dir))
            created = app.state.runtime.session_service.create_session(
                shop_id="sisun8082",
                session_key="web_phase2_no_photo",
            )

            response = client.post(f"/s/{created.session.customer_token}/upload/done")
            self.assertEqual(response.status_code, 400)
            self.assertIn("사진을 한 장 이상 업로드해 주세요.", response.text)

    def test_finalize_writes_preflight_and_turn1_and_routes_to_interview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, sample_image = self._build_client(Path(tmp_dir))
            created = app.state.runtime.session_service.create_session(
                shop_id="sisun8082",
                session_key="web_phase2_finalize",
            )

            with sample_image.open("rb") as handle:
                upload_response = client.post(
                    f"/s/{created.session.customer_token}/upload",
                    files={"media": (sample_image.name, handle, "image/jpeg")},
                )
            self.assertEqual(upload_response.status_code, 200)

            finalize_response = client.post(
                f"/s/{created.session.customer_token}/upload/done",
                follow_redirects=False,
            )
            self.assertEqual(finalize_response.status_code, 303)
            self.assertEqual(finalize_response.headers["location"], f"/s/{created.session.customer_token}/interview")

            interview_page = client.get(finalize_response.headers["location"])
            self.assertEqual(interview_page.status_code, 200)
            self.assertIn("첫번째 질문", interview_page.text)

            updated = app.state.runtime.session_repository.get_by_id(created.session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_turn1_answer")
            self.assertIsNotNone(updated.preflight_json)
            self.assertIsNotNone(updated.turn1_question)
            self.assertIn(updated.turn1_question, interview_page.text)

            artifact_dir = Path(created.artifacts.artifact_dir)
            preflight_path = artifact_dir / "generated" / "media_preflight.json"
            turn1_question_path = artifact_dir / "planners" / "turn1_question.txt"
            turn1_planner_path = artifact_dir / "planners" / "turn1_planner.json"
            metadata_path = artifact_dir / "session_metadata.json"

            self.assertTrue(preflight_path.exists())
            self.assertTrue(turn1_question_path.exists())
            self.assertTrue(turn1_planner_path.exists())
            self.assertTrue(metadata_path.exists())

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["stage"], "awaiting_turn1_answer")
            self.assertEqual(turn1_question_path.read_text(encoding="utf-8"), updated.turn1_question)
            planner_payload = json.loads(turn1_planner_path.read_text(encoding="utf-8"))
            self.assertEqual(planner_payload["next_question"], updated.turn1_question)
            preflight_payload = json.loads(preflight_path.read_text(encoding="utf-8"))
            self.assertIn("experience_sequence", preflight_payload)
            landing = client.get(f"/s/{created.session.customer_token}", follow_redirects=False)
            self.assertEqual(landing.status_code, 307)
            self.assertEqual(landing.headers["location"], f"/s/{created.session.customer_token}/interview")

    def _build_client(self, tmp_root: Path) -> tuple[TestClient, object, Path]:
        env = self._web_env(tmp_root)
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        config = load_config()
        shops = load_shop_registry(config.shops_file)
        app = create_app(config=config, shops=shops)
        sample_session = shops["sisun8082"].sample_sessions["2026_03_27_core"]
        sample_image = next(sample_session.image_dir.glob("*.jpg"))
        return TestClient(app), app, sample_image

    def _web_env(self, tmp_root: Path) -> dict[str, str]:
        return {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase2-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase2-password",
            "THOHAGO_SYNC_API_TOKEN": "phase2-sync-token",
            "THOHAGO_DEFAULT_INTERVIEW_ENGINE": "heuristic",
            "GEMINI_API_KEY": "",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
