from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.config import load_config
from thohago.interview_engine import HeuristicMultimodalInterviewEngine
from thohago.registry import load_shop_registry
from thohago.web.app import create_app


class MobileV1Phase3Tests(unittest.TestCase):
    def test_finalize_uploads_generates_turn1_and_stays_in_app_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, shops = self._client_bundle(Path(tmp_dir))
            session_id = self._create_session(client)
            self._upload_sample_image(client, session_id, shops)

            finalize = client.post(f"/app/session/{session_id}/upload/complete", follow_redirects=False)
            self.assertEqual(finalize.status_code, 303)
            self.assertEqual(finalize.headers["location"], f"/app/session/{session_id}")

            updated = app.state.runtime.session_repository.get_by_id(session_id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_turn1_answer")
            self.assertIsNotNone(updated.preflight_json)
            self.assertIsNotNone(updated.turn1_question)

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            self.assertTrue((artifacts.generated_dir / "media_preflight.json").exists())
            self.assertTrue((artifacts.prompts_dir / "turn1_question.txt").exists())
            self.assertTrue((artifacts.prompts_dir / "turn1_planner.json").exists())

            interview = client.get(finalize.headers["location"])
            self.assertEqual(interview.status_code, 200)
            self.assertIn(updated.turn1_question or "", interview.text)

    def test_reloading_after_duplicate_finalize_does_not_render_duplicate_turn1_bubble(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, shops = self._client_bundle(Path(tmp_dir))
            session_id = self._create_session(client)
            self._upload_sample_image(client, session_id, shops)

            first = client.post(f"/app/session/{session_id}/upload/complete", follow_redirects=False)
            self.assertEqual(first.status_code, 303)
            second = client.post(f"/app/session/{session_id}/upload/complete", follow_redirects=False)
            self.assertEqual(second.status_code, 303)

            session = app.state.runtime.session_repository.get_by_id(session_id)
            assert session is not None
            messages = app.state.runtime.session_repository.list_session_messages(session.id)
            turn1_messages = [
                message
                for message in messages
                if message.sender == "system" and message.message_type == "text" and message.turn_index == 1
            ]
            self.assertEqual(len(turn1_messages), 1)

            page = client.get(first.headers["location"])
            self.assertEqual(page.status_code, 200)
            self.assertEqual(page.text.count(session.turn1_question or ""), 1)

    def test_finalize_uploads_falls_back_to_heuristic_when_preflight_generation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, shops = self._client_bundle(Path(tmp_dir))
            session_id = self._create_session(client)
            self._upload_sample_image(client, session_id, shops)

            class BrokenPipeline:
                def prepare_media_artifacts(self, *args, **kwargs):
                    raise RuntimeError("preflight exploded")

            with patch.object(app.state.runtime.upload_service, "_resolve_pipeline_and_engine", return_value=(BrokenPipeline(), object())):
                finalize = client.post(f"/app/session/{session_id}/upload/complete", follow_redirects=False)

            self.assertEqual(finalize.status_code, 303)
            updated = app.state.runtime.session_repository.get_by_id(session_id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_turn1_answer")
            self.assertIsNotNone(updated.preflight_json)
            self.assertIsNotNone(updated.turn1_question)

    def test_app_session_submit_replace_and_retry_work_for_pending_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_app_session(Path(tmp_dir))

            submit = client.post(
                f"/app/session/{session.id}/interview/submit",
                data={"answer_text": "first answer"},
                follow_redirects=False,
            )
            self.assertEqual(submit.status_code, 303)
            self.assertEqual(submit.headers["location"], f"/app/session/{session.id}")

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "confirming_turn1")
            self.assertEqual(updated.pending_answer, "first answer")

            replace = client.post(
                f"/app/session/{session.id}/interview/submit",
                data={"answer_text": "replacement answer"},
                follow_redirects=False,
            )
            self.assertEqual(replace.status_code, 303)
            self.assertEqual(replace.headers["location"], f"/app/session/{session.id}")

            replaced = app.state.runtime.session_repository.get_by_id(session.id)
            assert replaced is not None
            self.assertEqual(replaced.stage, "confirming_turn1")
            self.assertEqual(replaced.pending_answer, "replacement answer")

            confirm_state = client.get(f"/app/session/{session.id}")
            self.assertEqual(confirm_state.status_code, 200)
            self.assertIn("data-interview-loading-modal", confirm_state.text)
            self.assertIn("다음 인터뷰 질문을 준비중입니다", confirm_state.text)

            retry = client.post(
                f"/app/session/{session.id}/interview/retry",
                follow_redirects=False,
            )
            self.assertEqual(retry.status_code, 303)
            self.assertEqual(retry.headers["location"], f"/app/session/{session.id}")

            refreshed = app.state.runtime.session_repository.get_by_id(session.id)
            assert refreshed is not None
            self.assertEqual(refreshed.stage, "awaiting_turn1_answer")
            self.assertIsNone(refreshed.pending_answer)

    def test_completing_all_turns_reaches_waiting_state_and_writes_single_full_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_app_session(Path(tmp_dir))

            turn1 = self._submit_and_confirm(client, session.id, "turn1 answer")
            self.assertEqual(turn1.status_code, 303)
            self.assertEqual(turn1.headers["location"], f"/app/session/{session.id}")

            after_turn1 = app.state.runtime.session_repository.get_by_id(session.id)
            assert after_turn1 is not None
            self.assertEqual(after_turn1.stage, "awaiting_turn2_answer")

            turn2 = self._submit_and_confirm(client, session.id, "turn2 answer")
            self.assertEqual(turn2.status_code, 303)
            self.assertEqual(turn2.headers["location"], f"/app/session/{session.id}")

            after_turn2 = app.state.runtime.session_repository.get_by_id(session.id)
            assert after_turn2 is not None
            self.assertEqual(after_turn2.stage, "awaiting_turn3_answer")

            final = self._submit_and_confirm(client, session.id, "turn3 answer")
            self.assertEqual(final.status_code, 303)
            self.assertEqual(final.headers["location"], f"/app/session/{session.id}")

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_production")
            self.assertIsNotNone(updated.interview_completed_at)

            artifacts = app.state.runtime.session_service.artifacts_for_session(updated)
            self.assertEqual(list(artifacts.transcripts_dir.glob("turn*_transcript.*")), [])
            self.assertTrue((artifacts.prompts_dir / "turn2_planner.json").exists())
            self.assertTrue((artifacts.prompts_dir / "turn3_planner.json").exists())

            full_transcript_candidates = sorted(artifacts.generated_dir.glob("interview_full_transcript_*.json"))
            self.assertEqual(len(full_transcript_candidates), 1)
            full_transcript_path = full_transcript_candidates[0]
            transcript_payload = json.loads(full_transcript_path.read_text(encoding="utf-8"))
            self.assertEqual(transcript_payload["session_id"], session.id)
            self.assertEqual(transcript_payload["interview_completed_at"], updated.interview_completed_at)
            self.assertEqual(len(transcript_payload["turns"]), 3)
            self.assertEqual(len(transcript_payload["messages"]), 6)
            self.assertEqual(transcript_payload["turns"][1]["answer"], "turn2 answer")

            intake_bundle_path = artifacts.generated_dir / "intake_bundle.json"
            self.assertTrue(intake_bundle_path.exists())
            intake_bundle = json.loads(intake_bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(intake_bundle["stage"], "awaiting_production")
            self.assertEqual(
                intake_bundle["full_transcript_path"],
                full_transcript_path.relative_to(artifacts.artifact_dir).as_posix(),
            )

            waiting = client.get(final.headers["location"])
            self.assertEqual(waiting.status_code, 200)
            self.assertIn("awaiting_production", waiting.text)
            self.assertIn("블로그 글 생성하기", waiting.text)
            self.assertIn("쓰레드 글 생성하기", waiting.text)
            self.assertIn("인스타 사진 생성하기", waiting.text)
            self.assertNotIn("숏폼 영상 생성하기", waiting.text)

            workspace = client.get("/app")
            self.assertEqual(workspace.status_code, 200)
            self.assertIn(session.id, workspace.text)

            metadata = json.loads((artifacts.artifact_dir / "session_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["stage"], "awaiting_production")
            self.assertIn("intake_bundle_path", metadata)
            self.assertEqual(metadata["full_transcript_path"], str(full_transcript_path))

    def test_turn2_planner_failure_falls_back_to_heuristic_in_app_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client, app, session = self._prepare_interview_ready_app_session(Path(tmp_dir))

            submit = client.post(
                f"/app/session/{session.id}/interview/submit",
                data={"answer_text": "turn1 answer"},
                follow_redirects=False,
            )
            self.assertEqual(submit.status_code, 303)

            original_resolve_pipeline = app.state.runtime.interview_service.__class__.__module__ + ".resolve_pipeline"

            class BrokenPipeline:
                def build_turn_planner(self, *args, **kwargs):
                    raise RuntimeError("planner exploded")

            with patch(original_resolve_pipeline, return_value=(BrokenPipeline(), object())):
                confirm = client.post(
                    f"/app/session/{session.id}/interview/confirm",
                    follow_redirects=False,
                )
            self.assertEqual(confirm.status_code, 303)
            self.assertEqual(confirm.headers["location"], f"/app/session/{session.id}")

            updated = app.state.runtime.session_repository.get_by_id(session.id)
            assert updated is not None
            self.assertEqual(updated.stage, "awaiting_turn2_answer")
            self.assertIsNotNone(updated.turn2_planner_json)

            planner_payload = json.loads(updated.turn2_planner_json or "{}")
            expected_question = HeuristicMultimodalInterviewEngine().plan_turn(
                2,
                ["turn1 answer"],
                json.loads(updated.preflight_json or "{}"),
            ).next_question
            self.assertEqual(planner_payload.get("next_question"), expected_question)

    def _submit_and_confirm(self, client: TestClient, session_id: str, answer_text: str):
        submit = client.post(
            f"/app/session/{session_id}/interview/submit",
            data={"answer_text": answer_text},
            follow_redirects=False,
        )
        self.assertEqual(submit.status_code, 303)
        return client.post(
            f"/app/session/{session_id}/interview/confirm",
            follow_redirects=False,
        )

    def _prepare_interview_ready_app_session(self, tmp_root: Path):
        client, app, shops = self._client_bundle(tmp_root)
        session_id = self._create_session(client)
        self._upload_sample_image(client, session_id, shops)

        finalize = client.post(f"/app/session/{session_id}/upload/complete", follow_redirects=False)
        self.assertEqual(finalize.status_code, 303)
        self.assertEqual(finalize.headers["location"], f"/app/session/{session_id}")

        session = app.state.runtime.session_repository.get_by_id(session_id)
        assert session is not None
        self.assertEqual(session.stage, "awaiting_turn1_answer")
        return client, app, session

    def _client_bundle(self, tmp_root: Path):
        env = {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://mobile.thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase3-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase3-password",
            "THOHAGO_SYNC_API_TOKEN": "phase3-sync-token",
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

    def _upload_sample_image(self, client: TestClient, session_id: str, shops) -> None:
        sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))
        with sample_image.open("rb") as handle:
            response = client.post(
                f"/app/session/{session_id}/upload",
                files=[("media", (sample_image.name, handle, "image/jpeg"))],
            )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
