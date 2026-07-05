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


def _get_admin_credentials() -> tuple[str, str]:
    return os.getenv("ADMIN_USERNAME", ""), os.getenv("ADMIN_PASSWORD", "")


def _admin_is_configured() -> bool:
    username, password = _get_admin_credentials()
    return bool(username and password)


def _render_market_page(backend_ready: bool) -> None:
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
    if len(accepted_tickers) == MAX_TICKERS and len([t for t in tickers_input.split(",") if t.strip()]) > MAX_TICKERS:
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


def _render_admin_page(backend_ready: bool) -> None:
    st.markdown(
        """
    <section class="hero">
      <h1>Admin Console</h1>
      <p>Monitor backend health, request analytics, and operational status in real time.</p>
    </section>
    """,
        unsafe_allow_html=True,
    )

    if not _admin_is_configured():
        st.error("Admin credentials are not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD.")
        st.code("export ADMIN_USERNAME='your-admin-user'\nexport ADMIN_PASSWORD='strong-password'")
        st.info("If you want username/password to match, set both variables to the same secure value.")
        return

    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if "admin_username_input" not in st.session_state:
        st.session_state["admin_username_input"] = ""
    if "admin_password_input" not in st.session_state:
        st.session_state["admin_password_input"] = ""

    with st.form("admin-login"):
        st.subheader("Admin Login")
        username = st.text_input("Username", value=st.session_state["admin_username_input"])
        password = st.text_input("Password", type="password", value=st.session_state["admin_password_input"])
        submitted = st.form_submit_button("Login")

    if submitted:
        expected_username, expected_password = _get_admin_credentials()
        if username == expected_username and password == expected_password:
            st.session_state["admin_authenticated"] = True
            st.session_state["admin_username_input"] = username
            st.session_state["admin_password_input"] = password
            st.success("Admin access granted.")
        else:
            st.session_state["admin_authenticated"] = False
            st.error("Invalid admin credentials.")

    if not st.session_state["admin_authenticated"]:
        return

    st.subheader("Operational Monitoring")
    if backend_ready:
        try:
            response = requests.get(
                f"{BACKEND_URL}/api/v1/admin/monitor",
                auth=(st.session_state["admin_username_input"], st.session_state["admin_password_input"]),
                timeout=8,
            )
            if response.status_code == 200:
                payload = response.json()
                req = payload.get("requests", {})
                st.markdown("#### Backend Metrics")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Uptime (sec)", payload.get("uptime_seconds", 0))
                col2.metric("Total requests", req.get("total", 0))
                col3.metric("Success requests", req.get("success", 0))
                col4.metric("Error requests", req.get("error", 0))
                st.metric("Average latency (ms)", req.get("avg_latency_ms", 0))
                st.markdown("#### Runtime Configuration")
                st.json(payload.get("config", {}))
            else:
                st.error(f"Failed to load monitor data ({response.status_code}): {response.text}")
        except requests.RequestException:
            st.error("Failed to connect to backend monitor endpoint.")
    else:
        st.warning("Backend is not reachable. Monitoring data is unavailable.")

    st.subheader("Viewer Management")
    viewer_mode = st.selectbox("Viewer mode", ["Read-only", "Analyst", "Admin"])
    auto_refresh = st.slider("Auto-refresh interval (seconds)", min_value=10, max_value=120, value=30, step=5)
    st.write(f"Current viewer mode: **{viewer_mode}** | Refresh interval: **{auto_refresh}s**")

    st.subheader("Develop Notes")
    st.text_area("Admin development notes", placeholder="Track fixes, ideas, and next backend/frontend tasks.")

    if st.button("Logout", use_container_width=True):
        st.session_state["admin_authenticated"] = False
        st.session_state["admin_password_input"] = ""
        st.success("Logged out.")


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

backend_ready = _ensure_backend_ready()
page = st.sidebar.radio("Workspace", ["Market Intelligence", "Admin Console"])
if page == "Market Intelligence":
    _render_market_page(backend_ready=backend_ready)
else:
    _render_admin_page(backend_ready=backend_ready)
