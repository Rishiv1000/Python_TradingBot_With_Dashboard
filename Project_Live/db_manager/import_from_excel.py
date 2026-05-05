import pandas as pd
import sqlite3
import os

# --- Setup ---
EXCEL_FILE = os.path.join(os.path.dirname(__file__), "symbols.xlsx")
DB_PATH = os.path.join(os.path.dirname(__file__), "trading_bot_live.db")

def import_now():
    if not os.path.exists(EXCEL_FILE):
        print(f"\n❌ {EXCEL_FILE} nahi mili!")
        return

    print("\n📊 Reading Excel file (Quiet Mode)...")
    try:
        df_excel = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        print(f"❌ Excel read error: {e}")
        return

    if 'Symbol' not in df_excel.columns or 'Exchange' not in df_excel.columns:
        print("❌ Excel columns check karein! 'Symbol' aur 'Exchange' hona zaroori hai.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    count = 0
    for index, row in df_excel.iterrows():
        symbol = str(row['Symbol']).upper().strip()
        exchange = str(row['Exchange']).upper().strip()
        
        if not symbol or symbol == 'NAN': continue
        
        # Sirf Symbol aur Exchange insert karein (isExecuted=0)
        # instrument_token ko NULL rehne dein, set_defaults ise fill karega
        cursor.execute("""
            INSERT OR IGNORE INTO symbols_state (symbol, exchange, isExecuted)
            VALUES (?, ?, 0)
        """, (symbol, exchange))
        count += 1

    conn.commit()
    conn.close()
    
    print(f"✅ {count} symbols added to database. Now run 'db_manager/set_defaults.py' to fetch tokens.")

if __name__ == "__main__":
    import_now()
