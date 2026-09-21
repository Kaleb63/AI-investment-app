import asyncio

import httpx

from backend.schemas.screen import ScreeningCriteria
from backend.services.ai_service import AIService
from backend.services.cache import MemoryTTLCache
from backend.services.finnhub_service import FinnhubService
from backend.services.stock_universe_service import StockUniverseService


class FakeUniverseProvider:
    async def get_symbols(self, exchange="US"):
        equities = [
            {
                "symbol": f"T{index}",
                "description": f"Company {index}",
                "type": "Common Stock",
                "currency": "USD",
            }
            for index in range(1200)
        ]
        return equities + [
            {
                "symbol": "ETF1",
                "description": "Example ETF",
                "type": "ETP",
                "currency": "USD",
            },
            equities[0],
            {
                "symbol": "BAD SYMBOL",
                "description": "Malformed",
                "type": "Common Stock",
                "currency": "USD",
            },
        ]


def test_stock_universe_supports_1000_equities_and_separates_etfs():
    service = StockUniverseService(FakeUniverseProvider())
    equities = asyncio.run(service.list_symbols(asset_type="equity", limit=1000))
    etfs = asyncio.run(service.list_symbols(asset_type="etf", limit=1000))

    assert equities["total_available"] == 1200
    assert len(equities["symbols"]) == 1000
    assert etfs["symbols"] == [
        {
            "ticker": "ETF1",
            "name": "Example ETF",
            "asset_type": "etf",
            "exchange": "US",
        }
    ]


def test_finnhub_metrics_are_cached_without_a_second_request():
    from backend.services import finnhub_service as finnhub_module

    original_key = finnhub_module.settings.finnhub_api_key
    object.__setattr__(finnhub_module.settings, "finnhub_api_key", "test-key")
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"metric": {"peTTM": 20}},
            request=request,
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://example.test",
    )
    cache = MemoryTTLCache()
    service = FinnhubService(cache, client)

    try:
        first = asyncio.run(service.get_clean_metrics("AAPL"))
        second = asyncio.run(service.get_clean_metrics("AAPL"))
        asyncio.run(client.aclose())
    finally:
        object.__setattr__(finnhub_module.settings, "finnhub_api_key", original_key)

    assert first == second
    assert calls == 1
    assert cache.stats() == {"hits": 1, "misses": 1}


class FakeAIResponse:
    output_parsed = ScreeningCriteria(
        min_score=70,
        max_pe_ratio=30,
        min_revenue_growth=15,
        min_profit_margin=10,
    )


class FakeResponses:
    async def parse(self, **_kwargs):
        return FakeAIResponse()


class FakeOpenAIClient:
    responses = FakeResponses()


def test_ai_criteria_are_validated_into_the_deterministic_schema():
    service = AIService()
    service._client = FakeOpenAIClient()

    result = asyncio.run(service.parse_screening_query("profitable growth at a fair price"))

    assert result == ScreeningCriteria(
        min_score=70,
        max_pe_ratio=30,
        min_revenue_growth=15,
        min_profit_margin=10,
    )
