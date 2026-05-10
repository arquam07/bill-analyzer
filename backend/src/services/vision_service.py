import asyncio
import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.core.constants import BILL_CATEGORIES, DEFAULT_LANGUAGE
from src.core.exceptions import OllamaUnavailable, VLMResponseInvalid
from src.schemas.extraction import RawBillExtraction

_LANGUAGE_NAMES = {"en": "English", "ja": "Japanese"}

_CATEGORY_LIST = ", ".join(BILL_CATEGORIES)


def _build_system_prompt(language: str) -> str:
    """Build the OCR prompt. The user's preferred_language controls the *output* language
    of human-readable text fields (merchant, item names) — receipt source language is
    detected automatically from the image.
    """
    lang_name = _LANGUAGE_NAMES.get(language, "English")
    return f"""You are an OCR engine for retail receipts and bills.
Extract structured data from the image and return ONLY valid JSON with this shape:
{{
  "merchant": string | null,
  "total": number | null,
  "currency": string | null,
  "billed_at": string | null,           // YYYY-MM-DD if a date is visible
  "category": string | null,            // one of: {_CATEGORY_LIST}
  "items": [
    {{
      "name": string,
      "quantity": number | null,
      "unit_price": number | null,
      "total_price": number | null,
      "tax_rate": number | null,        // decimal rate e.g. 0.08 or 0.10; null if unknown
      "category": string | null         // one of: {_CATEGORY_LIST}
    }}
  ],
  "raw_text": string                    // every line of text you read, joined by \\n
}}
Rules:
- Output JSON only. No prose, no markdown, no code fences.
- Use null for fields you cannot read confidently.
- Numeric fields must be numbers, not strings.
- Translate "merchant" and item "name" fields into {lang_name} when the receipt is in another language. "raw_text" stays in the original language exactly as printed.
- "category" describes the bill as a whole (e.g. a supermarket = grocery, a restaurant = food). Each item may also have its own category for finer breakdowns. Use null if uncertain.
- Japanese receipts use 外税 (exclusive/pre-tax pricing): item prices are pre-tax. Items marked with ※ carry 8% reduced tax (食料品, tax_rate=0.08); items WITHOUT ※ carry 10% standard tax (tax_rate=0.10). If the ※ mark cannot be determined, default to tax_rate=0.08.
- If the receipt shows no tax section or tax rates at all, prices are already tax-inclusive — set tax_rate=null for all items.
- For non-Japanese receipts: extract tax_rate per item if the receipt clearly shows per-item tax rates, otherwise null."""


class VisionService:
    def __init__(
        self,
        *,
        project: str,
        location: str,
        model: str,
        timeout_seconds: float,
        # injectable for tests — pass a mock genai.Client to skip ADC
        _client: genai.Client | None = None,
    ) -> None:
        self._client = _client or genai.Client(
            vertexai=True, project=project, location=location
        )
        self._model = model
        self._timeout = timeout_seconds

    async def extract_bill(
        self, image_bytes: bytes, *, language: str = DEFAULT_LANGUAGE
    ) -> RawBillExtraction:
        mime = "image/jpeg" if image_bytes[:2] == b"\xff\xd8" else "image/png"
        config = types.GenerateContentConfig(
            system_instruction=_build_system_prompt(language),
            response_mime_type="application/json",
            temperature=0.0,
        )
        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            types.Part(text="Extract all data from this bill or receipt."),
        ]
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,  # type: ignore[arg-type]
                    config=config,
                ),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError as exc:
            raise OllamaUnavailable(
                f"Vertex AI request timed out after {self._timeout}s"
            ) from exc
        except Exception as exc:
            raise OllamaUnavailable(f"Vertex AI error: {exc}") from exc

        raw = response.text or ""
        try:
            data = json.loads(raw)
            return RawBillExtraction.model_validate(data)
        except (json.JSONDecodeError, TypeError) as exc:
            raise VLMResponseInvalid(
                f"Vertex AI output is not valid JSON: {raw[:500]}"
            ) from exc
        except ValidationError as exc:
            raise VLMResponseInvalid(
                f"Vertex AI output failed schema validation: {exc.errors()[:5]}"
            ) from exc

    async def aclose(self) -> None:
        pass  # google-genai client has no persistent connection to close
