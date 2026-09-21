from backend.services.plaid_service import PlaidService


class FakeResponse:
    def to_dict(self):
        return {"accounts": [], "holdings": [], "securities": []}


class FakePlaidClient:
    def investments_holdings_get(self, _request):
        return FakeResponse()


def test_clean_holdings_joins_security_metadata():
    data = {
        "securities": [
            {
                "security_id": "security-1",
                "ticker_symbol": "AAPL",
                "name": "Apple",
                "type": "equity",
            }
        ],
        "holdings": [
            {
                "security_id": "security-1",
                "account_id": "account-1",
                "quantity": 2,
                "institution_price": 200,
                "institution_value": 400,
            }
        ],
    }

    result = PlaidService.clean_holdings(data)

    assert result == [
        {
            "ticker": "AAPL",
            "name": "Apple",
            "type": "equity",
            "shares": 2,
            "price": 200,
            "value": 400,
            "account_id": "account-1",
        }
    ]


def test_get_holdings_uses_mocked_plaid_client():
    import asyncio

    service = PlaidService()
    service.client = FakePlaidClient()

    result = asyncio.run(service.get_holdings("fake-token"))

    assert result == {"accounts": [], "holdings": [], "securities": []}
