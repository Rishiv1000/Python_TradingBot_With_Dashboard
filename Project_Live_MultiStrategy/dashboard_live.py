import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from kiteconnect import KiteConnect

try:
    import psutil
except ModuleNotFoundError:
    psutil = None


st.set_page_config(page_title="Multi Strategy Terminal", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
ACCESS_TOKEN_FILE = os.path.join(BASE_DIR, "access_token.txt")
load_dotenv(ENV_PATH)

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")

STRATEGIES = {
    "GREEN": {
        "folder": os.path.join(BASE_DIR, "Green Strategy"),
        "runner": os.path.join(BASE_DIR, "Green Strategy", "main_runner.py"),
        "db": os.path.join(BASE_DIR, "Green Strategy", "db_manager", "trading_bot_green.db"),
        "color": "#2ea043",
    },
    "RSI": {
        "folder": os.path.join(BASE_DIR, "Rsi Strategy"),
        "runner": os.path.join(BASE_DIR, "Rsi Strategy", "main_runner.py"),
        "db": os.path.join(BASE_DIR, "Rsi Strategy", "db_manager", "trading_bot_rsi.db"),
        "color": "#ff7b72",
    },
}


st.markdown("""
    <style>
    .stApp { background-color: #0d1117; }
    .stButton>button { height: 2.8rem; font-weight: 800; border-radius: 8px; }
    [data-testid="stSidebar"] label { font-size: 0.82rem !important; font-weight: 700 !important; }
    .status-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 900;
    }
    </style>
""", unsafe_allow_html=True)


def ensure_db(path):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symbols_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE,
            exchange TEXT,
            instrument_token INTEGER,
            isExecuted INTEGER DEFAULT 0,
            buyprice REAL DEFAULT NULL,
            buytime TEXT DEFAULT NULL,
            buy_order_id TEXT DEFAULT NULL,
            product TEXT DEFAULT 'MIS',
            last_sell_time TEXT DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            buytime TEXT,
            buyprice REAL,
            selltime TEXT,
            sellprice REAL,
            pnl REAL,
            reason TEXT,
            slippage REAL,
            buy_order_id TEXT,
            sell_order_id TEXT,
            strategy TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()


for meta in STRATEGIES.values():
    ensure_db(meta["db"])


def read_df(db_path, query, params=()):
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()


def execute_db(db_path, query, params=()):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(query, params)
        conn.commit()
    finally:
        conn.close()


def scalar(db_path, query, params=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query, params).fetchone()[0]
    finally:
        conn.close()


def kite_session():
    if not API_KEY or not os.path.exists(ACCESS_TOKEN_FILE):
        return None
    kite = KiteConnect(api_key=API_KEY, timeout=30)
    with open(ACCESS_TOKEN_FILE, "r") as f:
        token = f.read().strip()
    if not token:
        return None
    kite.set_access_token(token)
    return kite


def resolve_token(symbol, exchange):
    kite = kite_session()
    if not kite:
        raise RuntimeError("Kite session missing. Login first.")
    instrument = f"{exchange.upper()}:{symbol.upper()}"
    return kite.ltp(instrument)[instrument]["instrument_token"]


def process_for_runner(runner):
    runner_norm = os.path.normcase(os.path.abspath(runner))
    if psutil is None:
        script = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like '*"
            + runner.replace("\\", "\\\\")
            + "*' } | Select-Object -First 1 -ExpandProperty ProcessId"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pid = result.stdout.strip()
        return int(pid) if pid.isdigit() else None

    for proc in psutil.process_iter(["pid", "cmdline", "status"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if os.path.normcase(runner_norm) in os.path.normcase(cmdline):
                if proc.info.get("status") != psutil.STATUS_ZOMBIE:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def is_running(strategy):
    return process_for_runner(STRATEGIES[strategy]["runner"]) is not None


def start_strategy(strategy):
    meta = STRATEGIES[strategy]
    if is_running(strategy):
        return
    subprocess.Popen([sys.executable, meta["runner"]], cwd=meta["folder"])


def stop_strategy(strategy, hard=False):
    proc = process_for_runner(STRATEGIES[strategy]["runner"])
    if not proc:
        return
    if psutil is None:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {int(proc)} -Force"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return

    if hard:
        for child in proc.children(recursive=True):
            child.kill()
        proc.kill()
    else:
        proc.terminate()


with st.sidebar:
    st.title("Strategy Terminal")

    st.subheader("Button Meaning")
    st.caption("START: us strategy ka alag project/process start. Buy aur sell dono active.")
    st.caption("STOP: us strategy ka process stop. Buy aur sell dono band.")
    st.caption("TERMINATE: hard kill. Emergency stop.")

    st.divider()
    st.subheader("Strategy Control")
    for strategy, meta in STRATEGIES.items():
        running = is_running(strategy)
        color = "#238636" if running else "#da3633"
        text = "RUNNING" if running else "STOPPED"
        symbol_count = scalar(meta["db"], "SELECT COUNT(*) FROM symbols_state")
        open_count = scalar(meta["db"], "SELECT COUNT(*) FROM symbols_state WHERE isExecuted=1")

        st.markdown(
            f"<div style='margin-top:14px;font-weight:900;color:#f0f6fc'>{strategy} <span class='status-pill' style='background:{color}22;color:{color};border:1px solid {color};'>{text}</span></div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Symbols: {symbol_count} | Open: {open_count}")
        c1, c2 = st.columns(2)
        if c1.button(f"START {strategy}", key=f"start_{strategy}", use_container_width=True):
            start_strategy(strategy)
            st.rerun()
        if c2.button(f"STOP {strategy}", key=f"stop_{strategy}", use_container_width=True):
            stop_strategy(strategy)
            st.rerun()
        if st.button(f"TERMINATE {strategy}", key=f"term_{strategy}", use_container_width=True):
            stop_strategy(strategy, hard=True)
            st.rerun()

    st.divider()
    st.subheader("Kite Session")
    if API_KEY and API_SECRET:
        kite = KiteConnect(api_key=API_KEY)
        if st.button("Get Login URL", use_container_width=True):
            st.code(kite.login_url())
        req_token = st.text_input("Request Token")
        if st.button("Generate Session", use_container_width=True):
            try:
                data = kite.generate_session(req_token, api_secret=API_SECRET)
                with open(ACCESS_TOKEN_FILE, "w") as f:
                    f.write(data["access_token"])
                st.success("Session saved.")
            except Exception as e:
                st.error(str(e))
    else:
        st.error("Kite keys missing in .env")

    st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")


st.title("Multi Strategy Terminal")

cards = st.columns(len(STRATEGIES))
for col, (strategy, meta) in zip(cards, STRATEGIES.items()):
    with col:
        running = is_running(strategy)
        color = "#238636" if running else "#da3633"
        status = "RUNNING" if running else "STOPPED"
        st.markdown(
            f"""
            <div style="border:1px solid #30363d;border-radius:8px;padding:14px;background:#161b22">
                <div style="font-size:1.2rem;font-weight:900;color:{meta['color']}">{strategy}</div>
                <span class="status-pill" style="background:{color}22;color:{color};border:1px solid {color};">{status}</span>
                <div style="margin-top:8px;color:#8b949e">DB: {os.path.basename(meta['db'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

tab_symbols, tab_positions, tab_history, tab_memory = st.tabs([
    "Symbols",
    "Active Positions",
    "Trade History",
    "Bot Memory",
])

with tab_symbols:
    for strategy, meta in STRATEGIES.items():
        with st.expander(f"{strategy} Symbols", expanded=True):
            df = read_df(meta["db"], "SELECT symbol, exchange, instrument_token FROM symbols_state ORDER BY symbol")
            st.dataframe(df, use_container_width=True, height=220)

            a, b, c = st.columns([2, 1, 1])
            symbol = a.text_input(f"{strategy} symbol", key=f"symbol_{strategy}").strip().upper()
            exchange = b.text_input("Exchange", value="NSE", key=f"exchange_{strategy}").strip().upper()
            if c.button(f"Add {strategy}", key=f"add_{strategy}", use_container_width=True):
                try:
                    token = resolve_token(symbol, exchange)
                    execute_db(
                        meta["db"],
                        "INSERT OR IGNORE INTO symbols_state (symbol, exchange, instrument_token, isExecuted) VALUES (?, ?, ?, 0)",
                        (symbol, exchange, token),
                    )
                    execute_db(
                        meta["db"],
                        "UPDATE symbols_state SET exchange=?, instrument_token=? WHERE symbol=? AND isExecuted=0",
                        (exchange, token, symbol),
                    )
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            remove_symbol = st.selectbox(f"Remove from {strategy}", [""] + df["symbol"].tolist(), key=f"remove_{strategy}")
            if remove_symbol and st.button(f"Delete {remove_symbol}", key=f"delete_{strategy}"):
                execute_db(meta["db"], "DELETE FROM symbols_state WHERE symbol=? AND isExecuted=0", (remove_symbol,))
                st.rerun()

with tab_positions:
    frames = []
    for strategy, meta in STRATEGIES.items():
        df = read_df(
            meta["db"],
            "SELECT ? AS strategy, symbol, buyprice, buytime, product FROM symbols_state WHERE isExecuted=1",
            (strategy,),
        )
        frames.append(df)
    st.dataframe(pd.concat(frames, ignore_index=True), use_container_width=True, height=420)

with tab_history:
    frames = []
    for strategy, meta in STRATEGIES.items():
        df = read_df(
            meta["db"],
            "SELECT ? AS strategy, symbol, buytime, buyprice, selltime, sellprice, pnl, reason FROM trades_log ORDER BY id DESC LIMIT 100",
            (strategy,),
        )
        frames.append(df)
    history = pd.concat(frames, ignore_index=True)
    st.dataframe(history, use_container_width=True, height=420)
    if not history.empty:
        st.metric("Total PnL", f"Rs {history['pnl'].sum():,.2f}")

with tab_memory:
    for strategy, meta in STRATEGIES.items():
        cache_file = os.path.join(meta["folder"], "live_df_cache.pkl")
        with st.expander(f"{strategy} Memory", expanded=False):
            if not os.path.exists(cache_file):
                st.info("Bot has not written memory cache yet.")
                continue
            try:
                import pickle
                with open(cache_file, "rb") as f:
                    cache = pickle.load(f)
                if not cache:
                    st.info("Cache is empty.")
                    continue
                symbol = st.selectbox("Symbol", list(cache.keys()), key=f"cache_{strategy}")
                st.dataframe(cache[symbol].tail(50), use_container_width=True)
            except Exception as e:
                st.warning(f"Could not read cache: {e}")

time.sleep(5)
st.rerun()
