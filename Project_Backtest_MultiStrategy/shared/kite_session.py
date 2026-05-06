import os
import sys
from kiteconnect import KiteConnect

def generate_or_load_session(api_key, access_token_file):
    kite = KiteConnect(api_key=api_key, timeout=30)
    if os.path.exists(access_token_file):
        with open(access_token_file, "r") as f:
            access_token = f.read().strip()
        if access_token:
            kite.set_access_token(access_token)
            try:
                kite.profile()
                print("✅ Kite session active.")
                return kite
            except Exception:
                pass
    print("❌ No valid Kite session. Please login via Dashboard.")
    return None
