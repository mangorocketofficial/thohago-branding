from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from thohago.bot import TelegramIntakeLoop, TelegramStateStore
from thohago.config import load_config
from thohago.registry import load_shop_registry


class FakeTelegramApi:
    def __init__(self, file_map: dict[str, Path]) -> None:
        self.file_map = file_map
        self.sent_messages: list[tuple[str, str]] = []

    def send_message(self, chat_id: str, text: str, reply_markup=None) -> None:
        self.sent_messages.append((chat_id, text))

    def answer_callback_query(self, callback_query_id: str) -> None:
        pass

    def download_file(self, file_id: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.file_map[file_id], destination)
        return destination


class TelegramIntakeLoopTests(unittest.TestCase):
    def test_caption_corruption_detector(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        fake_api = FakeTelegramApi({})

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = TelegramIntakeLoop(
                api=fake_api,
                artifact_root=Path(tmp_dir),
                shops=shops,
                state_store=TelegramStateStore(Path(tmp_dir) / "_runtime"),
            )

            self.assertTrue(loop._caption_looks_corrupted("?? ???? ??? ???? ??."))
            self.assertFalse(loop._caption_looks_corrupted("부산 서면에서 경험한 헤드스파 케어"))

    def test_start_with_invite_token_resets_active_session(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        sample_session = shops["sisun8082"].sample_sessions["2026_03_27_core"]
        fake_api = FakeTelegramApi({"photo1": next(sample_session.image_dir.glob("*.jpg"))})

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = TelegramIntakeLoop(
                api=fake_api,
                artifact_root=Path(tmp_dir),
                shops=shops,
                state_store=TelegramStateStore(Path(tmp_dir) / "_runtime"),
            )

            chat_id = "2000004"
            loop.handle_update({"update_id": 1, "message": {"chat": {"id": int(chat_id)}, "text": "/start sisun8082-start"}})
            loop.handle_update({"update_id": 2, "message": {"chat": {"id": int(chat_id)}, "text": "/begin"}})
            loop.handle_update({"update_id": 3, "message": {"chat": {"id": int(chat_id)}, "photo": [{"file_id": "photo1"}]}})
            loop.handle_update({"update_id": 4, "message": {"chat": {"id": int(chat_id)}, "text": "/start sisun8082-start"}})

            state = loop.state_store.load(chat_id)
            self.assertIsNotNone(state)
            self.assertEqual(state.stage, "collecting_media")
            self.assertEqual(state.photo_paths, [])
            self.assertFalse(any("진행 중인 세션이 있어요." in text for _, text in fake_api.sent_messages))

    def test_duplicate_photo_update_id_is_ignored(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        sample_session = shops["sisun8082"].sample_sessions["2026_03_27_core"]
        fake_api = FakeTelegramApi({"photo1": next(sample_session.image_dir.glob("*.jpg"))})

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = TelegramIntakeLoop(
                api=fake_api,
                artifact_root=Path(tmp_dir),
                shops=shops,
                state_store=TelegramStateStore(Path(tmp_dir) / "_runtime"),
            )

            chat_id = "2000002"
            loop.handle_update({"update_id": 1, "message": {"chat": {"id": int(chat_id)}, "text": "/start sisun8082-start"}})
            loop.handle_update({"update_id": 2, "message": {"chat": {"id": int(chat_id)}, "text": "/begin"}})
            duplicate_photo_update = {"update_id": 3, "message": {"chat": {"id": int(chat_id)}, "photo": [{"file_id": "photo1"}]}}
            loop.handle_update(duplicate_photo_update)
            loop.handle_update(duplicate_photo_update)

            state = loop.state_store.load(chat_id)
            self.assertIsNotNone(state)
            self.assertEqual(len(state.photo_paths), 1)
            self.assertEqual(sum("사진 저장 완료 (1장)" in text for _, text in fake_api.sent_messages), 1)

    def test_duplicate_interview_callback_update_id_is_ignored(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        sample_session = shops["sisun8082"].sample_sessions["2026_03_27_core"]
        fake_api = FakeTelegramApi({"photo1": next(sample_session.image_dir.glob("*.jpg"))})

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = TelegramIntakeLoop(
                api=fake_api,
                artifact_root=Path(tmp_dir),
                shops=shops,
                state_store=TelegramStateStore(Path(tmp_dir) / "_runtime"),
            )

            chat_id = "2000003"
            loop.handle_update({"update_id": 1, "message": {"chat": {"id": int(chat_id)}, "text": "/start sisun8082-start"}})
            loop.handle_update({"update_id": 2, "message": {"chat": {"id": int(chat_id)}, "text": "/begin"}})
            loop.handle_update({"update_id": 3, "message": {"chat": {"id": int(chat_id)}, "photo": [{"file_id": "photo1"}]}})

            duplicate_callback_update = {
                "update_id": 4,
                "callback_query": {
                    "id": "cb-interview",
                    "message": {"chat": {"id": int(chat_id)}},
                    "data": "interview",
                },
            }
            loop.handle_update(duplicate_callback_update)
            loop.handle_update(duplicate_callback_update)

            state = loop.state_store.load(chat_id)
            self.assertIsNotNone(state)
            self.assertEqual(state.stage, "awaiting_turn1_answer")
            self.assertEqual(sum("사진을 분석하고 있어요." in text for _, text in fake_api.sent_messages), 1)
            self.assertEqual(
                sum("이번 포스팅에 대해 이야기해볼까요?" in text for _, text in fake_api.sent_messages),
                1,
            )

    def test_text_driven_intake_loop_reaches_completion(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        sample_session = shops["sisun8082"].sample_sessions["2026_03_27_core"]
        fake_api = FakeTelegramApi({"photo1": next(sample_session.image_dir.glob("*.jpg"))})

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = TelegramIntakeLoop(
                api=fake_api,
                artifact_root=Path(tmp_dir),
                shops=shops,
                state_store=TelegramStateStore(Path(tmp_dir) / "_runtime"),
            )

            chat_id = "2000001"
            loop.handle_update({"message": {"chat": {"id": int(chat_id)}, "text": "/start sisun8082-start"}})
            loop.handle_update({"message": {"chat": {"id": int(chat_id)}, "text": "/begin"}})
            loop.handle_update({"message": {"chat": {"id": int(chat_id)}, "photo": [{"file_id": "photo1"}]}})
            loop.handle_update({"message": {"chat": {"id": int(chat_id)}, "text": "/interview"}})
            # Turn 1: answer + confirm
            loop.handle_update({"message": {"chat": {"id": int(chat_id)}, "text": "외국인 관광객이 한국 오기 전에 미리 예약하고 방문했어요."}})
            loop.handle_update({"callback_query": {"id": "cb1", "message": {"chat": {"id": int(chat_id)}}, "data": "confirm_answer"}})
            # Turn 2: answer + confirm
            loop.handle_update({"message": {"chat": {"id": int(chat_id)}, "text": "시술 받으면서 너무 시원하고 좋았다고 반응하셨어요."}})
            loop.handle_update({"callback_query": {"id": "cb2", "message": {"chat": {"id": int(chat_id)}}, "data": "confirm_answer"}})
            # Turn 3: answer + confirm
            loop.handle_update({"message": {"chat": {"id": int(chat_id)}, "text": "서면 중심가라 관광 동선상 들르기 좋아요."}})
            loop.handle_update({"callback_query": {"id": "cb3", "message": {"chat": {"id": int(chat_id)}}, "data": "confirm_answer"}})

            state = loop.state_store.load(chat_id)
            self.assertIsNotNone(state)
            self.assertEqual(state.stage, "completed")
            self.assertEqual(loop.state_store.resolve_bound_shop_id(chat_id), "sisun8082")
            self.assertTrue((Path(state.generated_dir) / "content_bundle.json").exists())
            self.assertTrue((Path(state.published_dir) / "publish_result.json").exists())
            self.assertTrue(Path(state.chat_log_path).exists())
            chat_lines = Path(state.chat_log_path).read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(chat_lines), 8)
            self.assertEqual(json.loads(chat_lines[-1])["metadata"]["stage"], "completed")
            # Last user-facing message should be the completion thank-you
            self.assertIn("감사", fake_api.sent_messages[-1][1])

    def test_unregistered_chat_is_rejected(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        fake_api = FakeTelegramApi({})

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = TelegramIntakeLoop(
                api=fake_api,
                artifact_root=Path(tmp_dir),
                shops=shops,
                state_store=TelegramStateStore(Path(tmp_dir) / "_runtime"),
            )
            loop.handle_update({"message": {"chat": {"id": 9999999}, "text": "/begin"}})

        self.assertIn("아직 연결되지 않은 채팅", fake_api.sent_messages[-1][1])

    def test_invalid_invite_token_is_rejected(self) -> None:
        config = load_config()
        shops = load_shop_registry(config.shops_file)
        fake_api = FakeTelegramApi({})

        with tempfile.TemporaryDirectory() as tmp_dir:
            loop = TelegramIntakeLoop(
                api=fake_api,
                artifact_root=Path(tmp_dir),
                shops=shops,
                state_store=TelegramStateStore(Path(tmp_dir) / "_runtime"),
            )
            loop.handle_update({"message": {"chat": {"id": 8888888}, "text": "/start invalid-token"}})

        self.assertIn("유효하지 않은 초대 링크", fake_api.sent_messages[-1][1])


if __name__ == "__main__":
    unittest.main()
