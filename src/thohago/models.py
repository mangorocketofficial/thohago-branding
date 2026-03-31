from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SampleSession:
    key: str
    base_dir: Path
    image_dir: Path
    video_dir: Path
    interview_dir: Path
    turn_transcript_files: list[Path]


@dataclass(slots=True)
class PublishConfig:
    provider: str
    targets: list[str]


@dataclass(slots=True)
class ShopConfig:
    shop_id: str
    display_name: str
    invite_tokens: list[str]
    telegram_chat_ids: list[str]
    publish: PublishConfig
    media_hints: list[str] = field(default_factory=list)
    profile: dict[str, Any] = field(default_factory=dict)
    sample_sessions: dict[str, SampleSession] = field(default_factory=dict)


@dataclass(slots=True)
class MediaAsset:
    media_id: str
    kind: str
    source_path: Path
    relative_source_path: str
    experience_order: int
    preflight_analysis: dict[str, Any]
    selected_for_prompt: bool
    reels_eligible: bool = False
    duration_sec: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_path"] = str(self.source_path)
        return payload


@dataclass(slots=True)
class TranscriptArtifact:
    turn_index: int
    source_path: Path
    transcript_text: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_path"] = str(self.source_path)
        return payload


@dataclass(slots=True)
class PlannerOutput:
    turn_index: int
    main_angle: str
    covered_elements: list[str]
    missing_elements: list[str]
    question_strategy: str
    next_question: str
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TranscriptProviderResult:
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class SessionArtifacts:
    shop: ShopConfig
    session_key: str
    session_id: str
    artifact_dir: Path
    chat_log_path: Path
    raw_dir: Path
    prompts_dir: Path
    transcripts_dir: Path
    generated_dir: Path
    published_dir: Path


@dataclass(slots=True)
class SessionRunResult:
    artifacts: SessionArtifacts
    media_preflight_path: Path
    turn2_planner_path: Path
    turn3_planner_path: Path
    content_bundle_path: Path
    blog_article_path: Path
    publish_result_path: Path
