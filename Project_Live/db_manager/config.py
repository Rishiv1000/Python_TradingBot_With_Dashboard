import os
from dotenv import load_dotenv

# Base directory for the project (One level up from db_manager)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_MANAGER_DIR = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(DB_MANAGER_DIR, ".env")
load_dotenv(env_path)

ACCESS_TOKEN_FILE = os.path.join(DB_MANAGER_DIR, "access_token.txt")

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


LIVE_EXCHANGE = "NSE"
TIMEFRAME = "minute"

TARGET_PCT = 0.5
STOPLOSS_PCT = 0.5
SLIPPAGE_PCT = 0.05
BUY_SLIPPAGE_BUFFER = 0.05
SELL_SLIPPAGE_BUFFER = 0.05

DEFAULT_QTY = 1
MAX_SYMBOLS_PER_CYCLE = 100
CANDLE_LOOKBACK_DAYS = 1
PAPER_TRADE = False

BOT_RUNNING = False
BOT_STATUS = "Idle"
