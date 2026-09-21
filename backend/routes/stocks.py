from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_optional_user
from backend.models import AnalysisHistory, User
from backend.schemas.common import normalize_ticker
from backend.schemas.stock import StockAnalysis
from backend.services.ai_service import ai_service
from backend.services.finnhub_service import finnhub_service
from backend.services.historical_service import historical_service
from backend.services.scoring_service import score_equity

router = APIRouter(tags=["stocks"])
DEMO_SHARES = {"AAPL": 5, "NVDA": 2, "TSLA": 3}


@router.get("/stock/{ticker}", summary="Get a current stock quote")
async def stock_quote(ticker: str):
    ticker = normalize_ticker(ticker)
    quote = await finnhub_service.get_quote(ticker)
    shares = DEMO_SHARES.get(ticker)
    result = {"ticker": ticker, "price": quote["c"], "quote": quote}
    if shares is not None:
        result.update({"shares": shares, "value": quote["c"] * shares})
    return result


@router.get("/metrics/{ticker}", summary="Get normalized financial metrics")
async def stock_metrics(ticker: str):
    return await finnhub_service.get_clean_metrics(normalize_ticker(ticker))


@router.get(
    "/analysis/{ticker}",
    response_model=StockAnalysis,
    summary="Run deterministic equity analysis",
)
async def stock_analysis(
    ticker: str,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    ticker = normalize_ticker(ticker)
    metrics = await finnhub_service.get_clean_metrics(ticker)
    score = score_equity(metrics)
    db.add(
        AnalysisHistory(
            user_id=user.id if user else None,
            ticker=ticker,
            metrics_snapshot=metrics,
            score_snapshot=score,
            overall_score=score["overall_score"],
        )
    )
    db.commit()
    return {"ticker": ticker, "metrics": metrics, "score": score}


@router.get("/ai_analysis/{ticker}", summary="Explain deterministic stock analysis")
async def ai_stock_analysis(ticker: str):
    ticker = normalize_ticker(ticker)
    metrics = await finnhub_service.get_clean_metrics(ticker)
    score = score_equity(metrics)
    from backend.schemas.screen import MatchingStock, ScreeningCriteria

    stock = MatchingStock(
        ticker=ticker,
        metrics=metrics,
        score=score,
        passed_criteria=[],
    )
    explanation = await ai_service.explain_screen_match(stock, ScreeningCriteria())
    return {
        "ticker": ticker,
        "metrics": metrics,
        "score": score,
        "ai_explanation": explanation,
    }


@router.get(
    "/historical/{ticker}",
    summary="Calculate historical returns, volatility, and moving averages",
)
async def historical_analysis(ticker: str):
    return await historical_service.analyze(normalize_ticker(ticker))
