
import os
import sys
import pandas as pd
import requests
import json
import logging
import psycopg2


# Agent URL
AGENT_URL = "http://192.168.122.121:8001"

# DB Config
DB_HOST = "localhost"
DB_NAME = "jesse_db"
DB_USER = "jesse_user"
DB_PASS = "password"
DB_PORT = "5432"

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h"]
# Approx 2 years counts
COUNTS = {
    "1m": 90000,   # Capped to avoid Server 404/Timeout
    "5m": 90000,   # ~300 days of 5m
    "15m": 70200,  # 2 years matches
    "30m": 35100,  # 2 years matches
    "1h": 17600,   # 2 years matches
    "4h": 4400     # 2 years matches
}

SYMBOLS_MAP = {
    "GOLD": "GOLD-USDT",
    "BTCUSD": "BTC-USDT"
}

def fetch_data(agent_symbol, timeframe):
    count = COUNTS.get(timeframe, 10000)
    
    print(f"Fetching {count} candles for {agent_symbol} {timeframe} from {AGENT_URL}...")
    
    try:
        url = f"{AGENT_URL}/data/{agent_symbol}/{timeframe}?n={count}"
        # High timeout for large data
        resp = requests.get(url, timeout=120) 
        if resp.status_code == 404:
            print(f"Error 404 for {url}. Maybe symbol mismatch?")
            return None
        resp.raise_for_status()
        
        data = resp.json()
        rates = data if isinstance(data, list) else data.get('candles', [])
        
        if not rates:
            print(f"No data received for {agent_symbol} {timeframe}")
            return None
            
        print(f"Received {len(rates)} candles for {agent_symbol} {timeframe}.")
        df = pd.DataFrame(rates)
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
        return df
        
    except Exception as e:
        print(f"Fetch Error ({agent_symbol} {timeframe}): {e}")
        return None

def drop_table(cursor):
    try:
        cursor.execute("DROP TABLE IF EXISTS candle CASCADE;")
        print("Dropped old candle table.")
    except Exception as e:
        print(f"Drop error: {e}")

def insert_to_jesse():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    cursor = conn.cursor()
    
    # Drop table first to fix schema mismatch (UndefinedColumn timeframe)
    drop_table(cursor)

    # Create Table with Correct Schema (including timeframe)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candle (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            timestamp BIGINT NOT NULL,
            open DOUBLE PRECISION NOT NULL,
            close DOUBLE PRECISION NOT NULL,
            high DOUBLE PRECISION NOT NULL,
            low DOUBLE PRECISION NOT NULL,
            volume DOUBLE PRECISION NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            exchange VARCHAR(50) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            UNIQUE(exchange, symbol, timeframe, timestamp)
        );
    """)
    conn.commit()
    
    exchange_str = "Custom" 
    
    for agent_symbol, jesse_symbol in SYMBOLS_MAP.items():
        print(f"--- Processing {agent_symbol} -> {jesse_symbol} ---")
        for tf in TIMEFRAMES:
            df = fetch_data(agent_symbol, tf)
            if df is None or df.empty:
                continue
                
            print(f"Inserting {len(df)} candles for {jesse_symbol} {tf}...")
            
            args_list = []
            for row in df.itertuples():
                ts = int(row.time.timestamp() * 1000)
                # Jesse expectation: timestamp, open, close, high, low, volume
                # DB schema: timestamp, open, close, high, low, volume, symbol, exchange, timeframe
                # Wait, schema order in INSERT stmt must match values.
                # values: ts, row.open, row.high, row.low, row.close, row.tick_volume, jesse_symbol, exchange_str, tf
                args_list.append((ts, row.open, row.high, row.low, row.close, row.tick_volume, jesse_symbol, exchange_str, tf))
                
            # Bulk Insert
            query = "INSERT INTO candle (timestamp, open, high, low, close, volume, symbol, exchange, timeframe) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"
            
            try:
                 cursor.executemany(query, args_list)
                 conn.commit()
                 print(f"Inserted {len(df)} candles for {jesse_symbol} {tf}.")
            except Exception as e:
                 print(f"Insert Error {jesse_symbol} {tf}: {e}")
                 conn.rollback()

    conn.close()

if __name__ == "__main__":
    insert_to_jesse()
