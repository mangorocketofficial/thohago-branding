from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from thohago.web.dependencies import get_runtime, require_admin
from thohago.web.runtime import WebRuntime


router = APIRouter()


@router.get("/admin/sessions", response_class=HTMLResponse)
def list_sessions(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    _: str = Depends(require_admin),
) -> HTMLResponse:
    return runtime.templates.TemplateResponse(
        request,
        "admin_sessions.html",
        {
            "sessions": runtime.session_repository.list_sessions(),
            "shops": sorted(runtime.shops.values(), key=lambda shop: shop.shop_id),
            "created_session": None,
            "error_message": None,
            "title": "Admin Sessions",
        },
    )


@router.get("/admin/sessions/new", response_class=HTMLResponse)
def new_session_page(
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    _: str = Depends(require_admin),
) -> HTMLResponse:
    return runtime.templates.TemplateResponse(
        request,
        "admin_session_new.html",
        {
            "shops": sorted(runtime.shops.values(), key=lambda shop: shop.shop_id),
            "created_session": None,
            "error_message": None,
            "title": "New Session",
        },
    )


@router.post("/admin/sessions", response_class=HTMLResponse)
def create_session(
    request: Request,
    response: Response,
    shop_id: str = Form(...),
    session_key: str = Form(""),
    runtime: WebRuntime = Depends(get_runtime),
    _: str = Depends(require_admin),
) -> HTMLResponse:
    created_session = None
    error_message = None
    try:
        created_session = runtime.session_service.create_session(
            shop_id=shop_id,
            session_key=session_key.strip() or None,
        )
    except KeyError as exc:
        error_message = str(exc)
        response.status_code = status.HTTP_400_BAD_REQUEST

    if created_session is not None:
        return RedirectResponse(
            url=f"/admin/sessions/{created_session.session.id}?created=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return runtime.templates.TemplateResponse(
        request,
        "admin_session_new.html",
        {
            "shops": sorted(runtime.shops.values(), key=lambda shop: shop.shop_id),
            "created_session": None,
            "error_message": error_message,
            "title": "New Session",
        },
    )


@router.get("/admin/sessions/{session_id}", response_class=HTMLResponse)
def session_detail(
    session_id: str,
    request: Request,
    runtime: WebRuntime = Depends(get_runtime),
    _: str = Depends(require_admin),
) -> HTMLResponse:
    session = runtime.session_repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session id")
    artifacts = runtime.session_service.artifacts_for_session(session)
    customer_url = runtime.session_service.build_customer_url(session.customer_token)
    preview_url = runtime.session_service.customer_path_for_stage(session.customer_token, "awaiting_approval")
    complete_url = runtime.session_service.customer_path_for_stage(session.customer_token, "approved")
    return runtime.templates.TemplateResponse(
        request,
        "admin_session_detail.html",
        {
            "title": "Session Detail",
            "session": session,
            "shop": runtime.shops.get(session.shop_id),
            "customer_url": customer_url,
            "preview_url": preview_url,
            "complete_url": complete_url,
            "messages": runtime.session_repository.list_session_messages(session.id),
            "artifacts": runtime.session_repository.list_session_artifacts(session.id),
            "artifact_root": artifacts.artifact_dir,
            "created_flag": request.query_params.get("created") == "1",
        },
    )
