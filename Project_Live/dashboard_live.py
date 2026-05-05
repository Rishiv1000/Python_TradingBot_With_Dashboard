import streamlit as st
import pandas as pd
import os
import sys
import time
import subprocess
import sqlite3
import psutil
import pickle
from datetime import datetime
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Page Config
st.set_page_config(page_title="Trading Terminal Pro", layout="wide", page_icon="📈")

# Paths & Auth
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, "db_manager", "config.py")
load_dotenv(os.path.join(ROOT_DIR, "db_manager", ".env"))

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
ACCESS_TOKEN_FILE = os.path.join(ROOT_DIR, "db_manager", "access_token.txt")

# Styling
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; }
    .header-box { background: linear-gradient(90deg, #161b22, #21262d); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; border: 1px solid #30363d; }
    .stButton>button { height: 3.5rem; font-size: 1.1rem; font-weight: bold; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; }
    
    /* Sidebar Compact Style */
    [data-testid="stSidebar"] { font-size: 0.85rem; }
    [data-testid="stSidebar"] .stMarkdown p { font-size: 0.85rem; }
    [data-testid="stSidebar"] label { font-size: 0.8rem !important; font-weight: 600 !important; }
    </style>
""", unsafe_allow_html=True)

def get_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    parts = line.split("=")
                    k, v = parts[0].strip(), "=".join(parts[1:]).strip().strip('"').strip("'")
                    cfg[k] = v
    return cfg

def update_config(k, v):
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f: lines = f.readlines()
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith(f"{k} =") or line.strip().startswith(f"{k}="):
                new_lines.append(f"{k} = '{v}'\n" if isinstance(v, str) else f"{k} = {v}\n")
                found = True
            else: new_lines.append(line)
        if not found: new_lines.append(f"{k} = '{v}'\n" if isinstance(v, str) else f"{k} = {v}\n")
        with open(CONFIG_PATH, "w") as f: f.writelines(new_lines)

def is_bot_running():
    if "bot_pid" in st.session_state:
        pid = st.session_state["bot_pid"]
        if psutil.pid_exists(pid):
            p = psutil.Process(pid)
            if p.status() != psutil.STATUS_ZOMBIE: return True
    return False

cfg = get_config()
bot_active = is_bot_running()
is_live = str(cfg.get('REAL_TRADING_ENABLED', 'False')).lower() == 'true'
bot_running_flag = str(cfg.get('BOT_RUNNING', 'False')).lower() == 'true'

# --- SIDEBAR: CONFIG & AUTH ---
with st.sidebar:
    st.title("🛡️ Secure Terminal")
    
    with st.expander("🔑 Session Auth", expanded=not os.path.exists(ACCESS_TOKEN_FILE)):
        if API_KEY and API_SECRET:
            kite = KiteConnect(api_key=API_KEY)
            if st.button("🔗 Get Login URL", use_container_width=True):
                st.code(kite.login_url())
            req_token = st.text_input("Request Token")
            if st.button("✅ Generate Session", use_container_width=True):
                try:
                    data = kite.generate_session(req_token, api_secret=API_SECRET)
                    with open(ACCESS_TOKEN_FILE, "w") as f: f.write(data["access_token"])
                    st.success("Session Valid!")
                except Exception as e: st.error(str(e))
        else: st.error("Keys missing in .env")

    st.divider()
    st.markdown("**Environment Status**")
    if is_live: st.error("🚀 REAL TRADING ACTIVE")
    else: st.info("🛡️ PAPER TRADING")
    
    st.caption(f"Last Sync: {datetime.now().strftime('%H:%M:%S')}")
    st.caption("Auto-refreshing every 5s")

# --- MAIN INTERFACE ---


# --- STRATEGY BAR (HORIZONTAL) ---
sc1, sc2, sc3 = st.columns([2, 1.5, 3])

with sc1:
    current_strat = cfg.get('ACTIVE_STRATEGY', 'GREEN')
    new_strat = st.radio("📡 **Active Strategy**", ["GREEN", "RSI"], 
                         index=0 if current_strat == "GREEN" else 1, 
                         horizontal=True, label_visibility="collapsed")
    if new_strat != current_strat:
        update_config('ACTIVE_STRATEGY', new_strat)
        st.rerun()

with sc2:
    # --- PARAMETERS POPOVER ---
    with st.popover("⚙️ Edit Parameters", use_container_width=True):
        st.subheader(f"Settings for {new_strat}")
        if new_strat == "GREEN":
            t = st.number_input("Target %", float(cfg.get('TARGET', 0.5)), step=0.1)
            if t != float(cfg.get('TARGET', 0.5)): update_config('TARGET', t)
            sl = st.number_input("Stoploss %", float(cfg.get('STOPLOSS', 0.5)), step=0.1)
            if sl != float(cfg.get('STOPLOSS', 0.5)): update_config('STOPLOSS', sl)
        else:
            bl = st.number_input("RSI Buy Level", int(cfg.get('BUY_LEVEL', 30)))
            if bl != int(cfg.get('BUY_LEVEL', 30)): update_config('BUY_LEVEL', bl)
            sl_l = st.number_input("RSI Sell Level", int(cfg.get('SELL_LEVEL', 70)))
            if sl_l != int(cfg.get('SELL_LEVEL', 70)): update_config('SELL_LEVEL', sl_l)
        
        lb_key = f"LOOKBACK_DAYS_{new_strat}"
        lb_val = float(cfg.get(lb_key, 0.5 if new_strat == "GREEN" else 2.0))
        lb = st.slider(f"Signal Lookback", 0.01, 10.0, lb_val, step=0.01)
        if lb != lb_val: update_config(lb_key, lb)

with sc3:
    status_color = "#238636" if (bot_active and bot_running_flag) else ("#d29922" if bot_active else "#da3633")
    status_text = "ENGINE: RUNNING" if (bot_active and bot_running_flag) else ("ENGINE: STOPPING" if bot_active else "ENGINE: IDLE")
    st.markdown(f'<div style="text-align:center; padding:8px; border-radius:8px; background:{status_color}22; border:1px solid {status_color}; color:{status_color}; font-weight:bold;">{status_text}</div>', unsafe_allow_html=True)

st.divider()

# Three Buttons Row
c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
with c1:
    if st.button("▶️ START BOT", use_container_width=True, type="primary"):
        update_config("BOT_RUNNING", True)
        runner = os.path.join(ROOT_DIR, "main_runner.py")
        proc = subprocess.Popen([sys.executable, runner], cwd=ROOT_DIR)
        st.session_state["bot_pid"] = proc.pid
        st.rerun()
with c2:
    if st.button("⏸️ STOP ENTRY", use_container_width=True):
        update_config("BOT_RUNNING", False); st.rerun()
with c3:
    if st.button("🛑 TERMINATE", use_container_width=True):
        if "bot_pid" in st.session_state:
            pid = st.session_state["bot_pid"]
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                for child in p.children(recursive=True): child.kill()
                p.kill()
            del st.session_state["bot_pid"]
        update_config("BOT_RUNNING", False); st.rerun()
with c4:
    status_color = "#238636" if (bot_active and bot_running_flag) else ("#d29922" if bot_active else "#da3633")
    status_text = "RUNNING" if (bot_active and bot_running_flag) else ("STOPPING (Exit Only)" if bot_active else "IDLE")
    st.markdown(f'<div style="text-align:center; padding:15px; border-radius:10px; background:{status_color}22; border:1px solid {status_color}; color:{status_color}; font-weight:bold; font-size:1.1rem;">{status_text}</div>', unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Active Positions", "📜 Trade History", "📈 Market Signal Data"])

db_path = os.path.join(ROOT_DIR, "db_manager", f"{cfg.get('DB_NAME', 'trading_bot_live')}.db")

with tab1:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        df = pd.read_sql("SELECT symbol, buyprice, buytime, strategy FROM symbols_state WHERE isExecuted=1", conn)
        st.dataframe(df, use_container_width=True, height=400)
        conn.close()

with tab2:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        df_h = pd.read_sql("SELECT symbol, buytime, buyprice, selltime, sellprice, pnl, reason, strategy FROM trades_log ORDER BY id DESC LIMIT 100", conn)
        st.dataframe(df_h, use_container_width=True, height=400)
        if not df_h.empty:
            st.metric("Session PnL", f"₹{df_h['pnl'].sum():,.2f}")
        conn.close()

with tab3:
    cache_file = os.path.join(ROOT_DIR, "live_df_cache.pkl")
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cached_data = pickle.load(f)
        if cached_data:
            sym = st.selectbox("Symbol to Inspect", list(cached_data.keys()))
            st.dataframe(cached_data[sym].tail(50), use_container_width=True)
    else: st.info("Market data will appear here once the bot starts scanning.")

st.caption(f"Last Sync: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(5)
st.rerun()
