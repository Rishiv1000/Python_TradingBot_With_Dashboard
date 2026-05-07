import os
import pickle
import sys
import time
from datetime import datetime

import mysql.connector
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import config
from engine_symbol_data import build_green_dataframe, fetch_runtime_symbols, update_symbol_dataframe_cache
from shared.candle_data import interval_minutes
from shared.order_manager import place_real_buy


BOT_START_TIME = datetime.now()


class EntryEngine:
    def __init__(self, kite, df_cache):
        self.kite = kite
        self.df_cache = df_cache
        # symbol → timestamp of last rejection (for cooldown)
        self._rejected_until: dict = {}
        self.REJECTION_COOLDOWN_SEC = 300  # 5 minutes
        # symbol → timestamp of last failed signal (max 1 attempt)
        self._failed_signal: dict = {}
        self.SIGNAL_COOLDOWN_SEC = 0  # not time based, just until new signal


    def _db_connection(self):
        return mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
        )

    def _is_in_cooldown(self, symbol) -> bool:
        until = self._rejected_until.get(symbol)
        if until and time.time() < until:
            remaining = int(until - time.time())
            print(f"[GREEN] ⏸️ {symbol} in rejection cooldown — {remaining}s remaining, skipping.")
            return True
        return False

    def _set_cooldown(self, symbol):
        self._rejected_until[symbol] = time.time() + self.REJECTION_COOLDOWN_SEC
        print(f"[GREEN] ⏸️ {symbol} cooldown set for {self.REJECTION_COOLDOWN_SEC}s (order rejected).")

    def _check_signal(self, symbol, df, last_sell_time=None):
        # Need at least 3 rows: 2 completed candles + 1 forming candle
        if df is None or len(df) < 3:
            return False

        # Last 2 completed candles (excluding the forming candle at -1)
        completed = df.iloc[-3:-1]

        # Signal timestamp = last completed candle's date
        signal_ts = str(df.iloc[-2]["date"]) if "date" in df.columns else None

        # If this exact signal was already attempted and failed, skip
        if signal_ts is not None and self._failed_signal.get(symbol) == signal_ts:
            print(f"[GREEN] ⏭️ {symbol} — same signal already attempted ({signal_ts}), waiting for new candles.")
            return False

        # Check: both completed candles must be GREEN
        if not all(completed["candle_color"] == "GREEN"):
            return False

        # Signal is valid — clear any old failure record
        self._failed_signal.pop(symbol, None)
        return True

    def _mark_entry(self, symbol, buy_price, buy_time, order_id, product):
        conn = self._db_connection()
        cursor = conn.cursor()
        symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green")
        cursor.execute(
            f"UPDATE {symbols_table} SET isExecuted=1, buyprice=%s, buytime=%s, buy_order_id=%s, product=%s WHERE symbol=%s",
            (buy_price, buy_time, order_id, product, symbol),
        )
        conn.commit()
        conn.close()

    def perform_buy(self, symbol, exchange, buy_price, signal_time):
        order_id = place_real_buy(
            self.kite,
            symbol,
            quantity=getattr(config, "DEFAULT_QTY", 1),
            exchange=exchange,
            config=config,
        )

        if not order_id:
            print(f"[GREEN] BUY skipped for {symbol} — order not placed.")
            # Mark this signal as failed — wait for fresh GREEN candles
            self._failed_signal[symbol] = str(signal_time)
            return

        final_buy_price = buy_price
        if str(order_id).startswith("SIMULATED"):
            self._mark_entry(symbol, final_buy_price, str(signal_time), str(order_id), "MIS")
            return

        # For real orders — verify order was actually FILLED before marking entry
        try:
            # Retry up to 5 times (5 seconds total) waiting for COMPLETE status
            order_filled = False
            for attempt in range(5):
                time.sleep(1)
                for state in reversed(self.kite.order_history(order_id)):
                    if state["status"] == "COMPLETE":
                        order_filled = True
                        if state.get("average_price"):
                            final_buy_price = float(state["average_price"])
                        break
                    elif state["status"] in ("CANCELLED", "REJECTED"):
                        print(f"[GREEN] ❌ BUY order {order_id} was {state['status']} for {symbol} — NOT marking entry.")
                        self._failed_signal[symbol] = str(signal_time)
                        return
                if order_filled:
                    break
                print(f"[GREEN] ⏳ Waiting for order {order_id} to fill... attempt {attempt+1}/5")

            if not order_filled:
                # Order placed but not filled in 5s — still mark entry to prevent duplicate buy
                # Exit engine will handle it if position doesn't exist
                print(f"[GREEN] ⚠️ Order {order_id} not COMPLETE after 5s — marking entry anyway to prevent duplicate.")
                self._mark_entry(symbol, final_buy_price, str(signal_time), str(order_id), "MIS")
                return

        except Exception as e:
            print(f"[GREEN] ⚠️ Could not verify order {order_id} for {symbol}: {e} — marking entry to prevent duplicate.")
            self._mark_entry(symbol, final_buy_price, str(signal_time), str(order_id), "MIS")
            return

        self._mark_entry(symbol, final_buy_price, str(signal_time), str(order_id), "MIS")


    def run_cycle(self):
        now = datetime.now().strftime("%H:%M:%S")
        symbols_checked = 0
        for item in fetch_runtime_symbols(self.kite):
            symbol, token, exchange = item["symbol"], item["token"], item["exchange"]
            if not token:
                print(f"[{now}] [GREEN] ⚠️ {symbol}: instrument_token missing, skipping.")
                continue

            conn = self._db_connection()
            cursor = conn.cursor(dictionary=True)
            symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green")
            cursor.execute(f"SELECT * FROM {symbols_table} WHERE symbol=%s", (symbol,))
            row = cursor.fetchone()
            conn.close()

            if not row or row["isExecuted"] == 1:
                continue

            # Skip symbols in rejection cooldown
            if self._is_in_cooldown(symbol):
                continue


            symbols_checked += 1
            try:
                new_df = build_green_dataframe(self.kite, token)
                df = update_symbol_dataframe_cache(self.df_cache, symbol, new_df)
            except Exception as e:
                print(f"[{now}] [GREEN] ❌ Error fetching {symbol}: {e}")
                continue

            # Use new signature: symbol, df, last_sell_time
            if self._check_signal(symbol, df, row["last_sell_time"]):
                candles = len(df) if df is not None else 0
                print(f"[{now}] [GREEN] 🟢 SIGNAL {symbol} | candles:{candles} → BUY")
                self.perform_buy(symbol, exchange, float(df.iloc[-1]["close"]), str(df.iloc[-1]["date"]))
            else:
                if df is not None and len(df) >= 3:
                    completed = df.iloc[-3:-1]
                    colors = list(completed["candle_color"])
                    candles = len(df)
                    print(f"[{now}] [GREEN] {symbol} | last 2: {colors} | candles:{candles}")

        cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_df_cache.pkl")
        temp_file = cache_file + ".tmp"
        with open(temp_file, "wb") as f:
            pickle.dump(self.df_cache, f)
        os.replace(temp_file, cache_file)
