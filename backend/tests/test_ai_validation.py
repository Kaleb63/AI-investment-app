"""Exercise real explanation generation with adversarial, offline model replies.

The OpenAI transport is replaced; scoring, portfolio calculations, evidence
construction, schema validation, and final rendering all run as production code.
These tests establish grounding and fail-closed behavior without API credentials.
"""

import asyncio
import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from backend.errors import AppError, ProviderError
from backend.schemas.explanation import EvidenceSelection
from backend.schemas.screen import MatchingStock, ScreeningCriteria
from backend.schemas.stock import ScoringWeights, StockMetrics
from backend.services.ai_service import AIService
from backend.services.explanation_service import stock_evidence
from backend.services.portfolio_service import PortfolioService
from backend.services.scoring_service import score_equity


@pytest.fixture
def criteria():
    return ScreeningCriteria(min_score=70, max_pe_ratio=25, min_profit_margin=10)


def make_stock(*, pe_ratio=18, weights=None):
    metrics = StockMetrics(
        ticker="TEST",
        pe_ratio=pe_ratio,
        revenue_growth=15,
        profit_margin=12,
        current_ratio=1.6,
    )
    score = score_equity(metrics.model_dump(by_alias=True), weights)
    return MatchingStock(
        ticker="TEST",
        metrics=metrics,
        score=score,
        passed_criteria=["min_score", "max_pe_ratio", "min_profit_margin"],
    )


class NoMarket:
    async def get_clean_metrics(self, _ticker):
        raise AssertionError("preloaded portfolio metrics must not make network calls")

    async def get_company_profile(self, _ticker):
        raise AssertionError("preloaded portfolio sectors must not make network calls")


@pytest.fixture
def portfolio_data():
    # Hand-calculated weights: 60%, 30%, 10%; HHI = 3600 + 900 + 100 = 4600.
    holdings = [
        {
            "ticker": "AAA",
            "name": "Example A",
            "type": "equity",
            "shares": 6,
            "price": 10,
            "value": 60,
            "sector": "Technology",
            "simulated_metrics": {"ticker": "AAA", "pe_ratio": 18},
        },
        {
            "ticker": "BBB",
            "name": "Example B",
            "type": "equity",
            "shares": 3,
            "price": 10,
            "value": 30,
            "simulated_metrics": {"ticker": "BBB", "pe_ratio": 20},
        },
        {
            "ticker": None,
            "name": "Cash",
            "type": "cash",
            "shares": None,
            "price": None,
            "value": 10,
        },
    ]
    portfolio = asyncio.run(PortfolioService(NoMarket(), None).analyze(holdings))
    assert portfolio.total_value == 100
    assert portfolio.concentration_hhi == 4600
    assert portfolio.effective_position_count == 2.17
    assert portfolio.asset_type_allocation == {"cash": 10, "equity": 90}
    assert portfolio.sector_allocation == {"Technology": 60, "Unknown": 30}
    return portfolio.model_dump(by_alias=True, exclude={"ai_explanation"})


def fake_ai(payload, *, status="completed", side_effect=None):
    response = SimpleNamespace(
        output_parsed=payload,
        status=status,
        # Even when a valid selection exists, raw model prose must never escape.
        output_text="Buy TEST: earnings will be $999999 and the score is 999.",
    )
    parse = AsyncMock(return_value=response, side_effect=side_effect)
    create = AsyncMock(side_effect=AssertionError("free-text output must not be requested"))
    service = AIService()
    service._client = SimpleNamespace(responses=SimpleNamespace(parse=parse, create=create))
    return service, parse, create


def explain(service, kind, criteria, portfolio_data):
    if kind == "stock":
        return asyncio.run(service.explain_screen_match(make_stock(), criteria))
    return asyncio.run(service.explain_portfolio(portfolio_data))


def sent_evidence(parse):
    kwargs = parse.await_args.kwargs
    assert kwargs["text_format"] is EvidenceSelection
    return json.loads(kwargs["input"])


def assert_number(text, number):
    assert re.search(rf"(?<![\d.]){re.escape(str(number))}(?:\.0+)?(?!\d|\.\d)", text), text


