import asyncio
from typing import Any

from backend.errors import AppError
from backend.schemas.portfolio import PortfolioSummary
from backend.services.ai_service import AIService, ai_service
from backend.services.finnhub_service import FinnhubService, finnhub_service
from backend.services.scoring_service import score_equity


class PortfolioService:
    def __init__(self, market_data: FinnhubService, ai: AIService) -> None:
        self.market_data = market_data
        self.ai = ai

    async def _enrich_holding(self, holding: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(holding)
        ticker = holding.get("ticker")
        asset_type = str(holding.get("type") or "other").lower()
        if asset_type != "equity" or not ticker:
            enriched["analysis"] = {
                "status": "not_analyzed",
                "reason": f"{asset_type} requires a separate analysis model",
            }
            return enriched

        simulated_metrics = holding.get("simulated_metrics")
        if simulated_metrics:
            enriched["analysis"] = {
                "metrics": simulated_metrics,
                "score": score_equity(simulated_metrics),
            }
            enriched.pop("simulated_metrics", None)
            return enriched

        try:
            metrics = await self.market_data.get_clean_metrics(ticker)
            score = score_equity(metrics)
            enriched["analysis"] = {"metrics": metrics, "score": score}
        except AppError as exc:
            enriched["analysis"] = {"status": "unavailable", "reason": exc.message}

        try:
            profile = await self.market_data.get_company_profile(ticker)
            enriched["sector"] = profile.get("finnhubIndustry") or None
        except AppError:
            enriched["sector"] = None
        return enriched

    async def analyze(
        self,
        holdings: list[dict[str, Any]],
        *,
        simulated: bool = False,
        include_ai: bool = False,
    ) -> PortfolioSummary:
        enriched = await asyncio.gather(*(self._enrich_holding(holding) for holding in holdings))
        for holding in enriched:
            holding["value"] = float(holding.get("value") or 0)
        enriched.sort(key=lambda item: item["value"], reverse=True)

        total_value = sum(max(holding["value"], 0) for holding in enriched)
        for holding in enriched:
            holding["weight"] = round(
                holding["value"] / total_value * 100 if total_value else 0,
                2,
            )

        weights = [holding["weight"] for holding in enriched]
        hhi = sum(weight**2 for weight in weights)
        fraction_hhi = hhi / 10000
        asset_values: dict[str, float] = {}
        sector_values: dict[str, float] = {}
        for holding in enriched:
            asset_type = str(holding.get("type") or "other").lower()
            asset_values[asset_type] = asset_values.get(asset_type, 0) + holding["value"]
            if asset_type == "equity":
                sector = holding.get("sector") or "Unknown"
                sector_values[sector] = sector_values.get(sector, 0) + holding["value"]

        def allocation(values: dict[str, float]) -> dict[str, float]:
            return {
                key: round(value / total_value * 100, 2) if total_value else 0
                for key, value in sorted(values.items())
            }

        sector_allocation = allocation(sector_values)
        largest_sector = None
        if sector_allocation:
            sector, weight = max(sector_allocation.items(), key=lambda item: item[1])
            largest_sector = {"sector": sector, "weight": weight}

        largest_position = None
        if enriched:
            largest_position = {
                "ticker": enriched[0].get("ticker"),
                "name": enriched[0].get("name"),
                "weight": enriched[0]["weight"],
            }

        summary_data = {
            "simulated": simulated,
            "total_value": round(total_value, 2),
            "position_count": len(enriched),
            "largest_position": largest_position,
            "top_3_concentration": round(sum(weights[:3]), 2),
            "top_5_concentration": round(sum(weights[:5]), 2),
            "concentration_hhi": round(hhi, 2),
            "effective_position_count": round(1 / fraction_hhi, 2) if fraction_hhi else None,
            "asset_type_allocation": allocation(asset_values),
            "sector_allocation": sector_allocation,
            "largest_sector": largest_sector,
            "holdings": enriched,
            "ai_explanation": None,
        }
        if include_ai:
            try:
                ai_evidence = {
                    key: value
                    for key, value in summary_data.items()
                    if key not in {"ai_explanation"}
                }
                summary_data["ai_explanation"] = await self.ai.explain_portfolio(ai_evidence)
            except AppError:
                summary_data["ai_explanation"] = None
        return PortfolioSummary.model_validate(summary_data)


portfolio_service = PortfolioService(finnhub_service, ai_service)
