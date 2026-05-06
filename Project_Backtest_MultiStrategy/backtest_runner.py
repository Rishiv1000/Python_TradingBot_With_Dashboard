import sys
import os
import argparse

# Path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import importlib
from backtest_engine import BacktestSimulator

def main():
    parser = argparse.ArgumentParser(description="Multi-Strategy Backtest Runner")
    parser.add_argument("--strategy", type=str, default="GREEN", help="Strategy name (GREEN, RSI)")
    parser.add_argument("--days", type=int, default=30, help="Number of historical days")
    args = parser.parse_args()

    strat_name = args.strategy.upper()
    
    # Map strategy to folder
    strategies = {
        "GREEN": "Green_Strategy",
        "RSI": "Rsi_Strategy"
    }

    if strat_name not in strategies:
        print(f"❌ Error: Strategy {strat_name} not found.")
        return

    folder = strategies[strat_name]
    strat_path = os.path.join(BASE_DIR, folder)
    
    if not os.path.exists(strat_path):
        print(f"❌ Error: Strategy folder {folder} not found.")
        return

    sys.path.insert(0, strat_path)
    
    try:
        sys.modules.pop("config", None)
        sys.modules.pop("engine_symbol_data", None)
        cfg_mod = importlib.import_module("config")
        sym_mod = importlib.import_module("engine_symbol_data")
        
        print(f"🧪 Starting {strat_name} Backtest for {args.days} days...")
        sim = BacktestSimulator(strat_name, cfg_mod, sym_mod)
        results = sim.run(days=args.days)
        
        print(f"✅ Backtest Complete!")
        print(f"📈 Total Trades: {len(results)}")
        if results:
            total_pnl = sum(r['pnl'] for r in results)
            print(f"💰 Total PnL: Rs {total_pnl:,.2f}")
            
    except Exception as e:
        print(f"⚠️ Error during backtest: {e}")

if __name__ == "__main__":
    main()
