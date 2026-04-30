from io import BytesIO
from typing import Any

import pytest
from httpx import AsyncClient
from PIL import Image

from src.api.deps import get_vision_service
from src.core.exceptions import OllamaUnavailable, VLMResponseInvalid
from src.schemas.extraction import LineItem, RawBillExtraction


def _jpeg(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color="white")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture
def jpeg() -> bytes:
    return _jpeg()


class _FakeVision:
    def __init__(self, *, result: RawBillExtraction | None = None, raises: Exception | None = None):
        self._result = result
        self._raises = raises
        self.calls: list[bytes] = []

    async def extract_bill(self, image_bytes: bytes) -> RawBillExtraction:
        self.calls.append(image_bytes)
        if self._raises is not None:
            raise self._raises
        assert self._result is not None
        return self._result


def _override(app: Any, vision: _FakeVision) -> None:
    app.dependency_overrides[get_vision_service] = lambda: vision


async def _upload(client: AsyncClient, headers: dict[str, str], jpeg: bytes) -> str:
    r = await client.post("/bills", headers=headers, files={"image": ("r.jpg", jpeg, "image/jpeg")})
    assert r.status_code == 201
    return r.json()["id"]


async def test_extract_returns_parsed_extraction(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    from src.main import app

    bill_id = await _upload(client, auth["headers"], jpeg)
    fake = _FakeVision(
        result=RawBillExtraction(
            merchant="Acme",
            total=9.99,
            currency="USD",
            items=[LineItem(name="Coffee", total_price=9.99)],
            raw_text="ACME ...",
        )
    )
    _override(app, fake)
    try:
        r = await client.post(f"/bills/{bill_id}/extract", headers=auth["headers"])
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["merchant"] == "Acme"
    assert body["total"] == 9.99
    assert body["items"][0]["name"] == "Coffee"
    assert len(fake.calls) == 1
    assert len(fake.calls[0]) > 0


async def test_extract_unknown_bill_returns_404(
    client: AsyncClient, auth: dict[str, object]
) -> None:
    r = await client.post(
        "/bills/00000000-0000-0000-0000-000000000000/extract",
        headers=auth["headers"],
    )
    assert r.status_code == 404


async def test_extract_other_users_bill_returns_404(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    # Owner uploads
    bill_id = await _upload(client, auth["headers"], jpeg)

    # Second user authenticates
    other = await client.post(
        "/auth/register",
        json={"email": "stranger@example.com", "password": "passw0rd!", "username": "stranger"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['token']}"}

    r = await client.post(f"/bills/{bill_id}/extract", headers=other_headers)
    assert r.status_code == 404


async def test_extract_without_auth_returns_401(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    bill_id = await _upload(client, auth["headers"], jpeg)
    r = await client.post(f"/bills/{bill_id}/extract")
    assert r.status_code == 401


async def test_extract_propagates_ollama_unavailable_as_503(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    from src.main import app

    bill_id = await _upload(client, auth["headers"], jpeg)
    _override(app, _FakeVision(raises=OllamaUnavailable("connection refused")))
    try:
        r = await client.post(f"/bills/{bill_id}/extract", headers=auth["headers"])
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503


async def test_extract_propagates_invalid_vlm_response_as_502(
    client: AsyncClient, auth: dict[str, object], jpeg: bytes
) -> None:
    from src.main import app

    bill_id = await _upload(client, auth["headers"], jpeg)
    _override(app, _FakeVision(raises=VLMResponseInvalid("bad json")))
    try:
        r = await client.post(f"/bills/{bill_id}/extract", headers=auth["headers"])
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 502
