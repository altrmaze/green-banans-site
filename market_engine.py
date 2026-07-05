import asyncio
import logging
import os
import re
from functools import lru_cache

import uvicorn
import yfinance as yf
from crewai import Agent, Crew, Process, Task
from crewai.tools import tool
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
# Set your OpenAI API key as an environment variable before running:
#   export OPENAI_API_KEY="sk-..."
# Then launch the UI with:  streamlit run app.py

# ==========================================
# 2. BACKEND ENGINE (FastAPI Architecture)
# ==========================================
LOGGER = logging.getLogger("greens_market_engine")
MAX_WATCHLIST = 8
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def _get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "")
    if raw_origins.strip():
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return ["http://localhost:8501", "http://127.0.0.1:8501"]


app = FastAPI(title="Greens ACC Market Engine", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=128)
def _fetch_stock_snapshot(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    fast_info = dict(stock.fast_info or {})
    history = stock.history(period="7d", interval="1d", auto_adjust=False)
    closes = history.get("Close")
    close_trend = []
    if closes is not None:
        close_trend = [f"{idx.date()}: {value:.2f}" for idx, value in closes.dropna().tail(7).items()]
    return {
        "current_price": fast_info.get("last_price", "N/A"),
        "fifty_two_week_high": fast_info.get("year_high", "N/A"),
        "close_trend": close_trend,
    }


@tool("Stock Scanner Tool")
def fetch_stock_data(ticker: str) -> str:
    """Fetches high-level historical data and pricing profiles for market analysis."""
    try:
        snapshot = _fetch_stock_snapshot(ticker)
        trend_output = "\n".join(snapshot["close_trend"]) or "No close data available."
        return (
            f"Source Checked: Yahoo Finance Core API\n"
            f"Ticker: {ticker}\n"
            f"Current Price: ${snapshot['current_price']}\n"
            f"52-Week High: ${snapshot['fifty_two_week_high']}\n"
            f"7-Day Close Trend:\n{trend_output}\n"
        )
    except Exception as exc:
        LOGGER.warning("Stock data fetch failed for %s: %s", ticker, exc)
        return f"Error scanning {ticker}: market data currently unavailable."


class MarketScanRequest(BaseModel):
    watch_list: list[str] = Field(min_length=1, max_length=MAX_WATCHLIST)

    @field_validator("watch_list")
    @classmethod
    def normalize_watch_list(cls, tickers: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for ticker in tickers:
            value = ticker.strip().upper()
            if not value:
                continue
            if not TICKER_PATTERN.fullmatch(value):
                raise ValueError(f"Invalid ticker format: {ticker!r}")
            if value not in seen:
                seen.add(value)
                normalized.append(value)
        if not normalized:
            raise ValueError("watch_list must contain at least one valid ticker.")
        return normalized


def _build_market_crew(tickers: str, debug: bool) -> Crew:
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, timeout=90, max_retries=2)
    search_tool = DuckDuckGoSearchRun()

    financial_analyst = Agent(
        role="Senior Technical Financial Analyst",
        goal="Analyze charts, volumes, and mathematical indicators to find explosive setups.",
        backstory="A quantitative Wall Street analyst tracking historical indicators, support lines, and moving averages.",
        verbose=debug,
        llm=llm,
        tools=[fetch_stock_data],
    )

    sentiment_analyst = Agent(
        role="Global Financial News & Media Analyst",
        goal="Scan breaking news, financial magazines (Bloomberg, Reuters, Forbes, WSJ), and economic updates.",
        backstory=(
            "An expert financial media tracker specializing in detecting bullish or bearish "
            "market narratives, press releases, and geopolitical data."
        ),
        verbose=debug,
        llm=llm,
        tools=[search_tool],
    )

    committee_chair = Agent(
        role="Chief Investment Officer (CIO)",
        goal=(
            "Synthesize raw charts and media sentiment into exactly ONE high-probability "
            "recommendation with a full audit log."
        ),
        backstory=(
            "The final gatekeeper. Eliminates all asset noise. Rejects entries with high risk "
            "profiles and gives one definitive pick backed by source transparency."
        ),
        verbose=debug,
        llm=llm,
    )

    task_technical = Task(
        description=f"Analyze data logs and short-term trends for: {tickers}.",
        expected_output="Technical health assessment for the asset pool.",
        agent=financial_analyst,
    )

    task_sentiment = Task(
        description=(
            f"Scan recent financial news and market sentiment for: {tickers}. "
            "Identify bullish or bearish signals from credible financial media sources "
            "such as Bloomberg, Reuters, Forbes, and the Wall Street Journal."
        ),
        expected_output="Sentiment analysis report with bullish/bearish signals for each stock in the watchlist.",
        agent=sentiment_analyst,
    )

    task_committee = Task(
        description=(
            f"Review the technical and sentiment reports for: {tickers}. "
            "Select EXACTLY ONE best stock as your final recommendation. "
            "Provide: Ticker Symbol, Reason for Selection, Risk Level (Low/Medium/High), "
            "Confidence Score (0-100%), and all Data Sources Used."
        ),
        expected_output=(
            "Single best stock pick with full justification, risk level, confidence score, "
            "and a complete audit trail of all sources consulted."
        ),
        agent=committee_chair,
        context=[task_technical, task_sentiment],
    )

    return Crew(
        agents=[financial_analyst, sentiment_analyst, committee_chair],
        tasks=[task_technical, task_sentiment, task_committee],
        process=Process.sequential,
        verbose=debug,
    )


def _run_recommendation(watch_list: list[str]) -> str:
    tickers_string = ", ".join(watch_list)
    debug = os.getenv("MARKET_ENGINE_DEBUG", "false").lower() == "true"
    crew = _build_market_crew(tickers=tickers_string, debug=debug)
    return str(crew.kickoff())


@app.get("/api/v1/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/predict-best-stock")
async def get_single_best_stock(payload: MarketScanRequest) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="Server is missing required AI configuration.")
    try:
        recommendation = await asyncio.to_thread(_run_recommendation, payload.watch_list)
        return {"recommendation": recommendation}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        LOGGER.exception("Market analysis request failed")
        raise HTTPException(
            status_code=502,
            detail="Analysis engine is temporarily unavailable. Please retry.",
        )


# ==========================================
# 3. RUN SERVER (standalone mode)
# ==========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
