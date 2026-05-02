import sys
import os
import time
import mysql.connector
from datetime import datetime

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
        return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)

    def _check_signal(self, df, last_sell_time=None):
        if df is None or len(df) < 2: return False
        effective_start = BOT_START_TIME
        if last_sell_time and last_sell_time > BOT_START_TIME:
            effective_start = last_sell_time
        from engine_symbol_data import _interval_minutes
        from datetime import timedelta
        interval = _interval_minutes()
        new_candles = df[df["date"] + timedelta(minutes=interval) > effective_start]
        if len(new_candles) < 2: return False
        last_two_completed = df.iloc[-2:]
        if all(last_two_completed["date"] + timedelta(minutes=interval) > effective_start):
            return all(last_two_completed["candle_color"] == "GREEN")
        return False

    def place_real_buy(self, symbol, quantity, exchange):
        try:
            ltp_data = self.kite.ltp(f"{exchange}:{symbol}")
            ltp = ltp_data[f"{exchange}:{symbol}"]["last_price"]
            limit_price = round(ltp * (1 + getattr(config, 'BUY_SLIPPAGE_BUFFER', 0.05) / 100), 1) 
            return self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR, exchange=exchange, tradingsymbol=symbol, 
                transaction_type=self.kite.TRANSACTION_TYPE_BUY, quantity=quantity, 
                order_type=self.kite.ORDER_TYPE_LIMIT, price=limit_price, product=self.kite.PRODUCT_MIS,
            )
        except Exception as e:
            print(f"BUY Order Failed for {symbol}: {e}")
            return None

    def perform_buy(self, symbol, token, exchange, buy_price, buy_time):
        mode = "PAPER" if self.paper_trade else "REAL"
        final_buy_price = buy_price
        if self.paper_trade:
            order_id = f"PAPER-BUY-{symbol}-{int(time.time())}"
        else:
            order_id = self.place_real_buy(symbol, quantity=getattr(config, 'DEFAULT_QTY', 1), exchange=exchange)
            if not order_id: return
            try:
                time.sleep(1)
                history = self.kite.order_history(order_id)
                for state in reversed(history):
                    if state["status"] == "COMPLETE" and state.get("average_price"):
                        final_buy_price = float(state["average_price"])
                        break
            except: pass
        self._mark_entry(symbol, final_buy_price, buy_time, str(order_id), "MIS", mode)

    def _mark_entry(self, symbol, buy_price, buy_time, order_id, product, mode):
        conn = self._db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE symbols_state SET isExecuted=1, buyprice=%s, buytime=%s, buy_order_id=%s, product=%s, mode=%s WHERE symbol=%s", (buy_price, buy_time, order_id, product, mode, symbol))
        conn.commit()
        conn.close()

    def run_cycle(self):
        symbol_data_list = fetch_runtime_symbols(self.kite)
        for item in symbol_data_list:
            symbol, token, exchange = item["symbol"], item["token"], item["exchange"]
            conn = self._db_connection(); cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM symbols_state WHERE symbol=%s", (symbol,))
            row = cursor.fetchone(); conn.close()
            if not row or row["isExecuted"] == 1: continue
            try:
                records = fetch_symbol_candles(self.kite, token, days=getattr(config, 'CANDLE_LOOKBACK_DAYS', 5))
                if not records: continue
                new_df = build_symbol_dataframe(records)
                update_symbol_dataframe_cache(self.df_cache, symbol, new_df)
                df = self.df_cache[symbol]
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                continue
            if self._check_signal(df, last_sell_time=row["last_sell_time"]):
                buy_price = float(df.iloc[-1]["close"])
                buy_time = df.iloc[-1]["date"]
                self.perform_buy(symbol, token, exchange, buy_price, buy_time)

def run_entry_cycle(kite, df_cache, paper_trade=None):
    engine = EntryEngine(kite, df_cache, paper_trade)
    return engine.run_cycle()
