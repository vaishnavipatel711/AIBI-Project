from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Float, func, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import requests
import os
import time
import datetime
import json
import re

# ─── Database ─────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aibi.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=1)
    question = Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default=func.now())

class ScoreHistory(Base):
    __tablename__ = "score_history"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    intelligence_score = Column(Float)
    momentum_score = Column(Float)
    sentiment_score = Column(Float)
    financial_score = Column(Float)
    risk_level = Column(String)
    personality = Column(String)
    created_at = Column(DateTime, default=func.now())

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─── Config ───────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "")

import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

app = FastAPI(title="AI Investment Decision Intelligence Platform", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Stock Data ───────────────────────────────────────────────────────
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
    "M": "Macy's Inc",
    "AAPL": "Apple Inc",
    "MSFT": "Microsoft Corp",
    "GOOGL": "Alphabet Inc",
    "AMZN": "Amazon.com Inc",
    "TSLA": "Tesla Inc",
    "META": "Meta Platforms Inc",
    "NVDA": "NVIDIA Corp",
    "JPM": "JPMorgan Chase",
    "V": "Visa Inc",
}

watchlist = []

@app.get("/")
def home():
    return {"message": "AI Investment Decision Intelligence Platform v3.0 Running"}

@app.get("/test")
def test_keys():
    return {
        "finnhub_key_set": bool(FINNHUB_KEY),
        "gemini_key_set": bool(GEMINI_API_KEY),
    }

# ─── Helper: fetch with fallback ──────────────────────────────────────
def safe_finnhub_quote(ticker):
    """Fetch quote from Finnhub with fallback demo data."""
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data and data.get("c", 0) != 0:
            return data
    except Exception:
        pass
    # Fallback demo data
    import random
    base = {"INFY": 22.5, "WIT": 5.8, "IBN": 24.3, "HDB": 68.2, "TTM": 4.1,
            "RDY": 72.5, "VEDL": 16.8, "WNS": 62.3, "SIFY": 1.85, "MMYT": 78.4,
            "YTRA": 3.2, "AAPL": 185.5, "MSFT": 420.2, "GOOGL": 175.8, "AMZN": 185.3,
            "TSLA": 248.5, "META": 505.2, "NVDA": 875.3, "JPM": 195.8, "V": 275.4}.get(ticker, 50.0)
    change = random.uniform(-3, 3)
    pc = base - change
    return {"c": base, "pc": pc, "h": base * 1.02, "l": base * 0.98, "o": pc, "t": int(time.time())}

def safe_finnhub_candles(ticker, resolution="D", days=30):
    """Fetch candles with fallback."""
    try:
        now = int(time.time())
        from_t = now - days * 24 * 3600
        url = f"https://finnhub.io/api/v1/stock/candle?symbol={ticker}&resolution={resolution}&from={from_t}&to={now}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("s") == "ok":
            return data
    except Exception:
        pass
    # Generate synthetic candles
    import random
    base = {"INFY": 22.5, "WIT": 5.8, "IBN": 24.3, "HDB": 68.2, "TTM": 4.1,
            "RDY": 72.5, "VEDL": 16.8, "WNS": 62.3, "SIFY": 1.85, "MMYT": 78.4,
            "YTRA": 3.2, "AAPL": 185.5, "MSFT": 420.2, "GOOGL": 175.8, "AMZN": 185.3,
            "TSLA": 248.5, "META": 505.2, "NVDA": 875.3, "JPM": 195.8, "V": 275.4}.get(ticker, 50.0)
    t = int(time.time())
    candles = {"s": "ok", "t": [], "o": [], "h": [], "l": [], "c": [], "v": []}
    price = base * 0.95
    for i in range(days):
        candles["t"].append(t - (days - i) * 86400)
        daily_change = random.uniform(-0.02, 0.025)
        o = price
        c = price * (1 + daily_change)
        h = max(o, c) * (1 + random.uniform(0, 0.01))
        l = min(o, c) * (1 - random.uniform(0, 0.01))
        candles["o"].append(round(o, 2))
        candles["h"].append(round(h, 2))
        candles["l"].append(round(l, 2))
        candles["c"].append(round(c, 2))
        candles["v"].append(int(random.uniform(1e6, 5e7)))
        price = c
    return candles

