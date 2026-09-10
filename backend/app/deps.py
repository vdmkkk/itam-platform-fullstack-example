"""FastAPI dependencies: the database session, the calling student, the admin."""

from __future__ import annotations

import hmac
import math
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app import models, services
from app.db import get_db
from app.identity import (
    MISSING_TOKEN,
    TOKEN_HEADER,
    TOKEN_MAX_LENGTH,
    TOKEN_PAGE_HINT,
    TOKEN_PREFIX,
    hash_token,
)
from app.ratelimit import rate_limit_detail
from app.services import Actor

ADMIN_HEADER = "X-Admin-Token"
ADMIN_DISABLED = "Админский API выключен: на сервере не задан ADMIN_TOKEN."
ADMIN_MISSING = f"Нет заголовка {ADMIN_HEADER}."
ADMIN_WRONG = "Неверный админский токен."

course_token_header = APIKeyHeader(
    name=TOKEN_HEADER,
    scheme_name="CourseToken",
    description=(
        "Ваш личный токен курса (`exb_...`) со страницы курса, вкладка «API проекта». "
        "Нажмите **Authorize**, вставьте его, и каждый запрос через *Try it out* будет "
        "отправляться с ним."
    ),
    auto_error=False,
)

admin_token_header = APIKeyHeader(
    name=ADMIN_HEADER,
    scheme_name="AdminToken",
    description="Токен команды курса для эндпоинтов `/api/admin`. Студентам он не нужен.",
    auto_error=False,
)

DbSession = Annotated[Session, Depends(get_db)]


def _clean_token(raw: str | None) -> str:
    """Accept the token the way beginners paste it: quoted, or with a `Bearer ` prefix."""
    token = (raw or "").strip().strip("\"'").strip()
    if token.lower().startswith("bearer "):
        token = token[len("bearer ") :].strip()
    return token


def get_actor(
    request: Request,
    db: DbSession,
    raw_token: Annotated[str | None, Security(course_token_header)] = None,
) -> Actor:
    """Resolve the calling student, provisioning their stream and profile on first contact."""
    token = _clean_token(raw_token)
    if not token:
        if request.headers.get("authorization"):
            detail = f"Передайте токен курса в заголовке {TOKEN_HEADER}, а не в Authorization."
        else:
            detail = MISSING_TOKEN
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    if not token.startswith(TOKEN_PREFIX) or len(token) > TOKEN_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Это не похоже на токен курса: токены начинаются с {TOKEN_PREFIX}. {TOKEN_PAGE_HINT}",
        )

    state = request.app.state
    retry_after = state.rate_limiter.hit(hash_token(token))
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_limit_detail(state.settings.rate_limit_per_second),
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )

    identity = state.identity.resolve(token)
    stream = services.ensure_stream(db, identity.stream)
    user = services.ensure_user(db, stream, identity.user)
    return Actor(user=user, stream=stream)


CurrentActor = Annotated[Actor, Depends(get_actor)]


def get_board_settings(request: Request, db: DbSession) -> models.BoardSettings:
    return services.load_board_settings(db, request.app.state.settings)


BoardThresholds = Annotated[models.BoardSettings, Depends(get_board_settings)]


def require_admin(
    request: Request,
    raw_token: Annotated[str | None, Security(admin_token_header)] = None,
) -> None:
    expected: str = request.app.state.settings.admin_token
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=ADMIN_DISABLED)
    if not raw_token or not raw_token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ADMIN_MISSING)
    if not hmac.compare_digest(raw_token.strip().encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ADMIN_WRONG)
