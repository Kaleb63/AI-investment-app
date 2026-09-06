from fastapi import FastAPI

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