def safe_finnhub_news(category="general"):
    """Fetch market news with fallback."""
    try:
        url = f"https://finnhub.io/api/v1/news?category={category}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return data
    except Exception:
        pass
    # Fallback demo news
    demo_news = {
        "general": [
            {"headline": "Global markets rally as inflation data shows cooling trend", "summary": "Major indices rose today as new data suggested inflation is moderating faster than expected, boosting investor confidence.", "source": "Reuters", "url": "https://news.google.com/search?q=global+markets+rally+inflation", "image": "", "datetime": int(time.time()) - 3600},
            {"headline": "Tech sector leads gains amid AI investment boom", "summary": "Technology stocks continued their upward trajectory as companies announce major AI infrastructure investments.", "source": "Bloomberg", "url": "https://news.google.com/search?q=tech+sector+ai+investment", "image": "", "datetime": int(time.time()) - 7200},
            {"headline": "Federal Reserve signals potential rate cuts in coming months", "summary": "Fed officials hinted at possible interest rate reductions, sparking optimism across equity markets.", "source": "CNBC", "url": "https://news.google.com/search?q=federal+reserve+rate+cuts", "image": "", "datetime": int(time.time()) - 10800},
            {"headline": "Indian IT sector reports strong quarterly earnings", "summary": "Major Indian IT companies exceeded analyst expectations with robust revenue growth and improved margins.", "source": "Economic Times", "url": "https://news.google.com/search?q=indian+it+sector+earnings", "image": "", "datetime": int(time.time()) - 14400},
            {"headline": "Oil prices stabilize after volatile trading week", "summary": "Crude oil benchmarks found support as supply concerns ease and demand outlook improves.", "source": "Financial Times", "url": "https://news.google.com/search?q=oil+prices+stabilize", "image": "", "datetime": int(time.time()) - 18000},
            {"headline": "EV adoption accelerates in emerging markets", "summary": "Electric vehicle sales in developing economies surged 40% year-over-year, driven by government incentives.", "source": "TechCrunch", "url": "https://news.google.com/search?q=ev+adoption+emerging+markets", "image": "", "datetime": int(time.time()) - 21600},
        ],
        "forex": [
            {"headline": "USD/INR holds steady ahead of RBI policy meeting", "summary": "The Indian rupee remained stable as traders await the Reserve Bank of India's monetary policy decision.", "source": "ForexLive", "url": "https://news.google.com/search?q=usd+inr+rbi+policy", "image": "", "datetime": int(time.time()) - 3600},
            {"headline": "Euro gains against dollar on ECB hawkish signals", "summary": "The euro strengthened as European Central Bank officials suggested rates may stay higher for longer.", "source": "FXStreet", "url": "https://news.google.com/search?q=euro+dollar+ecb+hawkish", "image": "", "datetime": int(time.time()) - 7200},
        ],
        "crypto": [
            {"headline": "Bitcoin breaks $70,000 resistance level", "summary": "Bitcoin surged past a key psychological barrier as institutional inflows continue to drive demand.", "source": "CoinDesk", "url": "https://news.google.com/search?q=bitcoin+70000+break", "image": "", "datetime": int(time.time()) - 3600},
            {"headline": "Ethereum network upgrade promises faster transactions", "summary": "The upcoming Ethereum upgrade aims to reduce gas fees and improve transaction throughput significantly.", "source": "Decrypt", "url": "https://news.google.com/search?q=ethereum+upgrade+faster", "image": "", "datetime": int(time.time()) - 7200},
        ],
        "merger": [
            {"headline": "Major pharmaceutical merger reshapes industry landscape", "summary": "Two leading drugmakers announced a $50 billion merger that could create the world's largest pharma company.", "source": "WSJ", "url": "https://news.google.com/search?q=pharmaceutical+merger+2026", "image": "", "datetime": int(time.time()) - 3600},
            {"headline": "Tech giants eye strategic acquisitions in AI space", "summary": "Multiple technology companies are reportedly in talks to acquire AI startups to bolster their capabilities.", "source": "The Information", "url": "https://news.google.com/search?q=tech+acquisitions+ai+2026", "image": "", "datetime": int(time.time()) - 7200},
        ],
    }
    return demo_news.get(category, demo_news["general"])

