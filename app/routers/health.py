"""Health check routes."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return application health status."""
    return HealthResponse(status="healthy")
