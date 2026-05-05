import importlib
import os
import sys
import threading
import time
from datetime import datetime

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.insert(0, STRATEGY_DIR)
sys.path.insert(0, BASE_DIR)

from kiteconnect import KiteConnect

from db_manager import config
from db_manager.setup_db import setup_database
from engine_entry import EntryEngine
from engine_exit import ExitEngine
from shared.candle_data import interval_minutes


def generate_or_load_session():
    kite = KiteConnect(api_key=config.API_KEY, timeout=30)
    if os.path.exists(config.ACCESS_TOKEN_FILE):
        with open(config.ACCESS_TOKEN_FILE, "r") as f:
            access_token = f.read().strip()
        if access_token:
            kite.set_access_token(access_token)
            try:
                kite.profile()
                print("Kite session active.")
                return kite
            except Exception:
                pass
    raise ConnectionError("No valid Kite session. Login from dashboard first.")


def smart_sleep():
    timeframe = getattr(config, "TIMEFRAME", "minute")
    interval = interval_minutes(timeframe)
    now = datetime.now()
    total_seconds = now.hour * 3600 + now.minute * 60 + now.second
    next_boundary = ((total_seconds // (interval * 60)) + 1) * (interval * 60)
    sleep_time = max(1, next_boundary - total_seconds - 3)
    print(f"[GREEN] Sleeping {int(sleep_time)}s.")
    time.sleep(sleep_time)


def main():
    print("Starting GREEN strategy project...")
    setup_database()
    kite = generate_or_load_session()

    exit_engine = ExitEngine(kite)
    threading.Thread(target=exit_engine.start_monitoring, daemon=True).start()

    df_cache = {}
    entry_engine = EntryEngine(kite, df_cache)

    while True:
        importlib.reload(config)
        entry_engine.run_cycle()
        smart_sleep()


if __name__ == "__main__":
    main()
