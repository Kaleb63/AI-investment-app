import pytest
from pydantic import ValidationError

from backend.schemas.stock import ScoringWeights
from backend.services.scoring_service import score_equity


def metrics(**overrides):
    values = {
        "pe_ratio": 12,
        "revenue_growth": 25,
        "eps_growth": 25,
        "profit_margin": 25,
        "return_on_equity": 25,
        "current_ratio": 2,
        "52_week_return": 25,
    }
    values.update(overrides)
    return values


def test_excellent_metrics_score_100():
    result = score_equity(metrics())
    assert result["overall_score"] == 100
    assert result["signal"] == "positive"
    assert result["data_coverage"] == 100


def test_poor_metrics_are_negative():
    result = score_equity(
        metrics(
            pe_ratio=60,
            revenue_growth=-20,
            eps_growth=-30,
            profit_margin=-5,
            return_on_equity=-10,
            current_ratio=0.5,
            **{"52_week_return": -30},
        )
    )
    assert result["overall_score"] < 40
    assert result["signal"] == "negative"


def test_all_missing_returns_insufficient_data():
    result = score_equity(metrics(**{key: None for key in metrics()}))
    assert result["overall_score"] is None
    assert result["data_coverage"] == 0
    assert result["signal"] == "insufficient_data"


def test_missing_category_reweights_instead_of_scoring_zero():
    result = score_equity(metrics(pe_ratio=None))
    assert result["overall_score"] == 100
    assert result["data_coverage"] == 80


def test_negative_eps_does_not_create_an_unconfigured_penalty():
    baseline = score_equity(metrics())
    result = score_equity({**metrics(), "eps": -2})
    assert result["overall_score"] == baseline["overall_score"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"eps_growth": -5},
        {"revenue_growth": -5},
        {"profit_margin": -1},
        {"pe_ratio": 200},
    ],
)
def test_adverse_values_reduce_relevant_category(overrides):
    baseline = score_equity(metrics())
    result = score_equity(metrics(**overrides))
    assert result["overall_score"] < baseline["overall_score"]


def test_custom_weights_are_used_and_must_total_100():
    weights = ScoringWeights(
        valuation=100,
        growth=0,
        profitability=0,
        financial_health=0,
        momentum=0,
    )
    assert score_equity(metrics(pe_ratio=60), weights)["overall_score"] == 25

    with pytest.raises(ValidationError):
        ScoringWeights(valuation=10)
