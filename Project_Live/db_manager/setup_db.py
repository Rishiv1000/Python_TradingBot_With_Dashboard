import os
import sys
import sqlite3

# Add grandparent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from local config
from db_manager import config

DB_PATH = os.path.join(os.path.dirname(__file__), f"{config.DB_NAME}.db")

def setup_database():
    print("Starting Live Database Setup (SQLite)...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. symbols_state: Current Open Positions & Symbols to track
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
                last_sell_time TEXT DEFAULT NULL,
                strategy TEXT DEFAULT NULL
            )
        """)
        
        # 2. trades_log: History of completed trades
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
                strategy TEXT DEFAULT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"Live Database Setup Complete! Created: {DB_PATH}")
    except Exception as e:
        print(f"Error setting up SQLite: {e}")

if __name__ == "__main__":
    setup_database()
