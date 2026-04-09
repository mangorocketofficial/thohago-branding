from __future__ import annotations

import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class MobileV1Phase5Tests(unittest.TestCase):
    def test_approved_session_renders_delivery_view_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session, _ = self._prepare_approved_app_session(Path(tmp_dir))

            response = client.get(f"/app/session/{session.id}")
            self.assertEqual(response.status_code, 200)
            self.assertIn("결과 파일을 받을 수 있어요", response.text)
            self.assertIn("전체 결과 묶음 다운로드", response.text)
            self.assertIn(f"/app/session/{session.id}/download/bundle", response.text)
            self.assertIn(f"/app/session/{session.id}/download/file/published/threads/thread.txt", response.text)
            self.assertIn(f"/app/session/{session.id}/download/file/published/blog/index.html", response.text)
            self.assertIn(f"/app/session/{session.id}/download/file/published/shorts/preview.mp4", response.text)

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn(session.id, workspace.text)
            self.assertIn("승인 완료", workspace.text)

    def test_approved_session_can_download_individual_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session, _ = self._prepare_approved_app_session(Path(tmp_dir))

            asset = client.get(f"/app/session/{session.id}/download/file/published/threads/thread.txt")
            self.assertEqual(asset.status_code, 200)
            self.assertIn('filename="thread.txt"', asset.headers.get("content-disposition", ""))
            self.assertEqual(asset.content.decode("utf-8"), "Phase 5 thread delivery")

    def test_approved_session_bundle_download_contains_published_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session, _ = self._prepare_approved_app_session(Path(tmp_dir))

            bundle = client.get(f"/app/session/{session.id}/download/bundle")
            self.assertEqual(bundle.status_code, 200)
            self.assertIn(f'{session.id}-delivery.zip', bundle.headers.get("content-disposition", ""))

            with zipfile.ZipFile(io.BytesIO(bundle.content), mode="r") as archive:
                names = set(archive.namelist())

            self.assertIn("published/manifest.json", names)
            self.assertIn("published/shorts/preview.mp4", names)
            self.assertIn("published/blog/index.html", names)
            self.assertIn("published/threads/thread.txt", names)
            self.assertIn("published/carousel/slide_01.jpg", names)
            self.assertNotIn("raw/photo_01.jpg", names)

    def _prepare_approved_app_session(self, tmp_root: Path):
        client, app, shops = self._client_bundle(tmp_root)
        session_id = self._create_session(client)
        sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))
        sample_video = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].video_dir.glob("*.mp4"))

        with sample_image.open("rb") as image_handle, sample_video.open("rb") as video_handle:
            upload = client.post(
                f"/app/session/{session_id}/upload",
                files=[
                    ("media", (sample_image.name, image_handle, "image/jpeg")),
                    ("media", (sample_video.name, video_handle, "video/mp4")),
                ],
            )
        self.assertEqual(upload.status_code, 200)

        finalize = client.post(f"/app/session/{session_id}/upload/complete", follow_redirects=False)
        self.assertEqual(finalize.status_code, 303)

        for answer in ("첫 번째 설명입니다.", "두 번째 설명입니다.", "세 번째 설명입니다."):
            submit = client.post(
                f"/app/session/{session_id}/interview/submit",
                data={"answer_text": answer},
                follow_redirects=False,
            )
            self.assertEqual(submit.status_code, 303)
            confirm = client.post(
                f"/app/session/{session_id}/interview/confirm",
                follow_redirects=False,
            )
            self.assertEqual(confirm.status_code, 303)

        self._push_preview_bundle(client=client, session_id=session_id, tmp_root=tmp_root, sample_image=sample_image)

        approve = client.post(
            f"/app/session/{session_id}/approval",
            data={"action": "approve"},
            follow_redirects=False,
        )
        self.assertEqual(approve.status_code, 303)

        session = app.state.runtime.session_repository.get_by_id(session_id)
        assert session is not None
        self.assertEqual(session.stage, "approved")
        return client, app, session, sample_image

    def _push_preview_bundle(self, *, client: TestClient, session_id: str, tmp_root: Path, sample_image: Path) -> None:
        source_dir = tmp_root / "preview_source"
        (source_dir / "shorts").mkdir(parents=True, exist_ok=True)
        (source_dir / "blog").mkdir(parents=True, exist_ok=True)
        (source_dir / "threads").mkdir(parents=True, exist_ok=True)
        (source_dir / "carousel").mkdir(parents=True, exist_ok=True)

        (source_dir / "shorts" / "preview.mp4").write_bytes(b"fake-mp4-bytes")
        (source_dir / "blog" / "index.html").write_text("<article><h1>Phase 5 Blog Delivery</h1></article>", encoding="utf-8")
        (source_dir / "threads" / "thread.txt").write_text("Phase 5 thread delivery", encoding="utf-8")
        (source_dir / "carousel" / "slide_01.jpg").write_bytes(sample_image.read_bytes())

        manifest_json = """
{
  "status": "preview_ready",
  "shorts_video": "published/shorts/preview.mp4",
  "blog_html": "published/blog/index.html",
  "thread_text": "published/threads/thread.txt",
  "carousel_images": ["published/carousel/slide_01.jpg"]
}
""".strip()

        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in source_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(source_dir).as_posix())

        response = client.post(
            f"/api/sync/sessions/{session_id}/upload",
            headers={"Authorization": "Bearer phase5-sync-token"},
            data={"manifest_json": manifest_json},
            files={"bundle": ("preview_bundle.zip", bundle.getvalue(), "application/zip")},
        )
        self.assertEqual(response.status_code, 200)

    def _client_bundle(self, tmp_root: Path):
        env = {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://mobile.thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase5-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase5-password",
            "THOHAGO_SYNC_API_TOKEN": "phase5-sync-token",
            "THOHAGO_DEFAULT_INTERVIEW_ENGINE": "heuristic",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_config()
            shops = load_shop_registry(config.shops_file)
            app = create_app(config=config, shops=shops)
            client = TestClient(app)
            return client, app, shops

    def _sign_in_and_onboard(self, client: TestClient) -> None:
        client.get("/app/sign-in/google")
        client.post("/app/onboarding/complete")

    def _create_session(self, client: TestClient) -> str:
        self._sign_in_and_onboard(client)
        created = client.post("/app/sessions/new", follow_redirects=False)
        self.assertEqual(created.status_code, 303)
        return created.headers["location"].rsplit("/", 1)[-1]


if __name__ == "__main__":
    unittest.main()
