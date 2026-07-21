import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)

print("=== Test: auto provider, default model ===")
r = client.post("/api/v1/llm/chat", json={
    "messages": [{"role": "user", "content": "list populations"}],
    "provider": "auto",
})
data = r.json()
resp = data.get("response", "")
tcs = data.get("tool_calls", [])
print(f"Status: {r.status_code}")
print(f"Response (first 200): {resp[:200]}")
print(f"Tool calls: {len(tcs)}")
for tc in tcs:
    name = tc.get("tool_name", "?")
    status = tc.get("status", "?")
    print(f"  {name} -> {status}")
print("DONE")
