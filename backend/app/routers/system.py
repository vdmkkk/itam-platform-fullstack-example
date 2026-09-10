from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app import schemas
from app.deps import DbSession

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    response_model=schemas.Health,
    summary="Health check",
    responses={503: {"model": schemas.ErrorResponse, "description": "The database is unreachable."}},
)
def health(db: DbSession) -> schemas.Health:
    """Returns `{"status": "ok"}` when the API and its database are up. It needs **no token**."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The database is unreachable."
        ) from exc
    return schemas.Health(status="ok")


@router.get("/", include_in_schema=False)
def root(request: Request) -> RedirectResponse:
    """Opening the API URL in a browser lands on the docs."""
    return RedirectResponse(f"{request.scope.get('root_path', '')}/docs")
