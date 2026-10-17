"""Keep explanatory language aligned with zero and negative source metrics."""

import pytest

from backend.services.scoring_service import score_equity


@pytest.mark.parametrize(
    (
        "metric", "category", "zero_score", "negative_score", "coverage",
        "zero_reason", "negative_reason",
    ),
    (
        (
            "revenue_growth", "growth", 50, 35, 25,
            "Revenue growth is flat", "Revenue growth is negative",
        ),
        (
            "eps_growth", "growth", 50, 35, 25,
            "EPS growth is flat", "EPS growth is negative",
        ),
        (
            "profit_margin", "profitability", 20, 20, 25,
            "Company has a zero profit margin", "Company has a negative profit margin",
        ),
        (
            "return_on_equity", "profitability", 20, 20, 25,
            "Return on equity is zero", "Return on equity is negative",
        ),
        (
            "52_week_return", "momentum", 40, 40, 15,
            "Stock has flat 52-week momentum", "Stock has negative 52-week momentum",
        ),
    ),
)
def test_zero_metric_uses_factual_reason_and_preserves_numeric_scoring(
    metric, category, zero_score, negative_score, coverage, zero_reason, negative_reason
):
    zero = score_equity({metric: 0})
    negative = score_equity({metric: -1})

    assert zero["reasons"] == [zero_reason]
    assert negative["reasons"] == [negative_reason]
    assert zero["categories"][category] == zero["overall_score"] == zero_score
    assert negative["categories"][category] == negative["overall_score"] == negative_score
    assert zero["data_coverage"] == negative["data_coverage"] == coverage
    assert all(
        value is None for name, value in zero["categories"].items() if name != category
    )


def test_all_zero_observations_remain_available_with_accurate_explanations():
    result = score_equity(
        {
            "revenue_growth": 0,
            "eps_growth": 0,
            "profit_margin": 0,
            "return_on_equity": 0,
            "52_week_return": 0,
        }
    )

    assert result["categories"] == {
        "valuation": None,
        "growth": 50,
        "profitability": 20,
        "financial_health": None,
        "momentum": 40,
    }
    assert result["overall_score"] == 36.2
    assert result["data_coverage"] == 65
    assert result["signal"] == "negative"
    assert result["reasons"] == [
        "Revenue growth is flat",
        "EPS growth is flat",
        "Company has a zero profit margin",
        "Return on equity is zero",
        "Stock has flat 52-week momentum",
    ]
