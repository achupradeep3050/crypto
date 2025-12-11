import requests
import sys

# Backend URL (Local)
BACKEND_URL = "http://localhost:8001"

def run_test_trade():
    print("Sending Test Trade Request to Backend...")
    payload = {
        "strategy": "gold_1h", # Use a known valid strategy key
        "symbol": "GOLD",
        "action": "long",
        "order_type": "limit" # Limit to avoid immediate fill/loss
    }
    
    try:
        resp = requests.post(f"{BACKEND_URL}/api/test_trade", json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[SUCCESS] {resp.json()}")
            return True
        else:
            print(f"[ERROR] HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Could not reach backend: {e}")
        return False

if __name__ == "__main__":
    run_test_trade()
