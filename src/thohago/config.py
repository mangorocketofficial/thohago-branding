from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    repo_root: Path
    shops_file: Path
    artifact_root: Path
    web_database_path: Path
    web_base_url: str
    web_admin_username: str
    web_admin_password: str
    web_sync_api_token: str
    web_max_upload_photos: int
    web_max_upload_videos: int
    web_max_video_duration_sec: int
    web_stt_mode: str
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
    # Instagram Graph API
    instagram_access_token: str | None
    instagram_business_account_id: str | None
    facebook_page_id: str | None
    instagram_graph_version: str
    # Threads API
    threads_access_token: str | None
    threads_user_id: str | None


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
    web_database_path = Path(os.environ.get("THOHAGO_WEB_DB_PATH", "runs/_web_runtime/web.sqlite3"))
    web_base_url = os.environ.get("THOHAGO_WEB_BASE_URL", "http://localhost:8000").rstrip("/")
    return AppConfig(
        repo_root=root,
        shops_file=(root / shops_file).resolve(),
        artifact_root=(root / artifact_root).resolve(),
        web_database_path=(root / web_database_path).resolve(),
        web_base_url=web_base_url,
        web_admin_username=os.environ.get("THOHAGO_ADMIN_USERNAME", "admin"),
        web_admin_password=os.environ.get("THOHAGO_ADMIN_PASSWORD", "thohago-dev-password"),
        web_sync_api_token=os.environ.get("THOHAGO_SYNC_API_TOKEN", "thohago-sync-dev-token"),
        web_max_upload_photos=int(os.environ.get("THOHAGO_WEB_MAX_UPLOAD_PHOTOS", "5")),
        web_max_upload_videos=int(os.environ.get("THOHAGO_WEB_MAX_UPLOAD_VIDEOS", "1")),
        web_max_video_duration_sec=int(os.environ.get("THOHAGO_WEB_MAX_VIDEO_DURATION_SEC", "60")),
        web_stt_mode=os.environ.get("THOHAGO_WEB_STT_MODE", "stub"),
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
        # Instagram Graph API
        instagram_access_token=os.environ.get("GRAPH_META_ACCESS_TOKEN"),
        instagram_business_account_id=os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID"),
        facebook_page_id=os.environ.get("FACEBOOK_PAGE_ID"),
        instagram_graph_version=os.environ.get("INSTAGRAM_GRAPH_VERSION", "v23.0"),
        # Threads API
        threads_access_token=os.environ.get("THREADS_ACCESS_TOKEN"),
        threads_user_id=os.environ.get("THREADS_USER_ID"),
    )
