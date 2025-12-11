import pandas_ta as ta
import pandas as pd

class GoldTrend:
    def __init__(self):
        # Gold 1H Swing Parameters
        self.rsi_buy = 45 # Deep pullback
        self.rsi_sell = 55 # Shallow pullback in downtrend
        self.ema_short = 50
        self.ema_long = 200
        self.sl_atr_mult = 2.0 # Wide SL for Swing
        self.rr_ratio = 3.0 # High Reward
        self.fixed_lot = 0.01 
        
    def get_position_size(self, balance):
        return 0.02 # Fixed Lot (User Request)

    def calculate_indicators(self, df_current: pd.DataFrame, df_higher: pd.DataFrame = None):
        if len(df_current) < self.ema_long + 10:
            return None

        # 1. Trend
        df_current['ema_50'] = ta.ema(df_current['close'], length=self.ema_short)
        df_current['ema_200'] = ta.ema(df_current['close'], length=self.ema_long)
        
        # 2. Oscillator
        df_current['rsi'] = ta.rsi(df_current['close'], length=14)
        
        # 3. Volatility
        df_current['atr'] = ta.atr(df_current['high'], df_current['low'], df_current['close'], length=14)
        
        return df_current

    def get_signal(self, window):
        """
        Swing Entry: Trend Follow Pullback
        """
        if window is None or window.empty: return None
        curr = window.iloc[-2] # Closed
        
        # Trend Conditions
        uptrend = curr['ema_50'] > curr['ema_200'] and curr['close'] > curr['ema_200']
        downtrend = curr['ema_50'] < curr['ema_200'] and curr['close'] < curr['ema_200']
        
        # Pullback Conditions
        # Long: Uptrend + RSI dip
        if uptrend and curr['rsi'] < self.rsi_buy:
             # Additional momentum check? RSI turning up?
             # For simpler backtest: Entry on the dip state
             return "long"
             
        # Short: Downtrend + RSI spike
        if downtrend and curr['rsi'] > self.rsi_sell:
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
        Exit on Trend Reversal
        """
        if df.empty: return False
        curr = df.iloc[-1]
        
        # Simple exit if price crosses Major EMA 200 (Total failure of trend)
        if position_type == 'long':
            if curr['close'] < curr['ema_200']: return True
        elif position_type == 'short':
             if curr['close'] > curr['ema_200']: return True
             
        return False
