from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import InvalidInsightsRange
from src.models.user import User
from src.schemas.insights import (
    BreakdownRow,
    Dimension,
    Granularity,
    InsightsBreakdownResponse,
    InsightsOverviewResponse,
    InsightsTimeseriesResponse,
    InsightsTopItemsResponse,
    ItemOrderBy,
    ItemTimeseriesPoint,
    ItemTimeseriesResponse,
    TimeseriesPoint,
    TopItem,
)
from src.services.repositories.insights_repository import InsightsRepository

DEFAULT_RANGE_DAYS = 90
MAX_RANGE_DAYS = 366


def _today() -> date:
    return datetime.now(UTC).date()


def _resolve_range(range_from: date | None, range_to: date | None) -> tuple[date, date]:
    rt = range_to if range_to is not None else _today()
    rf = range_from if range_from is not None else rt - timedelta(days=DEFAULT_RANGE_DAYS)
    return rf, rt


def _validate_range(range_from: date, range_to: date) -> None:
    if range_from > range_to:
        raise InvalidInsightsRange("from must be <= to")
    if (range_to - range_from).days > MAX_RANGE_DAYS:
        raise InvalidInsightsRange("range exceeds 12-month cap")


class InsightsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = InsightsRepository(session)

    async def overview(
        self,
        *,
        user: User,
        range_from: date | None,
        range_to: date | None,
    ) -> InsightsOverviewResponse:
        rf, rt = _resolve_range(range_from, range_to)
        _validate_range(rf, rt)

        total, count = await self._repo.total_and_count(user_id=user.id, range_from=rf, range_to=rt)
        top_merchant = await self._repo.top_merchant(user_id=user.id, range_from=rf, range_to=rt)
        top_category = await self._repo.top_category(user_id=user.id, range_from=rf, range_to=rt)
        missing_date = await self._repo.bills_missing_date(user_id=user.id)

        duration = rt - rf
        prev_to = rf - timedelta(days=1)
        prev_from = prev_to - duration
        prev_total, _ = await self._repo.total_and_count(
            user_id=user.id, range_from=prev_from, range_to=prev_to
        )

        delta_pct: float | None
        if prev_total == 0:
            delta_pct = None
        else:
            delta_pct = (total - prev_total) / prev_total * 100.0

        avg_bill = total / count if count else 0.0

        return InsightsOverviewResponse(
            range_from=rf,
            range_to=rt,
            total_spend=total,
            bill_count=count,
            avg_bill=avg_bill,
            top_category=top_category,
            top_merchant=top_merchant,
            prev_total_spend=prev_total,
            spend_delta_pct=delta_pct,
            bills_missing_date=missing_date,
        )

    async def timeseries(
        self,
        *,
        user: User,
        range_from: date | None,
        range_to: date | None,
        granularity: Granularity,
    ) -> InsightsTimeseriesResponse:
        rf, rt = _resolve_range(range_from, range_to)
        _validate_range(rf, rt)

        rows = await self._repo.timeseries(
            user_id=user.id,
            range_from=rf,
            range_to=rt,
            granularity=granularity,
        )
        return InsightsTimeseriesResponse(
            range_from=rf,
            range_to=rt,
            granularity=granularity,
            points=[TimeseriesPoint(period=d, total=t, count=c) for d, t, c in rows],
        )

    async def breakdown(
        self,
        *,
        user: User,
        range_from: date | None,
        range_to: date | None,
        dimension: Dimension,
        limit: int,
    ) -> InsightsBreakdownResponse:
        rf, rt = _resolve_range(range_from, range_to)
        _validate_range(rf, rt)

        rows = await self._repo.breakdown(
            user_id=user.id,
            range_from=rf,
            range_to=rt,
            dimension=dimension,
            limit=limit,
        )
        return InsightsBreakdownResponse(
            range_from=rf,
            range_to=rt,
            dimension=dimension,
            rows=[BreakdownRow(label=label, total=total, count=count) for label, total, count in rows],
        )

    async def top_items(
        self,
        *,
        user: User,
        range_from: date | None,
        range_to: date | None,
        order_by: ItemOrderBy,
        limit: int,
    ) -> InsightsTopItemsResponse:
        rf, rt = _resolve_range(range_from, range_to)
        _validate_range(rf, rt)

        rows = await self._repo.top_items(
            user_id=user.id,
            range_from=rf,
            range_to=rt,
            order_by=order_by,
            limit=limit,
        )
        return InsightsTopItemsResponse(
            range_from=rf,
            range_to=rt,
            order_by=order_by,
            rows=[
                TopItem(
                    name=display,
                    normalized_name=normalized,
                    total_spend=total,
                    purchase_count=count,
                    last_purchased=last,
                )
                for display, normalized, total, count, last in rows
            ],
        )

    async def item_timeseries(
        self,
        *,
        user: User,
        normalized_name: str,
        range_from: date | None,
        range_to: date | None,
        granularity: Granularity,
    ) -> ItemTimeseriesResponse:
        rf, rt = _resolve_range(range_from, range_to)
        _validate_range(rf, rt)

        total_spend, purchase_count, points = await self._repo.item_timeseries(
            user_id=user.id,
            normalized_name=normalized_name,
            range_from=rf,
            range_to=rt,
            granularity=granularity,
        )
        return ItemTimeseriesResponse(
            normalized_name=normalized_name,
            range_from=rf,
            range_to=rt,
            granularity=granularity,
            total_spend=total_spend,
            purchase_count=purchase_count,
            points=[ItemTimeseriesPoint(period=d, total=t, count=c) for d, t, c in points],
        )
