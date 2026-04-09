from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from thohago.anthropic_live import AnthropicMultimodalInterviewEngine
from thohago.config import load_config
from thohago.gemini_live import GeminiMultimodalInterviewEngine
from thohago.groq_live import GroqTranscriptionProvider
from thohago.interview_engine import HeuristicMultimodalInterviewEngine
from thohago.models import MediaAsset, PlannerOutput
from thohago.registry import load_shop_registry
from thohago.web.app import create_app
from thohago.web.services.pipeline_runtime import OrderedFallbackInterviewEngine, resolve_engine


class WebPhase10Tests(unittest.TestCase):
    def test_auto_engine_prefers_gemini_then_groq(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir), default_interview_engine="auto")
            env["GEMINI_API_KEY"] = "phase10-gemini-key"
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            engine = resolve_engine(config)
            self.assertIsInstance(engine, OrderedFallbackInterviewEngine)
            self.assertIsInstance(engine.engines[0], GeminiMultimodalInterviewEngine)

    def test_auto_engine_falls_back_to_groq_when_gemini_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir), default_interview_engine="auto")
            env["GEMINI_API_KEY"] = "phase10-gemini-key"
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            engine = resolve_engine(config)
            self.assertIsInstance(engine, OrderedFallbackInterviewEngine)

            primary, fallback = engine.engines
            self.assertIsInstance(primary, GeminiMultimodalInterviewEngine)

            with patch.object(primary, "plan_turn1", side_effect=RuntimeError("gemini failed")), patch.object(
                fallback,
                "plan_turn1",
                return_value=PlannerOutput(
                    turn_index=1,
                    main_angle="groq fallback",
                    covered_elements=[],
                    missing_elements=[],
                    question_strategy="scene_anchor",
                    next_question="그록이 대신 만든 질문입니다.",
                    evidence=["fallback"],
                ),
            ):
                planner = engine.plan_turn1({"photos": []})
            self.assertEqual(planner.next_question, "그록이 대신 만든 질문입니다.")

    def test_default_interview_engine_claude_overrides_groq_for_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir), default_interview_engine="claude")
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            engine = resolve_engine(config)
            self.assertIsInstance(engine, AnthropicMultimodalInterviewEngine)

    def test_default_interview_engine_heuristic_is_respected_even_with_api_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir), default_interview_engine="heuristic")
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            engine = resolve_engine(config)
            self.assertIsInstance(engine, HeuristicMultimodalInterviewEngine)

    def test_explicit_claude_selection_without_key_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir), default_interview_engine="claude")
            env["CLAUDE_API_KEY"] = ""
            env["ANTHROPIC_API_KEY"] = ""
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            with self.assertRaises(RuntimeError):
                resolve_engine(config)

    def test_web_flow_uses_claude_for_preflight_and_turn2_while_stt_remains_groq(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._web_env(Path(tmp_dir), default_interview_engine="claude")
            patcher = patch.dict(os.environ, env, clear=False)
            patcher.start()
            self.addCleanup(patcher.stop)

            config = load_config()
            shops = load_shop_registry(config.shops_file)
            sample_image = next(shops["sisun8082"].sample_sessions["2026_03_27_core"].image_dir.glob("*.jpg"))

            with patch.object(
                AnthropicMultimodalInterviewEngine,
                "build_preflight",
                new=self._fake_build_preflight,
            ), patch.object(
                AnthropicMultimodalInterviewEngine,
                "plan_turn1",
                new=self._fake_plan_turn1,
            ), patch.object(
                AnthropicMultimodalInterviewEngine,
                "plan_turn",
                new=self._fake_plan_turn,
            ):
                app = create_app(config=config, shops=shops)
                client = TestClient(app)

                self.assertIsInstance(app.state.runtime.transcriber, GroqTranscriptionProvider)

                created = app.state.runtime.session_service.create_session(shop_id="sisun8082", session_key="web_phase10_flow")
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
                preflight = json.loads(session.preflight_json or "{}")
                self.assertEqual(preflight["model_mode"], "anthropic_messages:test-claude")
                self.assertEqual(session.turn1_question, "클로드가 생성한 첫번째 질문은 어떤 흐름으로 진행됐나요?")

                client.post(
                    f"/s/{created.session.customer_token}/interview/submit",
                    data={"answer_text": "첫번째 답변"},
                    follow_redirects=False,
                )
                confirm = client.post(
                    f"/s/{created.session.customer_token}/interview/confirm",
                    follow_redirects=False,
                )
                self.assertEqual(confirm.status_code, 303)

                updated = app.state.runtime.session_repository.get_by_id(created.session.id)
                assert updated is not None
                turn2 = json.loads(updated.turn2_planner_json or "{}")
                self.assertEqual(turn2["next_question"], "클로드가 생성한 두번째 질문에서 가장 기억에 남는 장면은 무엇인가요?")
                self.assertEqual(turn2["question_strategy"], "detail_deepening")

    def _fake_build_preflight(self, shop, photos, videos):
        photo_assets = [
            MediaAsset(
                media_id=f"photo_{index}",
                kind="photo",
                source_path=path,
                relative_source_path=str(path),
                experience_order=index,
                preflight_analysis={"scene": "anthropic scene", "details": ["anthropic detail"], "mood": "calming"},
                selected_for_prompt=True,
            )
            for index, path in enumerate(photos, start=1)
        ]
        preflight = {
            "model_mode": "anthropic_messages:test-claude",
            "structure_mode": "chronological_experience_order",
            "experience_sequence": [asset.media_id for asset in photo_assets],
            "representative_photo_ids": [asset.media_id for asset in photo_assets],
            "key_visual_evidence": ["anthropic evidence"],
            "question_focus_candidates": ["anthropic focus"],
            "photos": [asset.to_dict() for asset in photo_assets],
            "videos": [],
        }
        return preflight, photo_assets, []

    def _fake_plan_turn1(self, preflight):
        return PlannerOutput(
            turn_index=1,
            main_angle="anthropic turn1",
            covered_elements=[],
            missing_elements=[],
            question_strategy="scene_anchor",
            next_question="클로드가 생성한 첫번째 질문은 어떤 흐름으로 진행됐나요?",
            evidence=["anthropic evidence"],
        )

    def _fake_plan_turn(self, turn_index, transcripts, preflight):
        return PlannerOutput(
            turn_index=turn_index,
            main_angle=f"anthropic turn{turn_index}",
            covered_elements=[],
            missing_elements=[],
            question_strategy="detail_deepening" if turn_index == 2 else "owner_perspective",
            next_question=(
                "클로드가 생성한 두번째 질문에서 가장 기억에 남는 장면은 무엇인가요?"
                if turn_index == 2
                else "클로드가 생성한 세번째 질문에서 사장님은 어떤 생각이 드셨나요?"
            ),
            evidence=["anthropic evidence"],
        )

    def _web_env(self, tmp_root: Path, *, default_interview_engine: str) -> dict[str, str]:
        return {
            "THOHAGO_ARTIFACT_ROOT": str((tmp_root / "runs").resolve()),
            "THOHAGO_WEB_DB_PATH": str((tmp_root / "runtime" / "web.sqlite3").resolve()),
            "THOHAGO_WEB_BASE_URL": "https://thohago.test",
            "THOHAGO_ADMIN_USERNAME": "phase10-admin",
            "THOHAGO_ADMIN_PASSWORD": "phase10-password",
            "THOHAGO_SYNC_API_TOKEN": "phase10-sync-token",
            "THOHAGO_WEB_STT_MODE": "groq",
            "THOHAGO_DEFAULT_INTERVIEW_ENGINE": default_interview_engine,
            "GEMINI_API_KEY": "",
            "GROQ_API_KEY": "phase10-groq-key",
            "CLAUDE_API_KEY": "phase10-claude-key",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GPT_API_KEY": "",
        }


if __name__ == "__main__":
    unittest.main()