def test_stock_explanation_matches_hand_calculated_scores_and_missing_data(criteria):
    stock = make_stock()
    # (75*20 + 80*25 + 80*25 + 85*15) / 85 = 79.70588..., rounded to 79.7.
    assert stock.score.overall_score == 79.7
    assert stock.score.data_coverage == 85
    assert stock.score.categories == {
        "valuation": 75,
        "growth": 80,
        "profitability": 80,
        "financial_health": 85,
        "momentum": None,
    }
    chosen = [
        "score.category.valuation", "score.category.growth", "score.category.profitability",
        "score.category.financial_health", "score.category.momentum", "score.reason.0",
        "metric.pe_ratio", "screening.passed",
    ]
    service, parse, create = fake_ai(EvidenceSelection(evidence_ids=chosen))

    result = asyncio.run(service.explain_screen_match(stock, criteria))

    sent = sent_evidence(parse)
    facts = sent["facts"]
    assert_number(facts["score.overall"], 79.7)
    assert_number(facts["score.coverage"], 85)
    assert_number(facts["score.category.valuation"], 75)
    assert_number(facts["metric.pe_ratio"], 18)
    assert facts["score.coverage"] == (
        "Data coverage is 85% of the configured model weight. "
        "Missing categories are excluded and available categories are reweighted."
    )
    assert facts["metrics.missing"] == (
        "Missing financial metrics: EPS, EPS growth, Return on equity, Beta, "
        "52-week return. No values are inferred."
    )
    assert {key: value for key, value in facts.items() if key.startswith("score.category.")} == {
        "score.category.valuation": "Valuation scores 75/100.",
        "score.category.growth": "Growth scores 80/100.",
        "score.category.profitability": "Profitability scores 80/100.",
        "score.category.financial_health": "Financial health scores 85/100.",
        "score.category.momentum": (
            "Momentum has insufficient data and is excluded from the overall score."
        ),
    }
    assert facts["score.reason.0"] == "Scoring rule: P/E ratio is moderate."
    assert set(sent["required_ids"]) == {
        "score.overall", "score.breakdown", "score.coverage", "score.weights", "metrics.missing",
    }
    assert "Valuation 75/100" in facts["score.breakdown"]
    assert "Growth 80/100" in facts["score.breakdown"]
    assert "Profitability 80/100" in facts["score.breakdown"]
    assert "Financial health 85/100" in facts["score.breakdown"]
    assert "Momentum unavailable" in facts["score.breakdown"]
    for evidence_id in [*sent["required_ids"], *chosen]:
        assert facts[evidence_id] in result
    assert "999999" not in result
    assert "Buy TEST" not in result
    create.assert_not_awaited()


def test_custom_weights_and_available_category_coverage_are_explained(criteria):
    weights = ScoringWeights(
        valuation=30, growth=20, profitability=25, financial_health=15, momentum=10
    )
    stock = make_stock(weights=weights)
    # (75*30 + 80*20 + 80*25 + 85*15) / 90 = 79.16666..., rounded to 79.2.
    assert stock.score.overall_score == 79.2
    assert stock.score.data_coverage == 90
    service, parse, _ = fake_ai({"evidence_ids": ["score.category.financial_health"]})

    result = asyncio.run(service.explain_screen_match(stock, criteria))

    sent = sent_evidence(parse)
    assert_number(sent["facts"]["score.overall"], 79.2)
    assert_number(sent["facts"]["score.coverage"], 90)
    normalized_weights = sent["facts"]["score.weights"].replace("_", " ").lower()
    for name, expected in weights.model_dump().items():
        assert re.search(rf"{name.replace('_', ' ')}[^\d]*{expected:g}", normalized_weights)
    assert sent["facts"]["score.weights"] in result


def test_changed_scoring_data_changes_explanation_even_with_identical_ai_selection(criteria):
    service, parse, _ = fake_ai({"evidence_ids": ["score.category.valuation", "metric.pe_ratio"]})
    first = asyncio.run(service.explain_screen_match(make_stock(pe_ratio=18), criteria))
    first_facts = sent_evidence(parse)["facts"]
    second = asyncio.run(service.explain_screen_match(make_stock(pe_ratio=45), criteria))
    second_facts = sent_evidence(parse)["facts"]

    # Valuation drops from 75 to 25; (25*20 + 80*25 + 80*25 + 85*15)/85 = 67.9.
    assert_number(first_facts["score.overall"], 79.7)
    assert_number(second_facts["score.overall"], 67.9)
    assert_number(second_facts["metric.pe_ratio"], 45)
    assert first != second
    assert first_facts["score.overall"] in first
    assert second_facts["score.overall"] in second
    assert first_facts["score.overall"] not in second


