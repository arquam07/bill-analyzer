import uuid
from datetime import date, datetime
from typing import Literal

from sqlalchemy import DateTime, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bill import Bill, BillItem
from sqlalchemy.sql.selectable import Subquery

from src.models.split_request import STATUS_ACCEPTED, SplitRequest

REVIEWED = "reviewed"


def _split_subq(user_id: uuid.UUID) -> Subquery:
    """Per-bill subquery: sum of accepted outgoing split amounts for this user."""
    return (
        select(
            SplitRequest.bill_id,
            func.sum(SplitRequest.amount).label("split_out"),
        )
        .where(
            SplitRequest.from_user_id == user_id,
            SplitRequest.status == STATUS_ACCEPTED,
        )
        .group_by(SplitRequest.bill_id)
        .subquery("split_sums")
    )


def _effective_total(split_subq: Subquery) -> object:
    """bill.total minus split amounts (floored at 0)."""
    return func.greatest(
        Bill.total - func.coalesce(split_subq.c.split_out, 0), 0
    )


class InsightsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total_and_count(
        self, *, user_id: uuid.UUID, range_from: date, range_to: date
    ) -> tuple[float, int]:
        sq = _split_subq(user_id)
        eff = _effective_total(sq)
        stmt = (
            select(
                func.coalesce(func.sum(eff), 0),
                func.count(Bill.id),
            )
            .outerjoin(sq, sq.c.bill_id == Bill.id)
            .where(Bill.user_id == user_id)
            .where(Bill.status == REVIEWED)
            .where(Bill.billed_at.is_not(None))
            .where(Bill.billed_at >= range_from)
            .where(Bill.billed_at <= range_to)
        )
        row = (await self._session.execute(stmt)).one()
        return float(row[0] or 0), int(row[1] or 0)

    async def top_merchant(
        self, *, user_id: uuid.UUID, range_from: date, range_to: date
    ) -> str | None:
        stmt = (
            select(Bill.merchant)
            .where(Bill.user_id == user_id)
            .where(Bill.status == REVIEWED)
            .where(Bill.merchant.is_not(None))
            .where(Bill.billed_at.is_not(None))
            .where(Bill.billed_at >= range_from)
            .where(Bill.billed_at <= range_to)
            .group_by(Bill.merchant)
            .order_by(func.coalesce(func.sum(Bill.total), 0).desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def top_category(
        self, *, user_id: uuid.UUID, range_from: date, range_to: date
    ) -> str | None:
        stmt = (
            select(BillItem.category)
            .join(Bill, Bill.id == BillItem.bill_id)
            .where(Bill.user_id == user_id)
            .where(Bill.status == REVIEWED)
            .where(BillItem.category.is_not(None))
            .where(Bill.billed_at.is_not(None))
            .where(Bill.billed_at >= range_from)
            .where(Bill.billed_at <= range_to)
            .group_by(BillItem.category)
            .order_by(func.coalesce(func.sum(BillItem.total_price), 0).desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def timeseries(
        self,
        *,
        user_id: uuid.UUID,
        range_from: date,
        range_to: date,
        granularity: str,
    ) -> list[tuple[date, float, int]]:
        sq = _split_subq(user_id)
        eff = _effective_total(sq)
        period = func.date_trunc(granularity, cast(Bill.billed_at, DateTime)).label("period")
        stmt = (
            select(
                period,
                func.coalesce(func.sum(eff), 0),
                func.count(Bill.id),
            )
            .outerjoin(sq, sq.c.bill_id == Bill.id)
            .where(Bill.user_id == user_id)
            .where(Bill.status == REVIEWED)
            .where(Bill.billed_at.is_not(None))
            .where(Bill.billed_at >= range_from)
            .where(Bill.billed_at <= range_to)
            .group_by(period)
            .order_by(period)
        )
        rows = (await self._session.execute(stmt)).all()
        out: list[tuple[date, float, int]] = []
        for ts, total, count in rows:
            d: date = ts.date() if isinstance(ts, datetime) else ts
            out.append((d, float(total or 0), int(count or 0)))
        return out

    async def breakdown(
        self,
        *,
        user_id: uuid.UUID,
        range_from: date,
        range_to: date,
        dimension: Literal["category", "merchant"],
        limit: int,
    ) -> list[tuple[str, float, int]]:
        if dimension == "category":
            total_expr = func.coalesce(func.sum(BillItem.total_price), 0)
            stmt = (
                select(
                    BillItem.category,
                    total_expr,
                    func.count(BillItem.id),
                )
                .join(Bill, Bill.id == BillItem.bill_id)
                .where(Bill.user_id == user_id)
                .where(Bill.status == REVIEWED)
                .where(BillItem.category.is_not(None))
                .where(Bill.billed_at.is_not(None))
                .where(Bill.billed_at >= range_from)
                .where(Bill.billed_at <= range_to)
                .group_by(BillItem.category)
                .order_by(total_expr.desc())
                .limit(limit)
            )
        else:  # merchant
            total_expr = func.coalesce(func.sum(Bill.total), 0)
            stmt = (
                select(
                    Bill.merchant,
                    total_expr,
                    func.count(Bill.id),
                )
                .where(Bill.user_id == user_id)
                .where(Bill.status == REVIEWED)
                .where(Bill.merchant.is_not(None))
                .where(Bill.billed_at.is_not(None))
                .where(Bill.billed_at >= range_from)
                .where(Bill.billed_at <= range_to)
                .group_by(Bill.merchant)
                .order_by(total_expr.desc())
                .limit(limit)
            )
        rows = (await self._session.execute(stmt)).all()
        return [(label, float(total or 0), int(count or 0)) for label, total, count in rows]

    async def top_items(
        self,
        *,
        user_id: uuid.UUID,
        range_from: date,
        range_to: date,
        order_by: Literal["spend", "frequency"],
        limit: int,
    ) -> list[tuple[str, str, float, int, date | None]]:
        # Normalize: lower + collapse internal whitespace + trim.
        normalized = func.regexp_replace(
            func.btrim(func.lower(BillItem.name)), r"\s+", " ", "g"
        ).label("normalized")
        display = func.min(BillItem.name).label("display")
        total = func.coalesce(func.sum(BillItem.total_price), 0).label("total")
        count = func.count(BillItem.id).label("count")
        last_purchased = func.max(Bill.billed_at).label("last_purchased")
        order_col = total if order_by == "spend" else count

        stmt = (
            select(display, normalized, total, count, last_purchased)
            .join(Bill, Bill.id == BillItem.bill_id)
            .where(Bill.user_id == user_id)
            .where(Bill.status == REVIEWED)
            .where(Bill.billed_at.is_not(None))
            .where(Bill.billed_at >= range_from)
            .where(Bill.billed_at <= range_to)
            .group_by(normalized)
            .order_by(order_col.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            (d, n, float(t or 0), int(c or 0), last)
            for d, n, t, c, last in rows
        ]

    async def bills_missing_date(
        self, *, user_id: uuid.UUID
    ) -> int:
        stmt = (
            select(func.count(Bill.id))
            .where(Bill.user_id == user_id)
            .where(Bill.status == REVIEWED)
            .where(Bill.billed_at.is_(None))
        )
        result = (await self._session.execute(stmt)).scalar_one()
        return int(result or 0)

    async def item_timeseries(
        self,
        *,
        user_id: uuid.UUID,
        normalized_name: str,
        range_from: date,
        range_to: date,
        granularity: str,
    ) -> tuple[float, int, list[tuple[date, float, int]]]:
        normalized_expr = func.regexp_replace(
            func.btrim(func.lower(BillItem.name)), r"\s+", " ", "g"
        )
        period = func.date_trunc(granularity, cast(Bill.billed_at, DateTime)).label("period")

        stmt = (
            select(
                period,
                func.coalesce(func.sum(BillItem.total_price), 0),
                func.count(BillItem.id),
            )
            .join(Bill, Bill.id == BillItem.bill_id)
            .where(Bill.user_id == user_id)
            .where(Bill.status == REVIEWED)
            .where(Bill.billed_at.is_not(None))
            .where(Bill.billed_at >= range_from)
            .where(Bill.billed_at <= range_to)
            .where(normalized_expr == normalized_name)
            .group_by(period)
            .order_by(period)
        )
        rows = (await self._session.execute(stmt)).all()
        points: list[tuple[date, float, int]] = []
        total_spend = 0.0
        total_count = 0
        for ts, t, c in rows:
            d: date = ts.date() if isinstance(ts, datetime) else ts
            points.append((d, float(t or 0), int(c or 0)))
            total_spend += float(t or 0)
            total_count += int(c or 0)
        return total_spend, total_count, points
