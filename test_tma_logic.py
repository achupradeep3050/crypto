from strategy.TMA.tma_strategy import TMAStrategy

def test_tma_flow():
    strat = TMAStrategy()
    
    print("--- TMA Logic Test ---")
    
    # CASE 1: LONG
    # Rule: Close > TEMA AND ADX > 25 AND CMO < -50
    indicators_long = {
        "close": 105.0,
        "tema": 100.0,      # Close > TEMA
        "adx": 30.0,        # > 25
        "cmo": -60.0,       # < -50 (Oversold)
        "atr": 1.0
    }
    
    sig_long = strat.get_signal(indicators_long)
    print(f"Long Case: {sig_long} (Expected: long)")
    
    if sig_long == 'long':
        entry, sl, tp = strat.get_entry_params(sig_long, indicators_long)
        print(f"  Entry: {entry}")
        print(f"  SL: {sl} (Expected ~102)")
        print(f"  TP: {tp} (Expected ~111)")
    
    # CASE 2: SHORT
    # Rule: Close < TEMA AND ADX > 25 AND CMO > 50
    indicators_short = {
        "close": 95.0,
        "tema": 100.0,     # Close < TEMA
        "adx": 40.0,       # > 25
        "cmo": 70.0,       # > 50 (Overbought)
        "atr": 2.0
    }
    
    sig_short = strat.get_signal(indicators_short)
    print(f"Short Case: {sig_short} (Expected: short)")
    
    if sig_short == 'short':
        entry, sl, tp = strat.get_entry_params(sig_short, indicators_short)
        print(f"  Entry: {entry}")
        print(f"  SL: {sl} (Expected ~101)")
        print(f"  TP: {tp} (Expected ~83)")

    # CASE 3: NO SIGNAL
    indicators_none = {
        "close": 105.0,
        "tema": 100.0,
        "adx": 10.0,       # Low Trend
        "cmo": -60.0,
        "atr": 1.0
    }
    sig_none = strat.get_signal(indicators_none)
    print(f"No Signal Case: {sig_none} (Expected: None)")

if __name__ == "__main__":
    test_tma_flow()
