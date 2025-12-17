from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import ModerationStatus
from app.models.places import Place
from app.models.reviews import Review


def recompute_place_rating(db: Session, *, place_id: str) -> None:
    stmt = (
        select(func.count(Review.id), func.avg(Review.rating))
        .where(Review.place_id == place_id)
        .where(Review.status == ModerationStatus.approved.value)
    )
    cnt, avg = db.execute(stmt).one()
    place = db.get(Place, place_id)
    if not place:
        return
    place.review_count = int(cnt or 0)
    place.average_rating = float(avg or 0.0)
    db.add(place)
    db.commit()
