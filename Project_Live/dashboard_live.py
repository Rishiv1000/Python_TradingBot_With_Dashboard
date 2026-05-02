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
st.set_page_config(page_title="Live Trading Bot", layout="wide")

# UI Layout
st.title("💹 Live Trading Dashboard (Real Money)")

col_df = st.container()

# Sidebar
with st.sidebar:
    st.header("🔐 Secure Auth")
    authenticated = False
    try:
        if os.path.exists(config.ACCESS_TOKEN_FILE):
            if 'kite_session' not in st.session_state:
                st.session_state.kite_session = generate_or_load_session()
            authenticated = True
    except: authenticated = False

    if authenticated:
        st.success("✅ LIVE Session Active")
        if st.button("Logout"):
            if 'kite_session' in st.session_state: del st.session_state.kite_session
            if os.path.exists(config.ACCESS_TOKEN_FILE): os.remove(config.ACCESS_TOKEN_FILE)
            st.rerun()
    else:
        st.error("⚠️ Login Required for Live")
        st.markdown(f"[🔗 Live Login]({get_login_url()})")
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
    st.subheader("Bot Controls")
    import threading
    from main_runner import main as run_live_bot, df_cache
    
    status_msg = getattr(config, 'BOT_STATUS', 'Idle')
    st.info(f"**Status:** {status_msg}")
    
    if st.button("🚀 Start Live Bot", key="start_btn"):
        try:
            generate_or_load_session()
            config.BOT_RUNNING = True
            if not getattr(config, 'bot_thread', None) or not config.bot_thread.is_alive():
                config.bot_thread = threading.Thread(target=run_live_bot, daemon=True)
                config.bot_thread.start()
                st.toast("Bot Started Successfully!")
            else:
                st.toast("Bot is already active and resumed!")
        except Exception as e:
            st.error(f"Authentication Error: {e}")
    
    if st.button("🛑 Stop Live Bot", key="stop_btn"):
        config.BOT_RUNNING = False
        st.toast("Bot Stopping...")

with col_df:
    st.subheader("📌 Open Positions")
    try:
        import mysql.connector
        conn = mysql.connector.connect(host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB_NAME)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT symbol, buyprice, buytime, product FROM symbols_state WHERE isExecuted=1")
        df_open = pd.DataFrame(cursor.fetchall())
        if not df_open.empty:
            st.dataframe(df_open, width='stretch')
        else:
            st.info("No open positions.")
            
        st.markdown("### 📜 Today's Closed Trades")
        cursor.execute("SELECT symbol, buyprice, sellprice, pnl, reason, selltime FROM trades_log ORDER BY selltime DESC LIMIT 10")
        df_closed = pd.DataFrame(cursor.fetchall())
        if not df_closed.empty:
            st.dataframe(df_closed, width='stretch')
            st.metric("Today's Total PnL", f"{df_closed['pnl'].sum():.2f}")
        else:
            st.info("No trades closed today.")
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



# Auto-refresh
time.sleep(2)
st.rerun()
