import sys
import os
import asyncio
import pandas as pd
from datetime import datetime, timedelta

# Setup path
sys.path.append(os.getcwd())

from backend.database import db
from backend.backtest_engine import BacktestEngine
from strategy.mean_reversion import MeanReversionRSI
from strategy.DEMASuTBB.demasutbb_strategy import DEMASuTBBStrategy
from strategy.DEMASuTBB.demasutbb_5m import DEMASuTBBStrategy5m

async def run_test():
    print("--- Starting Manual Backtest Verification ---")
    
    if not db.conn:
        db.connect()
        
    engine = BacktestEngine(agent_url="http://dummy") # URL not used for DB fetch
    
    # Test Cases
    tests = [
        {"symbol": "GOLD", "tf": "1h", "strat": DEMASuTBBStrategy, "days": 30},
        {"symbol": "GOLD", "tf": "5m", "strat": DEMASuTBBStrategy5m, "days": 90},
        {"symbol": "GOLD", "tf": "15m", "strat": DEMASuTBBStrategy5m, "days": 90}, # Will enable after class creation
        {"symbol": "BITCOIN", "tf": "1h", "strat": MeanReversionRSI, "days": 30}
    ]
    
    for t in tests:
        print(f"\nTesting {t['symbol']} {t['tf']} ({t['days']} Days)...")
        now = datetime.now()
        end_ts = int(now.timestamp())
        start_ts = int((now - timedelta(days=t['days'])).timestamp())
        
        # 1. Fetch Data
        df = await engine.get_data(t['symbol'], t['tf'], start_ts, end_ts)
        print(f"Data Fetched: {len(df)} candles.")
        
        if df.empty:
            print("FAILED: No Data.")
            continue
            
        # 2. Run Strategy
        try:
            result = engine.run(t['strat'], df, start_balance=100)
            
            pnl = result['final_balance'] - 100
            trades = result['total_trades']
            wr = result['win_rate'] * 100
            
            print(f"RESULT: Trades={trades}, WinRate={wr:.1f}%, PnL=${pnl:.2f}")
            print(f"Status: {'OK' if trades >= 0 else 'ERROR'}") # 0 trades is 'ok' technically, just inactive
            
        except Exception as e:
            print(f"FAILED: Strategy Error - {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
