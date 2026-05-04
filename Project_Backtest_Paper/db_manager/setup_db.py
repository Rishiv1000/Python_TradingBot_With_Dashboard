import os
import sys
import mysql.connector

# Add grandparent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from local config
from db_manager.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def setup_database():
    print("🛠️ Starting Database Setup (MySQL)...")
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.close()
        print(f"✅ Database '{DB_NAME}' is ready.")
    except Exception as e:
        print(f"❌ Error creating database: {e}"); return

    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols_state (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(60) UNIQUE,
                exchange VARCHAR(20),
                instrument_token INT,
                isExecuted INT DEFAULT 0,
                buyprice FLOAT DEFAULT NULL,
                buytime DATETIME DEFAULT NULL,
                buy_order_id VARCHAR(100) DEFAULT NULL,
                product VARCHAR(20) DEFAULT 'MIS',
                last_sell_time DATETIME DEFAULT NULL,
                mode VARCHAR(20) DEFAULT 'PAPER',
                strategy VARCHAR(50) DEFAULT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(60), buytime DATETIME, buyprice FLOAT,
                selltime DATETIME, sellprice FLOAT, pnl FLOAT,
                reason VARCHAR(100), slippage FLOAT,
                buy_order_id VARCHAR(100), sell_order_id VARCHAR(100), 
                mode VARCHAR(20),
                strategy VARCHAR(50) DEFAULT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(60),
                buytime DATETIME,
                buyprice FLOAT,
                selltime DATETIME,
                sellprice FLOAT,
                pnl FLOAT,
                reason VARCHAR(100),
                slippage FLOAT,
                buy_order_id VARCHAR(100),
                sell_order_id VARCHAR(100),
                mode VARCHAR(20),
                strategy VARCHAR(50) DEFAULT NULL
            )
        """)
        conn.commit(); conn.close()
        print("🚀 MySQL Database Setup Complete!")
    except Exception as e:
        print(f"❌ Error setting up tables: {e}")

if __name__ == "__main__":
    setup_database()
