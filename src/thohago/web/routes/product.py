from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from thohago.web.dependencies import get_runtime
from thohago.web.repositories import SessionMessageRecord, SessionRecord
from thohago.web.runtime import WebRuntime
from thohago.web.services.generation import ContentGenerationValidationError
from thohago.web.services.interview import InterviewTranscriptionError, InterviewValidationError
from thohago.web.services.question_quality import question_title_for_turn
from thohago.web.services.sync import SyncValidationError
from thohago.web.services.uploads import UploadValidationError


router = APIRouter()

AUTH_COOKIE = "thohago_mobile_auth"
ONBOARDING_COOKIE = "thohago_mobile_onboarded"
APP_SESSION_PREFIX = "mobile_v1_app_"
APP_SESSION_SHOP_ID = "demo_shop_2"


def _is_authenticated(request: Request) -> bool:
    return bool(request.cookies.get(AUTH_COOKIE))


def _is_onboarded(request: Request) -> bool:
    return request.cookies.get(ONBOARDING_COOKIE) == "1"


def _redirect_to_public() -> RedirectResponse:
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


def _redirect_to_onboarding() -> RedirectResponse:
    return RedirectResponse("/app/onboarding", status_code=status.HTTP_303_SEE_OTHER)


def _require_app_auth(request: Request) -> Response | None:
    if not _is_authenticated(request):
        return _redirect_to_public()
    return None


def _list_app_sessions(runtime: WebRuntime) -> list[dict[str, object]]:
    sessions = []
    for session in runtime.session_repository.list_sessions(limit=50):
        if not session.session_key.startswith(APP_SESSION_PREFIX):
            continue
        uploads = runtime.upload_service.list_active_uploads(session)
        stage_label = _translate_stage(session.stage)
        sessions.append(
            {
                "id": session.id,
                "stage": session.stage,
                "stage_label": stage_label,
                "created_at": session.created_at,
                "media_count": len(uploads),
                "photo_count": sum(item.kind == "photo" for item in uploads),
                "video_count": sum(item.kind == "video" for item in uploads),
                "sidebar_label": _sidebar_label(session),
                "sidebar_meta": f"{stage_label} · 업로드 {len(uploads)}개",
            }
        )
    return sessions


def _get_app_session_or_404(runtime: WebRuntime, session_id: str) -> SessionRecord:
    session = runtime.session_repository.get_by_id(session_id)
    if session is None or not session.session_key.startswith(APP_SESSION_PREFIX):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown app session")
    return session


def _app_session_path(session_id: str) -> str:
    return f"/app/session/{session_id}"


def _ensure_delivery_ready(session: SessionRecord) -> None:
    if session.stage not in {"approved", "complete"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Download is not ready for this session")


def _prefers_json_response(request: Request) -> bool:
    requested_with = request.headers.get("x-requested-with", "")
    accept = request.headers.get("accept", "")
    return requested_with.lower() == "xmlhttprequest" or "application/json" in accept.lower()


@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request) -> HTMLResponse:
    return request.app.state.runtime.templates.TemplateResponse(  # type: ignore[attr-defined]
        request,
        "landing.html",
        {
            "title": "또하고 모바일",
            "is_authenticated": _is_authenticated(request),
            "is_onboarded": _is_onboarded(request),
        },
    )


@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request) -> HTMLResponse:
    return request.app.state.runtime.templates.TemplateResponse(  # type: ignore[attr-defined]
        request,
        "pricing.html",
        {
            "title": "요금 안내",
            "is_authenticated": _is_authenticated(request),
            "is_onboarded": _is_onboarded(request),
        },
    )


@router.get("/app/sign-in/google")
def google_sign_in_stub() -> RedirectResponse:
    response = RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(AUTH_COOKIE, "demo-google-user", httponly=True, samesite="lax")
    response.set_cookie(ONBOARDING_COOKIE, "1", httponly=True, samesite="lax")
    return response


@router.get("/app/sign-out")
def sign_out() -> RedirectResponse:
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(AUTH_COOKIE)
    response.delete_cookie(ONBOARDING_COOKIE)
    return response


@router.get("/app/onboarding", response_class=HTMLResponse)
def onboarding_shell(request: Request) -> Response:
    if not _is_authenticated(request):
        return _redirect_to_public()
    return RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/app/onboarding/complete")
