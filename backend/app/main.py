"""Application factory. Serve it with `uvicorn app.main:create_app --factory`."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings
from app.db import create_db_engine
from app.docs import TAGS, api_description
from app.errors import CatchAllErrorsMiddleware, install_error_handlers
from app.identity import IdentityResolver, PlatformClient, RosterThrottle
from app.ratelimit import RateLimiter
from app.routers import admin, board, cards, comments, system, users

SWAGGER_UI_PARAMETERS = {
    # Students paste their token once; keep it across page reloads.
    "persistAuthorization": True,
    "tryItOutEnabled": True,
    "displayRequestDuration": True,
    "filter": True,
    "docExpansion": "list",
    "defaultModelsExpandDepth": 1,
    "defaultModelExpandDepth": 2,
}


def operation_id(route: APIRoute) -> str:
    """`list_cards` -> `listCards`: tidy names for generated API clients."""
    head, *rest = route.name.split("_")
    return head + "".join(part.capitalize() for part in rest)


def use_friendly_validation_errors(spec: dict[str, Any]) -> None:
    """Document 422s with the shape our handler really returns.

    FastAPI adds its own `HTTPValidationError` to routes that declare no 422.
    Point those at `ValidationErrorResponse` and drop the unused schemas, so
    codegen produces a single error type.
    """
    friendly = {
        "description": "A parameter is invalid, for example the id is not a UUID.",
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}}
        },
    }
    for methods in spec.get("paths", {}).values():
        for operation in methods.values():
            response = operation.get("responses", {}).get("422")
            if response and "HTTPValidationError" in json.dumps(response):
                operation["responses"]["422"] = friendly
    component_schemas = spec.get("components", {}).get("schemas", {})
    component_schemas.pop("HTTPValidationError", None)
    component_schemas.pop("ValidationError", None)


def create_app(
    settings: Settings | None = None, *, platform_transport: httpx.BaseTransport | None = None
) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    engine = create_db_engine(settings.database_url)
    platform = PlatformClient(
        base_url=settings.platform_api_url,
        service_key=settings.platform_service_key,
        backend_slug=settings.backend_slug,
        timeout=settings.platform_timeout_seconds,
        transport=platform_transport,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        platform.close()
        engine.dispose()

    public_url = settings.public_base_url.rstrip("/")
    app = FastAPI(
        title="ITAM Board API",
        version="1.0.0",
        summary="A Trello-like board of events, ideas and questions for the Frontend (ITAM) course.",
        description=api_description(settings),
        openapi_tags=TAGS,
        # The edge proxy strips this prefix; re-advertise it so Swagger's calls go through it.
        root_path=settings.root_path.rstrip("/"),
        servers=[{"url": public_url, "description": "Public API"}] if public_url else None,
        root_path_in_servers=not public_url,
        generate_unique_id_function=operation_id,
        separate_input_output_schemas=False,
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
    app.state.platform = platform
    app.state.identity = IdentityResolver(
        platform,
        ttl=settings.identity_cache_ttl_seconds,
        negative_ttl=settings.identity_negative_cache_ttl_seconds,
    )
    app.state.roster_throttle = RosterThrottle(settings.roster_cache_ttl_seconds)
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_second, settings.rate_limit_burst)

    install_error_handlers(app)
    # Added first, so it is innermost: crashes become JSON 500s *inside* CORS, and the
    # browser shows the real error instead of a misleading CORS failure.
    app.add_middleware(CatchAllErrorsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Retry-After"],
        max_age=86400,
    )

    api = APIRouter(prefix="/api")
    for module in (board, cards, comments, users, admin):
        api.include_router(module.router)
    app.include_router(system.router)
    app.include_router(api)

    build_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            use_friendly_validation_errors(build_openapi())
        return app.openapi_schema  # type: ignore[return-value]

    app.openapi = openapi  # type: ignore[method-assign]
    return app
