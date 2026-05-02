from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image
from PIL.Image import Exif


def _jpeg_with_exif(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color="white")
    exif = Exif()
    exif[0x010F] = "TestCamera"  # Make
    exif[0x0110] = "TestModel"  # Model
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif, quality=90)
    return buf.getvalue()


def _png_bytes(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def jpeg_with_exif() -> bytes:
    return _jpeg_with_exif()


@pytest.fixture
def png_image() -> bytes:
    return _png_bytes()


async def test_upload_without_auth_returns_401(
    client: AsyncClient, jpeg_with_exif: bytes
) -> None:
    r = await client.post(
        "/bills",
        files={"image": ("receipt.jpg", jpeg_with_exif, "image/jpeg")},
    )
    assert r.status_code == 401


async def test_upload_jpeg_returns_201_and_metadata(
    client: AsyncClient, auth: dict[str, object], jpeg_with_exif: bytes
) -> None:
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("receipt.jpg", jpeg_with_exif, "image/jpeg")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["mime_type"] == "image/jpeg"
    assert body["status"] == "uploaded"
    assert body["byte_size"] > 0
    assert body["image_path"].startswith(f"users/{auth['user_id']}/bills/")
    assert body["image_path"].endswith(".jpg")


async def test_upload_png_returns_201(
    client: AsyncClient, auth: dict[str, object], png_image: bytes
) -> None:
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("receipt.png", png_image, "image/png")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["mime_type"] == "image/png"
    assert body["image_path"].endswith(".png")


async def test_upload_writes_to_user_scoped_path(
    client: AsyncClient,
    auth: dict[str, object],
    storage_root: Path,
    jpeg_with_exif: bytes,
) -> None:
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("receipt.jpg", jpeg_with_exif, "image/jpeg")},
    )
    assert r.status_code == 201
    image_path = r.json()["image_path"]
    on_disk = storage_root / image_path
    assert on_disk.is_file()
    assert on_disk.stat().st_size == r.json()["byte_size"]


async def test_upload_strips_exif(
    client: AsyncClient,
    auth: dict[str, object],
    storage_root: Path,
    jpeg_with_exif: bytes,
) -> None:
    # Sanity: the input has EXIF
    assert len(Image.open(BytesIO(jpeg_with_exif)).getexif()) > 0

    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("receipt.jpg", jpeg_with_exif, "image/jpeg")},
    )
    assert r.status_code == 201
    stored = (storage_root / r.json()["image_path"]).read_bytes()
    assert len(Image.open(BytesIO(stored)).getexif()) == 0


async def test_upload_oversized_returns_413(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    big = b"x" * (10 * 1024 * 1024 + 1)
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("huge.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 413


async def test_upload_non_image_returns_415(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    pdf = b"%PDF-1.4\n%fake\n"
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("doc.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 415


async def test_upload_pdf_declared_as_jpeg_returns_415(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    """MIME sniffing trumps the declared content type."""
    pdf = b"%PDF-1.4\n%fake content here\n"
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("fake.jpg", pdf, "image/jpeg")},
    )
    assert r.status_code == 415


async def test_upload_jpeg_with_wrong_extension_succeeds(
    client: AsyncClient, auth: dict[str, object], jpeg_with_exif: bytes
) -> None:
    """Real image bytes are accepted regardless of declared MIME / filename."""
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("looks-like.pdf", jpeg_with_exif, "application/pdf")},
    )
    assert r.status_code == 201
    assert r.json()["mime_type"] == "image/jpeg"


async def test_upload_empty_returns_400(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("empty.jpg", b"", "image/jpeg")},
    )
    assert r.status_code == 400


async def test_two_uploads_create_two_bills_with_distinct_paths(
    client: AsyncClient, auth: dict[str, object], jpeg_with_exif: bytes
) -> None:
    r1 = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("a.jpg", jpeg_with_exif, "image/jpeg")},
    )
    r2 = await client.post(
        "/bills",
        headers=auth["headers"],
        files={"image": ("b.jpg", jpeg_with_exif, "image/jpeg")},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]
    assert r1.json()["image_path"] != r2.json()["image_path"]
    # Same content → identical hash (the M10 dedupe hook lives here)
    assert r1.json()["content_hash"] == r2.json()["content_hash"]


# ---------- manual bill creation ----------


async def test_manual_bill_requires_auth(client: AsyncClient) -> None:
    r = await client.post("/bills/manual", json={})
    assert r.status_code == 401


