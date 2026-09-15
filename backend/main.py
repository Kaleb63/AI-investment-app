from fastapi import FastAPI
import os
import httpx
import plaid

from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
api_key = os.getenv("FINNHUB_API_KEY")
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

#get live stock price from finnhub api
def get_live_price(ticker: str):
    url = "https://finnhub.io/api/v1/quote"
    #make a request to the finnhub api to get the current price of the stock
    response = httpx.get(
        url,
        params={
            "symbol": ticker,
            "token": api_key
        }
    )
    data = response.json()
    return data["c"] #return current price


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