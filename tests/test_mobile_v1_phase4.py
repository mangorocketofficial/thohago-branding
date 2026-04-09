from __future__ import annotations

import io
import json
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


class MobileV1Phase4Tests(unittest.TestCase):
    class _FakeGeminiClient:
        def __init__(self, text: str) -> None:
            self.text = text

        def generate_content(self, **kwargs) -> dict:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": self.text},
                            ]
                        }
                    }
                ]
            }

    class _FailingGeminiClient:
        def generate_content(self, **kwargs) -> dict:
            raise RuntimeError("quota exceeded")

    def test_waiting_session_renders_inside_app_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, _ = self._prepare_awaiting_production_app_session(Path(tmp_dir))

            waiting = client.get(f"/app/session/{session.id}")
            self.assertEqual(waiting.status_code, 200)
            self.assertIn("제작 대기", waiting.text)
            self.assertIn("awaiting_production", waiting.text)
            self.assertIn("블로그 글 생성하기", waiting.text)
            self.assertIn("쓰레드 글 생성하기", waiting.text)
            self.assertIn("인스타 사진 생성하기", waiting.text)
            self.assertIn("숏폼 영상 생성하기", waiting.text)

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn(session.id, workspace.text)
            self.assertIn("제작 대기", workspace.text)

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_production")

    def test_blog_generation_from_waiting_creates_preview_html_and_transitions_to_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, _ = self._prepare_awaiting_production_app_session(Path(tmp_dir))
            app.state.runtime.generation_service.blog_composer.gemini_client = self._FakeGeminiClient(
                "<h2>새 블로그</h2><p>인터뷰를 재가공한 새 본문입니다.</p>"
            )

            generated = client.post(
                f"/app/session/{session.id}/generate/blog",
                follow_redirects=False,
            )
            self.assertEqual(generated.status_code, 303)
            self.assertEqual(generated.headers["location"], f"/app/session/{session.id}")

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_approval")

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            content_bundle_path = artifacts.generated_dir / "content_bundle.json"
            blog_article_path = artifacts.generated_dir / "naver_blog_article.md"
            manifest_path = artifacts.published_dir / "manifest.json"
            blog_html_path = artifacts.published_dir / "blog" / "index.html"
            self.assertTrue(content_bundle_path.exists())
            self.assertTrue(blog_article_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(blog_html_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["blog_html"], "published/blog/index.html")
            self.assertEqual(manifest["status"], "preview_ready")

            blog_html = blog_html_path.read_text(encoding="utf-8")
            self.assertIn("새 블로그", blog_html)
            self.assertIn("인터뷰를 재가공한 새 본문입니다.", blog_html)
            self.assertIn("새 블로그", blog_article_path.read_text(encoding="utf-8"))

            preview = client.get(generated.headers["location"])
            self.assertEqual(preview.status_code, 200)
            self.assertIn("새 블로그", preview.text)
            self.assertIn("인터뷰를 재가공한 새 본문입니다.", preview.text)

    def test_blog_generation_failure_returns_error_instead_of_template_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, _ = self._prepare_awaiting_production_app_session(Path(tmp_dir))
            app.state.runtime.generation_service.blog_composer.gemini_client = self._FailingGeminiClient()

            generated = client.post(
                f"/app/session/{session.id}/generate/blog",
                follow_redirects=False,
            )
            self.assertEqual(generated.status_code, 400)
            self.assertIn("Gemini 블로그 생성에 실패했어요", generated.text)

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_production")

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            self.assertFalse((artifacts.published_dir / "manifest.json").exists())

    def test_preview_ready_session_renders_preview_assets_inside_app_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, sample_image = self._prepare_awaiting_production_app_session(Path(tmp_dir))
            self._push_preview_bundle(client=client, session_id=session.id, tmp_root=Path(tmp_dir), sample_image=sample_image)

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_approval")

            preview = client.get(f"/app/session/{session.id}")
            self.assertEqual(preview.status_code, 200)
            self.assertIn("미리보기 확인", preview.text)
            self.assertIn("Blog preview body", preview.text)
            self.assertIn("Thread preview line", preview.text)
            self.assertIn(f"/app/session/{session.id}/files/published/shorts/preview.mp4", preview.text)
            self.assertIn(f"/app/session/{session.id}/files/published/carousel/slide_01.jpg", preview.text)

            image_asset = client.get(f"/app/session/{session.id}/files/published/carousel/slide_01.jpg")
            self.assertEqual(image_asset.status_code, 200)
            video_asset = client.get(f"/app/session/{session.id}/files/published/shorts/preview.mp4")
            self.assertEqual(video_asset.status_code, 200)

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn("미리보기 확인", workspace.text)

    def test_revision_and_approve_actions_stay_in_app_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, sample_image = self._prepare_awaiting_production_app_session(Path(tmp_dir))
            self._push_preview_bundle(client=client, session_id=session.id, tmp_root=Path(tmp_dir), sample_image=sample_image)

            revision = client.post(
                f"/app/session/{session.id}/approval",
                data={"action": "revision"},
                follow_redirects=False,
            )
            self.assertEqual(revision.status_code, 303)
            self.assertEqual(revision.headers["location"], f"/app/session/{session.id}")

            revised = app.state.runtime.session_repository.get_by_id(session.id)
            assert revised is not None
            self.assertEqual(revised.stage, "revision_requested")

            revision_page = client.get(revision.headers["location"])
            self.assertEqual(revision_page.status_code, 200)
            self.assertIn("수정 요청", revision_page.text)
            self.assertIn("수정 요청하기", revision_page.text)

            approve = client.post(
                f"/app/session/{session.id}/approval",
                data={"action": "approve"},
                follow_redirects=False,
            )
            self.assertEqual(approve.status_code, 303)
            self.assertEqual(approve.headers["location"], f"/app/session/{session.id}")

            approved = app.state.runtime.session_repository.get_by_id(session.id)
            assert approved is not None
            self.assertEqual(approved.stage, "approved")
            self.assertIsNotNone(approved.approved_at)

            complete = client.get(approve.headers["location"])
            self.assertEqual(complete.status_code, 200)
            self.assertIn("승인이 완료되었어요", complete.text)
            self.assertIn("승인 완료", complete.text)

            messages = app.state.runtime.session_repository.list_session_messages(session.id)
            status_texts = [message.text for message in messages if message.message_type == "status" and message.text]
            self.assertIn("미리보기 수정 요청을 남겼어요.", status_texts)
            self.assertIn("미리보기를 승인했어요.", status_texts)

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn(session.id, workspace.text)
            self.assertIn("승인 완료", workspace.text)

    def _prepare_awaiting_production_app_session(self, tmp_root: Path):
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

        self._submit_and_confirm(client, session_id, "첫 번째 설명입니다.")
        self._submit_and_confirm(client, session_id, "두 번째 설명입니다.")
        self._submit_and_confirm(client, session_id, "세 번째 설명입니다.")

        session = app.state.runtime.session_repository.get_by_id(session_id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_production")
        return client, app, session, sample_image

    def _submit_and_confirm(self, client: TestClient, session_id: str, answer_text: str) -> None:
        submit = client.post(
            f"/app/session/{session_id}/interview/submit",
            data={"answer_text": answer_text},
            follow_redirects=False,
        )
        self.assertEqual(submit.status_code, 303)
        confirm = client.post(
            f"/app/session/{session_id}/interview/confirm",
            follow_redirects=False,
        )
        self.assertEqual(confirm.status_code, 303)

    def _push_preview_bundle(self, *, client: TestClient, session_id: str, tmp_root: Path, sample_image: Path) -> None:
        source_dir = tmp_root / "preview_source"
        (source_dir / "shorts").mkdir(parents=True, exist_ok=True)
        (source_dir / "blog").mkdir(parents=True, exist_ok=True)
        (source_dir / "threads").mkdir(parents=True, exist_ok=True)
        (source_dir / "carousel").mkdir(parents=True, exist_ok=True)

        (source_dir / "shorts" / "preview.mp4").write_bytes(b"fake-mp4-bytes")
        (source_dir / "blog" / "index.html").write_text("<article><h1>Blog preview body</h1></article>", encoding="utf-8")
        (source_dir / "threads" / "thread.txt").write_text("Thread preview line", encoding="utf-8")
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
            headers={"Authorization": "Bearer phase4-sync-token"},
            data={"manifest_json": manifest_json},
            files={"bundle": ("preview_bundle.zip", bundle.getvalue(), "application/zip")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('"stage":"awaiting_approval"', response.text.replace(" ", ""))

    def _client_bundle(self, tmp_root: Path):
        env = {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://mobile.thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase4-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase4-password",
            "THOHAGO_SYNC_API_TOKEN": "phase4-sync-token",
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
