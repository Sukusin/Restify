from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.places import Place
from app.models.users import UserAuth
from app.schemas.places import PlaceCreate, PlaceListResponse, PlaceResponse

router = APIRouter(prefix="/places", tags=["places"])


def _to_place_response(place: Place) -> PlaceResponse:
    return PlaceResponse(
        id=place.id,
        name=place.name,
        category=place.category,
        city=place.city,
        address=place.address,
        description=place.description,
        created_at=place.created_at,
        avg_rating=place.avg_rating,
        reviews_count=place.reviews_count,
    )


@router.post("", response_model=PlaceResponse, status_code=201)
def create_place(
    payload: PlaceCreate,
    current: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaceResponse:
    # Минимально: создаём место сразу доступным (без модерации и лишних полей).
    place = Place(
        name=payload.name.strip(),
        category=payload.category.strip().lower(),
        city=payload.city.strip(),
        address=(payload.address or "").strip(),
        description=(payload.description or "").strip() or None,
    )
    db.add(place)
    db.commit()
    db.refresh(place)
    return _to_place_response(place)


@router.get("", response_model=PlaceListResponse)
def list_places(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=80),
    city: str | None = Query(default=None, max_length=120),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PlaceListResponse:
    stmt = select(Place)

    if q:
        # SQLite-friendly search (case-insensitive)
        q_norm = q.strip().lower()
        stmt = stmt.where(func.lower(Place.name).like(f"%{q_norm}%"))
    if category:
        stmt = stmt.where(Place.category == category.strip().lower())
    if city:
        stmt = stmt.where(Place.city == city.strip())
    if min_rating is not None:
        stmt = stmt.where(Place.avg_rating >= min_rating)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = list(
        db.scalars(
            stmt.order_by(Place.avg_rating.desc(), Place.reviews_count.desc(), Place.name)
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return PlaceListResponse(items=[_to_place_response(p) for p in items], total=int(total or 0))


@router.get("/{place_id}", response_model=PlaceResponse)
def get_place(place_id: int, db: Session = Depends(get_db)) -> PlaceResponse:
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return _to_place_response(place)
