from io import BytesIO
from typing import Any

import pytest
from httpx import AsyncClient
from PIL import Image

from src.api.deps import get_vision_service
from src.schemas.extraction import LineItem, RawBillExtraction


def _jpeg() -> bytes:
    img = Image.new("RGB", (60, 60), color="white")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture
def jpeg() -> bytes:
    return _jpeg()


class _FakeVision:
    def __init__(self, result: RawBillExtraction) -> None:
        self._result = result

    async def extract_bill(
        self, image_bytes: bytes, *, language: str = "en"
    ) -> RawBillExtraction:
        return self._result


def _override_vision(app: Any, vision: _FakeVision) -> None:
    app.dependency_overrides[get_vision_service] = lambda: vision


async def _upload(client: AsyncClient, headers: dict[str, str], jpeg: bytes) -> str:
    r = await client.post(
        "/bills", headers=headers, files={"image": ("r.jpg", jpeg, "image/jpeg")}
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _extract(
    client: AsyncClient,
    auth: dict[str, object],
    bill_id: str,
    extraction: RawBillExtraction,
) -> dict[str, Any]:
    from src.main import app

    _override_vision(app, _FakeVision(result=extraction))
    try:
        r = await client.post(
            f"/bills/{bill_id}/extract", headers=auth["headers"]
        )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    return r.json()


def _sample_extraction() -> RawBillExtraction:
    return RawBillExtraction(
        merchant="Acme",
        total=12.34,
        currency="USD",
        items=[
            LineItem(name="Milk", quantity=1, unit_price=3.50, total_price=3.50),
            LineItem(name="Bread", quantity=2, unit_price=4.42, total_price=8.84),
        ],
        raw_text="ACME ...",
    )


# ---------- extract persists ----------


async def test_extract_persists_bill_fields_and_items(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())

    assert body["status"] == "extracted"
    assert body["merchant"] == "Acme"
    assert body["total"] == 12.34
    assert body["extracted_at"] is not None
    assert len(body["items"]) == 2
    assert [i["name"] for i in body["items"]] == ["Milk", "Bread"]
    assert [i["position"] for i in body["items"]] == [0, 1]
    # ids assigned
    assert all(i["id"] for i in body["items"])

    # GET reflects same state
    r = await client.get(f"/bills/{bill_id}", headers=auth["headers"])
    assert r.status_code == 200
    got = r.json()
    assert got["status"] == "extracted"
    assert len(got["items"]) == 2


async def test_re_extract_replaces_items(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())

    second = RawBillExtraction(
        merchant="Acme v2",
        total=5.00,
        currency="USD",
        items=[LineItem(name="Coffee", total_price=5.00)],
        raw_text="ACME v2",
    )
    body = await _extract(client, auth, bill_id, second)
    assert body["merchant"] == "Acme v2"
    assert [i["name"] for i in body["items"]] == ["Coffee"]


# ---------- list ----------


async def test_list_bills_paginated(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    ids = [await _upload(client, auth["headers"], jpeg) for _ in range(3)]

    r = await client.get("/bills?limit=2&offset=0", headers=auth["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    # newest first
    assert body["items"][0]["id"] == ids[-1]

    r2 = await client.get("/bills?limit=2&offset=2", headers=auth["headers"])
    assert len(r2.json()["items"]) == 1


async def test_list_bills_only_returns_own(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    await _upload(client, auth["headers"], jpeg)

    other = await client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "passw0rd!", "username": "otheruser"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['token']}"}
    r = await client.get("/bills", headers=other_headers)
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------- get ownership ----------


async def test_get_other_users_bill_returns_404(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    other = await client.post(
        "/auth/register",
        json={"email": "stranger@example.com", "password": "passw0rd!", "username": "stranger"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['token']}"}
    r = await client.get(f"/bills/{bill_id}", headers=other_headers)
    assert r.status_code == 404


# ---------- patch bill ----------


async def test_patch_bill_updates_fields(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())

    r = await client.patch(
        f"/bills/{bill_id}",
        headers=auth["headers"],
        json={"merchant": "Renamed", "total": 99.99},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merchant"] == "Renamed"
    assert body["total"] == 99.99
    # untouched fields preserved
    assert body["currency"] == "USD"


async def test_patch_bill_only_provided_fields(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())

    r = await client.patch(
        f"/bills/{bill_id}", headers=auth["headers"], json={"merchant": "Only Name"}
    )
    body = r.json()
    assert body["merchant"] == "Only Name"
    assert body["total"] == 12.34  # unchanged


# ---------- item add/edit/delete ----------


async def test_add_item_appends_to_end(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())

    r = await client.post(
        f"/bills/{bill_id}/items",
        headers=auth["headers"],
        json={"name": "Tax", "total_price": 1.00, "category": "fees"},
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["items"]) == 3
    assert body["items"][2]["name"] == "Tax"
    assert body["items"][2]["position"] == 2
    assert body["items"][2]["category"] == "fees"


async def test_patch_item_updates_fields(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())
    item_id = body["items"][0]["id"]

    r = await client.patch(
        f"/bills/{bill_id}/items/{item_id}",
        headers=auth["headers"],
        json={"name": "Whole Milk", "total_price": 4.00},
    )
    assert r.status_code == 200
    items = {i["id"]: i for i in r.json()["items"]}
    assert items[item_id]["name"] == "Whole Milk"
    assert items[item_id]["total_price"] == 4.00


async def test_patch_unknown_item_returns_404(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())
    r = await client.patch(
        f"/bills/{bill_id}/items/00000000-0000-0000-0000-000000000000",
        headers=auth["headers"],
        json={"name": "x"},
    )
    assert r.status_code == 404


async def test_delete_item_removes_it(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())
    item_id = body["items"][0]["id"]

    r = await client.delete(
        f"/bills/{bill_id}/items/{item_id}", headers=auth["headers"]
    )
    assert r.status_code == 200
    remaining = [i["id"] for i in r.json()["items"]]
    assert item_id not in remaining
    assert len(remaining) == 1


# ---------- bill.total stays in sync with item totals ----------


async def test_add_item_recomputes_bill_total(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    # Sample extraction items: Milk 3.50 + Bread 8.84 = 12.34
    await _extract(client, auth, bill_id, _sample_extraction())

    r = await client.post(
        f"/bills/{bill_id}/items",
        headers=auth["headers"],
        json={"name": "Apples", "total_price": 5.00},
    )
    assert r.status_code == 201
    # 3.50 + 8.84 + 5.00 = 17.34
    assert r.json()["total"] == 17.34


async def test_update_item_recomputes_bill_total(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())
    milk_id = body["items"][0]["id"]  # 3.50

    r = await client.patch(
        f"/bills/{bill_id}/items/{milk_id}",
        headers=auth["headers"],
        json={"total_price": 4.00},
    )
    assert r.status_code == 200
    # 4.00 + 8.84 = 12.84
    assert r.json()["total"] == 12.84


async def test_delete_item_recomputes_bill_total(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())
    bread_id = body["items"][1]["id"]  # 8.84

    r = await client.delete(
        f"/bills/{bill_id}/items/{bread_id}", headers=auth["headers"]
    )
    assert r.status_code == 200
    # remaining: Milk 3.50
    assert r.json()["total"] == 3.50


async def test_delete_last_item_clears_bill_total(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())

    for it in body["items"]:
        r = await client.delete(
            f"/bills/{bill_id}/items/{it['id']}", headers=auth["headers"]
        )
        assert r.status_code == 200

    assert r.json()["total"] is None


async def test_extract_does_not_force_total_to_item_sum(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    """Extract preserves VLM-reported total even if it disagrees with item sum
    (receipts often have tax/fees in total but not as a line item)."""
    from src.schemas.extraction import LineItem, RawBillExtraction

    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(
        client,
        auth,
        bill_id,
        RawBillExtraction(
            merchant="Acme",
            total=20.00,  # VLM total
            currency="USD",
            items=[
                LineItem(name="Foo", total_price=8.00),
                LineItem(name="Bar", total_price=10.00),  # items sum to 18, total=20 (tax)
            ],
            raw_text="...",
        ),
    )
    assert body["total"] == 20.00  # NOT 18.00 — extract preserves VLM's number


# ---------- finalize ----------


async def test_finalize_locks_bill(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())

    r = await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "reviewed"
    assert body["reviewed_at"] is not None


async def test_finalize_before_extract_returns_409(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    r = await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])
    assert r.status_code == 409


async def test_finalize_twice_returns_409(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    r = await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])
    assert r.status_code == 409


# ---------- locked-after-finalize ----------


async def test_patch_after_finalize_returns_409(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    r = await client.patch(
        f"/bills/{bill_id}", headers=auth["headers"], json={"merchant": "Nope"}
    )
    assert r.status_code == 409


async def test_add_item_after_finalize_returns_409(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    r = await client.post(
        f"/bills/{bill_id}/items",
        headers=auth["headers"],
        json={"name": "Late add"},
    )
    assert r.status_code == 409


async def test_re_extract_after_finalize_returns_409(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    from src.main import app

    bill_id = await _upload(client, auth["headers"], jpeg)
    await _extract(client, auth, bill_id, _sample_extraction())
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    _override_vision(app, _FakeVision(result=_sample_extraction()))
    try:
        r = await client.post(
            f"/bills/{bill_id}/extract", headers=auth["headers"]
        )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 409


async def test_delete_item_after_finalize_returns_409(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())
    item_id = body["items"][0]["id"]
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    r = await client.delete(
        f"/bills/{bill_id}/items/{item_id}", headers=auth["headers"]
    )
    assert r.status_code == 409


# ---------- cross-user item access ----------


async def test_other_user_cannot_edit_item(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    body = await _extract(client, auth, bill_id, _sample_extraction())
    item_id = body["items"][0]["id"]

    other = await client.post(
        "/auth/register",
        json={"email": "intruder@example.com", "password": "passw0rd!", "username": "intruder"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['token']}"}

    r = await client.patch(
        f"/bills/{bill_id}/items/{item_id}",
        headers=other_headers,
        json={"name": "hacked"},
    )
    assert r.status_code == 404


# ---------- auth ----------


async def test_list_without_auth_returns_401(client: AsyncClient) -> None:
    r = await client.get("/bills")
    assert r.status_code == 401


async def test_get_without_auth_returns_401(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    r = await client.get(f"/bills/{bill_id}")
    assert r.status_code == 401
