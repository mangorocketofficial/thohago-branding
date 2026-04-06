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


class WebPhase9Tests(unittest.TestCase):
    def test_interview_page_uses_chat_layout_with_korean_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase9_interview")
            response = client.get(f"/s/{session.customer_token}/interview")
            self.assertEqual(response.status_code, 200)
            self.assertIn("customer-chat", response.text)
            self.assertIn("chat-thread", response.text)
            self.assertIn("첫번째 질문", response.text)
            self.assertIn("chat-composer-shell", response.text)
            self.assertIn("composer-field", response.text)
            self.assertIn("composer-inline-actions", response.text)
            self.assertIn("composer-mic-button", response.text)
            self.assertIn("composer-field-indicator", response.text)
            self.assertIn("보내기", response.text)
            self.assertIn("chat-avatar-icon", response.text)
            self.assertNotIn(">또<", response.text)
            self.assertNotIn("말로 답변하기", response.text)
            self.assertNotIn("직접 입력하기", response.text)

    def test_confirming_interview_hides_edit_button_and_locks_textarea(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase9_confirm")
            submit = client.post(
                f"/s/{session.customer_token}/interview/submit",
                data={"answer_text": "확인용 답변"},
                follow_redirects=False,
            )
            self.assertEqual(submit.status_code, 303)
            response = client.get(submit.headers["location"])
            self.assertEqual(response.status_code, 200)
            self.assertIn("composer-field", response.text)
            self.assertIn("composer-inline-actions", response.text)
            self.assertIn("composer-mic-button", response.text)
            self.assertIn("readonly", response.text)
            self.assertNotIn("composer-edit-button", response.text)
            self.assertNotIn("답변 수정하기</button>", response.text)

    def test_waiting_page_uses_chat_layout_and_korean_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_awaiting_production_session(Path(tmp_dir), "web_phase9_wait")
            response = client.get(f"/s/{session.customer_token}/waiting")
            self.assertEqual(response.status_code, 200)
            self.assertIn("제작 대기", response.text)
            self.assertIn("customer-chat", response.text)
            self.assertIn("같은 링크를 열어두면", response.text)
            self.assertIn('content="15;url=/s/', response.text)

    def test_preview_page_uses_chat_layout_and_korean_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_preview_ready_session(Path(tmp_dir), "web_phase9_preview")
            response = client.get(f"/s/{session.customer_token}/preview")
            self.assertEqual(response.status_code, 200)
            self.assertIn("미리보기 확인", response.text)
            self.assertIn("승인하기", response.text)
            self.assertIn("수정 요청하기", response.text)
            self.assertIn("chat-thread", response.text)

    def test_complete_page_uses_chat_layout_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_preview_ready_session(Path(tmp_dir), "web_phase9_complete")
            approve = client.post(
                f"/s/{session.customer_token}/approval",
                data={"action": "approve"},
                follow_redirects=False,
            )
            self.assertEqual(approve.status_code, 303)

            response = client.get(approve.headers["location"])
            self.assertEqual(response.status_code, 200)
            self.assertIn("승인 완료", response.text)
            self.assertIn("승인이 완료되었어요.", response.text)
            self.assertIn("chat-thread", response.text)

    def test_upload_page_remains_form_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, _, session = self._prepare_collecting_media_session(Path(tmp_dir), "web_phase9_upload")
            response = client.get(f"/s/{session.customer_token}/upload")
            self.assertEqual(response.status_code, 200)
            self.assertIn("사진+영상 업로드 하기", response.text)
            self.assertIn("파일 선택하기", response.text)
            self.assertIn("인터뷰하기", response.text)
            self.assertNotIn("chat-thread", response.text)

    def _prepare_collecting_media_session(self, tmp_root: Path, session_key: str):
        env = self._web_env(tmp_root)
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        config = load_config()
        shops = load_shop_registry(config.shops_file)
        app = create_app(config=config, shops=shops)
        client = TestClient(app)
        created = app.state.runtime.session_service.create_session(shop_id="sisun8082", session_key=session_key)
        session = app.state.runtime.session_repository.get_by_id(created.session.id)
        assert session is not None
        return client, app, session

    def _prepare_interview_ready_session(self, tmp_root: Path, session_key: str):
        client, app, session, _ = self._prepare_uploaded_session(tmp_root, session_key)
        return client, app, session

    def _prepare_awaiting_production_session(self, tmp_root: Path, session_key: str):
        client, app, session, _ = self._prepare_uploaded_session(tmp_root, session_key)
        for answer in ["첫번째 답변", "두번째 답변", "세번째 답변"]:
            client.post(
                f"/s/{session.customer_token}/interview/submit",
                data={"answer_text": answer},
                follow_redirects=False,
            )
            client.post(f"/s/{session.customer_token}/interview/confirm", follow_redirects=False)
            session = app.state.runtime.session_repository.get_by_id(session.id)
            assert session is not None
        self.assertEqual(session.stage, "awaiting_production")
        return client, app, session

    def _prepare_preview_ready_session(self, tmp_root: Path, session_key: str):
        client, app, session = self._prepare_awaiting_production_session(tmp_root, session_key)
        sample_image = next(load_shop_registry(load_config().shops_file)["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))
        source_dir, manifest_path = self._build_preview_source(tmp_root, sample_image)
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in source_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(source_dir).as_posix())
        response = client.post(
            f"/api/sync/sessions/{session.id}/upload",
            headers={"Authorization": "Bearer phase9-sync-token"},
            data={"manifest_json": manifest_path.read_text(encoding="utf-8")},
            files={"bundle": ("preview_bundle.zip", bundle.getvalue(), "application/zip")},
        )
        self.assertEqual(response.status_code, 200)
        updated = app.state.runtime.session_repository.get_by_id(session.id)
        assert updated is not None
        return client, app, updated

    def _prepare_uploaded_session(self, tmp_root: Path, session_key: str):
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
            upload = client.post(
                f"/s/{created.session.customer_token}/upload",
                files={"media": (sample_image.name, handle, "image/jpeg")},
            )
        self.assertEqual(upload.status_code, 200)
        finalize = client.post(f"/s/{created.session.customer_token}/upload/done", follow_redirects=False)
        self.assertEqual(finalize.status_code, 303)
        session = app.state.runtime.session_repository.get_by_id(created.session.id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_turn1_answer")
        return client, app, session, sample_image

    def _build_preview_source(self, tmp_root: Path, sample_image: Path) -> tuple[Path, Path]:
        source_dir = tmp_root / "preview_source"
        (source_dir / "shorts").mkdir(parents=True, exist_ok=True)
        (source_dir / "blog").mkdir(parents=True, exist_ok=True)
        (source_dir / "threads").mkdir(parents=True, exist_ok=True)
        (source_dir / "carousel").mkdir(parents=True, exist_ok=True)
        (source_dir / "shorts" / "preview.mp4").write_bytes(b"fake-mp4-bytes")
        (source_dir / "blog" / "index.html").write_text("<article><h1>미리보기 블로그</h1></article>", encoding="utf-8")
        (source_dir / "threads" / "thread.txt").write_text("미리보기 스레드", encoding="utf-8")
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
            "THOHAGO_ADMIN_USERNAME": "phase9-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase9-password",
            "THOHAGO_SYNC_API_TOKEN": "phase9-sync-token",
            "THOHAGO_WEB_STT_MODE": "stub",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
