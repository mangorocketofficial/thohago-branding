from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.config import load_config
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class WebPhase3Tests(unittest.TestCase):
    def test_interview_page_renders_current_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase3_page")
            response = client.get(f"/s/{session.customer_token}/interview")
            self.assertEqual(response.status_code, 200)
            self.assertIn("첫번째 질문", response.text)
            self.assertIn(session.turn1_question or "", response.text)

    def test_text_submit_sets_pending_answer_and_retry_clears_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase3_retry")
            submit = client.post(
                f"/s/{session.customer_token}/interview/submit",
                data={"answer_text": "첫 번째 답변입니다."},
                follow_redirects=False,
            )
            self.assertEqual(submit.status_code, 303)

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "confirming_turn1")
            self.assertEqual(updated.pending_answer, "첫 번째 답변입니다.")

            retry = client.post(
                f"/s/{session.customer_token}/interview/retry",
                follow_redirects=False,
            )
            self.assertEqual(retry.status_code, 303)
            refreshed = app.state.runtime.session_repository.get_by_id(session.id)
            assert refreshed is not None
            self.assertEqual(refreshed.stage, "awaiting_turn1_answer")
            self.assertIsNone(refreshed.pending_answer)

    def test_replacing_pending_answer_overwrites_previous_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase3_replace")
            client.post(
                f"/s/{session.customer_token}/interview/submit",
                data={"answer_text": "첫 답변"},
                follow_redirects=False,
            )
            replace = client.post(
                f"/s/{session.customer_token}/interview/submit",
                data={"answer_text": "교체된 답변"},
                follow_redirects=False,
            )
            self.assertEqual(replace.status_code, 303)
            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "confirming_turn1")
            self.assertEqual(updated.pending_answer, "교체된 답변")

    def test_confirm_turn1_writes_transcript_and_turn2_planner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase3_turn1")
            client.post(
                f"/s/{session.customer_token}/interview/submit",
                data={"answer_text": "손님이 편하게 케어받던 분위기가 기억나요."},
                follow_redirects=False,
            )
            confirm = client.post(
                f"/s/{session.customer_token}/interview/confirm",
                follow_redirects=False,
            )
            self.assertEqual(confirm.status_code, 303)
            self.assertEqual(confirm.headers["location"], f"/s/{session.customer_token}/interview")

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_turn2_answer")
            self.assertIsNotNone(updated.turn2_planner_json)

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            self.assertTrue((artifacts.transcripts_dir / "turn1_transcript.txt").exists())
            self.assertTrue((artifacts.transcripts_dir / "turn1_transcript.json").exists())
            self.assertTrue((artifacts.prompts_dir / "turn2_question.txt").exists())
            self.assertTrue((artifacts.prompts_dir / "turn2_planner.json").exists())

            interview = client.get(confirm.headers["location"])
            self.assertEqual(interview.status_code, 200)
            self.assertIn("두번째 질문", interview.text)

    def test_completing_all_turns_exports_intake_bundle_and_waiting_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_session(Path(tmp_dir), "web_phase3_complete")

            self._submit_and_confirm(client, session.customer_token, "첫 번째 경험 설명입니다.")
            self._submit_and_confirm(client, session.customer_token, "두 번째 디테일 설명입니다.")
            final = self._submit_and_confirm(client, session.customer_token, "세 번째 관점 설명입니다.")

            self.assertEqual(final.status_code, 303)
            self.assertEqual(final.headers["location"], f"/s/{session.customer_token}/waiting")

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_production")
            self.assertIsNotNone(updated.interview_completed_at)

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            self.assertTrue((artifacts.transcripts_dir / "turn1_transcript.txt").exists())
            self.assertTrue((artifacts.transcripts_dir / "turn2_transcript.txt").exists())
            self.assertTrue((artifacts.transcripts_dir / "turn3_transcript.txt").exists())
            self.assertTrue((artifacts.prompts_dir / "turn2_planner.json").exists())
            self.assertTrue((artifacts.prompts_dir / "turn3_planner.json").exists())
            intake_bundle_path = artifacts.generated_dir / "intake_bundle.json"
            self.assertTrue(intake_bundle_path.exists())
            intake_bundle = json.loads(intake_bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(intake_bundle["stage"], "awaiting_production")
            self.assertEqual(len(intake_bundle["transcript_paths"]), 3)

            waiting = client.get(final.headers["location"])
            self.assertEqual(waiting.status_code, 200)
            self.assertIn("제작 대기", waiting.text)

            landing = client.get(f"/s/{session.customer_token}", follow_redirects=False)
            self.assertEqual(landing.status_code, 307)
            self.assertEqual(landing.headers["location"], f"/s/{session.customer_token}/waiting")

            metadata = json.loads((artifacts.artifact_dir / "session_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["stage"], "awaiting_production")
            self.assertIn("intake_bundle_path", metadata)

    def _submit_and_confirm(self, client: TestClient, customer_token: str, answer_text: str):
        submit = client.post(
            f"/s/{customer_token}/interview/submit",
            data={"answer_text": answer_text},
            follow_redirects=False,
        )
        self.assertEqual(submit.status_code, 303)
        confirm = client.post(
            f"/s/{customer_token}/interview/confirm",
            follow_redirects=False,
        )
        return confirm

    def _prepare_interview_ready_session(self, tmp_root: Path, session_key: str):
        env = self._web_env(tmp_root)
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        config = load_config()
        shops = load_shop_registry(config.shops_file)
        app = create_app(config=config, shops=shops)
        client = TestClient(app)
        sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))

        created = app.state.runtime.session_service.create_session(
            shop_id="sisun8082",
            session_key=session_key,
        )
        with sample_image.open("rb") as handle:
            upload = client.post(
                f"/s/{created.session.customer_token}/upload",
                files={"media": (sample_image.name, handle, "image/jpeg")},
            )
        self.assertEqual(upload.status_code, 200)
        finalize = client.post(
            f"/s/{created.session.customer_token}/upload/done",
            follow_redirects=False,
        )
        self.assertEqual(finalize.status_code, 303)

        session = app.state.runtime.session_repository.get_by_id(created.session.id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_turn1_answer")
        return client, app, session

    def _web_env(self, tmp_root: Path) -> dict[str, str]:
        return {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase3-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase3-password",
            "THOHAGO_SYNC_API_TOKEN": "phase3-sync-token",
            "GROQ_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
