import os
import sys
import time

import mysql.connector
from kiteconnect import KiteConnect
from dotenv import load_dotenv


SETUP_DIR    = os.path.dirname(os.path.abspath(__file__))   # .../shared/setup_system
SHARED_DIR   = os.path.dirname(SETUP_DIR)                   # .../shared
PROJECT_ROOT = os.path.dirname(SHARED_DIR)                  # .../Project_Backtest_MultiStrategy
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.candle_data import search_kite_symbol
from setup_system.setup_db import initialize_backtest_database


load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

API_KEY = os.getenv("KITE_API_KEY")
ACCESS_TOKEN_FILE = os.path.join(PROJECT_ROOT, "access_token.txt")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "trading_bot_backtest")

STRATEGY_TABLES = {
    "GREEN":  "symbols_green",
    "GREEN3": "symbols_green3",
}


def kite_session():
    if not API_KEY:
        raise RuntimeError("KITE_API_KEY missing in .env")
    if not os.path.exists(ACCESS_TOKEN_FILE):
        raise RuntimeError("access_token.txt missing. Login from dashboard first.")

    with open(ACCESS_TOKEN_FILE, "r") as f:
        access_token = f.read().strip()
    if not access_token:
        raise RuntimeError("access_token.txt is empty. Login from dashboard first.")

    kite = KiteConnect(api_key=API_KEY, timeout=30)
    kite.set_access_token(access_token)
    kite.profile()
    return kite


def reset_strategy_table(cursor, table_name):
    cursor.execute(
        f"""
        UPDATE {table_name}
        SET isExecuted=0,
            buyprice=NULL,
            buytime=NULL,
            buy_order_id=NULL,
            product='MIS',
            mode='PAPER'
        """
    )


def fill_missing_tokens(cursor, table_name, strategy_name, kite):
    cursor.execute(
        f"""
        SELECT id, symbol, exchange
        FROM {table_name}
        WHERE instrument_token IS NULL OR instrument_token = 0
        ORDER BY symbol
        """
    )
    rows = cursor.fetchall()
    if not rows:
        print(f"{strategy_name}: no missing instrument tokens.")
        return 0

    updated = 0
    print(f"{strategy_name}: filling {len(rows)} missing instrument tokens...")
    for row_id, symbol, exchange in rows:
        token = search_kite_symbol(kite, exchange or "NSE", symbol)
        if token:
            cursor.execute(
                f"UPDATE {table_name} SET instrument_token=%s WHERE id=%s",
                (token, row_id),
            )
            updated += 1
            print(f"  {symbol} -> {token}")
        else:
            print(f"  token not found: {exchange}:{symbol}")
        time.sleep(0.35)
    return updated


def main():
    initialize_backtest_database(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)

    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    cursor = conn.cursor()

    kite = kite_session()
    total_updated = 0
    for strategy_name, table_name in STRATEGY_TABLES.items():
        reset_strategy_table(cursor, table_name)
        total_updated += fill_missing_tokens(cursor, table_name, strategy_name, kite)

    conn.commit()
    conn.close()
    print(f"Defaults complete. Updated {total_updated} instrument tokens.")


if __name__ == "__main__":
    main()
