from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=250)
    description: str | None = Field(default=None, max_length=1000)


class PlaceResponse(BaseModel):
    id: int
    name: str
    category: str
    city: str
    address: str
    description: str | None
    created_at: datetime
    avg_rating: float
    reviews_count: int


class PlaceListResponse(BaseModel):
    items: list[PlaceResponse]
    total: int
