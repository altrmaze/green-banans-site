"""
app.py — Greens ACC Market Intelligence Engine
Run with: streamlit run app.py
"""

import os
import re
import threading
import time

import requests
import streamlit as st
import uvicorn

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
LOCAL_BACKEND_URLS = {"http://127.0.0.1:8000", "http://localhost:8000"}
MAX_TICKERS = 8
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def _run_api() -> None:
    from market_engine import app as fastapi_app

    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")


def _wait_for_backend(timeout_seconds: float = 8.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/health", timeout=1.5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.4)
    return False


def _ensure_backend_ready() -> bool:
    if BACKEND_URL not in LOCAL_BACKEND_URLS:
        return _wait_for_backend()

    if "api_started" not in st.session_state:
        st.session_state["api_started"] = True
        api_thread = threading.Thread(target=_run_api, daemon=True)
        api_thread.start()
    return _wait_for_backend()


def _parse_tickers(raw_input: str) -> tuple[list[str], list[str]]:
    accepted: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for candidate in raw_input.split(","):
        ticker = candidate.strip().upper()
        if not ticker:
            continue
        if not TICKER_PATTERN.fullmatch(ticker):
            rejected.append(ticker)
            continue
        if ticker not in seen:
            seen.add(ticker)
            accepted.append(ticker)
    return accepted[:MAX_TICKERS], rejected


st.set_page_config(page_title="Greens ACC - Market Intelligence", page_icon="🟢", layout="wide")
st.markdown(
    """
<style>
    .stApp {
        background: linear-gradient(180deg, #f5faf6 0%, #eef5ef 100%);
        color: #0f2314;
    }
    .hero {
        border: 1px solid #d5e6d9;
        border-radius: 16px;
        padding: 1.5rem 1.6rem;
        background: linear-gradient(135deg, #ffffff 0%, #f1f8f3 100%);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: clamp(1.8rem, 3vw, 2.5rem);
        line-height: 1.15;
        color: #13351b;
    }
    .hero p {
        margin: 0.7rem 0 0;
        color: #2c4e35;
    }
    .metric-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.8rem;
        margin: 1rem 0 1.2rem;
    }
    .metric-card {
        border: 1px solid #d8e7dc;
        border-radius: 12px;
        padding: 0.75rem;
        background: #ffffff;
    }
    .metric-card small { color: #45634d; }
    .metric-card strong { color: #1a6d2c; font-size: 1.1rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<section class="hero">
  <h1>Greens ACC Market Intelligence</h1>
  <p>Corporate-grade AI stock committee with technical trend and sentiment signals in one recommendation flow.</p>
</section>
""",
    unsafe_allow_html=True,
)
st.markdown(
    """
<div class="metric-row">
  <div class="metric-card"><small>Watchlist limit</small><br><strong>8 tickers</strong></div>
  <div class="metric-card"><small>Analysis modes</small><br><strong>Technical + News</strong></div>
  <div class="metric-card"><small>Output shape</small><br><strong>Single ranked pick</strong></div>
</div>
""",
    unsafe_allow_html=True,
)

backend_ready = _ensure_backend_ready()

if not os.getenv("OPENAI_API_KEY"):
    st.warning("OPENAI_API_KEY is not set. Add it before running analysis requests.")

if not backend_ready:
    st.error("Backend health check failed. Confirm FastAPI is running and BACKEND_URL is correct.")

st.subheader("Build watchlist")
tickers_input = st.text_input(
    "Enter tickers (comma-separated)",
    placeholder="AAPL, MSFT, NVDA",
    help="Allowed format: uppercase letters, numbers, dot, and dash.",
)
accepted_tickers, rejected_tickers = _parse_tickers(tickers_input)

if rejected_tickers:
    st.warning(f"Ignored invalid ticker(s): {', '.join(rejected_tickers)}")
if len(accepted_tickers) == MAX_TICKERS and len([t for t in tickers_input.split(',') if t.strip()]) > MAX_TICKERS:
    st.info(f"Only the first {MAX_TICKERS} valid tickers are used per request.")

analyze = st.button("Run AI analysis", type="primary", use_container_width=True)
if analyze:
    if not accepted_tickers:
        st.error("Enter at least one valid ticker.")
    elif not os.getenv("OPENAI_API_KEY"):
        st.error("Server AI key is missing. Set OPENAI_API_KEY and retry.")
    elif not backend_ready:
        st.error("Backend is unavailable. Wait a moment and retry.")
    else:
        with st.spinner("Running analysis workflow. This may take up to a few minutes."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/v1/predict-best-stock",
                    json={"watch_list": accepted_tickers},
                    timeout=240,
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success("Analysis complete")
                    st.markdown("### AI committee recommendation")
                    st.markdown(data.get("recommendation", "No recommendation returned."))
                else:
                    try:
                        detail = response.json().get("detail", "Unknown API error")
                    except ValueError:
                        detail = response.text or "Unknown API error"
                    st.error(f"Request failed ({response.status_code}): {detail}")
            except requests.Timeout:
                st.error("Request timed out. Retry with fewer tickers.")
            except requests.RequestException:
                st.error("Could not reach backend service.")

st.caption("For informational use only. Not investment advice.")
