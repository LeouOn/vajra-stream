import sys
import os

project_root = r"c:\Users\llama\OneDrive\proj\vajra-stream"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
from fastapi.testclient import TestClient

def main():
    from backend.app.main import app
    client = TestClient(app)
    
    # Check models list
    print("Fetching models list...")
    res = client.get("/api/v1/llm/models")
    print(f"Status code: {res.status_code}")
    if res.status_code == 200:
        print("Models response:")
        print(res.json())
    else:
        print(res.text)

    # Check outlook history
    print("\nFetching outlook history...")
    res = client.get("/api/v1/outlook/history")
    print(f"Status code: {res.status_code}")
    if res.status_code == 200:
        print(f"History records found: {len(res.json().get('history', []))}")
        print("Latest history item preview:")
        history = res.json().get('history', [])
        if history:
            print(history[0])
    else:
        print(res.text)

if __name__ == "__main__":
    main()
