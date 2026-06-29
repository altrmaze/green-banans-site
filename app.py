"""
app.py — Greens ACC Market Intelligence Engine
Run with:  streamlit run app.py

Before launching, set your OpenAI API key:
    export OPENAI_API_KEY="sk-..."
"""

import os
import threading
import time

import requests
import streamlit as st
import uvicorn

# ==========================================
# 1. START FASTAPI BACKEND IN BACKGROUND
# ==========================================
# Streamlit re-runs this script on every interaction, so we guard
# the thread startup with st.session_state to start it only once.

def _run_api():
    from market_engine import app as fastapi_app
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="warning")


if "api_started" not in st.session_state:
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()
    time.sleep(2)  # give the server a moment to come up
    st.session_state["api_started"] = True

# ==========================================
# 2. STREAMLIT UI
# ==========================================

st.set_page_config(
    page_title="Greens ACC – Market Intelligence Engine",
    page_icon="🟢",
    layout="wide",
)

st.title("🟢 Greens ACC — AI Market Intelligence Engine")
st.caption("Powered by CrewAI & GPT-4o  |  Technical Analysis + News Sentiment")

# API key warning banner
if not os.getenv("OPENAI_API_KEY"):
    st.warning(
        "⚠️ **OPENAI_API_KEY is not set.** "
        "Export it before running:\n\n"
        "```bash\nexport OPENAI_API_KEY='sk-...'\n```"
    )

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
    elif not os.getenv("OPENAI_API_KEY"):
        st.error("❌ Set OPENAI_API_KEY before running an analysis.")
    else:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        st.info(f"🤖 AI Crew is analyzing **{len(tickers)} stock(s)**: {', '.join(tickers)}")

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
                    "The server may still be starting — wait a moment and try again."
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