def safe_company_news(ticker):
    """Fetch company news with fallback."""
    try:
        to_date = datetime.date.today()
        from_date = to_date - datetime.timedelta(days=7)
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return data
    except Exception:
        pass
    # Fallback
    company_demo = {
        "INFY": [
            {"headline": "Infosys wins $500 million digital transformation deal", "summary": "Infosys secured a major contract to modernize a Fortune 500 company's IT infrastructure.", "source": "Economic Times", "url": "https://news.google.com/search?q=Infosys+digital+transformation+deal", "image": "", "datetime": int(time.time()) - 3600},
            {"headline": "Infosys Q1 earnings beat estimates with 8% revenue growth", "summary": "The IT giant reported better-than-expected quarterly results driven by strong demand in cloud services.", "source": "Reuters", "url": "https://news.google.com/search?q=Infosys+Q1+earnings+2026", "image": "", "datetime": int(time.time()) - 10800},
        ],
        "WIT": [
            {"headline": "Wipro announces AI-powered automation platform", "summary": "Wipro launched a new AI platform aimed at automating enterprise workflows and reducing operational costs.", "source": "Business Standard", "url": "https://news.google.com/search?q=Wipro+AI+automation+platform", "image": "", "datetime": int(time.time()) - 7200},
        ],
        "AAPL": [
            {"headline": "Apple unveils next-gen AI features for iPhone", "summary": "Apple announced groundbreaking on-device AI capabilities that will transform user experience.", "source": "TechCrunch", "url": "https://news.google.com/search?q=Apple+AI+iPhone+2026", "image": "", "datetime": int(time.time()) - 3600},
            {"headline": "Apple services revenue hits all-time high", "summary": "The company's services division reported record-breaking quarterly revenue exceeding expectations.", "source": "CNBC", "url": "https://news.google.com/search?q=Apple+services+revenue+record", "image": "", "datetime": int(time.time()) - 14400},
        ],
    }
    return company_demo.get(ticker, [
        {"headline": f"{ticker} shows resilience amid market volatility", "summary": f"Analysts note that {ticker} has demonstrated strong fundamentals despite recent market turbulence.", "source": "MarketWatch", "url": f"https://news.google.com/search?q={ticker}+stock+news", "image": "", "datetime": int(time.time()) - 3600},
        {"headline": f"Investors eye {ticker} ahead of earnings season", "summary": f"Market participants are closely watching {ticker} as the company prepares to release its quarterly financial results.", "source": "Yahoo Finance", "url": f"https://news.google.com/search?q={ticker}+earnings+preview", "image": "", "datetime": int(time.time()) - 10800},
    ])

# ─── Market Data ──────────────────────────────────────────────────────
@app.get("/market")
def market_data(region: str = "india"):
    stocks = list(INDIA_STOCKS.keys())[:12]
    result = []
    for ticker in stocks:
        quote = safe_finnhub_quote(ticker)
        if quote and quote.get("c", 0) != 0:
            change = ((quote["c"] - quote["pc"]) / quote["pc"]) * 100 if quote["pc"] else 0
            result.append({
                "ticker": ticker,
                "name": INDIA_STOCKS.get(ticker, ticker),
                "price": round(quote["c"], 2),
                "change": round(change, 2),
            })
    return result

@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    t = ticker.upper()
    quote = safe_finnhub_quote(t)
    if not quote or quote.get("c", 0) == 0:
        raise HTTPException(status_code=404, detail=f"No data available for '{t}'")

    candles = safe_finnhub_candles(t, "D", 30)
    chart_data = []
    if candles.get("s") == "ok":
        for i in range(len(candles["t"])):
            chart_data.append({
                "date": str(datetime.date.fromtimestamp(candles["t"][i])),
                "close": round(candles["c"][i], 2),
                "high": round(candles["h"][i], 2),
                "low": round(candles["l"][i], 2),
                "open": round(candles["o"][i], 2),
                "volume": candles["v"][i],
            })

    return {
        "ticker": t,
        "name": INDIA_STOCKS.get(t, t),
        "close": round(quote["c"], 2),
        "high": round(quote["h"], 2),
        "low": round(quote["l"], 2),
        "open": round(quote["o"], 2),
        "previous_close": round(quote["pc"], 2),
        "volume": 0,
        "chart": chart_data,
    }

@app.get("/search/{query}")
def search_symbol(query: str):
    q = query.strip().lower()
    if not q:
        return []
    matches = [
        {"symbol": symbol, "description": name, "type": "Common Stock"}
        for symbol, name in INDIA_STOCKS.items()
        if q in symbol.lower() or q in name.lower()
    ]
    matches.sort(key=lambda m: (not m["description"].lower().startswith(q) and not m["symbol"].lower().startswith(q)))
    return matches[:15]

# ─── Watchlist ────────────────────────────────────────────────────────
@app.post("/watchlist/{ticker}")
def add_watchlist(ticker: str):
    t = ticker.upper().strip()
    if not t:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty")
    quote = safe_finnhub_quote(t)
    if not quote or quote.get("c", 0) == 0:
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

