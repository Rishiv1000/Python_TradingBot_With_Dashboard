import streamlit as st
import pandas as pd
import os
import sys
import time
import subprocess
import mysql.connector
import psutil
import pickle
from datetime import datetime
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Page Config
st.set_page_config(page_title="Lab Terminal Pro", layout="wide", page_icon="🧪")

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
    .stApp { background-color: #0b0e14; }
    .header-box { background: linear-gradient(90deg, #1c1c2b, #2d2d44); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; border: 1px solid #3e3e5e; }
    .stButton>button { height: 3.5rem; font-size: 1.1rem; font-weight: bold; border-radius: 10px; }
    .sidebar-section { background: #161625; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
    
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

cfg = get_config()
bot_active = is_bot_running() if 'is_bot_running' in globals() else False

# --- SIDEBAR: ALL PARAMETERS ---
with st.sidebar:
    st.title("🧪 Lab Controls")
    
    with st.expander("🔑 Authentication", expanded=not os.path.exists(ACCESS_TOKEN_FILE)):
        if API_KEY and API_SECRET:
            kite = KiteConnect(api_key=API_KEY)
            if st.button("🔗 Generate Login URL", use_container_width=True):
                st.code(kite.login_url())
            req_token = st.text_input("Request Token")
            if st.button("✅ Save Session", use_container_width=True):
                try:
                    data = kite.generate_session(req_token, api_secret=API_SECRET)
                    with open(ACCESS_TOKEN_FILE, "w") as f: f.write(data["access_token"])
                    st.success("Session Ready!")
                except Exception as e: st.error(str(e))
        else: st.error("Keys missing in .env")

    st.divider()
    
    # Strategy Selection
    st.subheader("🛠️ Core Settings")
    strat = st.selectbox("Strategy", ["GREEN", "RSI"], index=0 if cfg.get('ACTIVE_STRATEGY')=='GREEN' else 1)
    if strat != cfg.get('ACTIVE_STRATEGY'): update_config('ACTIVE_STRATEGY', strat); st.rerun()
    
    tf = st.selectbox("Timeframe", ["minute", "5minute", "15minute", "30minute", "60minute", "day"], index=["minute", "5minute", "15minute", "30minute", "60minute", "day"].index(cfg.get('TIMEFRAME', 'minute')))
    if tf != cfg.get('TIMEFRAME'): update_config('TIMEFRAME', tf); st.rerun()

    qty = st.number_input("Default Quantity", int(cfg.get('DEFAULT_QTY', 1)))
    if qty != int(cfg.get('DEFAULT_QTY', 1)): update_config('DEFAULT_QTY', qty)

    # Performance Config
    with st.expander("📈 Target / SL / Slippage"):
        if strat == "GREEN":
            t = st.number_input("Target %", float(cfg.get('TARGET', 0.5)), step=0.1)
            if t != float(cfg.get('TARGET', 0.5)): update_config('TARGET', t)
            sl = st.number_input("Stoploss %", float(cfg.get('STOPLOSS', 0.5)), step=0.1)
            if sl != float(cfg.get('STOPLOSS', 0.5)): update_config('STOPLOSS', sl)
        else:
            bl = st.number_input("RSI Buy Level", int(cfg.get('BUY_LEVEL', 30)))
            if bl != int(cfg.get('BUY_LEVEL', 30)): update_config('BUY_LEVEL', bl)
            sl_l = st.number_input("RSI Sell Level", int(cfg.get('SELL_LEVEL', 70)))
            if sl_l != int(cfg.get('SELL_LEVEL', 70)): update_config('SELL_LEVEL', sl_l)
        
        st.divider()
        bs = st.number_input("Buy Slippage %", float(cfg.get('BUY_SLIPPAGE', 0.05)), step=0.01)
        if bs != float(cfg.get('BUY_SLIPPAGE', 0.05)): update_config('BUY_SLIPPAGE', bs)
        st.divider()
        ss = st.number_input("Sell Slippage %", float(cfg.get('SELL_SLIPPAGE', 0.05)), step=0.01)
        if ss != float(cfg.get('SELL_SLIPPAGE', 0.05)): update_config('SELL_SLIPPAGE', ss)
        
    # Strategy-Specific Lookback
    lb_key = f"LOOKBACK_DAYS_{strat}"
    lb_val = float(cfg.get(lb_key, 0.5 if strat == "GREEN" else 2.0))
    lb = st.slider(f"Signal Lookback ({strat})", 0.1, 10.0, lb_val, step=0.1)
    if lb != lb_val: update_config(lb_key, lb)

# Helper for PID
def check_pid():
    if "bot_pid" in st.session_state:
        pid = st.session_state["bot_pid"]
        if psutil.pid_exists(pid):
            p = psutil.Process(pid)
            if p.status() != psutil.STATUS_ZOMBIE: return True
    return False

bot_active = check_pid()
bot_running_flag = str(cfg.get('BOT_RUNNING', 'False')).lower() == 'true'

# --- MAIN INTERFACE ---
tab_paper, tab_backtest = st.tabs(["⚡ PAPER TRADING TERMINAL", "📊 EXTENDED BACKTEST LAB"])

# --- TAB 1: PAPER TRADING ---
with tab_paper:
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
    with c1:
        if st.button("▶️ START PAPER", use_container_width=True, type="primary"):
            update_config("BOT_RUNNING", True)
            runner = os.path.join(ROOT_DIR, "main_runner.py")
            proc = subprocess.Popen([sys.executable, runner], cwd=ROOT_DIR)
            st.session_state["bot_pid"] = proc.pid
            st.rerun()
    with c2:
        if st.button("⏸️ STOP SCAN", use_container_width=True):
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
        status_text = "ACTIVE" if (bot_active and bot_running_flag) else ("IDLE (Wait Exits)" if bot_active else "OFFLINE")
        st.markdown(f'<div style="text-align:center; padding:15px; border-radius:10px; background:{status_color}22; border:1px solid {status_color}; color:{status_color}; font-weight:bold; font-size:1.1rem;">{status_text}</div>', unsafe_allow_html=True)

    st.divider()
    col_mon, col_data = st.columns([1.5, 1])
    with col_mon:
        st.subheader("📋 Monitor")
        try:
            conn = mysql.connector.connect(host=cfg.get("DB_HOST", "localhost"), user=cfg.get("DB_USER", "root"), password=cfg.get("DB_PASSWORD", ""), database=cfg.get("DB_NAME", "trading_bot_backtest"))
            df_open = pd.read_sql("SELECT symbol, buyprice, buytime, strategy FROM symbols_state WHERE isExecuted=1", conn)
            st.dataframe(df_open, use_container_width=True, height=350)
            conn.close()
        except: st.error("MySQL Error")
    with col_data:
        st.subheader("📈 Signals")
        cache_file = os.path.join(ROOT_DIR, "live_df_cache.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f: data = pickle.load(f)
            if data:
                sym = st.selectbox("Symbol", list(data.keys()))
                st.dataframe(data[sym].tail(20), use_container_width=True)

# --- TAB 2: EXTENDED BACKTEST ---
with tab_backtest:
    st.subheader("🧪 Professional Backtest Engine")
    c_bt1, c_bt2 = st.columns([1, 2])
    with c_bt1:
        st.write("Select Backtest Range")
        days = st.slider("Historical Days (Extended Range)", 1, 300, 30)
        if st.button("🚀 RUN EXTENDED BACKTEST", use_container_width=True):
            with st.spinner(f"Fetching {days} days of data and simulating..."):
                subprocess.run([sys.executable, os.path.join(ROOT_DIR, "backtest_engine.py"), str(days)], cwd=ROOT_DIR)
            st.success("Analysis Complete!")
            st.rerun()

    with c_bt2:
        st.warning("⚡ EXTENDED MODE: Engine will automatically handle data chunks for ranges over 60 days.")
        st.info("💡 Results will show exact Entry/Exit timestamps and PnL based on the Sidebar configuration.")

    st.divider()
    st.subheader("📜 Historical Trade Log")
    try:
        conn = mysql.connector.connect(host=cfg.get("DB_HOST", "localhost"), user=cfg.get("DB_USER", "root"), password=cfg.get("DB_PASSWORD", ""), database=cfg.get("DB_NAME", "trading_bot_backtest"))
        df_hist = pd.read_sql("SELECT symbol, buytime, buyprice, selltime, sellprice, pnl, reason, strategy FROM trades_log ORDER BY id DESC LIMIT 100", conn)
        st.dataframe(df_hist, use_container_width=True, height=400)
        if not df_hist.empty:
            total_pnl = df_hist['pnl'].sum()
            st.metric("Aggregate Session PnL", f"₹{total_pnl:,.2f}", delta=f"{total_pnl:.2f}")
        conn.close()
    except: st.info("Run an analysis to see history.")

st.caption(f"Sync: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(5)
st.rerun()
