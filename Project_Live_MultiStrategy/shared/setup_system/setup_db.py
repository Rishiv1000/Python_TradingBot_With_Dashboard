import os
import sys
import mysql.connector

# Path setup
# setup_db.py is at: Project_Live_MultiStrategy/shared/setup_system/setup_db.py
SETUP_DIR    = os.path.dirname(os.path.abspath(__file__))   # .../shared/setup_system
SHARED_DIR   = os.path.dirname(SETUP_DIR)                   # .../shared
PROJECT_ROOT = os.path.dirname(SHARED_DIR)                  # .../Project_Live_MultiStrategy
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.base_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def initialize_live_database(host, user, password, db_name):
    print(f"Initializing Live Database: {db_name}")
    try:
        # Create database if it doesn't exist
        conn = mysql.connector.connect(host=host, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        conn.close()

        # Connect to the database and create tables
        conn = mysql.connector.connect(host=host, user=user, password=password, database=db_name)
        cursor = conn.cursor()

        strategy_tables = ["symbols_green", "symbols_green3"]
        for table in strategy_tables:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(50) UNIQUE,
                    exchange VARCHAR(20),
                    instrument_token INT,
                    isExecuted TINYINT(1) DEFAULT 0,
                    buyprice DOUBLE DEFAULT NULL,
                    buytime DATETIME DEFAULT NULL,
                    buy_order_id VARCHAR(100) DEFAULT NULL,
                    product VARCHAR(20) DEFAULT 'MIS',
                    last_sell_time DATETIME DEFAULT NULL
                )
            """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(50),
                buytime DATETIME,
                buyprice DOUBLE,
                selltime DATETIME,
                sellprice DOUBLE,
                pnl DOUBLE,
                reason VARCHAR(255),
                slippage DOUBLE DEFAULT 0,
                buy_order_id VARCHAR(100),
                sell_order_id VARCHAR(100),
                strategy VARCHAR(50) DEFAULT NULL
            )
        """)

        conn.commit()
        conn.close()
        print("DONE: Live Database setup complete.")
        return True
    except Exception as e:
        print(f"ERROR setting up live database: {e}")
        return False


if __name__ == "__main__":
    initialize_live_database(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
