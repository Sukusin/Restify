from __future__ import annotations

import asyncio
import aiohttp
from aiohttp import ClientResponseError
from fastapi import status

from app.models.places import Place

from app.core.config import settings


LIMIT_PER_REQUEST = 300

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
    "leisure.spa": "Спа-салон"
}

CITIES = {
    "Москва" : (55.7558, 37.6176),
    "Санкт-Петербург" : (59.9343, 30.3351),
    "Екатеринбург" : (56.8389, 60.6057),
    "Тольятти" : (53.1959, 50.1001),
    "Уфа" : (54.7388, 55.9721),
    "Самара" : (53.7596, 49.1088),
    "Казань" : (55.8304, 49.0661),
    "Новосибирск" : (55.0381, 82.9058),
    "Тюмень" : (57.1523, 65.5289),
    "Орёл" : (54.5293, 36.2754),
    "Омск" : (54.9887, 73.3686),
    "Липецк" : (52.6045, 39.5953),
    "Саратов" : (51.5333, 46.0068),
    "Кемерово" : (55.3000, 86.0833),
    "Тула" : (54.0000, 37.7500),
    "Пенза" : (53.2000, 45.0000),
    "Воронеж" : (52.0000, 38.0000),
    "Оренбург" : (51.7000, 55.1000),
    "Сызрань" : (53.5000, 49.4000),
    "Йошкар-Ола" : (54.3000, 48.4000),
    "Курск" : (52.7000, 41.4000),
    "Краснодар" : (45.0000, 38.9000),
    "Нижний Новгород" : (56.3268, 44.0060),
    "Химки" : (55.8304, 37.6342),
    "Подольск" : (55.4500, 37.6167),
    "Балашиха" : (55.9106, 37.7344),
    "Люберцы" : (55.7522, 37.6156),
    "Набережные Челны" : (55.7911, 49.1353),
    "Красноярск" : (55.3042, 86.1047),
    "Жуковский" : (55.5953, 38.1191),
    "Владимир" : (56.1290, 40.4077),
    "Брянск" : (53.2431, 34.3635),
    "Смоленск" : (54.7815, 32.0508),
    "Архангельск" : (64.5396, 40.5200),
    "Мурманск" : (68.9705, 33.0745),
    "Чебоксары" : (56.1328, 47.2460),
    "Пермь" : (58.0105, 56.2504),
    "Волгоград" : (48.7080, 44.5133),
    "Ульяновск" : (54.3282, 48.3864),
    "Киров" : (58.6000, 49.6500),
    "Ярославль" : (57.6299, 39.8737),
    "Тверь" : (56.8583, 35.9000),
    "Иваново" : (57.0000, 40.9734),
    "Череповец" : (59.1333, 37.9000),
    "Астрахань" : (46.3490, 48.0430),
    "Ижевск" : (56.8497, 53.2050),
    "Великий Новгород" : (58.5220, 31.2695),
    "Хабаровск" : (48.4820, 135.0840),
    "Владивосток" : (43.1056, 131.8735)
}


async def fetch_places(session : aiohttp.ClientSession, category : str, cities : dict[str, tuple]) -> list:
    places = []

    async def fetch_single(lat : float, lon : float, city_name : str):
        params = {
            "categories": category,
            "filter": f"circle:{lon},{lat},20000",
            "limit": LIMIT_PER_REQUEST,
            "apiKey": settings.geoapify_key
        }

        try:
            async with session.get(settings.geoapify_url, params=params) as response:
                if response.status != status.HTTP_200_OK:
                    return
                data = await response.json()
        except ClientResponseError as e:
            print(f"Ошибка запроса: {e}")
            return

        for feature in data.get("features", []):
            props = feature["properties"]
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

            place = Place(
                name=name,
                category=(CATEGORY_MAP.get(category) or category).strip().lower(),
                address=address,
                city=city_name,
                description=""
            )

            places.append(place)

    tasks = [fetch_single(lat, lon, city_name) for city_name, (lat, lon) in cities.items()]
    await asyncio.gather(*tasks)

    return places


async def parse_places() -> list:
    all_places = []

    async def fetch_category(category: str):
        async with aiohttp.ClientSession() as session:
            result = await fetch_places(session, category, CITIES)
            all_places.extend(result)

    tasks = [fetch_category(category) for category in CATEGORY_MAP.keys()]
    await asyncio.gather(*tasks)

    print(f"Найдено {len(all_places)} мест:")

    return all_places