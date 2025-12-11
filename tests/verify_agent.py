import requests
import sys

# Windows Agent URL (Explicitly set to what is in config)
AGENT_URL = "http://192.168.122.121:8001"

def check_connection():
    print(f"Testing Connection to {AGENT_URL}...")
    try:
        # Check Account Info
        resp = requests.get(f"{AGENT_URL}/account", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[SUCCESS] Connection OK!")
            print(f"Account Balance: {data.get('balance')}")
            print(f"Equity: {data.get('equity')}")
            return True
        else:
            print(f"[ERROR] HTTP {resp.status_code}: {resp.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAILURE] Connection Refused. Is the Windows Agent running?")
        print("Tip: Check if 192.168.122.121 is reachable.")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected: {e}")
        return False

if __name__ == "__main__":
    success = check_connection()
    sys.exit(0 if success else 1)
