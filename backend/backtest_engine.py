import pandas as pd
import aiohttp
import asyncio
from datetime import datetime
from backend.database import db
from backend.config import settings

class BacktestEngine:
    def __init__(self, agent_url):
        self.agent_url = agent_url

    async def get_data(self, symbol, timeframe, start_ts, end_ts):
        """
        Smart Data Fetching:
        1. Check DB for existing candles in range.
        2. If gaps or missing, fetch from Agent (MT5).
        3. Save new data to DB.
        4. Return full DataFrame.
        """
        # 1. Try DB
        cached_data = db.get_candles(symbol, timeframe, start_ts, end_ts)
        
        # If we have enough data (naive check: at least 1 candle per timeframe interval roughly)
        # Proper check would be finding gaps, but for MVP:
        # If DB returns data covering the range, use it.
        # But MT5 fetch is usually fast, so we can fetch to fill gaps.
        # Let's fetch from Agent to ensure freshness and fill cache.
        # NOTE: MT5 `copy_rates_range` is better, but our Agent currently has `copy_rates_from_pos` (n candles).
        # We need to update Agent to support Date Range or just fetch a large N.
        # User said "pull candles from mt5... save in db".
        
        # Current Agent API: /data/{symbol}/{timeframe}?n=100
        # We should probably request a large N to cover the period if cache is empty.
        
        # Strategy: Always fetch fresh large chunk from Agent to Fill DB, then Read from DB.
        # Calculating N based on timeframe is complex. 
        # Simpler: Request N=5000 (enough for recent history) or add Date Range support to Agent.
        # Given constraints, let's stick to N=5000 for now.
        
        if not cached_data:
            print(f"Backtest: Fetching fresh data for {symbol} {timeframe}...")
            async with aiohttp.ClientSession() as session:
                try:
                    # Requesting 10000 candles to clear "history" needs.
                    url = f"{self.agent_url}/data/{symbol}/{timeframe}?n=5000"
                    async with session.get(url, timeout=30) as resp:
                        if resp.status == 200:
                            new_data = await resp.json()
                            if new_data:
                                db.save_candles(symbol, timeframe, new_data)
                                cached_data = new_data # Use what we just got
                        else:
                            print(f"Backtest: API Error {resp.status}")
                except Exception as e:
                    print(f"Backtest: Connection Error {e}")
        
        # Re-query DB significantly if we just saved? 
        # Actually `db.get_candles` filters by timestamp, so relying on DB is safest to respect start/end.
        # If we just fetched N=5000, we saved them. Now we query DB for specific range.
        
        final_data = db.get_candles(symbol, timeframe, start_ts, end_ts)
        if not final_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(final_data)
        # Ensure correct types
        df['time'] = pd.to_numeric(df['time'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        return df

    def run(self, strategy_class, df, start_balance=1000):
        """
        Simulates strategy on DataFrame.
        Assumes strategy has `calculate_indicators` and `get_signal`.
        """
        if df.empty:
            return {"error": "No Data"}

        balance = start_balance
        equity_curve = []
        trades = []
        position = None # {'type': 'long', 'entry': 100, 'size': 1.0}
        
        # Initialize Strategy
        strategy = strategy_class()
        
        # Pre-calc indicators
        df = strategy.calculate_indicators(df)
        
        # Iterate (Skip first 200 for warm up)
        for i in range(200, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1] # For close checks
            
            # Create a mini-slice for strategy if it needs history (most use columns)
            # Strategy expects full DF usually, but handles row-based logic via iloc[-1]
            # To simulate "Live", we should pass df[:i+1]. But that's slow.
            # Most of our strategies are vectorised or check last row.
            # We can hack `get_signal` to accept a row or just use pre-calced columns.
            
            # Our strategies use `curr = df.iloc[-2]` (closed candle).
            # So we need to simulate the "current" moment.
            # Let's assume indicators are already correct in `df`.
            # We just need to check signals at index `i`.
            
            # Adaptation: Our strategies might need slight tweak to accept "current index" or we pass sliced DF.
            # Passing sliced DF df.iloc[:i+1] is safest but slow.
            # Let's try passing sliced for correctness.
            
            window = df.iloc[:i+1]
            
            # 1. Check Exits (if position exists)
            # 1. Check Exits (if position exists)
            if position:
                # Check for strategy exit signal
                should_exit = strategy.get_exit_signal(window, position['type'])
                
                # Check TP/SL
                take_profit_hit = False
                stop_loss_hit = False
                
                if position.get('tp'):
                    if position['type'] == 'long' and curr['high'] >= position['tp']:
                        take_profit_hit = True
                        exit_price = position['tp'] # Assume partial fill at TP? Or slippage? Use TP level.
                    elif position['type'] == 'short' and curr['low'] <= position['tp']:
                        take_profit_hit = True
                        exit_price = position['tp']

                if position.get('sl'):
                    if position['type'] == 'long' and curr['low'] <= position['sl']:
                        stop_loss_hit = True
                        exit_price = position['sl'] 
                    elif position['type'] == 'short' and curr['high'] >= position['sl']:
                        stop_loss_hit = True
                        exit_price = position['sl']

                if should_exit and not (take_profit_hit or stop_loss_hit):
                     exit_price = curr['close'] # Exit at close

                if should_exit or take_profit_hit or stop_loss_hit:
                    # Calculate PnL
                    # If TP/SL hit, exit_price is set above.
                    # Note: If gap past SL, this assumes fill at SL. Optimistic.
                    
                    pnl = (exit_price - position['entry']) * position['size'] if position['type'] == 'long' else \
                          (position['entry'] - exit_price) * position['size']
                          
                    new_balance = balance + pnl
                    
                    if new_balance <= 0:
                         # ... (Bankruptcy logic same as before) ...
                        pnl = -balance 
                        balance = 0
                        trades.append({
                            "entry_time": position['time'],
                            "exit_time": curr['time'],
                            "type": position['type'],
                            "entry": position['entry'],
                            "exit": exit_price,
                            "pnl": pnl,
                            "size": position['size'],
                            "note": "LIQUIDATED"
                        })
                        position = None
                        break 
                    
                    balance = new_balance
                    
                    note = "TP" if take_profit_hit else "SL" if stop_loss_hit else "Signal"
                    
                    trades.append({
                        "entry_time": position['time'],
                        "exit_time": curr['time'],
                        "type": position['type'],
                        "entry": position['entry'],
                        "exit": exit_price,
                        "pnl": pnl,
                        "size": position['size'],
                        "note": note
                    })
                    position = None
            
            # 2. Check Entries (if no position)
            if not position:
                sig = strategy.get_signal(window)
                if sig:
                    entry_price = curr['close']
                    sl, tp = None, None
                    
                    # Call get_entry_params if available
                    if hasattr(strategy, 'get_entry_params'):
                         # Some strategies might return (entry, sl, tp)
                         # We pass 'signal' and 'window' (or full df?)
                         # GoldSniper expects (signal, window)
                         # But wait, logic might vary.
                         # Try/Except? Or assume standard interface.
                         try:
                             ep_res = strategy.get_entry_params(sig, window)
                             if ep_res:
                                 _, sl, tp = ep_res # Return logic: entry, sl, tp
                         except Exception as e:
                             pass
                             # print(f"Entry Params Error: {e}")

                    # Size Calc
                    if balance <= 0: break
                        
                    size = 1.0 # Default
                    if hasattr(strategy, 'get_position_size'):
                        size = strategy.get_position_size(balance)
                        size = max(0.01, size)
                    elif hasattr(strategy, 'fixed_lot'):
                        size = strategy.fixed_lot
                    
                    position = {
                        "type": sig,
                        "entry": entry_price,
                        "size": size,
                        "time": curr['time'],
                        "sl": sl,
                        "tp": tp
                    }
            
            equity_curve.append({"time": curr['time'], "equity": balance})
            
        # Prepare Price Data for Chart
        # Downsample if too large? For 100k points, chart.js might struggle.
        # But let's send full for now or downsample slightly.
        # Sending 100k points to frontend is heavy.
        # Simple Nth sampling if len > 2000
        
        price_data = []
        step = 1
        if len(df) > 2000:
            step = len(df) // 2000
            
        for i in range(0, len(df), step):
            row = df.iloc[i]
            price_data.append({"time": int(row['time']), "close": float(row['close'])})

        return {
            "final_balance": balance,
            "trades": trades,
            "equity_curve": equity_curve,  # Already sampled? No. Should sample entries too if needed.
            "price_data": price_data,
            "total_trades": len(trades),
            "win_rate": len([t for t in trades if t['pnl'] > 0]) / len(trades) if trades else 0
        }
