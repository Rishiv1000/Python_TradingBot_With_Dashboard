import os
import sys

# Path to this file
STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to project root (1 level up)
PROJECT_ROOT = os.path.dirname(STRATEGY_DIR)

# Add project root to sys.path
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from shared.base_config import *

STRATEGY_NAME = "GREEN"
SYMBOLS_TABLE = "symbols_green"

# Strategy Specific Params
TARGET = 0.1
STOPLOSS = 0.1
LOOKBACK_DAYS = 0.05  # ~3 days of 1-min candles
