import os
import sys

SETUP_DIR    = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR   = os.path.dirname(SETUP_DIR)
PROJECT_ROOT = os.path.dirname(SHARED_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.base_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from shared.setup_system.setup_db import initialize_live_database


def setup_all_databases():
    print("Starting Live Multi-Strategy Database Setup...")
    success = initialize_live_database(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
    if success:
        print("All tables initialized successfully.")
    else:
        print("Database setup failed — check MySQL connection and credentials.")
    return success


if __name__ == "__main__":
    setup_all_databases()
