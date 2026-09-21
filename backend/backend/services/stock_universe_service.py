from typing import Any, Protocol

from backend.schemas.common import TICKER_PATTERN
from backend.services.finnhub_service import finnhub_service


class StockUniverseProvider(Protocol):
    async def get_symbols(self, exchange: str = "US") -> list[dict[str, Any]]: ...


class StockUniverseService:
    EQUITY_TYPES = {"Common Stock", "Preferred Stock"}
    ETF_TYPES = {"ETP", "ETF", "Exchange Traded Fund"}

    def __init__(self, provider: StockUniverseProvider) -> None:
        self.provider = provider

    async def list_symbols(
        self,
        exchange: str = "US",
        asset_type: str | None = None,
        search: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> dict[str, Any]:
        raw_symbols = await self.provider.get_symbols(exchange.upper())
        unique: dict[str, dict[str, Any]] = {}

        for item in raw_symbols:
            symbol = str(item.get("symbol", "")).strip().upper()
            description = str(item.get("description", "")).strip()
            provider_type = str(item.get("type", "")).strip()
            currency = str(item.get("currency", "")).upper()

            if not TICKER_PATTERN.fullmatch(symbol):
                continue
            if currency and currency != "USD":
                continue
            if provider_type in self.EQUITY_TYPES:
                normalized_type = "equity"
            elif provider_type in self.ETF_TYPES:
                normalized_type = "etf"
            else:
                continue
            if asset_type and normalized_type != asset_type.lower():
                continue
            if search:
                needle = search.strip().upper()
                if needle not in symbol and needle not in description.upper():
                    continue

            existing = unique.get(symbol)
            candidate = {
                "ticker": symbol,
                "name": description or symbol,
                "asset_type": normalized_type,
                "exchange": exchange.upper(),
            }
            if existing is None or (
                existing["asset_type"] == "etf" and normalized_type == "equity"
            ):
                unique[symbol] = candidate

        symbols = sorted(unique.values(), key=lambda item: item["ticker"])
        return {
            "source": "finnhub",
            "exchange": exchange.upper(),
            "total_available": len(symbols),
            "offset": offset,
            "limit": limit,
            "symbols": symbols[offset : offset + limit],
        }


stock_universe_service = StockUniverseService(finnhub_service)
