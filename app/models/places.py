from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ModerationStatus


class Place(Base):
    __tablename__ = "places"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(250), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ModerationStatus.pending.value, index=True)

    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users_auth.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    average_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    reviews: Mapped[list["Review"]] = relationship(back_populates="place", cascade="all, delete-orphan")


Index("ix_places_category_city", Place.category, Place.city)
Index("ix_places_status_category", Place.status, Place.category)