def test_required_disclosures_cannot_be_omitted_by_ai_selection(criteria):
    stock = make_stock()
    evidence = stock_evidence(stock, criteria)
    result = evidence.render(EvidenceSelection(evidence_ids=["metric.pe_ratio"]))

    for evidence_id in evidence.required_ids:
        assert evidence.facts[evidence_id] in result
    assert evidence.facts["metric.pe_ratio"] in result


def test_negative_figures_preserve_their_sign_and_metric_units(criteria):
    metrics = StockMetrics(ticker="TEST", pe_ratio=18, eps=-2.1, return_52_week=-8.5)
    stock = MatchingStock(
        ticker="TEST", metrics=metrics,
        score=score_equity(metrics.model_dump(by_alias=True)), passed_criteria=[],
    )
    assert stock.score.overall_score == 60
    assert stock.score.data_coverage == 35
    service, parse, _ = fake_ai({"evidence_ids": ["metric.eps", "metric.52_week_return"]})

    result = asyncio.run(service.explain_screen_match(stock, criteria))

    facts = sent_evidence(parse)["facts"]
    assert "-8.5%" in facts["metric.52_week_return"]
    assert "-2.1" in facts["metric.eps"]
    assert "%" not in facts["metric.eps"]
    assert facts["metric.52_week_return"] in result
    assert facts["metric.eps"] in result
    assert_number(facts["score.overall"], 60)
    assert_number(facts["score.coverage"], 35)


def test_no_data_is_reported_as_unavailable_instead_of_inventing_a_score(criteria):
    metrics = StockMetrics(ticker="EMPTY")
    stock = MatchingStock(
        ticker="EMPTY", metrics=metrics,
        score=score_equity(metrics.model_dump(by_alias=True)), passed_criteria=[],
    )
    assert stock.score.overall_score is None
    assert stock.score.data_coverage == 0
    service, parse, _ = fake_ai({"evidence_ids": ["score.category.valuation"]})

    result = asyncio.run(service.explain_screen_match(stock, criteria))

    facts = sent_evidence(parse)["facts"]
    assert "No overall stock score is available" in result
    assert "insufficient_data" in facts["score.overall"]
    assert_number(facts["score.coverage"], 0)
    assert "insufficient data" in facts["score.category.valuation"]
    assert not any(key.startswith("metric.") for key in facts)


@pytest.mark.parametrize("kind", ["stock", "portfolio"])
@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        "The score is 100 and returns will double.",
        {"evidence_ids": []},
        {"evidence_ids": "score.overall"},
        {"evidence_ids": [79.7]},
        {"evidence_ids": [True]},
        {"evidence_ids": [None]},
        {"evidence_ids": ["invented.future_earnings"]},
        {"evidence_ids": ["metric.pe_ratio: 1000"]},
        {"evidence_ids": ["score.overall", "score.overall"]},
        {"evidence_ids": [f"invented.{index}" for index in range(13)]},
        {"evidence_ids": ["score.overall"], "explanation": "The score is 100."},
        {"evidence_ids": ["score.overall"], "overall_score": 100},
        # The number 18 exists in the source P/E data, but it is not the score.
        {"evidence_ids": ["score.overall"], "claims": [{"overall_score": 18}]},
        {"evidence_ids": ["score.overall"], "forecast": "EPS will be $999999."},
    ],
    ids=[
        "refusal-or-no-parsed-output", "missing-selection", "unstructured-prose",
        "empty-selection", "scalar-selection", "numeric-id", "boolean-id", "null-id",
        "unknown-id", "value-smuggled-in-id", "duplicate-id", "too-many-ids",
        "extra-prose", "changed-score", "source-number-reused-for-wrong-metric", "forecast",
    ],
)
def test_invalid_ai_output_is_rejected_without_returning_claims(
    kind, payload, criteria, portfolio_data
):
    service, parse, create = fake_ai(payload)

    with pytest.raises(ProviderError) as exc:
        explain(service, kind, criteria, portfolio_data)

    assert exc.value.code == "invalid_ai_explanation"
    assert exc.value.status_code == 502
    assert "999999" not in exc.value.message
    parse.assert_awaited_once()
    create.assert_not_awaited()


