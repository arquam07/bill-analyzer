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

    async def extract_bill(self, image_bytes: bytes) -> RawBillExtraction:
        return self._result


def _override_vision(app: Any, vision: _FakeVision) -> None:
    app.dependency_overrides[get_vision_service] = lambda: vision


async def _upload(client: AsyncClient, headers: dict[str, str], jpeg: bytes) -> str:
    r = await client.post(
        "/bills", headers=headers, files={"image": ("r.jpg", jpeg, "image/jpeg")}
    )
    assert r.status_code == 201
    return r.json()["id"]


def _three_item_extraction() -> RawBillExtraction:
    return RawBillExtraction(
        merchant="Cafe",
        total=30.00,
        currency="USD",
        items=[
            LineItem(name="Coffee", total_price=10.00),
            LineItem(name="Sandwich", total_price=15.00),
            LineItem(name="Dessert", total_price=5.00),
        ],
        raw_text="...",
    )


async def _setup_extracted_bill(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> tuple[str, list[str]]:
    """Returns (bill_id, [item_id, ...])."""
    from src.main import app

    bill_id = await _upload(client, auth["headers"], jpeg)
    _override_vision(app, _FakeVision(result=_three_item_extraction()))
    try:
        r = await client.post(
            f"/bills/{bill_id}/extract", headers=auth["headers"]
        )
    finally:
        app.dependency_overrides.clear()
    body = r.json()
    return bill_id, [it["id"] for it in body["items"]]


# ---------- get/create ----------


async def test_get_split_creates_empty_split_for_extracted_bill(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.get(f"/bills/{bill_id}/split", headers=auth["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["bill_id"] == bill_id
    assert body["participants"] == []
    assert body["item_assignments"] == []
    assert body["unassigned_total"] == 30.00
    assert body["bill_total"] == 30.00
    assert body["bill_locked"] is False


async def test_get_split_unknown_bill_returns_404(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.get(
        "/bills/00000000-0000-0000-0000-000000000000/split",
        headers=auth["headers"],
    )
    assert r.status_code == 404


async def test_get_split_other_users_bill_returns_404(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    other = await client.post(
        "/auth/register",
        json={"email": "stranger@example.com", "password": "passw0rd!", "username": "stranger"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['token']}"}
    r = await client.get(f"/bills/{bill_id}/split", headers=other_headers)
    assert r.status_code == 404


# ---------- participants ----------


async def test_add_participant_named_only(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Alice"},
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["participants"]) == 1
    assert body["participants"][0]["display_name"] == "Alice"
    assert body["participants"][0]["user_id"] is None


async def test_add_participant_links_user_by_email(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    # Register a friend so the email lookup hits
    friend = await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "passw0rd!", "username": "bob"},
    )
    friend_id = friend.json()["user"]["id"]

    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Bob", "user_email": "bob@example.com"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["participants"][0]["user_id"] == friend_id


async def test_add_participant_unknown_email_still_creates_unlinked(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Ghost", "user_email": "ghost@example.com"},
    )
    assert r.status_code == 201
    assert r.json()["participants"][0]["user_id"] is None


async def test_duplicate_participant_name_returns_409(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Alice"},
    )
    r = await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Alice"},
    )
    assert r.status_code == 409


async def test_remove_participant(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Alice"},
    )
    pid = r.json()["participants"][0]["id"]
    r = await client.delete(
        f"/bills/{bill_id}/split/participants/{pid}", headers=auth["headers"]
    )
    assert r.status_code == 200
    assert r.json()["participants"] == []


# ---------- item assignment ----------


async def test_assign_item_single_participant_full_share(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, item_ids = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Alice"},
    )
    alice = r.json()["participants"][0]["id"]
    r = await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[0]}/participants",
        headers=auth["headers"],
        json={"participant_ids": [alice]},
    )
    body = r.json()
    totals = {t["display_name"]: t["total"] for t in body["participant_totals"]}
    assert totals == {"Alice": 10.00}
    assert body["unassigned_total"] == 20.00  # remaining items still unassigned


async def test_assign_item_multiple_participants_equal_split(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, item_ids = await _setup_extracted_bill(client, auth, jpeg)
    await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "A"},
    )
    body_b = (
        await client.post(
            f"/bills/{bill_id}/split/participants",
            headers=auth["headers"],
            json={"display_name": "B"},
        )
    ).json()
    a = next(p["id"] for p in body_b["participants"] if p["display_name"] == "A")
    b = next(p["id"] for p in body_b["participants"] if p["display_name"] == "B")

    # Sandwich (15.00) split between A and B → 7.50 each
    r = await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[1]}/participants",
        headers=auth["headers"],
        json={"participant_ids": [a, b]},
    )
    body = r.json()
    totals = {t["display_name"]: t["total"] for t in body["participant_totals"]}
    assert totals == {"A": 7.50, "B": 7.50}
    assert body["unassigned_total"] == 15.00  # Coffee + Dessert


