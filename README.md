# AIBI — AI Business Intelligence Platform

A full-stack web app with real-time stock data, Gemini AI chat, CSV data analysis, and a live dashboard.

---

## 📁 Project Structure

```
aibi-app/
├── backend/           ← FastAPI Python server
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── requirements.txt
│   ├── Procfile
│   └── .env.example
└── frontend/
    └── index.html     ← Single-file frontend (no build needed)
```

---

## ⚙️ Local Setup

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Create your .env file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

uvicorn main:app --reload
# Backend runs at http://localhost:8000
```

### 2. Frontend

Just open `frontend/index.html` in your browser.  
Make sure the `API` variable at the top of the `<script>` points to `http://localhost:8000`.

---

## 🚀 Deploy to the Internet (Free)

### BACKEND → Render.com (Free Tier)

1. Push your `backend/` folder to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables:
   - `GEMINI_API_KEY` = your key
6. Click Deploy → you get a URL like `https://aibi-api.onrender.com`

### FRONTEND → Netlify (Free)

1. Go to https://netlify.com → Drop your `frontend/` folder on the deploy zone
2. **Before deploying**, edit `frontend/index.html`:
   - Find `const API = "http://localhost:8000";`
   - Replace with your Render URL: `const API = "https://aibi-api.onrender.com";`
3. Your site goes live at `https://yoursite.netlify.app`

### Optional: Custom Domain

- Buy a `.com` domain on Namecheap (~$10/year)
- Point it to Netlify in Netlify's domain settings

---

## 🔑 Getting Your Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy it into your `.env` file as `GEMINI_API_KEY=your_key_here`

---

## 📦 Tech Stack

| Layer     | Technology               |
|-----------|--------------------------|
| Backend   | FastAPI + Python         |
| AI        | Google Gemini 2.5 Flash  |
| Stock Data| yfinance                 |
| Database  | SQLite (SQLAlchemy)      |
| Frontend  | HTML + CSS + Chart.js    |
| Deploy    | Render (backend) + Netlify (frontend) |

---

## 🌟 Features

- 📈 **Live Market Overview** — AAPL, MSFT, NVDA, TSLA, GOOGL, AMZN prices & % change
- 🔍 **Stock Search** — Any ticker worldwide (e.g. RELIANCE.NS for Indian stocks)
- ⭐ **Watchlist** — Save and track your favourite stocks
- 🤖 **AI Chat** — Ask any financial/business question, powered by Gemini
- 📊 **Data Analysis** — Upload CSV → auto-clean, visualize, and get AI insights
- 🕘 **Chat History** — View and clear all past AI conversations
