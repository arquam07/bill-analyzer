import base64
import json

import httpx
from pydantic import ValidationError

from src.core.exceptions import (
    OllamaResponseError,
    OllamaUnavailable,
    VLMResponseInvalid,
)
from src.schemas.extraction import RawBillExtraction

SYSTEM_PROMPT = """You are an OCR engine for retail receipts and bills.
Extract structured data from the image and return ONLY valid JSON with this shape:
{
  "merchant": string | null,
  "total": number | null,
  "currency": string | null,
  "billed_at": string | null,           // YYYY-MM-DD if a date is visible
  "items": [
    {
      "name": string,
      "quantity": number | null,
      "unit_price": number | null,
      "total_price": number | null
    }
  ],
  "raw_text": string                    // every line of text you read, joined by \\n
}
Rules:
- Output JSON only. No prose, no markdown, no code fences.
- Use null for fields you cannot read confidently.
- Numeric fields must be numbers, not strings."""

USER_PROMPT = "Extract the receipt's structured data."


class VisionService:
    def __init__(
        self,
        *,
        ollama_host: str,
        ollama_model: str,
        timeout_seconds: float,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._host = ollama_host.rstrip("/")
        self._model = ollama_model
        self._timeout = timeout_seconds
        self._api_key = api_key
        self._http = http_client or httpx.AsyncClient()
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def extract_bill(self, image_bytes: bytes) -> RawBillExtraction:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        print(f"ollama model: {self._model}")
        print(f"ollama timeout: {self._timeout}")
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT, "images": [b64]},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else None
        try:
            response = await self._http.post(
                f"{self._host}/api/chat",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise OllamaUnavailable(f"request timed out after {self._timeout}s: {exc}") from exc
        except httpx.ConnectError as exc:
            raise OllamaUnavailable(f"cannot connect to {self._host}: {exc}") from exc

        if response.status_code != 200:
            raise OllamaResponseError(
                f"ollama returned {response.status_code}: {response.text[:500]}"
            )

        try:
            envelope = response.json()
            content: str = envelope["message"]["content"]
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            raise VLMResponseInvalid(
                f"unexpected ollama response shape: {response.text[:500]}"
            ) from exc

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise VLMResponseInvalid(
                f"vlm output is not valid JSON: {content[:500]}"
            ) from exc

        try:
            return RawBillExtraction.model_validate(data)
        except ValidationError as exc:
            raise VLMResponseInvalid(
                f"vlm output failed schema validation: {exc.errors()[:5]}"
            ) from exc
