from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.users import UserAuth, UserProfile
from app.schemas.places import PlaceResponse
from app.schemas.recommendations import RecommendationResponse
from app.services.recommendations import parse_categories, recommend_places
from app.routers.places import _to_place_response

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    current: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
    city: str | None = Query(default=None, max_length=120),
    exclude_reviewed: bool = Query(default=True),
) -> RecommendationResponse:
    profile = db.get(UserProfile, current.id)
    cats = parse_categories(profile.preferred_categories if profile else "")
    city_val = city or (profile.city if profile else None)

    places = recommend_places(
        db,
        user_id=current.id,
        categories=cats,
        city=city_val,
        limit=limit,
        exclude_reviewed=exclude_reviewed,
    )

    items = [_to_place_response(p) for p in places]
    return RecommendationResponse(items=items, total=len(items))
