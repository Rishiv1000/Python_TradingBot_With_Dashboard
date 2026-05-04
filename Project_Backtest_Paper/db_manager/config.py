import os
from dotenv import load_dotenv

DB_MANAGER_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(DB_MANAGER_DIR, ".env")
load_dotenv(env_path)

# --- [SYSTEM & AUTH] ---
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
ACCESS_TOKEN_FILE = os.path.join(DB_MANAGER_DIR, "access_token.txt")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "trading_bot_backtest")

DEFAULT_QTY = 1
PAPER_TRADE = True
BOT_RUNNING = False
BOT_STATUS = "Idle"
LIVE_EXCHANGE = "NSE"
MAX_SYMBOLS_PER_CYCLE = 50

# --- [STRATEGY CONFIG] ---
ACTIVE_STRATEGY = 'RSI'
TIMEFRAME = "minute"
TARGET = 0.5
STOPLOSS = 0.5
BUY_SLIPPAGE = 0.05
SELL_SLIPPAGE = 0.05
LOOKBACK_DAYS_GREEN = 0.5
LOOKBACK_DAYS_RSI = 2.0

# RSI Specific
BUY_LEVEL = 30
SELL_LEVEL = 70
PERIOD = 14
