import pandas_ta as ta
import pandas as pd

class MeanReversionRSI:
    def __init__(self):
        pass

    def calculate_indicators(self, df_current: pd.DataFrame, df_higher: pd.DataFrame):
        """
        Calculates indicators for both current and higher timeframes.
        df_current: DataFrame with 1h candles (assuming base TF is 1h based on context logic, or user defined)
        df_higher: DataFrame with 4h candles
        """
        # Ensure sufficient data
        if len(df_current) < 50 or len(df_higher) < 50:
            return None

        # --- Higher Timeframe Indicators (4H) ---
        # RSI
        rsi_higher = ta.rsi(df_higher['close'], length=14)
        
        # SuperTrend (using default length=10, multiplier=3 as commonly used, usually Jesse defaults need checking but 10,3 is standard)
        st_higher = ta.supertrend(df_higher['high'], df_higher['low'], df_higher['close'], length=10, multiplier=3)
        # supertrend returns specific columns like SUPERT_10_3.0, SUPERTs_10_3.0, etc.
        # We need the trend direction. pandas_ta returns 'SUPERTd_10_3.0' which is 1 (up) or -1 (down) 
        
        # ADX
        adx_higher = ta.adx(df_higher['high'], df_higher['low'], df_higher['close'], length=14)
        
        # --- Current Timeframe Indicators ---
        # ADX
        adx_current = ta.adx(df_current['high'], df_current['low'], df_current['close'], length=14)
        
        # Bollinger Bands
        bb_current = ta.bbands(df_current['close'], length=20, std=2)
        
        # ATR
        atr_current = ta.atr(df_current['high'], df_current['low'], df_current['close'], length=14)

        # Combine latest values into a result dict for easy access
        # using iloc[-1] for the latest closed candle value
        
        # Need to handle case where indicators might be NaN at the beginning
        if st_higher is None or rsi_higher is None or adx_higher is None or adx_current is None or bb_current is None or atr_current is None:
            return None

        result = {
            "rsi_higher": rsi_higher.iloc[-1],
            "trend_higher": st_higher['SUPERTd_10_3'].iloc[-1], # 1 for up, -1 for down
            "adx_higher": adx_higher['ADX_14'].iloc[-1],
            "adx_current": adx_current['ADX_14'].iloc[-1],
            "bb_lower": bb_current.iloc[-1, 0],  # Lower Band
            "bb_middle": bb_current.iloc[-1, 1], # Middle Band
            "bb_upper": bb_current.iloc[-1, 2],  # Upper Band
            "atr": atr_current.iloc[-1],
            "close": df_current['close'].iloc[-1]
        }
        return result

    def get_signal(self, indicators):
        """
        Determines entry signal based on indicators.
        Returns: 'long', 'short', or None
        """
        if not indicators:
            return None

        # Long Logic
        # RSI > 70 (4H)
        # SuperTrend == 1 (4H)
        # ADX > 20 (Current)
        # ADX > 40 (4H)
        if (indicators['rsi_higher'] > 70 and 
            indicators['trend_higher'] == 1 and 
            indicators['adx_current'] > 20 and 
            indicators['adx_higher'] > 40):
            return "long"

        # Short Logic
        # RSI < 30 (4H)
        # SuperTrend == -1 (4H)
        # ADX > 20 (Current)
        # ADX > 40 (4H)
        if (indicators['rsi_higher'] < 30 and 
            indicators['trend_higher'] == -1 and 
            indicators['adx_current'] > 20 and 
            indicators['adx_higher'] > 40):
            return "short"
            
        return None

    def get_entry_params(self, signal, indicators):
        """
        Returns entry price, stop loss, and take profit.
        """
        if signal == 'long':
            entry_price = indicators['bb_lower']
            stop_loss = entry_price - (indicators['atr'] * 6)
            take_profit = indicators['bb_upper']
            return entry_price, stop_loss, take_profit
            
        elif signal == 'short':
            entry_price = indicators['bb_upper']
            stop_loss = entry_price + (indicators['atr'] * 6)
            take_profit = indicators['bb_lower']
            return entry_price, stop_loss, take_profit
            
        return None, None, None