@pytest.mark.parametrize("kind", ["stock", "portfolio"])
def test_constructed_invalid_parsed_model_is_revalidated(kind, criteria, portfolio_data):
    forged = EvidenceSelection.model_construct(evidence_ids=[123])
    service, _, _ = fake_ai(forged)

    with pytest.raises(ProviderError) as exc:
        explain(service, kind, criteria, portfolio_data)

    assert exc.value.code == "invalid_ai_explanation"
    assert exc.value.status_code == 502


@pytest.mark.parametrize("kind", ["stock", "portfolio"])
def test_evidence_ids_cannot_cross_stock_and_portfolio_boundaries(kind, criteria, portfolio_data):
    other_domain_id = "portfolio.summary" if kind == "stock" else "score.overall"
    service, _, _ = fake_ai({"evidence_ids": [other_domain_id]})

    with pytest.raises(ProviderError) as exc:
        explain(service, kind, criteria, portfolio_data)

    assert exc.value.code == "invalid_ai_explanation"


@pytest.mark.parametrize("kind", ["stock", "portfolio"])
@pytest.mark.parametrize("status", ["incomplete", "failed", "in_progress"])
def test_incomplete_provider_response_is_rejected(kind, status, criteria, portfolio_data):
    evidence_id = "score.overall" if kind == "stock" else "portfolio.summary"
    service, _, _ = fake_ai({"evidence_ids": [evidence_id]}, status=status)

    with pytest.raises(ProviderError) as exc:
        explain(service, kind, criteria, portfolio_data)

    assert exc.value.code == "invalid_ai_explanation"
    assert exc.value.status_code == 502


@pytest.mark.parametrize("kind", ["stock", "portfolio"])
def test_provider_failure_is_normalized_without_leaking_provider_text(
    kind, criteria, portfolio_data
):
    service, _, _ = fake_ai(None, side_effect=TimeoutError("private token and $999999 forecast"))

    with pytest.raises(ProviderError) as exc:
        explain(service, kind, criteria, portfolio_data)

    assert exc.value.code == "openai_unavailable"
    assert exc.value.status_code == 502
    assert "private token" not in exc.value.message
    assert "999999" not in exc.value.message


@pytest.mark.parametrize("kind", ["stock", "portfolio"])
def test_missing_api_key_returns_configuration_error(kind, criteria, portfolio_data):
    service = AIService()
    service._client = None

    with pytest.raises(AppError) as exc:
        explain(service, kind, criteria, portfolio_data)

    assert exc.value.code == "openai_not_configured"
    assert exc.value.status_code == 503


def test_portfolio_explanation_preserves_calculated_allocations_and_missing_data(portfolio_data):
    service, parse, create = fake_ai({"evidence_ids": ["holding.0"]})

    result = asyncio.run(service.explain_portfolio(portfolio_data))

    sent = sent_evidence(parse)
    facts = sent["facts"]
    assert set(sent["required_ids"]) == {
        "portfolio.summary", "portfolio.concentration", "portfolio.assets",
        "portfolio.sectors", "portfolio.missing",
    }
    assert_number(facts["portfolio.summary"], 100)
    assert_number(facts["portfolio.summary"], 3)
    assert_number(facts["portfolio.concentration"], 60)
    assert_number(facts["portfolio.concentration"], 4600)
    assert_number(facts["portfolio.concentration"], 2.17)
    assert_number(facts["portfolio.assets"], 90)
    assert_number(facts["portfolio.assets"], 10)
    assert "Technology" in facts["portfolio.sectors"]
    assert "Unknown" in facts["portfolio.sectors"]
    assert "BBB" in facts["portfolio.missing"]
    assert "AAA" in facts["holding.0"]
    assert_number(facts["holding.0"], 60)
    for evidence_id in [*sent["required_ids"], "holding.0"]:
        assert facts[evidence_id] in result
    assert "999999" not in result
    create.assert_not_awaited()


@pytest.mark.parametrize("payload", [
    {"evidence_ids": []},
    {"evidence_ids": [1]},
    {"evidence_ids": ("score.overall",)},
    {"evidence_ids": ["score.overall"], "text": "invented explanation"},
    {"evidence_ids": [str(index) for index in range(13)]},
])
def test_evidence_selection_schema_rejects_unstructured_or_coerced_data(payload):
    with pytest.raises(ValidationError):
        EvidenceSelection.model_validate(payload)
