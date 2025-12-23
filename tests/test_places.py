from app.models.places import Place


def _seed_places(db):
    db.add_all(
        [
            Place(name="Cafe Alpha", category="Кафе", city="Москва", address="Tverskaya 1", avg_rating=4.7, reviews_count=12),
            Place(name="Cafe Beta", category="Кафе", city="Москва", address="Arbat 2", avg_rating=4.1, reviews_count=5),
            Place(name="Cinema One", category="Кинотеатр", city="Москва", address="Lenina 3", avg_rating=4.9, reviews_count=2),
            Place(name="Park Green", category="Парк культуры и отдыха", city="Казань", address="Park 10", avg_rating=4.8, reviews_count=7),
        ]
    )
    db.commit()


def test_places_filter_city_and_min_rating(client, db):
    _seed_places(db)

    r = client.get("/places", params={"city": "Москва", "min_rating": 4.5, "limit": 100, "offset": 0})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2  # Cafe Alpha + Cinema One
    names = [x["name"] for x in body["items"]]
    assert "Cafe Alpha" in names
    assert "Cinema One" in names
    assert "Cafe Beta" not in names


def test_places_search_and_pagination(client, db):
    _seed_places(db)

    # search "cafe" should match 2 items in Moscow
    r1 = client.get("/places", params={"q": "cafe", "limit": 1, "offset": 0})
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["total"] >= 2
    assert len(body1["items"]) == 1

    r2 = client.get("/places", params={"q": "cafe", "limit": 1, "offset": 1})
    body2 = r2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["id"] != body1["items"][0]["id"]
