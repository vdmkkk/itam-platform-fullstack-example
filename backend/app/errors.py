"""Error responses.

Every error has the same shape: `{"detail": "a human-readable sentence"}`.
Validation errors also carry `errors: [{field, message}]`, so forms can
highlight the exact input that is wrong.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

FRIENDLY_MESSAGES = {
    "missing": "This field is required",
    "extra_forbidden": "Unknown field: check the spelling, or look up the allowed fields in /docs",
}

# Errors located at the body itself, which usually means "no JSON was sent".
BODY_SHAPE_ERRORS = {"missing", "model_attributes_type", "dict_type", "model_type"}

LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


class FieldProblem(Exception):
    """A business-rule failure about one input, such as an email that is already taken."""

    def __init__(self, status_code: int, field: str, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.field = field
        self.message = message
        self.detail = detail or f"{field}: {message}"


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(part) for part in loc]
    if parts and parts[0] in LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(parts) or "body"


def _describe(error: dict[str, Any]) -> tuple[str, str]:
    kind = error.get("type", "")
    loc = tuple(error.get("loc", ()))
    if kind == "json_invalid":
        reason = error.get("ctx", {}).get("error", "syntax error")
        return "body", f"The request body is not valid JSON ({reason})"
    if loc == ("body",) and kind in BODY_SHAPE_ERRORS:
        return "body", "Send the request body as a JSON object, with the header Content-Type: application/json"
    message = FRIENDLY_MESSAGES.get(kind, error.get("msg", "Invalid value"))
    return _field_name(loc), message.removeprefix("Value error, ")


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        field, message = _describe(error)
        errors.append({"field": field, "message": message})
    detail = "; ".join(f"{e['field']}: {e['message']}" for e in errors) or "Invalid request"
    return JSONResponse(status_code=422, content={"detail": detail, "errors": errors})


async def handle_field_problem(request: Request, exc: FieldProblem) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "errors": [{"field": exc.field, "message": exc.message}]},
    )


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> Response:
    headers = getattr(exc, "headers", None)
    if exc.status_code in (204, 304):
        return Response(status_code=exc.status_code, headers=headers)

    detail = exc.detail
    docs = f"{request.scope.get('root_path', '')}/docs"
    if exc.status_code == 404 and detail == "Not Found":
        detail = (
            f"There is no endpoint {request.method} {request.url.path}. Board endpoints start "
            f"with /api; see {docs} for the full list."
        )
    elif exc.status_code == 405 and detail == "Method Not Allowed":
        detail = f"{request.method} is not allowed on {request.url.path}. Check the method in {docs}."
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=headers)


class CatchAllErrorsMiddleware:
    """Turns unexpected exceptions into a JSON 500.

    It sits inside the CORS middleware, so even a crash reaches the browser
    with CORS headers. Otherwise students would see a misleading CORS error
    instead of the 500.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = False

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            logger.exception("Unhandled error on %s %s", scope.get("method"), scope.get("path"))
            if started:
                raise
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "Something went wrong on the server. It's not your fault; please "
                    "tell the course team if it keeps happening."
                },
            )
            await response(scope, receive, send)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(FieldProblem, handle_field_problem)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)  # type: ignore[arg-type]
