from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.places import Place
from app.models.reviews import Review
from app.models.users import UserAuth
from app.schemas.reviews import ReviewCreate, ReviewListResponse, ReviewResponse, ReviewSummaryResponse
from app.services.llm import llm, LLMError
from app.services.ratings import recompute_place_rating

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/places/{place_id}/reviews", tags=["reviews"])


def _to_review_response(r: Review) -> ReviewResponse:
    return ReviewResponse(
        id=r.id,
        place_id=r.place_id,
        user_id=r.user_id,
        rating=r.rating,
        text=r.text,
        created_at=r.created_at,
    )


@router.post("", response_model=ReviewResponse, status_code=201)
def create_review(
    place_id: int,
    payload: ReviewCreate,
    current: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    review = Review(
        place_id=place_id,
        user_id=current.id,
        rating=payload.rating,
        text=(payload.text or "").strip() or None,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Без модерации пересчитываем рейтинг сразу после добавления отзыва
    recompute_place_rating(db, place_id=place_id)

    return _to_review_response(review)


@router.get("", response_model=ReviewListResponse)
def list_reviews(
    place_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ReviewListResponse:
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    stmt = (
        select(Review)
        .where(Review.place_id == place_id)
        .order_by(Review.created_at.desc())
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = list(db.scalars(stmt.limit(limit).offset(offset)).all())
    return ReviewListResponse(items=[_to_review_response(r) for r in items], total=int(total or 0))


@router.get("/summary", response_model=ReviewSummaryResponse)
async def summarize_reviews(
    place_id: int,
    db: Session = Depends(get_db),
) -> ReviewSummaryResponse:
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    reviews = list(
        db.scalars(
            select(Review)
            .where(Review.place_id == place_id)
            .order_by(Review.created_at.desc())
            .limit(50)
        ).all()
    )
    texts = [r.text for r in reviews if r.text]
    if not texts:
        return ReviewSummaryResponse(place_id=place_id, summary="Нет текстовых отзывов для суммаризации.")

    try:
        summary = await llm.summarize_reviews(place_name=place.name, reviews=texts)
    except LLMError:
        logger.exception("LLM summary error")
        summary = "(Ошибка LLM при суммаризации)"

    return ReviewSummaryResponse(place_id=place_id, summary=summary)
