from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    preferred_categories: list[str] = Field(default_factory=list)
    bio: str | None = Field(default=None, max_length=500)


class UserProfileResponse(BaseModel):
    user_id: str
    display_name: str | None
    city: str | None
    preferred_categories: list[str]
    bio: str | None
