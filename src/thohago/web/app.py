from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from thohago.config import AppConfig, load_config
from thohago.models import ShopConfig
from thohago.web.event_bus import SessionEventBus
from thohago.registry import load_shop_registry
from thohago.web.config import build_web_config
from thohago.web.database import initialize_database
from thohago.web.repositories import SessionRepository
from thohago.web.routes import admin, customer, events, product, pwa, sync_api
from thohago.web.runtime import WebRuntime
from thohago.web.services.generation import ContentGenerationService
from thohago.web.services.interview import InterviewService
from thohago.web.services.pipeline_runtime import resolve_engine
from thohago.web.services.sessions import SessionService
from thohago.web.services.sync import SyncService
from thohago.web.services.transcription_runtime import resolve_transcriber
from thohago.web.services.uploads import UploadService


def create_app(
    *,
    config: AppConfig | None = None,
    shops: dict[str, ShopConfig] | None = None,
) -> FastAPI:
    app_config = config or load_config()
    web_config = build_web_config(app_config)
    initialize_database(web_config.database_path)
    resolve_engine(app_config)

    loaded_shops = shops or load_shop_registry(app_config.shops_file)
    template_dir = Path(__file__).resolve().parent / "templates"
    static_dir = Path(__file__).resolve().parent / "static"
    templates = Jinja2Templates(directory=str(template_dir))
    session_repository = SessionRepository(web_config.database_path)
    session_service = SessionService(
        config=app_config,
        web_config=web_config,
        shops=loaded_shops,
        repository=session_repository,
    )
    upload_service = UploadService(
        config=app_config,
        web_config=web_config,
        repository=session_repository,
        session_service=session_service,
    )
    event_bus = SessionEventBus(session_repository)
    sync_service = SyncService(
        config=app_config,
        repository=session_repository,
        session_service=session_service,
        event_bus=event_bus,
    )
    transcriber = resolve_transcriber(app_config)
    interview_service = InterviewService(
        config=app_config,
        repository=session_repository,
        session_service=session_service,
        event_bus=event_bus,
        transcriber=transcriber,
    )
    generation_service = ContentGenerationService(
        config=app_config,
        repository=session_repository,
        session_service=session_service,
        sync_service=sync_service,
    )

    app = FastAPI(title="Thohago Web")
    app.state.runtime = WebRuntime(
        app_config=app_config,
        web_config=web_config,
        shops=loaded_shops,
        templates=templates,
        session_repository=session_repository,
        session_service=session_service,
        upload_service=upload_service,
        interview_service=interview_service,
        generation_service=generation_service,
        sync_service=sync_service,
        event_bus=event_bus,
        transcriber=transcriber,
    )

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(product.router)
    app.include_router(customer.router)
    app.include_router(admin.router)
    app.include_router(sync_api.router)
    app.include_router(events.router)
    app.include_router(pwa.router)

    @app.get("/healthz")
    def healthcheck() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app
