from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from thohago.artifacts import create_session_artifacts, write_json, write_text
from thohago.anthropic_live import AnthropicApiClient, AnthropicMultimodalInterviewEngine
from thohago.config import AppConfig, load_config
from thohago.groq_live import GroqApiClient, GroqMultimodalInterviewEngine, GroqTranscriptionProvider
from thohago.instagram_content import InstagramCaptionComposer
from thohago.instagram_publish import InstagramGraphPublisher, InstagramPublishError
from thohago.threads_content import ThreadsCaptionComposer
from thohago.threads_publish import ThreadsPublisher, ThreadsPublishError
from thohago.openai_live import OpenAIChatCompletionsClient, OpenAIMultimodalInterviewEngine
from thohago.models import MediaAsset, PlannerOutput, SessionArtifacts, ShopConfig, TranscriptArtifact
from thohago.pipeline import Phase1ReplayPipeline
from thohago.registry import load_shop_registry, resolve_shop_by_chat_id, resolve_shop_by_invite_token


HELP_TEXT = (
    "Thohago intake bot\n"
    "- /begin : 새 세션 시작\n"
    "- 사진/영상 업로드\n"
    "- /interview : 인터뷰 시작\n"
    "- 인터뷰 중에는 답변을 텍스트로 보내면 다음 질문으로 진행\n"
    "- /status : 현재 상태 확인\n"
    "- /reset : 현재 세션 초기화"
)


@dataclass(slots=True)
class TelegramSessionState:
    chat_id: str
    shop_id: str
    session_key: str
    session_id: str
    artifact_dir: str
    chat_log_path: str
    raw_dir: str
    prompts_dir: str
    transcripts_dir: str
    generated_dir: str
    published_dir: str
    stage: str
    photo_paths: list[str]
    video_paths: list[str]
    preflight: dict[str, Any] | None
    photo_assets: list[dict[str, Any]]
    video_assets: list[dict[str, Any]]
    transcripts: list[dict[str, Any]]
    turn2_planner: dict[str, Any] | None
    turn3_planner: dict[str, Any] | None
    pending_answer: str | None
    instagram_caption: str | None
    threads_caption: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelegramBotApi:
    def __init__(self, token: str) -> None:
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            payload["offset"] = offset
        return self._request("getUpdates", payload).get("result", [])

    def send_message(self, chat_id: str, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        self._request("sendMessage", payload)

    def answer_callback_query(self, callback_query_id: str) -> None:
        self._request("answerCallbackQuery", {"callback_query_id": callback_query_id})

    def delete_webhook(self, drop_pending_updates: bool = False) -> dict[str, Any]:
        return self._request("deleteWebhook", {"drop_pending_updates": drop_pending_updates})

    def download_file(self, file_id: str, destination: Path) -> Path:
        file_meta = self._request("getFile", {"file_id": file_id}).get("result", {})
        file_path = file_meta["file_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(f"{self.file_base_url}/{file_path}") as response:
            destination.write_bytes(response.read())
        return destination

    def _request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}/{method}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request) as response:
            parsed = json.loads(response.read().decode("utf-8"))
        if not parsed.get("ok", False):
            description = parsed.get("description", "Unknown Telegram API error")
            raise RuntimeError(f"{method} failed: {description}")
        return parsed


