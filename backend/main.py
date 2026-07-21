from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests
import os

from database import engine, SessionLocal, get_db
from models import Base, ChatHistory
import google.generativeai as genai

Base.metadata.create_all(bind=engine)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

app = FastAPI(title="AI Business Intelligence API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "AI Business Intelligence API v2.0 Running"}
@app.get("/test")
def test_keys():
    return {
        "finnhub_key_set": bool(FINNHUB_KEY),
        "gemini_key_set": bool(GEMINI_API_KEY),
        "finnhub_key_preview": FINNHUB_KEY[:5] if FINNHUB_KEY else "NOT SET"
    }

INDIA_STOCKS = {
    "INFY": "Infosys Ltd",
    "WIT": "Wipro Ltd",
    "IBN": "ICICI Bank Ltd",
    "HDB": "HDFC Bank Ltd",
    "TTM": "Tata Motors Ltd",
    "RDY": "Dr. Reddy's Laboratories",
    "VEDL": "Vedanta Ltd",
    "WNS": "WNS Global Services",
    "SIFY": "Sify Technologies Ltd",
    "MMYT": "MakeMyTrip Ltd",
    "YTRA": "Yatra Online Inc",
}

@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    try:
        t = ticker.upper()
        # Get quote
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB_KEY}"
        quote = requests.get(quote_url, timeout=10).json()

        if not quote or quote.get("c", 0) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"'{t}' has no available quote data. If this is an NSE/BSE-listed "
                       f"symbol (ending in .NS or .BO), our Finnhub plan doesn't support Indian "
                       f"exchange data directly — try the US-listed ADR instead (e.g. INFY, WIT, IBN).",
            )

        # Get candles for chart (last 30 days)
        import time
        now = int(time.time())
        month_ago = now - 30 * 24 * 3600
        candle_url = f"https://finnhub.io/api/v1/stock/candle?symbol={t}&resolution=D&from={month_ago}&to={now}&token={FINNHUB_KEY}"
        candles = requests.get(candle_url, timeout=10).json()

        chart_data = []
        if candles.get("s") == "ok":
            import datetime
            for i in range(len(candles["t"])):
                chart_data.append({
                    "date": str(datetime.date.fromtimestamp(candles["t"][i])),
                    "close": round(candles["c"][i], 2)
                })

        return {
            "ticker": t,
            "name": INDIA_STOCKS.get(t, t),
            "close": round(quote["c"], 2),
            "high": round(quote["h"], 2),
            "low": round(quote["l"], 2),
            "volume": 0,
            "chart": chart_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

MARKET_REGIONS = {
    "india": list(INDIA_STOCKS.keys()),
}

@app.get("/market")
def market_data(region: str = "india"):
    stocks = MARKET_REGIONS.get(region, MARKET_REGIONS["india"])
    result = []
    for ticker in stocks:
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
            quote = requests.get(url, timeout=10).json()
            if quote and quote.get("c", 0) != 0:
                change = ((quote["c"] - quote["pc"]) / quote["pc"]) * 100
                result.append({
                    "ticker": ticker,
                    "name": INDIA_STOCKS.get(ticker, ticker),
                    "price": round(quote["c"], 2),
                    "change": round(change, 2),
                })
        except:
            pass
    return result

@app.get("/search/{query}")
def search_symbol(query: str):
    """Search Indian companies (by name or ticker) from our supported ADR list."""
    q = query.strip().lower()
    if not q:
        return []
    matches = [
        {"symbol": symbol, "description": name, "type": "Common Stock"}
        for symbol, name in INDIA_STOCKS.items()
        if q in symbol.lower() or q in name.lower()
    ]
    # prioritize matches where the query is a prefix
    matches.sort(key=lambda m: (not m["description"].lower().startswith(q) and not m["symbol"].lower().startswith(q)))
    return matches[:15]

def _is_valid_ticker(ticker: str) -> bool:
    """Check a ticker actually resolves to a real quote before we let it touch the watchlist."""
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
        quote = requests.get(url, timeout=8).json()
        return bool(quote) and any(quote.get(k, 0) not in (0, None) for k in ("c", "h", "l", "o", "pc"))
    except Exception:
        return False

watchlist = []

@app.post("/watchlist/{ticker}")
def add_watchlist(ticker: str):
    t = ticker.upper().strip()
    if not t:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty")
    if not _is_valid_ticker(t):
        raise HTTPException(status_code=404, detail=f"'{t}' is not a recognized stock ticker")
    if t not in watchlist:
        watchlist.append(t)
    return {"message": "Added", "ticker": t}

@app.get("/watchlist")
def get_watchlist():
    return watchlist

@app.delete("/watchlist/{ticker}")
def remove_watchlist(ticker: str):
    t = ticker.upper()
    if t in watchlist:
        watchlist.remove(t)
    return {"message": "Removed", "ticker": t}

@app.get("/news/market")
def market_news(category: str = "general"):
    """General financial news feed. category: general | forex | crypto | merger"""
    try:
        url = f"https://finnhub.io/api/v1/news?category={category}&token={FINNHUB_KEY}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if not isinstance(data, list):
            raise HTTPException(
                status_code=502,
                detail=f"Finnhub news request failed (status {resp.status_code}): {data}",
            )
        return [
            {
                "headline": a.get("headline"),
                "summary": a.get("summary"),
                "source": a.get("source"),
                "url": a.get("url"),
                "image": a.get("image"),
                "datetime": a.get("datetime"),
            }
            for a in data[:24]
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/company/{ticker}")
def company_news(ticker: str):
    """News for a specific ticker over the last 7 days."""
    try:
        import datetime
        to_date = datetime.date.today()
        from_date = to_date - datetime.timedelta(days=7)
        url = (
            f"https://finnhub.io/api/v1/company-news?symbol={ticker.upper()}"
            f"&from={from_date}&to={to_date}&token={FINNHUB_KEY}"
        )
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if not isinstance(data, list):
            raise HTTPException(
                status_code=502,
                detail=f"Finnhub company-news request failed (status {resp.status_code}): {data}",
            )
        return [
            {
                "headline": a.get("headline"),
                "summary": a.get("summary"),
                "source": a.get("source"),
                "url": a.get("url"),
                "image": a.get("image"),
                "datetime": a.get("datetime"),
            }
            for a in data[:15]
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str

@app.get("/analysis/{ticker}")
def stock_analysis(ticker: str):
    """AI-generated investment insight combining price trend + recent news for one stock."""
    t = ticker.upper()
    try:
        # 1. Quote + trend
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB_KEY}"
        quote = requests.get(quote_url, timeout=10).json()
        if not quote or quote.get("c", 0) == 0:
            raise HTTPException(status_code=404, detail=f"No data available for '{t}'")

        import time, datetime
        now = int(time.time())
        month_ago = now - 30 * 24 * 3600
        candle_url = f"https://finnhub.io/api/v1/stock/candle?symbol={t}&resolution=D&from={month_ago}&to={now}&token={FINNHUB_KEY}"
        candles = requests.get(candle_url, timeout=10).json()

        trend_line = "No 30-day history available."
        if candles.get("s") == "ok" and len(candles.get("c", [])) > 1:
            closes = candles["c"]
            pct_change = ((closes[-1] - closes[0]) / closes[0]) * 100
            high30, low30 = max(closes), min(closes)
            trend_line = (
                f"Over the last 30 trading days, {t} moved from ${closes[0]:.2f} to "
                f"${closes[-1]:.2f} ({pct_change:+.2f}%). 30-day high: ${high30:.2f}, low: ${low30:.2f}."
            )

        # 2. Recent news (last 7 days)
        to_date = datetime.date.today()
        from_date = to_date - datetime.timedelta(days=7)
        news_url = (
            f"https://finnhub.io/api/v1/company-news?symbol={t}&from={from_date}&to={to_date}&token={FINNHUB_KEY}"
        )
        news_data = requests.get(news_url, timeout=10).json()
        headlines = []
        if isinstance(news_data, list):
            headlines = [a.get("headline", "") for a in news_data[:8] if a.get("headline")]
        headlines_block = "\n".join(f"- {h}" for h in headlines) if headlines else "No recent news found."

        company_name = INDIA_STOCKS.get(t, t)

        prompt = f"""You are an AI financial analyst. Analyze {company_name} ({t}) using ONLY the data below.

PRICE DATA:
{trend_line}
Current price: ${quote['c']:.2f}, Today's high: ${quote['h']:.2f}, Today's low: ${quote['l']:.2f}, Previous close: ${quote['pc']:.2f}

RECENT NEWS HEADLINES (last 7 days):
{headlines_block}

Respond ONLY with valid JSON (no markdown fences, no preamble) in this exact shape:
{{
  "trend_summary": "2-3 sentence plain-language summary of the price movement",
  "news_drivers": ["short bullet point tying a specific headline to the stock's story", "..."],
  "risk_factors": ["short bullet point on a risk or uncertainty worth watching", "..."],
  "sentiment": "bullish" | "neutral" | "bearish"
}}
Base news_drivers strictly on the headlines given; if there is no relevant news, return an empty array. Keep each bullet under 20 words."""

        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        import json
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {
                "trend_summary": raw[:400],
                "news_drivers": [],
                "risk_factors": [],
                "sentiment": "neutral",
            }

        parsed["ticker"] = t
        parsed["name"] = company_name
        parsed["disclaimer"] = "This is an AI-generated summary for educational purposes only, not financial advice."
        return parsed

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        prompt = f"""
You are an expert AI Financial and Business Intelligence Assistant.
Answer clearly, professionally, and concisely.

User Question: {req.message}
"""
        response = model.generate_content(prompt)
        reply = response.text
        new_chat = ChatHistory(user_id=1, question=req.message, answer=reply)
        db.add(new_chat)
        db.commit()
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    chats = db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(50).all()
    return [{"question": c.question, "answer": c.answer} for c in chats]

@app.delete("/history")
def clear_history(db: Session = Depends(get_db)):
    db.query(ChatHistory).delete()
    db.commit()
    return {"message": "History cleared"}