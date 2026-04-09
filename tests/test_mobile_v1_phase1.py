from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class MobileV1Phase1Tests(unittest.TestCase):
    def test_public_pages_render_korean_mobile_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))

            landing = client.get("/")
            self.assertEqual(landing.status_code, 200)
            self.assertIn("또하고 모바일", landing.text)
            self.assertIn("구글로 시작하기", landing.text)
            self.assertIn("사진과 인터뷰만 보내면 콘텐츠 초안을 만들어 드려요", landing.text)

            pricing = client.get("/pricing")
            self.assertEqual(pricing.status_code, 200)
            self.assertIn("요금 안내", pricing.text)
            self.assertIn("가볍게 시작", pricing.text)
            self.assertIn("꾸준히 운영", pricing.text)

    def test_app_shell_redirects_without_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))

            app_response = client.get("/app", follow_redirects=False)
            self.assertEqual(app_response.status_code, 303)
            self.assertEqual(app_response.headers["location"], "/")

            onboarding_response = client.get("/app/onboarding", follow_redirects=False)
            self.assertEqual(onboarding_response.status_code, 303)
            self.assertEqual(onboarding_response.headers["location"], "/")

    def test_sign_in_stub_lands_directly_in_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))

            sign_in = client.get("/app/sign-in/google", follow_redirects=False)
            self.assertEqual(sign_in.status_code, 303)
            self.assertEqual(sign_in.headers["location"], "/app")
            self.assertIn("thohago_mobile_auth=", sign_in.headers.get("set-cookie", ""))

            onboarding = client.get("/app/onboarding", follow_redirects=False)
            self.assertEqual(onboarding.status_code, 303)
            self.assertEqual(onboarding.headers["location"], "/app")

            completed = client.post("/app/onboarding/complete", follow_redirects=False)
            self.assertEqual(completed.status_code, 303)
            self.assertEqual(completed.headers["location"], "/app")

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn("메인 채팅", workspace.text)
            self.assertIn("새 작업 시작", workspace.text)
            self.assertIn("app-sidebar", workspace.text)

    def test_new_session_shell_opens_after_workspace_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))

            client.get("/app/sign-in/google")

            created = client.post("/app/sessions/new", follow_redirects=False)
            self.assertEqual(created.status_code, 303)
            self.assertTrue(created.headers["location"].startswith("/app/session/mobile_v1_app_"))

            session_page = client.get(created.headers["location"])
            self.assertEqual(session_page.status_code, 200)
            self.assertIn("새 작업을 준비할게요", session_page.text)
            self.assertIn("업로드 안내", session_page.text)
            self.assertIn("인터뷰로 넘어가기", session_page.text)

    def _client(self, tmp_root: Path) -> TestClient:
        env = {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://mobile.thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase1-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase1-password",
            "THOHAGO_SYNC_API_TOKEN": "phase1-sync-token",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_config()
            shops = load_shop_registry(config.shops_file)
            app = create_app(config=config, shops=shops)
            return TestClient(app)


if __name__ == "__main__":
    unittest.main()
