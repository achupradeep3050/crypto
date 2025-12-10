import unittest
import pandas as pd
import numpy as np
from strategy.DEMASuTBB.demasutbb_strategy import DEMASuTBBStrategy

class TestDEMASuTBB(unittest.TestCase):
    def setUp(self):
        self.strategy = DEMASuTBBStrategy()
        
    def test_indicators_calculation(self):
        # Create Dummy Data
        df = pd.DataFrame({
            'high': np.random.uniform(100, 200, 300),
            'low': np.random.uniform(100, 200, 300),
            'close': np.random.uniform(100, 200, 300),
            'open': np.random.uniform(100, 200, 300),
            'volume': np.random.uniform(100, 200, 300)
        })
        
        df = self.strategy.calculate_indicators(df)
        print("Columns found:", df.columns.tolist())
        
        self.assertIn('dema', df.columns)
        self.assertIn('supertrend', df.columns)
        self.assertIn('supertrend_dir', df.columns)
        self.assertIn('bbu', df.columns)
        self.assertIn('bbl', df.columns)
        
    def test_long_signal(self):
        # Scenario: Close > DEMA and SuperTrend is Green (1)
        df = pd.DataFrame({
            'close': [100] * 300,
            'dema': [90] * 300, # DEMA below price
            'supertrend_dir': [1] * 300, # Green
            'bbu': [110] * 300, # BBU above close (valid entry)
            'bbl': [80] * 300   # BBL below close
        })
        
        # We need realistic length for iloc checks
        # Strategy checks iloc[-2]
        
        signal = self.strategy.get_signal(df)
        self.assertEqual(signal, 'long')
        
    def test_short_signal(self):
        # Scenario: Close < DEMA and SuperTrend is Red (-1)
        df = pd.DataFrame({
            'close': [80] * 300,
            'dema': [90] * 300, # DEMA above price
            'supertrend_dir': [-1] * 300, # Red
            'bbu': [100] * 300,
            'bbl': [70] * 300   # BBL below close (valid entry)
        })
        
        signal = self.strategy.get_signal(df)
        self.assertEqual(signal, 'short')

    def test_exit_conditions(self):
        # 1. Long Exit (Hit Upper BB)
        df = pd.DataFrame({'high': [200], 'bbu': [199], 'supertrend_dir': [1]}) # High > BBU
        should_exit = self.strategy.get_exit_signal(df, "long")
        self.assertTrue(should_exit)
        
        # 2. Long Exit (SuperTrend Flip)
        df = pd.DataFrame({'high': [100], 'bbu': [200], 'supertrend_dir': [-1]}) # Flip to Red
        should_exit = self.strategy.get_exit_signal(df, "long")
        self.assertTrue(should_exit)

    def test_no_entry_at_bb_extreme(self):
        # Scenario: Long Signal valid (Close > DEMA, Green), BUT Close > Upper BB
        # Should return None (No Signal)
        df = pd.DataFrame({
            'close': [105] * 300, # Above BBU (100)
            'dema': [90] * 300,
            'supertrend_dir': [1] * 300,
            'bbu': [100] * 300, # Upper BB
            'bbl': [50] * 300
        })
        
        signal = self.strategy.get_signal(df)
        self.assertIsNone(signal, "Should not enter long if Price > Upper BB")
        
        # Scenario: Short Signal valid (Close < DEMA, Red), BUT Close < Lower BB
        df_short = pd.DataFrame({
            'close': [40] * 300, # Below BBL (50)
            'dema': [90] * 300,
            'supertrend_dir': [-1] * 300,
            'bbu': [150] * 300,
            'bbl': [50] * 300 # Lower BB
        })
        
        signal_short = self.strategy.get_signal(df_short)
        self.assertIsNone(signal_short, "Should not enter short if Price < Lower BB")


if __name__ == '__main__':
    unittest.main()
