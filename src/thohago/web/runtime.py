from __future__ import annotations

from dataclasses import dataclass

from fastapi.templating import Jinja2Templates

from thohago.config import AppConfig
from thohago.models import ShopConfig
from thohago.web.event_bus import SessionEventBus
from thohago.web.config import WebConfig
from thohago.web.repositories import SessionRepository
from thohago.web.services.generation import ContentGenerationService
from thohago.web.services.interview import InterviewService
from thohago.web.services.sessions import SessionService
from thohago.web.services.sync import SyncService
from thohago.web.services.uploads import UploadService


@dataclass(slots=True)
class WebRuntime:
    app_config: AppConfig
    web_config: WebConfig
    shops: dict[str, ShopConfig]
    templates: Jinja2Templates
    session_repository: SessionRepository
    session_service: SessionService
    upload_service: UploadService
    interview_service: InterviewService
    generation_service: ContentGenerationService
    sync_service: SyncService
    event_bus: SessionEventBus
    transcriber: object
