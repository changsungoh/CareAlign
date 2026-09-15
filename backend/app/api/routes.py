from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse, VersionResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(
        app_version=settings.app_version,
        prompt_version=settings.prompt_version,
        rules_version=settings.rules_version,
        dataset_version=settings.dataset_version,
        evaluated_at=datetime.now(UTC),
        demo_mode=settings.demo_mode,
    )
