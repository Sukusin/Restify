from app.core.rate_limit import _reset_for_tests


def test_register_and_me(client):
    r = client.post("/auth/register", json={"email": "u1@example.com", "password": "password123"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    assert token

    r2 = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["email"] == "u1@example.com"
    assert body["is_active"] is True


def test_register_duplicate_email_409(client):
    r1 = client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert r1.status_code == 201

    r2 = client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert r2.status_code == 409


def test_login_invalid_credentials_401(client):
    r = client.post("/auth/token", data={"username": "nope@example.com", "password": "password123"})
    assert r.status_code == 401


def test_login_success(client):
    client.post("/auth/register", json={"email": "u2@example.com", "password": "password123"})
    r = client.post("/auth/token", data={"username": "u2@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_rate_limit_on_login(client):
    _reset_for_tests()

    for i in range(10):
        r = client.post("/auth/token", data={"username": "x@example.com", "password": "wrongpass"})
        assert r.status_code in (401, 200)

    r = client.post("/auth/token", data={"username": "x@example.com", "password": "wrongpass"})
    assert r.status_code == 429, r.text
    assert "Retry-After" in r.headers
