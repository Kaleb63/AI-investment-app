"""Exercise stock HTTP contracts with isolated storage and no external API calls."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.dependencies import get_optional_user
from backend.errors import ProviderError
from backend.main import create_app
from backend.models import AnalysisHistory, User
from backend.routes import stocks

ENDPOINTS = ("/analysis", "/ai_analysis")


def stock_metrics(**overrides):
    values = {
        "ticker": "AAPL",
        "pe_ratio": 12,
        "eps": 5,
        "revenue_growth": 25,
        "eps_growth": 25,
        "profit_margin": 25,
        "return_on_equity": 25,
        "current_ratio": 2,
        "beta": 1,
        "52_week_return": 25,
    }
    values.update(overrides)
    return values


@pytest.fixture
def stock_db(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'stocks.sqlite3').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def stock_app(stock_db):
    application = create_app()

    def isolated_db():
        with stock_db() as session:
            yield session

    application.dependency_overrides[get_db] = isolated_db
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def stock_client(stock_app):
    with TestClient(stock_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def market_metrics(monkeypatch):
    mock = AsyncMock(return_value=stock_metrics())
    monkeypatch.setattr(stocks.finnhub_service, "get_clean_metrics", mock)
    return mock


@pytest.fixture(autouse=True)
def explanation(monkeypatch):
    mock = AsyncMock(return_value="Explanation based on supplied scoring evidence.")
    monkeypatch.setattr(stocks.ai_service, "explain_screen_match", mock)
    return mock


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_stock_endpoint_returns_exact_category_and_weighted_scores(
    endpoint, stock_client, market_metrics
):
    market_metrics.return_value = stock_metrics(
        pe_ratio=30,
        revenue_growth=10,
        eps_growth=-5,
        profit_margin=15,
        return_on_equity=5,
        current_ratio=1.2,
        **{"52_week_return": -5},
    )

    response = stock_client.get(f"{endpoint}/AAPL")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["metrics"] == market_metrics.return_value
    assert body["score"]["categories"] == {
        "valuation": 50,
        "growth": 57.5,
        "profitability": 70,
        "financial_health": 70,
        "momentum": 40,
    }
    assert body["score"]["weights"] == {
        "valuation": 20,
        "growth": 25,
        "profitability": 25,
        "financial_health": 15,
        "momentum": 15,
    }
    assert body["score"]["overall_score"] == 58.4
    assert body["score"]["signal"] == "mixed"
    assert body["score"]["data_coverage"] == 100
    assert "EPS growth is negative" in body["score"]["reasons"]
    market_metrics.assert_awaited_once_with("AAPL")


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_stock_endpoint_reweights_missing_category_without_inventing_metric(
    endpoint, stock_client, market_metrics
):
    market_metrics.return_value = stock_metrics(pe_ratio=None)

    response = stock_client.get(f"{endpoint}/AAPL")

    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["pe_ratio"] is None
    assert body["score"]["categories"]["valuation"] is None
    assert body["score"]["data_coverage"] == 80
    assert body["score"]["overall_score"] == 100
    assert body["score"]["signal"] == "positive"
    assert not any("P/E" in reason for reason in body["score"]["reasons"])


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_stock_endpoint_preserves_insufficient_data_instead_of_scoring_zero(
    endpoint, stock_client, market_metrics
):
    market_metrics.return_value = {
        key: value if key == "ticker" else None for key, value in stock_metrics().items()
    }

    response = stock_client.get(f"{endpoint}/AAPL")

    assert response.status_code == 200
    score = response.json()["score"]
    assert score["overall_score"] is None
    assert score["signal"] == "insufficient_data"
    assert score["data_coverage"] == 0
    assert all(value is None for value in score["categories"].values())
    assert score["reasons"] == []


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_stock_endpoint_normalizes_ticker_before_requesting_data(
    endpoint, stock_client, market_metrics
):
    response = stock_client.get(f"{endpoint}/ aapl ")

    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"
    market_metrics.assert_awaited_once_with("AAPL")


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("ticker", ("bad ticker", "123", "A" * 16))
def test_stock_endpoint_rejects_invalid_ticker_before_provider_or_ai_calls(
    endpoint, ticker, stock_client, market_metrics, explanation
):
    response = stock_client.get(f"{endpoint}/{ticker}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    market_metrics.assert_not_awaited()
    explanation.assert_not_awaited()


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize(
    ("code", "message", "status"),
    (
        ("provider_unavailable", "Market data is temporarily unavailable", 502),
        ("rate_limited", "Market data request limit reached", 429),
        ("not_found", "No market data found for ticker", 404),
    ),
)
def test_stock_endpoint_returns_provider_failure_without_ai_or_history(
    endpoint, code, message, status, stock_client, market_metrics, explanation, stock_db
):
    market_metrics.side_effect = ProviderError(code, message, status)

    response = stock_client.get(f"{endpoint}/AAPL")

    assert response.status_code == status
    assert response.json() == {"error": {"code": code, "message": message}}
    explanation.assert_not_awaited()
    with stock_db() as session:
        assert session.scalars(select(AnalysisHistory)).all() == []


@pytest.mark.parametrize("authenticated", (False, True))
def test_analysis_persists_exact_metrics_and_score_snapshot(
    authenticated, stock_app, stock_client, market_metrics, stock_db
):
    expected_user_id = None
    if authenticated:
        user = User(
            id="stock-endpoint-user",
            email="stocks@example.com",
            password_hash="unused-in-this-test",
        )
        with stock_db() as session:
            session.add(user)
            session.commit()
        stock_app.dependency_overrides[get_optional_user] = lambda: user
        expected_user_id = user.id

    response = stock_client.get("/analysis/AAPL")

    assert response.status_code == 200
    body = response.json()
    market_metrics.return_value["pe_ratio"] = 999
    with stock_db() as session:
        history = session.scalars(select(AnalysisHistory)).one()
        assert history.user_id == expected_user_id
        assert history.ticker == body["ticker"]
        assert history.metrics_snapshot == body["metrics"]
        assert history.score_snapshot == body["score"]
        assert history.overall_score == body["score"]["overall_score"]
        assert history.metrics_snapshot["pe_ratio"] == 12


def test_ai_endpoint_explains_the_same_score_and_metrics_it_returns(
    stock_client, market_metrics, explanation
):
    response = stock_client.get("/ai_analysis/aapl")

    assert response.status_code == 200
    body = response.json()
    explanation.assert_awaited_once()
    supplied_stock, _criteria = explanation.await_args.args
    assert supplied_stock.ticker == body["ticker"] == "AAPL"
    assert supplied_stock.metrics.model_dump(by_alias=True) == body["metrics"]
    assert supplied_stock.score.model_dump() == body["score"]
    assert body["ai_explanation"] == explanation.return_value
    market_metrics.assert_awaited_once_with("AAPL")
