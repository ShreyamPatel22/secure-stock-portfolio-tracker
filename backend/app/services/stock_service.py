import httpx
from fastapi import HTTPException
from app.core.config import settings

BASE_URL = "https://www.alphavantage.co/query"


async def fetch_quote(ticker: str) -> dict:
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": ticker,
        "apikey": settings.ALPHA_VANTAGE_API_KEY,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    quote = data.get("Global Quote", {})
    if not quote:
        raise HTTPException(status_code=404, detail=f"No data found for '{ticker}'")

    return {
        "ticker": ticker.upper(),
        "price": float(quote.get("05. price", 0)),
        "change": float(quote.get("09. change", 0)),
        "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
        "volume": int(quote.get("06. volume", 0)),
        "latest_trading_day": quote.get("07. latest trading day"),
    }


async def fetch_daily_series(ticker: str, outputsize: str = "compact") -> list[dict]:
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": outputsize,
        "apikey": settings.ALPHA_VANTAGE_API_KEY,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    series = data.get("Time Series (Daily)", {})
    if not series:
        raise HTTPException(status_code=404, detail=f"No time series data for '{ticker}'")

    return [
        {
            "date": date,
            "open": float(v["1. open"]),
            "high": float(v["2. high"]),
            "low": float(v["3. low"]),
            "close": float(v["4. close"]),
            "volume": int(v["5. volume"]),
        }
        for date, v in sorted(series.items())
    ]
