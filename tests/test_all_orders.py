import requests
import json
import time

AGENT_URL = "http://192.168.122.121:8001"
SYMBOL = "BITCOIN"
VOLUME = 0.01

def send_trade(action, order_type, price, sl, tp, desc):
    print(f"\n--- TESTING: {desc} ---")
    payload = {
        "symbol": SYMBOL,
        "action": action,
        "volume": VOLUME,
        "price": price,
        "sl": sl,
        "tp": tp,
        "order_type": order_type,
        "deviation": 20 # The Fix
    }
    
    try:
        start_t = time.time()
        res = requests.post(f"{AGENT_URL}/trade", json=payload, timeout=10)
        end_t = time.time()
        
        if res.status_code == 200:
            print(f"✅ SUCCESS ({int((end_t-start_t)*1000)}ms)")
            print("Response:", res.json())
        else:
            print(f"❌ FAILED (Status {res.status_code})")
            print("Response:", res.text)
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

def get_current_price():
    try:
        res = requests.get(f"{AGENT_URL}/data/{SYMBOL}/1m?n=1")
        if res.status_code == 200:
            data = res.json()
            return data[-1]['close']
    except:
        pass
    return 100000.0 # Fallback

if __name__ == "__main__":
    print(f"Connecting to Agent at {AGENT_URL}...")
    
    # Get Price for Limit Orders
    current_price = get_current_price()
    print(f"Current Price Reference: {current_price}")
    
    # 1. Market Buy
    send_trade("buy", "market", 0, 0, 0, "Market BUY")
    time.sleep(1)
    
    # 2. Market Sell
    send_trade("sell", "market", 0, 0, 0, "Market SELL")
    time.sleep(1)
    
    # 3. Limit Buy (Wait for Price - 1000)
    limit_buy_price = int(current_price - 1000)
    send_trade("buy", "limit", limit_buy_price, limit_buy_price-500, limit_buy_price+2000, f"Limit BUY @ {limit_buy_price}")
    time.sleep(1)
    
    # 4. Limit Sell (Wait for Price + 1000)
    limit_sell_price = int(current_price + 1000)
    send_trade("sell", "limit", limit_sell_price, limit_sell_price+500, limit_sell_price-2000, f"Limit SELL @ {limit_sell_price}")
