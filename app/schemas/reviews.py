from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    id: str
    place_id: str
    user_id: str
    rating: int
    text: str | None
    status: str
    created_at: datetime


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    total: int


class ReviewSummaryResponse(BaseModel):
    place_id: str
    summary: str
