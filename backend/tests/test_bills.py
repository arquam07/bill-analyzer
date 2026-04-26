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