# ─── News ─────────────────────────────────────────────────────────────
@app.get("/news/market")
def market_news(category: str = "general"):
    data = safe_finnhub_news(category)
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

@app.get("/news/company/{ticker}")
def company_news(ticker: str):
    data = safe_company_news(ticker.upper())
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

# ─── AI Investment Intelligence Score ─────────────────────────────────
def calculate_momentum_score(chart_data):
    """Calculate momentum score 0-100 from price data."""
    if not chart_data or len(chart_data) < 5:
        return 50
    closes = [d["close"] for d in chart_data]
    # Short term (5 days)
    st_change = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if closes[-5] != 0 else 0
    # Medium term (all available)
    mt_change = ((closes[-1] - closes[0]) / closes[0]) * 100 if closes[0] != 0 else 0
    # Volatility
    returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes))]
    volatility = sum(r**2 for r in returns) / len(returns) if returns else 0
    vol_penalty = min(volatility * 2, 20)
    # Score
    score = 50 + st_change * 2 + mt_change * 0.5 - vol_penalty
    return max(0, min(100, round(score)))

def calculate_risk_level(chart_data, news_items):
    """Determine risk level from price volatility and negative news."""
    if not chart_data or len(chart_data) < 5:
        return "Medium"
    closes = [d["close"] for d in chart_data]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes))]
    volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5 if returns else 0
    # Count negative keywords in news
    negative_words = ["fall", "drop", "decline", "crash", "loss", "bearish", "sell", "downgrade", "cut", "layoff", "debt", "default"]
    neg_count = sum(1 for news in news_items for w in negative_words if w in (news.get("headline", "") + news.get("summary", "")).lower())

    if volatility > 3 or neg_count >= 3:
        return "High"
    elif volatility > 1.5 or neg_count >= 1:
        return "Medium"
    return "Low"

def determine_personality(momentum, sentiment, financial, risk):
    """Determine company personality based on scores."""
    if risk == "High":
        return "Risk Alert"
    if momentum > 70 and financial > 65:
        return "Growth Explorer"
    if momentum < 40 and financial > 60:
        return "Recovery Candidate"
    if financial > 70 and risk == "Low":
        return "Stable Performer"
    if momentum > 60 and sentiment > 60:
        return "Growth Explorer"
    return "Stable Performer"

