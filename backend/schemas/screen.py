import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.config import settings
from backend.schemas.common import normalize_ticker
from backend.schemas.stock import EquityScore, ScoringWeights, StockMetrics


class ScreeningCriteria(BaseModel):
    min_score: float | None = Field(default=None, ge=0, le=100)
    max_pe_ratio: float | None = Field(default=None, gt=0)
    min_revenue_growth: float | None = None
    min_eps_growth: float | None = None
    min_profit_margin: float | None = None
    min_return_on_equity: float | None = None
    min_current_ratio: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("*")
    @classmethod
    def criteria_must_be_finite(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("screening criteria must be finite numbers")
        return value


class ScreenRequest(ScreeningCriteria):
    tickers: list[str]
    weights: ScoringWeights | None = None

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, tickers: list[str]) -> list[str]:
        if not tickers:
            raise ValueError("at least one ticker is required")
        unique = []
        seen = set()
        for ticker in tickers:
            normalized = normalize_ticker(ticker)
            if normalized not in seen:
                unique.append(normalized)
                seen.add(normalized)
        if len(unique) > settings.max_scan_tickers:
            raise ValueError(f"at most {settings.max_scan_tickers} unique tickers are allowed")
        return unique

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "tickers": ["AAPL", "MSFT", "NVDA", "GOOGL"],
                "min_score": 70,
                "max_pe_ratio": 30,
                "min_revenue_growth": 10,
                "min_eps_growth": 5,
                "min_profit_margin": 10,
                "min_return_on_equity": 15,
                "min_current_ratio": 1.2,
            }
        },
    )


class FailedCriterion(BaseModel):
    criterion: str
    comparison: str
    required_value: float
    actual_value: float


class UnevaluatedCriterion(BaseModel):
    criterion: str
    required_value: float
    reason: str


class MatchingStock(BaseModel):
    ticker: str
    metrics: StockMetrics
    score: EquityScore
    passed_criteria: list[str]
    ai_explanation: str | None = None


class RejectedStock(MatchingStock):
    failed_criteria: list[FailedCriterion]
    unevaluated_criteria: list[UnevaluatedCriterion]


class UnavailableStock(BaseModel):
    ticker: str
    status: Literal["insufficient_data", "error"]
    reason: str
    missing_criteria: list[UnevaluatedCriterion] = Field(default_factory=list)


class ScanPerformance(BaseModel):
    duration_seconds: float
    stocks_attempted: int
    stocks_successfully_analyzed: int
    stocks_failed: int
    average_processing_seconds: float
    successful_stocks_per_second: float
    failure_percentage: float
    cache_hits: int
    cache_misses: int


class ScreenSummary(BaseModel):
    total_requested: int
    successfully_analyzed: int
    matched: int
    rejected: int
    unavailable: int
    errored: int


class ScreenResponse(BaseModel):
    criteria: ScreeningCriteria
    summary: ScreenSummary
    performance: ScanPerformance
    matching_stocks: list[MatchingStock]
    rejected_stocks: list[RejectedStock]
    unavailable_stocks: list[UnavailableStock]


class AIScreenRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    tickers: list[str] | None = None
    universe_limit: int = Field(default=100, ge=1, le=settings.max_scan_tickers)
    include_explanations: bool = True
    weights: ScoringWeights | None = None

    @field_validator("tickers")
    @classmethod
    def normalize_optional_tickers(cls, tickers: list[str] | None) -> list[str] | None:
        if tickers is None:
            return None
        if not tickers:
            raise ValueError("tickers cannot be an empty list")
        unique = list(dict.fromkeys(normalize_ticker(ticker) for ticker in tickers))
        if len(unique) > settings.max_scan_tickers:
            raise ValueError(f"at most {settings.max_scan_tickers} unique tickers are allowed")
        return unique


class AIScreenResponse(BaseModel):
    query: str
    interpreted_criteria: ScreeningCriteria
    number_of_stocks_searched: int
    results: ScreenResponse
    explanation_errors: dict[str, str] = Field(default_factory=dict)


class SavedScreenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    criteria: ScreeningCriteria


class SavedScreenResponse(BaseModel):
    id: str
    name: str
    criteria: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
