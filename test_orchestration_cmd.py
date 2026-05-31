import urllib.request
import json

url = "http://localhost:8008/api/v1/outlook/loop/start"
payload = {
    "interval_minutes": 1,
    "lat": 34.0522,
    "lon": -118.2437,
    "languages": ["English"],
    "genre": "alchemist"
}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print("Status:", response.status)
        print("Response:", response.read().decode('utf-8'))
except Exception as e:
    print(f"Error starting the narrative loop: {e}")
