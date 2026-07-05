"""
app.py — Greens ACC Market Intelligence Engine
Run with: streamlit run app.py
"""

import os
import re
import threading
import time
from html import escape
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests
import streamlit as st
import uvicorn

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
LOCAL_BACKEND_URLS = {"http://127.0.0.1:8000", "http://localhost:8000"}
MAX_TICKERS = 8
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
WORKSPACE_TO_QUERY = {"Market Intelligence": "market", "Admin Console": "admin"}
QUERY_TO_WORKSPACE = {value: key for key, value in WORKSPACE_TO_QUERY.items()}
ECONOMY_FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("Forbes", "https://www.forbes.com/business/feed/"),
    ("The Economist", "https://www.economist.com/finance-and-economics/rss.xml"),
]


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


def _request_analysis(accepted_tickers: list[str]) -> bool:
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
                return True
            try:
                detail = response.json().get("detail", "Unknown API error")
            except ValueError:
                detail = response.text or "Unknown API error"
            st.error(f"Request failed ({response.status_code}): {detail}")
            return False
        except requests.Timeout:
            st.error("Request timed out. Retry with fewer tickers.")
            return False
        except requests.RequestException:
            st.error("Could not reach backend service.")
            return False


def _workspace_from_query() -> str:
    raw_workspace = st.query_params.get("workspace", "market")
    workspace_key = raw_workspace[0] if isinstance(raw_workspace, list) else raw_workspace
    return QUERY_TO_WORKSPACE.get(str(workspace_key).lower(), "Market Intelligence")


def _sync_workspace_query(selected_workspace: str) -> None:
    target = WORKSPACE_TO_QUERY[selected_workspace]
    current = st.query_params.get("workspace", "")
    current_value = current[0] if isinstance(current, list) else current
    if current_value != target:
        st.query_params["workspace"] = target


def _parse_news_items(source: str, payload: str, limit: int = 2) -> list[dict[str, str]]:
    root = ET.fromstring(payload)
    headlines: list[dict[str, str]] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            headlines.append({"source": source, "title": title, "link": link})
        if len(headlines) >= limit:
            return headlines

    for entry in root.findall(".//{*}entry"):
        title = (entry.findtext("{*}title") or "").strip()
        link_elem = entry.find("{*}link")
        link = ""
        if link_elem is not None:
            link = (link_elem.get("href") or link_elem.text or "").strip()
        if title and link:
            headlines.append({"source": source, "title": title, "link": link})
        if len(headlines) >= limit:
            return headlines

    return headlines


@st.cache_data(ttl=600)
def _load_economy_headlines(max_items: int = 8) -> list[dict[str, str]]:
    headlines: list[dict[str, str]] = []
    for source, feed_url in ECONOMY_FEEDS:
        try:
            response = requests.get(
                feed_url,
                timeout=6,
                headers={"User-Agent": "greens-acc-news-client/1.0"},
            )
            response.raise_for_status()
            headlines.extend(_parse_news_items(source=source, payload=response.text))
        except (requests.RequestException, ET.ParseError):
            continue
        if len(headlines) >= max_items:
            break

    if headlines:
        return headlines[:max_items]

    return [
        {
            "source": "Reuters",
            "title": "Global stocks steady as investors watch inflation data and central bank policy outlook.",
            "link": "https://www.reuters.com/markets/",
        },
        {
            "source": "The Economist",
            "title": "Debt, rates, and growth are reshaping the next cycle for global capital flows.",
            "link": "https://www.economist.com/finance-and-economics",
        },
        {
            "source": "Forbes",
            "title": "Tech and industrial earnings remain key drivers for market leadership this quarter.",
            "link": "https://www.forbes.com/business/",
        },
    ]


