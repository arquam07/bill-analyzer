from httpx import AsyncClient


async def test_register_creates_user_and_returns_token(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "passw0rd!", "name": "Alice"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["name"] == "Alice"
    assert "id" in body["user"]
    assert isinstance(body["token"], str) and len(body["token"]) > 20


async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "passw0rd!"}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 409


async def test_register_normalizes_email_case(client: AsyncClient) -> None:
    r1 = await client.post(
        "/auth/register", json={"email": "Mixed@Example.com", "password": "passw0rd!"}
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/auth/register", json={"email": "mixed@example.com", "password": "passw0rd!"}
    )
    assert r2.status_code == 409


async def test_register_short_password_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "short"}
    )
    assert r.status_code == 422


async def test_login_with_valid_credentials_returns_token(client: AsyncClient) -> None:
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "passw0rd!"}
    )
    r = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "passw0rd!"}
    )
    assert r.status_code == 200
    assert "token" in r.json()


async def test_login_with_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "passw0rd!"}
    )
    r = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong"}
    )
    assert r.status_code == 401


async def test_login_with_unknown_email_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "passw0rd!"}
    )
    assert r.status_code == 401


async def test_me_with_valid_token_returns_user(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "passw0rd!", "name": "Alice"},
    )
    token = r.json()["token"]
    me = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"
    assert me.json()["name"] == "Alice"


async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/me")
    assert r.status_code == 401


async def test_me_with_invalid_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


async def test_logout_invalidates_token(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "passw0rd!"}
    )
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/me", headers=headers)).status_code == 200
    assert (await client.post("/auth/logout", headers=headers)).status_code == 204
    assert (await client.get("/me", headers=headers)).status_code == 401


async def test_logout_one_session_does_not_affect_other(client: AsyncClient) -> None:
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "passw0rd!"}
    )
    t1 = (
        await client.post(
            "/auth/login", json={"email": "alice@example.com", "password": "passw0rd!"}
        )
    ).json()["token"]
    t2 = (
        await client.post(
            "/auth/login", json={"email": "alice@example.com", "password": "passw0rd!"}
        )
    ).json()["token"]
    assert t1 != t2
    await client.post("/auth/logout", headers={"Authorization": f"Bearer {t1}"})
    me = await client.get("/me", headers={"Authorization": f"Bearer {t2}"})
    assert me.status_code == 200
