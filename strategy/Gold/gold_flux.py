import pandas_ta as ta
import pandas as pd

class GoldFlux:
    def __init__(self):
        # Gold 5m Scalp Parameters
        self.breakout_period = 20 # Faster breakout
        self.adx_min = 25
        self.ema_length = 200 # Major trend filter
        self.sl_atr_mult = 1.0 # Tight SL for Scalp
        self.rr_ratio = 3.0 # High Reward
        self.fixed_lot = 0.01 # Fallback
        
    def get_position_size(self, balance):
        return 0.02 # Fixed Lot (User Request)

    def calculate_indicators(self, df_current: pd.DataFrame, df_higher: pd.DataFrame = None):
        """
        Calculates indicators for Gold Scalp.
        """
        if len(df_current) < self.ema_length + 10:
            return None

        # 1. Breakout Levels
        df_current['high_n'] = df_current['high'].rolling(self.breakout_period).max().shift(1)
        df_current['low_n'] = df_current['low'].rolling(self.breakout_period).min().shift(1)
        
        # 2. Trend
        df_current['ema_trend'] = ta.ema(df_current['close'], length=self.ema_length)
        
        # 3. Filter
        adx = ta.adx(df_current['high'], df_current['low'], df_current['close'], length=14)
        df_current['adx'] = adx['ADX_14']
        
        # 4. Volatility
        df_current['atr'] = ta.atr(df_current['high'], df_current['low'], df_current['close'], length=14)
        
        return df_current

    def get_signal(self, window):
        """
        Scalp Entry Logic
        """
        if window is None or window.empty: return None
        curr = window.iloc[-2] # Closed Candle
        
        # Conditions
        trend_up = curr['close'] > curr['ema_trend']
        trend_down = curr['close'] < curr['ema_trend']
        strong = curr['adx'] > self.adx_min
        
        # Long Breakout
        if trend_up and strong and curr['close'] > curr['high_n']:
            return "long"
            
        # Short Breakout
        if trend_down and strong and curr['close'] < curr['low_n']:
            return "short"
            
        return None

    def get_entry_params(self, signal, indicators):
        curr = indicators if isinstance(indicators, pd.Series) else indicators.iloc[-1]
        
        entry = curr['close']
        atr = curr['atr']
        dist = atr * self.sl_atr_mult
        
        if signal == 'long':
            sl = entry - dist
            tp = entry + (dist * self.rr_ratio)
            return entry, sl, tp
            
        elif signal == 'short':
            sl = entry + dist
            tp = entry - (dist * self.rr_ratio)
            return entry, sl, tp
            
        return None, None, None

    def get_exit_signal(self, df, position_type):
        """
        Fast Exit on Trend Change
        """
        if df.empty: return False
        curr = df.iloc[-1]
        
        if position_type == 'long':
            # Exit if price falls below EMA 50 (Faster exit than 200)
            ema_fast = ta.ema(df['close'], length=50).iloc[-1]
            if curr['close'] < ema_fast: return True
            
        elif position_type == 'short':
            ema_fast = ta.ema(df['close'], length=50).iloc[-1]
            if curr['close'] > ema_fast: return True
            
        return False
