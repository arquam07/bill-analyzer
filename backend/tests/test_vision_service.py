import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import OllamaUnavailable, VLMResponseInvalid
from src.services.vision_service import VisionService

_JPEG = b"\xff\xd8\xff\xe0fakejpeg"
_PNG = b"\x89PNG\r\nfakepng"


def _make_response(payload: dict | str) -> MagicMock:
    resp = MagicMock()
    resp.text = json.dumps(payload) if isinstance(payload, dict) else payload
    return resp


def _make_service(generate_response: MagicMock | None = None) -> tuple[VisionService, AsyncMock]:
    """Return a VisionService wired to a mock client. Also returns the generate mock."""
    mock_generate = AsyncMock(
        return_value=generate_response or _make_response({"raw_text": "x"})
    )
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = mock_generate
    svc = VisionService(
        project="test-project",
        location="asia-northeast1",
        model="gemini-2.0-flash-001",
        timeout_seconds=5.0,
        _client=mock_client,
    )
    return svc, mock_generate


# ── success cases ─────────────────────────────────────────────────────────────


async def test_extract_parses_full_response() -> None:
    payload = {
        "merchant": "Acme Grocery",
        "total": 12.34,
        "currency": "USD",
        "billed_at": "2026-04-26",
        "category": "grocery",
        "items": [
            {"name": "Milk", "quantity": 1, "unit_price": 3.50, "total_price": 3.50},
            {"name": "Bread", "quantity": 2, "unit_price": 4.42, "total_price": 8.84},
        ],
        "raw_text": "ACME GROCERY\nMilk 3.50\nBread 8.84\nTotal 12.34",
    }
    svc, _ = _make_service(_make_response(payload))
    result = await svc.extract_bill(_JPEG)

    assert result.merchant == "Acme Grocery"
    assert result.total == 12.34
    assert result.currency == "USD"
    assert str(result.billed_at) == "2026-04-26"
    assert result.category == "grocery"
    assert len(result.items) == 2
    assert result.items[0].name == "Milk"
    assert result.items[1].total_price == 8.84


async def test_extract_handles_partial_response() -> None:
    """Model omits optional fields → defaults apply, no error raised."""
    svc, _ = _make_service(_make_response({"merchant": "Cafe", "raw_text": "CAFE"}))
    result = await svc.extract_bill(_JPEG)

    assert result.merchant == "Cafe"
    assert result.total is None
    assert result.items == []


async def test_jpeg_mime_type_sent() -> None:
    """JPEG magic bytes → image/jpeg MIME type in the request."""
    svc, mock_generate = _make_service()
    await svc.extract_bill(_JPEG)

    contents = mock_generate.call_args.kwargs["contents"]
    image_part = contents[0]
    assert image_part.inline_data.mime_type == "image/jpeg"


async def test_png_mime_type_sent() -> None:
    """PNG magic bytes → image/png MIME type in the request."""
    svc, mock_generate = _make_service()
    await svc.extract_bill(_PNG)

    contents = mock_generate.call_args.kwargs["contents"]
    image_part = contents[0]
    assert image_part.inline_data.mime_type == "image/png"


async def test_language_hint_in_system_prompt() -> None:
    """Japanese language hint → 'Japanese' appears in the system instruction."""
    svc, mock_generate = _make_service()
    await svc.extract_bill(_JPEG, language="ja")

    config = mock_generate.call_args.kwargs["config"]
    assert "Japanese" in config.system_instruction


async def test_english_is_default_language() -> None:
    svc, mock_generate = _make_service()
    await svc.extract_bill(_JPEG)

    config = mock_generate.call_args.kwargs["config"]
    assert "English" in config.system_instruction


async def test_bill_level_category_persists() -> None:
    payload = {
        "merchant": "MegaMart",
        "category": "grocery",
        "items": [{"name": "Milk", "category": "grocery"}],
        "raw_text": "x",
    }
    svc, _ = _make_service(_make_response(payload))
    result = await svc.extract_bill(_JPEG)

    assert result.category == "grocery"
    assert result.items[0].category == "grocery"


async def test_unknown_category_becomes_none() -> None:
    """VLM emits a category outside our enum → silently set to None."""
    svc, _ = _make_service(_make_response({"category": "luxury_yachts", "raw_text": "x"}))
    result = await svc.extract_bill(_JPEG)

    assert result.category is None


# ── error cases ───────────────────────────────────────────────────────────────


async def test_timeout_raises_ollama_unavailable() -> None:
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=asyncio.TimeoutError)
    svc = VisionService(
        project="p", location="l", model="m", timeout_seconds=0.001, _client=mock_client
    )
    with pytest.raises(OllamaUnavailable, match="timed out"):
        await svc.extract_bill(_JPEG)


async def test_api_error_raises_ollama_unavailable() -> None:
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("quota exceeded")
    )
    svc = VisionService(
        project="p", location="l", model="m", timeout_seconds=5.0, _client=mock_client
    )
    with pytest.raises(OllamaUnavailable, match="Vertex AI error"):
        await svc.extract_bill(_JPEG)


async def test_invalid_json_raises_vlm_response_invalid() -> None:
    svc, _ = _make_service(_make_response("Sorry, I cannot read that."))
    with pytest.raises(VLMResponseInvalid):
        await svc.extract_bill(_JPEG)


async def test_schema_failure_raises_vlm_response_invalid() -> None:
    svc, _ = _make_service(_make_response({"total": "not-a-number", "items": [{"name": 123}]}))
    with pytest.raises(VLMResponseInvalid):
        await svc.extract_bill(_JPEG)


async def test_aclose_is_noop() -> None:
    svc, _ = _make_service()
    await svc.aclose()  # must not raise
