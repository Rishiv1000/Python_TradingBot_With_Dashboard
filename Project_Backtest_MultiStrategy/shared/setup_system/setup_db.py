import os
import sys
import mysql.connector

# Path setup
# setup_db.py is at: Project_Backtest_MultiStrategy/shared/setup_system/setup_db.py
# We need Project_Backtest_MultiStrategy/ in sys.path so `shared` is importable
SETUP_DIR    = os.path.dirname(os.path.abspath(__file__))   # .../shared/setup_system
SHARED_DIR   = os.path.dirname(SETUP_DIR)                   # .../shared
PROJECT_ROOT = os.path.dirname(SHARED_DIR)                  # .../Project_Backtest_MultiStrategy
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.base_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def initialize_backtest_database(host, user, password, db_name):
    print(f"Initializing Backtest/Paper Database: {db_name}")
    try:
        conn = mysql.connector.connect(host=host, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        conn.close()

        conn = mysql.connector.connect(host=host, user=user, password=password, database=db_name)
        cursor = conn.cursor()

        def ensure_column(table_name, column_name, column_def):
            cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
            if cursor.fetchone() is None:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

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
                    mode VARCHAR(20) DEFAULT 'PAPER',
                    strategy VARCHAR(50) DEFAULT NULL,
                    last_sell_time DATETIME DEFAULT NULL
                )
            """)
            ensure_column(table, "mode", "VARCHAR(20) DEFAULT 'PAPER'")
            ensure_column(table, "strategy", "VARCHAR(50) DEFAULT NULL")

        cursor.execute("SHOW TABLES LIKE 'symbols_state'")
        if cursor.fetchone():
            for table in strategy_tables:
                cursor.execute(f"""
                    INSERT IGNORE INTO {table}
                    (symbol, exchange, instrument_token, isExecuted, product, mode)
                    SELECT symbol, exchange, instrument_token, 0, 'MIS', 'PAPER'
                    FROM symbols_state
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
                mode VARCHAR(20) DEFAULT 'PAPER',
                strategy VARCHAR(50) DEFAULT NULL
            )
        """)
        ensure_column("trades_log", "mode", "VARCHAR(20) DEFAULT 'PAPER'")

        cursor.execute("DROP TABLE IF EXISTS backtest_log")
        cursor.execute("DROP TABLE IF EXISTS backtest_reports")
        cursor.execute("DROP TABLE IF EXISTS symbols_state")

        conn.commit()
        conn.close()
        print("DONE: Backtest/Paper Database setup complete.")
        return True
    except Exception as e:
        print(f"ERROR setting up backtest database: {e}")
        return False

if __name__ == "__main__":
    initialize_backtest_database(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
