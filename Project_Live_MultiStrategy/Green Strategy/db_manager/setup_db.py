import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_manager import config


def setup_database():
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symbols_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE,
            exchange TEXT,
            instrument_token INTEGER,
            isExecuted INTEGER DEFAULT 0,
            buyprice REAL DEFAULT NULL,
            buytime TEXT DEFAULT NULL,
            buy_order_id TEXT DEFAULT NULL,
            product TEXT DEFAULT 'MIS',
            last_sell_time TEXT DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            buytime TEXT,
            buyprice REAL,
            selltime TEXT,
            sellprice REAL,
            pnl REAL,
            reason TEXT,
            slippage REAL,
            buy_order_id TEXT,
            sell_order_id TEXT,
            strategy TEXT DEFAULT 'GREEN'
        )
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    setup_database()
