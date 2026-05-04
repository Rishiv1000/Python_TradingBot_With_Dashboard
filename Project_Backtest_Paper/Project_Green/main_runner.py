import sys
import os
import time
import threading
from datetime import datetime

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import db_manager.config as config
from kiteconnect import KiteConnect
from db_manager.config import ACCESS_TOKEN_FILE, API_KEY, API_SECRET

df_cache = {}

def get_login_url():
    kite = KiteConnect(api_key=API_KEY)
    return kite.login_url()

def generate_or_load_session(allow_interact=False):
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

    # If no valid session and interaction is allowed, try console login
    if allow_interact:
        print(f"\n🔑 No valid Kite session found.")
        print(f"1. Open this URL in your browser: {kite.login_url()}")
        request_token = input("2. Enter the Request Token from the URL: ").strip()
        
        if request_token:
            try:
                data = kite.generate_session(request_token, api_secret=API_SECRET)
                access_token = data["access_token"]
                with open(ACCESS_TOKEN_FILE, "w") as f:
                    f.write(access_token)
                kite.set_access_token(access_token)
                print("✅ Session generated successfully via console!")
                return kite
            except Exception as e:
                print(f"❌ Failed to generate session: {e}")

    raise ConnectionError("No valid Kite session found. Please login via Dashboard or Console.")
def main():
    print("Starting Kite Automated Trading Bot (GREEN)...")
    kite = generate_or_load_session(allow_interact=False)
    paper_trade = config.PAPER_TRADE
    
    from engine_entry import EntryEngine
    from engine_exit import ExitEngine
    entry_engine_class = EntryEngine
    exit_engine_class = ExitEngine

    target = getattr(config, "TARGET", 0.5)
    sl = getattr(config, "STOPLOSS", 0.5)
    exit_engine_inst = exit_engine_class(kite, paper_trade, target_pct=target, stoploss_pct=sl)
    threading.Thread(target=exit_engine_inst.start_monitoring, daemon=True).start()
    
    # Entry Loop
    global df_cache
    engine = entry_engine_class(kite, df_cache, paper_trade)
    while True:
        if config.BOT_RUNNING:
            from engine_symbol_data import _interval_minutes
            timeframe = getattr(config, "TIMEFRAME", 'minute')
            interval = _interval_minutes(timeframe)
            engine.run_cycle()
            wait_time = (interval * 60) + 2
            for i in range(int(wait_time), 0, -1):
                if not config.BOT_RUNNING: break
                msg = f"[GREEN] [{timeframe}] Waiting... {i}s"
                config.BOT_STATUS = msg
                sys.stdout.write(f"\r{msg} ")
                sys.stdout.flush()
                time.sleep(1)
            config.BOT_STATUS = "Processing..."
            sys.stdout.write("\n")
        else: time.sleep(2)

if __name__ == "__main__":
    config.BOT_RUNNING = True
    main()
