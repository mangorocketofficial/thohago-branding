from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

from fastapi.testclient import TestClient

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class WebPhase5Tests(unittest.TestCase):
    def test_admin_session_list_links_to_detail_and_is_authenticated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session, _ = self._prepare_preview_ready_session(Path(tmp_dir), "web_phase5_list")
            unauthorized = client.get("/admin/sessions")
            self.assertEqual(unauthorized.status_code, 401)

            authorized = client.get("/admin/sessions", auth=("phase5-admin", "phase5-password"))
            self.assertEqual(authorized.status_code, 200)
            self.assertIn(f"/admin/sessions/{session.id}", authorized.text)
            self.assertIn("Create New Session", authorized.text)

    def test_admin_new_page_creates_session_and_redirects_to_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir))
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            shops = load_shop_registry(config.shops_file)
            app = create_app(config=config, shops=shops)
            client = TestClient(app)

            new_page = client.get("/admin/sessions/new", auth=("phase5-admin", "phase5-password"))
            self.assertEqual(new_page.status_code, 200)
            self.assertIn("Create Session", new_page.text)

            created = client.post(
                "/admin/sessions",
                auth=("phase5-admin", "phase5-password"),
                data={"shop_id": "sisun8082", "session_key": "phase5_new"},
                follow_redirects=False,
            )
            self.assertEqual(created.status_code, 303)
            detail = client.get(created.headers["location"], auth=("phase5-admin", "phase5-password"))
            self.assertEqual(detail.status_code, 200)
            self.assertIn("Session Detail", detail.text)
            self.assertIn("Customer URL", detail.text)

    def test_admin_detail_shows_messages_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session, _ = self._prepare_preview_ready_session(Path(tmp_dir), "web_phase5_detail")
            detail = client.get(f"/admin/sessions/{session.id}", auth=("phase5-admin", "phase5-password"))
            self.assertEqual(detail.status_code, 200)
            self.assertIn("Message History", detail.text)
            self.assertIn("Artifacts", detail.text)
            self.assertIn("미리보기가 준비되었어요. 확인 후 승인하거나 수정 요청을 남겨주세요.", detail.text)
            self.assertIn("published/manifest.json", detail.text)

    def test_waiting_page_has_auto_check_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase5_wait")
            waiting = client.get(f"/s/{session.customer_token}/waiting")
            self.assertEqual(waiting.status_code, 200)
            self.assertIn("15초마다 자동으로 다시 확인", waiting.text)
            self.assertIn(f'content="15;url=/s/{session.customer_token}"', waiting.text)
            self.assertIn(f'window.location.href = "/s/{session.customer_token}"', waiting.text)

    def test_pwa_routes_are_reachable_and_layout_references_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir))
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            shops = load_shop_registry(config.shops_file)
            app = create_app(config=config, shops=shops)
            client = TestClient(app)

            manifest = client.get("/manifest.webmanifest")
            self.assertEqual(manifest.status_code, 200)
            self.assertEqual(manifest.json()["name"], "Thohago")

            sw = client.get("/sw.js")
            self.assertEqual(sw.status_code, 200)
            self.assertIn("CACHE_NAME", sw.text)

            offline = client.get("/offline")
            self.assertEqual(offline.status_code, 200)
            self.assertIn("Offline Fallback", offline.text)

            page = client.get("/admin/sessions/new", auth=("phase5-admin", "phase5-password"))
            self.assertIn('/manifest.webmanifest', page.text)
            self.assertIn('navigator.serviceWorker.register("/sw.js")', page.text)

    def _prepare_preview_ready_session(self, tmp_root: Path, session_key: str):
        client, app, session = self._prepare_awaiting_production_session(tmp_root, session_key)
        source_dir, manifest_path = self._build_preview_source(tmp_root)
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in source_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(source_dir).as_posix())
        response = client.post(
            f"/api/sync/sessions/{session.id}/upload",
            headers={"Authorization": "Bearer phase5-sync-token"},
            data={"manifest_json": manifest_path.read_text(encoding="utf-8")},
            files={"bundle": ("preview_bundle.zip", bundle.getvalue(), "application/zip")},
        )
        self.assertEqual(response.status_code, 200)
        updated = app.state.runtime.session_repository.get_by_id(session.id)
        assert updated is not None
        return client, app, updated, manifest_path

    def _prepare_awaiting_production_session(self, tmp_root: Path, session_key: str):
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
        for answer in ["첫 번째 답변", "두 번째 답변", "세 번째 답변"]:
            client.post(
                f"/s/{created.session.customer_token}/interview/submit",
                data={"answer_text": answer},
                follow_redirects=False,
            )
            client.post(f"/s/{created.session.customer_token}/interview/confirm", follow_redirects=False)

        session = app.state.runtime.session_repository.get_by_id(created.session.id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_production")
        return client, app, session

    def _build_preview_source(self, tmp_root: Path) -> tuple[Path, Path]:
        env = self._web_env(tmp_root)
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))
        source_dir = tmp_root / "preview_source"
        (source_dir / "shorts").mkdir(parents=True, exist_ok=True)
        (source_dir / "blog").mkdir(parents=True, exist_ok=True)
        (source_dir / "threads").mkdir(parents=True, exist_ok=True)
        (source_dir / "carousel").mkdir(parents=True, exist_ok=True)
        (source_dir / "shorts" / "preview.mp4").write_bytes(b"fake-mp4-bytes")
        (source_dir / "blog" / "index.html").write_text("<article><h1>Phase 5 Blog Preview</h1></article>", encoding="utf-8")
        (source_dir / "threads" / "thread.txt").write_text("Phase 5 thread preview", encoding="utf-8")
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

    def _web_env(self, tmp_root: Path) -> dict[str, str]:
        return {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase5-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase5-password",
            "THOHAGO_SYNC_API_TOKEN": "phase5-sync-token",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
