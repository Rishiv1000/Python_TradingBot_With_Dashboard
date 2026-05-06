import os
import sys
import threading
import time
from datetime import datetime

import mysql.connector
from kiteconnect import KiteTicker

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import config
from shared.order_manager import place_real_sell


class ExitEngine:
    def __init__(self, kite):
        self.kite = kite
        self.target_pct = getattr(config, "TARGET", 0.5)
        self.stoploss_pct = getattr(config, "STOPLOSS", 0.5)
        self.state = {
            "open_by_token": {},
            "subscribed_tokens": set(),
            "processing": set(),
            "lock": threading.Lock(),
        }

    def _db_connection(self):
        return mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
        )

    def _fetch_open_positions(self):
        conn = self._db_connection()
        cursor = conn.cursor(dictionary=True)
        symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green3")
        cursor.execute(f"SELECT * FROM {symbols_table} WHERE isExecuted=1")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def _should_exit(self, buy_price, ltp):
        pnl_pct = ((ltp - buy_price) / buy_price) * 100
        if pnl_pct >= self.target_pct:
            return True, "TARGET HIT"
        if pnl_pct <= -self.stoploss_pct:
            return True, "STOPLOSS HIT"
        return False, ""

    def _close_position_and_log(self, row, sell_price, reason, sell_order_id):
        pnl = (sell_price - float(row["buyprice"])) * getattr(config, "DEFAULT_QTY", 1)
        slippage = float(row["buyprice"]) * (getattr(config, "SELL_SLIPPAGE", 0.05) / 100)
        conn = self._db_connection()
        cursor = conn.cursor()
        symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green3")
        cursor.execute(
            "INSERT INTO trades_log (symbol, buytime, buyprice, selltime, sellprice, pnl, reason, slippage, buy_order_id, sell_order_id, strategy) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (row["symbol"], row["buytime"], row["buyprice"], datetime.now(),
             sell_price, pnl, reason, slippage,
             str(row["buy_order_id"]), str(sell_order_id), config.STRATEGY_NAME),
        )
        cursor.execute(
            f"UPDATE {symbols_table} SET isExecuted=0, buyprice=NULL, buytime=NULL, buy_order_id=NULL, product=NULL, last_sell_time=%s WHERE symbol=%s",
            (datetime.now(), row["symbol"]),
        )
        conn.commit()
        conn.close()
        print(f"[GREEN3] SOLD {row['symbol']} @ {sell_price} ({reason})")

    def _place_sell(self, row):
        order_id = str(row["buy_order_id"])

        # SIMULATED buy — place simulated sell directly without looking up Zerodha orders
        if order_id.startswith("SIMULATED"):
            return place_real_sell(
                self.kite,
                row["symbol"],
                quantity=getattr(config, "DEFAULT_QTY", 1),
                exchange=getattr(config, "LIVE_EXCHANGE", "NSE"),
                product="MIS",
                config=config,
                tag=order_id,
            )

        # Real order — look up from Zerodha
        try:
            if order_id == "FAILED_OR_REJECTED":
                print(f"[GREEN3] Cleaning up failed entry for {row['symbol']}.")
                return "CLEANUP"

            orders = self.kite.orders()
            order = next((o for o in orders if str(o["order_id"]) == order_id), None)
            if not order:
                print(f"[GREEN3] Order {order_id} not found in Zerodha orders.")
                return None
            return place_real_sell(
                self.kite,
                order["tradingsymbol"],
                order["quantity"],
                order["exchange"],
                order["product"],
                config=config,
                tag=order_id,
            )
        except Exception as e:
            print(f"Exit failed: {e}")
            return None

    def _refresh_positions(self, kws):
        positions = self._fetch_open_positions()
        with self.state["lock"]:
            self.state["open_by_token"] = {
                row["instrument_token"]: row
                for row in positions
                if row["instrument_token"] and row["buy_order_id"] not in self.state["processing"]
            }
        if kws.is_connected():
            with self.state["lock"]:
                latest = set(self.state["open_by_token"].keys())
                to_add = list(latest - self.state["subscribed_tokens"])
                to_remove = list(self.state["subscribed_tokens"] - latest)
                if to_add:
                    kws.subscribe(to_add)
                    kws.set_mode(kws.MODE_FULL, to_add)
                if to_remove:
                    kws.unsubscribe(to_remove)
                self.state["subscribed_tokens"] = latest

    def _perform_sell(self, row, ltp, reason):
        exit_order_id = self._place_sell(row)
        if not exit_order_id:
            with self.state["lock"]:
                self.state["processing"].discard(row["buy_order_id"])
            return

        if exit_order_id == "CLEANUP":
            # Just reset the database, don't log a real trade
            conn = self._db_connection()
            cursor = conn.cursor()
            symbols_table = getattr(config, "SYMBOLS_TABLE", "symbols_green3")
            cursor.execute(
                f"UPDATE {symbols_table} SET isExecuted=0, buyprice=NULL, buytime=NULL, buy_order_id=NULL, product=NULL, last_sell_time=%s WHERE symbol=%s",
                (datetime.now(), row["symbol"]),
            )
            conn.commit()
            conn.close()
            with self.state["lock"]:
                self.state["processing"].discard(row["buy_order_id"])
            return

        sell_price = ltp
        if not str(exit_order_id).startswith("SIMULATED"):
            try:
                for state in reversed(self.kite.order_history(exit_order_id)):
                    if state["status"] == "COMPLETE" and state.get("average_price"):
                        sell_price = float(state["average_price"])
                        break
            except Exception:
                pass

        self._close_position_and_log(row, sell_price, reason, exit_order_id)
        with self.state["lock"]:
            self.state["processing"].discard(row["buy_order_id"])

    def start_monitoring(self):
        kws = KiteTicker(config.API_KEY, self.kite.access_token)

        def on_ticks(_ws, ticks):
            for tick in ticks:
                token = tick["instrument_token"]
                ltp = float(tick["last_price"])
                row_to_sell = None
                with self.state["lock"]:
                    row = self.state["open_by_token"].get(token)
                    if row and row["buy_order_id"] not in self.state["processing"]:
                        should_exit, reason = self._should_exit(float(row["buyprice"]), ltp)
                        if should_exit:
                            self.state["processing"].add(row["buy_order_id"])
                            row_to_sell = row
                            exit_reason = reason
                if row_to_sell:
                    self._perform_sell(row_to_sell, ltp, exit_reason)

        kws.on_ticks = on_ticks
        kws.on_connect = lambda ws, _res: self._refresh_positions(ws)
        kws.connect(threaded=True)
        while True:
            self._refresh_positions(kws)
            time.sleep(2)
