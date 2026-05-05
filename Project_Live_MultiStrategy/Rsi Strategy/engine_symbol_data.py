import sqlite3
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from db_manager import config
from shared.candle_data import (
    build_symbol_dataframe,
    fetch_symbol_candles,
    interval_minutes,
    search_kite_symbol,
    update_symbol_dataframe_cache,
)


def calculate_rsi(df, period=14):
    if df.empty or len(df) < period:
        return df
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def fetch_runtime_symbols(kite):
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, instrument_token AS token, exchange
        FROM symbols_state
        LIMIT ?
    """, (getattr(config, "MAX_SYMBOLS_PER_CYCLE", 50),))
    rows = [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    conn.close()
    return rows


def build_rsi_dataframe(kite, token):
    records = fetch_symbol_candles(
        kite,
        token,
        days=getattr(config, "LOOKBACK_DAYS", 2.0),
        timeframe=getattr(config, "TIMEFRAME", "minute"),
    )
    df = build_symbol_dataframe(records)
    return calculate_rsi(df, period=getattr(config, "PERIOD", 14))
