from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from thohago.artifacts import create_session_artifacts, write_json, write_text
from thohago.anthropic_live import AnthropicApiClient, AnthropicMultimodalInterviewEngine
from thohago.config import load_config
from thohago.groq_live import GroqApiClient, GroqMultimodalInterviewEngine, GroqTranscriptionProvider
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelegramBotApi:
    def __init__(self, token: str) -> None:
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base_url = f"https://api.telegram.org/file/bot{token}"

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        return self._request("getUpdates", payload).get("result", [])

    def send_message(self, chat_id: str, text: str) -> None:
        self._request("sendMessage", {"chat_id": chat_id, "text": text})

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
    ) -> None:
        self.api = api
        self.artifact_root = artifact_root
        self.shops = shops
        self.state_store = state_store
        self.pipeline = pipeline or Phase1ReplayPipeline()
        self.fallback_pipeline = fallback_pipeline or Phase1ReplayPipeline()
        self.final_fallback_pipeline = final_fallback_pipeline or Phase1ReplayPipeline()

    def run_forever(self) -> int:
        offset: int | None = None
        while True:
            updates = self.api.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update["update_id"] + 1
                self.handle_update(update)
            if not updates:
                time.sleep(1)

    def handle_update(self, update: dict[str, Any]) -> None:
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
            state = self._create_new_session(shop, chat_id)
            self.api.send_message(chat_id, f"새 세션을 시작했습니다.\n세션 ID: {state.session_id}\n이제 사진/영상을 보내고 /interview 를 입력해주세요.")
            return
        if text == "/reset":
            self.state_store.clear(chat_id)
            self.api.send_message(chat_id, "현재 세션을 초기화했습니다. /begin 으로 다시 시작해주세요.")
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

    def _handle_start(self, chat_id: str, text: str) -> None:
        parts = text.split(maxsplit=1)
        invite_token = parts[1].strip() if len(parts) > 1 else ""
        bound_shop = self._resolve_shop_for_chat(chat_id)

        if bound_shop and not invite_token:
            self.api.send_message(chat_id, HELP_TEXT)
            return

        if bound_shop and invite_token:
            self.api.send_message(chat_id, f"이미 `{bound_shop.shop_id}` 에 연결된 채팅입니다. 바로 /begin 으로 시작해주세요.")
            return

        if not invite_token:
            self.api.send_message(chat_id, "이 채팅은 아직 연결되지 않았습니다. 고객 전용 초대 링크를 눌러서 시작해주세요.")
            return

        try:
            shop = resolve_shop_by_invite_token(self.shops, invite_token)
        except KeyError:
            self.api.send_message(chat_id, "유효하지 않은 초대 링크입니다. 최신 고객 전용 링크를 다시 받아서 시도해주세요.")
            return

        self.state_store.bind_chat_to_shop(chat_id, shop.shop_id)
        self.api.send_message(
            chat_id,
            "\n".join(
                [
                    f"{shop.display_name} 전용 채팅으로 연결되었습니다.",
                    "이제 /begin 으로 새 세션을 시작해주세요.",
                    HELP_TEXT,
                ]
            ),
        )

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
        self.api.send_message(chat_id, f"사진 저장 완료 ({len(state.photo_paths)}장). 더 보내거나 /interview 를 입력해주세요.")

    def _handle_video_message(self, shop: ShopConfig, chat_id: str, message: dict[str, Any]) -> None:
        state = self._load_or_create_collecting_session(shop, chat_id)
        if state.stage != "collecting_media":
            self.api.send_message(chat_id, "이미 인터뷰가 시작됐습니다. 새 세션은 /reset 후 /begin 으로 시작해주세요.")
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
        self.api.send_message(chat_id, f"영상 저장 완료 ({len(state.video_paths)}개). 더 보내거나 /interview 를 입력해주세요.")

    def _handle_audio_message(self, shop: ShopConfig, chat_id: str, message: dict[str, Any]) -> None:
        state = self.state_store.load(chat_id)
        if not state or not state.stage.startswith("awaiting_turn"):
            self.api.send_message(chat_id, "현재는 인터뷰 답변을 받을 단계가 아닙니다. /status 로 상태를 확인해주세요.")
            return

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
            self.api.send_message(chat_id, f"음성 전사 완료: {result.text}")
            self._handle_text_answer(shop, chat_id, result.text)
            return

        self.api.send_message(
            chat_id,
            "음성 파일은 저장했습니다. 현재 live STT provider가 설정되지 않아 자동 전사는 못 합니다. 같은 답변을 텍스트로 한 번만 보내주세요.",
        )

    def _handle_text_answer(self, shop: ShopConfig, chat_id: str, text: str) -> None:
        state = self.state_store.load(chat_id)
        if not state or not state.stage.startswith("awaiting_turn"):
            self.api.send_message(chat_id, "현재 인터뷰 단계가 아닙니다. /begin 후 사진을 보내고 /interview 로 시작해주세요.")
            return

        artifacts = self._artifacts_from_state(shop, state)
        turn_index = self._stage_to_turn_index(state.stage)
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

        transcript_artifacts = [self._transcript_from_dict(item) for item in state.transcripts]
        content_bundle_path, blog_article_path, publish_result_path = self.pipeline.finalize_session(
            artifacts=artifacts,
            shop=shop,
            photo_assets=[self._media_from_dict(item) for item in state.photo_assets],
            video_assets=[self._media_from_dict(item) for item in state.video_assets],
            preflight=state.preflight or {},
            transcript_artifacts=transcript_artifacts,
            turn2_planner=self._planner_from_dict(state.turn2_planner),
            turn3_planner=self._planner_from_dict(state.turn3_planner),
        )
        state.stage = "completed"
        self.state_store.save(state)
        publish_result = json.loads(publish_result_path.read_text(encoding="utf-8"))
        completion_text = "\n".join(
            [
                "인터뷰와 콘텐츠 생성이 완료됐습니다.",
                f"- content_bundle: {content_bundle_path.name}",
                f"- blog_article: {blog_article_path.name}",
                f"- publish_status: {publish_result['status']}",
                f"- publish_url: {publish_result.get('published_url')}",
            ]
        )
        self.api.send_message(chat_id, completion_text)

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

        artifacts = self._artifacts_from_state(shop, state)
        preflight, photo_assets, video_assets, _ = self._prepare_media_with_fallback(
            artifacts=artifacts,
            shop=shop,
            photos=[Path(path) for path in state.photo_paths],
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
    loop = TelegramIntakeLoop(
        api=api,
        artifact_root=config.artifact_root,
        shops=shops,
        state_store=state_store,
        pipeline=pipeline,
        fallback_pipeline=fallback_pipeline,
        final_fallback_pipeline=final_fallback_pipeline,
    )
    print(f"Telegram intake loop started. provider={provider_label} fallback={fallback_label} final=heuristic")
    return loop.run_forever()


if __name__ == "__main__":
    raise SystemExit(start_bot())