class TelegramStateStore:
    def __init__(self, runtime_root: Path) -> None:
        self.runtime_root = runtime_root
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def load(self, chat_id: str) -> TelegramSessionState | None:
        path = self.runtime_root / f"{chat_id}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TelegramSessionState(**payload)

    def save(self, state: TelegramSessionState) -> None:
        path = self.runtime_root / f"{state.chat_id}.json"
        path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        session_metadata_path = Path(state.artifact_dir) / "session_metadata.json"
        if session_metadata_path.parent.exists():
            session_metadata_path.write_text(
                json.dumps(
                    {
                        "shop_id": state.shop_id,
                        "chat_id": state.chat_id,
                        "session_key": state.session_key,
                        "session_id": state.session_id,
                        "artifact_dir": state.artifact_dir,
                        "chat_log_path": state.chat_log_path,
                        "stage": state.stage,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def clear(self, chat_id: str) -> None:
        path = self.runtime_root / f"{chat_id}.json"
        if path.exists():
            path.unlink()

    def _binding_path(self) -> Path:
        return self.runtime_root / "chat_bindings.json"

    def load_bindings(self) -> dict[str, str]:
        path = self._binding_path()
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def resolve_bound_shop_id(self, chat_id: str) -> str | None:
        return self.load_bindings().get(chat_id)

    def bind_chat_to_shop(self, chat_id: str, shop_id: str) -> None:
        bindings = self.load_bindings()
        bindings[chat_id] = shop_id
        self._binding_path().write_text(json.dumps(bindings, ensure_ascii=False, indent=2), encoding="utf-8")

    def claim_update(self, update_id: int | None) -> bool:
        if update_id is None:
            return True
        claims_dir = self.runtime_root / "processed_updates"
        claims_dir.mkdir(parents=True, exist_ok=True)
        claim_path = claims_dir / f"{update_id}.claim"
        try:
            handle = os.open(str(claim_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        try:
            os.write(handle, datetime.now(UTC).isoformat().encode("utf-8"))
        finally:
            os.close(handle)
        return True


class TelegramIntakeLoop:
    def __init__(
        self,
        api: TelegramBotApi,
        artifact_root: Path,
        shops: dict[str, ShopConfig],
        state_store: TelegramStateStore,
        pipeline: Phase1ReplayPipeline | None = None,
        fallback_pipeline: Phase1ReplayPipeline | None = None,
        final_fallback_pipeline: Phase1ReplayPipeline | None = None,
        instagram_publisher: InstagramGraphPublisher | None = None,
        threads_publisher: ThreadsPublisher | None = None,
    ) -> None:
        self.api = api
        self.artifact_root = artifact_root
        self.shops = shops
        self.state_store = state_store
        self.pipeline = pipeline or Phase1ReplayPipeline()
        self.fallback_pipeline = fallback_pipeline or Phase1ReplayPipeline()
        self.final_fallback_pipeline = final_fallback_pipeline or Phase1ReplayPipeline()
        self.instagram_publisher = instagram_publisher
        self.threads_publisher = threads_publisher
        self.instagram_caption_composer = InstagramCaptionComposer()
        self.threads_caption_composer = ThreadsCaptionComposer()
        # Debounce: track last media receive time per chat to send interview button once
        self._media_debounce: dict[str, float] = {}
        self._media_debounce_notified: set[str] = set()

    def run_forever(self) -> int:
        offset: int | None = None
        retry_delay = 1
        while True:
            try:
                updates = self.api.get_updates(offset=offset, timeout=30)
                retry_delay = 1  # Reset on success
                for update in updates:
                    offset = update["update_id"] + 1
                    try:
                        self.handle_update(update)
                    except Exception as exc:
                        print(f"[bot] Error handling update: {exc}")
                self._check_media_debounce()
                if not updates:
                    time.sleep(1)
            except Exception as exc:
                print(f"[bot] Network error, retrying in {retry_delay}s: {exc}")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s

    MEDIA_DEBOUNCE_SEC = 5

    def _check_media_debounce(self) -> None:
        """After MEDIA_DEBOUNCE_SEC of silence, send the interview-start button once."""
        now = time.monotonic()
        done = []
        for chat_id, last_time in self._media_debounce.items():
            if chat_id in self._media_debounce_notified:
                done.append(chat_id)
                continue
            if now - last_time >= self.MEDIA_DEBOUNCE_SEC:
                state = self.state_store.load(chat_id)
                if state and state.stage == "collecting_media":
                    n_photos = len(state.photo_paths)
                    n_videos = len(state.video_paths)
                    summary = []
                    if n_photos:
                        summary.append(f"사진 {n_photos}장")
                    if n_videos:
                        summary.append(f"영상 {n_videos}개")
                    media_text = ", ".join(summary) if summary else "미디어"
                    self.api.send_message(
                        chat_id,
                        f"모든 사진과 영상 저장을 완료했습니다! ({media_text})\n아래 인터뷰 시작 버튼을 눌러주세요.",
                        reply_markup=self._interview_start_button(),
                    )
                self._media_debounce_notified.add(chat_id)
                done.append(chat_id)
        for chat_id in done:
            self._media_debounce.pop(chat_id, None)

    def handle_update(self, update: dict[str, Any]) -> None:
        if not self.state_store.claim_update(update.get("update_id")):
            return

        # Handle button clicks (callback_query)
        if "callback_query" in update:
            self._handle_callback_query(update["callback_query"])
            return

        message = update.get("message")
        if not message:
            return

        chat_id = str(message["chat"]["id"])

        text = message.get("text", "")
        if text.startswith("/start"):
            self._handle_start(chat_id, text)
            return

        shop = self._resolve_shop_for_chat(chat_id)
        if not shop:
            self.api.send_message(chat_id, "아직 연결되지 않은 채팅입니다. 고객 전용 초대 링크를 다시 눌러서 시작해주세요.")
            return
        if text == "/begin":
            self._do_begin(shop, chat_id)
            return
        if text == "/reset":
            self.state_store.clear(chat_id)
            self.api.send_message(chat_id, "현재 세션을 초기화했습니다.", reply_markup=self._begin_button())
            return
        if text == "/status":
            self.api.send_message(chat_id, self._render_status(chat_id))
            return
        if text == "/interview":
            self._start_interview(shop, chat_id)
            return

        if "photo" in message:
            self._handle_photo_message(shop, chat_id, message)
            return
        if "video" in message:
            self._handle_video_message(shop, chat_id, message)
            return
        if "voice" in message or "audio" in message:
            self._handle_audio_message(shop, chat_id, message)
            return
        if text:
            self._handle_text_answer(shop, chat_id, text)

    # ---- Button helpers ----

    def _begin_button(self) -> dict:
        return {"inline_keyboard": [[{"text": "📸 시작하기 (사진/영상 전송)", "callback_data": "begin"}]]}

    def _interview_button(self) -> dict:
        return {"inline_keyboard": [[{"text": "🎤 인터뷰하기", "callback_data": "interview"}]]}

    def _interview_start_button(self) -> dict:
        return {"inline_keyboard": [[{"text": "🎤 인터뷰 시작", "callback_data": "interview"}]]}

    def _confirm_answer_buttons(self) -> dict:
        return {"inline_keyboard": [[
            {"text": "✅ 확인", "callback_data": "confirm_answer"},
            {"text": "🔄 다시 녹음", "callback_data": "retry_answer"},
        ]]}

    def _instagram_approval_buttons(self) -> dict:
        return {"inline_keyboard": [[
            {"text": "📷 인스타그램 업로드", "callback_data": "approve_instagram"},
            {"text": "건너뛰기", "callback_data": "skip_instagram"},
        ]]}

    def _threads_approval_buttons(self) -> dict:
        return {"inline_keyboard": [[
            {"text": "🧵 Threads 업로드", "callback_data": "approve_threads"},
            {"text": "건너뛰기", "callback_data": "skip_threads"},
        ]]}

    # ---- Callback query handler ----

    def _handle_callback_query(self, query: dict[str, Any]) -> None:
        chat_id = str(query["message"]["chat"]["id"])
        data = query.get("data", "")
        self.api.answer_callback_query(query["id"])

        shop = self._resolve_shop_for_chat(chat_id)
        if not shop:
            self.api.send_message(chat_id, "아직 연결되지 않은 채팅입니다. 초대 링크를 다시 눌러주세요.")
            return

        if data == "begin":
            self._do_begin(shop, chat_id)
        elif data == "interview":
            self.api.send_message(chat_id, "사진을 분석하고 있어요. 잠시만 기다려주세요...")
            self._start_interview(shop, chat_id)
        elif data == "confirm_answer":
            self._confirm_pending_answer(shop, chat_id)
        elif data == "retry_answer":
            self._retry_pending_answer(shop, chat_id)
        elif data == "approve_instagram":
            self._publish_to_instagram(shop, chat_id)
        elif data == "skip_instagram":
            self._skip_instagram(shop, chat_id)
        elif data == "approve_threads":
            self._publish_to_threads(shop, chat_id)
        elif data == "skip_threads":
            self._skip_threads(shop, chat_id)

    # ---- Begin flow ----

    def _do_begin(self, shop: ShopConfig, chat_id: str) -> None:
        state = self._create_new_session(shop, chat_id)
        self.api.send_message(
            chat_id,
            "\n".join([
                "안녕하세요!",
                "새로운 포스팅을 만들어볼까요?",
                "",
                "사진(최대 5장)이나 영상(30초 이내)을 첨부해주세요.",
            ]),
        )

    # ---- Start command ----

    def _handle_start(self, chat_id: str, text: str) -> None:
        parts = text.split(maxsplit=1)
        invite_token = parts[1].strip() if len(parts) > 1 else ""
        bound_shop = self._resolve_shop_for_chat(chat_id)

        if bound_shop and not invite_token:
            # Re-entered — check if active session exists
            state = self.state_store.load(chat_id)
            if state and state.stage not in ("completed", "awaiting_instagram_approval", "awaiting_threads_approval"):
                self.api.send_message(chat_id, f"진행 중인 세션이 있어요. 사진/영상을 보내거나 아래 버튼을 눌러주세요.", reply_markup=self._interview_button())
            else:
                self._do_begin(bound_shop, chat_id)
            return

        if bound_shop and invite_token:
            # A deep-linked /start is treated as an explicit fresh start request.
            self._do_begin(bound_shop, chat_id)
            return

        if not invite_token:
            self.api.send_message(chat_id, "이 채팅은 아직 연결되지 않았습니다. 고객 전용 초대 링크를 눌러서 시작해주세요.")
            return

        try:
            shop = resolve_shop_by_invite_token(self.shops, invite_token)
        except KeyError:
            self.api.send_message(chat_id, "유효하지 않은 초대 링크입니다. 최신 고객 전용 링크를 다시 받아서 시도해주세요.")
            return

        # Bind + immediately create session
        self.state_store.bind_chat_to_shop(chat_id, shop.shop_id)
        self._do_begin(shop, chat_id)

    def _resolve_shop_for_chat(self, chat_id: str) -> ShopConfig | None:
        bound_shop_id = self.state_store.resolve_bound_shop_id(chat_id)
        if bound_shop_id:
            return self.shops.get(bound_shop_id)
        try:
            return resolve_shop_by_chat_id(self.shops, chat_id)
        except KeyError:
            return None

    def _handle_photo_message(self, shop: ShopConfig, chat_id: str, message: dict[str, Any]) -> None:
        state = self._load_or_create_collecting_session(shop, chat_id)
        if state.stage != "collecting_media":
            self.api.send_message(chat_id, "이미 인터뷰가 시작됐습니다. 새 세션은 /reset 후 /begin 으로 시작해주세요.")
            return

        self.api.send_message(chat_id, "사진을 저장하고 있어요...")

        photo_sizes = message["photo"]
        file_id = photo_sizes[-1]["file_id"]
        destination = Path(state.raw_dir) / f"photo_{len(state.photo_paths) + 1:02d}.jpg"
        saved_path = self.api.download_file(file_id, destination)
        state.photo_paths.append(str(saved_path))
        self.state_store.save(state)
        self.pipeline.log_chat_event(
            artifacts=self._artifacts_from_state(shop, state),
            sender="user",
            message_type="photo",
            file_paths=[str(saved_path)],
        )
        self.api.send_message(chat_id, f"사진 저장 완료 ({len(state.photo_paths)}장)")
        self._media_debounce[chat_id] = time.monotonic()
        self._media_debounce_notified.discard(chat_id)

    MAX_VIDEO_DURATION_SEC = 60

    def _handle_video_message(self, shop: ShopConfig, chat_id: str, message: dict[str, Any]) -> None:
        state = self._load_or_create_collecting_session(shop, chat_id)
        if state.stage != "collecting_media":
            self.api.send_message(chat_id, "이미 인터뷰가 시작됐습니다. 새 세션은 /reset 후 /begin 으로 시작해주세요.")
            return

        # Check video duration from Telegram metadata
        video_duration = message.get("video", {}).get("duration", 0)
        if video_duration > self.MAX_VIDEO_DURATION_SEC:
            self.api.send_message(
                chat_id,
                f"영상이 너무 깁니다 ({video_duration}초). 1분 이내 영상만 사용 가능합니다. 짧은 영상으로 다시 보내주세요.",
            )
            return

        file_id = message["video"]["file_id"]
        destination = Path(state.raw_dir) / f"video_{len(state.video_paths) + 1:02d}.mp4"
        saved_path = self.api.download_file(file_id, destination)
        state.video_paths.append(str(saved_path))
        self.state_store.save(state)
        self.pipeline.log_chat_event(
            artifacts=self._artifacts_from_state(shop, state),
            sender="user",
            message_type="video",
            file_paths=[str(saved_path)],
        )
        self.api.send_message(chat_id, f"영상 저장 완료 ({len(state.video_paths)}개)")
        self._media_debounce[chat_id] = time.monotonic()
        self._media_debounce_notified.discard(chat_id)

    def _handle_audio_message(self, shop: ShopConfig, chat_id: str, message: dict[str, Any]) -> None:
        state = self.state_store.load(chat_id)
        if not state or not state.stage.startswith("awaiting_turn"):
            self.api.send_message(chat_id, "현재는 인터뷰 답변을 받을 단계가 아닙니다. /status 로 상태를 확인해주세요.")
            return

        self.api.send_message(chat_id, "전사중 ...")

        file_id = (message.get("voice") or message.get("audio"))["file_id"]
        turn_index = self._stage_to_turn_index(state.stage)
        destination = Path(state.raw_dir) / f"turn{turn_index}_voice.ogg"
        saved_path = self.api.download_file(file_id, destination)
        self.pipeline.log_chat_event(
            artifacts=self._artifacts_from_state(shop, state),
            sender="user",
            message_type="voice",
            file_paths=[str(saved_path)],
            metadata={"turn_index": turn_index},
        )
        if hasattr(self.pipeline.transcriber, "transcribe_audio"):
            try:
                result = self.pipeline.transcriber.transcribe_audio(saved_path, language="ko")
            except Exception as exc:
                self.api.send_message(
                    chat_id,
                    f"음성 전사에 실패했습니다: {exc}\n같은 답변을 텍스트로 한 번만 보내주세요.",
                )
                return
            # Show transcribed text, then ask for confirmation
            state.pending_answer = result.text
            state.stage = f"confirming_turn{turn_index}"
            self.state_store.save(state)
            self.api.send_message(chat_id, result.text)
            self.api.send_message(
                chat_id,
                "이 답변으로 제출하시겠어요?",
                reply_markup=self._confirm_answer_buttons(),
            )
            return

        self.api.send_message(
            chat_id,
            "음성 파일은 저장했습니다. 현재 live STT provider가 설정되지 않아 자동 전사는 못 합니다. 같은 답변을 텍스트로 한 번만 보내주세요.",
        )

    def _handle_text_answer(self, shop: ShopConfig, chat_id: str, text: str) -> None:
        state = self.state_store.load(chat_id)
        if not state:
            self.api.send_message(chat_id, "현재 인터뷰 단계가 아닙니다. /begin 후 사진을 보내고 /interview 로 시작해주세요.")
            return

        # If in confirming stage, treat text as a new answer replacing pending
        if state.stage.startswith("confirming_turn"):
            turn_index = self._stage_to_turn_index(state.stage)
            state.pending_answer = text
            self.state_store.save(state)
            self.api.send_message(
                chat_id,
                "이 답변으로 제출하시겠어요?",
                reply_markup=self._confirm_answer_buttons(),
            )
            return

        if not state.stage.startswith("awaiting_turn"):
            self.api.send_message(chat_id, "현재 인터뷰 단계가 아닙니다. /begin 후 사진을 보내고 /interview 로 시작해주세요.")
            return

        # Save pending answer and ask for confirmation
        turn_index = self._stage_to_turn_index(state.stage)
        state.pending_answer = text
        state.stage = f"confirming_turn{turn_index}"
        self.state_store.save(state)
        self.api.send_message(
            chat_id,
            "이 답변으로 제출하시겠어요?",
            reply_markup=self._confirm_answer_buttons(),
        )
        return

    def _confirm_pending_answer(self, shop: ShopConfig, chat_id: str) -> None:
        """User confirmed their answer — proceed to next question."""
        state = self.state_store.load(chat_id)
        if not state or not state.stage.startswith("confirming_turn"):
            return

        turn_index = self._stage_to_turn_index(state.stage)
        text = state.pending_answer or ""
        state.pending_answer = None
        state.stage = f"awaiting_turn{turn_index}_answer"  # Restore to process

        self.api.send_message(chat_id, "답변이 제출되었어요. 다음 질문을 준비하고 있어요...")

        artifacts = self._artifacts_from_state(shop, state)
        source_path = Path(state.transcripts_dir) / f"turn{turn_index}_live_input.txt"
        write_text(source_path, text)
        transcript_artifact = self.pipeline.write_transcript_artifact(
            artifacts=artifacts,
            turn_index=turn_index,
            source_path=source_path,
            transcript_text=text,
        )
        state.transcripts.append(transcript_artifact.to_dict())
        self.pipeline.log_chat_event(
            artifacts=artifacts,
            sender="user",
            message_type="text",
            text=text,
            metadata={"turn_index": turn_index},
        )

        if turn_index == 1:
            planner, _ = self._build_turn_planner_with_fallback(
                artifacts=artifacts,
                turn_index=2,
                transcripts=[text],
                preflight=state.preflight or {},
                chat_id=chat_id,
            )
            state.turn2_planner = planner.to_dict()
            state.stage = "awaiting_turn2_answer"
            self.state_store.save(state)
            self.pipeline.log_chat_event(
                artifacts=artifacts,
                sender="bot",
                message_type="text",
                text=planner.next_question,
                metadata={"turn_index": 2},
            )
            self.api.send_message(chat_id, planner.next_question)
            return

        if turn_index == 2:
            transcript_texts = [item["transcript_text"] for item in state.transcripts[:2]]
            planner, _ = self._build_turn_planner_with_fallback(
                artifacts=artifacts,
                turn_index=3,
                transcripts=transcript_texts,
                preflight=state.preflight or {},
                chat_id=chat_id,
            )
            state.turn3_planner = planner.to_dict()
            state.stage = "awaiting_turn3_answer"
            self.state_store.save(state)
            self.pipeline.log_chat_event(
                artifacts=artifacts,
                sender="bot",
                message_type="text",
                text=planner.next_question,
                metadata={"turn_index": 3},
            )
            self.api.send_message(chat_id, planner.next_question)
            return

        self.api.send_message(
            chat_id,
            "\n".join([
                "모든 답변이 제출되었어요.",
                "인터뷰에 응해주셔서 감사드립니다!",
                "",
                "콘텐츠를 생성하고 있어요...",
            ]),
        )

        transcript_artifacts = [self._transcript_from_dict(item) for item in state.transcripts]
        photo_assets = [self._media_from_dict(item) for item in state.photo_assets]
        video_assets = [self._media_from_dict(item) for item in state.video_assets]
        turn2_planner = self._planner_from_dict(state.turn2_planner)
        turn3_planner = self._planner_from_dict(state.turn3_planner)

        content_bundle_path, blog_article_path, publish_result_path = self.pipeline.finalize_session(
            artifacts=artifacts,
            shop=shop,
            photo_assets=photo_assets,
            video_assets=video_assets,
            preflight=state.preflight or {},
            transcript_artifacts=transcript_artifacts,
            turn2_planner=turn2_planner,
            turn3_planner=turn3_planner,
        )

        # Generate Instagram caption and offer upload
        if self.instagram_publisher and photo_assets:
            try:
                caption = self.instagram_caption_composer.compose(
                    shop=shop,
                    photos=photo_assets,
                    transcripts=transcript_artifacts,
                    turn2_planner=turn2_planner,
                    turn3_planner=turn3_planner,
                )
                state.instagram_caption = caption
                state.stage = "awaiting_instagram_approval"
                self.state_store.save(state)

                # Save caption to artifacts
                from thohago.artifacts import write_text as _write_text
                _write_text(
                    Path(state.generated_dir) / "instagram_caption.txt",
                    caption,
                )

                # Send preview to user
                preview_msg = "\n".join([
                    "블로그 글이 생성되었습니다!",
                    "",
                    "--- 인스타그램 캡션 미리보기 ---",
                    "",
                    caption,
                    "",
                    "---",
                    "",
                    f"사진 {len(photo_assets)}장으로 캐러셀을 업로드할까요?",
                ])
                self.api.send_message(chat_id, preview_msg, reply_markup=self._instagram_approval_buttons())
                return
            except Exception as exc:
                print(f"[bot] Instagram caption generation failed: {exc}")
                self.api.send_message(chat_id, f"인스타그램 캡션 생성에 실패했습니다: {exc}")

        # No Instagram publisher configured or caption failed — complete
        state.stage = "completed"
        self.state_store.save(state)
        self.api.send_message(
            chat_id,
            "인터뷰에 응해주셔서 감사드립니다! 콘텐츠 생성이 완료되었어요.",
        )

    def _retry_pending_answer(self, shop: ShopConfig, chat_id: str) -> None:
        """User wants to re-record — go back to awaiting state."""
        state = self.state_store.load(chat_id)
        if not state or not state.stage.startswith("confirming_turn"):
            return

        turn_index = self._stage_to_turn_index(state.stage)
        state.pending_answer = None
        state.stage = f"awaiting_turn{turn_index}_answer"
        self.state_store.save(state)
        self.api.send_message(chat_id, "답변을 다시 보내주세요. 음성 또는 텍스트 모두 가능합니다.")

    def _caption_looks_corrupted(self, text: str) -> bool:
        if not text.strip():
            return True
        if "??" in text or "\ufffd" in text:
            return True
        hangul_count = len(re.findall(r"[\u3131-\u318E\uAC00-\uD7A3]", text))
        question_count = text.count("?")
        return question_count >= 5 and hangul_count == 0

    def _refresh_instagram_caption(self, shop: ShopConfig, state: TelegramSessionState) -> str:
        photo_assets = [self._media_from_dict(item) for item in state.photo_assets]
        transcript_artifacts = [self._transcript_from_dict(item) for item in state.transcripts]
        turn2_planner = self._planner_from_dict(state.turn2_planner)
        turn3_planner = self._planner_from_dict(state.turn3_planner)
        caption = self.instagram_caption_composer.compose(
            shop=shop,
            photos=photo_assets,
            transcripts=transcript_artifacts,
            turn2_planner=turn2_planner,
            turn3_planner=turn3_planner,
        )
        state.instagram_caption = caption
        self.state_store.save(state)
        write_text(Path(state.generated_dir) / "instagram_caption.txt", caption)
        return caption

    def _publish_to_instagram(self, shop: ShopConfig, chat_id: str) -> None:
        """User approved — upload carousel to Instagram."""
        state = self.state_store.load(chat_id)
        if not state or state.stage != "awaiting_instagram_approval":
            self.api.send_message(chat_id, "인스타그램 업로드 대기 상태가 아닙니다.")
            return
        if not self.instagram_publisher:
            self.api.send_message(chat_id, "인스타그램 연동이 설정되지 않았습니다.")
            state.stage = "completed"
            self.state_store.save(state)
            return

        self.api.send_message(chat_id, "인스타그램에 업로드 중입니다... 잠시만 기다려주세요.")

        photo_assets = [self._media_from_dict(item) for item in state.photo_assets]
        image_paths = [asset.source_path for asset in photo_assets if asset.selected_for_prompt]
        if not image_paths:
            image_paths = [asset.source_path for asset in photo_assets]

        caption = state.instagram_caption or ""
        if self._caption_looks_corrupted(caption):
            try:
                caption = self._refresh_instagram_caption(shop, state)
            except Exception as exc:
                print(f"[bot] Instagram caption refresh failed: {exc}")
                self.api.send_message(chat_id, f"인스타그램 캡션 재생성에 실패했습니다: {exc}")
                return

        try:
            if len(image_paths) >= 2:
                result = self.instagram_publisher.publish_carousel(image_paths, caption)
            else:
                result = self.instagram_publisher.publish_single_image(image_paths[0], caption)

            # Save result
            publish_result_path = Path(state.published_dir) / "instagram_publish_result.json"
            write_json(publish_result_path, result)

            permalink = result.get("permalink", "")
            self.api.send_message(
                chat_id,
                "\n".join([
                    "인스타그램 업로드가 완료되었습니다!",
                    f"게시물 링크: {permalink}" if permalink else "게시물이 성공적으로 업로드되었습니다.",
                ]),
            )
        except InstagramPublishError as exc:
            self.api.send_message(chat_id, f"인스타그램 업로드에 실패했습니다: {exc}")
        except Exception as exc:
            self.api.send_message(chat_id, f"업로드 중 오류가 발생했습니다: {exc}")

        self._offer_threads_upload(shop, chat_id, state)

    def _skip_instagram(self, shop: ShopConfig, chat_id: str) -> None:
        """User chose to skip Instagram upload."""
        state = self.state_store.load(chat_id)
        if not state or state.stage != "awaiting_instagram_approval":
            return
        self._offer_threads_upload(shop, chat_id, state)

    def _offer_threads_upload(self, shop: ShopConfig, chat_id: str, state: TelegramSessionState) -> None:
        """After Instagram step, offer Threads upload if configured."""
        if not self.threads_publisher:
            state.stage = "completed"
            self.state_store.save(state)
            self.api.send_message(chat_id, "모든 콘텐츠 발행이 완료되었습니다!")
            return

        photo_assets = [self._media_from_dict(item) for item in state.photo_assets]
        transcript_artifacts = [self._transcript_from_dict(item) for item in state.transcripts]
        turn2_planner = self._planner_from_dict(state.turn2_planner)
        turn3_planner = self._planner_from_dict(state.turn3_planner)

        try:
            caption = self.threads_caption_composer.compose(
                shop=shop,
                photos=photo_assets,
                transcripts=transcript_artifacts,
                turn2_planner=turn2_planner,
                turn3_planner=turn3_planner,
            )
            state.threads_caption = caption
            state.stage = "awaiting_threads_approval"
            self.state_store.save(state)

            from thohago.artifacts import write_text as _write_text
            _write_text(
                Path(state.generated_dir) / "threads_caption.txt",
                caption,
            )

            preview_msg = "\n".join([
                "--- Threads 캡션 미리보기 ---",
                "",
                caption,
                "",
                "---",
                "",
                "Threads에 업로드할까요?",
            ])
            self.api.send_message(chat_id, preview_msg, reply_markup=self._threads_approval_buttons())
        except Exception as exc:
            print(f"[bot] Threads caption generation failed: {exc}")
            state.stage = "completed"
            self.state_store.save(state)
            self.api.send_message(chat_id, f"Threads 캡션 생성에 실패했습니다. 콘텐츠 발행이 완료되었습니다.")

    def _publish_to_threads(self, shop: ShopConfig, chat_id: str) -> None:
        """User approved — upload to Threads."""
        state = self.state_store.load(chat_id)
        if not state or state.stage != "awaiting_threads_approval":
            self.api.send_message(chat_id, "Threads 업로드 대기 상태가 아닙니다.")
            return
        if not self.threads_publisher:
            state.stage = "completed"
            self.state_store.save(state)
            return

        self.api.send_message(chat_id, "Threads에 업로드 중입니다... 잠시만 기다려주세요.")

        photo_assets = [self._media_from_dict(item) for item in state.photo_assets]
        image_paths = [asset.source_path for asset in photo_assets if asset.selected_for_prompt]
        if not image_paths:
            image_paths = [asset.source_path for asset in photo_assets]

        caption = state.threads_caption or ""

        try:
            if len(image_paths) >= 2:
                result = self.threads_publisher.publish_carousel(image_paths, caption)
            elif len(image_paths) == 1:
                result = self.threads_publisher.publish_single_image(image_paths[0], caption)
            else:
                result = self.threads_publisher.publish_text(caption)

            publish_result_path = Path(state.published_dir) / "threads_publish_result.json"
            write_json(publish_result_path, result)

            permalink = result.get("permalink", "")
            self.api.send_message(
                chat_id,
                "\n".join([
                    "Threads 업로드가 완료되었습니다!",
                    f"게시물 링크: {permalink}" if permalink else "게시물이 성공적으로 업로드되었습니다.",
                ]),
            )
        except ThreadsPublishError as exc:
            self.api.send_message(chat_id, f"Threads 업로드에 실패했습니다: {exc}")
        except Exception as exc:
            self.api.send_message(chat_id, f"업로드 중 오류가 발생했습니다: {exc}")

        state.stage = "completed"
        self.state_store.save(state)
        self.api.send_message(chat_id, "모든 콘텐츠 발행이 완료되었습니다!")

    def _skip_threads(self, shop: ShopConfig, chat_id: str) -> None:
        """User chose to skip Threads upload."""
        state = self.state_store.load(chat_id)
        if not state or state.stage != "awaiting_threads_approval":
            return
        state.stage = "completed"
        self.state_store.save(state)
        self.api.send_message(chat_id, "모든 콘텐츠 발행이 완료되었습니다!")

    def _start_interview(self, shop: ShopConfig, chat_id: str) -> None:
        state = self.state_store.load(chat_id)
        if not state:
            self.api.send_message(chat_id, "활성 세션이 없습니다. /begin 으로 세션을 시작해주세요.")
            return
        if state.stage != "collecting_media":
            self.api.send_message(chat_id, "이미 인터뷰가 시작되었거나 종료되었습니다. /status 로 상태를 확인해주세요.")
            return
        if not state.photo_paths:
            self.api.send_message(chat_id, "사진이 없습니다. 최소 1장 이상의 사진을 먼저 보내주세요.")
            return

        # Use only the latest 5 photos
        MAX_PHOTOS = 5
        selected_photos = state.photo_paths[-MAX_PHOTOS:]
        if len(state.photo_paths) > MAX_PHOTOS:
            self.api.send_message(
                chat_id,
                f"사진 {len(state.photo_paths)}장 중 최근 {MAX_PHOTOS}장을 사용합니다.",
            )

        artifacts = self._artifacts_from_state(shop, state)
        preflight, photo_assets, video_assets, _ = self._prepare_media_with_fallback(
            artifacts=artifacts,
            shop=shop,
            photos=[Path(path) for path in selected_photos],
            videos=[Path(path) for path in state.video_paths],
            chat_id=chat_id,
        )
        write_text(Path(state.prompts_dir) / "turn1_question.txt", "이번 포스팅에 대해 이야기해볼까요? 어떤 상황이었고, 무엇이 가장 인상깊으셨나요?")
        state.preflight = preflight
        state.photo_assets = [asset.to_dict() for asset in photo_assets]
        state.video_assets = [asset.to_dict() for asset in video_assets]
        state.stage = "awaiting_turn1_answer"
        self.state_store.save(state)
        turn1_question = "이번 포스팅에 대해 이야기해볼까요? 어떤 상황이었고, 무엇이 가장 인상깊으셨나요?"
        self.pipeline.log_chat_event(
            artifacts=artifacts,
            sender="bot",
            message_type="text",
            text=turn1_question,
            metadata={"turn_index": 1},
        )
        self.api.send_message(chat_id, turn1_question)

    def _create_new_session(self, shop: ShopConfig, chat_id: str) -> TelegramSessionState:
        self.state_store.clear(chat_id)
        session_key = datetime.now(UTC).strftime("live_%Y%m%dT%H%M%S")
        artifacts = create_session_artifacts(self.artifact_root, shop, session_key)
        state = TelegramSessionState(
            chat_id=chat_id,
            shop_id=shop.shop_id,
            session_key=session_key,
            session_id=artifacts.session_id,
            artifact_dir=str(artifacts.artifact_dir),
            chat_log_path=str(artifacts.chat_log_path),
            raw_dir=str(artifacts.raw_dir),
            prompts_dir=str(artifacts.prompts_dir),
            transcripts_dir=str(artifacts.transcripts_dir),
            generated_dir=str(artifacts.generated_dir),
            published_dir=str(artifacts.published_dir),
            stage="collecting_media",
            photo_paths=[],
            video_paths=[],
            preflight=None,
            photo_assets=[],
            video_assets=[],
            transcripts=[],
            turn2_planner=None,
            turn3_planner=None,
            pending_answer=None,
            instagram_caption=None,
            threads_caption=None,
        )
        write_json(Path(state.artifact_dir) / "session_metadata.json", {
            "shop_id": shop.shop_id,
            "chat_id": chat_id,
            "session_key": state.session_key,
            "session_id": state.session_id,
            "artifact_dir": state.artifact_dir,
            "chat_log_path": state.chat_log_path,
            "stage": state.stage,
        })
        self.state_store.save(state)
        return state

    def _load_or_create_collecting_session(self, shop: ShopConfig, chat_id: str) -> TelegramSessionState:
        state = self.state_store.load(chat_id)
        if state:
            return state
        return self._create_new_session(shop, chat_id)

    def _render_status(self, chat_id: str) -> str:
        state = self.state_store.load(chat_id)
        if not state:
            return "활성 세션이 없습니다. /begin 으로 시작해주세요."
        return (
            f"shop_id={state.shop_id}\n"
            f"session_id={state.session_id}\n"
            f"stage={state.stage}\n"
            f"photos={len(state.photo_paths)}\n"
            f"videos={len(state.video_paths)}\n"
            f"answers={len(state.transcripts)}"
        )

    def _artifacts_from_state(self, shop: ShopConfig, state: TelegramSessionState) -> SessionArtifacts:
        return SessionArtifacts(
            shop=shop,
            session_key=state.session_key,
            session_id=state.session_id,
            artifact_dir=Path(state.artifact_dir),
            chat_log_path=Path(state.chat_log_path),
            raw_dir=Path(state.raw_dir),
            prompts_dir=Path(state.prompts_dir),
            transcripts_dir=Path(state.transcripts_dir),
            generated_dir=Path(state.generated_dir),
            published_dir=Path(state.published_dir),
        )

    def _stage_to_turn_index(self, stage: str) -> int:
        return {
            "awaiting_turn1_answer": 1,
            "awaiting_turn2_answer": 2,
            "awaiting_turn3_answer": 3,
            "confirming_turn1": 1,
            "confirming_turn2": 2,
            "confirming_turn3": 3,
        }[stage]

    def _planner_from_dict(self, payload: dict[str, Any] | None) -> PlannerOutput:
        if payload is None:
            raise ValueError("Planner payload is missing")
        return PlannerOutput(**payload)

    def _media_from_dict(self, payload: dict[str, Any]) -> MediaAsset:
        return MediaAsset(
            media_id=payload["media_id"],
            kind=payload["kind"],
            source_path=Path(payload["source_path"]),
            relative_source_path=payload["relative_source_path"],
            experience_order=payload["experience_order"],
            preflight_analysis=payload["preflight_analysis"],
            selected_for_prompt=payload["selected_for_prompt"],
            reels_eligible=payload.get("reels_eligible", False),
            duration_sec=payload.get("duration_sec"),
        )

    def _transcript_from_dict(self, payload: dict[str, Any]) -> TranscriptArtifact:
        return TranscriptArtifact(
            turn_index=payload["turn_index"],
            source_path=Path(payload["source_path"]),
            transcript_text=payload["transcript_text"],
        )

    def _prepare_media_with_fallback(self, artifacts, shop: ShopConfig, photos: list[Path], videos: list[Path], chat_id: str):
        try:
            return self.pipeline.prepare_media_artifacts(
                artifacts=artifacts,
                shop=shop,
                photos=photos,
                videos=videos,
            )
        except Exception as exc:
            self.api.send_message(chat_id, f"실제 AI preflight 호출에 실패해서 fallback 모드로 진행합니다: {exc}")
            try:
                return self.fallback_pipeline.prepare_media_artifacts(
                    artifacts=artifacts,
                    shop=shop,
                    photos=photos,
                    videos=videos,
                )
            except Exception as fallback_exc:
                self.api.send_message(chat_id, f"OpenAI fallback preflight에도 실패했습니다. heuristic fallback으로 전환합니다: {fallback_exc}")
                return self.final_fallback_pipeline.prepare_media_artifacts(
                    artifacts=artifacts,
                    shop=shop,
                    photos=photos,
                    videos=videos,
                )

    def _build_turn_planner_with_fallback(self, artifacts, turn_index: int, transcripts: list[str], preflight: dict, chat_id: str):
        try:
            return self.pipeline.build_turn_planner(
                artifacts=artifacts,
                turn_index=turn_index,
                transcripts=transcripts,
                preflight=preflight,
            )
        except Exception as exc:
            self.api.send_message(chat_id, f"실제 AI 질문 생성에 실패해서 fallback 모드로 진행합니다: {exc}")
            try:
                return self.fallback_pipeline.build_turn_planner(
                    artifacts=artifacts,
                    turn_index=turn_index,
                    transcripts=transcripts,
                    preflight=preflight,
                )
            except Exception as fallback_exc:
                self.api.send_message(chat_id, f"OpenAI fallback 질문 생성에도 실패했습니다. heuristic fallback으로 전환합니다: {fallback_exc}")
                return self.final_fallback_pipeline.build_turn_planner(
                    artifacts=artifacts,
                    turn_index=turn_index,
                    transcripts=transcripts,
                    preflight=preflight,
                )


def start_bot() -> int:
    config = load_config()
    shops = load_shop_registry(config.shops_file)
    if not config.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not configured. Bot startup is blocked.")
        return 1

    api = TelegramBotApi(config.telegram_bot_token)
    api.delete_webhook(drop_pending_updates=False)
    state_store = TelegramStateStore(config.artifact_root / "_telegram_runtime")
    pipeline = Phase1ReplayPipeline()
    fallback_pipeline = Phase1ReplayPipeline()
    final_fallback_pipeline = Phase1ReplayPipeline()
    provider_label = "heuristic"
    fallback_label = "heuristic"
    if config.openai_api_key:
        openai_client = OpenAIChatCompletionsClient(config.openai_api_key, config.openai_model)
        fallback_pipeline = Phase1ReplayPipeline(
            engine=OpenAIMultimodalInterviewEngine(openai_client),
            transcriber=final_fallback_pipeline.transcriber,
        )
        fallback_label = f"openai:{config.openai_model}"
    if config.groq_api_key and config.anthropic_api_key:
        groq_client = GroqApiClient(config.groq_api_key)
        anthropic_client = AnthropicApiClient(config.anthropic_api_key, config.anthropic_model)
        pipeline = Phase1ReplayPipeline(
            engine=AnthropicMultimodalInterviewEngine(anthropic_client),
            transcriber=GroqTranscriptionProvider(groq_client, config.groq_stt_model),
        )
        provider_label = f"anthropic:{config.anthropic_model}+groq:{config.groq_stt_model}"
    elif config.groq_api_key:
        groq_client = GroqApiClient(config.groq_api_key)
        pipeline = Phase1ReplayPipeline(
            engine=GroqMultimodalInterviewEngine(groq_client, config.groq_vision_model),
            transcriber=GroqTranscriptionProvider(groq_client, config.groq_stt_model),
        )
        provider_label = f"groq:{config.groq_vision_model}+{config.groq_stt_model}"
    # Instagram publisher (optional — only if credentials are configured)
    # NOTE: 자동 업로드 기능 임시 비활성화 (수동 재활성화 필요)
    ig_publisher = None
    # if config.instagram_access_token and config.instagram_business_account_id and config.facebook_page_id:
    #     try:
    #         candidate = InstagramGraphPublisher(
    #             access_token=config.instagram_access_token,
    #             ig_user_id=config.instagram_business_account_id,
    #             fb_page_id=config.facebook_page_id,
    #             graph_version=config.instagram_graph_version,
    #         )
    #         candidate.validate_access()
    #         ig_publisher = candidate
    #         print(f"Instagram publisher enabled: ig_user={config.instagram_business_account_id}")
    #     except InstagramPublishError as exc:
    #         print(f"Instagram publisher disabled (auth/permission check failed: {exc})")
    # else:
    #     print("Instagram publisher disabled (missing GRAPH_META_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ACCOUNT_ID / FACEBOOK_PAGE_ID)")
    print("Instagram publisher disabled (자동 업로드 임시 비활성화)")

    # Threads publisher (optional)
    # NOTE: 자동 업로드 기능 임시 비활성화 (수동 재활성화 필요)
    threads_pub = None
    # if config.threads_access_token and config.threads_user_id and config.facebook_page_id:
    #     try:
    #         candidate = ThreadsPublisher(
    #             access_token=config.threads_access_token,
    #             threads_user_id=config.threads_user_id,
    #             fb_page_id=config.facebook_page_id,
    #             fb_page_upload_token=config.instagram_access_token,
    #             graph_version=config.instagram_graph_version,
    #         )
    #         candidate.validate_access()
    #         threads_pub = candidate
    #         print(f"Threads publisher enabled: user={config.threads_user_id}")
    #     except ThreadsPublishError as exc:
    #         print(f"Threads publisher disabled (auth/permission check failed: {exc})")
    # else:
    #     print("Threads publisher disabled (missing THREADS_ACCESS_TOKEN / THREADS_USER_ID / FACEBOOK_PAGE_ID)")
    print("Threads publisher disabled (자동 업로드 임시 비활성화)")

    loop = TelegramIntakeLoop(
        api=api,
        artifact_root=config.artifact_root,
        shops=shops,
        state_store=state_store,
        pipeline=pipeline,
        fallback_pipeline=fallback_pipeline,
        final_fallback_pipeline=final_fallback_pipeline,
        instagram_publisher=ig_publisher,
        threads_publisher=threads_pub,
    )
    print(f"Telegram intake loop started. provider={provider_label} fallback={fallback_label} final=heuristic")
    return loop.run_forever()


if __name__ == "__main__":
    raise SystemExit(start_bot())
