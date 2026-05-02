import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from src.models.bill import Bill, BillItem


def _today() -> date:
    return datetime.now(UTC).date()


async def _register(
    client: AsyncClient, *, email: str, username: str
) -> dict[str, Any]:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "passw0rd!", "username": username, "name": username},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return {
        "headers": {"Authorization": f"Bearer {body['token']}"},
        "user_id": body["user"]["id"],
        "username": username,
    }


async def _seed_bill(
    *,
    user_id: str,
    merchant: str | None = None,
    total: float,
    billed_at: date | None = None,
    items: list[dict[str, Any]] | None = None,
) -> tuple[uuid.UUID, list[uuid.UUID]]:
    """Seed a reviewed bill directly for the user; return bill_id + ordered item_ids."""
    from src.main import app

    sessionmaker = app.state.sessionmaker
    bill_id = uuid.uuid4()
    item_ids: list[uuid.UUID] = []
    async with sessionmaker() as s:
        s.add(
            Bill(
                id=bill_id,
                user_id=uuid.UUID(user_id),
                image_path=f"users/{user_id}/bills/{bill_id}.jpg",
                content_hash="x" * 64,
                mime_type="image/jpeg",
                byte_size=1,
                status="reviewed",
                merchant=merchant,
                total=Decimal(str(total)),
                currency="USD",
                billed_at=billed_at or _today(),
            )
        )
        await s.flush()
        for i, it in enumerate(items or []):
            item = BillItem(
                bill_id=bill_id,
                position=i,
                name=it["name"],
                category=it.get("category"),
                total_price=(
                    Decimal(str(it["total_price"]))
                    if it.get("total_price") is not None
                    else None
                ),
            )
            s.add(item)
            await s.flush()
            item_ids.append(item.id)
        await s.commit()
    return bill_id, item_ids


# ---------- user lookup ----------


async def test_get_user_by_username(client: AsyncClient, auth: dict[str, object]) -> None:
    r = await client.get("/users/by-username/testuser", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["username"] == "testuser"


async def test_get_user_by_unknown_username_404(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get("/users/by-username/ghost", headers=auth["headers"])
    assert r.status_code == 404


# ---------- create split requests ----------


async def test_create_split_with_items_records_per_item_shares(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        merchant="Diner",
        total=1600.0,
        items=[{"name": "Burger", "category": "food", "total_price": 1600.0}],
    )

    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["items"]) == 1
    sr = body["items"][0]
    assert sr["amount"] == pytest.approx(800.0)
    assert sr["status"] == "pending"
    assert sr["to_username"] == "bob"


async def test_create_split_invalid_item_id_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    await _register(client, email="bob@example.com", username="bob")
    bill_id, _ = await _seed_bill(
        user_id=str(auth["user_id"]), total=100.0, items=[{"name": "X", "total_price": 100.0}]
    )
    other_item = str(uuid.uuid4())
    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [other_item]},
        headers=auth["headers"],
    )
    assert r.status_code == 422


async def test_create_split_unpriced_item_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        total=100.0,
        items=[{"name": "X", "total_price": None}],
    )
    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )
    assert r.status_code == 422


async def test_create_split_without_items_falls_back_to_total(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    await _register(client, email="bob@example.com", username="bob")
    bill_id, _ = await _seed_bill(user_id=str(auth["user_id"]), total=300.0)
    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"]},
        headers=auth["headers"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["items"][0]["amount"] == pytest.approx(150.0)


async def test_split_with_self_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    bill_id, _ = await _seed_bill(user_id=str(auth["user_id"]), total=10.0)
    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["testuser"]},
        headers=auth["headers"],
    )
    assert r.status_code == 422


async def test_split_other_users_bill_404(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, _ = await _seed_bill(user_id=bob["user_id"], total=10.0)
    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"]},
        headers=auth["headers"],
    )
    assert r.status_code == 404


# ---------- accept / reject ----------


async def test_accept_request_and_balances(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        total=100.0,
        items=[{"name": "Pizza", "total_price": 100.0}],
    )
    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )
    sr_id = r.json()["items"][0]["id"]

    # Bob sees it incoming, accepts
    r2 = await client.get("/split-requests/incoming", headers=bob["headers"])
    assert r2.status_code == 200 and len(r2.json()["items"]) == 1
    r3 = await client.post(
        f"/split-requests/{sr_id}/accept", headers=bob["headers"]
    )
    assert r3.status_code == 200 and r3.json()["status"] == "accepted"

    # Balances: bob owes alice 50, alice is owed 50
    bal_alice = await client.get("/balances", headers=auth["headers"])
    assert bal_alice.json()["balances"][0]["net"] == pytest.approx(50.0)
    bal_bob = await client.get("/balances", headers=bob["headers"])
    assert bal_bob.json()["balances"][0]["net"] == pytest.approx(-50.0)


async def test_reject_does_not_affect_balances(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        total=100.0,
        items=[{"name": "X", "total_price": 100.0}],
    )
    r = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )
    sr_id = r.json()["items"][0]["id"]
    await client.post(f"/split-requests/{sr_id}/reject", headers=bob["headers"])
    bal = await client.get("/balances", headers=auth["headers"])
    assert bal.json() == {"balances": []}


