import os
import sys

# Path to this file
STRATEGY_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to project root (1 level up)
PROJECT_ROOT = os.path.dirname(STRATEGY_DIR)

# Add project root to sys.path so we can import from shared
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from shared.base_config import *
except ImportError:
    # Fallback for direct execution if needed
    sys.path.append(os.path.join(PROJECT_ROOT))
    from shared.base_config import *

# --- [STRATEGY SPECIFIC TABLE NAMES] ---
SYMBOLS_TABLE = "symbols_green"


# --- [STRATEGY SPECIFIC CONFIG] ---
ACTIVE_STRATEGY = 'GREEN'
TARGET = 0.5
STOPLOSS = 0.5
LOOKBACK_DAYS_GREEN = 0.5
