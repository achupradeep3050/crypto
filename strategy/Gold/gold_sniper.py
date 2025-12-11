import pandas_ta as ta
import pandas as pd

class GoldSniper:
    def __init__(self, time_period=20, rsi_period=2, rsi_lower=5, rsi_upper=95, bb_std=2.0, use_bands=False):
        # Optimized Constants for 15m Timeframe
        self.bb_length = time_period
        self.bb_std = bb_std
        self.rsi_length = rsi_period
        self.rsi_low = rsi_lower
        self.rsi_high = rsi_upper
        self.use_bands = use_bands
        
        # Risk Settings
        self.sl_atr_mult = 1.0 
        self.tp_atr_mult = 1.5 
        self.fixed_lot = 0.01

    def get_position_size(self, balance):
        return 0.02 # FIXED LOT SIZE (User Request)

    def calculate_indicators(self, df: pd.DataFrame, df_higher: pd.DataFrame = None):
        if len(df) < self.bb_length + 10: return None
        
        # 1. Bollinger Bands (Optional but calculated)
        bb = ta.bbands(df['close'], length=self.bb_length, std=self.bb_std)
        if bb is not None:
            cols = bb.columns
            df['bbl'] = bb[cols[0]] 
            df['bbm'] = bb[cols[1]]
            df['bbu'] = bb[cols[2]]
        
        # 2. RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_length)
        
        # 3. ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        return df

    def get_signal(self, window):
        if window is None or window.empty: return None
        curr = window.iloc[-2] # Closed Candle
        
        # Signals based on RSI extremes (Connors RSI style)
        long_condition = curr['rsi'] < self.rsi_low
        short_condition = curr['rsi'] > self.rsi_high
        
        if self.use_bands and 'bbl' in curr:
             long_condition = long_condition and (curr['low'] < curr['bbl'])
             short_condition = short_condition and (curr['high'] > curr['bbu'])

        if long_condition:
            return "long"
            
        if short_condition:
            return "short"
            
        return None

    def get_entry_params(self, signal, indicators):
        curr = indicators if isinstance(indicators, pd.Series) else indicators.iloc[-1]
        
        entry = curr['close']
        atr = curr['atr']
        
        sl_dist = atr * self.sl_atr_mult
        tp_dist = atr * self.tp_atr_mult
        
        if signal == 'long':
            sl = entry - sl_dist
            tp = entry + tp_dist
            return entry, sl, tp
            
        elif signal == 'short':
             sl = entry + sl_dist
             tp = entry - tp_dist
             return entry, sl, tp
            
        return None, None, None

    def get_exit_signal(self, df, position_type):
        # RSI Mean Reversion Exit?
        # Exit if RSI returns to 50?
        if df.empty: return False
        curr = df.iloc[-1]
        
        if position_type == 'long':
            if curr['rsi'] > 50: return True
        elif position_type == 'short':
            if curr['rsi'] < 50: return True
            
        return False
