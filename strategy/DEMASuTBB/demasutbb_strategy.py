
import pandas_ta as ta
import numpy as np

class DEMASuTBBStrategy:
    def __init__(self):
        # Parameters
        self.dema_period = 200
        self.st_length = 12
        self.st_factor = 3
        # Bollinger Bands (Exit)
        self.bb_length = 20
        self.bb_std = 2.0 
        
        # Fixed Lot Size for GOLD
        self.fixed_lot = 0.02

    def calculate_indicators(self, df):
        if df.empty: return df
        
        # 1. DEMA 200
        df['dema'] = ta.dema(df['close'], length=self.dema_period)
        
        # 2. SuperTrend (ATR 12, Factor 3)
        st = ta.supertrend(df['high'], df['low'], df['close'], length=self.st_length, multiplier=self.st_factor)
        # Pandas TA output columns might be dynamic, usually: SUPERT_7_3.0, SUPERTd_7_3.0, etc.
        # We need to find them or rename them.
        st_cols = [c for c in st.columns if c.startswith('SUPERT_')]
        st_dir_cols = [c for c in st.columns if c.startswith('SUPERTd_')]
        
        if st_cols and st_dir_cols:
             df['supertrend'] = st[st_cols[0]]
             df['supertrend_dir'] = st[st_dir_cols[0]] # 1 = Up, -1 = Down
        
        # 3. Bollinger Bands
        bb = ta.bbands(df['close'], length=self.bb_length, std=self.bb_std)
        # Columns: BBL, BBM, BBU, BBB, BBP
        # We need BBU (Upper) and BBL (Lower)
        # Names depend on pandas_ta version, usually BBL_length_std
        if bb is not None:
             # BB Columns: BBL, BBM, BBU, BBB, BBP
             # Dynamically find them
             bbu_col = [c for c in bb.columns if c.startswith('BBU')][0]
             bbl_col = [c for c in bb.columns if c.startswith('BBL')][0]
             
             df['bbu'] = bb[bbu_col]
             df['bbl'] = bb[bbl_col]

        return df

    def get_signal(self, df):
        if df.empty or len(df) < 201: return None
        
        # Always look at the last COMPLETED candle for entry signals to avoid repainting
        # "Make sure the candle is closed before entering"
        # Since we fetch live data, the last row (iloc[-1]) is usually the open candle unless we fetch explicitly history.
        # Assuming fetch_candles returns open candle at end, we use iloc[-2].
        # However, standard practice in this bot has been checking iloc[-1]. 
        # CAUTION: If iloc[-1] is live, we must wait or check iloc[-2]. 
        # Let's assume the loop runs somewhat frequently. Safe bet: Check iloc[-2] (confirmed close).
        
        curr = df.iloc[-2]  
        
        # Entry Logic
        # Long: Close > DEMA and SuperTrend == 1 (Green)
        # Short: Close < DEMA and SuperTrend == -1 (Red)
        
        signal = None
        
        # Valid DEMA check
        if np.isnan(curr['dema']) or np.isnan(curr['supertrend_dir']):
            return None

        # Refined Logic ("Secret Tip"): Don't enter if price is already at the exit level (BB).
        # Ensures we don't buy the top or sell the bottom.
        
        if curr['close'] > curr['dema'] and curr['supertrend_dir'] == 1:
            # Long Condition
            # Check: Close must be BELOW Upper BB (Room to move)
            if curr['close'] < curr['bbu']:
                 signal = "long"
                 
        elif curr['close'] < curr['dema'] and curr['supertrend_dir'] == -1:
            # Short Condition
            # Check: Close must be ABOVE Lower BB
            if curr['close'] > curr['bbl']:
                signal = "short"
            
        return signal

    def get_exit_signal(self, df, position_type):
        '''
        Checks for exit conditions based on the CURRENT price (live).
        We can use iloc[-1] (current live candle) for exits as requested "closes once price hits bolinger band".
        Touch = Live price action.
        '''
        if df.empty: return False
        
        curr = df.iloc[-1] 
        # Also check previous closed candle for flip confirmation if needed, but "hits" implies touch.
        
        if position_type == "long":
            # Exit if Price >= Upper BB OR SuperTrend flips to -1 (Red)
            # Use High for touch check on Upper BB? Conservative: Close. 
            # "hits" -> High >= BBU
            if curr['high'] >= curr['bbu']: return True
            if curr['supertrend_dir'] == -1: return True
            
        elif position_type == "short":
             # Exit if Price <= Lower BB OR SuperTrend flips to 1 (Green)
             # "hits" -> Low <= BBL
            if curr['low'] <= curr['bbl']: return True
            if curr['supertrend_dir'] == 1: return True
            
        return False

    def get_entry_params(self, df, signal):
        # Fixed Lot Size
        # No TP set (Exit by signal)
        # SL? User said "no TP set because trade closes...", didn't explicitly forbid SL, but implies manual management.
        # Standard safety SL is good practice, but strategy relies on dynamic exit.
        # We'll set a massive SL/TP just to comply with order structure, or handle via Agent.
        
        entry_price = df['close'].iloc[-1]
        
        # Arbitrary Wide SL/TP because strategy manages exit
        if signal == "long":
            sl = entry_price * 0.90 
            tp = entry_price * 1.50
        else:
            sl = entry_price * 1.10
            tp = entry_price * 0.50
            
        return {
            "qty": self.fixed_lot,
            "sl": sl,
            "tp": tp
        }
