
import json
import os

import httpx
import plaid
from openai import OpenAI
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from fastapi import HTTPException
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest

class PublicTokenRequest(BaseModel):
    public_token: str

from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("FINNHUB_API_KEY", "").strip()
app = FastAPI()
plaid_client_id = os.getenv("PLAID_CLIENT_ID")
plaid_secret = os.getenv("PLAID_SECRET")
#sandbox environment for testing
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        "clientId": plaid_client_id,
        "secret": plaid_secret,
    }
)
#create a plaid client
api_client = plaid.ApiClient(configuration)
plaid_client = plaid_api.PlaidApi(api_client)
access_token = None
openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

openai_client = None

# Keep non-AI endpoints available when an OpenAI key has not been configured.
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)


#home page message
@app.get("/")
def home():
    return {"message": "Investment app backend is running"}

#test data for stocks
stocks = {
    "AAPL": {"price": 200, "shares": 5},
    "NVDA": {"price": 180, "shares": 2},
    "TSLA": {"price": 700, "shares": 3}
}

#get stock price info for a specific ticker
@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    ticker = ticker.upper()
    return {
        "ticker": ticker,
        "price": get_live_price(ticker),
        "shares": stocks[ticker]["shares"],
        "value": get_live_price(ticker) * stocks[ticker]["shares"]
    }
#create a link token for the plaid api
@app.post("/create_link_token")
def create_link_token():
    request = LinkTokenCreateRequest(
        products=[Products("investments")],
        client_name="Investment App",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id="user-id")
    )
    response = plaid_client.link_token_create(request)
    return {"link_token": response.link_token}
# Get temporary access token from Plaid
@app.post("/exchange_public_token")
def exchange_public_token(data: PublicTokenRequest):
    global access_token

    request = ItemPublicTokenExchangeRequest(
        public_token=data.public_token
    )

    response = plaid_client.item_public_token_exchange(request)

    access_token = response.access_token

    return {"message": "Plaid account connected"}
#get a sandbox public token for testing purposes
@app.post("/sandbox_public_token")
def create_sandbox_public_token():

    request = SandboxPublicTokenCreateRequest(
        institution_id="ins_109508",
        initial_products=[Products("investments")]
    )

    response = plaid_client.sandbox_public_token_create(request)

    return {
        "public_token": response.public_token
    }

# get investment data using the Plaid access token
@app.get("/holdings")
def get_holdings():
    if access_token is None:
        raise HTTPException(
            status_code=400,
            detail="Connect a Plaid account first"
        )

    request = InvestmentsHoldingsGetRequest(
        access_token=access_token
    )

    response = plaid_client.investments_holdings_get(request)

    return response.to_dict()

def get_plaid_portfolio_data():

    if access_token is None:
        raise HTTPException(
            status_code=400,
            detail="Connect a Plaid account first"
        )

    request = InvestmentsHoldingsGetRequest(
        access_token=access_token
    )

    response = plaid_client.investments_holdings_get(request)

    data = response.to_dict()

    securities = {
        security["security_id"]: security
        for security in data["securities"]
    }

    portfolio = []

    for holding in data["holdings"]:
        security = securities[holding["security_id"]]
        portfolio.append({
            "ticker": security.get("ticker_symbol"),
            "name": security.get("name"),
            "type": security.get("type"),
            "shares": holding.get("quantity"),
            "price": holding.get("institution_price"),
            "value": holding.get("institution_value")
        })

    return portfolio

# clean up the portfolio data to only include relevant information
@app.get("/plaid_portfolio")
def get_plaid_portfolio():
    portfolio = get_plaid_portfolio_data()

    return {"portfolio": portfolio}

#get live stock price from finnhub api
def get_finnhub_data(endpoint: str, ticker: str, **params):
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=f"FINNHUB_API_KEY is missing from {env_path}"
        )

    try:
        response = httpx.get(
            f"https://finnhub.io/api/v1/{endpoint}",
            params={
                "symbol": ticker,
                "token": api_key,
                **params
            },
            timeout=10.0
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Finnhub data unavailable for {ticker}"
        ) from exc

    data = response.json()
    if "error" in data:
        raise HTTPException(status_code=502, detail=f"Finnhub error: {data['error']}")

    return data


def get_live_price(ticker: str):
    data = get_finnhub_data("quote", ticker)
    return data["c"] #return current price

def get_stock_metrics(ticker: str):
    return get_finnhub_data("stock/metric", ticker, metric="all")

def get_clean_metrics(ticker: str):
    data = get_stock_metrics(ticker)
    metrics = data.get("metric", {})

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
        "52_week_return": metrics.get("52WeekPriceReturnDaily")
    }


