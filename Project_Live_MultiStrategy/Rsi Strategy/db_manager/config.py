import os
from dotenv import load_dotenv


STRATEGY_NAME = "RSI"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_MANAGER_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
ACCESS_TOKEN_FILE = os.path.join(BASE_DIR, "access_token.txt")

DB_NAME = "trading_bot_rsi"
DB_PATH = os.path.join(DB_MANAGER_DIR, f"{DB_NAME}.db")

DEFAULT_QTY = 1
REAL_TRADING_ENABLED = False
LIVE_EXCHANGE = "NSE"
MAX_SYMBOLS_PER_CYCLE = 50
TIMEFRAME = "minute"

TARGET = 0.5
STOPLOSS = 0.5
BUY_SLIPPAGE = 0.05
SELL_SLIPPAGE = 0.05
LOOKBACK_DAYS = 2.0

BUY_LEVEL = 30
SELL_LEVEL = 70
PERIOD = 14
