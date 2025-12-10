from strategy.mean_reversion import MeanReversionRSI

def test_doge_params():
    strategy = MeanReversionRSI()
    
    # DOGE Scenario
    # Price = 0.38
    # ATR = 0.002
    
    indicators = {
        "bb_lower": 0.37500, # Entry for Long
        "bb_upper": 0.38500, # TP for Long
        "atr": 0.00200,      # ATR
    }
    
    print("\n--- DOGE Long Test ---")
    signal = 'long'
    entry, sl, tp = strategy.get_entry_params(signal, indicators)
    
    print(f"Entry: {entry}")
    print(f"SL: {sl}")
    print(f"TP: {tp}")
    
    # Check Logic
    # SL = Entry - 6*ATR = 0.375 - 0.012 = 0.363
    # TP = Upper = 0.385
    
    expected_sl = 0.363
    
    print(f"Calculated SL: {sl}")
    print(f"Expected SL: {expected_sl}")
    print(f"Distance SL: {entry - sl}")
    print(f"Distance TP: {tp - entry}")
    
    if abs(sl - expected_sl) < 0.00001:
        print("✅ SL Valid")
    else:
        print("❌ SL Invalid Calculation")

    # Rounding Check (What the Agent will receive before my fix)
    print(f"Entry (rounded 5): {round(entry, 5)}")
    print(f"SL (rounded 5): {round(sl, 5)}")
    print(f"TP (rounded 5): {round(tp, 5)}")

if __name__ == "__main__":
    test_doge_params()
