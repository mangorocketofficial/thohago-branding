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


class MobileV1Phase6Tests(unittest.TestCase):
    def test_sign_in_flows_directly_to_chat_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))

            sign_in = client.get("/app/sign-in/google", follow_redirects=False)
            self.assertEqual(sign_in.status_code, 303)
            self.assertEqual(sign_in.headers["location"], "/app")

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn("app-frame", workspace.text)
            self.assertIn("app-sidebar", workspace.text)
            self.assertIn("메인 채팅", workspace.text)
            self.assertIn("새 작업 시작", workspace.text)

    def test_workspace_and_session_share_sidebar_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            client.get("/app/sign-in/google")

            created = client.post("/app/sessions/new", follow_redirects=False)
            self.assertEqual(created.status_code, 303)
            session_path = created.headers["location"]
            session_id = session_path.rsplit("/", 1)[-1]

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn(session_id, workspace.text)
            self.assertIn("app-session-link", workspace.text)

            session_page = client.get(session_path)
            self.assertEqual(session_page.status_code, 200)
            self.assertIn("app-frame", session_page.text)
            self.assertIn("app-sidebar", session_page.text)
            self.assertIn("app-menu-button", session_page.text)
            self.assertIn("is-active", session_page.text)
            self.assertIn(session_id, session_page.text)

    def test_onboarding_route_is_no_longer_a_standalone_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._client(Path(tmp_dir))
            client.get("/app/sign-in/google")

            onboarding = client.get("/app/onboarding", follow_redirects=False)
            self.assertEqual(onboarding.status_code, 303)
            self.assertEqual(onboarding.headers["location"], "/app")

    def _client(self, tmp_root: Path) -> TestClient:
        env = {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://mobile.thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase6-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase6-password",
            "THOHAGO_SYNC_API_TOKEN": "phase6-sync-token",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_config()
            shops = load_shop_registry(config.shops_file)
            app = create_app(config=config, shops=shops)
            return TestClient(app)


if __name__ == "__main__":
    unittest.main()
