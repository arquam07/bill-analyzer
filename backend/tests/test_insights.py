import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from src.models.bill import Bill, BillItem


def _today() -> date:
    return datetime.now(UTC).date()


async def _seed_bill(
    *,
    user_id: str,
    billed_at: date | None,
    merchant: str | None = None,
    total: float | None = None,
    status: str = "reviewed",
    items: list[dict[str, Any]] | None = None,
) -> uuid.UUID:
    from src.main import app

    sessionmaker = app.state.sessionmaker
    bill_id = uuid.uuid4()
    async with sessionmaker() as s:
        s.add(
            Bill(
                id=bill_id,
                user_id=uuid.UUID(user_id),
                image_path=f"users/{user_id}/bills/{bill_id}.jpg",
                content_hash="x" * 64,
                mime_type="image/jpeg",
                byte_size=1,
                status=status,
                merchant=merchant,
                total=Decimal(str(total)) if total is not None else None,
                currency="USD",
                billed_at=billed_at,
            )
        )
        await s.flush()
        for i, it in enumerate(items or []):
            s.add(
                BillItem(
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
            )
        await s.commit()
    return bill_id


# ---------- auth ----------


async def test_overview_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/insights/overview")
    assert r.status_code == 401


async def test_timeseries_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/insights/timeseries")
    assert r.status_code == 401


# ---------- empty state ----------


async def test_overview_empty_user_returns_zeros(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get("/insights/overview", headers=auth["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["total_spend"] == 0
    assert body["bill_count"] == 0
    assert body["avg_bill"] == 0
    assert body["top_category"] is None
    assert body["top_merchant"] is None
    assert body["prev_total_spend"] == 0
    assert body["spend_delta_pct"] is None


async def test_timeseries_empty_user_returns_no_points(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get("/insights/timeseries", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["points"] == []


# ---------- aggregation ----------


async def test_overview_aggregates_reviewed_bills_in_range(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today - timedelta(days=10), total=10.0)
    await _seed_bill(user_id=uid, billed_at=today - timedelta(days=5), total=25.50)
    await _seed_bill(user_id=uid, billed_at=today, total=4.50)

    r = await client.get("/insights/overview", headers=auth["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["total_spend"] == pytest.approx(40.0)
    assert body["bill_count"] == 3
    assert body["avg_bill"] == pytest.approx(40.0 / 3)


async def test_overview_excludes_unreviewed_bills(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=100.0, status="reviewed")
    await _seed_bill(user_id=uid, billed_at=today, total=999.0, status="extracted")
    await _seed_bill(user_id=uid, billed_at=today, total=999.0, status="uploaded")

    body = (await client.get("/insights/overview", headers=auth["headers"])).json()
    assert body["total_spend"] == pytest.approx(100.0)
    assert body["bill_count"] == 1


async def test_overview_excludes_bills_without_billed_at(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=10.0)
    await _seed_bill(user_id=uid, billed_at=None, total=999.0)

    body = (await client.get("/insights/overview", headers=auth["headers"])).json()
    assert body["total_spend"] == pytest.approx(10.0)
    assert body["bill_count"] == 1


async def test_overview_excludes_other_users_bills(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=10.0)

    other = await client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "passw0rd!", "username": "otheruser", "name": "O"},
    )
    other_uid = other.json()["user"]["id"]
    await _seed_bill(user_id=other_uid, billed_at=today, total=999.0)

    body = (await client.get("/insights/overview", headers=auth["headers"])).json()
    assert body["total_spend"] == pytest.approx(10.0)


async def test_overview_respects_explicit_range(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today - timedelta(days=2), total=5.0)
    await _seed_bill(user_id=uid, billed_at=today - timedelta(days=20), total=100.0)

    rf = (today - timedelta(days=7)).isoformat()
    rt = today.isoformat()
    body = (
        await client.get(f"/insights/overview?from={rf}&to={rt}", headers=auth["headers"])
    ).json()
    assert body["total_spend"] == pytest.approx(5.0)
    assert body["bill_count"] == 1


# ---------- top category / merchant ----------


async def test_overview_top_merchant_by_spend(client: AsyncClient, auth: dict[str, object]) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, merchant="Walmart", total=10.0)
    await _seed_bill(user_id=uid, billed_at=today, merchant="Walmart", total=10.0)
    await _seed_bill(user_id=uid, billed_at=today, merchant="Costco", total=15.0)

    body = (await client.get("/insights/overview", headers=auth["headers"])).json()
    assert body["top_merchant"] == "Walmart"


async def test_overview_top_category_by_item_total(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        total=20.0,
        items=[
            {"name": "Milk", "category": "Groceries", "total_price": 3.0},
            {"name": "Pen", "category": "Office", "total_price": 17.0},
        ],
    )
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        total=10.0,
        items=[
            {"name": "Bread", "category": "Groceries", "total_price": 10.0},
        ],
    )

    body = (await client.get("/insights/overview", headers=auth["headers"])).json()
    # Groceries: 3 + 10 = 13; Office: 17 -> Office wins on item-total
    assert body["top_category"] == "Office"


# ---------- prev window delta ----------


async def test_overview_delta_compares_to_prior_equivalent_window(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    # current window: last 30 days, total = 200
    await _seed_bill(user_id=uid, billed_at=today, total=200.0)
    # prev window (days -31..-60): total = 100 -> +100% delta
    await _seed_bill(user_id=uid, billed_at=today - timedelta(days=45), total=100.0)

    rf = (today - timedelta(days=30)).isoformat()
    rt = today.isoformat()
    body = (
        await client.get(f"/insights/overview?from={rf}&to={rt}", headers=auth["headers"])
    ).json()
    assert body["total_spend"] == pytest.approx(200.0)
    assert body["prev_total_spend"] == pytest.approx(100.0)
    assert body["spend_delta_pct"] == pytest.approx(100.0)


async def test_overview_delta_is_null_when_prev_window_empty(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=50.0)

    rf = (today - timedelta(days=7)).isoformat()
    rt = today.isoformat()
    body = (
        await client.get(f"/insights/overview?from={rf}&to={rt}", headers=auth["headers"])
    ).json()
    assert body["spend_delta_pct"] is None


# ---------- range validation ----------


async def test_overview_inverted_range_returns_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get(
        "/insights/overview?from=2026-05-01&to=2026-04-01", headers=auth["headers"]
    )
    assert r.status_code == 422


async def test_overview_range_over_12_months_returns_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    today = _today()
    rf = (today - timedelta(days=400)).isoformat()
    rt = today.isoformat()
    r = await client.get(f"/insights/overview?from={rf}&to={rt}", headers=auth["headers"])
    assert r.status_code == 422


# ---------- timeseries ----------


async def test_timeseries_groups_by_month(client: AsyncClient, auth: dict[str, object]) -> None:
    uid = str(auth["user_id"])
    today = _today()
    # Two bills in the same month, one in a different month
    await _seed_bill(user_id=uid, billed_at=date(today.year, today.month, 1), total=5.0)
    await _seed_bill(user_id=uid, billed_at=date(today.year, today.month, 2), total=3.0)
    prev_month_start = date(today.year, today.month, 1) - timedelta(days=1)
    prev_month_first = prev_month_start.replace(day=1)
    await _seed_bill(user_id=uid, billed_at=prev_month_first, total=10.0)

    rf = (prev_month_first - timedelta(days=1)).isoformat()
    rt = today.isoformat()
    r = await client.get(
        f"/insights/timeseries?from={rf}&to={rt}&granularity=month",
        headers=auth["headers"],
    )
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) == 2
    by_period = {p["period"]: p for p in points}
    current_key = date(today.year, today.month, 1).isoformat()
    prev_key = prev_month_first.isoformat()
    assert by_period[current_key]["total"] == pytest.approx(8.0)
    assert by_period[current_key]["count"] == 2
    assert by_period[prev_key]["total"] == pytest.approx(10.0)
    assert by_period[prev_key]["count"] == 1


async def test_timeseries_groups_by_day(client: AsyncClient, auth: dict[str, object]) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=5.0)
    await _seed_bill(user_id=uid, billed_at=today, total=2.5)
    await _seed_bill(user_id=uid, billed_at=today - timedelta(days=1), total=10.0)

    rf = (today - timedelta(days=2)).isoformat()
    rt = today.isoformat()
    r = await client.get(
        f"/insights/timeseries?from={rf}&to={rt}&granularity=day",
        headers=auth["headers"],
    )
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) == 2
    by_period = {p["period"]: p for p in points}
    assert by_period[today.isoformat()]["total"] == pytest.approx(7.5)
    assert by_period[today.isoformat()]["count"] == 2
    yesterday_key = (today - timedelta(days=1)).isoformat()
    assert by_period[yesterday_key]["total"] == pytest.approx(10.0)


async def test_timeseries_groups_by_week(client: AsyncClient, auth: dict[str, object]) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=5.0)
    await _seed_bill(user_id=uid, billed_at=today - timedelta(days=14), total=10.0)

    rf = (today - timedelta(days=20)).isoformat()
    rt = today.isoformat()
    r = await client.get(
        f"/insights/timeseries?from={rf}&to={rt}&granularity=week",
        headers=auth["headers"],
    )
    assert r.status_code == 200
    points = r.json()["points"]
    # Two bills 14 days apart land in different ISO weeks
    assert len(points) == 2


async def test_timeseries_excludes_bills_without_billed_at(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=5.0)
    await _seed_bill(user_id=uid, billed_at=None, total=999.0)

    r = await client.get("/insights/timeseries?granularity=day", headers=auth["headers"])
    body = r.json()
    assert sum(p["count"] for p in body["points"]) == 1
    assert sum(p["total"] for p in body["points"]) == pytest.approx(5.0)


async def test_timeseries_invalid_granularity_returns_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get("/insights/timeseries?granularity=year", headers=auth["headers"])
    assert r.status_code == 422


async def test_timeseries_inverted_range_returns_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get(
        "/insights/timeseries?from=2026-05-01&to=2026-04-01",
        headers=auth["headers"],
    )
    assert r.status_code == 422


# ---------- breakdown ----------


async def test_breakdown_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/insights/breakdown?dimension=category")
    assert r.status_code == 401


async def test_breakdown_requires_dimension(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get("/insights/breakdown", headers=auth["headers"])
    assert r.status_code == 422


async def test_breakdown_by_category_sums_item_totals(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        items=[
            {"name": "Milk", "category": "Groceries", "total_price": 3.0},
            {"name": "Pen", "category": "Office", "total_price": 17.0},
        ],
    )
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        items=[
            {"name": "Bread", "category": "Groceries", "total_price": 10.0},
            {"name": "Uncategorized item", "category": None, "total_price": 99.0},
        ],
    )
    r = await client.get(
        "/insights/breakdown?dimension=category", headers=auth["headers"]
    )
    assert r.status_code == 200
    rows = r.json()["rows"]
    by_label = {row["label"]: row for row in rows}
    assert by_label["Office"]["total"] == pytest.approx(17.0)
    assert by_label["Groceries"]["total"] == pytest.approx(13.0)
    assert "Uncategorized item" not in by_label  # null category filtered
    # ordered by total desc
    assert rows[0]["label"] == "Office"


async def test_breakdown_by_merchant_sums_bill_totals(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, merchant="Walmart", total=10.0)
    await _seed_bill(user_id=uid, billed_at=today, merchant="Walmart", total=15.0)
    await _seed_bill(user_id=uid, billed_at=today, merchant="Costco", total=20.0)
    await _seed_bill(user_id=uid, billed_at=today, merchant=None, total=999.0)

    r = await client.get(
        "/insights/breakdown?dimension=merchant", headers=auth["headers"]
    )
    rows = r.json()["rows"]
    assert len(rows) == 2  # null merchant excluded
    assert rows[0]["label"] == "Walmart"
    assert rows[0]["total"] == pytest.approx(25.0)
    assert rows[0]["count"] == 2


async def test_breakdown_excludes_unreviewed(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, merchant="A", total=10.0)
    await _seed_bill(
        user_id=uid, billed_at=today, merchant="B", total=999.0, status="extracted"
    )
    rows = (
        await client.get(
            "/insights/breakdown?dimension=merchant", headers=auth["headers"]
        )
    ).json()["rows"]
    labels = [r["label"] for r in rows]
    assert labels == ["A"]


async def test_breakdown_respects_limit(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    for i in range(5):
        await _seed_bill(user_id=uid, billed_at=today, merchant=f"M{i}", total=float(i + 1))
    rows = (
        await client.get(
            "/insights/breakdown?dimension=merchant&limit=2", headers=auth["headers"]
        )
    ).json()["rows"]
    assert len(rows) == 2


# ---------- top items ----------


async def test_items_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/insights/items")
    assert r.status_code == 401


async def test_items_groups_by_normalized_name(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        items=[
            {"name": "Milk", "total_price": 3.0},
            {"name": "MILK", "total_price": 4.0},  # case variant
            {"name": "  milk  ", "total_price": 5.0},  # whitespace variant
            {"name": "Bread", "total_price": 6.0},
        ],
    )
    rows = (
        await client.get("/insights/items", headers=auth["headers"])
    ).json()["rows"]
    by_norm = {r["normalized_name"]: r for r in rows}
    assert by_norm["milk"]["total_spend"] == pytest.approx(12.0)
    assert by_norm["milk"]["purchase_count"] == 3
    assert by_norm["bread"]["total_spend"] == pytest.approx(6.0)


async def test_items_default_orders_by_spend(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        items=[
            {"name": "Cheap thing", "total_price": 1.0},
            {"name": "Cheap thing", "total_price": 1.0},
            {"name": "Cheap thing", "total_price": 1.0},  # 3 cheap = 3 total
            {"name": "Expensive thing", "total_price": 100.0},  # 1 = 100
        ],
    )
    rows = (
        await client.get("/insights/items", headers=auth["headers"])
    ).json()["rows"]
    assert rows[0]["normalized_name"] == "expensive thing"


async def test_items_order_by_frequency(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        items=[
            {"name": "Cheap thing", "total_price": 1.0},
            {"name": "Cheap thing", "total_price": 1.0},
            {"name": "Cheap thing", "total_price": 1.0},
            {"name": "Expensive thing", "total_price": 100.0},
        ],
    )
    rows = (
        await client.get(
            "/insights/items?order_by=frequency", headers=auth["headers"]
        )
    ).json()["rows"]
    assert rows[0]["normalized_name"] == "cheap thing"


async def test_items_last_purchased_is_max_billed_at(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today - timedelta(days=10),
        items=[{"name": "Milk", "total_price": 3.0}],
    )
    await _seed_bill(
        user_id=uid,
        billed_at=today - timedelta(days=2),
        items=[{"name": "Milk", "total_price": 4.0}],
    )
    rows = (
        await client.get("/insights/items", headers=auth["headers"])
    ).json()["rows"]
    milk = next(r for r in rows if r["normalized_name"] == "milk")
    assert milk["last_purchased"] == (today - timedelta(days=2)).isoformat()


async def test_items_excludes_other_users(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid, billed_at=today, items=[{"name": "Milk", "total_price": 1.0}]
    )

    other = await client.post(
        "/auth/register",
        json={"email": "x@y.com", "password": "passw0rd!", "username": "xuser", "name": "X"},
    )
    other_uid = other.json()["user"]["id"]
    await _seed_bill(
        user_id=other_uid,
        billed_at=today,
        items=[{"name": "Milk", "total_price": 999.0}],
    )

    rows = (
        await client.get("/insights/items", headers=auth["headers"])
    ).json()["rows"]
    milk = next(r for r in rows if r["normalized_name"] == "milk")
    assert milk["total_spend"] == pytest.approx(1.0)


async def test_items_excludes_unreviewed_bills(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        status="extracted",
        items=[{"name": "Milk", "total_price": 999.0}],
    )
    rows = (
        await client.get("/insights/items", headers=auth["headers"])
    ).json()["rows"]
    assert rows == []


async def test_items_inverted_range_returns_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get(
        "/insights/items?from=2026-05-01&to=2026-04-01", headers=auth["headers"]
    )
    assert r.status_code == 422


# ---------- bills_missing_date ----------


async def test_overview_bills_missing_date_counts_reviewed_without_billed_at(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=10.0)  # has date — not counted
    await _seed_bill(user_id=uid, billed_at=None, total=5.0, status="reviewed")  # counted
    await _seed_bill(user_id=uid, billed_at=None, total=5.0, status="extracted")  # not reviewed — ignored

    body = (await client.get("/insights/overview", headers=auth["headers"])).json()
    assert body["bills_missing_date"] == 1


async def test_overview_bills_missing_date_zero_when_all_have_date(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(user_id=uid, billed_at=today, total=10.0)

    body = (await client.get("/insights/overview", headers=auth["headers"])).json()
    assert body["bills_missing_date"] == 0


# ---------- item timeseries ----------


async def test_item_timeseries_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/insights/items/milk/timeseries")
    assert r.status_code == 401


async def test_item_timeseries_returns_points_for_normalized_name(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    prev_month = date(today.year, today.month, 1) - timedelta(days=1)
    prev_month_first = prev_month.replace(day=1)

    await _seed_bill(
        user_id=uid,
        billed_at=date(today.year, today.month, 1),
        items=[{"name": "Milk", "total_price": 3.0}],
    )
    await _seed_bill(
        user_id=uid,
        billed_at=prev_month_first,
        items=[{"name": "MILK", "total_price": 4.0}],
    )
    # Bread should not appear
    await _seed_bill(
        user_id=uid,
        billed_at=today,
        items=[{"name": "Bread", "total_price": 99.0}],
    )

    rf = (prev_month_first - timedelta(days=1)).isoformat()
    rt = today.isoformat()
    r = await client.get(
        f"/insights/items/milk/timeseries?from={rf}&to={rt}&granularity=month",
        headers=auth["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["normalized_name"] == "milk"
    assert body["total_spend"] == pytest.approx(7.0)
    assert body["purchase_count"] == 2
    assert len(body["points"]) == 2


async def test_item_timeseries_empty_when_item_not_in_range(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid,
        billed_at=today - timedelta(days=200),
        items=[{"name": "Milk", "total_price": 5.0}],
    )

    rf = (today - timedelta(days=30)).isoformat()
    rt = today.isoformat()
    r = await client.get(
        f"/insights/items/milk/timeseries?from={rf}&to={rt}&granularity=day",
        headers=auth["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_spend"] == pytest.approx(0.0)
    assert body["purchase_count"] == 0
    assert body["points"] == []


async def test_item_timeseries_excludes_other_users(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    uid = str(auth["user_id"])
    today = _today()
    await _seed_bill(
        user_id=uid, billed_at=today, items=[{"name": "Milk", "total_price": 1.0}]
    )

    other = await client.post(
        "/auth/register",
        json={"email": "itemts@y.com", "password": "passw0rd!", "username": "itemtsuser", "name": "X"},
    )
    other_uid = other.json()["user"]["id"]
    await _seed_bill(
        user_id=other_uid, billed_at=today, items=[{"name": "Milk", "total_price": 999.0}]
    )

    body = (
        await client.get("/insights/items/milk/timeseries", headers=auth["headers"])
    ).json()
    assert body["total_spend"] == pytest.approx(1.0)


async def test_item_timeseries_inverted_range_returns_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get(
        "/insights/items/milk/timeseries?from=2026-05-01&to=2026-04-01",
        headers=auth["headers"],
    )
    assert r.status_code == 422
