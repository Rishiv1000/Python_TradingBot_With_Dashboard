import sys
import os
import time
import sqlite3
from datetime import datetime
from order_manager import place_real_buy

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_manager.config as config
from db_manager.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER
from engine_symbol_data import build_symbol_dataframe, fetch_runtime_symbols, fetch_symbol_candles, update_symbol_dataframe_cache

BOT_START_TIME = datetime.now()

class EntryEngine:
    def __init__(self, kite, df_cache, paper_trade=None):
        self.kite = kite
        self.df_cache = df_cache
        self.paper_trade = paper_trade if paper_trade is not None else config.PAPER_TRADE

    def _db_connection(self):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db_manager", f"{config.DB_NAME}.db")
        return sqlite3.connect(db_path)

    def _check_signal(self, df, last_sell_time=None):
        if df is None or len(df) < 2: return False
        effective_start = BOT_START_TIME
        if last_sell_time and last_sell_time > BOT_START_TIME:
            effective_start = last_sell_time
        from engine_symbol_data import _interval_minutes
        from datetime import timedelta
        interval = _interval_minutes(getattr(config, 'TIMEFRAME', 'minute'))
        new_candles = df[df["date"] + timedelta(minutes=interval) > effective_start]
        if len(new_candles) < 2: return False
        last_two_completed = df.iloc[-2:]
        if all(last_two_completed["date"] + timedelta(minutes=interval) > effective_start):
            return all(last_two_completed["candle_color"] == "GREEN")
        return False
 
    def perform_buy(self, symbol, token, exchange, buy_price, buy_time):
        order_id = place_real_buy(self.kite, symbol, quantity=getattr(config, 'DEFAULT_QTY', 1), exchange=exchange)
        if not order_id: return
        
        final_buy_price = buy_price
        # If it's a real order (not blocked by lock), try to get actual fill price
        if not str(order_id).startswith("SIMULATED"):
            try:
                time.sleep(1)
                history = self.kite.order_history(order_id)
                for state in reversed(history):
                    if state["status"] == "COMPLETE" and state.get("average_price"):
                        final_buy_price = float(state["average_price"])
                        break
            except: pass
            
        self._mark_entry(symbol, final_buy_price, buy_time, str(order_id), "MIS", "GREEN")

    def _mark_entry(self, symbol, buy_price, buy_time, order_id, product, strategy_name):
        conn = self._db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE symbols_state SET isExecuted=1, buyprice=?, buytime=?, buy_order_id=?, product=?, strategy=? WHERE symbol=?", (buy_price, buy_time, order_id, product, strategy_name, symbol))
        conn.commit()
        conn.close()

    def run_cycle(self):
        symbol_data_list = fetch_runtime_symbols(self.kite)
        for item in symbol_data_list:
            symbol, token, exchange = item["symbol"], item["token"], item["exchange"]
            conn = self._db_connection(); cursor = conn.cursor()
            cursor.execute("SELECT * FROM symbols_state WHERE symbol=?", (symbol,))
            res = cursor.fetchone()
            if res:
                # SQLite row access
                colnames = [d[0] for d in cursor.description]
                row = dict(zip(colnames, res))
            else: row = None
            conn.close()
            if not row or row["isExecuted"] == 1: continue
            try:
                records = fetch_symbol_candles(self.kite, token, timeframe=getattr(config, 'TIMEFRAME', 'minute'), days=getattr(config, 'LOOKBACK_DAYS_GREEN', 0.5))
                if not records: continue
                new_df = build_symbol_dataframe(records)
                update_symbol_dataframe_cache(self.df_cache, symbol, new_df)
                df = self.df_cache[symbol]
                
                # --- LIVE PROCESSING LOG FOR TERMINAL ---
                last_row = df.iloc[-1]
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                continue
            if self._check_signal(df, last_sell_time=row["last_sell_time"]):
                buy_price = float(df.iloc[-1]["close"])
                buy_time = df.iloc[-1]["date"]
                self.perform_buy(symbol, token, exchange, buy_price, buy_time)
                
        # Dump memory cache for Dashboard (Spyder-like view)
        try:
            import pickle
            cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "live_df_cache.pkl")
            temp_file = cache_file + ".tmp"
            with open(temp_file, "wb") as f:
                pickle.dump(self.df_cache, f)
            os.replace(temp_file, cache_file)
        except Exception as e: pass

def run_entry_cycle(kite, df_cache, paper_trade=None):
    engine = EntryEngine(kite, df_cache, paper_trade)
    return engine.run_cycle()
