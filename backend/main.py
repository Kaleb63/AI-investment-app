from fastapi import FastAPI
import os
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
api_key = os.getenv("FINNHUB_API_KEY")
app = FastAPI()

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

get_stock("AAPL")
#calculate the total value of the portfolio by summing the value of each stock
@app.get("/portfolio")
def get_portfolio():
portfolio = []
for ticker, stock in stocks:
    value = get_live_price(ticker) * stock["shares"]
    portfolio.append({
        "ticker": ticker,
        "price": get_live_price(ticker),
        "shares": stock["shares"],
        "value": value
    })