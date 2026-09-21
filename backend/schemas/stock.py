from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.schemas.common import normalize_ticker


class StockMetrics(BaseModel):
    ticker: str
    pe_ratio: float | None = None
    eps: float | None = None
    revenue_growth: float | None = None
    eps_growth: float | None = None
    profit_margin: float | None = None
    return_on_equity: float | None = None
    current_ratio: float | None = None
    beta: float | None = None
    return_52_week: float | None = Field(default=None, alias="52_week_return")

    model_config = ConfigDict(populate_by_name=True)


class ScoringWeights(BaseModel):
    valuation: float = Field(default=20, ge=0, le=100)
    growth: float = Field(default=25, ge=0, le=100)
    profitability: float = Field(default=25, ge=0, le=100)
    financial_health: float = Field(default=15, ge=0, le=100)
    momentum: float = Field(default=15, ge=0, le=100)

    @model_validator(mode="after")
    def weights_must_total_100(self):
        if abs(sum(self.model_dump().values()) - 100) > 0.001:
            raise ValueError("scoring weights must sum to 100")
        return self


class EquityScore(BaseModel):
    overall_score: float | None
    signal: str
    data_coverage: float
    categories: dict[str, float | None]
    reasons: list[str]
    weights: dict[str, float]


class StockAnalysis(BaseModel):
    ticker: str
    metrics: StockMetrics
    score: EquityScore


class StockRequest(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        return normalize_ticker(value)
