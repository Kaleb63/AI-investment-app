from fastapi import FastAPI
import os
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
api_key = os.getenv("FINNHUB_API_KEY")
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Investment app backend is running"}

stocks = {
    "AAPL": {"price": 200, "shares": 5},
    "NVDA": {"price": 180, "shares": 2},
    "TSLA": {"price": 700, "shares": 3}
}

@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    return {
        "ticker": ticker,
        "price": stocks[ticker]["price"],
        "shares": stocks[ticker]["shares"]
    }
get_stock("NVDA")

def get_live_price(ticker: str):
    url = "https://finnhub.io/api/v1/quote"

    response = httpx.get(
        url,
        params={
            "symbol": ticker,
            "token": api_key
        }
    )
    data = response.json()
    return data["c"]

print(get_live_price("NVDA"))
