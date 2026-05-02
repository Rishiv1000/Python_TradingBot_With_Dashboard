import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import mysql.connector

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db_manager.config as config
from db_manager.config import BACKTEST_EXCHANGES, SLIPPAGE_PCT, STOPLOSS_PCT, TARGET_PCT, TIMEFRAME
from main_runner import generate_or_load_session
from engine_symbol_data import build_symbol_dataframe, fetch_runtime_symbols

backtest_data_cache = {}

def save_backtest_excel(results, output_file="backtest_report.xlsx"):
    report_path = os.path.join(os.path.dirname(__file__), output_file)
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
        prev2, prev1 = df.iloc[i - 2], df.iloc[i - 1]
        if prev2["candle_color"] == "GREEN" and prev1["candle_color"] == "GREEN": return True
        return False

class ExitEngineSim:
    def __init__(self, target_pct, stoploss_pct, slippage_pct):
        self.target_pct, self.stoploss_pct, self.slippage_pct = target_pct, stoploss_pct, slippage_pct
    def check_exit(self, position, cur_candle):
        buy_price = position["buyprice"]
        target_price = buy_price * (1 + self.target_pct / 100)
        sl_price = buy_price * (1 - self.stoploss_pct / 100)
        hit_target = float(cur_candle["high"]) >= target_price
        hit_sl = float(cur_candle["low"]) <= sl_price
        if hit_target or hit_sl:
            raw_sell = target_price if hit_target else sl_price
            sell_price = raw_sell * (1 - (self.slippage_pct / 100))
            return {"symbol": position["symbol"], "buytime": position["buytime"], "buyprice": buy_price, "selltime": cur_candle["date"], "sellprice": sell_price, "pnl": sell_price - buy_price, "reason": "TARGET" if hit_target else "SL", "slippage": buy_price * (self.slippage_pct / 100), "mode": "BACKTEST"}
        return None

def run_backtest(days=10):
    kite = generate_or_load_session()
    symbols = fetch_runtime_symbols(kite)
    entry_engine = EntryEngineSim()
    exit_engine = ExitEngineSim(TARGET_PCT, STOPLOSS_PCT, SLIPPAGE_PCT)
    all_results = []
    for item in symbols:
        symbol, token = item["symbol"], item["token"]
        try:
            to_date = datetime.now(); from_date = to_date - timedelta(days=days)
            records = kite.historical_data(token, from_date, to_date, TIMEFRAME)
            df = build_symbol_dataframe(records); backtest_data_cache[symbol] = df
        except: continue
        position = None
        for i in range(len(df)):
            cur_candle = df.iloc[i]
            if position is None:
                if entry_engine.check_signal(df, i, symbol):
                    position = {"symbol": symbol, "buytime": cur_candle["date"], "buyprice": float(cur_candle["open"])}
            else:
                trade_result = exit_engine.check_exit(position, cur_candle)
                if trade_result: all_results.append(trade_result); position = None
    save_backtest_excel(all_results)
    return all_results
