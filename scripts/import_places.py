from __future__ import annotations

import logging
import asyncio

from app.db.session import SessionLocal
from sqlalchemy import select

from app.models.places import Place
from app.parsers.parse_places import parse_places

logger = logging.getLogger(__name__)


def import_places() -> dict:
    added = 0
    skipped = 0
    updated = 0

    places = asyncio.run(parse_places())

    db = SessionLocal()

    for p in places:
        name = p.name.strip()
        city = p.city.strip()
        address = p.address.strip()
        category = p.category.strip().lower()
        description = (p.description or "").strip() or None

        if not name or not city or not category:
            logger.warning("Skip invalid place: %r", p)
            skipped += 1
            continue

        # Ищем дубликат
        existing = db.execute(
            select(Place).where(
                Place.name == name,
                Place.city == city,
                Place.category == category,
            )
        ).scalar_one_or_none()

        if existing:
            # Можно обновлять описание, если пришло новое
            if description and (existing.description or "").strip() != description:
                existing.description = description
                updated += 1
            else:
                skipped += 1
            continue

        obj = Place(
            name=name,
            city=city,
            address=address,
            category=category,
            description=description
        )
        db.add(obj)
        added += 1

        db.commit()

    logger.info("Import finished: added=%s updated=%s skipped=%s", added, updated, skipped)
    return {"added": added, "updated": updated, "skipped": skipped}

import_places()
