from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.errors import AppError
from backend.models import User, WatchlistEntry
from backend.schemas.screen import ScreenRequest, ScreenResponse
from backend.schemas.watchlist import WatchlistCreate, WatchlistResponse
from backend.services.finnhub_service import finnhub_service
from backend.services.screening_service import screening_service

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get(
    "",
    response_model=list[WatchlistResponse],
    summary="List the signed-in user's watchlist",
)
def list_watchlist(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(WatchlistEntry)
            .where(WatchlistEntry.user_id == user.id)
            .order_by(WatchlistEntry.created_at.desc())
        )
    )


@router.post(
    "",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a validated ticker to the watchlist",
)
async def add_to_watchlist(
    request: WatchlistCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    await finnhub_service.get_quote(request.ticker)
    entry = WatchlistEntry(user_id=user.id, ticker=request.ticker)
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except IntegrityError as exc:
        db.rollback()
        raise AppError("watchlist_duplicate", "Ticker is already on the watchlist", 409) from exc
    return entry


@router.delete("/{ticker}", status_code=204, summary="Remove a watchlist ticker")
def remove_from_watchlist(
    ticker: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.strip().upper()
    entry = db.scalar(
        select(WatchlistEntry).where(
            WatchlistEntry.user_id == user.id,
            WatchlistEntry.ticker == ticker,
        )
    )
    if entry is None:
        raise AppError("watchlist_entry_not_found", "Ticker is not on the watchlist", 404)
    db.delete(entry)
    db.commit()


@router.get(
    "/analysis",
    response_model=ScreenResponse,
    summary="Analyze every ticker on the watchlist",
)
async def analyze_watchlist(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tickers = list(
        db.scalars(select(WatchlistEntry.ticker).where(WatchlistEntry.user_id == user.id))
    )
    if not tickers:
        raise AppError("watchlist_empty", "The watchlist is empty", 400)
    return await screening_service.screen(ScreenRequest(tickers=tickers))
