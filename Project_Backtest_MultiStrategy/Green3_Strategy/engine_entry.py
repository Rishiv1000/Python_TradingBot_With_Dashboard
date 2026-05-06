import sys
import os
import time
import mysql.connector
from datetime import datetime, timedelta
import pickle

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(STRATEGY_DIR, ".."))
sys.path.append(STRATEGY_DIR)
sys.path.append(ROOT_DIR)

import config
from shared.candle_data import build_symbol_dataframe, fetch_symbol_candles, update_symbol_dataframe_cache, interval_minutes

BOT_START_TIME = datetime.now()

class EntryEngineGreen3:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache

    def _db_connection(self):
        return mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )

    def _check_signal(self, df, last_sell_time=None):
        """Signal: last 3 completed candles must ALL be GREEN."""
        if df is None or len(df) < 4: return False
        completed = df.iloc[-4:-1]
        def get_color(row):
            return "GREEN" if row["close"] > row["open"] else "RED"
        colors = completed.apply(get_color, axis=1)
        return all(colors == "GREEN")

    def perform_buy(self, symbol, token, exchange, buy_price, buy_time):
        final_buy_price = buy_price * (1 + getattr(config, 'BUY_SLIPPAGE', 0.05) / 100)
        order_id = f"PAPER-BUY-GREEN3-{symbol}-{int(time.time())}"
        print(f"🚀 [GREEN3] BUY {symbol} at {final_buy_price}")
        self._mark_entry(symbol, final_buy_price, str(buy_time), str(order_id), "MIS", "PAPER", "GREEN3")

    def _mark_entry(self, symbol, buy_price, buy_time, order_id, product, mode, strategy_name):
        conn = self._db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE symbols_green3 SET isExecuted=1, buyprice=%s, buytime=%s, buy_order_id=%s, product=%s, mode=%s, strategy=%s WHERE symbol=%s",
            (buy_price, buy_time, order_id, product, mode, strategy_name, symbol)
        )
        conn.commit()
        conn.close()

    def run_cycle(self):
        from engine_symbol_data import fetch_runtime_symbols
        symbol_data_list = fetch_runtime_symbols(self.kite)

        for item in symbol_data_list:
            symbol, token, exchange = item["symbol"], item["token"], item["exchange"]

            conn = self._db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM symbols_green3 WHERE symbol=%s", (symbol,))
            row = cursor.fetchone()
            conn.close()

            if not row or row["isExecuted"] == 1: continue

            try:
                records = fetch_symbol_candles(
                    self.kite, token,
                    timeframe=getattr(config, 'TIMEFRAME', 'minute'),
                    days=getattr(config, 'LOOKBACK_DAYS_GREEN3', 3.0)
                )
                if not records: continue
                new_df = build_symbol_dataframe(records)
                from engine_symbol_data import calculate_candle_color
                new_df = calculate_candle_color(new_df)
                update_symbol_dataframe_cache(self.df_cache, symbol, new_df)
                df = self.df_cache[symbol]
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                continue

            if self._check_signal(df, last_sell_time=row["last_sell_time"]):
                buy_price = float(df.iloc[-1]["close"])
                buy_time = df.iloc[-1]["date"]
                self.perform_buy(symbol, token, exchange, buy_price, buy_time)

        try:
            cache_file = os.path.join(STRATEGY_DIR, "live_df_cache.pkl")
            with open(cache_file, "wb") as f:
                pickle.dump(self.df_cache, f)
        except Exception:
            pass
