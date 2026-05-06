import mysql.connector
import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(STRATEGY_DIR)
sys.path.append(ROOT_DIR)

import config
from shared.candle_data import (
    build_symbol_dataframe,
    fetch_symbol_candles,
    update_symbol_dataframe_cache,
)

# ── In-memory symbol cache ────────────────────────────────────────────────────
RELOAD_SIGNAL_FILE = os.path.join(STRATEGY_DIR, ".reload_symbols")
_symbol_cache = []
_cache_loaded = False


def _load_symbols_from_db():
    global _symbol_cache, _cache_loaded
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT symbol, instrument_token as token, exchange FROM symbols_green LIMIT %s",
        (getattr(config, "MAX_SYMBOLS_PER_CYCLE", 50),)
    )
    _symbol_cache = cursor.fetchall()
    conn.close()
    _cache_loaded = True
    print(f"[GREEN] Symbol cache loaded: {[s['symbol'] for s in _symbol_cache]}")
    return _symbol_cache


def fetch_runtime_symbols(kite):
    global _cache_loaded
    if os.path.exists(RELOAD_SIGNAL_FILE):
        try:
            os.remove(RELOAD_SIGNAL_FILE)
        except Exception:
            pass
        _cache_loaded = False
        print("[GREEN] Symbol cache reload triggered.")
    if not _cache_loaded:
        _load_symbols_from_db()
    return _symbol_cache


def calculate_candle_color(df):
    if df.empty: return df
    df["candle_color"] = "DOJI"
    df.loc[df["close"] > df["open"], "candle_color"] = "GREEN"
    df.loc[df["close"] < df["open"], "candle_color"] = "RED"
    return df


def build_green_dataframe(kite, token):
    records = fetch_symbol_candles(
        kite,
        token,
        days=getattr(config, 'LOOKBACK_DAYS_GREEN', 3.0),
        timeframe=getattr(config, 'TIMEFRAME', 'minute')
    )
    df = build_symbol_dataframe(records)
    df = calculate_candle_color(df)
    return df
