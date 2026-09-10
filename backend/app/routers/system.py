from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app import schemas
from app.deps import DbSession

router = APIRouter(tags=["System"])

DATABASE_DOWN = "База данных недоступна."


@router.get(
    "/health",
    response_model=schemas.Health,
    summary="Проверка работоспособности",
    responses={503: {"model": schemas.ErrorResponse, "description": DATABASE_DOWN}},
)
def health(db: DbSession) -> schemas.Health:
    """Возвращает `{"status": "ok"}`, когда API и его база данных работают. Токен **не нужен**."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=DATABASE_DOWN) from exc
    return schemas.Health(status="ok")


@router.get("/", include_in_schema=False)
def root(request: Request) -> RedirectResponse:
    """Opening the API URL in a browser lands on the docs."""
    return RedirectResponse(f"{request.scope.get('root_path', '')}/docs")
