import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import mysql.connector

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db_manager.config as config
from main_runner import generate_or_load_session
from engine_symbol_data import build_symbol_dataframe, fetch_runtime_symbols

backtest_data_cache = {}

def fetch_extended_candles(kite, token, days, timeframe):
    """Fetches historical data in chunks to bypass Kite API limits for extended backtests."""
    all_records = []
    end_date = datetime.now()
    remaining_days = days
    
    # Chunk size: 30 days is safe for most timeframes
    chunk_size = 30
    
    while remaining_days > 0:
        current_chunk = min(remaining_days, chunk_size)
        start_date = end_date - timedelta(days=current_chunk)
        
        try:
            records = kite.historical_data(token, start_date, end_date, timeframe)
            if records:
                # Add to start of list (since we are moving backwards)
                all_records = records + all_records
            
            end_date = start_date # Move window back
            remaining_days -= current_chunk
        except Exception as e:
            print(f"Error fetching chunk: {e}")
            break
            
    return all_records

class EntryEngineSim:
    def __init__(self, strategy_type):
        self.strategy_type = strategy_type
        
    def check_signal(self, df, i, symbol):
        if i < 2: return False
        if self.strategy_type == "GREEN":
            prev2, prev1 = df.iloc[i - 2], df.iloc[i - 1]
            if prev2["candle_color"] == "GREEN" and prev1["candle_color"] == "GREEN": return True
        elif self.strategy_type == "RSI":
            cur_candle = df.iloc[i]
            buy_level = int(getattr(config, 'BUY_LEVEL', 30))
            if 'rsi' in df.columns and pd.notna(cur_candle['rsi']):
                if cur_candle['rsi'] < buy_level: return True
        return False

class ExitEngineSim:
    def __init__(self, target_pct, stoploss_pct, slippage_pct):
        self.target_pct, self.stoploss_pct, self.slippage_pct = target_pct, stoploss_pct, slippage_pct
    
    def check_exit(self, position, cur_candle, df=None, i=None, strategy_type="GREEN"):
        buy_price = float(position["buyprice"])
        qty = int(getattr(config, 'DEFAULT_QTY', 1))
        
        if strategy_type == "GREEN":
            target_price = buy_price * (1 + self.target_pct / 100)
            sl_price = buy_price * (1 - self.stoploss_pct / 100)
            if float(cur_candle["high"]) >= target_price:
                return self._format_result(position, cur_candle, target_price, "TARGET", qty)
            if float(cur_candle["low"]) <= sl_price:
                return self._format_result(position, cur_candle, sl_price, "SL", qty)
                
        elif strategy_type == "RSI":
            sell_level = int(getattr(config, 'SELL_LEVEL', 70))
            if df is not None and i is not None and 'rsi' in df.columns:
                if pd.notna(cur_candle['rsi']) and cur_candle['rsi'] > sell_level:
                    return self._format_result(position, cur_candle, float(cur_candle["close"]), "RSI_EXIT", qty)
        return None

    def _format_result(self, position, cur_candle, raw_sell, reason, qty):
        buy_price = float(position["buyprice"])
        sell_price = raw_sell * (1 - (self.slippage_pct / 100))
        return {
            "symbol": position["symbol"],
            "buytime": position["buytime"],
            "buyprice": buy_price,
            "selltime": cur_candle["date"],
            "sellprice": sell_price,
            "pnl": (sell_price - buy_price) * qty,
            "reason": reason,
            "strategy": getattr(config, 'ACTIVE_STRATEGY', 'GREEN')
        }

def run_backtest(days=10):
    kite = generate_or_load_session()
    symbols = fetch_runtime_symbols(kite)
    
    active_strat = getattr(config, "ACTIVE_STRATEGY", "GREEN")
    lb_key = f"LOOKBACK_DAYS_{active_strat}"
    if days is None: days = float(getattr(config, lb_key, 0.5 if active_strat == "GREEN" else 2.0))
    entry_engine = EntryEngineSim(active_strat)
    
    target = float(getattr(config, "TARGET", 0.5))
    sl = float(getattr(config, "STOPLOSS", 0.5))
    slip = float(getattr(config, "SELL_SLIPPAGE", 0.05))
    timeframe = getattr(config, "TIMEFRAME", "minute")
    
    exit_engine = ExitEngineSim(target, sl, slip)
    all_results = []
    
    for item in symbols:
        symbol, token = item["symbol"], item["token"]
        print(f"Analyzing {symbol} for {days} days...")
        try:
            records = fetch_extended_candles(kite, token, days, timeframe)
            if not records: continue
            df = build_symbol_dataframe(records)
            backtest_data_cache[symbol] = df
        except Exception as e: 
            print(f"Error {symbol}: {e}"); continue

        position = None
        for i in range(len(df)):
            cur_candle = df.iloc[i]
            if position is None:
                if entry_engine.check_signal(df, i, symbol):
                    buy_price = float(cur_candle["close"]) * (1 + float(getattr(config, 'BUY_SLIPPAGE', 0.05))/100)
                    position = {"symbol": symbol, "buytime": cur_candle["date"], "buyprice": buy_price}
            else:
                trade_result = exit_engine.check_exit(position, cur_candle, df=df, i=i, strategy_type=active_strat)
                if trade_result: 
                    all_results.append(trade_result)
                    position = None
    
    # Save to database
    try:
        conn = mysql.connector.connect(host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD, database=config.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trades_log WHERE mode='BACKTEST' OR mode IS NULL") # Clear old backtest log
        for r in all_results:
            cursor.execute("INSERT INTO trades_log (symbol, buytime, buyprice, selltime, sellprice, pnl, reason, strategy) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (r["symbol"], r["buytime"], r["buyprice"], r["selltime"], r["sellprice"], r["pnl"], r["reason"], r["strategy"]))
        conn.commit(); conn.close()
    except Exception as e: print(f"DB Error: {e}")

    return all_results

if __name__ == "__main__":
    test_days = 10
    if len(sys.argv) > 1:
        try: test_days = int(sys.argv[1])
        except: pass
    run_backtest(days=test_days)