async def test_assign_item_replaces_previous_assignment(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, item_ids = await _setup_extracted_bill(client, auth, jpeg)
    await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "A"},
    )
    body_b = (
        await client.post(
            f"/bills/{bill_id}/split/participants",
            headers=auth["headers"],
            json={"display_name": "B"},
        )
    ).json()
    a = next(p["id"] for p in body_b["participants"] if p["display_name"] == "A")
    b = next(p["id"] for p in body_b["participants"] if p["display_name"] == "B")

    # Initially A only
    await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[0]}/participants",
        headers=auth["headers"],
        json={"participant_ids": [a]},
    )
    # Replace with B only
    r = await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[0]}/participants",
        headers=auth["headers"],
        json={"participant_ids": [b]},
    )
    totals = {
        t["display_name"]: t["total"] for t in r.json()["participant_totals"]
    }
    assert totals == {"A": 0.00, "B": 10.00}


async def test_assign_unknown_participant_returns_400(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, item_ids = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[0]}/participants",
        headers=auth["headers"],
        json={"participant_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert r.status_code == 400


async def test_assign_unknown_item_returns_404(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    a = (
        await client.post(
            f"/bills/{bill_id}/split/participants",
            headers=auth["headers"],
            json={"display_name": "A"},
        )
    ).json()["participants"][0]["id"]
    r = await client.put(
        f"/bills/{bill_id}/split/items/00000000-0000-0000-0000-000000000000/participants",
        headers=auth["headers"],
        json={"participant_ids": [a]},
    )
    assert r.status_code == 404


# ---------- settle ----------


async def test_settle_and_unsettle_participant(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, item_ids = await _setup_extracted_bill(client, auth, jpeg)
    pid = (
        await client.post(
            f"/bills/{bill_id}/split/participants",
            headers=auth["headers"],
            json={"display_name": "Alice"},
        )
    ).json()["participants"][0]["id"]
    await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[0]}/participants",
        headers=auth["headers"],
        json={"participant_ids": [pid]},
    )

    r = await client.post(
        f"/bills/{bill_id}/split/participants/{pid}/settle",
        headers=auth["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["participants"][0]["settled_at"] is not None
    assert body["participant_totals"][0]["settled_at"] is not None

    r = await client.delete(
        f"/bills/{bill_id}/split/participants/{pid}/settle",
        headers=auth["headers"],
    )
    assert r.json()["participants"][0]["settled_at"] is None


# ---------- finalize locking ----------


async def test_split_locks_after_bill_finalized(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, item_ids = await _setup_extracted_bill(client, auth, jpeg)
    pid = (
        await client.post(
            f"/bills/{bill_id}/split/participants",
            headers=auth["headers"],
            json={"display_name": "Alice"},
        )
    ).json()["participants"][0]["id"]
    await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[0]}/participants",
        headers=auth["headers"],
        json={"participant_ids": [pid]},
    )
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    # Read still works and reports locked=True
    r = await client.get(f"/bills/{bill_id}/split", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["bill_locked"] is True

    # Mutations 409
    r = await client.post(
        f"/bills/{bill_id}/split/participants",
        headers=auth["headers"],
        json={"display_name": "Bob"},
    )
    assert r.status_code == 409

    r = await client.delete(
        f"/bills/{bill_id}/split/participants/{pid}", headers=auth["headers"]
    )
    assert r.status_code == 409

    r = await client.put(
        f"/bills/{bill_id}/split/items/{item_ids[0]}/participants",
        headers=auth["headers"],
        json={"participant_ids": []},
    )
    assert r.status_code == 409

    # Settle is still allowed after finalize (debt-tracking, not split structure)
    r = await client.post(
        f"/bills/{bill_id}/split/participants/{pid}/settle",
        headers=auth["headers"],
    )
    assert r.status_code == 200


async def test_get_split_on_finalized_bill_without_split_returns_empty(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])
    r = await client.get(f"/bills/{bill_id}/split", headers=auth["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["participants"] == []
    assert body["bill_locked"] is True


# ---------- auth ----------


async def test_split_endpoints_require_auth(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id, _ = await _setup_extracted_bill(client, auth, jpeg)
    r = await client.get(f"/bills/{bill_id}/split")
    assert r.status_code == 401
    r = await client.post(
        f"/bills/{bill_id}/split/participants", json={"display_name": "X"}
    )
    assert r.status_code == 401
