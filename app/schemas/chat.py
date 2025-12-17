from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.places import PlaceResponse


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    city: str | None = None
    category: str | None = None
    min_rating: float | None = None
    limit_places: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    reply: str
    places: list[PlaceResponse]
