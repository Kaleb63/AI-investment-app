import math
import statistics
from datetime import date, timedelta
from typing import Any

from backend.errors import ProviderError
from backend.services.finnhub_service import FinnhubService, finnhub_service


def _period_return(closes: list[float], trading_days: int) -> float | None:
    if len(closes) <= trading_days or closes[-trading_days - 1] == 0:
        return None
    return round((closes[-1] / closes[-trading_days - 1] - 1) * 100, 2)


class HistoricalService:
    def __init__(self, market_data: FinnhubService) -> None:
        self.market_data = market_data

    async def analyze(self, ticker: str) -> dict[str, Any]:
        end_date = date.today()
        start_date = end_date - timedelta(days=370)
        data = await self.market_data.get_candles(ticker, start_date, end_date)
        if data.get("s") != "ok" or not data.get("c"):
            raise ProviderError(
                "historical_data_unavailable",
                f"Historical price data is unavailable for {ticker}",
                404,
            )
        closes = [float(value) for value in data["c"]]
        daily_returns = [
            closes[index] / closes[index - 1] - 1
            for index in range(1, len(closes))
            if closes[index - 1] != 0
        ]
        volatility = (
            statistics.stdev(daily_returns) * math.sqrt(252) * 100
            if len(daily_returns) > 1
            else None
        )
        return {
            "ticker": ticker.upper(),
            "start_date": start_date,
            "end_date": end_date,
            "observations": len(closes),
            "latest_close": closes[-1],
            "returns": {
                "one_month": _period_return(closes, 21),
                "three_month": _period_return(closes, 63),
                "six_month": _period_return(closes, 126),
                "one_year": _period_return(closes, 252),
            },
            "annualized_volatility": (round(volatility, 2) if volatility is not None else None),
            "moving_averages": {
                "sma_50": round(sum(closes[-50:]) / 50, 2) if len(closes) >= 50 else None,
                "sma_200": round(sum(closes[-200:]) / 200, 2) if len(closes) >= 200 else None,
            },
            "note": "Historical indicators are reported separately from fundamental scoring.",
        }


historical_service = HistoricalService(finnhub_service)
