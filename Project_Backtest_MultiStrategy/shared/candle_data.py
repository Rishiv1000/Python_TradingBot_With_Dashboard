from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

def search_kite_symbol(kite, exchange, symbol):
    try:
        instrument = f"{exchange.upper()}:{symbol.upper()}"
        data = kite.ltp(instrument)
        if instrument in data:
            return data[instrument]["instrument_token"]
    except Exception as e:
        print(f"Search failed for {symbol}: {e}")
    return None

def interval_minutes(timeframe):
    if timeframe == "minute":
        return 1
    if timeframe.endswith("minute"):
        return int(timeframe.replace("minute", ""))
    if timeframe == "day":
        return 24 * 60
    raise ValueError(f"Unsupported timeframe: {timeframe}")

def last_closed_candle_time(timeframe):
    now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(second=0, microsecond=0)
    interval = interval_minutes(timeframe)
    midnight = now.replace(hour=0, minute=0)
    elapsed_minutes = int((now - midnight).total_seconds() // 60)
    bucket = (elapsed_minutes // interval) * interval
    return midnight + timedelta(minutes=bucket)

def fetch_symbol_candles(kite, token, days, timeframe):
    to_date = last_closed_candle_time(timeframe)
    from_date = to_date - timedelta(days=days)
    rows = []

    while True:
        if from_date.date() >= (datetime.now().date() - timedelta(days=100)):
            chunk = kite.historical_data(token, from_date, datetime.now(), timeframe)
            if chunk:
                rows.extend(chunk)
            break

        current_to = from_date + timedelta(days=100)
        chunk = kite.historical_data(token, from_date, current_to, timeframe)
        if chunk:
            rows.extend(chunk)
        from_date = current_to

    return rows

def build_symbol_dataframe(records):
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df

def update_symbol_dataframe_cache(cache, symbol, df, rows=200):
    if df.empty:
        return cache.get(symbol, pd.DataFrame())
    if symbol in cache and not cache[symbol].empty:
        merged = pd.concat([cache[symbol], df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
        cache[symbol] = merged.tail(rows)
    else:
        cache[symbol] = df.tail(rows).reset_index(drop=True)
    return cache[symbol]
