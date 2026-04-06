from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from thohago.web.repositories import SessionRecord
from thohago.web.runtime import WebRuntime


admin_security = HTTPBasic()
sync_security = HTTPBearer()


def get_runtime(request: Request) -> WebRuntime:
    return request.app.state.runtime  # type: ignore[return-value]


def get_session_or_404(
    customer_token: str,
    runtime: WebRuntime = Depends(get_runtime),
) -> SessionRecord:
    session = runtime.session_repository.get_by_customer_token(customer_token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown customer token")
    return session


def require_admin(
    credentials: HTTPBasicCredentials = Depends(admin_security),
    runtime: WebRuntime = Depends(get_runtime),
) -> str:
    valid_username = secrets.compare_digest(credentials.username, runtime.web_config.admin_username)
    valid_password = secrets.compare_digest(credentials.password, runtime.web_config.admin_password)
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def require_sync_token(
    credentials: HTTPAuthorizationCredentials = Depends(sync_security),
    runtime: WebRuntime = Depends(get_runtime),
) -> str:
    if not secrets.compare_digest(credentials.credentials, runtime.web_config.sync_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sync token",
        )
    return credentials.credentials
