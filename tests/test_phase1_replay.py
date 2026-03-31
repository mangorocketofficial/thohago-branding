from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from thohago.config import load_config
from thohago.pipeline import Phase1ReplayPipeline
from thohago.registry import load_shop_registry, resolve_shop_by_invite_token


class Phase1ReplayPipelineTests(unittest.TestCase):
    def test_registry_supports_multiple_shops(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        self.assertGreaterEqual(len(shops), 2)
        self.assertIn("sisun8082", shops)
        self.assertIn("demo_shop_2", shops)
        self.assertIn("sisun8082-start", shops["sisun8082"].invite_tokens)
        self.assertEqual(resolve_shop_by_invite_token(shops, "sisun8082-start").shop_id, "sisun8082")

    def test_replay_pipeline_writes_contract_artifacts(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = Phase1ReplayPipeline().run(
                artifact_root=Path(tmp_dir),
                shop=shops["sisun8082"],
                session_key="2026_03_27_core",
            )

            expected_paths = [
                result.artifacts.chat_log_path,
                result.media_preflight_path,
                result.turn2_planner_path,
                result.turn3_planner_path,
                result.content_bundle_path,
                result.blog_article_path,
                result.publish_result_path,
            ]
            for path in expected_paths:
                self.assertTrue(path.exists(), msg=f"missing expected artifact: {path}")

            content_bundle = json.loads(result.content_bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(content_bundle["shop"]["shop_id"], "sisun8082")
            # Q1 is now dynamically generated — just verify it exists and is non-empty
            turn1_q = content_bundle["interview"]["turn1_question"]
            self.assertTrue(len(turn1_q) > 10, msg="turn1_question should be meaningful")
            self.assertEqual(len(content_bundle["experience_sequence"]), len(content_bundle["photos"]))

            turn2_planner = json.loads(result.turn2_planner_path.read_text(encoding="utf-8"))
            self.assertIn("next_question", turn2_planner)
            self.assertIn("question_strategy", turn2_planner)

            chat_lines = result.artifacts.chat_log_path.read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(chat_lines), 8)
            first_entry = json.loads(chat_lines[0])
            last_entry = json.loads(chat_lines[-1])
            self.assertEqual(first_entry["sender"], "user")
            self.assertEqual(last_entry["sender"], "bot")
            self.assertEqual(last_entry["metadata"]["stage"], "completed")


if __name__ == "__main__":
    unittest.main()
