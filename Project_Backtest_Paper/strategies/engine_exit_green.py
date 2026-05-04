import sys
import os
from datetime import datetime
import threading
import time
import mysql.connector
from kiteconnect import KiteTicker

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_manager.config as config
from db_manager.config import API_KEY, DB_HOST, DB_NAME, DB_PASSWORD, DB_USER

class ExitEngineGreen:
    def __init__(self, kite, paper_trade=None, target_pct=None, stoploss_pct=None):
        self.kite = kite
        self.paper_trade = paper_trade if paper_trade is not None else config.PAPER_TRADE
        self.target_pct = target_pct if target_pct is not None else getattr(config, 'TARGET', 0.5)
        self.stoploss_pct = stoploss_pct if stoploss_pct is not None else getattr(config, 'STOPLOSS', 0.5)
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
        if pnl_pct >= self.target_pct: return True, "TARGET HIT"
        if pnl_pct <= -self.stoploss_pct: return True, "STOPLOSS HIT"
        return False, ""

    def _close_position_and_log(self, position, sell_price, reason, sell_order_id):
        pnl = (sell_price - float(position["buyprice"])) * getattr(config, 'DEFAULT_QTY', 1)
        slippage_amt = float(position["buyprice"]) * (getattr(config, 'SELL_SLIPPAGE', 0.05) / 100)
        conn = self._db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO trades_log (symbol, buytime, buyprice, selltime, sellprice, pnl, reason, slippage, buy_order_id, sell_order_id, mode, strategy) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (position["symbol"], position["buytime"], position["buyprice"], datetime.now(), sell_price, pnl, reason, slippage_amt, str(position["buy_order_id"]), str(sell_order_id), position["mode"], position.get("strategy")))
        cursor.execute("UPDATE symbols_state SET isExecuted=0, buyprice=NULL, buytime=NULL, buy_order_id=NULL, product=NULL, strategy=NULL, last_sell_time=%s WHERE symbol=%s", (datetime.now(), position["symbol"]))
        conn.commit(); conn.close()

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
        # In Backtest/Paper project, we ONLY do paper trading
        sell_price = ltp * (1 - (getattr(config, 'SELL_SLIPPAGE', 0.05) / 100))
        exit_order_id = f"PAPER-SELL-{row['symbol']}-{int(time.time())}"
        self._close_position_and_log(row, sell_price, reason, exit_order_id)
        
        with self.state["lock"]:
            if row['instrument_token'] in self.state["processing_tokens"]: 
                self.state["processing_tokens"].remove(row['instrument_token'])

def monitor_and_exit_single_websocket(kite, paper_trade=None):
    engine = ExitEngineGreen(kite, paper_trade)
    engine.start_monitoring()
