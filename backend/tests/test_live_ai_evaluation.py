"""Optional real-model grounding evaluations; enable explicitly to use OpenAI credits."""

import asyncio
import os

import pytest

from backend.schemas.screen import MatchingStock, ScreeningCriteria
from backend.services.ai_service import AIService
from backend.services.explanation_service import portfolio_evidence, stock_evidence
from backend.services.portfolio_service import PortfolioService
from backend.services.scoring_service import score_equity

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_OPENAI_EVAL") != "1",
    reason="Set RUN_LIVE_OPENAI_EVAL=1 and OPENAI_API_KEY for paid real-model evaluations",
)


def assert_grounded(result, evidence):
    assert result
    for key in evidence.required_ids:
        assert evidence.facts[key] in result
    assert all(paragraph in evidence.facts.values() for paragraph in result.split("\n\n"))


def test_live_openai_stock_explanation_is_grounded():
    async def evaluate():
        service = AIService()
        if service._client is None:
            pytest.fail("OPENAI_API_KEY is required when RUN_LIVE_OPENAI_EVAL=1")
        try:
            metrics = {
                "ticker": "TEST", "pe_ratio": 18, "revenue_growth": 15,
                "profit_margin": 12, "current_ratio": 1.6,
            }
            stock = MatchingStock(
                ticker="TEST", metrics=metrics, score=score_equity(metrics), passed_criteria=[],
            )
            assert stock.score.overall_score == 79.7
            criteria = ScreeningCriteria()
            result = await service.explain_screen_match(stock, criteria)
            assert_grounded(result, stock_evidence(stock, criteria))
        finally:
            await service._client.close()

    asyncio.run(evaluate())


def test_live_openai_portfolio_explanation_is_grounded():
    async def evaluate():
        service = AIService()
        if service._client is None:
            pytest.fail("OPENAI_API_KEY is required when RUN_LIVE_OPENAI_EVAL=1")
        try:
            # Cash uses the actual portfolio pipeline without a market-data request.
            summary = await PortfolioService(None, service).analyze([
                {"ticker": None, "name": "Cash", "type": "cash", "shares": None,
                 "price": None, "value": 125},
            ])
            evidence = summary.model_dump(by_alias=True, exclude={"ai_explanation"})
            assert summary.concentration_hhi == 10000
            result = await service.explain_portfolio(evidence)
            assert_grounded(result, portfolio_evidence(evidence))
        finally:
            await service._client.close()

    asyncio.run(evaluate())
