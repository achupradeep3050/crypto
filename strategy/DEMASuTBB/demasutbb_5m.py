import pandas_ta as ta
import numpy as np
import pandas as pd
from .demasutbb_strategy import DEMASuTBBStrategy

class DEMASuTBBStrategy5m(DEMASuTBBStrategy):
    def __init__(self):
        super().__init__()
        # Optimization Parameters for 5m Scalping
        self.dema_period = 200
        self.st_length = 12
        self.st_factor = 3
        # Use Standard BB
        self.bb_length = 20
        self.bb_std = 2.0 
        
        # New Filters
        self.adx_threshold = 20 # Stronger Trend Requirement (default was implicit or low)
        self.rsi_buy_max = 68 # Don't buy if RSI > 68 (Overbought)
        self.rsi_sell_min = 32 # Don't sell if RSI < 32 (Oversold)
        
        self.fixed_lot = 0.05 # Aggressive lot for scalping
        
    def calculate_indicators(self, df, *args, **kwargs):
        df = super().calculate_indicators(df, *args, **kwargs)
        if df.empty: return df
        
        # Add RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # Add ADX
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if 'ADX_14' in adx.columns:
            df['adx'] = adx['ADX_14']
            
        # Add Heikin Ashi
        ha = ta.ha(df['open'], df['high'], df['low'], df['close'])
        if ha is not None:
             # Columns: HA_open, HA_high, HA_low, HA_close
             df['ha_open'] = ha['HA_open']
             df['ha_close'] = ha['HA_close']

        # 1H Trend (for safety)
        if 'time' in df.columns:
            df_curr = df.copy()
            df_curr['datetime'] = pd.to_datetime(df_curr['time'], unit='s')
            df_curr.set_index('datetime', inplace=True)
            df_1h = df_curr.resample('1h').agg({'close': 'last'}).dropna()
            
            # Simple 1H SMA 50 Trend
            sma_1h = ta.sma(df_1h['close'], length=50)
            df_1h['sma_50'] = sma_1h
            
            # Merge
            df_1h_shifted = df_1h[['sma_50']].shift(1)
            df_merged = df_curr.join(df_1h_shifted.reindex(df_curr.index, method='ffill'))
            df['trend_1h_sma'] = df_merged['sma_50'].values
        else:
             df['trend_1h_sma'] = 0

        return df

    def get_signal(self, df):
        if df.empty or len(df) < 5: return None
        curr = df.iloc[-2] # Closed
        
        # Iteration 17: Dynamic Smart Sniper + Trailing (Goal: 85% WR)
        
        trend_4h = curr.get('trend_1h_sma', 0) 
        if trend_4h == 0: trend_4h = curr['close'] 
        is_uptrend = curr['close'] > trend_4h
        is_downtrend = curr['close'] < trend_4h
        
        adx = curr['adx']
        
        # Relaxed Entry for Volume
        rsi_buy = 30
        rsi_sell = 70
        
        if adx > 30: # Strong Trend
            rsi_buy = 40 # Aggressive
            rsi_sell = 60
            
        signal = None
        
        if is_uptrend and adx > 20: 
             # Long
             if curr['rsi'] < rsi_buy and curr['close'] > curr['open']:
                  if curr['close'] < curr['bbu']:
                      signal = "long"
        
        elif is_downtrend and adx > 20:
             # Short
             if curr['rsi'] > rsi_sell and curr['close'] < curr['open']:
                  if curr['close'] > curr['bbl']:
                      signal = "short"
        
        return signal

    def get_exit_signal(self, df, position_type):
        if df.empty: return False
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # RSI Trailing Logic
        # We don't have state (entry RSI), but we can check momentum loss.
        # If RSI was high and tick down -> Exit.
        
        if position_type == "long":
            # Exit if RSI turns down from overbought zone
            if curr['rsi'] > 50 and curr['rsi'] < prev['rsi']:
                 return True
            # Hard Exit
            if curr['rsi'] > 70: return True
            
        elif position_type == "short":
            # Exit if RSI turns up from oversold zone
            if curr['rsi'] < 50 and curr['rsi'] > prev['rsi']:
                return True
            # Hard Exit
            if curr['rsi'] < 30: return True
            
        return False
