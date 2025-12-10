import pandas_ta as ta
import pandas as pd

class TMAStrategy:
    def __init__(self):
        self.tema_length = 50
        self.cmo_length = 10
        self.adx_length = 14
        self.adx_threshold = 25
        self.cmo_oversold = -50
        self.cmo_overbought = 50

    def calculate_indicators(self, df_current: pd.DataFrame, df_higher: pd.DataFrame = None):
        """
        Calculates indicators. Uses Dual Timeframe logic.
        df_higher (e.g. 4H): Used for Trend (TEMA) and Strength (ADX).
        df_current (e.g. 15m): Used for Entry Timing (CMO).
        """
        if df_higher is None or len(df_higher) < max(self.tema_length, self.adx_length) + 10:
            return None
        if len(df_current) < self.cmo_length + 10:
            return None

        # Higher Timeframe Indicators (Trend)
        tema_high = ta.tema(df_higher['close'], length=self.tema_length)
        adx_high = ta.adx(df_higher['high'], df_higher['low'], df_higher['close'], length=self.adx_length)
        
        # Current Timeframe Indicators (Entry)
        cmo_curr = ta.cmo(df_current['close'], length=self.cmo_length)
        atr_curr = ta.atr(df_current['high'], df_current['low'], df_current['close'], length=14)

        if tema_high is None or adx_high is None or cmo_curr is None or atr_curr is None:
            return None

        # We compare Current Price to Higher TF TEMA? 
        # Usually we compare Higher TF Price to Higher TF TEMA for *Trend Direction*.
        # Let's say Trend is UP if Close_High > TEMA_High.
        
        result = {
            "close": df_current['close'].iloc[-1], # Execution Price
            "close_high": df_higher['close'].iloc[-1], # For Trend Check
            "tema": tema_high.iloc[-1],
            "cmo": cmo_curr.iloc[-1],
            "adx": adx_high['ADX_14'].iloc[-1],
            "atr": atr_curr.iloc[-1]
        }
        return result

    def get_signal(self, indicators):
        if not indicators:
            return None

        close_high = indicators['close_high'] # Use Higher TF close for Trend confirmation
        tema = indicators['tema']
        cmo = indicators['cmo']
        adx = indicators['adx']

        # Trend Logic (Higher TF)
        trend_up = close_high > tema
        trend_down = close_high < tema
        strong_trend = adx > self.adx_threshold

        # Entry Logic (Current TF Pullback)
        # Long: Trend UP + Strong + Oversold Pullback
        if trend_up and strong_trend and cmo < self.cmo_oversold:
            return "long"

        # Short: Trend DOWN + Strong + Overbought Pullback
        if trend_down and strong_trend and cmo > self.cmo_overbought:
            return "short"

        return None

    def get_entry_params(self, signal, indicators):
        """
        Returns entry price, stop loss, and take profit.
        Using ATR based SL/TP as strict rules weren't provided in title, standard is 1.5-2x ATR usually.
        Let's use 2x ATR for SL and 4x ATR for TP (2:1 Ratio) or similar.
        Strategy in video often uses fixed RR. Let's go with 3x ATR SL.
        """
        entry = indicators['close'] # Market Entry essentially, or close price
        atr = indicators['atr']
        
        if signal == 'long':
            sl = entry - (atr * 3)
            tp = entry + (atr * 6) # 1:2 RR
            return entry, sl, tp
            
        elif signal == 'short':
            sl = entry + (atr * 3)
            tp = entry - (atr * 6) # 1:2 RR
            return entry, sl, tp
            
        return None, None, None
