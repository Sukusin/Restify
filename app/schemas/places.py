from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlaceResponse(BaseModel):
    id: int
    name: str
    category: str
    city: str
    address: str | None
    description: str | None
    created_at: datetime
    avg_rating: float
    reviews_count: int


class PlaceListResponse(BaseModel):
    items: list[PlaceResponse]
    total: int
