import sys
import os
import time
import threading
import importlib
from datetime import datetime

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import db_manager.config as config
from kiteconnect import KiteConnect
from db_manager.config import ACCESS_TOKEN_FILE, API_KEY, API_SECRET

def generate_or_load_session():
    kite = KiteConnect(api_key=API_KEY, timeout=30)
    if os.path.exists(ACCESS_TOKEN_FILE):
        with open(ACCESS_TOKEN_FILE, "r") as f:
            access_token = f.read().strip()
            if access_token:
                kite.set_access_token(access_token)
                try:
                    kite.profile()
                    print(f"✅ Kite session active.")
                    return kite
                except: pass
    print("❌ No valid Kite session. Please login via Dashboard.")
    sys.exit(1)

def smart_sleep(timeframe):
    """Wait until 3 seconds before the next candle boundary."""
    from engine_symbol_data import _interval_minutes
    try:
        interval = _interval_minutes(timeframe)
        now = datetime.now()
        
        # Calculate seconds until next boundary
        total_seconds = now.hour * 3600 + now.minute * 60 + now.second
        next_boundary_seconds = ((total_seconds // (interval * 60)) + 1) * (interval * 60)
        
        sleep_time = next_boundary_seconds - total_seconds - 3 # Wake up 3s early
        
        if sleep_time < 0: # If we are already within the 3s window
            sleep_time = (interval * 60) + sleep_time 
            
        print(f"⏳ Sleeping for {int(sleep_time)}s until next cycle (3s before candle close)...")
        time.sleep(sleep_time)
    except Exception as e:
        print(f"⚠️ Smart Sleep Error: {e}")
        time.sleep(60)

def main():
    print("🚀 Starting Trading Engine...")
    kite = generate_or_load_session()
    
    # Reload config to get latest strategy from Dashboard
    importlib.reload(config)
    strategy = getattr(config, 'ACTIVE_STRATEGY', 'GREEN')
    print(f"📡 Initialized Strategy: {strategy}")

    # --- START EXIT MONITORING (Background) ---
    if strategy == "GREEN":
        from strategies.engine_exit_green import ExitEngineGreen
        exit_engine = ExitEngineGreen(kite)
    else:
        from strategies.engine_exit_rsi import ExitEngineRSI
        exit_engine = ExitEngineRSI(kite)
        
    threading.Thread(target=exit_engine.start_monitoring, daemon=True).start()
    print(f"🛡️ Exit Monitor active for {strategy}")

    # --- ENTRY LOOP ---
    df_cache = {}
    import pickle
    while True:
        try:
            # Check for strategy changes dynamically
            importlib.reload(config)
            current_strategy = getattr(config, 'ACTIVE_STRATEGY', 'GREEN')
            is_running = str(getattr(config, 'BOT_RUNNING', 'True')).lower() == 'true'
            
            if is_running:
                if current_strategy == "GREEN":
                    from strategies.engine_entry_green import run_entry_cycle
                    run_entry_cycle(kite, df_cache)
                else:
                    from strategies.engine_entry_rsi import run_entry_cycle_rsi
                    run_entry_cycle_rsi(kite, df_cache)
                
                # --- SAVE CACHE FOR DASHBOARD ---
                try:
                    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_df_cache.pkl")
                    with open(cache_file, "wb") as f:
                        pickle.dump(df_cache, f)
                except: pass
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot is STOPPED (Graceful). Scanning skipped.")
            
            # Smart Wait
            smart_sleep(getattr(config, "TIMEFRAME", 'minute'))
            
        except Exception as e:
            print(f"⚠️ Error in cycle: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
