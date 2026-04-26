import json

import httpx
import pytest

from src.core.exceptions import (
    OllamaResponseError,
    OllamaUnavailable,
    VLMResponseInvalid,
)
from src.services.vision_service import VisionService


def _make_service(handler, *, api_key: str | None = None) -> VisionService:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return VisionService(
        ollama_host="http://test-ollama",
        ollama_model="glm-ocr",
        timeout_seconds=5.0,
        api_key=api_key,
        http_client=client,
    )


async def test_extract_attaches_bearer_when_api_key_set() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps({"merchant": "X", "raw_text": "x"})}},
        )

    service = _make_service(handler, api_key="sk-cloud-123")
    await service.extract_bill(b"x")
    assert seen[0].headers.get("authorization") == "Bearer sk-cloud-123"


async def test_extract_omits_bearer_when_no_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps({"merchant": "X", "raw_text": "x"})}},
        )

    service = _make_service(handler)
    await service.extract_bill(b"x")
    assert "authorization" not in {k.lower() for k in seen[0].headers.keys()}


async def test_extract_parses_full_response() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "merchant": "Acme Grocery",
                            "total": 12.34,
                            "currency": "USD",
                            "billed_at": "2026-04-26",
                            "items": [
                                {
                                    "name": "Milk",
                                    "quantity": 1,
                                    "unit_price": 3.50,
                                    "total_price": 3.50,
                                },
                                {
                                    "name": "Bread",
                                    "quantity": 2,
                                    "unit_price": 4.42,
                                    "total_price": 8.84,
                                },
                            ],
                            "raw_text": "ACME GROCERY\\nMilk 3.50\\nBread 8.84\\nTotal 12.34",
                        }
                    )
                }
            },
        )

    service = _make_service(handler)
    result = await service.extract_bill(b"\xff\xd8\xff\xe0fakejpeg")

    assert result.merchant == "Acme Grocery"
    assert result.total == 12.34
    assert result.currency == "USD"
    assert str(result.billed_at) == "2026-04-26"
    assert len(result.items) == 2
    assert result.items[0].name == "Milk"
    assert result.items[1].total_price == 8.84

    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert body["model"] == "glm-ocr"
    assert body["stream"] is False
    assert body["format"] == "json"
    assert body["options"]["temperature"] == 0
    user_msg = body["messages"][1]
    assert user_msg["role"] == "user"
    assert len(user_msg["images"]) == 1


async def test_extract_handles_partial_extraction() -> None:
    """Model omits some fields → defaults apply, no error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {"merchant": "Cafe", "raw_text": "CAFE\\n..."}
                    )
                }
            },
        )

    service = _make_service(handler)
    result = await service.extract_bill(b"x")
    assert result.merchant == "Cafe"
    assert result.total is None
    assert result.items == []


async def test_extract_raises_when_ollama_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    service = _make_service(handler)
    with pytest.raises(OllamaUnavailable):
        await service.extract_bill(b"x")


async def test_extract_raises_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    service = _make_service(handler)
    with pytest.raises(OllamaUnavailable):
        await service.extract_bill(b"x")


async def test_extract_raises_on_non_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal")

    service = _make_service(handler)
    with pytest.raises(OllamaResponseError):
        await service.extract_bill(b"x")


async def test_extract_raises_when_envelope_malformed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    service = _make_service(handler)
    with pytest.raises(VLMResponseInvalid):
        await service.extract_bill(b"x")


async def test_extract_raises_when_content_not_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"content": "I cannot do this. Sorry!"}}
        )

    service = _make_service(handler)
    with pytest.raises(VLMResponseInvalid):
        await service.extract_bill(b"x")


async def test_extract_raises_when_content_fails_schema() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {"total": "not-a-number", "items": [{"name": 123}]}
                    )
                }
            },
        )

    service = _make_service(handler)
    with pytest.raises(VLMResponseInvalid):
        await service.extract_bill(b"x")
