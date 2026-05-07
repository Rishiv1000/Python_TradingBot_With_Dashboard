import os
from dotenv import load_dotenv

# Path to this shared directory
SHARED_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to project root
PROJECT_ROOT = os.path.dirname(SHARED_DIR)

# Load .env from shared directory
env_path = os.path.join(SHARED_DIR, ".env")
load_dotenv(env_path)

# --- [SYSTEM & AUTH] ---
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
ACCESS_TOKEN_FILE = os.path.join(SHARED_DIR, "access_token.txt")

# --- [DATABASE CONFIG (MySQL)] ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "trading_bot_live")

# --- [COMMON TRADING SETTINGS] ---
DEFAULT_QTY = 1
REAL_TRADING_ENABLED = True
LIVE_EXCHANGE = "NSE"
TIMEFRAME = "minute"

BUY_SLIPPAGE  = 0.01   # 0.05% above LTP
SELL_SLIPPAGE = 0.01   # 0.05% below LTP

# --- [COMMON TABLE NAMES] ---
TRADES_TABLE = "trades_log"