def complete_onboarding(request: Request) -> Response:
    if not _is_authenticated(request):
        return _redirect_to_public()

    response = RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(ONBOARDING_COOKIE, "1", httponly=True, samesite="lax")
    return response


@router.get("/app", response_class=HTMLResponse)
def workspace_shell(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    return runtime.templates.TemplateResponse(
        request,
        "app_workspace.html",
        {
            "title": "작업 공간",
            "user_name": "고객님",
            "sessions": _list_app_sessions(runtime),
            "current_session_id": None,
            "page_shell_class": "page-shell page-shell--app",
            "card_class": "card card--app-layout",
        },
    )


@router.post("/app/sessions/new")
def create_session_shell(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session_key = APP_SESSION_PREFIX + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    created = runtime.session_service.create_session(
        shop_id=APP_SESSION_SHOP_ID,
        session_key=session_key,
    )
    return RedirectResponse(f"/app/session/{created.session.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/app/session/{session_id}", response_class=HTMLResponse)
def session_shell(
    request: Request,
    session_id: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    return _render_app_session_page(request=request, runtime=runtime, session=session)


@router.post("/app/session/{session_id}/upload", response_class=HTMLResponse)
async def upload_media_from_app_session(
    request: Request,
    session_id: str,
    media: list[UploadFile] = File(...),
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        saved_records = await runtime.upload_service.save_uploads(session, media)
    except UploadValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        if _prefers_json_response(request):
            media_files = runtime.upload_service.list_active_uploads(refreshed)
            return JSONResponse(
                {
                    "error_message": str(exc),
                    "photo_count": sum(item.kind == "photo" for item in media_files),
                    "video_count": sum(item.kind == "video" for item in media_files),
                    "media_count": len(media_files),
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    refreshed = runtime.session_repository.get_by_id(session.id) or session
    if _prefers_json_response(request):
        media_files = runtime.upload_service.list_active_uploads(refreshed)
        return JSONResponse(
            {
                "session_id": refreshed.id,
                "uploaded": [
                    {
                        "id": record.id,
                        "kind": record.kind,
                        "filename": record.filename,
                        "file_size": record.file_size,
                    }
                    for record in saved_records
                ],
                "photo_count": sum(item.kind == "photo" for item in media_files),
                "video_count": sum(item.kind == "video" for item in media_files),
                "media_count": len(media_files),
            }
        )
    return _render_app_session_page(request=request, runtime=runtime, session=refreshed)


@router.post("/app/session/{session_id}/upload/delete", response_class=HTMLResponse)
def delete_media_from_app_session(
    request: Request,
    session_id: str,
    media_file_id: int = Form(...),
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        runtime.upload_service.delete_upload(session, media_file_id)
    except UploadValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    refreshed = runtime.session_repository.get_by_id(session.id) or session
    return _render_app_session_page(request=request, runtime=runtime, session=refreshed)


@router.post("/app/session/{session_id}/upload/complete")
def finalize_uploads_from_app_session(
    request: Request,
    session_id: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        updated = runtime.upload_service.finalize_uploads(session)
    except UploadValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(_app_session_path(updated.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/app/session/{session_id}/generate/blog")
def generate_blog_from_app_session(
    request: Request,
    session_id: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        updated = runtime.generation_service.generate_blog_preview(session)
    except ContentGenerationValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except SyncValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(_app_session_path(updated.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/app/session/{session_id}/interview/submit")
def submit_app_session_interview_answer(
    request: Request,
    session_id: str,
    answer_text: str = Form(...),
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        updated = runtime.interview_service.submit_text_answer(session, answer_text)
    except InterviewValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(_app_session_path(updated.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/app/session/{session_id}/interview/retry")
def retry_app_session_interview_answer(
    request: Request,
    session_id: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        updated = runtime.interview_service.retry_pending_answer(session)
    except InterviewValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(_app_session_path(updated.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/app/session/{session_id}/interview/confirm")
def confirm_app_session_interview_answer(
    request: Request,
    session_id: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        updated = runtime.interview_service.confirm_pending_answer(session)
    except InterviewValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(_app_session_path(updated.id), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/app/session/{session_id}/interview/record")
async def record_app_session_interview_answer(
    request: Request,
    session_id: str,
    audio: UploadFile = File(...),
    runtime: WebRuntime = Depends(get_runtime),
) -> JSONResponse:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    session = _get_app_session_or_404(runtime, session_id)
    try:
        updated = await runtime.interview_service.record_audio(
            session,
            audio_bytes=await audio.read(),
            filename=audio.filename,
            content_type=audio.content_type,
        )
    except InterviewValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InterviewTranscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return JSONResponse({"stage": updated.stage, "pending_answer": updated.pending_answer or ""}, status_code=202)


@router.get("/app/session/{session_id}/events")
async def app_session_events(
    request: Request,
    session_id: str,
    last_event_id: str | None = None,
    runtime: WebRuntime = Depends(get_runtime),
) -> StreamingResponse:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    session = _get_app_session_or_404(runtime, session_id)
    queue = runtime.event_bus.subscribe(session.id)
    replay_after_id = _parse_last_event_id(last_event_id) if last_event_id else None

    async def event_stream():
        replayed_max_id = replay_after_id or 0
        try:
            if replay_after_id is not None:
                replay_events = runtime.session_repository.list_session_events_after(session.id, replay_after_id)
                for replay_event in replay_events:
                    replayed_max_id = max(replayed_max_id, replay_event.id)
                    yield _format_sse(
                        replay_event.id,
                        replay_event.event_type,
                        json.loads(replay_event.data_json),
                    )
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    if event["id"] <= replayed_max_id:
                        continue
                    replayed_max_id = event["id"]
                    yield _format_sse(event["id"], event["type"], event["data"])
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            runtime.event_bus.unsubscribe(session.id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/app/session/{session_id}/files/{relative_path:path}")
def app_session_preview_file(
    request: Request,
    session_id: str,
    relative_path: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        target = runtime.sync_service.resolve_customer_file(session, relative_path)
    except SyncValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(target)


@router.get("/app/session/{session_id}/download/file/{relative_path:path}")
def app_session_download_file(
    request: Request,
    session_id: str,
    relative_path: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    _ensure_delivery_ready(session)
    try:
        target = runtime.sync_service.resolve_customer_file(session, relative_path)
    except SyncValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(target, filename=target.name)


@router.get("/app/session/{session_id}/download/bundle")
def app_session_download_bundle(
    request: Request,
    session_id: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    _ensure_delivery_ready(session)
    try:
        content = runtime.sync_service.build_customer_delivery_zip(session)
    except SyncValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{session.id}-delivery.zip"'},
    )


@router.post("/app/session/{session_id}/approval")
def app_session_preview_approval(
    request: Request,
    session_id: str,
    action: str = Form(...),
    runtime: WebRuntime = Depends(get_runtime),
) -> Response:
    auth_redirect = _require_app_auth(request)
    if auth_redirect is not None:
        return auth_redirect

    session = _get_app_session_or_404(runtime, session_id)
    try:
        if action == "approve":
            updated = runtime.sync_service.approve_preview(session)
        elif action == "revision":
            updated = runtime.sync_service.request_revision(session)
        else:
            raise SyncValidationError(f"Unknown approval action: {action}")
    except SyncValidationError as exc:
        refreshed = runtime.session_repository.get_by_id(session.id) or session
        return _render_app_session_page(
            request=request,
            runtime=runtime,
            session=refreshed,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(_app_session_path(updated.id), status_code=status.HTTP_303_SEE_OTHER)


def _render_app_session_page(
    *,
    request: Request,
    runtime: WebRuntime,
    session: SessionRecord,
    error_message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    media_files = runtime.upload_service.list_active_uploads(session)
    view_mode = _session_view_mode(session.stage)
    stage_label = _translate_stage(session.stage)
    conversation_messages = _build_conversation_messages(runtime, session)
    interview_view = None
    question_title = None
    turn_progress = None
    preview_context = None
    title = "새 작업"

    if view_mode == "interview":
        interview_view = runtime.interview_service.build_view(session)
        question_title = question_title_for_turn(interview_view.turn_index)
        turn_progress = f"{interview_view.turn_index} / 3"
        title = question_title
    elif view_mode == "waiting":
        title = "제작 대기"
    elif view_mode in {"preview", "complete"}:
        title = "미리보기 확인" if view_mode == "preview" else "결과 받기"
        try:
            preview_context = runtime.sync_service.load_preview_context(session)
        except SyncValidationError as exc:
            if error_message is None:
                error_message = str(exc)

    response = runtime.templates.TemplateResponse(
        request,
        "app_session.html",
        {
            "title": title,
            "user_name": "고객님",
            "sessions": _list_app_sessions(runtime),
            "current_session_id": session.id,
            "page_shell_class": "page-shell page-shell--app",
            "card_class": "card card--app-layout",
            "session": session,
            "session_id": session.id,
            "stage_label": stage_label,
            "view_mode": view_mode,
            "media_files": media_files,
            "limits": {
                "photos": runtime.web_config.max_upload_photos,
                "videos": runtime.web_config.max_upload_videos,
                "video_seconds": runtime.web_config.max_video_duration_sec,
            },
            "error_message": error_message,
            "photo_count": sum(item.kind == "photo" for item in media_files),
            "video_count": sum(item.kind == "video" for item in media_files),
            "conversation_messages": conversation_messages,
            "interview_view": interview_view,
            "question_title": question_title,
            "turn_progress": turn_progress,
            "upload_complete_url": f"/app/session/{session.id}/upload/complete",
            "interview_submit_url": f"/app/session/{session.id}/interview/submit",
            "interview_retry_url": f"/app/session/{session.id}/interview/retry",
            "interview_confirm_url": f"/app/session/{session.id}/interview/confirm",
            "interview_record_url": f"/app/session/{session.id}/interview/record",
            "events_url": f"/app/session/{session.id}/events",
            "preview_context": preview_context,
            "preview_file_base_url": f"/app/session/{session.id}/files",
            "approval_action_url": f"/app/session/{session.id}/approval",
            "generate_blog_url": f"/app/session/{session.id}/generate/blog",
            "download_file_base_url": f"/app/session/{session.id}/download/file",
            "download_bundle_url": f"/app/session/{session.id}/download/bundle",
        },
    )
    response.status_code = status_code
    return response


def _session_view_mode(stage: str) -> str:
    if stage == "collecting_media":
        return "upload"
    if stage.startswith("awaiting_turn") or stage.startswith("confirming_turn"):
        return "interview"
    if stage == "awaiting_production":
        return "waiting"
    if stage in {"awaiting_approval", "revision_requested"}:
        return "preview"
    if stage in {"approved", "complete"}:
        return "complete"
    return "status"


def _build_conversation_messages(runtime: WebRuntime, session: SessionRecord) -> list[dict[str, str | bool]]:
    messages = runtime.session_repository.list_session_messages(session.id)
    rendered: list[dict[str, str | bool]] = []
    for message in messages:
        bubble = _render_conversation_message(message)
        if bubble is not None:
            if rendered:
                last = rendered[-1]
                if (
                    last["role"] == bubble["role"]
                    and last["label"] == bubble["label"]
                    and last["text"] == bubble["text"]
                    and last["is_status"] == bubble["is_status"]
                ):
                    continue
            rendered.append(bubble)
    return rendered


def _render_conversation_message(message: SessionMessageRecord) -> dict[str, str | bool] | None:
    if message.message_type not in {"text", "status"}:
        return None
    text = (message.text or "").strip()
    if not text:
        return None
    role = "assistant" if message.sender == "system" else "user"
    return {
        "role": role,
        "label": _conversation_label(message),
        "text": text,
        "is_status": message.message_type == "status",
    }


def _conversation_label(message: SessionMessageRecord) -> str:
    if message.message_type == "status":
        return "안내" if message.sender == "system" else "내 선택"
    if message.turn_index:
        if message.sender == "system":
            return question_title_for_turn(message.turn_index)
        return f"{question_title_for_turn(message.turn_index)} 답변"
    return "안내" if message.sender == "system" else "내 답변"


def _translate_stage(stage: str) -> str:
    return {
        "collecting_media": "업로드 중",
        "awaiting_turn1_answer": "인터뷰 대기",
        "awaiting_turn2_answer": "인터뷰 진행 중",
        "awaiting_turn3_answer": "인터뷰 진행 중",
        "confirming_turn1": "답변 확인 중",
        "confirming_turn2": "답변 확인 중",
        "confirming_turn3": "답변 확인 중",
        "awaiting_production": "제작 대기",
        "awaiting_approval": "미리보기 확인",
        "revision_requested": "수정 요청",
        "approved": "승인 완료",
        "complete": "완료",
    }.get(stage, stage)


def _sidebar_label(session: SessionRecord) -> str:
    created = session.created_at
    compact_time = created[5:16].replace("T", " ") if "T" in created else created[:16]
    return f"세션 {compact_time}"


def _format_sse(event_id: int, event_type: str, data: dict) -> str:
    return f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _parse_last_event_id(value: str | None) -> int:
    if not value:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        return 0
