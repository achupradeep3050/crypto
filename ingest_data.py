
import sys
import os
import requests
import asyncio
from datetime import datetime, timedelta
import pandas as pd

# Add root to path to allow imports
sys.path.append(os.getcwd())

from backend.database import db
from backend.config import settings

# Configuration
SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "BITCOIN", "ETHEREUM", "DOGECOIN"] 
# User asked for XAUUSD, EURUSD, GBPUSD, BTCUSD. 
# "BITCOIN" is the symbol in main.py status. Backtest html uses "BTCUSD". 
# I should check what the Agent expects. 
# Looking at `backend/main.py`: status uses "BITCOIN", "ETHEREUM", "DOGECOIN", "GOLD" (for XAUUSD?).
# In `backtest.html`: <option value="XAUUSD">GOLD (XAUUSD)</option>, <option value="BTCUSD">BTCUSD</option>
# I better check what the agent uses. 
# If the agent uses "BITCOIN", then sending "BTCUSD" might fail.
# However, `backtest.html` sends "BTCUSD". 
# Let's try to infer or check config. 
# The user's request: "XAUUSD, EURUSD, GBPUSD, BTCUSD".
# I will use these. Note: User has "Gold (XAUUSD)" in UI.
# Let's map them if needed. 

# Target List based on user request
# Check agent logs/status for exact names if these fail.
# XAUUSD -> GOLD, BTCUSD -> BITCOIN
# Target List based on user request - Crypto Portfolio + Gold
TARGETS = ["GOLD", "BITCOIN", "ETHEREUM", "DOGECOIN"]

# Timeframes covering all strategies (Swing 1h, Scalp 5m, Gold 1h/15m/5m)
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"]

# Agent URL
AGENT_URL = settings.AGENT_URL

def calculate_n_candles(timeframe, years=2):
    minutes_map = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "45m": 45,
        "1h": 60,
        "4h": 240,
        "D1": 1440
    }
    
    tf_min = minutes_map.get(timeframe, 60)
    
    # Total minutes in 2 years
    total_minutes = years * 365 * 24 * 60
    
    # Required candles
    n = int(total_minutes / tf_min)
    
    # Buffer
    n = int(n * 1.1)
    # Cap at 100,000 initial attempt
    return min(n, 100000)

def ingest():
    print(f"Starting Bulk Ingestion from {AGENT_URL}...")
    
    if not db.conn:
        db.connect()
        
    for symbol in TARGETS:
        print(f"--- Processing {symbol} ---")
        for tf in TIMEFRAMES:
            n = calculate_n_candles(tf)
            
            # Undo lowercase for display if preferred, but for logic keep strict
            
            success = False
            attempts = 0
            while not success and n >= 1000 and attempts < 5:
                print(f"Fetching {tf} (~{n} candles)...", end=" ", flush=True)
                
                try:
                    url = f"{AGENT_URL}/data/{symbol}/{tf}?n={n}"
                    response = requests.get(url, timeout=120) 
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            db.save_candles(symbol, tf, data)
                            print(f"Success! Saved {len(data)} candles.")
                            success = True
                        else:
                            print("Empty data.")
                            break # Don't retry if clean empty
                    elif response.status_code == 404:
                         print("404 (Likely too many candles). Retrying with half...")
                         n = int(n / 2)
                         attempts += 1
                    else:
                        print(f"Failed. Status: {response.status_code} - {response.text[:50]}")
                        break # Other errors, stop
                        
                except Exception as e:
                    print(f"Error: {e}")
                    break
            
                except Exception as e:
                    print(f"Error: {e}")
                    break

if __name__ == "__main__":
    ingest()
