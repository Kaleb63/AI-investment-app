"""Verify HTTP behavior with real AI validation and only the model transport replaced."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.routes import demo, stocks
from backend.services.ai_service import AIService
from backend.services.portfolio_service import portfolio_service


@pytest.fixture
def explanation_api(monkeypatch):
    ai = AIService()
    parse = AsyncMock()
    ai._client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    monkeypatch.setattr(stocks, "ai_service", ai)
    monkeypatch.setattr(portfolio_service, "ai", ai)
    monkeypatch.setattr(
        stocks.finnhub_service, "get_clean_metrics",
        AsyncMock(return_value={"ticker": "TEST", "pe_ratio": 18}),
    )
    monkeypatch.setattr(demo, "settings", SimpleNamespace(demo_mode=True))
    with TestClient(create_app()) as client:
        yield client, parse


@pytest.mark.parametrize("payload", [
    {"evidence_ids": ["metric.pe_ratio"]},
    {"evidence_ids": ["score.overall"]},
])
def test_stock_http_response_uses_calculated_figures(explanation_api, payload):
    client, parse = explanation_api
    parse.return_value = SimpleNamespace(
        output_parsed=payload, status="completed", output_text="Invented score: 999."
    )

    response = client.get("/ai_analysis/test")

    assert response.status_code == 200
    body = response.json()
    assert body["score"]["overall_score"] == 75
    assert body["score"]["data_coverage"] == 20
    assert "stock score of 75/100" in body["ai_explanation"]
    assert "Valuation 75/100" in body["ai_explanation"]
    assert "20% of the configured model weight" in body["ai_explanation"]
    assert "999" not in body["ai_explanation"]


@pytest.mark.parametrize("payload", [
    {"evidence_ids": ["score.overall"], "overall_score": 18},
    {"evidence_ids": ["invented.future_earnings"]},
    None,
])
def test_stock_http_response_rejects_unverified_ai_output(explanation_api, payload):
    client, parse = explanation_api
    parse.return_value = SimpleNamespace(output_parsed=payload, status="completed")

    response = client.get("/ai_analysis/TEST")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_ai_explanation"
    assert "ai_explanation" not in response.json()


def test_demo_portfolio_keeps_calculations_when_ai_output_is_invalid(explanation_api):
    client, parse = explanation_api
    parse.return_value = SimpleNamespace(
        output_parsed={"evidence_ids": ["invented.holding"]}, status="completed"
    )

    response = client.get("/demo/portfolio_analysis?include_ai=true")

    assert response.status_code == 200
    result = response.json()
    assert result["simulated"] is True
    assert result["total_value"] > 0
    assert result["holdings"]
    assert result["ai_explanation"] is None
    parse.assert_awaited_once()
