from __future__ import annotations

import io
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.cli import main
from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app
from thohago.web.database import initialize_database
from thohago.web.repositories import SessionRepository
from thohago.web.services.sessions import SessionService


class WebPhase1Tests(unittest.TestCase):
    def test_init_db_creates_required_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir))
            with patch.dict(os.environ, env, clear=False):
                config = load_config()
                initialize_database(config.web_database_path)

                self.assertTrue(config.web_database_path.exists())
                connection = sqlite3.connect(config.web_database_path)
                try:
                    rows = connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'",
                    ).fetchall()
                finally:
                    connection.close()

                table_names = {row[0] for row in rows}
                self.assertTrue({"sessions", "media_files", "session_messages", "session_artifacts"}.issubset(table_names))

    def test_cli_create_session_writes_artifact_and_db_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir))
            with patch.dict(os.environ, env, clear=False):
                init_stdout = io.StringIO()
                with redirect_stdout(init_stdout):
                    exit_code = main(["web", "init-db"])
                self.assertEqual(exit_code, 0)

                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        ["web", "create-session", "--shop-id", "sisun8082", "--session-key", "web_phase1_cli"],
                    )
                self.assertEqual(exit_code, 0)

                parsed = self._parse_key_value_lines(stdout.getvalue())
                self.assertEqual(parsed["shop_id"], "sisun8082")
                self.assertEqual(parsed["session_key"], "web_phase1_cli")
                self.assertIn("/s/", parsed["customer_url"])

                artifact_dir = Path(parsed["artifact_dir"])
                metadata_path = Path(parsed["session_metadata"])
                self.assertTrue(artifact_dir.exists())
                self.assertTrue(metadata_path.exists())

                connection = sqlite3.connect(env["THOHAGO_WEB_DB_PATH"])
                try:
                    row = connection.execute(
                        "SELECT shop_id, stage, customer_token FROM sessions WHERE id = ?",
                        (parsed["session_id"],),
                    ).fetchone()
                finally:
                    connection.close()

                self.assertIsNotNone(row)
                self.assertEqual(row[0], "sisun8082")
                self.assertEqual(row[1], "collecting_media")
                self.assertEqual(row[2], parsed["customer_token"])

    def test_customer_token_redirects_to_upload_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir))
            with patch.dict(os.environ, env, clear=False):
                config = load_config()
                shops = load_shop_registry(config.shops_file)
                initialize_database(config.web_database_path)
                repository = SessionRepository(config.web_database_path)
                service = SessionService(
                    config=config,
                    web_config=create_app(config=config, shops=shops).state.runtime.web_config,
                    shops=shops,
                    repository=repository,
                )
                created = service.create_session(shop_id="sisun8082", session_key="web_phase1_redirect")
                app = create_app(config=config, shops=shops)
                client = TestClient(app)

                response = client.get(f"/s/{created.session.customer_token}", follow_redirects=False)
                self.assertEqual(response.status_code, 307)
                self.assertEqual(response.headers["location"], f"/s/{created.session.customer_token}/upload")

                upload_page = client.get(response.headers["location"])
                self.assertEqual(upload_page.status_code, 200)
                self.assertIn("사진+영상 업로드 하기", upload_page.text)
                self.assertIn("파일 선택하기", upload_page.text)

                missing = client.get("/s/not-a-real-token", follow_redirects=False)
                self.assertEqual(missing.status_code, 404)

    def test_admin_requires_auth_and_can_create_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir))
            with patch.dict(os.environ, env, clear=False):
                config = load_config()
                shops = load_shop_registry(config.shops_file)
                app = create_app(config=config, shops=shops)
                client = TestClient(app)

                unauthorized = client.get("/admin/sessions")
                self.assertEqual(unauthorized.status_code, 401)

                authorized = client.post(
                    "/admin/sessions",
                    auth=(env["THOHAGO_ADMIN_USERNAME"], env["THOHAGO_ADMIN_PASSWORD"]),
                    data={"shop_id": "sisun8082", "session_key": "admin_created"},
                )
                self.assertEqual(authorized.status_code, 200)
                self.assertIn("Session created.", authorized.text)
                self.assertIn("admin_created", authorized.text)

                runtime = app.state.runtime
                sessions = runtime.session_repository.list_sessions()
                self.assertEqual(len(sessions), 1)
                self.assertEqual(sessions[0].stage, "collecting_media")

    def _web_env(self, tmp_root: Path) -> dict[str, str]:
        return {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase1-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase1-password",
            "THOHAGO_SYNC_API_TOKEN": "phase1-sync-token",
        }

    def _parse_key_value_lines(self, raw: str) -> dict[str, str]:
        parsed: dict[str, str] = {}
        for line in raw.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
        return parsed


if __name__ == "__main__":
    unittest.main()
