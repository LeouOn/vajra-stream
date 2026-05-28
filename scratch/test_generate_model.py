import sys
import os

project_root = r"c:\Users\llama\OneDrive\proj\vajra-stream"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi.testclient import TestClient

def main():
    from backend.app.main import app
    client = TestClient(app)
    
    payload = {
        "lat": 34.0522,
        "lon": -118.2437,
        "languages": ["English", "Sanskrit"],
        "genre": "victory",
        "model": "g4-runic-oarfish-26b-a4b-v1.2-i1",
        "randomize_realm": True,
        "randomize_characters": True
    }
    
    print("Testing generate_single with model 'g4-runic-oarfish-26b-a4b-v1.2-i1'...")
    res = client.post("/api/v1/outlook/generate_single", json=payload)
    print(f"Status code: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print("Success! Generated narrative:")
        print(data.get("narrative", "")[:500])
        print("...")
        print(f"Narrative ID: {data.get('id')}")
    else:
        print(res.text)

if __name__ == "__main__":
    main()
