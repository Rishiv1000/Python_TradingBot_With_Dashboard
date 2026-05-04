import streamlit as st
import pandas as pd
import os
import sys
import time
import subprocess
import mysql.connector
from datetime import datetime

# Page Config
st.set_page_config(page_title="Multi-Project Terminal", layout="wide")

# Paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS = {
    "GREEN": {
        "path": os.path.join(ROOT_DIR, "Project_Green"),
        "db_config": "trading_bot_green", # Default, will try to read from config
        "color": "#00ffcc"
    },
    "RSI": {
        "path": os.path.join(ROOT_DIR, "Project_RSI"),
        "db_config": "trading_bot_rsi", # Default
        "color": "#ff4b4b"
    }
}

# Custom CSS
st.markdown("""
    <style>
    .project-header {
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
    }
    .status-badge {
        padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)

def get_project_config(project_name):
    config_path = os.path.join(PROJECTS[project_name]["path"], "db_manager", "config.py")
    config_data = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                if "=" in line and not line.startswith("#"):
                    parts = line.split("=")
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    config_data[key] = val
    return config_data

def update_project_config(project_name, key, value):
    config_path = os.path.join(PROJECTS[project_name]["path"], "db_manager", "config.py")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if line.startswith(f"{key} =") or line.startswith(f"{key}="):
                if isinstance(value, str):
                    new_lines.append(f"{key} = '{value}'\n")
                else:
                    new_lines.append(f"{key} = {value}\n")
            else:
                new_lines.append(line)
        
        with open(config_path, "w") as f:
            f.writelines(new_lines)

def get_db_connection(config_data):
    try:
        # These should be in your .env or root config, but for now we use defaults
        # Better: Dashboard has its own .env for DB credentials
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT_DIR, ".env"))
        
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=config_data.get("DB_NAME", "trading_bot")
        )
        return conn
    except:
        return None

def is_project_running(project_name):
    # Check session state for process
    if f"proc_{project_name}" in st.session_state:
        proc = st.session_state[f"proc_{project_name}"]
        if proc.poll() is None:
            return True
    return False

def start_project(project_name):
    path = PROJECTS[project_name]["path"]
    runner = os.path.join(path, "main_runner.py")
    # Start as subprocess
    # We use sys.executable to ensure same python environment
    proc = subprocess.Popen([sys.executable, runner], cwd=path)
    st.session_state[f"proc_{project_name}"] = proc

def stop_project(project_name):
    if f"proc_{project_name}" in st.session_state:
        proc = st.session_state[f"proc_{project_name}"]
        proc.terminate()
        del st.session_state[f"proc_{project_name}"]

# --- KITE AUTH (Shared across projects) ---
st.sidebar.markdown("### 🔐 Kite Central Auth")
ACCESS_TOKEN_FILE = os.path.join(ROOT_DIR, "access_token.txt")
# Read API keys from root .env
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")

if os.path.exists(ACCESS_TOKEN_FILE):
    with open(ACCESS_TOKEN_FILE, "r") as f:
        token = f.read().strip()
    if token:
        st.sidebar.success("Kite Session Active")
        if st.sidebar.button("Logout / Clear Session"):
            os.remove(ACCESS_TOKEN_FILE)
            st.rerun()
else:
    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=API_KEY)
    st.sidebar.info("No active session found.")
    st.sidebar.markdown(f"[🔗 Get Login URL]({kite.login_url()})")
    req_token = st.sidebar.text_input("Enter Request Token", type="password")
    if st.sidebar.button("Generate Session"):
        try:
            data = kite.generate_session(req_token, api_secret=API_SECRET)
            with open(ACCESS_TOKEN_FILE, "w") as f:
                f.write(data["access_token"])
            st.sidebar.success("Session Saved!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

st.sidebar.divider()

tabs = st.tabs(["🚀 PROJECT GREEN", "🔥 PROJECT RSI"])

for i, p_name in enumerate(["GREEN", "RSI"]):
    with tabs[i]:
        cfg = get_project_config(p_name)
        is_running = is_project_running(p_name)
        
        # Header
        color = PROJECTS[p_name]["color"]
        st.markdown(f"""
            <div class="project-header" style="background: linear-gradient(90deg, #12141e 0%, {color}22 100%); border-left: 5px solid {color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin: 0; color: {color};">Project {p_name}</h2>
                    <span class="status-badge" style="background: {'#00ff0022' if is_running else '#ff000022'}; color: {'#00ff00' if is_running else '#ff0000'}; border: 1px solid {'#00ff00' if is_running else '#ff0000'};">
                        {'● RUNNING' if is_running else '○ STOPPED'}
                    </span>
                </div>
                <p style="color: #999; margin: 5px 0 0 0;">Database: <code>{cfg.get('DB_NAME', 'Unknown')}</code></p>
            </div>
        """, unsafe_allow_html=True)
        
        # Controls
        c1, c2, c3 = st.columns([1, 1, 2])
        if not is_running:
            if c1.button(f"▶️ START {p_name}", use_container_width=True, type="primary"):
                start_project(p_name)
                st.rerun()
        else:
            if c1.button(f"⏹️ STOP {p_name}", use_container_width=True):
                stop_project(p_name)
                st.rerun()
        
        # Quick Config
        with st.expander("⚙️ Strategy Parameters"):
            st.info(f"Edits will take effect after restarting Project {p_name}")
            col1, col2 = st.columns(2)
            
            if p_name == "GREEN":
                t = col1.number_input("Target%", value=float(cfg.get('TARGET', 0.5)), step=0.1, key=f"t_{p_name}")
                if t != float(cfg.get('TARGET', 0.5)): update_project_config(p_name, 'TARGET', t)
                
                sl = col1.number_input("Stoploss%", value=float(cfg.get('STOPLOSS', 0.5)), step=0.1, key=f"sl_{p_name}")
                if sl != float(cfg.get('STOPLOSS', 0.5)): update_project_config(p_name, 'STOPLOSS', sl)
            else:
                rb = col1.number_input("RSI Buy", value=int(cfg.get('BUY_LEVEL', 30)), key=f"rb_{p_name}")
                if rb != int(cfg.get('BUY_LEVEL', 30)): update_project_config(p_name, 'BUY_LEVEL', rb)
                
                rs = col1.number_input("RSI Sell", value=int(cfg.get('SELL_LEVEL', 70)), key=f"rs_{p_name}")
                if rs != int(cfg.get('SELL_LEVEL', 70)): update_project_config(p_name, 'SELL_LEVEL', rs)

        st.divider()
        m1, m2 = st.columns([2, 1])
        with m1:
            st.markdown("### 📡 Live Database View")
            conn = get_db_connection(cfg)
            if conn:
                try:
                    # Show Open Positions
                    st.markdown("**🟢 Active Open Positions**")
                    df_p = pd.read_sql("SELECT symbol, instrument_token, buyprice, buytime FROM symbols_state WHERE isExecuted=1", conn)
                    if not df_p.empty:
                        # Fetch Live PNL for open positions
                        if os.path.exists(ACCESS_TOKEN_FILE):
                            try:
                                with open(ACCESS_TOKEN_FILE, "r") as f: k_token = f.read().strip()
                                from kiteconnect import KiteConnect
                                k_app = KiteConnect(api_key=API_KEY)
                                k_app.set_access_token(k_token)
                                
                                tokens_to_fetch = [int(t) for t in df_p['instrument_token'].tolist() if pd.notna(t)]
                                if tokens_to_fetch:
                                    quotes = k_app.quote(["NSE:" + s for s in df_p['symbol'].tolist()] + [str(t) for t in tokens_to_fetch]) # Try both symbol and token
                                    
                                    live_pnls = []
                                    ltps = []
                                    for idx, row in df_p.iterrows():
                                        token_str = str(row['instrument_token'])
                                        symbol_str = f"NSE:{row['symbol']}"
                                        buy_p = float(row['buyprice'])
                                        ltp = None
                                        if token_str in quotes: ltp = quotes[token_str].get('last_price')
                                        elif symbol_str in quotes: ltp = quotes[symbol_str].get('last_price')
                                        
                                        if ltp and buy_p > 0:
                                            pnl = ((ltp - buy_p) / buy_p) * 100
                                            live_pnls.append(round(pnl, 2))
                                            ltps.append(ltp)
                                        else:
                                            live_pnls.append(None)
                                            ltps.append(None)
                                            
                                    df_p['LTP'] = ltps
                                    df_p['Live PNL %'] = live_pnls
                            except Exception as e: pass # Silently fail and just show without PNL if network issue
                        
                        df_p = df_p.drop(columns=['instrument_token']) # Hide token from UI
                        st.dataframe(df_p, use_container_width=True)
                    else: st.info("No open positions right now")
                    
                    # Show Full Symbols State (DF)
                    with st.expander("📋 View All Tracked Symbols"):
                        df_all = pd.read_sql("SELECT symbol, instrument_token, mode, isExecuted FROM symbols_state", conn)
                        if not df_all.empty: st.dataframe(df_all, use_container_width=True, height=200)
                        else: st.info("No symbols found. Run setup_db & set_defaults first.")

                    # Show Trades Log
                    with st.expander("📜 View Trades Log (History)"):
                        df_log = pd.read_sql("SELECT symbol, buytime, buyprice, selltime, sellprice, pnl, reason FROM trades_log ORDER BY id DESC", conn)
                        if not df_log.empty: st.dataframe(df_log, use_container_width=True)
                        else: st.info("No trades executed yet.")
                        
                    # --- NEW: CANDLE VIEWER (SPYDER IDE STYLE) ---
                    st.markdown("### 🕯️ Live Bot Memory (Spyder View)")
                    st.caption("Auto-refreshes with the exact DF currently in the bot's memory.")
                    cache_file = os.path.join(PROJECTS[p_name]["path"], "live_df_cache.pkl")
                    if os.path.exists(cache_file):
                        try:
                            import pickle
                            with open(cache_file, "rb") as f:
                                bot_df_cache = pickle.load(f)
                            
                            if bot_df_cache:
                                selected_sym = st.selectbox("Select Symbol", list(bot_df_cache.keys()), key=f"sym_{p_name}")
                                df_candles = bot_df_cache[selected_sym]
                                st.dataframe(df_candles.tail(15), use_container_width=True)
                            else:
                                st.info("Bot cache is empty. Waiting for next cycle...")
                        except Exception as e:
                            st.warning(f"Reading cache... Please wait. ({e})")
                    else:
                        st.info("Bot is not running or hasn't completed its first cycle yet.")
                    
                    conn.close()
                except Exception as e: 
                    st.error(f"Database Table Error: {e}. Run setup_db.py for this project.")
            else:
                st.error("Could not connect to project database.")
        
        with m2:
            st.markdown("### 📊 Backtest (Project Level)")
            days = st.number_input("Days to Backtest", min_value=1, max_value=365, value=10, key=f"days_{p_name}")
            if st.button(f"Run Backtest for {p_name}", key=f"bt_btn_{p_name}"):
                st.warning(f"Backtest for {p_name} starting for {days} days...")
                bt_path = os.path.join(PROJECTS[p_name]["path"], "backtest_engine.py")
                # Run backtest_engine.py as a script. 
                # Note: Project backtest_engine.py might need a __main__ block to accept args
                subprocess.run([sys.executable, bt_path, str(days)], cwd=PROJECTS[p_name]["path"])
                st.success(f"Backtest Completed! Check Excel report in {p_name} folder.")

st.caption("Auto-refreshing every 5s...")
time.sleep(5)
st.rerun()
