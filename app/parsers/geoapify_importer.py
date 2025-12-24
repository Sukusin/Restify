from __future__ import annotations

import asyncio
import logging

import aiohttp
from aiohttp import ClientResponseError
from fastapi import status

from app.core.config import settings
from app.db.crud import insert_places, get_places_count
from app.db.session import SessionLocal
from app.models.places import Place

logger = logging.getLogger(__name__)

LIMIT_PER_REQUEST = 300

CATEGORIES = [
    "catering.cafe",
    "sport.fitness.fitness_centre",
    "leisure.park",
    "commercial.shopping_mall",
    "entertainment.museum",
    "entertainment.cinema",
    "entertainment.theatre",
    "entertainment.zoo",
    "entertainment.amusement_park",
    "leisure.beach",
    "entertainment.nightclub",
    "catering.restaurant",
    "entertainment.library",
    "leisure.spa",
]

CATEGORY_MAP = {
    "catering.cafe": "Кафе",
    "leisure.park": "Парк культуры и отдыха",
    "entertainment.museum": "Музей",
    "sport.fitness.fitness_centre": "Спорт",
    "commercial.shopping_mall": "Торговый центр",
    "entertainment.cinema": "Кинотеатр",
    "entertainment.theatre": "Театр",
    "entertainment.zoo": "Зоопарк",
    "entertainment.amusement_park": "Парк развлечений",
    "leisure.beach": "Пляж",
    "entertainment.nightclub": "Ночной клуб",
    "catering.restaurant": "Ресторан",
    "entertainment.library": "Библиотека",
    "leisure.spa": "Спа-салон",
}

CITIES: dict[str, tuple[float, float]] = {
    "Москва": (55.7558, 37.6176),
    "Санкт-Петербург": (59.9343, 30.3351),
    "Екатеринбург": (56.8389, 60.6057),
    "Тольятти": (53.1959, 50.1001),
    "Уфа": (54.7388, 55.9721),
    "Самара": (53.7596, 49.1088),
    "Казань": (55.8304, 49.0661),
    "Новосибирск": (55.0381, 82.9058),
    "Тюмень": (57.1523, 65.5289),
    "Орёл": (54.5293, 36.2754),
    "Омск": (54.9887, 73.3686),
    "Липецк": (52.6045, 39.5953),
    "Саратов": (51.5333, 46.0068),
    "Кемерово": (55.3000, 86.0833),
    "Тула": (54.0000, 37.7500),
    "Пенза": (53.2000, 45.0000),
    "Воронеж": (52.0000, 38.0000),
    "Оренбург": (51.7000, 55.1000),
    "Сызрань": (53.5000, 49.4000),
    "Йошкар-Ола": (54.3000, 48.4000),
    "Курск": (52.7000, 41.4000),
    "Краснодар": (45.0000, 38.9000),
    "Нижний Новгород": (56.3268, 44.0060),
    "Химки": (55.8304, 37.6342),
    "Подольск": (55.4500, 37.6167),
    "Балашиха": (55.9106, 37.7344),
    "Люберцы": (55.7522, 37.6156),
    "Набережные Челны": (55.7911, 49.1353),
    "Красноярск": (55.3042, 86.1047),
    "Жуковский": (55.5953, 38.1191),
    "Владимир": (56.1290, 40.4077),
    "Брянск": (53.2431, 34.3635),
    "Смоленск": (54.7815, 32.0508),
    "Архангельск": (64.5396, 40.5200),
    "Мурманск": (68.9705, 33.0745),
    "Чебоксары": (56.1328, 47.2460),
    "Пермь": (58.0105, 56.2504),
    "Волгоград": (48.7080, 44.5133),
    "Ульяновск": (54.3282, 48.3864),
    "Киров": (58.6000, 49.6500),
    "Ярославль": (57.6299, 39.8737),
    "Тверь": (56.8583, 35.9000),
    "Иваново": (57.0000, 40.9734),
    "Череповец": (59.1333, 37.9000),
    "Астрахань": (46.3490, 48.0430),
    "Ижевск": (56.8497, 53.2050),
    "Великий Новгород": (58.5220, 31.2695),
    "Хабаровск": (48.4820, 135.0840),
    "Владивосток": (43.1056, 131.8735),
}


async def _fetch_single_city(
    *,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    category: str,
    city_name: str,
    lat: float,
    lon: float,
    api_key: str,
) -> list[Place]:
    params = {
        "categories": category,
        "filter": f"circle:{lon},{lat},20000",
        "limit": LIMIT_PER_REQUEST,
        "apiKey": api_key,
    }

    async with semaphore:
        try:
            async with session.get(settings.geoapify_url or BASE_URL, params=params) as response:
                if response.status != status.HTTP_200_OK:
                    return []
                data = await response.json()
        except ClientResponseError as e:
            logger.warning("Geoapify request error: %s", e)
            return []
        except Exception as e:
            logger.warning("Geoapify unexpected error: %s", e)
            return []

    result: list[Place] = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        place_id = props.get("place_id")
        place_name = props.get("name")
        place_street = props.get("street") or "None"
        place_housenumber = props.get("housenumber") or "None"

        address = f"{place_street} {place_housenumber}".strip()

        if not place_name or not place_id:
            continue

        name = str(place_name).strip()
        if not name or name.isdigit():
            continue

        result.append(
            Place(
                name=name,
                category=CATEGORY_MAP.get(category) or category,
                address=address,
                city=city_name,
                description=None,
            )
        )

    return result


async def fetch_all_places() -> list[Place]:
    api_key = (settings.geoapify_key or "").strip()
    if not api_key:
        logger.warning("Geoapify API key not configured; skipping import")
        return []

    semaphore = asyncio.Semaphore(25)

    connector = aiohttp.TCPConnector(limit=50)
    timeout = aiohttp.ClientTimeout(total=60)

    all_places: list[Place] = []

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for category in CATEGORIES:
            tasks = [
                _fetch_single_city(
                    session=session,
                    semaphore=semaphore,
                    category=category,
                    city_name=city_name,
                    lat=lat,
                    lon=lon,
                    api_key=api_key,
                )
                for city_name, (lat, lon) in CITIES.items()
            ]

            for chunk in asyncio.as_completed(tasks):
                all_places.extend(await chunk)

    logger.info("Geoapify fetched %s places", len(all_places))
    return all_places


async def import_places_on_startup() -> None:

    db = SessionLocal()
    try:
        cnt = get_places_count(db)
    finally:
        db.close()

    if cnt > 0:
        logger.info("Places already present (%s). Import skipped.", cnt)
        return

    logger.info("No places in DB. Importing from Geoapify...")
    places = await fetch_all_places()
    if not places:
        logger.warning("No places fetched. Import skipped.")
        return

    inserted = await insert_places(places)
    logger.info("Places import done. Inserted ~%s rows.", inserted)