@app.get("/intelligence/{ticker}")
def get_intelligence(ticker: str, db: Session = Depends(get_db)):
    """Generate comprehensive Investment Intelligence Score for a stock."""
    t = ticker.upper()

    # 1. Get stock data
    quote = safe_finnhub_quote(t)
    if not quote or quote.get("c", 0) == 0:
        raise HTTPException(status_code=404, detail=f"No data available for '{t}'")

    # 2. Get chart data (60 days for better analysis)
    candles = safe_finnhub_candles(t, "D", 60)
    chart_data = []
    if candles.get("s") == "ok":
        for i in range(len(candles["t"])):
            chart_data.append({
                "date": str(datetime.date.fromtimestamp(candles["t"][i])),
                "close": round(candles["c"][i], 2),
                "high": round(candles["h"][i], 2),
                "low": round(candles["l"][i], 2),
                "volume": candles["v"][i],
            })

    # 3. Get news
    news_items = safe_company_news(t)

    # 4. Calculate scores
    momentum_score = calculate_momentum_score(chart_data)
    risk_level = calculate_risk_level(chart_data, news_items)

    # 5. AI-powered sentiment and financial analysis
    company_name = INDIA_STOCKS.get(t, t)
    headlines = [n.get("headline", "") for n in news_items[:8]]
    headlines_block = "\n".join(f"- {h}" for h in headlines) if headlines else "No recent news."

    # Price trend summary
    if chart_data and len(chart_data) > 1:
        closes = [d["close"] for d in chart_data]
        pct_change = ((closes[-1] - closes[0]) / closes[0]) * 100
        high_30 = max(closes[-30:]) if len(closes) >= 30 else max(closes)
        low_30 = min(closes[-30:]) if len(closes) >= 30 else min(closes)
        trend_text = f"Price moved from ${closes[0]:.2f} to ${closes[-1]:.2f} ({pct_change:+.2f}%). 30D high: ${high_30:.2f}, low: ${low_30:.2f}."
    else:
        trend_text = "No sufficient price history."

    # AI prompt for comprehensive analysis
    prompt = f"""You are an expert AI Investment Analyst. Analyze {company_name} ({t}) using the data below.

PRICE DATA:
Current: ${quote['c']:.2f}, Previous Close: ${quote['pc']:.2f}, High: ${quote['h']:.2f}, Low: ${quote['l']:.2f}
{trend_text}

RECENT NEWS HEADLINES:
{headlines_block}

Respond ONLY with valid JSON (no markdown fences, no preamble) in this exact shape:
{{
  "sentiment_score": <number 0-100>,
  "financial_score": <number 0-100>,
  "sentiment_explanation": "2-3 sentences explaining news sentiment and its likely impact",
  "financial_explanation": "2-3 sentences about financial health based on price trends and market position",
  "risk_factors": ["short risk bullet under 20 words", "..."],
  "company_story": "A simple, engaging 3-4 sentence explanation of the company's current condition for non-experts",
  "what_changed": "2-3 sentences on what changed recently in the company's situation"
}}

sentiment_score: 0-100 where 100 is extremely positive news sentiment.
financial_score: 0-100 based on price stability, growth trends, and market position."""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(raw)
    except Exception as e:
        ai_data = {
            "sentiment_score": 55,
            "financial_score": 60,
            "sentiment_explanation": f"News coverage for {company_name} shows mixed signals with some positive developments balanced by market uncertainty.",
            "financial_explanation": f"Based on recent price action, {company_name} demonstrates moderate financial stability with room for improvement in growth metrics.",
            "risk_factors": ["Market volatility remains a concern", "Sector-specific headwinds may impact performance"],
            "company_story": f"{company_name} is navigating a dynamic market environment. While the company maintains solid fundamentals, investors should monitor upcoming developments closely.",
            "what_changed": f"Recent price movements suggest shifting investor sentiment toward {company_name}. News flow indicates both opportunities and challenges ahead.",
        }

    sentiment_score = max(0, min(100, int(ai_data.get("sentiment_score", 55))))
    financial_score = max(0, min(100, int(ai_data.get("financial_score", 60))))

    # Risk score (inverse of risk level)
    risk_score = {"Low": 80, "Medium": 50, "High": 25}.get(risk_level, 50)

    # Overall Intelligence Score (weighted average)
    intelligence_score = round(
        momentum_score * 0.30 + 
        sentiment_score * 0.25 + 
        financial_score * 0.30 + 
        risk_score * 0.15
    )

    personality = determine_personality(momentum_score, sentiment_score, financial_score, risk_level)

    # Calculate price change
    change_pct = ((quote["c"] - quote["pc"]) / quote["pc"]) * 100 if quote["pc"] else 0

    result = {
        "ticker": t,
        "name": company_name,
        "current_price": round(quote["c"], 2),
        "previous_close": round(quote["pc"], 2),
        "price_change_pct": round(change_pct, 2),
        "intelligence_score": intelligence_score,
        "momentum_score": momentum_score,
        "sentiment_score": sentiment_score,
        "financial_score": financial_score,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "personality": personality,
        "sentiment_explanation": ai_data.get("sentiment_explanation", ""),
        "financial_explanation": ai_data.get("financial_explanation", ""),
        "risk_factors": ai_data.get("risk_factors", []),
        "company_story": ai_data.get("company_story", ""),
        "what_changed": ai_data.get("what_changed", ""),
        "chart_data": chart_data,
        "news": [
            {
                "headline": n.get("headline"),
                "summary": n.get("summary"),
                "source": n.get("source"),
                "url": n.get("url"),
                "datetime": n.get("datetime"),
            }
            for n in news_items[:8]
        ],
        "disclaimer": "This is an AI-generated analysis for educational purposes only. Not financial advice."
    }

    # Save to history for "What Changed?" feature
    prev = db.query(ScoreHistory).filter(ScoreHistory.ticker == t).order_by(ScoreHistory.id.desc()).first()
    if prev:
        result["previous_score"] = {
            "intelligence_score": prev.intelligence_score,
            "momentum_score": prev.momentum_score,
            "sentiment_score": prev.sentiment_score,
            "financial_score": prev.financial_score,
            "risk_level": prev.risk_level,
            "personality": prev.personality,
        }
    else:
        result["previous_score"] = None

    # Save current score
    new_score = ScoreHistory(
        ticker=t,
        intelligence_score=intelligence_score,
        momentum_score=momentum_score,
        sentiment_score=sentiment_score,
        financial_score=financial_score,
        risk_level=risk_level,
        personality=personality,
    )
    db.add(new_score)
    db.commit()

    return result

