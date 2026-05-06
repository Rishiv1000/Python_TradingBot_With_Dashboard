import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Path setup — backtest_engine.py lives inside Project_Backtest_MultiStrategy/
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKTEST_RESULTS_DIR = os.path.join(PROJECT_ROOT, "backtest_results")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.kite_session import generate_or_load_session
from shared.candle_data import build_symbol_dataframe

def fetch_extended_candles(kite, token, days, timeframe):
    """Fetches historical data in chunks to bypass Kite API limits."""
    all_records = []
    end_date = datetime.now()
    remaining_days = days
    chunk_size = 30
    
    while remaining_days > 0:
        current_chunk = min(remaining_days, chunk_size)
        start_date = end_date - timedelta(days=current_chunk)
        try:
            records = kite.historical_data(token, start_date, end_date, timeframe)
            if records:
                all_records = records + all_records
            end_date = start_date
            remaining_days -= current_chunk
        except Exception as e:
            print(f"Error fetching chunk: {e}")
            break
    return all_records

class BacktestSimulator:
    def __init__(self, strategy_name, config_module, symbol_data_module):
        self.strategy_name = strategy_name
        self.config = config_module
        self.symbol_data = symbol_data_module

    def run(self, days=30):
        kite = generate_or_load_session(self.config.API_KEY, self.config.ACCESS_TOKEN_FILE)
        if not kite: return []

        symbols = self.symbol_data.fetch_runtime_symbols(kite)
        timeframe = getattr(self.config, "TIMEFRAME", "minute")
        target_pct = float(getattr(self.config, "TARGET", 0.5))
        sl_pct = float(getattr(self.config, "STOPLOSS", 0.5))
        slip_pct = float(getattr(self.config, "SELL_SLIPPAGE", 0.05))
        qty = int(getattr(self.config, "DEFAULT_QTY", 1))

        all_results = []
        for item in symbols:
            symbol, token = item["symbol"], item["token"]
            print(f"Simulating {symbol} ({self.strategy_name}) for {days} days...")
            try:
                records = fetch_extended_candles(kite, token, days, timeframe)
                if not records: continue
                
                # Use strategy-specific dataframe builder
                if hasattr(self.symbol_data, f"build_{self.strategy_name.lower()}_dataframe"):
                    builder = getattr(self.symbol_data, f"build_{self.strategy_name.lower()}_dataframe")
                    df = builder(kite, token) # Note: this builder might only fetch a small range, so we might need a custom one for backtest
                    # Re-build for full range
                    df = build_symbol_dataframe(records)
                    # Apply strategy indicators
                    if self.strategy_name == "GREEN":
                        from Green_Strategy.engine_symbol_data import calculate_candle_color
                        df = calculate_candle_color(df)
                    elif self.strategy_name == "GREEN3":
                        from Green3_Strategy.engine_symbol_data import calculate_candle_color
                        df = calculate_candle_color(df)
                else:
                    df = build_symbol_dataframe(records)

            except Exception as e:
                print(f"Error {symbol}: {e}"); continue

            position = None
            for i in range(len(df)):
                cur_candle = df.iloc[i]
                if position is None:
                    # Check signal
                    signal = False
                    if self.strategy_name == "GREEN" and i >= 2:
                        # Simple Green implementation for sim
                        def get_color(row): return "GREEN" if row["close"] > row["open"] else "RED"
                        if get_color(df.iloc[i-2]) == "GREEN" and get_color(df.iloc[i-1]) == "GREEN":
                            signal = True
                    elif self.strategy_name == "GREEN3" and i >= 3:
                        def get_color(row): return "GREEN" if row["close"] > row["open"] else "RED"
                        if (get_color(df.iloc[i-3]) == "GREEN" and
                            get_color(df.iloc[i-2]) == "GREEN" and
                            get_color(df.iloc[i-1]) == "GREEN"):
                            signal = True
                    elif self.strategy_name == "RSI" and 'rsi' in df.columns:
                        if pd.notna(cur_candle['rsi']) and cur_candle['rsi'] <= getattr(self.config, 'BUY_LEVEL', 30):
                            signal = True
                    
                    if signal:
                        buy_price = float(cur_candle["close"]) * (1 + float(getattr(self.config, 'BUY_SLIPPAGE', 0.05))/100)
                        position = {"symbol": symbol, "buytime": cur_candle["date"], "buyprice": buy_price}
                else:
                    # Check exit
                    exit_triggered = False
                    sell_price = 0
                    reason = ""
                    
                    target_price = position["buyprice"] * (1 + target_pct / 100)
                    sl_price = position["buyprice"] * (1 - sl_pct / 100)
                    
                    if float(cur_candle["high"]) >= target_price:
                        exit_triggered, sell_price, reason = True, target_price, "TARGET"
                    elif float(cur_candle["low"]) <= sl_price:
                        exit_triggered, sell_price, reason = True, sl_price, "SL"
                    
                    if exit_triggered:
                        final_sell = sell_price * (1 - (slip_pct / 100))
                        all_results.append({
                            "symbol": symbol,
                            "buytime": position["buytime"],
                            "buyprice": position["buyprice"],
                            "selltime": cur_candle["date"],
                            "sellprice": final_sell,
                            "pnl": (final_sell - position["buyprice"]) * qty,
                            "reason": reason,
                            "strategy": self.strategy_name,
                            "mode": "BACKTEST"
                        })
                        position = None
        
        # Save Results
        if all_results:
            self._save_to_excel(all_results)
        
        return all_results

    def _save_to_excel(self, results):
        try:
            os.makedirs(BACKTEST_RESULTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(BACKTEST_RESULTS_DIR, f"{self.strategy_name.lower()}_backtest_{timestamp}.xlsx")
            pd.DataFrame(results).to_excel(output_path, index=False)
            print(f"DONE: Backtest Excel saved: {output_path}")
        except Exception as e:
            print(f"ERROR: Excel Save Error: {e}")
