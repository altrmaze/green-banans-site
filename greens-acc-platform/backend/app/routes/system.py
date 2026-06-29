from fastapi import APIRouter

from app.models.platform import HealthResponse, PlatformOverview
from app.services.platform import PlatformService

router = APIRouter()
service = PlatformService()


@router.get("/", response_model=PlatformOverview)
async def root() -> PlatformOverview:
    return service.overview()


@router.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")
