import sys
import os
import mysql.connector
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kite_connector import generate_or_load_session
from symbol_data_engine import search_kite_symbol
from db_manager.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def fill_missing_tokens_and_reset():
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor(dictionary=True)
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
        kite = generate_or_load_session()
        for row in missing_symbols:
            sym, exch = row['symbol'], row['exchange']
            token = search_kite_symbol(kite, exch, sym)
            if token:
                cursor.execute("UPDATE symbols_state SET instrument_token = %s WHERE symbol = %s AND exchange = %s", (token, sym, exch))
                print(f"✅ Updated {sym} -> Token: {token}")
            time.sleep(0.5)
    conn.commit(); conn.close()
    print("\n🏁 Process complete!")

if __name__ == "__main__":
    fill_missing_tokens_and_reset()
