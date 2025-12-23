from app.models.places import Place


def _register_get_token(client, email="chat@example.com"):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def test_chat_grounding_returns_db_candidates(client, db):
    # Seed several places; order should be by avg_rating desc, then reviews_count desc
    db.add_all(
        [
            Place(name="Cafe A", category="Кафе", city="Москва", address="Addr A", avg_rating=4.9, reviews_count=1),
            Place(name="Cafe B", category="Кафе", city="Москва", address="Addr B", avg_rating=4.5, reviews_count=10),
            Place(name="Cafe C", category="Кафе", city="Москва", address="Addr C", avg_rating=4.5, reviews_count=2),
            Place(name="Cafe D", category="Кафе", city="Казань", address="Addr D", avg_rating=5.0, reviews_count=99),
        ]
    )
    db.commit()

    token = _register_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"message": "Хочу уютное кафе", "city": "Москва", "category": "Кафе", "limit_places": 2}
    r = client.post("/chat", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()

    assert "reply" in body
    assert len(body["places"]) == 2

    # Top-2 for Moscow cafes: Cafe A (4.9) then Cafe B (4.5, reviews=10) over Cafe C (4.5, reviews=2)
    names = [p["name"] for p in body["places"]]
    assert names == ["Cafe A", "Cafe B"]
