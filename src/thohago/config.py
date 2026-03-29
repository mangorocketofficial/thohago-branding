from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    repo_root: Path
    shops_file: Path
    artifact_root: Path
    default_interview_engine: str
    default_stt_provider: str
    default_publisher: str
    telegram_bot_token: str | None
    groq_api_key: str | None
    groq_vision_model: str
    groq_stt_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    openai_api_key: str | None
    openai_model: str


def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_config(repo_root: Path | None = None) -> AppConfig:
    root = repo_root or Path(__file__).resolve().parents[2]
    load_dotenv_file(root / ".env")
    shops_file = Path(os.environ.get("THOHAGO_SHOPS_FILE", "config/shops.example.json"))
    artifact_root = Path(os.environ.get("THOHAGO_ARTIFACT_ROOT", "runs"))
    return AppConfig(
        repo_root=root,
        shops_file=(root / shops_file).resolve(),
        artifact_root=(root / artifact_root).resolve(),
        default_interview_engine=os.environ.get("THOHAGO_DEFAULT_INTERVIEW_ENGINE", "heuristic"),
        default_stt_provider=os.environ.get("THOHAGO_DEFAULT_STT_PROVIDER", "sidecar"),
        default_publisher=os.environ.get("THOHAGO_DEFAULT_PUBLISHER", "mock_naver"),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        groq_vision_model=os.environ.get(
            "THOHAGO_GROQ_VISION_MODEL",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ),
        groq_stt_model=os.environ.get("THOHAGO_GROQ_STT_MODEL", "whisper-large-v3"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY"),
        anthropic_model=os.environ.get("THOHAGO_ANTHROPIC_MODEL", "claude-opus-4-5-20251101"),
        openai_api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("GPT_API_KEY"),
        openai_model=os.environ.get("THOHAGO_OPENAI_MODEL", "gpt-4o-mini"),
    )
