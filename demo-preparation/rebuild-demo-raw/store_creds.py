import requests
import sys

API_URL = "http://127.0.0.1:8001/api/v1/leetcode"
SESSION = "REDACTED"
CSRF = "REDACTED"

def store_credentials():
    """Store LeetCode credentials via API (off-camera)."""
    resp = requests.post(
        f"{API_URL}/auth/store",
        json={"session": SESSION, "csrf_token": CSRF}
    )
    print(f"Store result: {resp.status_code}")
    print(f"Credentials stored: {resp.json().get('credentialsStored')}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "store"
    if cmd == "store":
        store_credentials()
    elif cmd == "status":
        resp = requests.get(f"{API_URL}/status")
        print(resp.json())
    elif cmd == "verify":
        resp = requests.post(f"{API_URL}/auth/validate")
        data = resp.json()
        print(f"Connected: {data.get('connected')}")
        print(f"Credentials stored: {data.get('credentialsStored')}")
