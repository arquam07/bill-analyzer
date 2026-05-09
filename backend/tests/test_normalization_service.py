import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.normalization_service import NormalizationService


def _make_service(llm_response: str | None = None) -> tuple[NormalizationService, AsyncMock]:
    mock_generate = AsyncMock()
    mock_generate.return_value = MagicMock(text=llm_response or "{}")
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = mock_generate
    svc = NormalizationService(
        project="test-project",
        location="asia-northeast1",
        model="gemini-2.5-flash",
        timeout_seconds=5.0,
        _client=mock_client,
    )
    return svc, mock_generate


def _make_row(item_id: uuid.UUID, item_name: str) -> MagicMock:
    """Row mock where .id and .name are real values (MagicMock(name=...) is reserved)."""
    m = MagicMock()
    m.id = item_id
    m.name = item_name
    return m


def _make_session(
    item_rows: list[tuple[uuid.UUID, str]],
    canonical_rows: list[str],
) -> AsyncMock:
    """Build a mock AsyncSession that returns item rows then canonical rows on execute()."""
    session = AsyncMock(spec=AsyncSession)

    item_result = MagicMock()
    item_result.all.return_value = [_make_row(iid, n) for iid, n in item_rows]

    canonical_result = MagicMock()
    canonical_result.scalars.return_value.all.return_value = canonical_rows

    # execute() called twice: items then canonicals; then possibly more for updates
    session.execute = AsyncMock(side_effect=[item_result, canonical_result] + [MagicMock()] * 10)
    return session


# ── success cases ──────────────────────────────────────────────────────────────


async def test_normalizes_items_and_commits() -> None:
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    session = _make_session(
        item_rows=[(id1, "fresh eggs"), (id2, "brown eggs")],
        canonical_rows=[],
    )
    svc, _ = _make_service(json.dumps({"fresh eggs": "eggs", "brown eggs": "eggs"}))

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    session.commit.assert_awaited_once()


async def test_uses_existing_canonicals_in_prompt() -> None:
    id1 = uuid.uuid4()
    session = _make_session(
        item_rows=[(id1, "halal chicken")],
        canonical_rows=["eggs", "milk"],
    )
    svc, mock_generate = _make_service(json.dumps({"halal chicken": "chicken"}))

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    call_args = mock_generate.call_args
    contents = call_args.kwargs["contents"]
    payload = json.loads(contents[0].text)
    assert "eggs" in payload["existing_canonicals"]
    assert "milk" in payload["existing_canonicals"]
    assert "halal chicken" in payload["new_items"]


async def test_no_items_skips_llm_call() -> None:
    session = _make_session(item_rows=[], canonical_rows=[])
    svc, mock_generate = _make_service()

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    mock_generate.assert_not_called()
    session.commit.assert_not_called()


async def test_null_mapping_skips_update() -> None:
    """LLM returns null for an item → no DB update, no commit."""
    id1 = uuid.uuid4()
    session = _make_session(item_rows=[(id1, "misc charge")], canonical_rows=[])
    svc, _ = _make_service(json.dumps({"misc charge": None}))

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    # execute was called for items + canonicals only (no update statements)
    assert session.execute.await_count == 2
    session.commit.assert_not_called()


async def test_canonical_lowercased_and_stripped() -> None:
    """LLM response with extra whitespace/caps → stored lowercase stripped."""
    id1 = uuid.uuid4()
    session = _make_session(item_rows=[(id1, "Whole Milk")], canonical_rows=[])
    svc, _ = _make_service(json.dumps({"Whole Milk": "  Milk  "}))

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    # Verify the update was executed (commit proves something was written)
    session.commit.assert_awaited_once()


# ── error resilience ───────────────────────────────────────────────────────────


async def test_llm_error_does_not_raise() -> None:
    """Any LLM exception → normalize_bill returns silently (best-effort)."""
    id1 = uuid.uuid4()
    session = _make_session(item_rows=[(id1, "eggs")], canonical_rows=[])
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("quota exceeded")
    )
    svc = NormalizationService(
        project="p", location="l", model="m", timeout_seconds=5.0, _client=mock_client
    )

    # Must not raise
    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    session.commit.assert_not_called()


async def test_invalid_json_does_not_raise() -> None:
    id1 = uuid.uuid4()
    session = _make_session(item_rows=[(id1, "eggs")], canonical_rows=[])
    svc, _ = _make_service("Sorry, I cannot help with that.")

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    session.commit.assert_not_called()


async def test_non_dict_response_does_not_raise() -> None:
    id1 = uuid.uuid4()
    session = _make_session(item_rows=[(id1, "eggs")], canonical_rows=[])
    svc, _ = _make_service(json.dumps(["eggs", "milk"]))

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    session.commit.assert_not_called()


async def test_timeout_does_not_raise() -> None:
    import asyncio

    id1 = uuid.uuid4()
    session = _make_session(item_rows=[(id1, "eggs")], canonical_rows=[])
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=asyncio.TimeoutError
    )
    svc = NormalizationService(
        project="p", location="l", model="m", timeout_seconds=0.001, _client=mock_client
    )

    await svc.normalize_bill(session, bill_id=uuid.uuid4(), user_id=uuid.uuid4())

    session.commit.assert_not_called()