def _render_logo_and_news() -> None:
    st.markdown(
        """
    <section class="brand-shell">
      <div class="brand-lockup">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 96 96" role="img">
            <defs>
              <linearGradient id="greensGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#18a64a" />
                <stop offset="100%" stop-color="#0f6d2d" />
              </linearGradient>
            </defs>
            <circle cx="48" cy="48" r="44" fill="url(#greensGradient)" />
            <path d="M30 54c8-19 24-22 39-20-7 17-18 29-39 20z" fill="#ecfff1" opacity="0.95" />
            <path d="M37 63c4-9 14-12 25-11-4 9-11 16-25 11z" fill="#c6f8d3" />
            <circle cx="66" cy="30" r="5" fill="#ecfff1" />
          </svg>
        </div>
        <div>
          <p class="brand-eyebrow">Greens ACC identity</p>
          <h2>Greens ACC</h2>
          <p>Professional AI market intelligence interface with connected frontend and backend execution.</p>
        </div>
      </div>
    </section>
    """,
        unsafe_allow_html=True,
    )

    headlines = _load_economy_headlines()
    ticker_text = "  •  ".join([f"{item['source']}: {item['title']}" for item in headlines])
    st.markdown(
        f"""
    <div class="news-ticker-wrap">
      <strong>Live Economy News</strong>
      <div class="news-ticker" aria-label="Live economy headlines from leading publications">
        <div class="news-ticker-track">{escape(ticker_text)}</div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    news_cards = "".join(
        [
            (
                f"<a class='news-card' href='{escape(item['link'], quote=True)}' target='_blank' "
                f"rel='noopener noreferrer'><small>{escape(item['source'])}</small>"
                f"<span>{escape(item['title'])}</span></a>"
            )
            for item in headlines[:4]
        ]
    )
    st.markdown(
        f"""
    <section class="news-grid">
      {news_cards}
    </section>
    """,
        unsafe_allow_html=True,
    )


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
    _render_logo_and_news()
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
    else:
        st.success("Backend connected and ready.")

    st.link_button("Open Admin Console", "?workspace=admin", use_container_width=True)

    st.subheader("Build watchlist")
    tickers_input = st.text_input(
        "Enter tickers (comma-separated)",
        placeholder="AAPL, MSFT, NVDA",
        help="Allowed format: uppercase letters, numbers, dot, and dash.",
    )
    accepted_tickers, rejected_tickers = _parse_tickers(tickers_input)

    queued_order = st.session_state.get("queued_admin_order")
    if queued_order:
        st.markdown("#### Pending admin order")
        st.info(
            "Admin queued this watchlist on "
            f"{queued_order.get('created_at', 'unknown time')}: {', '.join(queued_order.get('watch_list', []))}"
        )
        queued_execute = st.button("Execute admin order", key="execute_admin_order", use_container_width=True)
        queued_clear = st.button("Clear admin order", key="clear_admin_order", use_container_width=True)

        if queued_clear:
            st.session_state["queued_admin_order"] = None
            st.success("Pending admin order cleared.")
        elif queued_execute:
            queued_tickers = queued_order.get("watch_list", [])
            if not queued_tickers:
                st.error("Queued order is empty.")
            elif not os.getenv("OPENAI_API_KEY"):
                st.error("Server AI key is missing. Set OPENAI_API_KEY and retry.")
            elif not backend_ready:
                st.error("Backend is unavailable. Wait a moment and retry.")
            elif _request_analysis(queued_tickers):
                st.session_state["queued_admin_order"] = None
                st.success("Admin order executed and removed from queue.")

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
            _request_analysis(accepted_tickers)

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
    st.link_button("Back to Market Intelligence", "?workspace=market", use_container_width=True)

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

    st.subheader("Mini Assistant Order")
    st.caption("Queue a market-analysis order here, then execute it from the Market Intelligence page.")
    admin_order_input = st.text_input(
        "Order tickers (comma-separated)",
        key="admin_order_input",
        placeholder="AAPL, MSFT, NVDA",
    )
    admin_accepted, admin_rejected = _parse_tickers(admin_order_input)
    if admin_rejected:
        st.warning(f"Ignored invalid admin ticker(s): {', '.join(admin_rejected)}")
    if st.button("Send order to Market page", key="send_admin_order", use_container_width=True):
        if not admin_accepted:
            st.error("Enter at least one valid ticker for the admin order.")
        else:
            st.session_state["queued_admin_order"] = {
                "watch_list": admin_accepted,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
            st.success("Order sent. Open Market Intelligence to execute it.")

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
    .brand-shell {
        border: 1px solid #d8e7dc;
        border-radius: 16px;
        padding: 1rem;
        background: #ffffff;
        margin-bottom: 0.8rem;
    }
    .brand-lockup {
        display: grid;
        grid-template-columns: auto 1fr;
        align-items: center;
        gap: 1rem;
    }
    .brand-mark {
        width: 88px;
        height: 88px;
        border-radius: 18px;
        overflow: hidden;
        background: #eaf8ed;
        border: 1px solid #cde8d4;
    }
    .brand-mark svg {
        width: 100%;
        height: 100%;
        display: block;
    }
    .brand-eyebrow {
        margin: 0;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #2d6540;
    }
    .brand-lockup h2 {
        margin: 0.2rem 0;
        color: #114822;
    }
    .brand-lockup p {
        margin: 0;
        color: #2f5740;
    }
    .news-ticker-wrap {
        display: grid;
        gap: 0.5rem;
        margin: 0.9rem 0 1rem;
    }
    .news-ticker-wrap strong {
        color: #174d27;
        font-size: 0.95rem;
    }
    .news-ticker {
        border: 1px solid #cfe6d5;
        border-radius: 12px;
        background: #f6fcf7;
        overflow: hidden;
        padding: 0.6rem 0;
    }
    .news-ticker-track {
        color: #1f4b2c;
        font-size: 0.95rem;
        white-space: nowrap;
        padding-left: 100%;
        animation: ticker-scroll 38s linear infinite;
    }
    .news-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.8rem;
        margin-bottom: 1rem;
    }
    .news-card {
        display: grid;
        gap: 0.35rem;
        text-decoration: none;
        border: 1px solid #d8e7dc;
        border-radius: 12px;
        background: #ffffff;
        padding: 0.8rem;
        color: #173824;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .news-card:hover {
        border-color: #2a8e43;
        transform: translateY(-1px);
    }
    .news-card small {
        color: #3b6e4d;
        font-weight: 600;
    }
    .news-card span {
        line-height: 1.35;
        color: #183727;
    }
    @keyframes ticker-scroll {
        from { transform: translateX(0); }
        to { transform: translateX(-100%); }
    }
    @media (max-width: 840px) {
        .brand-lockup {
            grid-template-columns: 1fr;
        }
        .news-grid {
            grid-template-columns: 1fr;
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .news-ticker-track {
            animation: none;
            padding-left: 0.8rem;
            white-space: normal;
            padding-right: 0.8rem;
        }
        .news-card {
            transition: none;
        }
    }
    .metric-card small { color: #45634d; }
    .metric-card strong { color: #1a6d2c; font-size: 1.1rem; }
</style>
""",
    unsafe_allow_html=True,
)

backend_ready = _ensure_backend_ready()
default_workspace = _workspace_from_query()
page = st.sidebar.radio(
    "Workspace",
    ["Market Intelligence", "Admin Console"],
    index=0 if default_workspace == "Market Intelligence" else 1,
)
_sync_workspace_query(page)
if page == "Market Intelligence":
    _render_market_page(backend_ready=backend_ready)
else:
    _render_admin_page(backend_ready=backend_ready)