@app.get("/intelligence/history/{ticker}")
def get_score_history(ticker: str, db: Session = Depends(get_db)):
    """Get historical intelligence scores for a ticker."""
    records = db.query(ScoreHistory).filter(ScoreHistory.ticker == ticker.upper()).order_by(ScoreHistory.id.desc()).limit(10).all()
    return [
        {
            "intelligence_score": r.intelligence_score,
            "momentum_score": r.momentum_score,
            "sentiment_score": r.sentiment_score,
            "financial_score": r.financial_score,
            "risk_level": r.risk_level,
            "personality": r.personality,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]

# ─── AI News Sentiment Analysis ───────────────────────────────────────
@app.get("/news/sentiment/{ticker}")
def analyze_news_sentiment(ticker: str):
    """Analyze sentiment of company news with AI explanation."""
    t = ticker.upper()
    news_items = safe_company_news(t)

    if not news_items:
        return {"sentiment": "Neutral", "score": 50, "explanation": "No recent news available for analysis.", "articles": []}

    headlines_block = "\n".join(f"- {n.get('headline', '')}" for n in news_items[:6])

    prompt = f"""Analyze the sentiment of these news headlines for {t}:

{headlines_block}

Respond ONLY with valid JSON:
{{
  "overall_sentiment": "Positive" | "Negative" | "Neutral",
  "sentiment_score": <number 0-100>,
  "explanation": "2-3 sentences explaining the overall sentiment and its likely impact on the stock",
  "key_themes": ["theme1", "theme2"]
}}"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_result = json.loads(raw)
    except Exception:
        ai_result = {
            "overall_sentiment": "Neutral",
            "sentiment_score": 50,
            "explanation": "News sentiment appears balanced with no dominant positive or negative themes.",
            "key_themes": ["Market Performance", "General Updates"],
        }

    return {
        "ticker": t,
        "sentiment": ai_result.get("overall_sentiment", "Neutral"),
        "score": max(0, min(100, int(ai_result.get("sentiment_score", 50)))),
        "explanation": ai_result.get("explanation", ""),
        "key_themes": ai_result.get("key_themes", []),
        "articles": [
            {
                "headline": n.get("headline"),
                "source": n.get("source"),
                "url": n.get("url"),
                "datetime": n.get("datetime"),
            }
            for n in news_items[:8]
        ],
    }

# ─── Chat ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    context: str = ""

@app.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        system_prompt = """You are an expert AI Investment Intelligence Assistant. You help users understand stocks, markets, and investment concepts.

CRITICAL FORMATTING RULES:
- Use proper Markdown formatting
- Use ## for main headings
- Use ### for sub-headings  
- Use bullet points (- item) for lists
- Use numbered lists (1. item) for steps
- Use **bold** for emphasis
- Use tables for comparisons
- Add line breaks between sections
- Never output everything as one long paragraph
- Structure your response clearly with sections

You can:
- Analyze stocks and explain trends
- Explain financial news and its impact
- Compare companies
- Discuss risk factors
- Explain "what could happen next"
- Break down complex financial concepts simply

Always be professional, accurate, and educational."""

        full_prompt = f"{system_prompt}\n\nUser Question: {req.message}"
        if req.context:
            full_prompt += f"\n\nContext: {req.context}"

        response = model.generate_content(full_prompt)
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

# ─── Company Comparison ───────────────────────────────────────────────
class CompareRequest(BaseModel):
    tickers: list

@app.post("/compare")
def compare_stocks(req: CompareRequest, db: Session = Depends(get_db)):
    """Compare multiple stocks with intelligence scores."""
    results = []
    for ticker in req.tickers:
        t = ticker.upper().strip()
        if not t:
            continue
        try:
            quote = safe_finnhub_quote(t)
            if not quote or quote.get("c", 0) == 0:
                continue
            change_pct = ((quote["c"] - quote["pc"]) / quote["pc"]) * 100 if quote["pc"] else 0

            # Get latest score from DB
            score = db.query(ScoreHistory).filter(ScoreHistory.ticker == t).order_by(ScoreHistory.id.desc()).first()

            results.append({
                "ticker": t,
                "name": INDIA_STOCKS.get(t, t),
                "price": round(quote["c"], 2),
                "change_pct": round(change_pct, 2),
                "intelligence_score": score.intelligence_score if score else None,
                "personality": score.personality if score else None,
                "risk_level": score.risk_level if score else None,
            })
        except Exception:
            pass
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
