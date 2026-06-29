from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class PlatformOverview(BaseModel):
    status: str
    platform: str
    systems: list[str]