def score_growth_metric(growth):

    if growth >= 20:
        return 100

    elif growth >= 10:
        return 80

    elif growth > 0:
        return 65

    elif growth == 0:
        return 50

    elif growth >= -10:
        return 35

    else:
        return 15


def score_equity(metrics):

    pe_ratio = metrics.get("pe_ratio")
    revenue_growth = metrics.get("revenue_growth")
    eps_growth = metrics.get("eps_growth")
    profit_margin = metrics.get("profit_margin")
    return_on_equity = metrics.get("return_on_equity")
    current_ratio = metrics.get("current_ratio")
    year_return = metrics.get("52_week_return")

    category_scores = {
        "valuation": None,
        "growth": None,
        "profitability": None,
        "financial_health": None,
        "momentum": None
    }

    reasons = []

    # -------------------------
    # Valuation - 20%
    # -------------------------
    if pe_ratio is not None and pe_ratio > 0:

        if pe_ratio <= 15:
            category_scores["valuation"] = 100
            reasons.append("P/E ratio is low")

        elif pe_ratio <= 25:
            category_scores["valuation"] = 75
            reasons.append("P/E ratio is moderate")

        elif pe_ratio <= 40:
            category_scores["valuation"] = 50
            reasons.append("P/E ratio is elevated")

        else:
            category_scores["valuation"] = 25
            reasons.append("P/E ratio is high")

    # -------------------------
    # Growth - 25%
    # -------------------------
    growth_scores = []

    if revenue_growth is not None:
        growth_scores.append(score_growth_metric(revenue_growth))

        if revenue_growth >= 20:
            reasons.append("Revenue growth is strong")
        elif revenue_growth > 0:
            reasons.append("Revenue is growing")
        else:
            reasons.append("Revenue growth is negative")

    if eps_growth is not None:
        growth_scores.append(score_growth_metric(eps_growth))

        if eps_growth >= 20:
            reasons.append("EPS growth is strong")
        elif eps_growth > 0:
            reasons.append("EPS is growing")
        else:
            reasons.append("EPS growth is negative")

    if growth_scores:
        category_scores["growth"] = (
            sum(growth_scores) / len(growth_scores)
        )

    # -------------------------
    # Profitability - 25%
    # -------------------------
    profitability_scores = []

    if profit_margin is not None:

        if profit_margin >= 20:
            profitability_scores.append(100)

        elif profit_margin >= 10:
            profitability_scores.append(80)

        elif profit_margin > 0:
            profitability_scores.append(60)

        else:
            profitability_scores.append(20)

        if profit_margin >= 20:
            reasons.append("Profit margin is strong")
        elif profit_margin > 0:
            reasons.append("Company is profitable")
        else:
            reasons.append("Company has a negative profit margin")

    if return_on_equity is not None:

        if return_on_equity >= 20:
            profitability_scores.append(100)

        elif return_on_equity >= 10:
            profitability_scores.append(80)

        elif return_on_equity > 0:
            profitability_scores.append(60)

        else:
            profitability_scores.append(20)

        if return_on_equity >= 20:
            reasons.append("Return on equity is strong")
        elif return_on_equity >= 10:
            reasons.append("Return on equity is healthy")
        elif return_on_equity > 0:
            reasons.append("Return on equity is positive but relatively low")
        else:
            reasons.append("Return on equity is negative")

    if profitability_scores:
        category_scores["profitability"] = (
            sum(profitability_scores) / len(profitability_scores)
        )

    # -------------------------
    # Financial Health - 15%
    # -------------------------
    if current_ratio is not None:

        if current_ratio >= 2:
            category_scores["financial_health"] = 100

        elif current_ratio >= 1.5:
            category_scores["financial_health"] = 85

        elif current_ratio >= 1:
            category_scores["financial_health"] = 70

        elif current_ratio >= 0.75:
            category_scores["financial_health"] = 45

        else:
            category_scores["financial_health"] = 20

        if current_ratio >= 1.5:
            reasons.append("Liquidity is strong")
        elif current_ratio >= 1:
            reasons.append("Current assets cover current liabilities")
        else:
            reasons.append("Current ratio is below 1")

    # -------------------------
    # Momentum - 15%
    # -------------------------
    if year_return is not None:

        if year_return >= 20:
            category_scores["momentum"] = 100

        elif year_return >= 10:
            category_scores["momentum"] = 80

        elif year_return > 0:
            category_scores["momentum"] = 65

        elif year_return >= -10:
            category_scores["momentum"] = 40

        else:
            category_scores["momentum"] = 20

        if year_return >= 20:
            reasons.append("52-week price momentum is strong")
        elif year_return > 0:
            reasons.append("Stock has positive 52-week momentum")
        else:
            reasons.append("Stock has negative 52-week momentum")

    # Category weights
    weights = {
        "valuation": 20,
        "growth": 25,
        "profitability": 25,
        "financial_health": 15,
        "momentum": 15
    }

    weighted_total = 0
    available_weight = 0

    # Reweight using only available categories so missing data does not count as zero.
    for category, category_score in category_scores.items():

        if category_score is not None:
            weighted_total += (
                category_score * weights[category]
            )

            available_weight += weights[category]

    if available_weight > 0:
        overall_score = round(
            weighted_total / available_weight,
            1
        )
    else:
        overall_score = None

    if overall_score is None:
        signal = "insufficient_data"

    elif overall_score >= 70:
        signal = "positive"

    elif overall_score >= 40:
        signal = "mixed"

    else:
        signal = "negative"

    data_coverage = round(available_weight, 1)
    return {
        "overall_score": overall_score,
        "signal": signal,
        "data_coverage": data_coverage,
        "categories": category_scores,
        "reasons": reasons
    }


