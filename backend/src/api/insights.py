from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.exceptions import InvalidInsightsRange
from src.models.user import User
from src.schemas.insights import (
    Dimension,
    Granularity,
    InsightsBreakdownResponse,
    InsightsOverviewResponse,
    InsightsTimeseriesResponse,
    InsightsTopItemsResponse,
    ItemOrderBy,
)
from src.services.insights_service import InsightsService

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/overview", response_model=InsightsOverviewResponse)
async def overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
) -> InsightsOverviewResponse:
    try:
        return await InsightsService(db).overview(
            user=user, range_from=range_from, range_to=range_to
        )
    except InvalidInsightsRange as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.get("/breakdown", response_model=InsightsBreakdownResponse)
async def breakdown(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dimension: Dimension = Query(...),
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=10, ge=1, le=50),
) -> InsightsBreakdownResponse:
    try:
        return await InsightsService(db).breakdown(
            user=user,
            range_from=range_from,
            range_to=range_to,
            dimension=dimension,
            limit=limit,
        )
    except InvalidInsightsRange as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.get("/items", response_model=InsightsTopItemsResponse)
async def top_items(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
    order_by: ItemOrderBy = Query(default="spend"),
    limit: int = Query(default=20, ge=1, le=100),
) -> InsightsTopItemsResponse:
    try:
        return await InsightsService(db).top_items(
            user=user,
            range_from=range_from,
            range_to=range_to,
            order_by=order_by,
            limit=limit,
        )
    except InvalidInsightsRange as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.get("/timeseries", response_model=InsightsTimeseriesResponse)
async def timeseries(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
    granularity: Granularity = Query(default="month"),
) -> InsightsTimeseriesResponse:
    try:
        return await InsightsService(db).timeseries(
            user=user,
            range_from=range_from,
            range_to=range_to,
            granularity=granularity,
        )
    except InvalidInsightsRange as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