# ---------- INSIGHTS: per-item adjustment for both parties ----------


async def test_owner_insights_adjusted_after_accept(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    """userA's per-item view halves after split is accepted."""
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        merchant="Diner",
        total=1600.0,
        items=[{"name": "Burger", "category": "food", "total_price": 1600.0}],
    )
    # Before split: Burger shows full 1600
    r0 = await client.get("/insights/items", headers=auth["headers"])
    rows0 = r0.json()["rows"]
    assert rows0[0]["name"] == "Burger"
    assert rows0[0]["total_spend"] == pytest.approx(1600.0)

    # Split with bob, bob accepts
    sr = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )
    sr_id = sr.json()["items"][0]["id"]
    await client.post(f"/split-requests/{sr_id}/accept", headers=bob["headers"])

    # After split: Burger now shows 800 for Alice
    r1 = await client.get("/insights/items", headers=auth["headers"])
    burger = next(r for r in r1.json()["rows"] if r["normalized_name"] == "burger")
    assert burger["total_spend"] == pytest.approx(800.0)

    # Overview total also halved
    o = await client.get("/insights/overview", headers=auth["headers"])
    assert o.json()["total_spend"] == pytest.approx(800.0)

    # Category breakdown reflects the share
    bd = await client.get(
        "/insights/breakdown?dimension=category", headers=auth["headers"]
    )
    assert bd.json()["rows"][0]["total"] == pytest.approx(800.0)


async def test_recipient_insights_show_shared_items(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    """userB's dashboard surfaces accepted shared items + their share amount."""
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        merchant="Diner",
        total=1600.0,
        items=[{"name": "Burger", "category": "food", "total_price": 1600.0}],
    )

    # Bob's dashboard is empty initially
    r0 = await client.get("/insights/overview", headers=bob["headers"])
    assert r0.json()["total_spend"] == 0
    r0i = await client.get("/insights/items", headers=bob["headers"])
    assert r0i.json()["rows"] == []

    sr = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )
    sr_id = sr.json()["items"][0]["id"]
    await client.post(f"/split-requests/{sr_id}/accept", headers=bob["headers"])

    # Bob's overview now shows 800
    r1 = await client.get("/insights/overview", headers=bob["headers"])
    assert r1.json()["total_spend"] == pytest.approx(800.0)
    assert r1.json()["bill_count"] == 1

    # Bob sees the burger at his share
    r1i = await client.get("/insights/items", headers=bob["headers"])
    rows = r1i.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["normalized_name"] == "burger"
    assert rows[0]["total_spend"] == pytest.approx(800.0)

    # Bob's category and merchant breakdowns reflect it
    bd_cat = await client.get(
        "/insights/breakdown?dimension=category", headers=bob["headers"]
    )
    assert bd_cat.json()["rows"][0]["label"] == "food"
    assert bd_cat.json()["rows"][0]["total"] == pytest.approx(800.0)

    bd_mer = await client.get(
        "/insights/breakdown?dimension=merchant", headers=bob["headers"]
    )
    assert bd_mer.json()["rows"][0]["label"] == "Diner"
    assert bd_mer.json()["rows"][0]["total"] == pytest.approx(800.0)


async def test_pending_request_does_not_affect_insights(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    """While the request is pending, neither user's insights change."""
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        total=200.0,
        items=[{"name": "Pizza", "total_price": 200.0}],
    )
    await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )

    a = await client.get("/insights/overview", headers=auth["headers"])
    assert a.json()["total_spend"] == pytest.approx(200.0)
    b = await client.get("/insights/overview", headers=bob["headers"])
    assert b.json()["total_spend"] == 0


async def test_partial_item_split_leaves_unchecked_items_intact(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    """When user splits only burger, fries spend stays untouched for owner."""
    bob = await _register(client, email="bob@example.com", username="bob")
    bill_id, item_ids = await _seed_bill(
        user_id=str(auth["user_id"]),
        total=1600.0,
        items=[
            {"name": "Burger", "category": "food", "total_price": 1000.0},
            {"name": "Fries", "category": "food", "total_price": 600.0},
        ],
    )
    sr = await client.post(
        f"/bills/{bill_id}/split-requests",
        json={"usernames": ["bob"], "bill_item_ids": [str(item_ids[0])]},
        headers=auth["headers"],
    )
    sr_id = sr.json()["items"][0]["id"]
    await client.post(f"/split-requests/{sr_id}/accept", headers=bob["headers"])

    r = await client.get("/insights/items", headers=auth["headers"])
    rows = {row["normalized_name"]: row["total_spend"] for row in r.json()["rows"]}
    assert rows["burger"] == pytest.approx(500.0)
    assert rows["fries"] == pytest.approx(600.0)

    # Bob only sees burger
    rb = await client.get("/insights/items", headers=bob["headers"])
    rb_rows = {row["normalized_name"] for row in rb.json()["rows"]}
    assert rb_rows == {"burger"}
