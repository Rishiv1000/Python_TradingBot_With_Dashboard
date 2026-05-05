import pandas as pd
import mysql.connector
import os
import sys

# Add current directory to path for config import
import config

# --- Setup ---
EXCEL_FILE = os.path.join(os.path.dirname(__file__), "symbols_backtest.xlsx")

def import_now():
    if not os.path.exists(EXCEL_FILE):
        print(f"\n❌ {EXCEL_FILE} nahi mili!")
        return

    print("\n📊 Reading Backtest Excel file (Quiet Mode)...")
    try:
        df_excel = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        print(f"❌ Excel read error: {e}")
        return

    # Connect to MySQL
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ MySQL Connection Failed: {e}")
        return

    count = 0
    for index, row in df_excel.iterrows():
        symbol = str(row['Symbol']).upper().strip()
        exchange = str(row['Exchange']).upper().strip()
        
        if not symbol or symbol == 'NAN': continue
        
        # Insert only Symbol and Exchange into MySQL
        sql = """
            INSERT INTO symbols_state (symbol, exchange, isExecuted)
            VALUES (%s, %s, 0)
            ON DUPLICATE KEY UPDATE exchange = VALUES(exchange)
        """
        cursor.execute(sql, (symbol, exchange))
        count += 1

    conn.commit()
    conn.close()
    
    print(f"✅ {count} symbols added to Backtest database. Now run 'db_manager/set_defaults.py' to fetch tokens.")

if __name__ == "__main__":
    import_now()
