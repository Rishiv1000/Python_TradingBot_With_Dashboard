import sys
import os
import sqlite3
import time
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main_runner import generate_or_load_session
from engine_symbol_data import search_kite_symbol
from db_manager import config

DB_PATH = os.path.join(os.path.dirname(__file__), f"{config.DB_NAME}.db")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "symbols_list.xlsx")

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def import_from_excel():
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ Excel file not found: {EXCEL_PATH}")
        print("Please create 'symbols_list.xlsx' inside the db_manager folder with columns 'Symbol' and 'Exchange'.")
        # Create a dummy one for them
        pd.DataFrame([{"Symbol": "RELIANCE", "Exchange": "NSE"}, {"Symbol": "TCS", "Exchange": "NSE"}]).to_excel(EXCEL_PATH, index=False)
        print(f"✅ I just created a template Excel file for you at {EXCEL_PATH}. Please edit it and run again.")
        return

    try:
        df = pd.read_excel(EXCEL_PATH)
        if 'Symbol' not in df.columns:
            print("❌ Excel must have a 'Symbol' column!")
            return
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        count = 0
        for _, row in df.iterrows():
            sym = str(row['Symbol']).strip().upper()
            if not sym or sym == 'NAN': continue
            exch = str(row.get('Exchange', 'NSE')).strip().upper()
            
            cursor.execute("INSERT OR IGNORE INTO symbols_state (symbol, exchange) VALUES (?, ?)", (sym, exch))
            count += 1
            
        conn.commit()
        conn.close()
        print(f"✅ Successfully read and added {count} symbols from Excel into the database.")
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")

def fill_missing_tokens_and_reset():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ DB Connection Error: {e}"); return
    
    print("🧹 Resetting all symbols to unexecuted state...")
    cursor.execute("UPDATE symbols_state SET isExecuted = 0, buyprice = NULL, buytime = NULL, buy_order_id = NULL")
    conn.commit()

    cursor.execute("SELECT symbol, exchange FROM symbols_state WHERE instrument_token IS NULL OR instrument_token = 0")
    missing_symbols = cursor.fetchall()
    
    if not missing_symbols:
        print("✅ No missing tokens found. Reset complete!")
    else:
        print(f"🔄 Found {len(missing_symbols)} symbols with missing tokens. Initializing Kite...")
        try:
            kite = generate_or_load_session(allow_interact=False)
            for row in missing_symbols:
                sym, exch = row['symbol'], row['exchange']
                token = search_kite_symbol(kite, exch, sym)
                if token:
                    cursor.execute("UPDATE symbols_state SET instrument_token = ? WHERE symbol = ? AND exchange = ?", (token, sym, exch))
                    print(f"✅ Updated {sym} -> Token: {token}")
                time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ Could not fetch tokens. Please start Bot first or Login to Kite. ({e})")
    conn.commit()
    conn.close()
    print("\n🏁 Process complete!")

if __name__ == "__main__":
    import_from_excel()
    fill_missing_tokens_and_reset()
