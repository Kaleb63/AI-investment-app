import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, get_optional_user
from backend.errors import AppError
from backend.models import SavedScreen, ScanHistory, User
from backend.schemas.screen import (
    AIScreenRequest,
    AIScreenResponse,
    SavedScreenCreate,
    SavedScreenResponse,
    ScreenRequest,
    ScreenResponse,
)
from backend.services.ai_service import ai_service
from backend.services.screening_service import screening_service
from backend.services.stock_universe_service import stock_universe_service

router = APIRouter(tags=["screening"])


def _save_scan(db: Session, user: User | None, result: ScreenResponse) -> None:
    db.add(
        ScanHistory(
            user_id=user.id if user else None,
            criteria=result.criteria.model_dump(exclude_none=True),
            stocks_analyzed=result.summary.successfully_analyzed,
            matches=result.summary.matched,
            failures=(result.summary.unavailable + result.summary.errored),
            duration_seconds=result.performance.duration_seconds,
            result_summary=result.summary.model_dump(),
        )
    )
    db.commit()


@router.post(
    "/screen",
    response_model=ScreenResponse,
    summary="Screen stocks using deterministic financial rules",
)
async def screen_stocks(
    request: ScreenRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    result = await screening_service.screen(request)
    _save_scan(db, user, result)
    return result


@router.get("/stock_universe", summary="List supported U.S. equities and ETFs")
async def stock_universe(
    exchange: str = Query(default="US", min_length=1, max_length=10),
    asset_type: Literal["equity", "etf"] | None = None,
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    return await stock_universe_service.list_symbols(
        exchange=exchange,
        asset_type=asset_type,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/ai_screen",
    response_model=AIScreenResponse,
    summary="Translate natural language into deterministic screening criteria",
)
async def ai_screen(
    request: AIScreenRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    criteria = await ai_service.parse_screening_query(request.query)
    tickers = request.tickers
    if tickers is None:
        universe = await stock_universe_service.list_symbols(
            asset_type="equity", limit=request.universe_limit
        )
        tickers = [item["ticker"] for item in universe["symbols"]]
    if not tickers:
        raise AppError("empty_universe", "No stocks were available to screen", 503)

    screen_request = ScreenRequest(
        tickers=tickers,
        weights=request.weights,
        **criteria.model_dump(exclude_none=True),
    )
    result = await screening_service.screen(screen_request)
    explanation_errors = {}
    if request.include_explanations and result.matching_stocks:
        explanation_tasks = [
            ai_service.explain_screen_match(stock, criteria) for stock in result.matching_stocks
        ]
        explanations = await asyncio.gather(*explanation_tasks, return_exceptions=True)
        for stock, explanation in zip(result.matching_stocks, explanations, strict=True):
            if isinstance(explanation, Exception):
                explanation_errors[stock.ticker] = "AI explanation unavailable"
            else:
                stock.ai_explanation = explanation

    _save_scan(db, user, result)
    return AIScreenResponse(
        query=request.query,
        interpreted_criteria=criteria,
        number_of_stocks_searched=len(tickers),
        results=result,
        explanation_errors=explanation_errors,
    )


@router.post(
    "/saved_screens",
    response_model=SavedScreenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save screening criteria",
)
def save_screen(
    request: SavedScreenCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = SavedScreen(
        user_id=user.id,
        name=request.name.strip(),
        criteria=request.criteria.model_dump(exclude_none=True),
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.get(
    "/saved_screens",
    response_model=list[SavedScreenResponse],
    summary="List the signed-in user's saved screens",
)
def list_saved_screens(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(SavedScreen)
            .where(SavedScreen.user_id == user.id)
            .order_by(SavedScreen.created_at.desc())
        )
    )


@router.delete("/saved_screens/{screen_id}", status_code=204)
def delete_saved_screen(
    screen_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = db.scalar(
        select(SavedScreen).where(
            SavedScreen.id == screen_id,
            SavedScreen.user_id == user.id,
        )
    )
    if saved is None:
        raise AppError("saved_screen_not_found", "Saved screen was not found", 404)
    db.delete(saved)
    db.commit()


@router.get("/scan_history", summary="List the signed-in user's scan history")
def scan_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = db.scalars(
        select(ScanHistory)
        .where(ScanHistory.user_id == user.id)
        .order_by(ScanHistory.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": record.id,
            "criteria": record.criteria,
            "stocks_analyzed": record.stocks_analyzed,
            "matches": record.matches,
            "failures": record.failures,
            "duration_seconds": record.duration_seconds,
            "summary": record.result_summary,
            "created_at": record.created_at,
        }
        for record in records
    ]
