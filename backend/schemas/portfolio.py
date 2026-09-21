from typing import Any

from pydantic import BaseModel, Field


class PortfolioHolding(BaseModel):
    ticker: str | None
    name: str | None
    asset_type: str = Field(alias="type")
    shares: float | None
    price: float | None
    value: float
    weight: float = 0
    sector: str | None = None
    analysis: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class LargestPosition(BaseModel):
    ticker: str | None
    name: str | None
    weight: float


class PortfolioSummary(BaseModel):
    simulated: bool = False
    total_value: float
    position_count: int
    largest_position: LargestPosition | None
    top_3_concentration: float
    top_5_concentration: float
    concentration_hhi: float
    effective_position_count: float | None
    asset_type_allocation: dict[str, float]
    sector_allocation: dict[str, float]
    largest_sector: dict[str, Any] | None
    holdings: list[PortfolioHolding]
    ai_explanation: str | None = None
