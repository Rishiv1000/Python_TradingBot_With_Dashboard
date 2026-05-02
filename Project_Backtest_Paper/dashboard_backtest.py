import streamlit as st
import pandas as pd
import os
import sys
import time
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path: sys.path.append(PROJECT_ROOT)

import db_manager.config as config
from main_runner import generate_or_load_session, get_login_url

# Page Config
st.set_page_config(page_title="Backtest & Paper Trading", layout="wide")

# UI Layout
st.title("🧪 Backtest & Paper Trading Dashboard")

col_df = st.container()

# Sidebar
with st.sidebar:
    st.header("🔑 Authentication")
    authenticated = False
    try:
        if os.path.exists(config.ACCESS_TOKEN_FILE):
            if 'kite_session' not in st.session_state:
                st.session_state.kite_session = generate_or_load_session()
            authenticated = True
    except: authenticated = False

    if authenticated:
        st.success("✅ Authenticated")
        if st.button("Logout"):
            if 'kite_session' in st.session_state: del st.session_state.kite_session
            if os.path.exists(config.ACCESS_TOKEN_FILE): os.remove(config.ACCESS_TOKEN_FILE)
            st.rerun()
    else:
        st.markdown(f"[🔗 Login with Kite]({get_login_url()})")
        token = st.text_input("Request Token", type="password")
        if st.button("Generate Session"):
            try:
                from kiteconnect import KiteConnect
                kite = KiteConnect(api_key=config.API_KEY)
                data = kite.generate_session(token, api_secret=config.API_SECRET)
                with open(config.ACCESS_TOKEN_FILE, "w") as f:
                    f.write(data["access_token"])
                st.success("✅ Logged In Successfully!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.divider()
    st.subheader("Paper Bot Controls")
    import threading
    from main_runner import main as run_paper_bot, df_cache
    
    timeframes = ["minute", "3minute", "5minute", "10minute", "15minute", "30minute", "60minute", "day"]
    current_idx = timeframes.index(getattr(config, 'TIMEFRAME', 'minute')) if getattr(config, 'TIMEFRAME', 'minute') in timeframes else 0
    config.TIMEFRAME = st.selectbox("⏱️ Timeframe", timeframes, index=current_idx)
    
    st.markdown("### Bot Parameters")
    config.TARGET_PCT = st.number_input("Target (%)", value=float(getattr(config, 'TARGET_PCT', 0.5)), step=0.1)
    config.STOPLOSS_PCT = st.number_input("Stoploss (%)", value=float(getattr(config, 'STOPLOSS_PCT', 0.5)), step=0.1)
    config.SLIPPAGE_PCT = st.number_input("Slippage (%)", value=float(getattr(config, 'SLIPPAGE_PCT', 0.05)), step=0.01, format="%.2f")
    config.BUY_SLIPPAGE_BUFFER = st.number_input("Buy Buffer (%)", value=float(getattr(config, 'BUY_SLIPPAGE_BUFFER', 0.05)), step=0.01, format="%.2f")
    config.SELL_SLIPPAGE_BUFFER = st.number_input("Sell Buffer (%)", value=float(getattr(config, 'SELL_SLIPPAGE_BUFFER', 0.05)), step=0.01, format="%.2f")
    
    with st.expander("⚙️ Advanced / Secret Settings"):
        config.PAPER_TRADE = st.toggle("🧪 Paper Trade Mode", value=getattr(config, 'PAPER_TRADE', True))
        config.DEFAULT_QTY = st.number_input("Default Quantity", value=int(getattr(config, 'DEFAULT_QTY', 1)), step=1)
        config.MAX_SYMBOLS_PER_CYCLE = st.number_input("Max Symbols / Cycle", value=int(getattr(config, 'MAX_SYMBOLS_PER_CYCLE', 100)), step=10)
        config.CANDLE_LOOKBACK_DAYS = st.number_input("Candle Lookback (Days)", value=float(getattr(config, 'CANDLE_LOOKBACK_DAYS', 0.05)), step=0.01, format="%.2f")

    
    status_msg = getattr(config, 'BOT_STATUS', 'Idle')
    st.info(f"**Status:** {status_msg}")
    
    if st.button("🚀 Start Paper Bot", key="start_btn"):
        try:
            generate_or_load_session()
            config.BOT_RUNNING = True
            if not getattr(config, 'bot_thread', None) or not config.bot_thread.is_alive():
                config.bot_thread = threading.Thread(target=run_paper_bot, daemon=True)
                config.bot_thread.start()
                st.toast("Paper Bot Started Successfully!")
            else:
                st.toast("Bot is already active and resumed!")
        except Exception as e:
            st.error(f"Error: {e}")
    
    if st.button("🛑 Stop Paper Bot", key="stop_btn"):
        config.BOT_RUNNING = False
        st.toast("Bot Stopping...")

with col_df:
    tab1, tab2 = st.tabs(["📄 Paper Trading", "📊 Backtesting"])
    
    with tab1:
        st.subheader("📌 Paper Open Positions")
        try:
            import mysql.connector
            conn = mysql.connector.connect(host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB_NAME)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT symbol, buyprice, buytime, product, mode FROM symbols_state WHERE isExecuted=1 AND mode='PAPER'")
            df_open = pd.DataFrame(cursor.fetchall())
            if not df_open.empty:
                st.dataframe(df_open, width='stretch')
            else:
                st.info("No open paper positions.")
                
            st.markdown("### 📜 Today's Paper Trades")
            cursor.execute("SELECT symbol, buyprice, sellprice, pnl, reason, selltime FROM trades_log WHERE mode='PAPER' ORDER BY selltime DESC LIMIT 10")
            df_closed = pd.DataFrame(cursor.fetchall())
            if not df_closed.empty:
                st.dataframe(df_closed, width='stretch')
                st.metric("Paper Total PnL", f"{df_closed['pnl'].sum():.2f}")
            else:
                st.info("No paper trades closed today.")
            conn.close()
        except Exception as e:
            st.error(f"Database Error: {e}")
            
        st.divider()
        st.subheader("Internal DataFrames Cache")
        if 'df_cache' in globals() and df_cache:
            selected_symbol = st.selectbox("Select Symbol:", list(df_cache.keys()))
            if selected_symbol:
                st.dataframe(df_cache[selected_symbol].tail(20), width='stretch')
        else:
            st.info("No cache data. Start the bot first.")

    with tab2:
        st.subheader("📊 Backtest Results & DataFrames")
        days = st.slider("Days", 1, 30, 5)
        if st.button("🚀 Run Backtest"):
            with st.spinner("Running simulation..."):
                from backtest_engine import run_backtest
                results = run_backtest(days=days)
                st.session_state.bt_results = results
                st.success("Complete!")

        if 'bt_results' in st.session_state and st.session_state.bt_results:
            df_res = pd.DataFrame(st.session_state.bt_results)
            
            # Summary Metrics
            s_col1, s_col2, s_col3 = st.columns(3)
            s_col1.metric("Total Trades", len(df_res))
            s_col2.metric("Win Rate", f"{(len(df_res[df_res['pnl'] > 0]) / len(df_res) * 100):.2f}%")
            s_col3.metric("Net PnL", f"{df_res['pnl'].sum():.2f}")
            
            # Download Button
            report_path = os.path.join(PROJECT_ROOT, "backtest_report.xlsx")
            if os.path.exists(report_path):
                with open(report_path, "rb") as f:
                    st.download_button(label="📥 Download Excel Report", data=f, file_name="backtest_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            st.subheader("All Trades")
            st.dataframe(df_res, width='stretch')



# Auto-refresh
time.sleep(2)
st.rerun()
