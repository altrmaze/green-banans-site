import os
import threading
import time
import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crewai import Agent, Crew, Process, Task
from crewai.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
import yfinance as yf
import streamlit as st

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
# Set your OpenAI API key as an environment variable before running:
#   export OPENAI_API_KEY="sk-..."
# Then launch with:  streamlit run market_engine.py

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise EnvironmentError(
        "OPENAI_API_KEY environment variable is not set. "
        "Export it before running: export OPENAI_API_KEY='sk-...'"
    )

# Global LLM settings - low temperature for sharp analytical logic
llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
search_tool = DuckDuckGoSearchRun()

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
    try:
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
# 3. STREAMLIT FRONTEND
# ==========================================

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


def main():
    st.set_page_config(
        page_title="Greens ACC – Market Intelligence Engine",
        page_icon="🟢",
        layout="wide",
    )

    st.title("🟢 Greens ACC — AI Market Intelligence Engine")
    st.caption("Powered by CrewAI & GPT-4o | Technical Analysis + News Sentiment")

    st.divider()

    st.subheader("📋 Build Your Watchlist")
    tickers_input = st.text_input(
        "Enter stock tickers (comma-separated)",
        placeholder="e.g. AAPL, TSLA, NVDA, MSFT, AMZN",
    )

    col1, _ = st.columns([1, 3])
    with col1:
        analyze = st.button("🔍 Run AI Analysis", type="primary", use_container_width=True)

    if analyze:
        if not tickers_input.strip():
            st.error("⚠️ Please enter at least one stock ticker.")
        else:
            tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
            st.info(
                f"🤖 AI Crew is analyzing **{len(tickers)} stock(s)**: {', '.join(tickers)}"
            )

            with st.spinner("Running multi-agent analysis… This may take 1–3 minutes."):
                try:
                    response = requests.post(
                        "http://localhost:8000/api/v1/predict-best-stock",
                        json={"watch_list": tickers},
                        timeout=300,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.success("✅ Analysis Complete!")
                        st.divider()
                        st.subheader("🏆 AI Committee Recommendation")
                        st.markdown(data["recommendation"])
                    else:
                        st.error(f"API Error {response.status_code}: {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error(
                        "❌ Cannot connect to the backend API. "
                        "Ensure the server started correctly on port 8000."
                    )
                except requests.exceptions.Timeout:
                    st.error(
                        "⏱️ Request timed out. The analysis is taking longer than expected. "
                        "Try a smaller watchlist."
                    )
                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")

    st.divider()
    st.caption(
        "⚠️ This tool is for educational and informational purposes only. "
        "Not financial advice."
    )


if __name__ == "__main__":
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    time.sleep(2)
    main()
