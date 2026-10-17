"""Render explanations from calculated evidence, never from model-written figures.

Checking whether a number occurs somewhere in a prompt is insufficient: a model
could reuse a score as a P/E ratio, omit its sign, or invent its units. Instead,
the model selects fact IDs and the application owns every displayed sentence.
"""

import math
from dataclasses import dataclass
from typing import Any

from backend.errors import ProviderError
from backend.schemas.explanation import EvidenceSelection
from backend.schemas.screen import MatchingStock, ScreeningCriteria

CATEGORY_LABELS = {
    "valuation": "Valuation",
    "growth": "Growth",
    "profitability": "Profitability",
    "financial_health": "Financial health",
    "momentum": "Momentum",
}
METRIC_LABELS = {
    "pe_ratio": ("P/E ratio", ""),
    "eps": ("EPS", " (as supplied by the market-data provider)"),
    "revenue_growth": ("Revenue growth", "%"),
    "eps_growth": ("EPS growth", "%"),
    "profit_margin": ("Profit margin", "%"),
    "return_on_equity": ("Return on equity", "%"),
    "current_ratio": ("Current ratio", ""),
    "beta": ("Beta", ""),
    "52_week_return": ("52-week return", "%"),
}


def _number(value: int | float) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProviderError("invalid_ai_evidence", "Explanation evidence must be finite", 502)
    return str(int(value)) if value == int(value) else str(value)


@dataclass(frozen=True)
class ExplanationEvidence:
    facts: dict[str, str]
    required_ids: tuple[str, ...]

    def render(self, selection: EvidenceSelection) -> str:
        ids = selection.evidence_ids
        if len(ids) != len(set(ids)) or any(key not in self.facts for key in ids):
            raise ProviderError(
                "invalid_ai_explanation",
                "AI explanation referenced invalid or duplicate evidence",
                502,
            )
        ordered_ids = dict.fromkeys((*self.required_ids, *ids))
        return "\n\n".join(self.facts[key] for key in ordered_ids)


def stock_evidence(stock: MatchingStock, criteria: ScreeningCriteria) -> ExplanationEvidence:
    score = stock.score
    overall = (
        "No overall stock score is available"
        if score.overall_score is None
        else f"{stock.ticker} has a calculated stock score of {_number(score.overall_score)}/100"
    )
    facts = {
        "score.overall": f"{overall}; scoring signal: {score.signal}.",
        "score.coverage": (
            f"Data coverage is {_number(score.data_coverage)}% of the configured model weight. "
            "Missing categories are excluded and available categories are reweighted."
        ),
        "score.weights": "Configured category weights: " + "; ".join(
            f"{CATEGORY_LABELS[key]} {_number(score.weights[key])}%"
            for key in CATEGORY_LABELS
        ) + ".",
    }
    for key, label in CATEGORY_LABELS.items():
        value = score.categories.get(key)
        facts[f"score.category.{key}"] = (
            f"{label} has insufficient data and is excluded from the overall score."
            if value is None
            else f"{label} scores {_number(value)}/100."
        )
    facts["score.breakdown"] = "Category scores: " + "; ".join(
        f"{label} " + (
            "unavailable" if score.categories.get(key) is None
            else f"{_number(score.categories[key])}/100"
        )
        for key, label in CATEGORY_LABELS.items()
    ) + "."
    for index, reason in enumerate(score.reasons):
        facts[f"score.reason.{index}"] = f"Scoring rule: {reason}."
    missing = []
    metrics = stock.metrics.model_dump(by_alias=True)
    for key, (label, unit) in METRIC_LABELS.items():
        value = metrics[key]
        if value is None:
            missing.append(label)
        else:
            facts[f"metric.{key}"] = f"{label}: {_number(value)}{unit}."
    facts["metrics.missing"] = (
        "Missing financial metrics: " + ", ".join(missing) + ". No values are inferred."
        if missing
        else "All listed financial metrics are available."
    )
    if stock.passed_criteria:
        facts["screening.passed"] = (
            "Passed screening checks: " + ", ".join(stock.passed_criteria) + "."
        )
    requested = criteria.model_dump(exclude_none=True)
    if requested:
        facts["screening.criteria"] = "Requested screening thresholds: " + "; ".join(
            f"{key} = {_number(value)}" for key, value in requested.items()
        ) + "."
    return ExplanationEvidence(
        facts=facts,
        required_ids=(
            "score.overall", "score.breakdown", "score.coverage",
            "score.weights", "metrics.missing",
        ),
    )


def portfolio_evidence(evidence: dict[str, Any]) -> ExplanationEvidence:
    def allocation(key: str) -> str:
        values = evidence.get(key, {})
        return "; ".join(f"{name} {_number(value)}%" for name, value in values.items()) or "none"

    effective_count = evidence.get("effective_position_count")
    effective_text = "unavailable" if effective_count is None else _number(effective_count)
    facts = {
        "portfolio.summary": (
            f"Portfolio total value is {_number(evidence['total_value'])} in the supplied "
            f"valuation units across {_number(evidence['position_count'])} positions."
            + (" This is a simulated portfolio." if evidence.get("simulated") else "")
        ),
        "portfolio.concentration": (
            f"Top-three concentration is {_number(evidence['top_3_concentration'])}%; "
            f"top-five concentration is {_number(evidence['top_5_concentration'])}%. "
            f"Concentration HHI is {_number(evidence['concentration_hhi'])}; "
            f"effective position count is {effective_text}."
        ),
        "portfolio.assets": f"Asset allocation: {allocation('asset_type_allocation')}.",
        "portfolio.sectors": (
            f"Equity sector allocation as a share of the whole portfolio: "
            f"{allocation('sector_allocation')}."
        ),
    }
    largest = evidence.get("largest_position")
    if largest is not None:
        label = largest.get("ticker") or largest.get("name") or "Unnamed holding"
        facts["portfolio.concentration"] += (
            f" Largest position: {label}, {_number(largest['weight'])}% of portfolio value."
        )
    unavailable = []
    for index, holding in enumerate(evidence.get("holdings", [])):
        label = holding.get("ticker") or holding.get("name") or "Unnamed holding"
        fact = (
            f"{label}: value {_number(holding['value'])} in the supplied valuation units; "
            f"portfolio weight {_number(holding['weight'])}%."
        )
        analysis = holding.get("analysis") or {}
        score = analysis.get("score") or {}
        if score.get("overall_score") is not None:
            fact += (
                f" Calculated equity score: {_number(score['overall_score'])}/100; "
                f"data coverage {_number(score['data_coverage'])}%."
            )
        elif str(holding.get("type")).lower() == "equity":
            unavailable.append(f"{label}: equity score unavailable")
        if str(holding.get("type")).lower() == "equity":
            if not holding.get("sector"):
                unavailable.append(f"{label}: sector unavailable")
            metrics = analysis.get("metrics")
            if isinstance(metrics, dict):
                missing = [
                    label for key, (label, _unit) in METRIC_LABELS.items()
                    if metrics.get(key) is None
                ]
                if missing:
                    unavailable.append(f"{label}: missing " + ", ".join(missing))
        facts[f"holding.{index}"] = fact
    facts["portfolio.missing"] = (
        "Missing portfolio information: " + "; ".join(unavailable) + ". No values are inferred."
        if unavailable
        else "No missing equity scoring or sector information was reported."
    )
    return ExplanationEvidence(
        facts=facts,
        required_ids=(
            "portfolio.summary", "portfolio.concentration", "portfolio.assets",
            "portfolio.sectors", "portfolio.missing",
        ),
    )
