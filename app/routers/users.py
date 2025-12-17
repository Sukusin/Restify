from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.users import UserAuth, UserProfile
from app.schemas.auth import UserMeResponse
from app.schemas.users import UserProfileResponse, UserProfileUpdate
from app.services.recommendations import categories_to_csv, parse_categories

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserMeResponse)
def me(current: UserAuth = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(id=current.id, email=current.email, role=current.role, is_active=current.is_active)


@router.get("/me/profile", response_model=UserProfileResponse)
def get_profile(
    current: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    profile = db.get(UserProfile, current.id)
    cats = parse_categories(profile.preferred_categories if profile else "")
    return UserProfileResponse(
        user_id=current.id,
        display_name=profile.display_name if profile else None,
        city=profile.city if profile else None,
        preferred_categories=cats,
        bio=profile.bio if profile else None,
    )


@router.put("/me/profile", response_model=UserProfileResponse)
def update_profile(
    payload: UserProfileUpdate,
    current: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    profile = db.get(UserProfile, current.id)
    if not profile:
        profile = UserProfile(user_id=current.id)

    profile.display_name = payload.display_name
    profile.city = payload.city
    profile.bio = payload.bio
    profile.preferred_categories = categories_to_csv(payload.preferred_categories)

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return UserProfileResponse(
        user_id=current.id,
        display_name=profile.display_name,
        city=profile.city,
        preferred_categories=parse_categories(profile.preferred_categories),
        bio=profile.bio,
    )