async def test_manual_bill_creates_in_extracted_state(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post(
        "/bills/manual",
        headers=auth["headers"],
        json={"merchant": "Diner", "total": 25.0, "currency": "USD", "billed_at": "2026-04-01"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "extracted"
    assert body["merchant"] == "Diner"
    assert body["total"] == 25.0
    assert body["currency"] == "USD"
    assert body["billed_at"] == "2026-04-01"
    assert body["image_path"] == ""
    assert body["byte_size"] == 0
    assert body["items"] == []


async def test_manual_bill_can_be_finalized_directly(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post(
        "/bills/manual",
        headers=auth["headers"],
        json={"merchant": "Manual", "billed_at": "2026-04-15"},
    )
    bill_id = r.json()["id"]

    # Add an item via existing endpoint
    r2 = await client.post(
        f"/bills/{bill_id}/items",
        headers=auth["headers"],
        json={"name": "Coffee", "total_price": 5.0, "category": "drinks"},
    )
    assert r2.status_code == 201
    assert r2.json()["total"] == 5.0  # bill.total recomputed from items

    # Finalize
    r3 = await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])
    assert r3.status_code == 200
    assert r3.json()["status"] == "reviewed"


async def test_manual_bill_appears_in_insights_after_finalize(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post(
        "/bills/manual",
        headers=auth["headers"],
        json={"merchant": "Cafe", "total": 12.5, "billed_at": "2026-04-20"},
    )
    bill_id = r.json()["id"]
    await client.post(
        f"/bills/{bill_id}/items",
        headers=auth["headers"],
        json={"name": "Latte", "total_price": 12.5, "category": "drinks"},
    )
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    r = await client.get(
        "/insights/overview?from=2026-04-01&to=2026-04-30",
        headers=auth["headers"],
    )
    assert r.json()["total_spend"] == 12.5
    assert r.json()["bill_count"] == 1


async def test_manual_bill_with_empty_body(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post("/bills/manual", headers=auth["headers"], json={})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "extracted"
    assert body["merchant"] is None
    assert body["total"] is None


# ---------- bill category ----------


async def test_manual_bill_with_category(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post(
        "/bills/manual",
        headers=auth["headers"],
        json={"merchant": "MegaMart", "category": "grocery"},
    )
    assert r.status_code == 201
    assert r.json()["category"] == "grocery"


async def test_manual_bill_with_invalid_category_422(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post(
        "/bills/manual",
        headers=auth["headers"],
        json={"category": "made_up"},
    )
    assert r.status_code == 422


async def test_patch_bill_category(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    bill_id = (await client.post("/bills/manual", headers=auth["headers"], json={})).json()["id"]
    r = await client.patch(
        f"/bills/{bill_id}",
        headers=auth["headers"],
        json={"category": "pharmacy"},
    )
    assert r.status_code == 200
    assert r.json()["category"] == "pharmacy"


async def test_breakdown_coalesces_bill_category_when_item_has_none(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    """An item with no category falls back to the bill's category in breakdown."""
    # Create a manual bill tagged as grocery, finalize it
    r = await client.post(
        "/bills/manual",
        headers=auth["headers"],
        json={"merchant": "MegaMart", "category": "grocery", "billed_at": "2026-04-15"},
    )
    bill_id = r.json()["id"]
    await client.post(
        f"/bills/{bill_id}/items",
        headers=auth["headers"],
        json={"name": "Milk", "total_price": 3.0},  # no item-level category
    )
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    bd = await client.get(
        "/insights/breakdown?dimension=category&from=2026-04-01&to=2026-04-30",
        headers=auth["headers"],
    )
    rows = bd.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["label"] == "grocery"
    assert rows[0]["total"] == 3.0


async def test_breakdown_prefers_item_category_over_bill(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    """When the item has its own category, it wins over the bill-level category."""
    r = await client.post(
        "/bills/manual",
        headers=auth["headers"],
        json={"merchant": "MegaMart", "category": "grocery", "billed_at": "2026-04-16"},
    )
    bill_id = r.json()["id"]
    await client.post(
        f"/bills/{bill_id}/items",
        headers=auth["headers"],
        json={"name": "Aspirin", "total_price": 5.0, "category": "pharmacy"},
    )
    await client.post(f"/bills/{bill_id}/finalize", headers=auth["headers"])

    bd = await client.get(
        "/insights/breakdown?dimension=category&from=2026-04-01&to=2026-04-30",
        headers=auth["headers"],
    )
    rows = bd.json()["rows"]
    labels = {r["label"]: r["total"] for r in rows}
    assert labels == {"pharmacy": 5.0}
