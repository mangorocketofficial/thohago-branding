from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class MobileV1Phase2Tests(unittest.TestCase):
    def test_workspace_creates_real_persisted_app_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            self._sign_in_and_onboard(client)

            created = client.post("/app/sessions/new", follow_redirects=False)
            self.assertEqual(created.status_code, 303)
            session_path = created.headers["location"]
            self.assertTrue(session_path.startswith("/app/session/"))

            session_id = session_path.rsplit("/", 1)[-1]
            runtime = client.app.state.runtime
            session = runtime.session_repository.get_by_id(session_id)

            self.assertIsNotNone(session)
            self.assertTrue(session.session_key.startswith("mobile_v1_app_"))
            self.assertEqual(session.stage, "collecting_media")

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn(session_id, workspace.text)
            self.assertIn("업로드 중", workspace.text)

    def test_app_session_accepts_photo_and_video_uploads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            session_id = self._create_session(client)
            runtime = client.app.state.runtime
            session = runtime.session_repository.get_by_id(session_id)

            session_page = client.get(f"/app/session/{session_id}")
            self.assertEqual(session_page.status_code, 200)
            self.assertIn("data-upload-loading-modal", session_page.text)
            self.assertIn("업로드 중입니다", session_page.text)
            self.assertIn("data-upload-loading-percent", session_page.text)
            self.assertIn("data-upload-loading-bar", session_page.text)

            response = client.post(
                f"/app/session/{session_id}/upload",
                files=[
                    ("media", ("photo_01.jpg", b"fake-image-1", "image/jpeg")),
                    ("media", ("clip_01.mp4", b"fake-video-1", "video/mp4")),
                ],
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("photo_01.jpg", response.text)
            self.assertIn("video_01.mp4", response.text)

            media_files = runtime.session_repository.list_media_files(session_id, role="upload")
            self.assertEqual(len(media_files), 2)

            artifacts = runtime.session_service.artifacts_for_session(session)
            self.assertTrue((artifacts.raw_dir / "photo_01.jpg").exists())
            self.assertTrue((artifacts.raw_dir / "video_01.mp4").exists())

    def test_app_session_upload_route_supports_json_response_for_xhr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            session_id = self._create_session(client)

            response = client.post(
                f"/app/session/{session_id}/upload",
                files=[("media", ("photo_01.jpg", b"fake-image-1", "image/jpeg"))],
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["session_id"], session_id)
            self.assertEqual(payload["photo_count"], 1)
            self.assertEqual(payload["video_count"], 0)
            self.assertEqual(payload["media_count"], 1)
            self.assertEqual(payload["uploaded"][0]["filename"], "photo_01.jpg")

    def test_header_detection_classifies_jpeg_bytes_as_photo_even_with_mp4_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            session_id = self._create_session(client)
            runtime = client.app.state.runtime

            jpeg_bytes = b"\xff\xd8\xff\xe0" + (b"0" * 64)
            response = client.post(
                f"/app/session/{session_id}/upload",
                files=[("media", ("misleading.mp4", io.BytesIO(jpeg_bytes), "video/mp4"))],
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("photo_01.jpg", response.text)

            media_files = runtime.session_repository.list_media_files(session_id, role="upload")
            self.assertEqual(len(media_files), 1)
            self.assertEqual(media_files[0].kind, "photo")
            self.assertEqual(media_files[0].filename, "photo_01.jpg")

    def test_header_detection_classifies_mp4_bytes_as_video_even_with_jpg_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            session_id = self._create_session(client)
            runtime = client.app.state.runtime

            mp4_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41" + (b"0" * 48)
            response = client.post(
                f"/app/session/{session_id}/upload",
                files=[("media", ("misleading.jpg", io.BytesIO(mp4_bytes), "image/jpeg"))],
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("video_01.mp4", response.text)

            media_files = runtime.session_repository.list_media_files(session_id, role="upload")
            self.assertEqual(len(media_files), 1)
            self.assertEqual(media_files[0].kind, "video")
            self.assertEqual(media_files[0].filename, "video_01.mp4")

    def test_app_session_accepts_up_to_three_videos_and_rejects_fourth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            session_id = self._create_session(client)
            runtime = client.app.state.runtime

            response = client.post(
                f"/app/session/{session_id}/upload",
                files=[
                    ("media", ("clip_01.mp4", b"fake-video-1", "video/mp4")),
                    ("media", ("clip_02.mp4", b"fake-video-2", "video/mp4")),
                    ("media", ("clip_03.mp4", b"fake-video-3", "video/mp4")),
                ],
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("video_01.mp4", response.text)
            self.assertIn("video_02.mp4", response.text)
            self.assertIn("video_03.mp4", response.text)

            overflow = client.post(
                f"/app/session/{session_id}/upload",
                files=[("media", ("clip_04.mp4", b"fake-video-4", "video/mp4"))],
            )
            self.assertEqual(overflow.status_code, 400)
            self.assertIn("최대 3개", overflow.text)

            media_files = runtime.session_repository.list_media_files(session_id, role="upload")
            self.assertEqual(sum(item.kind == "video" for item in media_files), 3)

    def test_uploaded_media_can_be_deleted_from_app_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            session_id = self._create_session(client)
            runtime = client.app.state.runtime
            session = runtime.session_repository.get_by_id(session_id)

            client.post(
                f"/app/session/{session_id}/upload",
                files=[("media", ("photo_01.jpg", b"fake-image-1", "image/jpeg"))],
            )
            media_files = runtime.session_repository.list_media_files(session_id, role="upload")
            self.assertEqual(len(media_files), 1)

            deleted = client.post(
                f"/app/session/{session_id}/upload/delete",
                data={"media_file_id": media_files[0].id},
            )
            self.assertEqual(deleted.status_code, 200)
            self.assertIn("아직 업로드한 파일이 없습니다", deleted.text)

            refreshed = runtime.session_repository.list_media_files(session_id, role="upload")
            self.assertEqual(len(refreshed), 0)

            artifacts = runtime.session_service.artifacts_for_session(session)
            self.assertFalse((artifacts.raw_dir / "photo_01.jpg").exists())

    def test_session_page_rejects_unknown_app_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            self._sign_in_and_onboard(client)

            missing = client.get("/app/session/not-a-real-session")
            self.assertEqual(missing.status_code, 404)

    def _client(self, tmp_root: Path) -> TestClient:
        env = {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://mobile.thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase2-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase2-password",
            "THOHAGO_SYNC_API_TOKEN": "phase2-sync-token",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_config()
            shops = load_shop_registry(config.shops_file)
            app = create_app(config=config, shops=shops)
            return TestClient(app)

    def _sign_in_and_onboard(self, client: TestClient) -> None:
        client.get("/app/sign-in/google")
        client.post("/app/onboarding/complete")

    def _create_session(self, client: TestClient) -> str:
        self._sign_in_and_onboard(client)
        created = client.post("/app/sessions/new", follow_redirects=False)
        return created.headers["location"].rsplit("/", 1)[-1]


if __name__ == "__main__":
    unittest.main()
