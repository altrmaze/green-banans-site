# Greens ACC Market Intelligence

This repository provides a Streamlit frontend and FastAPI backend for AI-assisted stock watchlist analysis.

## Stack

- Frontend: Streamlit (`/app.py`)
- Backend API: FastAPI + CrewAI (`/market_engine.py`)
- Data source: Yahoo Finance (`yfinance`)

## Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set required environment variables:

```bash
export OPENAI_API_KEY="your-key"
```

Optional:

```bash
export BACKEND_URL="http://127.0.0.1:8000"
export ALLOWED_ORIGINS="http://localhost:8501,http://127.0.0.1:8501"
```

3. Start the app:

```bash
streamlit run app.py
```

## API endpoints

- `GET /api/v1/health`
- `POST /api/v1/predict-best-stock`

Request body:

```json
{
  "watch_list": ["AAPL", "MSFT", "NVDA"]
}
```

Constraints:

- 1 to 8 tickers per request
- ticker format: uppercase letters, numbers, dot, and dash