# Keep the rule-based evidence in one stable shape for API clients and the AI layer.
def build_equity_explanation(metrics, score):

    return {
        "ticker": metrics["ticker"],
        "overall_score": score["overall_score"],
        "signal": score["signal"],
        "data_coverage": score["data_coverage"],
        "category_scores": score["categories"],
        "metrics": metrics,
        "key_points": score["reasons"]
    }


def generate_ai_explanation(explanation_data):

    if openai_client is None:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is missing"
        )

    try:
        # Send only the structured scoring evidence; no Plaid account or position data.
        response = openai_client.responses.create(
            model="gpt-5.6-luna",

            instructions="""
You explain a rule-based stock analysis.

Use only the financial data provided to you.
Do not invent company facts, news, or market information.
Explain the company's main strengths and weaknesses.
Mention missing data when it affects the analysis.
Explain what drove the score.
Do not tell the user to buy or sell the stock.
Keep the explanation clear and concise.
""",

            input=json.dumps(explanation_data)
        )

        return response.output_text

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="AI explanation unavailable"
        ) from exc


@app.get("/ai_analysis/{ticker}")
def ai_stock_analysis(ticker: str):

    ticker = ticker.upper()

    metrics = get_clean_metrics(ticker)

    score = score_equity(metrics)

    explanation_data = build_equity_explanation(
        metrics,
        score
    )

    ai_explanation = generate_ai_explanation(
        explanation_data
    )

    return {
        "ticker": ticker,
        "metrics": metrics,
        "score": score,
        "ai_explanation": ai_explanation
    }


@app.get("/portfolio_analysis")
def portfolio_analysis():

    portfolio = get_plaid_portfolio_data()
    analyzed_portfolio = []

    for stock in portfolio:
        ticker = stock["ticker"]
        asset_type = stock["type"]

        # This scoring model applies only to equities; other assets need separate rules.
        if asset_type == "equity" and ticker is not None:
            try:
                metrics = get_clean_metrics(ticker)
                score = score_equity(metrics)
                explanation = build_equity_explanation(metrics, score)

                analysis = {
                    "metrics": metrics,
                    "score": score,
                    "explanation": explanation
                }
            except HTTPException as exc:
                analysis = {
                    "status": "unavailable",
                    "reason": exc.detail
                }
        else:
            analysis = {
                "status": "not_analyzed",
                "reason": f"{asset_type} requires different analysis"
            }

        analyzed_portfolio.append({
            "ticker": ticker,
            "name": stock["name"],
            "type": asset_type,
            "shares": stock["shares"],
            "price": stock["price"],
            "value": stock["value"],
            "analysis": analysis
        })

    return {"portfolio": analyzed_portfolio}

@app.get("/analysis/{ticker}")
def stock_analysis(ticker: str):
    ticker = ticker.upper()
    metrics = get_clean_metrics(ticker)
    score = score_equity(metrics)

    analysis = {
        "metrics": metrics,
        "score": score
    }
    return analysis


@app.get("/metrics/{ticker}")
def stock_metrics(ticker: str):
    return get_stock_metrics(ticker.upper())

#calculate the total value of the portfolio by summing the value of each stock
@app.get("/portfolio")
def get_portfolio():
    portfolio = []
    for ticker, stock in stocks.items():
        value = get_live_price(ticker) * stock["shares"]
        portfolio.append({
            "ticker": ticker,
            "price": get_live_price(ticker),
            "shares": stock["shares"],
            "value": value
        })
    total_value = sum(item["value"] for item in portfolio)
    return {"portfolio": portfolio, "total_value": total_value}
