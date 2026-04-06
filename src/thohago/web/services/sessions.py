from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

from thohago.artifacts import create_session_artifacts, write_json
from thohago.config import AppConfig
from thohago.models import SessionArtifacts, ShopConfig
from thohago.web.config import WebConfig
from thohago.web.repositories import SessionRecord, SessionRepository


@dataclass(slots=True)
class CreatedSession:
    session: SessionRecord
    customer_url: str
    artifacts: SessionArtifacts
    metadata_path: Path


class SessionService:
    def __init__(
        self,
        *,
        config: AppConfig,
        web_config: WebConfig,
        shops: dict[str, ShopConfig],
        repository: SessionRepository,
    ) -> None:
        self.config = config
        self.web_config = web_config
        self.shops = shops
        self.repository = repository

    def create_session(self, *, shop_id: str, session_key: str | None = None) -> CreatedSession:
        shop = self.shops.get(shop_id)
        if shop is None:
            raise KeyError(f"Unknown shop_id: {shop_id}")

        resolved_session_key = session_key or datetime.now(UTC).strftime("live_%Y%m%dT%H%M%S")
        artifacts = create_session_artifacts(self.config.artifact_root, shop, resolved_session_key)
        customer_token = secrets.token_urlsafe(24)
        relative_artifact_dir = artifacts.artifact_dir.relative_to(self.config.artifact_root).as_posix()

        session = self.repository.create_session(
            session_id=artifacts.session_id,
            shop_id=shop.shop_id,
            session_key=resolved_session_key,
            customer_token=customer_token,
            stage="collecting_media",
            artifact_dir=relative_artifact_dir,
        )

        metadata_path = self.write_session_metadata(session)

        return CreatedSession(
            session=session,
            customer_url=self.build_customer_url(session.customer_token),
            artifacts=artifacts,
            metadata_path=metadata_path,
        )

    def get_shop(self, session: SessionRecord) -> ShopConfig:
        shop = self.shops.get(session.shop_id)
        if shop is None:
            raise KeyError(f"Unknown shop_id for session: {session.shop_id}")
        return shop

    def artifacts_for_session(self, session: SessionRecord) -> SessionArtifacts:
        shop = self.get_shop(session)
        artifact_dir = self.config.artifact_root / session.artifact_dir
        return SessionArtifacts(
            shop=shop,
            session_key=session.session_key,
            session_id=session.id,
            artifact_dir=artifact_dir,
            chat_log_path=artifact_dir / "chat_log.jsonl",
            raw_dir=artifact_dir / "raw",
            prompts_dir=artifact_dir / "planners",
            transcripts_dir=artifact_dir / "transcripts",
            generated_dir=artifact_dir / "generated",
            published_dir=artifact_dir / "published",
        )

    def write_session_metadata(self, session: SessionRecord) -> Path:
        artifacts = self.artifacts_for_session(session)
        shop = self.get_shop(session)
        metadata_path = artifacts.artifact_dir / "session_metadata.json"
        metadata = {
            "shop_id": shop.shop_id,
            "display_name": shop.display_name,
            "session_id": session.id,
            "session_key": session.session_key,
            "customer_token": session.customer_token,
            "customer_url": self.build_customer_url(session.customer_token),
            "stage": session.stage,
            "artifact_dir": str(artifacts.artifact_dir),
            "chat_log_path": str(artifacts.chat_log_path),
            "created_at": session.created_at,
        }
        if session.production_completed_at:
            metadata["production_completed_at"] = session.production_completed_at
        if session.approved_at:
            metadata["approved_at"] = session.approved_at
        if session.turn1_question:
            metadata["turn1_question"] = session.turn1_question
            metadata["turn1_question_path"] = str(artifacts.prompts_dir / "turn1_question.txt")
        if session.turn2_planner_json:
            metadata["turn2_planner"] = json.loads(session.turn2_planner_json)
            metadata["turn2_planner_path"] = str(artifacts.prompts_dir / "turn2_planner.json")
            metadata["turn2_question_path"] = str(artifacts.prompts_dir / "turn2_question.txt")
        if session.turn3_planner_json:
            metadata["turn3_planner"] = json.loads(session.turn3_planner_json)
            metadata["turn3_planner_path"] = str(artifacts.prompts_dir / "turn3_planner.json")
            metadata["turn3_question_path"] = str(artifacts.prompts_dir / "turn3_question.txt")
        if session.preflight_json:
            metadata["preflight"] = json.loads(session.preflight_json)
            metadata["preflight_path"] = str(artifacts.generated_dir / "media_preflight.json")
        intake_bundle_path = artifacts.generated_dir / "intake_bundle.json"
        if intake_bundle_path.exists():
            metadata["intake_bundle_path"] = str(intake_bundle_path)
        preview_manifest_path = artifacts.published_dir / "manifest.json"
        if preview_manifest_path.exists():
            metadata["preview_manifest_path"] = str(preview_manifest_path)
        write_json(metadata_path, metadata)
        return metadata_path

    def build_customer_url(self, customer_token: str) -> str:
        return f"{self.web_config.base_url}/s/{customer_token}"

    def customer_path_for_stage(self, customer_token: str, stage: str) -> str:
        if stage == "collecting_media":
            return f"/s/{customer_token}/upload"
        if stage.startswith("awaiting_turn") or stage.startswith("confirming_turn"):
            return f"/s/{customer_token}/interview"
        if stage == "awaiting_production":
            return f"/s/{customer_token}/waiting"
        if stage in {"awaiting_approval", "revision_requested"}:
            return f"/s/{customer_token}/preview"
        return f"/s/{customer_token}/complete"
