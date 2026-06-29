import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crewai import Agent, Crew, Process, Task
from crewai.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
import yfinance as yf

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
# Set your OpenAI API key as an environment variable before running:
#   export OPENAI_API_KEY="sk-..."
# Then launch the UI with:  streamlit run app.py

# ==========================================
# 2. BACKEND ENGINE (FastAPI Architecture)
# ==========================================
app = FastAPI(title="Greens ACC Market Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@tool("Stock Scanner Tool")
def fetch_stock_data(ticker: str) -> str:
    """Fetches high-level historical data and pricing profiles for market analysis."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="7d")
        return (
            f"Source Checked: Yahoo Finance Core API\n"
            f"Ticker: {ticker}\n"
            f"Current Price: ${info.get('currentPrice', 'N/A')}\n"
            f"52-Week High: ${info.get('fiftyTwoWeekHigh', 'N/A')}\n"
            f"7-Day Close Trend:\n{hist['Close'].to_string()}\n"
        )
    except Exception as e:
        return f"Error scanning {ticker}: {str(e)}"


class MarketScanRequest(BaseModel):
    watch_list: list[str]


@app.post("/api/v1/predict-best-stock")
async def get_single_best_stock(payload: MarketScanRequest):
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set.",
        )

    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        search_tool = DuckDuckGoSearchRun()
        tickers_string = ", ".join(payload.watch_list)

        # Agent 1: Quantitative Specialist
        financial_analyst = Agent(
            role="Senior Technical Financial Analyst",
            goal="Analyze charts, volumes, and mathematical indicators to find explosive setups.",
            backstory="A quantitative Wall Street analyst tracking historical indicators, support lines, and moving averages.",
            verbose=True,
            llm=llm,
            tools=[fetch_stock_data],
        )

        # Agent 2: Media and Economic Sentiment Tracker
        sentiment_analyst = Agent(
            role="Global Financial News & Media Analyst",
            goal="Scan breaking news, financial magazines (Bloomberg, Reuters, Forbes, WSJ), and economic updates.",
            backstory=(
                "An expert financial media tracker specializing in detecting bullish or bearish "
                "market narratives, press releases, and geopolitical data."
            ),
            verbose=True,
            llm=llm,
            tools=[search_tool],
        )

        # Agent 3: The Ultimate Filter / Committee Chair
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
            verbose=True,
            llm=llm,
        )

        # Task Definitions
        task_technical = Task(
            description=f"Analyze data logs and short-term trends for: {tickers_string}.",
            expected_output="Technical health assessment for the asset pool.",
            agent=financial_analyst,
        )

        task_sentiment = Task(
            description=(
                f"Scan recent financial news and market sentiment for: {tickers_string}. "
                "Identify bullish or bearish signals from credible financial media sources "
                "such as Bloomberg, Reuters, Forbes, and the Wall Street Journal."
            ),
            expected_output=(
                "Sentiment analysis report with bullish/bearish signals for each stock in the watchlist."
            ),
            agent=sentiment_analyst,
        )

        task_committee = Task(
            description=(
                f"Review the technical and sentiment reports for: {tickers_string}. "
                "Select EXACTLY ONE best stock as your final recommendation. "
                "Provide: Ticker Symbol, Reason for Selection, Risk Level (Low/Medium/High), "
                "Confidence Score (0–100%), and all Data Sources Used."
            ),
            expected_output=(
                "Single best stock pick with full justification, risk level, confidence score, "
                "and a complete audit trail of all sources consulted."
            ),
            agent=committee_chair,
            context=[task_technical, task_sentiment],
        )

        crew = Crew(
            agents=[financial_analyst, sentiment_analyst, committee_chair],
            tasks=[task_technical, task_sentiment, task_committee],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        return {"recommendation": str(result)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. RUN SERVER (standalone mode)
# ==========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
