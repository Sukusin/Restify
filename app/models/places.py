from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    avg_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    reviews: Mapped[list["Review"]] = relationship(back_populates="place", cascade="all, delete-orphan")


Index("ix_places_category_city", Place.category, Place.city)
