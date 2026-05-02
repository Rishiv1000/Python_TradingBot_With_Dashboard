import sys
import os
from datetime import datetime
import threading
import time
import mysql.connector
from kiteconnect import KiteTicker

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import db_manager.config as config
from db_manager.config import API_KEY, DB_HOST, DB_NAME, DB_PASSWORD, DB_USER

class ExitEngine:
    def __init__(self, kite, paper_trade=False):
        self.kite = kite
        self.paper_trade = paper_trade
        self.state = {"open_by_token": {}, "subscribed_tokens": set(), "processing_tokens": set(), "lock": threading.Lock()}

    def _db_connection(self):
        return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)

    def _fetch_open_positions(self):
        conn = self._db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM symbols_state WHERE isExecuted=1")
        rows = cursor.fetchall(); conn.close()
        return rows

    def _should_exit(self, buy_price, ltp):
        pnl_pct = ((ltp - buy_price) / buy_price) * 100
        if pnl_pct >= getattr(config, 'TARGET_PCT', 0.5): return True, "TARGET HIT"
        if pnl_pct <= -getattr(config, 'STOPLOSS_PCT', 0.5): return True, "STOPLOSS HIT"
        return False, ""

    def _close_position_and_log(self, position, sell_price, reason, sell_order_id):
        pnl = (sell_price - float(position["buyprice"])) * getattr(config, 'DEFAULT_QTY', 1)
        slippage_amt = float(position["buyprice"]) * (getattr(config, 'SLIPPAGE_PCT', 0.05) / 100)
        conn = self._db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO trades_log (symbol, buytime, buyprice, selltime, sellprice, pnl, reason, slippage, buy_order_id, sell_order_id, mode) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (position["symbol"], position["buytime"], position["buyprice"], datetime.now(), sell_price, pnl, reason, slippage_amt, str(position["buy_order_id"]), str(sell_order_id), position["mode"]))
        cursor.execute("UPDATE symbols_state SET isExecuted=0, buyprice=NULL, buytime=NULL, buy_order_id=NULL, product=NULL, last_sell_time=%s WHERE symbol=%s", (datetime.now(), position["symbol"]))
        conn.commit(); conn.close()

    def exit_from_db_record(self, row):
        if self.paper_trade:
            return f"PAPER-SELL-{row['symbol']}-{int(time.time())}"
        try:
            orig_order_id = str(row["buy_order_id"])
            all_orders = self.kite.orders()
            orig_order = next((o for o in all_orders if str(o["order_id"]) == orig_order_id), None)
            if not orig_order: return None
            symbol, qty, exchange, product = orig_order["tradingsymbol"], orig_order["quantity"], orig_order["exchange"], orig_order["product"]
            ltp_data = self.kite.ltp(f"{exchange}:{symbol}")
            ltp = ltp_data[f"{exchange}:{symbol}"]["last_price"]
            limit_price = round(ltp * (1 - getattr(config, 'SELL_SLIPPAGE_BUFFER', 0.05) / 100), 1)
            return self.kite.place_order(variety=self.kite.VARIETY_REGULAR, exchange=exchange, tradingsymbol=symbol, transaction_type=self.kite.TRANSACTION_TYPE_SELL, quantity=qty, order_type=self.kite.ORDER_TYPE_LIMIT, price=limit_price, product=product, tag=str(orig_order_id)[:20])
        except Exception as e:
            print(f"❌ Exit Failed: {e}"); return None

    def _refresh_positions(self, kws):
        positions = self._fetch_open_positions()
        with self.state["lock"]:
            next_open_by_token = {row["instrument_token"]: row for row in positions if row["instrument_token"] and row["instrument_token"] not in self.state["processing_tokens"]}
            self.state["open_by_token"] = next_open_by_token
        if kws.is_connected():
            with self.state["lock"]:
                latest_tokens = set(self.state["open_by_token"].keys())
                to_add = list(latest_tokens - self.state["subscribed_tokens"])
                to_remove = list(self.state["subscribed_tokens"] - latest_tokens)
                if to_add: kws.subscribe(to_add); kws.set_mode(kws.MODE_FULL, to_add)
                if to_remove: kws.unsubscribe(to_remove)
                self.state["subscribed_tokens"] = latest_tokens

    def start_monitoring(self):
        kws = KiteTicker(API_KEY, self.kite.access_token)
        def on_ticks(_ws, ticks):
            for tick in ticks:
                token, ltp = tick["instrument_token"], float(tick["last_price"])
                row_to_sell = None
                with self.state["lock"]:
                    row = self.state["open_by_token"].get(token)
                    if row and token not in self.state["processing_tokens"]:
                        should_exit, reason = self._should_exit(float(row['buyprice']), ltp)
                        if should_exit:
                            row_to_sell = self.state["open_by_token"].pop(token)
                            self.state["processing_tokens"].add(token)
                            exit_reason = reason
                if row_to_sell: self._perform_sell(row_to_sell, ltp, exit_reason)
        kws.on_ticks = on_ticks
        kws.on_connect = lambda ws, res: self._refresh_positions(ws)
        kws.connect(threaded=True)
        while True: self._refresh_positions(kws); time.sleep(2)

    def _perform_sell(self, row, ltp, reason):
        sell_price = ltp * (1 - (getattr(config, 'SLIPPAGE_PCT', 0.05) / 100))
        exit_order_id = self.exit_from_db_record(row)
        if not exit_order_id: return
        try:
            history = self.kite.order_history(exit_order_id)
            for s in reversed(history):
                if s["status"] == "COMPLETE" and s.get("average_price"):
                    sell_price = float(s["average_price"]); break
        except: pass
        self._close_position_and_log(row, sell_price, reason, exit_order_id)
        with self.state["lock"]:
            if row['instrument_token'] in self.state["processing_tokens"]: self.state["processing_tokens"].remove(row['instrument_token'])

def monitor_and_exit_single_websocket(kite, paper_trade=False):
    engine = ExitEngine(kite, paper_trade)
    engine.start_monitoring()
