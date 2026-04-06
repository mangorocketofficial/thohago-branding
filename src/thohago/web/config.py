from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from thohago.config import AppConfig


@dataclass(slots=True)
class WebConfig:
    database_path: Path
    base_url: str
    admin_username: str
    admin_password: str
    sync_api_token: str
    max_upload_photos: int
    max_upload_videos: int
    max_video_duration_sec: int
    stt_mode: str


def build_web_config(config: AppConfig) -> WebConfig:
    return WebConfig(
        database_path=config.web_database_path,
        base_url=config.web_base_url,
        admin_username=config.web_admin_username,
        admin_password=config.web_admin_password,
        sync_api_token=config.web_sync_api_token,
        max_upload_photos=config.web_max_upload_photos,
        max_upload_videos=config.web_max_upload_videos,
        max_video_duration_sec=config.web_max_video_duration_sec,
        stt_mode=config.web_stt_mode,
    )
