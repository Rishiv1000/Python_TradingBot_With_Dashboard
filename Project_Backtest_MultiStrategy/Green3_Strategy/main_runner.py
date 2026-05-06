import importlib
import os
import sys
import threading
import time
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.insert(0, STRATEGY_DIR)
sys.path.insert(0, PROJECT_ROOT)

try:
    from shared.terminal_capture import start_strategy_capture, stop_strategy_capture
except ImportError:
    def start_strategy_capture(name): pass
    def stop_strategy_capture(name): pass

import config
from shared.kite_session import generate_or_load_session
from engine_entry import EntryEngineGreen3
from engine_exit import ExitEngineGreen3
from shared.candle_data import interval_minutes

def smart_sleep():
    timeframe = getattr(config, "TIMEFRAME", "minute")
    interval = interval_minutes(timeframe)
    now = datetime.now()
    total_seconds = now.hour * 3600 + now.minute * 60 + now.second
    next_boundary = ((total_seconds // (interval * 60)) + 1) * (interval * 60)
    sleep_time = max(1, next_boundary - total_seconds - 3)
    print(f"😴 [GREEN3] Sleeping {int(sleep_time)}s until next candle.")
    time.sleep(sleep_time)

def main():
    print("🚀 Starting GREEN3 Strategy Runner (3 Green Candles / Paper)...")
    start_strategy_capture("GREEN3")
    try:
        kite = generate_or_load_session(config.API_KEY, config.ACCESS_TOKEN_FILE)
        if not kite:
            return

        exit_engine = ExitEngineGreen3(kite)
        threading.Thread(target=exit_engine.start_monitoring, daemon=True).start()

        df_cache = {}
        entry_engine = EntryEngineGreen3(kite, df_cache)

        while True:
            try:
                importlib.reload(config)
                if str(getattr(config, 'BOT_RUNNING', 'True')).lower() == 'true':
                    entry_engine.run_cycle()
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [GREEN3] Paused.")
                smart_sleep()
            except Exception as e:
                err = str(e)
                print(f"⚠️ [GREEN3] Runner Error: {err}")
                if any(x in err for x in ["Unknown database", "Access denied", "No valid Kite"]):
                    print(f"❌ [GREEN3] Fatal error — stopping strategy.")
                    return
                time.sleep(10)
    finally:
        stop_strategy_capture("GREEN3")

if __name__ == "__main__":
    main()
