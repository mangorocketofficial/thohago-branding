from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, Response

from thohago.web.dependencies import get_runtime, require_sync_token
from thohago.web.runtime import WebRuntime
from thohago.web.services.sync import SyncValidationError


router = APIRouter()


@router.get("/api/sync/sessions")
def list_sync_sessions(
    stage: str | None = None,
    runtime: WebRuntime = Depends(get_runtime),
    _: str = Depends(require_sync_token),
) -> JSONResponse:
    sessions = runtime.sync_service.list_sessions(stage=stage)
    payload = {
        "sessions": [
            {
                "session_id": session.id,
                "shop_id": session.shop_id,
                "session_key": session.session_key,
                "stage": session.stage,
                "customer_url": runtime.session_service.build_customer_url(session.customer_token),
            }
            for session in sessions
        ]
    }
    return JSONResponse(payload)


@router.get("/api/sync/sessions/{session_id}/download")
def download_sync_session(
    session_id: str,
    runtime: WebRuntime = Depends(get_runtime),
    _: str = Depends(require_sync_token),
) -> Response:
    session = runtime.session_repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session id")
    content = runtime.sync_service.build_download_zip(session)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{session_id}.zip"'},
    )


@router.post("/api/sync/sessions/{session_id}/upload")
async def upload_sync_session(
    session_id: str,
    bundle: UploadFile = File(...),
    manifest_json: str = Form(...),
    runtime: WebRuntime = Depends(get_runtime),
    _: str = Depends(require_sync_token),
) -> JSONResponse:
    session = runtime.session_repository.get_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session id")
    try:
        manifest = json.loads(manifest_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid manifest JSON: {exc}") from exc

    try:
        updated = runtime.sync_service.apply_preview_upload(
            session,
            manifest=manifest,
            bundle_bytes=await bundle.read(),
        )
    except SyncValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return JSONResponse(
        {
            "session_id": updated.id,
            "stage": updated.stage,
            "preview_url": f"/s/{updated.customer_token}/preview",
            "manifest_path": "published/manifest.json",
        }
    )
