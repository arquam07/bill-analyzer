import uuid
from datetime import date, datetime
from typing import Literal

from sqlalchemy import ColumnElement, DateTime, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from src.models.bill import Bill, BillItem
from src.models.split_request import (
    STATUS_ACCEPTED,
    SplitRequest,
    SplitRequestItem,
)

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


def _item_share_out_subq(user_id: uuid.UUID) -> Subquery:
    """Per-item subquery: sum of accepted outgoing per-item split amounts for this user."""
    return (
        select(
            SplitRequestItem.bill_item_id,
            func.sum(SplitRequestItem.share_amount).label("share_out"),
        )
        .join(SplitRequest, SplitRequest.id == SplitRequestItem.split_request_id)
        .where(
            SplitRequest.from_user_id == user_id,
            SplitRequest.status == STATUS_ACCEPTED,
        )
        .group_by(SplitRequestItem.bill_item_id)
        .subquery("item_share_out")
    )


def _effective_total(split_subq: Subquery) -> object:
    """bill.total minus split amounts (floored at 0)."""
    return func.greatest(
        Bill.total - func.coalesce(split_subq.c.split_out, 0), 0
    )


def _bill_filters_owner(
    user_id: uuid.UUID, range_from: date, range_to: date
) -> list[ColumnElement[bool]]:
    return [
        Bill.user_id == user_id,
        Bill.status == REVIEWED,
        Bill.billed_at.is_not(None),
        Bill.billed_at >= range_from,
        Bill.billed_at <= range_to,
    ]


def _bill_filters_any(range_from: date, range_to: date) -> list[ColumnElement[bool]]:
    """For incoming queries — bill belongs to someone else but appears in this user's stats."""
    return [
        Bill.status == REVIEWED,
        Bill.billed_at.is_not(None),
        Bill.billed_at >= range_from,
        Bill.billed_at <= range_to,
    ]


def _effective_items_subq(
    user_id: uuid.UUID, range_from: date, range_to: date
) -> Subquery:
    """UNION ALL of owner-side items (adjusted for outgoing splits) + incoming item shares.

    Yields one row per "effective item" the user spent on, with bill metadata.
    """
    out_share = _item_share_out_subq(user_id)

    # Coalesce per-item category with bill-level category so manual bills + bills where
    # only the VLM-level category is set still surface in /insights/breakdown?dimension=category.
    coalesced_category = func.coalesce(BillItem.category, Bill.category)

    owner_q = (
        select(
            BillItem.id.label("bill_item_id"),
            BillItem.name.label("name"),
            BillItem.normalized_name.label("normalized_name"),
            coalesced_category.label("category"),
            Bill.merchant.label("merchant"),
            Bill.billed_at.label("billed_at"),
            func.greatest(
                func.coalesce(BillItem.total_price, 0)
                - func.coalesce(out_share.c.share_out, 0),
                0,
            ).label("amount"),
            literal(1).label("cnt"),
        )
        .select_from(BillItem)
        .join(Bill, Bill.id == BillItem.bill_id)
        .outerjoin(out_share, out_share.c.bill_item_id == BillItem.id)
        .where(*_bill_filters_owner(user_id, range_from, range_to))
    )

    incoming_q = (
        select(
            SplitRequestItem.bill_item_id.label("bill_item_id"),
            BillItem.name.label("name"),
            BillItem.normalized_name.label("normalized_name"),
            coalesced_category.label("category"),
            Bill.merchant.label("merchant"),
            Bill.billed_at.label("billed_at"),
            SplitRequestItem.share_amount.label("amount"),
            literal(1).label("cnt"),
        )
        .select_from(SplitRequestItem)
        .join(SplitRequest, SplitRequest.id == SplitRequestItem.split_request_id)
        .join(BillItem, BillItem.id == SplitRequestItem.bill_item_id)
        .join(Bill, Bill.id == BillItem.bill_id)
        .where(
            SplitRequest.to_user_id == user_id,
            SplitRequest.status == STATUS_ACCEPTED,
            *_bill_filters_any(range_from, range_to),
        )
    )

    return union_all(owner_q, incoming_q).subquery("effective_items")


class InsightsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total_and_count(
        self, *, user_id: uuid.UUID, range_from: date, range_to: date
    ) -> tuple[float, int]:
        sq = _split_subq(user_id)
        eff = _effective_total(sq)
        owner_stmt = (
            select(
                func.coalesce(func.sum(eff), 0),
                func.count(Bill.id),
            )
            .outerjoin(sq, sq.c.bill_id == Bill.id)
            .where(*_bill_filters_owner(user_id, range_from, range_to))
        )
        incoming_stmt = (
            select(
                func.coalesce(func.sum(SplitRequest.amount), 0),
                func.count(SplitRequest.id),
            )
            .select_from(SplitRequest)
            .join(Bill, Bill.id == SplitRequest.bill_id)
            .where(
                SplitRequest.to_user_id == user_id,
                SplitRequest.status == STATUS_ACCEPTED,
                *_bill_filters_any(range_from, range_to),
            )
        )
        owner_total, owner_count = (await self._session.execute(owner_stmt)).one()
        inc_total, inc_count = (await self._session.execute(incoming_stmt)).one()
        return (
            float(owner_total or 0) + float(inc_total or 0),
            int(owner_count or 0) + int(inc_count or 0),
        )

    async def top_merchant(
        self, *, user_id: uuid.UUID, range_from: date, range_to: date
    ) -> str | None:
        sq = _split_subq(user_id)
        owner_q = (
            select(
                Bill.merchant.label("merchant"),
                func.greatest(
                    func.coalesce(Bill.total, 0) - func.coalesce(sq.c.split_out, 0),
                    0,
                ).label("amount"),
            )
            .outerjoin(sq, sq.c.bill_id == Bill.id)
            .where(*_bill_filters_owner(user_id, range_from, range_to))
        )
        incoming_q = (
            select(
                Bill.merchant.label("merchant"),
                SplitRequest.amount.label("amount"),
            )
            .select_from(SplitRequest)
            .join(Bill, Bill.id == SplitRequest.bill_id)
            .where(
                SplitRequest.to_user_id == user_id,
                SplitRequest.status == STATUS_ACCEPTED,
                *_bill_filters_any(range_from, range_to),
            )
        )
        combined = union_all(owner_q, incoming_q).subquery("merchant_amounts")
        stmt = (
            select(combined.c.merchant)
            .where(combined.c.merchant.is_not(None))
            .group_by(combined.c.merchant)
            .order_by(func.coalesce(func.sum(combined.c.amount), 0).desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def top_category(
        self, *, user_id: uuid.UUID, range_from: date, range_to: date
    ) -> str | None:
        ei = _effective_items_subq(user_id, range_from, range_to)
        stmt = (
            select(ei.c.category)
            .where(ei.c.category.is_not(None))
            .group_by(ei.c.category)
            .order_by(func.coalesce(func.sum(ei.c.amount), 0).desc())
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
        period_owner = func.date_trunc(
            granularity, cast(Bill.billed_at, DateTime)
        ).label("period")
        owner_stmt = (
            select(
                period_owner,
                func.coalesce(func.sum(eff), 0),
                func.count(Bill.id),
            )
            .outerjoin(sq, sq.c.bill_id == Bill.id)
            .where(*_bill_filters_owner(user_id, range_from, range_to))
            .group_by(period_owner)
        )
        period_inc = func.date_trunc(
            granularity, cast(Bill.billed_at, DateTime)
        ).label("period")
        incoming_stmt = (
            select(
                period_inc,
                func.coalesce(func.sum(SplitRequest.amount), 0),
                func.count(SplitRequest.id),
            )
            .select_from(SplitRequest)
            .join(Bill, Bill.id == SplitRequest.bill_id)
            .where(
                SplitRequest.to_user_id == user_id,
                SplitRequest.status == STATUS_ACCEPTED,
                *_bill_filters_any(range_from, range_to),
            )
            .group_by(period_inc)
        )
        owner_rows = (await self._session.execute(owner_stmt)).all()
        inc_rows = (await self._session.execute(incoming_stmt)).all()

        bucket: dict[date, tuple[float, int]] = {}
        for ts, total, count in list(owner_rows) + list(inc_rows):
            d: date = ts.date() if isinstance(ts, datetime) else ts
            cur_t, cur_c = bucket.get(d, (0.0, 0))
            bucket[d] = (cur_t + float(total or 0), cur_c + int(count or 0))
        return sorted(
            [(d, t, c) for d, (t, c) in bucket.items()],
            key=lambda r: r[0],
        )

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
            ei = _effective_items_subq(user_id, range_from, range_to)
            total_expr = func.coalesce(func.sum(ei.c.amount), 0)
            stmt = (
                select(
                    ei.c.category,
                    total_expr,
                    func.coalesce(func.sum(ei.c.cnt), 0),
                )
                .where(ei.c.category.is_not(None))
                .group_by(ei.c.category)
                .order_by(total_expr.desc())
                .limit(limit)
            )
        else:  # merchant
            sq = _split_subq(user_id)
            owner_q = (
                select(
                    Bill.merchant.label("merchant"),
                    func.greatest(
                        func.coalesce(Bill.total, 0) - func.coalesce(sq.c.split_out, 0),
                        0,
                    ).label("amount"),
                    literal(1).label("cnt"),
                )
                .outerjoin(sq, sq.c.bill_id == Bill.id)
                .where(*_bill_filters_owner(user_id, range_from, range_to))
            )
            incoming_q = (
                select(
                    Bill.merchant.label("merchant"),
                    SplitRequest.amount.label("amount"),
                    literal(1).label("cnt"),
                )
                .select_from(SplitRequest)
                .join(Bill, Bill.id == SplitRequest.bill_id)
                .where(
                    SplitRequest.to_user_id == user_id,
                    SplitRequest.status == STATUS_ACCEPTED,
                    *_bill_filters_any(range_from, range_to),
                )
            )
            combined = union_all(owner_q, incoming_q).subquery("merchant_amounts")
            total_expr = func.coalesce(func.sum(combined.c.amount), 0)
            stmt = (
                select(
                    combined.c.merchant,
                    total_expr,
                    func.coalesce(func.sum(combined.c.cnt), 0),
                )
                .where(combined.c.merchant.is_not(None))
                .group_by(combined.c.merchant)
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
        ei = _effective_items_subq(user_id, range_from, range_to)
        normalized = func.coalesce(
            ei.c.normalized_name,
            func.regexp_replace(func.btrim(func.lower(ei.c.name)), r"\s+", " ", "g"),
        ).label("normalized")
        display = func.min(ei.c.name).label("display")
        total = func.coalesce(func.sum(ei.c.amount), 0).label("total")
        count = func.coalesce(func.sum(ei.c.cnt), 0).label("count")
        last_purchased = func.max(ei.c.billed_at).label("last_purchased")
        order_col = total if order_by == "spend" else count

        stmt = (
            select(display, normalized, total, count, last_purchased)
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
        ei = _effective_items_subq(user_id, range_from, range_to)
        normalized_expr = func.coalesce(
            ei.c.normalized_name,
            func.regexp_replace(func.btrim(func.lower(ei.c.name)), r"\s+", " ", "g"),
        )
        period = func.date_trunc(granularity, cast(ei.c.billed_at, DateTime)).label("period")

        stmt = (
            select(
                period,
                func.coalesce(func.sum(ei.c.amount), 0),
                func.coalesce(func.sum(ei.c.cnt), 0),
            )
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
