import os
from dotenv import load_dotenv

# Path to this shared directory
SHARED_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to project root
PROJECT_ROOT = os.path.dirname(SHARED_DIR)

# Load .env from shared directory (where it actually lives)
env_path = os.path.join(SHARED_DIR, ".env")
load_dotenv(env_path)

# --- [SYSTEM & AUTH] ---
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
ACCESS_TOKEN_FILE = os.path.join(SHARED_DIR, "access_token.txt")

# --- [DATABASE CONFIG] ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "trading_bot_backtest")

# --- [COMMON TRADING SETTINGS] ---
DEFAULT_QTY = 1
PAPER_TRADE = True
BOT_RUNNING = True
BOT_STATUS = "Idle"
LIVE_EXCHANGE = "NSE"
TIMEFRAME = "minute"

BUY_SLIPPAGE = 0.05
SELL_SLIPPAGE = 0.05

# --- [COMMON TABLE NAMES] ---
TRADES_TABLE = "trades_log"

