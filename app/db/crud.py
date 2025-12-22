from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models.places import Place


def _place_to_dict(p: Place) -> dict:
    return {
        "name": p.name,
        "category": p.category,
        "city": p.city,
        "address": p.address,
        "description": p.description,
    }


async def insert_places(places: list[Place]) -> int:
    if not places:
        return 0

    dialect = engine.dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        from sqlalchemy import insert as dialect_insert

    inserted_total = 0

    db: Session = SessionLocal()
    try:
        ncols = 5
        if dialect == 'sqlite':
            batch_size = max(50, 999 // ncols)
        else:
            batch_size = 1000
        for i in range(0, len(places), batch_size):
            chunk = places[i : i + batch_size]
            values = [_place_to_dict(p) for p in chunk]

            stmt = dialect_insert(Place).values(values)
            if hasattr(stmt, "on_conflict_do_nothing"):
                stmt = stmt.on_conflict_do_nothing(index_elements=["name", "category", "city", "address"])

            res = db.execute(stmt)
            db.commit()

            if res.rowcount and res.rowcount > 0:
                inserted_total += int(res.rowcount)

        return inserted_total
    finally:
        db.close()


def get_places_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(Place)) or 0)
