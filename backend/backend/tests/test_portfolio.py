import asyncio

from backend.services.portfolio_service import PortfolioService


class NoExternalMarket:
    async def get_clean_metrics(self, ticker):
        raise AssertionError("cash and preloaded demo data must not call market data")

    async def get_company_profile(self, ticker):
        raise AssertionError("preloaded demo data must not call company profile")


class NoAI:
    async def explain_portfolio(self, evidence):
        raise AssertionError("AI should not run unless requested")


def holding(ticker, value, asset_type="equity"):
    item = {
        "ticker": ticker,
        "name": ticker or "Cash",
        "type": asset_type,
        "shares": 1,
        "price": value,
        "value": value,
    }
    if asset_type == "equity":
        item["sector"] = "Technology"
        item["simulated_metrics"] = {
            "ticker": ticker,
            "pe_ratio": 15,
            "revenue_growth": 20,
            "eps_growth": 20,
            "profit_margin": 20,
            "return_on_equity": 20,
            "current_ratio": 2,
            "52_week_return": 20,
        }
    return item


def test_single_holding_is_100_percent_concentrated():
    service = PortfolioService(NoExternalMarket(), NoAI())
    result = asyncio.run(service.analyze([holding("ONE", 100)]))
    assert result.holdings[0].weight == 100
    assert result.top_3_concentration == 100
    assert result.concentration_hhi == 10000
    assert result.effective_position_count == 1


def test_multiple_holdings_cash_and_percentages():
    service = PortfolioService(NoExternalMarket(), NoAI())
    result = asyncio.run(
        service.analyze(
            [
                holding("AAA", 50),
                holding("BBB", 30),
                holding(None, 20, "cash"),
            ]
        )
    )
    assert [item.weight for item in result.holdings] == [50, 30, 20]
    assert result.top_3_concentration == 100
    assert result.asset_type_allocation == {"cash": 20, "equity": 80}
    assert result.holdings[2].analysis["status"] == "not_analyzed"


def test_unsupported_asset_and_missing_ticker_are_not_equity_scored():
    service = PortfolioService(NoExternalMarket(), NoAI())
    result = asyncio.run(
        service.analyze(
            [
                holding(None, 60, "equity"),
                holding("BOND", 40, "fixed income"),
            ]
        )
    )
    assert all(item.analysis["status"] == "not_analyzed" for item in result.holdings)
