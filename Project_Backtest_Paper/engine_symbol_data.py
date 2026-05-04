from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import mysql.connector
import os
import sys

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_manager.config import LIVE_EXCHANGE, MAX_SYMBOLS_PER_CYCLE, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import db_manager.config as config

def fetch_runtime_symbols(kite):
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT symbol, instrument_token as token, exchange FROM symbols_state")
    rows = cursor.fetchall()
    conn.close()
    return rows

def search_kite_symbol(kite, exchange, symbol):
    try:
        instrument_str = f"{exchange.upper()}:{symbol.upper()}"
        data = kite.ltp(instrument_str)
        if instrument_str in data:
            return data[instrument_str]["instrument_token"]
    except Exception as e:
        print(f"⚠️ Search failed for {symbol}: {e}")
    return None

def _interval_minutes(timeframe):
    if timeframe == "minute": return 1
    if timeframe.endswith("minute"): return int(timeframe.replace("minute", ""))
    if timeframe == "day": return 24 * 60
    raise ValueError(f"Unsupported timeframe: {timeframe}")

def _last_closed_candle_time(timeframe):
    now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(second=0, microsecond=0)
    interval = _interval_minutes(timeframe)
    midnight = now.replace(hour=0, minute=0)
    elapsed_minutes = int((now - midnight).total_seconds() // 60)
    bucket = (elapsed_minutes // interval) * interval
    last_closed = midnight + timedelta(minutes=bucket)
    return last_closed

def fetch_symbol_candles(kite, token, days=None, timeframe=None):
    if days is None: days = getattr(config, 'LOOKBACK_DAYS_GREEN', 2.0)
    if timeframe is None: timeframe = getattr(config, 'TIMEFRAME', 'minute')
    
    to_date = _last_closed_candle_time(timeframe)
    from_date = to_date - timedelta(days=days)
    
    data_list = []
    while True:
        if from_date.date() >= (datetime.now().date() - timedelta(days=100)):
            chunk = kite.historical_data(token, from_date, datetime.now(), timeframe)
            if chunk: data_list.extend(chunk)
            break
        else:
            current_to = from_date + timedelta(days=100)
            chunk = kite.historical_data(token, from_date, current_to, timeframe)
            if chunk: data_list.extend(chunk)
            from_date = current_to
            
    return data_list

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def build_symbol_dataframe(records):
    if not records: return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = (pd.to_datetime(df["date"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None))
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    
    # Calculate RSI
    df = calculate_rsi(df)

    def calculate_color(row):
        diff = row["close"] - row["open"]
        if diff > 0: return "GREEN"
        elif diff < 0: return "RED"
        else: return "DOJI"
    df["candle_color"] = df.apply(calculate_color, axis=1)
    return df

def update_symbol_dataframe_cache(cache, symbol, df):
    if df.empty: return cache.get(symbol, pd.DataFrame())
    if symbol in cache and not cache[symbol].empty:
        merged = pd.concat([cache[symbol], df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
        cache[symbol] = merged.tail(2)
    else:
        cache[symbol] = df.tail(2).reset_index(drop=True)
    return cache[symbol]
