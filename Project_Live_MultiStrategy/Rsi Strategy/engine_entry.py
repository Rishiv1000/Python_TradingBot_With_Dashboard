import os
import pickle
import sqlite3
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import pandas as pd

from db_manager import config
from engine_symbol_data import build_rsi_dataframe, fetch_runtime_symbols, update_symbol_dataframe_cache
from shared.order_manager import place_real_buy


class EntryEngineRSI:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache

    def _db_connection(self):
        return sqlite3.connect(config.DB_PATH)

    def _check_signal(self, df):
        if df is None or len(df) < 2 or "rsi" not in df:
            return False
        last_rsi = df.iloc[-1]["rsi"]
        if pd.isna(last_rsi):
            return False
        return last_rsi <= getattr(config, "BUY_LEVEL", 30)

    def _mark_entry(self, symbol, buy_price, buy_time, order_id, product):
        conn = self._db_connection()
        conn.execute(
            "UPDATE symbols_state SET isExecuted=1, buyprice=?, buytime=?, buy_order_id=?, product=? WHERE symbol=?",
            (buy_price, buy_time, order_id, product, symbol),
        )
        conn.commit()
        conn.close()

    def perform_buy(self, symbol, exchange, buy_price, buy_time):
        order_id = place_real_buy(
            self.kite,
            symbol,
            quantity=getattr(config, "DEFAULT_QTY", 1),
            exchange=exchange,
            config=config,
        )
        if order_id:
            self._mark_entry(symbol, buy_price, buy_time, str(order_id), "MIS")

    def run_cycle(self):
        for item in fetch_runtime_symbols(self.kite):
            symbol, token, exchange = item["symbol"], item["token"], item["exchange"]
            if not token:
                print(f"Skipping RSI:{symbol}; instrument_token missing.")
                continue

            conn = self._db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM symbols_state WHERE symbol=?", (symbol,))
            row_data = cursor.fetchone()
            row = dict(zip([d[0] for d in cursor.description], row_data)) if row_data else None
            conn.close()

            if not row or row["isExecuted"] == 1:
                continue

            try:
                new_df = build_rsi_dataframe(self.kite, token)
                df = update_symbol_dataframe_cache(self.df_cache, symbol, new_df)
            except Exception as e:
                print(f"Error fetching RSI:{symbol}: {e}")
                continue

            if self._check_signal(df):
                self.perform_buy(symbol, exchange, float(df.iloc[-1]["close"]), df.iloc[-1]["date"])

        cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_df_cache.pkl")
        temp_file = cache_file + ".tmp"
        with open(temp_file, "wb") as f:
            pickle.dump(self.df_cache, f)
        os.replace(temp_file, cache_file)
