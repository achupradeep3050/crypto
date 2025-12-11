import pandas_ta as ta
import pandas as pd

class BitcoinBreakout:
    def __init__(self):
        # Parameters optimized for higher win rate & stability
        self.breakout_period = 50
        self.adx_min = 25
        self.ema_length = 200 # Stronger Trend Filter
        self.sl_atr_mult = 1.5
        self.rr_ratio = 3.0 # Higher Risk:Reward

    def get_position_size(self, balance):
        return 0.10 # FIXED LOT SIZE (User Request)

    def calculate_indicators(self, df_current: pd.DataFrame, df_higher: pd.DataFrame = None):
        """
        Calculates indicators for the Breakout strategy.
        """
        # Ensure sufficient data
        if len(df_current) < self.breakout_period + 10:
            return None

        # 1. Breakout Levels (Donchian Channel)
        # Shift 1 to avoid lookahead (Don't breakout of current candle's own high)
        df_current['high_n'] = df_current['high'].rolling(self.breakout_period).max().shift(1)
        df_current['low_n'] = df_current['low'].rolling(self.breakout_period).min().shift(1)
        
        # 2. Trend (EMA)
        df_current['ema_trend'] = ta.ema(df_current['close'], length=self.ema_length)
        
        # 3. Filter (ADX)
        adx = ta.adx(df_current['high'], df_current['low'], df_current['close'], length=14)
        df_current['adx'] = adx['ADX_14']
        
        # 4. Volatility (ATR) for SL/TP
        df_current['atr'] = ta.atr(df_current['high'], df_current['low'], df_current['close'], length=14)
        
        return df_current

    def get_signal(self, window):
        """
        Returns 'long', 'short', or None.
        Check strict breakout conditions.
        """
        if window is None or window.empty: return None
        curr = window.iloc[-2] # Closed Candle
        
        # Conditions
        trend_up = curr['close'] > curr['ema_trend']
        trend_down = curr['close'] < curr['ema_trend']
        strong = curr['adx'] > self.adx_min
        
        # Long Breakout
        # Price must have closed ABOVE the N-period High
        if trend_up and strong and curr['close'] > curr['high_n']:
            return "long"
            
        # Short Breakout
        # Price must have closed BELOW the N-period Low
        if trend_down and strong and curr['close'] < curr['low_n']:
            return "short"
            
        return None

    def get_entry_params(self, signal, indicators):
        """
        Returns entry, sl, tp.
        """
        # "indicators" here is usually the row or df. 
        # For this system, we expect 'indicators' to be the latest row (dict like)
        # But if it's the full DF, we take last.
        
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
        Dynamic Exit? 
        Breakout strategy usually rides until TP/SL or Trend Reversal.
        Let's allow exit on EMA crossover.
        """
        if df.empty: return False
        curr = df.iloc[-1]
        
        if position_type == 'long':
            if curr['close'] < curr['ema_trend']: return True
            
        elif position_type == 'short':
            if curr['close'] > curr['ema_trend']: return True
            
        return False
