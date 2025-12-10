import pandas as pd
from strategy.mean_reversion import MeanReversionRSI

def test_long_signal():
    print("--- Testing LONG Signal Logic ---")
    strategy = MeanReversionRSI()
    
    # Create fake 4H data (Higher TF)
    # We need RSI > 70 and SuperTrend = 1 (Uptrend) and ADX > 40
    # To get RSI > 70, prices must be rising
    prices_high = [100 + i for i in range(50)] # Rising prices
    df_high = pd.DataFrame({
        'high': [p + 2 for p in prices_high],
        'low': [p - 2 for p in prices_high],
        'close': prices_high
    })
    
    # Create fake 1H data (Current TF)
    # We need ADX > 20
    prices_curr = [100 + i for i in range(50)]
    df_curr = pd.DataFrame({
        'high': [p + 2 for p in prices_curr],
        'low': [p - 2 for p in prices_curr],
        'close': prices_curr
    })

    # Calculate indicators
    # Note: We can't easily force pandas_ta to give exact values without enough data points
    # So we will mock the "calculate_indicators" output dictionary directly to test the "get_signal" logic.
    # This isolates the decision making from the math library (which we assume works if used correctly).
    
    mock_indicators_long = {
        "rsi_higher": 75.0,        # > 70 ✅
        "trend_higher": 1,         # Uptrend ✅
        "adx_higher": 45.0,        # > 40 ✅
        "adx_current": 25.0,       # > 20 ✅
        "bb_lower": 95.0,
        "bb_upper": 105.0,
        "bb_middle": 100.0,
        "atr": 1.0,
        "close": 96.0
    }
    
    signal = strategy.get_signal(mock_indicators_long)
    print(f"Inputs: {mock_indicators_long}")
    print(f"Result Signal: {signal}")
    
    if signal == 'long':
        print("✅ LONG Logic Verified")
    else:
        print("❌ LONG Logic Failed")

def test_short_signal():
    print("\n--- Testing SHORT Signal Logic ---")
    strategy = MeanReversionRSI()
    
    mock_indicators_short = {
        "rsi_higher": 25.0,        # < 30 ✅
        "trend_higher": -1,        # Downtrend ✅
        "adx_higher": 45.0,        # > 40 ✅
        "adx_current": 25.0,       # > 20 ✅
        "bb_lower": 95.0,
        "bb_upper": 105.0,
        "bb_middle": 100.0,
        "atr": 1.0,
        "close": 104.0
    }
    
    signal = strategy.get_signal(mock_indicators_short)
    print(f"Result Signal: {signal}")
    
    if signal == 'short':
        print("✅ SHORT Logic Verified")
    else:
        print("❌ SHORT Logic Failed")

if __name__ == "__main__":
    test_long_signal()
    test_short_signal()
