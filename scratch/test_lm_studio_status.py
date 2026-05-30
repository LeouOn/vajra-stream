import json
import urllib.error
import urllib.request

url = "http://127.0.0.1:1234"

print("--- Probing /api/v0/models ---")
try:
    req = urllib.request.Request(f"{url}/api/v0/models")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        # Print first model to see structure
        if data.get("data"):
            print(json.dumps(data["data"][0], indent=2))
        else:
            print("No models found in /api/v0/models")
except Exception as e:
    print(f"Error querying /api/v0/models: {e}")

print("\n--- Probing /api/v1/models ---")
try:
    req = urllib.request.Request(f"{url}/api/v1/models")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        if data.get("data"):
            print(json.dumps(data["data"][0], indent=2))
        else:
            print("No models found in /api/v1/models")
except Exception as e:
    print(f"Error querying /api/v1/models: {e}")
