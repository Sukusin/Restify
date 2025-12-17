from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.places import PlaceResponse


class RecommendationResponse(BaseModel):
    items: list[PlaceResponse]
    total: int


class RecommendationParams(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)
    exclude_reviewed: bool = True
