from __future__ import annotations

import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
import zipfile

from fastapi.testclient import TestClient
import uvicorn

from thohago.cli import main
from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class WebPhase4Tests(unittest.TestCase):
    def test_sync_api_requires_token_and_lists_awaiting_production(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, _ = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase4_list")
            unauthorized = client.get("/api/sync/sessions")
            self.assertEqual(unauthorized.status_code, 403)

            authorized = client.get(
                "/api/sync/sessions",
                headers={"Authorization": "Bearer phase4-sync-token"},
                params={"stage": "awaiting_production"},
            )
            self.assertEqual(authorized.status_code, 200)
            payload = authorized.json()
            self.assertEqual(len(payload["sessions"]), 1)
            self.assertEqual(payload["sessions"][0]["session_id"], session.id)
            self.assertEqual(payload["sessions"][0]["stage"], "awaiting_production")

    def test_sync_download_contains_intake_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session, _ = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase4_download")
            response = client.get(
                f"/api/sync/sessions/{session.id}/download",
                headers={"Authorization": "Bearer phase4-sync-token"},
            )
            self.assertEqual(response.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(response.content), mode="r") as archive:
                names = set(archive.namelist())
            self.assertIn("generated/intake_bundle.json", names)

    def test_sync_upload_writes_preview_and_preview_page_renders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, sample_image = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase4_upload")
            source_dir, manifest_path = self._build_preview_source(Path(tmp_dir), sample_image)

            response = self._push_preview_bundle(
                client=client,
                session_id=session.id,
                source_dir=source_dir,
                manifest_path=manifest_path,
            )
            self.assertEqual(response.status_code, 200)

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_approval")

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            self.assertTrue((artifacts.published_dir / "manifest.json").exists())
            self.assertTrue((artifacts.published_dir / "blog" / "index.html").exists())
            self.assertTrue((artifacts.published_dir / "threads" / "thread.txt").exists())

            preview = client.get(f"/s/{updated.customer_token}/preview")
            self.assertEqual(preview.status_code, 200)
            self.assertIn("미리보기 확인", preview.text)
            self.assertIn("Blog preview body", preview.text)
            self.assertIn("Thread preview line", preview.text)

            landing = client.get(f"/s/{updated.customer_token}", follow_redirects=False)
            self.assertEqual(landing.status_code, 307)
            self.assertEqual(landing.headers["location"], f"/s/{updated.customer_token}/preview")

            asset = client.get(f"/s/{updated.customer_token}/files/published/carousel/slide_01.jpg")
            self.assertEqual(asset.status_code, 200)

    def test_revision_and_approval_update_stage_and_redirects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, sample_image = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase4_approval")
            source_dir, manifest_path = self._build_preview_source(Path(tmp_dir), sample_image)
            push = self._push_preview_bundle(
                client=client,
                session_id=session.id,
                source_dir=source_dir,
                manifest_path=manifest_path,
            )
            self.assertEqual(push.status_code, 200)

            revision = client.post(
                f"/s/{session.customer_token}/approval",
                data={"action": "revision"},
                follow_redirects=False,
            )
            self.assertEqual(revision.status_code, 303)
            revised = app.state.runtime.session_repository.get_by_id(session.id)
            assert revised is not None
            self.assertEqual(revised.stage, "revision_requested")
            landing_revision = client.get(f"/s/{session.customer_token}", follow_redirects=False)
            self.assertEqual(landing_revision.headers["location"], f"/s/{session.customer_token}/preview")

            approve = client.post(
                f"/s/{session.customer_token}/approval",
                data={"action": "approve"},
                follow_redirects=False,
            )
            self.assertEqual(approve.status_code, 303)
            approved = app.state.runtime.session_repository.get_by_id(session.id)
            assert approved is not None
            self.assertEqual(approved.stage, "approved")
            self.assertIsNotNone(approved.approved_at)
            complete = client.get(approve.headers["location"])
            self.assertEqual(complete.status_code, 200)
            self.assertIn("승인 완료", complete.text)

    def test_sync_cli_list_pull_push_against_live_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session, sample_image = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase4_cli")
            source_dir, manifest_path = self._build_preview_source(Path(tmp_dir), sample_image)
            token = "phase4-sync-token"

            with self._run_live_server(app) as base_url:
                list_stdout = io.StringIO()
                with redirect_stdout(list_stdout):
                    exit_code = main(["sync", "list", "--base-url", base_url, "--token", token, "--stage", "awaiting_production"])
                self.assertEqual(exit_code, 0)
                self.assertIn(session.id, list_stdout.getvalue())

                output_dir = Path(tmp_dir) / "pulled"
                pull_stdout = io.StringIO()
                with redirect_stdout(pull_stdout):
                    exit_code = main(
                        ["sync", "pull", "--base-url", base_url, "--token", token, "--session-id", session.id, "--output-dir", str(output_dir)],
                    )
                self.assertEqual(exit_code, 0)
                extracted_dir = output_dir / session.id
                self.assertTrue((extracted_dir / "generated" / "intake_bundle.json").exists())

                push_stdout = io.StringIO()
                with redirect_stdout(push_stdout):
                    exit_code = main(
                        [
                            "sync",
                            "push",
                            "--base-url",
                            base_url,
                            "--token",
                            token,
                            "--session-id",
                            session.id,
                            "--source-dir",
                            str(source_dir),
                            "--manifest",
                            str(manifest_path),
                        ]
                    )
                self.assertEqual(exit_code, 0)
                self.assertIn("stage=awaiting_approval", push_stdout.getvalue())

                updated = app.state.runtime.session_repository.get_by_id(session.id)
                assert updated is not None
                self.assertEqual(updated.stage, "awaiting_approval")

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
        self._submit_and_confirm(client, created.session.customer_token, "첫 번째 설명입니다.")
        self._submit_and_confirm(client, created.session.customer_token, "두 번째 설명입니다.")
        self._submit_and_confirm(client, created.session.customer_token, "세 번째 설명입니다.")

        session = app.state.runtime.session_repository.get_by_id(created.session.id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_production")
        return client, app, session, sample_image

    def _submit_and_confirm(self, client: TestClient, customer_token: str, answer_text: str) -> None:
        submit = client.post(
            f"/s/{customer_token}/interview/submit",
            data={"answer_text": answer_text},
            follow_redirects=False,
        )
        self.assertEqual(submit.status_code, 303)
        confirm = client.post(f"/s/{customer_token}/interview/confirm", follow_redirects=False)
        self.assertEqual(confirm.status_code, 303)

    def _build_preview_source(self, tmp_root: Path, sample_image: Path) -> tuple[Path, Path]:
        source_dir = tmp_root / "preview_source"
        (source_dir / "shorts").mkdir(parents=True, exist_ok=True)
        (source_dir / "blog").mkdir(parents=True, exist_ok=True)
        (source_dir / "threads").mkdir(parents=True, exist_ok=True)
        (source_dir / "carousel").mkdir(parents=True, exist_ok=True)

        (source_dir / "shorts" / "preview.mp4").write_bytes(b"fake-mp4-bytes")
        (source_dir / "blog" / "index.html").write_text("<article><h1>Blog preview body</h1></article>", encoding="utf-8")
        (source_dir / "threads" / "thread.txt").write_text("Thread preview line", encoding="utf-8")
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

    def _push_preview_bundle(self, *, client: TestClient, session_id: str, source_dir: Path, manifest_path: Path):
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in source_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(source_dir).as_posix())
        return client.post(
            f"/api/sync/sessions/{session_id}/upload",
            headers={"Authorization": "Bearer phase4-sync-token"},
            data={"manifest_json": manifest_path.read_text(encoding="utf-8")},
            files={"bundle": ("preview_bundle.zip", bundle.getvalue(), "application/zip")},
        )

    @contextmanager
    def _run_live_server(self, app):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()

        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)
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
            "THOHAGO_ADMIN_USERNAME": "phase4-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase4-password",
            "THOHAGO_SYNC_API_TOKEN": "phase4-sync-token",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
