from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.enums import ModerationStatus, UserRole
from app.models.places import Place
from app.models.reviews import Review
from app.schemas.places import PlaceListResponse
from app.schemas.reviews import ReviewListResponse
from app.routers.places import _to_place_response
from app.routers.reviews import _to_review_response
from app.services.ratings import recompute_place_rating

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get(
    "/places/pending",
    response_model=PlaceListResponse,
    dependencies=[Depends(require_role(UserRole.moderator, UserRole.admin))],
)
def pending_places(db: Session = Depends(get_db)) -> PlaceListResponse:
    places = list(db.scalars(select(Place).where(Place.status == ModerationStatus.pending.value)).all())
    return PlaceListResponse(items=[_to_place_response(p) for p in places], total=len(places))


@router.post(
    "/places/{place_id}/approve",
    status_code=204,
    dependencies=[Depends(require_role(UserRole.moderator, UserRole.admin))],
)
def approve_place(place_id: str, db: Session = Depends(get_db)) -> None:
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    place.status = ModerationStatus.approved.value
    db.add(place)
    db.commit()


@router.post(
    "/places/{place_id}/reject",
    status_code=204,
    dependencies=[Depends(require_role(UserRole.moderator, UserRole.admin))],
)
def reject_place(place_id: str, db: Session = Depends(get_db)) -> None:
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    place.status = ModerationStatus.rejected.value
    db.add(place)
    db.commit()


@router.get(
    "/reviews/pending",
    response_model=ReviewListResponse,
    dependencies=[Depends(require_role(UserRole.moderator, UserRole.admin))],
)
def pending_reviews(db: Session = Depends(get_db)) -> ReviewListResponse:
    reviews = list(db.scalars(select(Review).where(Review.status == ModerationStatus.pending.value)).all())
    return ReviewListResponse(items=[_to_review_response(r) for r in reviews], total=len(reviews))


@router.post(
    "/reviews/{review_id}/approve",
    status_code=204,
    dependencies=[Depends(require_role(UserRole.moderator, UserRole.admin))],
)
def approve_review(review_id: str, db: Session = Depends(get_db)) -> None:
    r = db.get(Review, review_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    r.status = ModerationStatus.approved.value
    db.add(r)
    db.commit()
    recompute_place_rating(db, place_id=r.place_id)


@router.post(
    "/reviews/{review_id}/reject",
    status_code=204,
    dependencies=[Depends(require_role(UserRole.moderator, UserRole.admin))],
)
def reject_review(review_id: str, db: Session = Depends(get_db)) -> None:
    r = db.get(Review, review_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    r.status = ModerationStatus.rejected.value
    db.add(r)
    db.commit()
    recompute_place_rating(db, place_id=r.place_id)
