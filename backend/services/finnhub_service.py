import asyncio
import logging
import random
from datetime import UTC, date, datetime, time
from typing import Any

import httpx

from backend.config import settings
from backend.errors import AppError, ProviderError, RateLimitError
from backend.schemas.common import normalize_ticker
from backend.services.cache import CacheService, cache_service

logger = logging.getLogger(__name__)


class FinnhubService:
    def __init__(
        self,
        cache: CacheService,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.cache = cache
        self._client = client
        self._owns_client = client is None
        self._semaphore = asyncio.Semaphore(settings.finnhub_max_concurrency)

    async def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.finnhub_base_url,
                timeout=httpx.Timeout(settings.finnhub_timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        endpoint: str,
        *,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
        **params: Any,
    ) -> Any:
        if cache_key:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        if not settings.finnhub_api_key:
            raise AppError(
                "finnhub_not_configured",
                "FINNHUB_API_KEY is not configured",
                503,
            )

        client = await self._http_client()
        request_params = {"token": settings.finnhub_api_key, **params}
        for attempt in range(settings.finnhub_max_retries + 1):
            try:
                async with self._semaphore:
                    response = await client.get(endpoint, params=request_params)

                if response.status_code == 429:
                    retry_after = min(float(response.headers.get("Retry-After", "1")), 30.0)
                    if attempt < settings.finnhub_max_retries:
                        await asyncio.sleep(retry_after + random.uniform(0, 0.25))
                        continue
                    raise RateLimitError(
                        "finnhub_rate_limited",
                        "Finnhub rate limit was reached",
                        429,
                    )

                if response.status_code in {500, 502, 503, 504}:
                    response.raise_for_status()
                if response.status_code in {401, 403}:
                    raise ProviderError(
                        "finnhub_access_denied",
                        "Finnhub rejected the request or plan access",
                        502,
                    )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict) and data.get("error"):
                    raise ProviderError("finnhub_error", str(data["error"]), 502)
                if cache_key:
                    await self.cache.set(
                        cache_key,
                        data,
                        cache_ttl or settings.metrics_cache_ttl_seconds,
                    )
                return data
            except (RateLimitError, ProviderError):
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
                if attempt >= settings.finnhub_max_retries:
                    break
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.25))

        logger.warning("Finnhub request failed endpoint=%s", endpoint)
        raise ProviderError(
            "finnhub_unavailable",
            "Finnhub data is temporarily unavailable",
            502,
        ) from None

    async def get_quote(self, ticker: str) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        data = await self.request(
            "/quote",
            symbol=ticker,
            cache_key=f"quote:{ticker}",
            cache_ttl=60,
        )
        if not data or data.get("c") in {None, 0}:
            raise ProviderError(
                "ticker_unavailable",
                f"No current quote is available for {ticker}",
                404,
            )
        return data

    async def get_stock_metrics(self, ticker: str) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        return await self.request(
            "/stock/metric",
            symbol=ticker,
            metric="all",
            cache_key=f"metrics:{ticker}",
        )

    async def get_clean_metrics(self, ticker: str) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        data = await self.get_stock_metrics(ticker)
        metrics = data.get("metric", {}) if isinstance(data, dict) else {}
        return {
            "ticker": ticker,
            "pe_ratio": metrics.get("peTTM"),
            "eps": metrics.get("epsTTM"),
            "revenue_growth": metrics.get("revenueGrowthTTMYoy"),
            "eps_growth": metrics.get("epsGrowthTTMYoy"),
            "profit_margin": metrics.get("netProfitMarginTTM"),
            "return_on_equity": metrics.get("roeTTM"),
            "current_ratio": metrics.get("currentRatioAnnual"),
            "beta": metrics.get("beta"),
            "52_week_return": metrics.get("52WeekPriceReturnDaily"),
        }

    async def get_company_profile(self, ticker: str) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        return await self.request(
            "/stock/profile2",
            symbol=ticker,
            cache_key=f"profile:{ticker}",
            cache_ttl=86400,
        )

    async def get_symbols(self, exchange: str = "US") -> list[dict[str, Any]]:
        data = await self.request(
            "/stock/symbol",
            exchange=exchange,
            cache_key=f"symbols:{exchange.upper()}",
            cache_ttl=86400,
        )
        return data if isinstance(data, list) else []

    async def get_candles(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        start_timestamp = int(datetime.combine(start_date, time.min, tzinfo=UTC).timestamp())
        end_timestamp = int(datetime.combine(end_date, time.max, tzinfo=UTC).timestamp())
        return await self.request(
            "/stock/candle",
            symbol=ticker,
            resolution="D",
            **{"from": start_timestamp, "to": end_timestamp},
            cache_key=f"candles:{ticker}:{start_date}:{end_date}",
            cache_ttl=3600,
        )


finnhub_service = FinnhubService(cache_service)
