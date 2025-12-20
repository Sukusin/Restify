from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.places import Place
from app.models.reviews import Review


def recompute_place_rating(db: Session, *, place_id: int) -> None:
    """Recompute aggregated rating fields for a place.

    Keeps the places table minimal: aggregates are stored in-place (avg_rating, reviews_count).
    """

    stmt = select(func.count(Review.id), func.avg(Review.rating)).where(Review.place_id == place_id)
    cnt, avg = db.execute(stmt).one()

    place = db.get(Place, place_id)
    if not place:
        return

    place.reviews_count = int(cnt or 0)
    place.avg_rating = float(avg or 0.0)
    db.add(place)
    db.commit()
