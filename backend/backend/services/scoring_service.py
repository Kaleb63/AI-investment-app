from typing import Any

from backend.schemas.stock import ScoringWeights

DEFAULT_WEIGHTS = ScoringWeights()


def score_growth_metric(growth: float) -> float:
    if growth >= 20:
        return 100
    if growth >= 10:
        return 80
    if growth > 0:
        return 65
    if growth == 0:
        return 50
    if growth >= -10:
        return 35
    return 15


def score_equity(
    metrics: dict[str, Any],
    weights: ScoringWeights | None = None,
) -> dict[str, Any]:
    """Return a deterministic score, reweighted over available categories."""

    weights_model = weights or DEFAULT_WEIGHTS
    weight_values = weights_model.model_dump()
    category_scores = {
        "valuation": None,
        "growth": None,
        "profitability": None,
        "financial_health": None,
        "momentum": None,
    }
    reasons = []

    pe_ratio = metrics.get("pe_ratio")
    if pe_ratio is not None and pe_ratio > 0:
        if pe_ratio <= 15:
            category_scores["valuation"] = 100
            reasons.append("P/E ratio is low")
        elif pe_ratio <= 25:
            category_scores["valuation"] = 75
            reasons.append("P/E ratio is moderate")
        elif pe_ratio <= 40:
            category_scores["valuation"] = 50
            reasons.append("P/E ratio is elevated")
        else:
            category_scores["valuation"] = 25
            reasons.append("P/E ratio is high")

    growth_scores = []
    for metric_name, label in (
        ("revenue_growth", "Revenue"),
        ("eps_growth", "EPS"),
    ):
        value = metrics.get(metric_name)
        if value is None:
            continue
        growth_scores.append(score_growth_metric(value))
        if value >= 20:
            reasons.append(f"{label} growth is strong")
        elif value > 0:
            reasons.append(f"{label} is growing")
        else:
            reasons.append(f"{label} growth is negative")
    if growth_scores:
        category_scores["growth"] = sum(growth_scores) / len(growth_scores)

    profitability_scores = []
    profit_margin = metrics.get("profit_margin")
    if profit_margin is not None:
        if profit_margin >= 20:
            profitability_scores.append(100)
            reasons.append("Profit margin is strong")
        elif profit_margin >= 10:
            profitability_scores.append(80)
            reasons.append("Company is profitable")
        elif profit_margin > 0:
            profitability_scores.append(60)
            reasons.append("Company is profitable")
        else:
            profitability_scores.append(20)
            reasons.append("Company has a negative profit margin")

    return_on_equity = metrics.get("return_on_equity")
    if return_on_equity is not None:
        if return_on_equity >= 20:
            profitability_scores.append(100)
            reasons.append("Return on equity is strong")
        elif return_on_equity >= 10:
            profitability_scores.append(80)
            reasons.append("Return on equity is healthy")
        elif return_on_equity > 0:
            profitability_scores.append(60)
            reasons.append("Return on equity is positive but relatively low")
        else:
            profitability_scores.append(20)
            reasons.append("Return on equity is negative")
    if profitability_scores:
        category_scores["profitability"] = sum(profitability_scores) / len(profitability_scores)

    current_ratio = metrics.get("current_ratio")
    if current_ratio is not None:
        if current_ratio >= 2:
            category_scores["financial_health"] = 100
        elif current_ratio >= 1.5:
            category_scores["financial_health"] = 85
        elif current_ratio >= 1:
            category_scores["financial_health"] = 70
        elif current_ratio >= 0.75:
            category_scores["financial_health"] = 45
        else:
            category_scores["financial_health"] = 20

        if current_ratio >= 1.5:
            reasons.append("Liquidity is strong")
        elif current_ratio >= 1:
            reasons.append("Current assets cover current liabilities")
        else:
            reasons.append("Current ratio is below 1")

    year_return = metrics.get("52_week_return")
    if year_return is not None:
        if year_return >= 20:
            category_scores["momentum"] = 100
            reasons.append("52-week price momentum is strong")
        elif year_return >= 10:
            category_scores["momentum"] = 80
            reasons.append("Stock has positive 52-week momentum")
        elif year_return > 0:
            category_scores["momentum"] = 65
            reasons.append("Stock has positive 52-week momentum")
        elif year_return >= -10:
            category_scores["momentum"] = 40
            reasons.append("Stock has negative 52-week momentum")
        else:
            category_scores["momentum"] = 20
            reasons.append("Stock has negative 52-week momentum")

    weighted_total = 0.0
    available_weight = 0.0
    for category, category_score in category_scores.items():
        if category_score is not None:
            weighted_total += category_score * weight_values[category]
            available_weight += weight_values[category]

    overall_score = round(weighted_total / available_weight, 1) if available_weight > 0 else None
    if overall_score is None:
        signal = "insufficient_data"
    elif overall_score >= 70:
        signal = "positive"
    elif overall_score >= 40:
        signal = "mixed"
    else:
        signal = "negative"

    return {
        "overall_score": overall_score,
        "signal": signal,
        "data_coverage": round(available_weight, 1),
        "categories": category_scores,
        "reasons": reasons,
        "weights": weight_values,
    }


scoring_service = score_equity
