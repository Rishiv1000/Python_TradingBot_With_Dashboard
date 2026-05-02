import sys
import os
import time
import threading
from datetime import datetime

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import db_manager.config as config
from entry_engine import EntryEngine
from exit_engine import ExitEngine
from kiteconnect import KiteConnect
from db_manager.config import ACCESS_TOKEN_FILE, API_KEY, API_SECRET

def get_login_url():
    kite = KiteConnect(api_key=API_KEY)
    return kite.login_url()

def generate_or_load_session():
    kite = KiteConnect(api_key=API_KEY, timeout=30)
    
    if os.path.exists(ACCESS_TOKEN_FILE):
        with open(ACCESS_TOKEN_FILE, "r") as f:
            access_token = f.read().strip()
            if access_token:
                kite.set_access_token(access_token)
                try:
                    profile = kite.profile()
                    print(f"Kite session valid for: {profile.get('user_name')}")
                    return kite
                except Exception as e:
                    print(f"Session check failed: {e}")

    raise ConnectionError("No valid Kite session found. Please login via Dashboard.")
from entry_engine import EntryEngine
from exit_engine import ExitEngine

df_cache = {}

def _entry_loop(kite, paper_trade):
    global df_cache
    engine = EntryEngine(kite, df_cache, paper_trade)
    while True:
        if config.BOT_RUNNING:
            from engine_symbol_data import _interval_minutes
            interval = _interval_minutes()
            engine.run_cycle()
            wait_time = (interval * 60) + 2
            for i in range(int(wait_time), 0, -1):
                if not config.BOT_RUNNING: break
                msg = f"Waiting for next candle... {i}s left"
                config.BOT_STATUS = msg
                sys.stdout.write(f"\r{msg} ")
                sys.stdout.flush()
                time.sleep(1)
            config.BOT_STATUS = "Processing..."
            sys.stdout.write("\n")
        else: time.sleep(2)

def main():
    print("Starting Kite Automated Trading Bot (LIVE)...")
    kite = generate_or_load_session()
    paper_trade = getattr(config, 'PAPER_TRADE', False)
    exit_engine = ExitEngine(kite, paper_trade)
    threading.Thread(target=exit_engine.start_monitoring, daemon=True).start()
    _entry_loop(kite, paper_trade)

if __name__ == "__main__":
    main()
