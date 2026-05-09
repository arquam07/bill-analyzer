import asyncio
import json
import logging
import uuid
from datetime import date, timedelta

from google import genai
from google.genai import types
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bill import Bill, BillItem

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an item canonicalization engine for a personal expense tracker.
Map each receipt item name to a short, lowercase, singular English noun that represents
what the product fundamentally is. Group variants together:
"brown eggs", "halal eggs", "free-range eggs" -> "eggs"
"whole milk", "2% milk", "oat milk" -> "milk"
"sourdough bread", "white sandwich bread" -> "bread"

Use existing canonical names when they match. Create new ones only when needed.
Return null for uncategorizable items (barcodes, misc charges, etc.).

Input JSON:
{
  "existing_canonicals": ["eggs", "milk", "bread"],
  "new_items": ["fresh eggs", "halal chicken", "artisan bread"]
}

Output JSON ONLY (no prose, no markdown, no code fences):
{
  "fresh eggs": "eggs",
  "halal chicken": "chicken",
  "artisan bread": "bread"
}"""


class NormalizationService:
    def __init__(
        self,
        *,
        project: str,
        location: str,
        model: str,
        timeout_seconds: float,
        _client: genai.Client | None = None,
    ) -> None:
        self._client = _client or genai.Client(
            vertexai=True, project=project, location=location
        )
        self._model = model
        self._timeout = timeout_seconds

    async def normalize_bill(
        self,
        session: AsyncSession,
        *,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        try:
            await self._do_normalize(session, bill_id=bill_id, user_id=user_id)
        except Exception:
            logger.warning(
                "normalization failed for bill %s — insights will use SQL fallback",
                bill_id,
                exc_info=True,
            )

    async def _do_normalize(
        self,
        session: AsyncSession,
        *,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        # Load un-normalized items for this bill
        items_stmt = select(BillItem.id, BillItem.name).where(
            BillItem.bill_id == bill_id,
            BillItem.normalized_name.is_(None),
        )
        rows = (await session.execute(items_stmt)).all()
        if not rows:
            return

        item_ids = [r.id for r in rows]
        item_names = [r.name for r in rows]

        # Fetch existing canonical names from the last 30 days for this user
        since = date.today() - timedelta(days=30)
        canonicals_stmt = (
            select(BillItem.normalized_name)
            .distinct()
            .join(Bill, Bill.id == BillItem.bill_id)
            .where(
                Bill.user_id == user_id,
                BillItem.normalized_name.is_not(None),
                Bill.billed_at >= since,
            )
        )
        existing_canonicals: list[str] = [
            c
            for c in (await session.execute(canonicals_stmt)).scalars().all()
            if c is not None
        ]

        # Build and send the LLM request
        payload = json.dumps(
            {"existing_canonicals": existing_canonicals, "new_items": item_names}
        )
        config = types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.0,
        )
        response = await asyncio.wait_for(
            self._client.aio.models.generate_content(
                model=self._model,
                contents=[types.Part(text=payload)],  # type: ignore[arg-type]
                config=config,
            ),
            timeout=self._timeout,
        )

        # Parse mapping {item_name: canonical | null}
        mapping: object = json.loads(response.text or "{}")
        if not isinstance(mapping, dict):
            logger.warning(
                "normalization: unexpected LLM response shape for bill %s", bill_id
            )
            return

        # Group item IDs by the canonical name they map to
        canonical_to_ids: dict[str, list[uuid.UUID]] = {}
        for item_id, name in zip(item_ids, item_names):
            raw = mapping.get(name)
            if not raw or not isinstance(raw, str):
                continue
            canonical = raw.strip().lower()
            if not canonical:
                continue
            canonical_to_ids.setdefault(canonical, []).append(item_id)

        if not canonical_to_ids:
            return

        for canonical, ids in canonical_to_ids.items():
            await session.execute(
                update(BillItem)
                .where(BillItem.id.in_(ids))
                .values(normalized_name=canonical)
            )

        await session.commit()
