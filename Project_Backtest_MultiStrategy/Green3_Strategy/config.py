import os
import sys

STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(STRATEGY_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from shared.base_config import *
except ImportError:
    sys.path.append(PROJECT_ROOT)
    from shared.base_config import *

# --- [STRATEGY SPECIFIC TABLE NAMES] ---
SYMBOLS_TABLE = "symbols_green3"

# --- [STRATEGY SPECIFIC CONFIG] ---
ACTIVE_STRATEGY = 'GREEN3'
TARGET = 0.5
STOPLOSS = 0.5
LOOKBACK_DAYS_GREEN3 = 3.0
