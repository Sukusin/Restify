from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.places import Place
from app.models.reviews import Review


def parse_categories(csv: str) -> list[str]:
    return [c.strip().lower() for c in (csv or "").split(",") if c.strip()]


def categories_to_csv(cats: list[str]) -> str:
    return ",".join(sorted({c.strip().lower() for c in cats if c.strip()}))


def recommend_places(
    db: Session,
    *,
    user_id: str,
    categories: list[str],
    city: str | None = None,
    limit: int = 10,
    exclude_reviewed: bool = True,
) -> list[Place]:
    q = select(Place)

    if city:
        q = q.where(Place.city == city)
    if categories:
        q = q.where(Place.category.in_(categories))

    if exclude_reviewed:
        subq = select(Review.place_id).where(Review.user_id == user_id)
        q = q.where(~Place.id.in_(subq))

    q = q.order_by(desc(Place.avg_rating), desc(Place.reviews_count), Place.name).limit(limit)
    return list(db.scalars(q).all())
