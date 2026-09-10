"""Error responses.

Every error has the same shape: `{"detail": "a human-readable sentence"}`.
Validation errors also carry `errors: [{field, message}]`, so forms can
highlight the exact input that is wrong. Students show these messages in
their UI, so they are in Russian, pydantic's own messages included.
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

REQUIRED = "Обязательное поле"
BODY_NOT_JSON = "Отправьте тело запроса JSON-объектом с заголовком Content-Type: application/json"
UUID_EXPECTED = "Нужен UUID, например 3f8e9c1a-5b2d-4e7f-9a61-2c4b8d0e1f23"

# Pydantic error types whose Russian message needs no context.
MESSAGES = {
    "missing": REQUIRED,
    "extra_forbidden": "Неизвестное поле: проверьте, как оно пишется, или посмотрите список полей в /docs",
    "string_type": "Нужна строка",
    "int_type": "Нужно целое число",
    "int_parsing": "Нужно целое число",
    "int_from_float": "Нужно целое число, без дробной части",
    "bool_type": "Нужно true или false",
    "bool_parsing": "Нужно true или false",
    "uuid_type": UUID_EXPECTED,
    "uuid_parsing": UUID_EXPECTED,
}

# An explicit `null` for a field that can't be null fails with one of these.
NOT_NULL_TYPES = {"string_type", "int_type", "bool_type", "uuid_type", "enum"}

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


def _plural(count: int, one: str, few: str, many: str) -> str:
    """Russian plural forms: 1 символ, 2 символа, 5 символов."""
    tens, units = count % 100, count % 10
    if units == 1 and tens != 11:
        return one
    if 2 <= units <= 4 and not 12 <= tens <= 14:
        return few
    return many


def _characters(count: int) -> str:
    return f"{count} {_plural(count, 'символ', 'символа', 'символов')}"


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(part) for part in loc]
    if parts and parts[0] in LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(parts) or "body"


def _message(error: dict[str, Any]) -> str:
    """Pydantic's message, in Russian. Our own validators already raise Russian messages."""
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    if kind in NOT_NULL_TYPES and "input" in error and error["input"] is None:
        return "Не может быть null"
    if kind in MESSAGES:
        return MESSAGES[kind]
    if kind == "string_too_short":
        minimum = ctx.get("min_length", 1)
        return "Не может быть пустым" if minimum == 1 else f"Минимум {_characters(minimum)}"
    if kind == "string_too_long":
        return f"Максимум {_characters(ctx.get('max_length', 0))}"
    if kind == "greater_than_equal":
        return f"Должно быть не меньше {ctx.get('ge')}"
    if kind == "less_than_equal":
        return f"Должно быть не больше {ctx.get('le')}"
    if kind == "enum":
        # ctx: {"expected": "'event', 'idea' or 'question'"}
        return f"Допустимые значения: {str(ctx.get('expected', '')).replace(' or ', ', ')}"
    if kind == "value_error" and "email" in str(error.get("msg", "")).lower():
        return "Некорректный email"
    return str(error.get("msg", "Некорректное значение")).removeprefix("Value error, ")


def _describe(error: dict[str, Any]) -> tuple[str, str]:
    kind = error.get("type", "")
    loc = tuple(error.get("loc", ()))
    if kind == "json_invalid":
        reason = error.get("ctx", {}).get("error", "syntax error")
        return "body", f"Тело запроса — не валидный JSON ({reason})"
    if loc == ("body",) and kind in BODY_SHAPE_ERRORS:
        return "body", BODY_NOT_JSON
    return _field_name(loc), _message(error)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        field, message = _describe(error)
        errors.append({"field": field, "message": message})
    detail = "; ".join(f"{e['field']}: {e['message']}" for e in errors) or "Некорректный запрос"
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
            f"Эндпоинта {request.method} {request.url.path} нет. Эндпоинты доски начинаются "
            f"с /api, полный список — в {docs}."
        )
    elif exc.status_code == 405 and detail == "Method Not Allowed":
        detail = (
            f"Метод {request.method} не поддерживается для {request.url.path}. "
            f"Проверьте метод в {docs}."
        )
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
                    "detail": "Что-то сломалось на сервере. Вы тут ни при чём; если это "
                    "повторяется, сообщите команде курса."
                },
            )
            await response(scope, receive, send)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(FieldProblem, handle_field_problem)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)  # type: ignore[arg-type]
