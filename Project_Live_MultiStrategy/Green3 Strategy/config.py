import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(STRATEGY_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from shared.base_config import *

STRATEGY_NAME = "GREEN3"
SYMBOLS_TABLE = "symbols_green3"

# Strategy Specific Params
TARGET        = 0.1
STOPLOSS      = 0.1
LOOKBACK_DAYS = 0.05  # ~3 days of 1-min candles
