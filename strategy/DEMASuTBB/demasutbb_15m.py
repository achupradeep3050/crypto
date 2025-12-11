
import pandas_ta as ta
import numpy as np
import pandas as pd
from .demasutbb_strategy import DEMASuTBBStrategy

class DEMASuTBBStrategy15m(DEMASuTBBStrategy):
    def __init__(self):
        super().__init__()
        # 15m Optimization Parameters
        self.dema_period = 200
        self.st_length = 12
        self.st_factor = 3
        self.bb_length = 20
        self.bb_std = 2.0 
        
        # Filters
        self.adx_threshold = 20 
        
        self.fixed_lot = 0.05 
        
    def calculate_indicators(self, df, *args, **kwargs):
        df = super().calculate_indicators(df, *args, **kwargs)
        if df.empty: return df
        
        # Add RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # Add StochRSI (Faster signal than RSI)
        stochrsi = ta.stochrsi(df['close'], length=14, rsi_length=14, k=3, d=3)
        if stochrsi is not None:
             # Columns usually: STOCHRSIk_14_14_3_3, STOCHRSId_14_14_3_3
             k_col = [c for c in stochrsi.columns if c.startswith('STOCHRSIk')][0]
             d_col = [c for c in stochrsi.columns if c.startswith('STOCHRSId')][0]
             df['stoch_k'] = stochrsi[k_col]
             df['stoch_d'] = stochrsi[d_col]
        
        # ADX
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if 'ADX_14' in adx.columns:
            df['adx'] = adx['ADX_14']
            
        return df

    def get_signal(self, df):
        if df.empty or len(df) < 5: return None
        curr = df.iloc[-2]
        
        # Iteration 17: Dynamic Smart Sniper 15m
        
        if np.isnan(curr['dema']): return None
        is_uptrend = curr['close'] > curr['dema'] and curr['supertrend_dir'] == 1
        is_downtrend = curr['close'] < curr['dema'] and curr['supertrend_dir'] == -1
        
        adx = curr['adx']
        signal = None
        
        # Dynamic Thresholds
        rsi_buy = 30
        rsi_sell = 70
        
        if adx > 30: 
            rsi_buy = 40 # Aggressive in strong trend
            rsi_sell = 60
        
        if is_uptrend and adx > 20: 
            if curr['rsi'] < rsi_buy and curr['close'] > curr['open']:
                 if curr['close'] < curr['bbu']:
                     signal = "long"
                     
        elif is_downtrend and adx > 20:
             if curr['rsi'] > rsi_sell and curr['close'] < curr['open']:
                 if curr['close'] > curr['bbl']:
                     signal = "short"
        
        return signal

    def get_exit_signal(self, df, position_type):
        if df.empty: return False
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # RSI Trailing Logic
        if position_type == "long":
            if curr['rsi'] > 55 and curr['rsi'] < prev['rsi']: return True
            if curr['rsi'] > 75: return True
            
        elif position_type == "short":
            if curr['rsi'] < 45 and curr['rsi'] > prev['rsi']: return True
            if curr['rsi'] < 25: return True
            
        return False
