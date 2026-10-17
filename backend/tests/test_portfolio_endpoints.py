"""Exercise portfolio HTTP routes with real cleaning, scoring, and persistence.

Only provider boundaries are mocked; expectations below are calculated from the
small, synthetic portfolios rather than copied from the scoring implementation.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.errors import AppError, ProviderError
from backend.main import create_app
from backend.models import PlaidItem, User
from backend.routes import plaid as plaid_routes
from backend.services.security_service import create_access_token, encrypt_secret

PORTFOLIO_PATHS = ("/portfolio_analysis", "/portfolio")


def plaid_payload(*positions):
    """Build a provider response from (ticker, asset type, value) positions."""
    return {
        "accounts": [
            {"account_id": "account-1", "name": "Investments", "type": "investment"}
        ],
        "securities": [
            {
                "security_id": f"security-{index}",
                "ticker_symbol": ticker,
                "name": ticker or "Cash",
                "type": asset_type,
            }
            for index, (ticker, asset_type, _value) in enumerate(positions)
        ],
        "holdings": [
            {
                "security_id": f"security-{index}",
                "account_id": "account-1",
                "quantity": 2,
                "institution_price": value / 2,
                "institution_value": value,
            }
            for index, (_ticker, _asset_type, value) in enumerate(positions)
        ],
    }


@pytest.fixture
def portfolio_api(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'portfolio.sqlite3').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()

    def test_db():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    providers = SimpleNamespace(
        holdings=AsyncMock(return_value=plaid_payload()),
        metrics=AsyncMock(return_value={}),
        profile=AsyncMock(return_value={}),
        ai=AsyncMock(return_value="The portfolio holds a single position."),
    )
    monkeypatch.setattr(plaid_routes.plaid_service, "get_holdings", providers.holdings)
    service = plaid_routes.portfolio_service
    monkeypatch.setattr(service.market_data, "get_clean_metrics", providers.metrics)
    monkeypatch.setattr(service.market_data, "get_company_profile", providers.profile)
    monkeypatch.setattr(service.ai, "explain_portfolio", providers.ai)

    def user(email="owner@example.com"):
        with sessions() as session:
            account = User(email=email, password_hash="unused-in-token-authentication")
            session.add(account)
            session.commit()
            return account.id, {"Authorization": f"Bearer {create_access_token(account.id)}"}

    def connect(user_id, token="owner-access-token", status="active"):
        with sessions() as session:
            item = PlaidItem(
                user_id=user_id,
                plaid_item_id=f"item-{token}",
                encrypted_access_token=encrypt_secret(token),
                connection_status=status,
            )
            session.add(item)
            session.commit()
            return item.id

    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            providers=providers,
            user=user,
            connect=connect,
            sessions=sessions,
        )
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.parametrize("path", PORTFOLIO_PATHS)
@pytest.mark.parametrize(
    ("headers", "error_code"),
    [({}, "authentication_required"), ({"Authorization": "Bearer invalid"}, "invalid_token")],
)
def test_portfolio_routes_require_valid_authentication(portfolio_api, path, headers, error_code):
    response = portfolio_api.client.get(path, headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == error_code
    portfolio_api.providers.holdings.assert_not_awaited()


@pytest.mark.parametrize("path", PORTFOLIO_PATHS)
@pytest.mark.parametrize("connection_status", [None, "error"])
def test_portfolio_requires_an_active_connection(portfolio_api, path, connection_status):
    user_id, headers = portfolio_api.user()
    if connection_status:
        portfolio_api.connect(user_id, status=connection_status)

    response = portfolio_api.client.get(path, headers=headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "plaid_not_connected"
    portfolio_api.providers.holdings.assert_not_awaited()


def test_portfolio_does_not_read_another_users_connection(portfolio_api):
    owner_id, owner_headers = portfolio_api.user()
    _other_id, other_headers = portfolio_api.user("other@example.com")
    portfolio_api.connect(owner_id)
    portfolio_api.providers.holdings.return_value = plaid_payload((None, "cash", 125))

    denied = portfolio_api.client.get("/portfolio_analysis", headers=other_headers)
    assert denied.status_code == 400
    assert denied.json()["error"]["code"] == "plaid_not_connected"
    portfolio_api.providers.holdings.assert_not_awaited()

    allowed = portfolio_api.client.get("/portfolio_analysis", headers=owner_headers)
    assert allowed.status_code == 200
    assert allowed.json()["total_value"] == 125
    portfolio_api.providers.holdings.assert_awaited_once_with("owner-access-token")


@pytest.mark.parametrize("path", PORTFOLIO_PATHS)
def test_portfolio_calculates_allocation_concentration_and_equity_scores(portfolio_api, path):
    user_id, headers = portfolio_api.user()
    portfolio_api.connect(user_id)
    # Deliberately unsorted so position rankings also pass through the real service.
    portfolio_api.providers.holdings.return_value = plaid_payload(
        (None, "cash", 100),
        ("HEALTH", "equity", 250),
        ("BOND", "fixed income", 50),
        ("TECH", "equity", 400),
        ("FUND", "etf", 200),
    )
    metrics = {
        "TECH": {
            "ticker": "TECH",
            "pe_ratio": 15,
            "revenue_growth": 20,
            "eps_growth": 20,
            "profit_margin": 20,
            "return_on_equity": 20,
            "current_ratio": 2,
            "52_week_return": 20,
        },
        "HEALTH": {
            "ticker": "HEALTH",
            "pe_ratio": 30,
            "revenue_growth": 10,
            "eps_growth": 10,
            "profit_margin": 10,
            "return_on_equity": 10,
            "current_ratio": 1,
            "52_week_return": -5,
        },
    }

    async def get_metrics(ticker):
        return metrics[ticker]

    async def get_profile(ticker):
        return {"finnhubIndustry": {"TECH": "Technology", "HEALTH": "Healthcare"}[ticker]}

    portfolio_api.providers.metrics.side_effect = get_metrics
    portfolio_api.providers.profile.side_effect = get_profile

    response = portfolio_api.client.get(path, headers=headers)

    assert response.status_code == 200
    result = response.json()
    assert result["simulated"] is False
    assert result["total_value"] == 1000
    assert result["position_count"] == 5
    assert [holding["ticker"] for holding in result["holdings"]] == [
        "TECH", "HEALTH", "FUND", None, "BOND"
    ]
    assert [holding["weight"] for holding in result["holdings"]] == [40, 25, 20, 10, 5]
    assert result["largest_position"] == {"ticker": "TECH", "name": "TECH", "weight": 40}
    assert result["top_3_concentration"] == 85
    assert result["top_5_concentration"] == 100
    # 40² + 25² + 20² + 10² + 5² = 2750; 10000 / 2750 = 3.64 positions.
    assert result["concentration_hhi"] == 2750
    assert result["effective_position_count"] == 3.64
    assert result["asset_type_allocation"] == {
        "equity": 65, "etf": 20, "cash": 10, "fixed income": 5
    }
    assert result["sector_allocation"] == {"Technology": 40, "Healthcare": 25}
    assert result["largest_sector"] == {"sector": "Technology", "weight": 40}
    assert result["holdings"][0]["analysis"]["score"]["overall_score"] == 100
    # 50*.20 + 80*.25 + 80*.25 + 70*.15 + 40*.15 = 66.5.
    health_score = result["holdings"][1]["analysis"]["score"]
    assert health_score["overall_score"] == 66.5
    assert health_score["signal"] == "mixed"
    assert health_score["data_coverage"] == 100
    assert all(
        holding["analysis"]["status"] == "not_analyzed"
        for holding in result["holdings"][2:]
    )
    assert {call.args[0] for call in portfolio_api.providers.metrics.await_args_list} == {
        "TECH", "HEALTH"
    }
    assert result["ai_explanation"] is None
    portfolio_api.providers.ai.assert_not_awaited()


@pytest.mark.parametrize(
    ("metrics", "expected_score", "expected_coverage", "expected_signal"),
    [
        ({"ticker": "PARTIAL", "pe_ratio": 20}, 75, 20, "positive"),
        ({"ticker": "PARTIAL", "pe_ratio": None}, None, 0, "insufficient_data"),
    ],
)
def test_portfolio_keeps_missing_metrics_missing(
    portfolio_api, metrics, expected_score, expected_coverage, expected_signal
):
    user_id, headers = portfolio_api.user()
    portfolio_api.connect(user_id)
    portfolio_api.providers.holdings.return_value = plaid_payload(("PARTIAL", "equity", 200))
    portfolio_api.providers.metrics.return_value = metrics

    response = portfolio_api.client.get("/portfolio_analysis", headers=headers)

    assert response.status_code == 200
    result = response.json()
    assert result["sector_allocation"] == {"Unknown": 100}
    analysis = result["holdings"][0]["analysis"]
    assert analysis["metrics"] == metrics
    score = analysis["score"]
    assert score["overall_score"] == expected_score
    assert score["data_coverage"] == expected_coverage
    assert score["signal"] == expected_signal
    assert score["categories"]["growth"] is None
    assert score["categories"]["profitability"] is None
    assert score["categories"]["financial_health"] is None
    assert score["categories"]["momentum"] is None


def test_portfolio_market_failure_preserves_holdings_and_unknown_sector(portfolio_api):
    user_id, headers = portfolio_api.user()
    portfolio_api.connect(user_id)
    portfolio_api.providers.holdings.return_value = plaid_payload(("MISSING", "equity", 200))
    portfolio_api.providers.metrics.side_effect = ProviderError(
        "market_unavailable", "Market data unavailable", 502
    )
    portfolio_api.providers.profile.side_effect = ProviderError(
        "profile_unavailable", "Profile unavailable", 502
    )

    response = portfolio_api.client.get("/portfolio_analysis", headers=headers)

    assert response.status_code == 200
    result = response.json()
    assert result["total_value"] == 200
    assert result["top_3_concentration"] == 100
    assert result["sector_allocation"] == {"Unknown": 100}
    assert result["holdings"][0]["analysis"] == {
        "status": "unavailable", "reason": "Market data unavailable"
    }


def test_portfolio_provider_failure_marks_connection_and_returns_gateway_error(portfolio_api):
    user_id, headers = portfolio_api.user()
    connection_id = portfolio_api.connect(user_id)
    portfolio_api.providers.holdings.side_effect = ProviderError(
        "plaid_holdings_error", "Provider is down", 502
    )

    response = portfolio_api.client.get("/portfolio_analysis", headers=headers)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "plaid_holdings_unavailable"
    with portfolio_api.sessions() as session:
        assert session.get(PlaidItem, connection_id).connection_status == "error"
    portfolio_api.providers.metrics.assert_not_awaited()
    portfolio_api.providers.ai.assert_not_awaited()


def test_portfolio_uses_successful_accounts_when_one_provider_request_fails(portfolio_api):
    user_id, headers = portfolio_api.user()
    failed_id = portfolio_api.connect(user_id, "failed-access-token")
    good_id = portfolio_api.connect(user_id, "good-access-token")

    async def get_holdings(access_token):
        if access_token == "failed-access-token":
            raise ProviderError("plaid_holdings_error", "Provider is down", 502)
        return plaid_payload((None, "cash", 250))

    portfolio_api.providers.holdings.side_effect = get_holdings

    response = portfolio_api.client.get("/portfolio_analysis", headers=headers)

    assert response.status_code == 200
    assert response.json()["total_value"] == 250
    assert response.json()["asset_type_allocation"] == {"cash": 100}
    with portfolio_api.sessions() as session:
        assert session.get(PlaidItem, failed_id).connection_status == "error"
        good_item = session.get(PlaidItem, good_id)
        assert good_item.connection_status == "active"
        assert good_item.account_metadata[0]["account_id"] == "account-1"


def test_portfolio_empty_connected_account_has_zero_allocation(portfolio_api):
    user_id, headers = portfolio_api.user()
    portfolio_api.connect(user_id)

    response = portfolio_api.client.get("/portfolio_analysis", headers=headers)

    assert response.status_code == 200
    result = response.json()
    assert result["total_value"] == 0
    assert result["position_count"] == 0
    assert result["holdings"] == []
    assert result["asset_type_allocation"] == {}
    assert result["sector_allocation"] == {}
    assert result["largest_position"] is None
    assert result["largest_sector"] is None
    assert result["top_3_concentration"] == 0
    assert result["top_5_concentration"] == 0
    assert result["concentration_hhi"] == 0
    assert result["effective_position_count"] is None


def test_portfolio_ai_receives_calculated_evidence_without_credentials(portfolio_api):
    user_id, headers = portfolio_api.user()
    portfolio_api.connect(user_id)
    portfolio_api.providers.holdings.return_value = plaid_payload((None, "cash", 125))
    portfolio_api.providers.ai.return_value = "Cash accounts for 100% of the portfolio."

    response = portfolio_api.client.get(
        "/portfolio_analysis?include_ai=true", headers=headers
    )

    assert response.status_code == 200
    result = response.json()
    assert result["ai_explanation"] == "Cash accounts for 100% of the portfolio."
    portfolio_api.providers.ai.assert_awaited_once()
    evidence = portfolio_api.providers.ai.await_args.args[0]
    assert evidence["total_value"] == 125
    assert evidence["asset_type_allocation"] == {"cash": 100}
    assert evidence["concentration_hhi"] == 10000
    assert evidence["holdings"][0]["weight"] == 100
    assert "ai_explanation" not in evidence
    assert "owner-access-token" not in str(evidence)
    assert user_id not in str(evidence)


def test_portfolio_ai_failure_still_returns_calculated_analysis(portfolio_api):
    user_id, headers = portfolio_api.user()
    portfolio_api.connect(user_id)
    portfolio_api.providers.holdings.return_value = plaid_payload((None, "cash", 125))
    portfolio_api.providers.ai.side_effect = AppError("ai_unavailable", "AI unavailable", 503)

    response = portfolio_api.client.get("/portfolio?include_ai=true", headers=headers)

    assert response.status_code == 200
    assert response.json()["total_value"] == 125
    assert response.json()["concentration_hhi"] == 10000
    assert response.json()["ai_explanation"] is None
