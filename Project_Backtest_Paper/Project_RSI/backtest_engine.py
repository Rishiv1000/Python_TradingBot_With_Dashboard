import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import mysql.connector

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db_manager.config as config
from main_runner import generate_or_load_session
from engine_symbol_data import build_symbol_dataframe, fetch_runtime_symbols

backtest_data_cache = {}

def save_backtest_excel(results, output_file="backtest_report.xlsx"):
    report_path = os.path.join(config.DB_MANAGER_DIR, output_file)
    try:
        if not results and not backtest_data_cache: return None
        with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
            if results:
                df_trades = pd.DataFrame(results)
                df_trades.to_excel(writer, sheet_name="All_Trades", index=False)
            for symbol, df_candles in backtest_data_cache.items():
                sheet_name = f"Data_{symbol}"[:31]
                df_candles.to_excel(writer, sheet_name=sheet_name, index=False)
            if results:
                summary = pd.DataFrame([{"total_trades": len(df_trades), "win_rate": (len(df_trades[df_trades["pnl"] > 0]) / len(df_trades)) * 100, "net_pnl": df_trades["pnl"].sum()}])
                summary.to_excel(writer, sheet_name="Summary", index=False)
        return report_path
    except Exception as e:
        print(f"❌ Excel Error: {e}"); return None

class EntryEngineSim:
    def check_signal(self, df, i, symbol):
        if i < 2: return False
        # RSI Entry Logic
        cur_rsi = df.iloc[i]["rsi"]
        if pd.isna(cur_rsi): return False
        if cur_rsi <= getattr(config, 'BUY_LEVEL', 30): return True
        return False

class ExitEngineSim:
    def __init__(self, target_pct, stoploss_pct, slippage_pct):
        self.target_pct, self.stoploss_pct, self.slippage_pct = target_pct, stoploss_pct, slippage_pct
    
    def check_exit(self, position, cur_candle, df=None, i=None):
        buy_price = position["buyprice"]
        # Strategy specific exit logic (RSI Only)
        if df is not None and i is not None:
            cur_rsi = df.iloc[i]["rsi"]
            if not pd.isna(cur_rsi) and cur_rsi >= getattr(config, 'SELL_LEVEL', 70):
                sell_price = float(cur_candle["close"]) * (1 - (self.slippage_pct / 100))
                return self._format_result(position, cur_candle, sell_price, "RSI EXIT")
        return None

    def _format_result(self, position, cur_candle, sell_price, reason):
        buy_price = position["buyprice"]
        return {
            "symbol": position["symbol"],
            "buytime": position["buytime"],
            "buyprice": buy_price,
            "selltime": cur_candle["date"],
            "sellprice": sell_price,
            "pnl": sell_price - buy_price,
            "reason": reason,
            "slippage": buy_price * (self.slippage_pct / 100),
            "mode": "BACKTEST"
        }

def run_backtest(days=10):
    kite = generate_or_load_session()
    symbols = fetch_runtime_symbols(kite)
    entry_engine = EntryEngineSim()
    
    target = getattr(config, "TARGET", 0.5)
    sl = getattr(config, "STOPLOSS", 0.5)
    slip = getattr(config, "SELL_SLIPPAGE", 0.10)
    
    exit_engine = ExitEngineSim(target, sl, slip)
    all_results = []
    
    for item in symbols:
        symbol, token = item["symbol"], item["token"]
        try:
            from engine_symbol_data import fetch_symbol_candles
            records = fetch_symbol_candles(kite, token, days=days, timeframe=getattr(config, 'TIMEFRAME', 'minute'))
            df = build_symbol_dataframe(records); backtest_data_cache[symbol] = df
        except: continue
        position = None
        for i in range(len(df)):
            cur_candle = df.iloc[i]
            if position is None:
                if entry_engine.check_signal(df, i, symbol):
                    position = {"symbol": symbol, "buytime": cur_candle["date"], "buyprice": float(cur_candle["open"])}
            else:
                trade_result = exit_engine.check_exit(position, cur_candle, df=df, i=i)
                if trade_result: all_results.append(trade_result); position = None
    
    save_backtest_excel(all_results)
    return all_results

if __name__ == "__main__":
    import sys
    test_days = 10
    if len(sys.argv) > 1:
        try: test_days = int(sys.argv[1])
        except: pass
    print(f"Starting Backtest for {test_days} days...")
    run_backtest(days=test_days)
    print("Backtest Complete.")
