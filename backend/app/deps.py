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
from app.identity import TOKEN_HEADER, TOKEN_MAX_LENGTH, TOKEN_PAGE_HINT, TOKEN_PREFIX, hash_token
from app.services import Actor

ADMIN_HEADER = "X-Admin-Token"

course_token_header = APIKeyHeader(
    name=TOKEN_HEADER,
    scheme_name="CourseToken",
    description=(
        "Your personal course token (`exb_...`) from the course page, tab «API проекта». "
        "Click **Authorize**, paste it, and every *Try it out* request will carry it."
    ),
    auto_error=False,
)

admin_token_header = APIKeyHeader(
    name=ADMIN_HEADER,
    scheme_name="AdminToken",
    description="Course-team token for the `/api/admin` endpoints. Students don't need it.",
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
            detail = f"Send your course token in the {TOKEN_HEADER} header, not in Authorization."
        else:
            detail = (
                f"Missing {TOKEN_HEADER} header. {TOKEN_PAGE_HINT} Send it with every request. "
                "In Swagger, click Authorize."
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    if not token.startswith(TOKEN_PREFIX) or len(token) > TOKEN_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"This doesn't look like a course token: tokens start with {TOKEN_PREFIX}. {TOKEN_PAGE_HINT}",
        )

    state = request.app.state
    retry_after = state.rate_limiter.hit(hash_token(token))
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Too many requests: the limit is {state.settings.rate_limit_per_second:g} per "
                "second per token. Is a useEffect re-running in a loop? Check its dependency array."
            ),
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The admin API is disabled: ADMIN_TOKEN is not configured on the server.",
        )
    if not raw_token or not raw_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Missing {ADMIN_HEADER} header."
        )
    if not hmac.compare_digest(raw_token.strip().encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong admin token.")
