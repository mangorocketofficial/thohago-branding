from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from thohago.web.dependencies import get_runtime, get_session_or_404
from thohago.web.repositories import SessionMessageRecord, SessionRecord
from thohago.web.runtime import WebRuntime
from thohago.web.services.interview import InterviewTranscriptionError, InterviewValidationError
from thohago.web.services.question_quality import question_title_for_turn
from thohago.web.services.sync import SyncValidationError
from thohago.web.services.uploads import UploadValidationError


router = APIRouter()


@router.get("/s/{customer_token}")
def customer_landing(
    customer_token: str,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> RedirectResponse:
    return RedirectResponse(
        runtime.session_service.customer_path_for_stage(customer_token, session.stage),
        status_code=307,
    )


@router.get("/s/{customer_token}/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> Response:
    if session.stage != "collecting_media":
        return RedirectResponse(
            runtime.session_service.customer_path_for_stage(customer_token=session.customer_token, stage=session.stage),
            status_code=307,
        )
    return _render_upload_page(request=request, runtime=runtime, session=session)


@router.post("/s/{customer_token}/upload", response_class=HTMLResponse)
async def upload_media(
    request: Request,
    media: list[UploadFile] = File(...),
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> HTMLResponse:
    try:
        await runtime.upload_service.save_uploads(session, media)
    except UploadValidationError as exc:
        return _render_upload_page(
            request=request,
            runtime=runtime,
            session=session,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    refreshed = runtime.session_repository.get_by_id(session.id)
    if refreshed is None:
        refreshed = session
    return _render_upload_page(request=request, runtime=runtime, session=refreshed)


@router.post("/s/{customer_token}/upload/delete", response_class=HTMLResponse)
def delete_upload(
    request: Request,
    media_file_id: int = Form(...),
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> HTMLResponse:
    try:
        runtime.upload_service.delete_upload(session, media_file_id)
    except UploadValidationError as exc:
        return _render_upload_page(
            request=request,
            runtime=runtime,
            session=session,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    refreshed = runtime.session_repository.get_by_id(session.id)
    if refreshed is None:
        refreshed = session
    return _render_upload_page(request=request, runtime=runtime, session=refreshed)


@router.post("/s/{customer_token}/upload/done")
def finalize_uploads(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> Response:
    try:
        updated_session = runtime.upload_service.finalize_uploads(session)
    except UploadValidationError as exc:
        return _render_upload_page(
            request=request,
            runtime=runtime,
            session=session,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        runtime.session_service.customer_path_for_stage(updated_session.customer_token, updated_session.stage),
        status_code=303,
    )


@router.get("/s/{customer_token}/interview", response_class=HTMLResponse)
def interview_page(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> Response:
    if session.stage == "collecting_media":
        return RedirectResponse(
            runtime.session_service.customer_path_for_stage(customer_token=session.customer_token, stage=session.stage),
            status_code=307,
        )
    if session.stage.startswith("awaiting_turn") or session.stage.startswith("confirming_turn"):
        interview_view = runtime.interview_service.build_view(session)
        question_title = question_title_for_turn(interview_view.turn_index)
        return runtime.templates.TemplateResponse(
            request,
            "interview.html",
            {
                "session": session,
                "shop": runtime.shops.get(session.shop_id),
                "title": question_title,
                "turn_index": interview_view.turn_index,
                "question_title": question_title,
                "is_confirming": interview_view.is_confirming,
                "pending_answer": interview_view.pending_answer,
                "error_message": None,
                "events_url": f"/s/{session.customer_token}/events",
                "record_url": f"/s/{session.customer_token}/interview/record",
                "submit_url": f"/s/{session.customer_token}/interview/submit",
                "conversation_messages": _build_conversation_messages(runtime, session),
            },
        )
    return RedirectResponse(
        runtime.session_service.customer_path_for_stage(customer_token=session.customer_token, stage=session.stage),
        status_code=307,
    )


@router.post("/s/{customer_token}/interview/submit")
def submit_interview_answer(
    request: Request,
    answer_text: str = Form(...),
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> Response:
    try:
        updated = runtime.interview_service.submit_text_answer(session, answer_text)
    except InterviewValidationError as exc:
        return _render_interview_page(
            request=request,
            runtime=runtime,
            session=session,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        runtime.session_service.customer_path_for_stage(updated.customer_token, updated.stage),
        status_code=303,
    )


@router.post("/s/{customer_token}/interview/record")
async def record_interview_answer(
    audio: UploadFile = File(...),
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> JSONResponse:
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


@router.post("/s/{customer_token}/interview/retry")
def retry_interview_answer(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> Response:
    try:
        updated = runtime.interview_service.retry_pending_answer(session)
    except InterviewValidationError as exc:
        return _render_interview_page(
            request=request,
            runtime=runtime,
            session=session,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        runtime.session_service.customer_path_for_stage(updated.customer_token, updated.stage),
        status_code=303,
    )


@router.post("/s/{customer_token}/interview/confirm")
def confirm_interview_answer(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> Response:
    try:
        updated = runtime.interview_service.confirm_pending_answer(session)
    except InterviewValidationError as exc:
        return _render_interview_page(
            request=request,
            runtime=runtime,
            session=session,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        runtime.session_service.customer_path_for_stage(updated.customer_token, updated.stage),
        status_code=303,
    )


@router.get("/s/{customer_token}/waiting", response_class=HTMLResponse)
def waiting_placeholder(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> HTMLResponse:
    return runtime.templates.TemplateResponse(
        request,
        "waiting.html",
        {
            "session": session,
            "title": "제작 대기",
            "shop": runtime.shops.get(session.shop_id),
            "events_url": f"/s/{session.customer_token}/events",
            "conversation_messages": _build_conversation_messages(runtime, session),
        },
    )


@router.get("/s/{customer_token}/preview", response_class=HTMLResponse)
def preview_page(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> HTMLResponse:
    try:
        preview_context = runtime.sync_service.load_preview_context(session)
    except SyncValidationError as exc:
        return runtime.templates.TemplateResponse(
            request,
            "preview.html",
            {
                "session": session,
                "shop": runtime.shops.get(session.shop_id),
                "title": "미리보기 확인",
                "preview_context": None,
                "error_message": str(exc),
                "conversation_messages": _build_conversation_messages(runtime, session),
            },
        )
    return runtime.templates.TemplateResponse(
        request,
        "preview.html",
        {
            "session": session,
            "shop": runtime.shops.get(session.shop_id),
            "title": "미리보기 확인",
            "preview_context": preview_context,
            "error_message": None,
            "conversation_messages": _build_conversation_messages(runtime, session),
        },
    )


@router.get("/s/{customer_token}/files/{relative_path:path}")
def preview_file(
    customer_token: str,
    relative_path: str,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> FileResponse:
    try:
        target = runtime.sync_service.resolve_customer_file(session, relative_path)
    except SyncValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(target)


@router.post("/s/{customer_token}/approval")
def preview_approval(
    action: str = Form(...),
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> Response:
    try:
        if action == "approve":
            updated = runtime.sync_service.approve_preview(session)
        elif action == "revision":
            updated = runtime.sync_service.request_revision(session)
        else:
            raise SyncValidationError(f"Unknown approval action: {action}")
    except SyncValidationError as exc:
        return RedirectResponse(
            f"/s/{session.customer_token}/preview?error={str(exc)}",
            status_code=303,
        )
    return RedirectResponse(
        runtime.session_service.customer_path_for_stage(updated.customer_token, updated.stage),
        status_code=303,
    )


@router.get("/s/{customer_token}/complete", response_class=HTMLResponse)
def complete_page(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> HTMLResponse:
    return runtime.templates.TemplateResponse(
        request,
        "complete.html",
        {
            "session": session,
            "title": "승인 완료",
            "shop": runtime.shops.get(session.shop_id),
            "conversation_messages": _build_conversation_messages(runtime, session),
        },
    )


def _render_upload_page(
    *,
    request: Request,
    runtime: WebRuntime,
    session: SessionRecord,
    error_message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    response = runtime.templates.TemplateResponse(
        request,
        "upload.html",
        {
            "session": session,
            "shop": runtime.shops.get(session.shop_id),
            "title": "사진+영상 업로드 하기",
            "media_files": runtime.upload_service.list_active_uploads(session),
            "error_message": error_message,
            "limits": {
                "photos": runtime.web_config.max_upload_photos,
                "videos": runtime.web_config.max_upload_videos,
            },
        },
    )
    response.status_code = status_code
    return response


def _render_interview_page(
    *,
    request: Request,
    runtime: WebRuntime,
    session: SessionRecord,
    error_message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    interview_view = runtime.interview_service.build_view(session)
    question_title = question_title_for_turn(interview_view.turn_index)
    response = runtime.templates.TemplateResponse(
        request,
        "interview.html",
        {
            "session": session,
            "shop": runtime.shops.get(session.shop_id),
            "title": question_title,
            "turn_index": interview_view.turn_index,
            "question_title": question_title,
            "is_confirming": interview_view.is_confirming,
            "pending_answer": interview_view.pending_answer,
            "error_message": error_message,
            "events_url": f"/s/{session.customer_token}/events",
            "record_url": f"/s/{session.customer_token}/interview/record",
            "submit_url": f"/s/{session.customer_token}/interview/submit",
            "conversation_messages": _build_conversation_messages(runtime, session),
        },
    )
    response.status_code = status_code
    return response


def _build_conversation_messages(runtime: WebRuntime, session: SessionRecord) -> list[dict[str, str | bool]]:
    messages = runtime.session_repository.list_session_messages(session.id)
    rendered: list[dict[str, str | bool]] = []
    for message in messages:
        bubble = _render_conversation_message(message)
        if bubble is not None:
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
