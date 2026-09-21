import asyncio
from typing import Any

import plaid
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest

from backend.config import settings
from backend.errors import AppError, ProviderError


class PlaidService:
    def __init__(self) -> None:
        self.client = None
        if settings.plaid_client_id and settings.plaid_secret:
            environment = {
                "sandbox": plaid.Environment.Sandbox,
                "production": plaid.Environment.Production,
            }.get(settings.plaid_environment, plaid.Environment.Sandbox)
            configuration = plaid.Configuration(
                host=environment,
                api_key={
                    "clientId": settings.plaid_client_id,
                    "secret": settings.plaid_secret,
                },
            )
            self.client = plaid_api.PlaidApi(plaid.ApiClient(configuration))

    def _require_client(self):
        if self.client is None:
            raise AppError(
                "plaid_not_configured",
                "Plaid credentials are not configured",
                503,
            )
        return self.client

    async def create_link_token(self, user_id: str) -> str:
        client = self._require_client()
        request = LinkTokenCreateRequest(
            products=[Products("investments")],
            client_name="AI Investment Research",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
        )
        try:
            response = await asyncio.to_thread(client.link_token_create, request)
            return response.link_token
        except Exception as exc:
            raise ProviderError("plaid_error", "Plaid link token creation failed", 502) from exc

    async def create_sandbox_public_token(self) -> str:
        if settings.plaid_environment != "sandbox":
            raise AppError(
                "sandbox_only",
                "Sandbox public tokens are unavailable outside sandbox mode",
                403,
            )
        client = self._require_client()
        request = SandboxPublicTokenCreateRequest(
            institution_id="ins_109508",
            initial_products=[Products("investments")],
        )
        try:
            response = await asyncio.to_thread(client.sandbox_public_token_create, request)
            return response.public_token
        except Exception as exc:
            raise ProviderError("plaid_error", "Plaid sandbox token creation failed", 502) from exc

    async def exchange_public_token(self, public_token: str) -> dict[str, str]:
        client = self._require_client()
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        try:
            response = await asyncio.to_thread(client.item_public_token_exchange, request)
            return {
                "access_token": response.access_token,
                "item_id": response.item_id,
            }
        except Exception as exc:
            raise ProviderError("plaid_error", "Plaid public-token exchange failed", 502) from exc

    async def get_holdings(self, access_token: str) -> dict[str, Any]:
        client = self._require_client()
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        try:
            response = await asyncio.to_thread(client.investments_holdings_get, request)
            return response.to_dict()
        except Exception as exc:
            raise ProviderError(
                "plaid_holdings_error",
                "Plaid investment holdings are unavailable",
                502,
            ) from exc

    @staticmethod
    def clean_holdings(data: dict[str, Any]) -> list[dict[str, Any]]:
        securities = {security["security_id"]: security for security in data.get("securities", [])}
        portfolio = []
        for holding in data.get("holdings", []):
            security = securities.get(holding.get("security_id"), {})
            portfolio.append(
                {
                    "ticker": security.get("ticker_symbol"),
                    "name": security.get("name"),
                    "type": str(security.get("type") or "other").lower(),
                    "shares": holding.get("quantity"),
                    "price": holding.get("institution_price"),
                    "value": holding.get("institution_value") or 0,
                    "account_id": holding.get("account_id"),
                }
            )
        return portfolio


plaid_service = PlaidService()
