from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=250)


class PlaceResponse(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    city: str
    address: str | None
    status: str
    average_rating: float
    review_count: int
    created_at: datetime


class PlaceListResponse(BaseModel):
    items: list[PlaceResponse]
    total: int
