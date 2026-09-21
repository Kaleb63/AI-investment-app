import asyncio

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.screen import ScreenRequest
from backend.services.cache import MemoryTTLCache
from backend.services.screening_service import ScreeningService


def make_metrics(ticker, **overrides):
    metrics = {
        "ticker": ticker,
        "pe_ratio": 15,
        "eps": 5,
        "revenue_growth": 25,
        "eps_growth": 25,
        "profit_margin": 25,
        "return_on_equity": 25,
        "current_ratio": 2,
        "beta": 1,
        "52_week_return": 25,
    }
    metrics.update(overrides)
    return metrics


class FakeMarketData:
    def __init__(self, values):
        self.values = values
        self.requests = []

    async def get_clean_metrics(self, ticker):
        self.requests.append(ticker)
        value = self.values[ticker]
        if isinstance(value, Exception):
            raise value
        return value


def test_screen_separates_matches_rejections_missing_data_and_errors():
    from backend.errors import ProviderError

    market = FakeMarketData(
        {
            "PASS": make_metrics("PASS"),
            "FAIL": make_metrics("FAIL", pe_ratio=45, revenue_growth=5),
            "MISSING": make_metrics("MISSING", pe_ratio=None),
            "ERROR": ProviderError("provider_error", "Finnhub unavailable", 502),
        }
    )
    service = ScreeningService(market, MemoryTTLCache())
    request = ScreenRequest(
        tickers=["pass", "FAIL", "MISSING", "ERROR"],
        min_score=70,
        max_pe_ratio=30,
        min_revenue_growth=10,
    )

    result = asyncio.run(service.screen(request))

    assert result.summary.model_dump() == {
        "total_requested": 4,
        "successfully_analyzed": 2,
        "matched": 1,
        "rejected": 1,
        "unavailable": 1,
        "errored": 1,
    }
    assert [stock.ticker for stock in result.matching_stocks] == ["PASS"]
    assert {item.criterion for item in result.rejected_stocks[0].failed_criteria} == {
        "max_pe_ratio",
        "min_revenue_growth",
    }
    assert result.unavailable_stocks[0].missing_criteria[0].criterion == "max_pe_ratio"
    assert result.unavailable_stocks[1].reason == "Finnhub unavailable"


def test_rejection_reports_unavailable_criteria_too():
    market = FakeMarketData({"TEST": make_metrics("TEST", pe_ratio=50, current_ratio=None)})
    service = ScreeningService(market, MemoryTTLCache())
    request = ScreenRequest(
        tickers=["TEST"],
        max_pe_ratio=30,
        min_current_ratio=1.2,
    )

    result = asyncio.run(service.screen(request))

    rejected = result.rejected_stocks[0]
    assert rejected.failed_criteria[0].criterion == "max_pe_ratio"
    assert rejected.unevaluated_criteria[0].criterion == "min_current_ratio"


def test_duplicate_tickers_are_normalized_once():
    request = ScreenRequest(tickers=["aapl", " AAPL "])
    market = FakeMarketData({"AAPL": make_metrics("AAPL")})
    result = asyncio.run(ScreeningService(market, MemoryTTLCache()).screen(request))

    assert result.summary.total_requested == 1
    assert market.requests == ["AAPL"]


def test_invalid_request_returns_consistent_422_response():
    with TestClient(app) as client:
        response = client.post("/screen", json={"tickers": []})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_criterion_is_rejected():
    with TestClient(app) as client:
        response = client.post("/screen", json={"tickers": ["AAPL"], "min_score": 101})

    assert response.status_code == 422


def test_malformed_ticker_is_rejected():
    with TestClient(app) as client:
        response = client.post("/screen", json={"tickers": ["not a ticker"]})

    assert response.status_code == 422
