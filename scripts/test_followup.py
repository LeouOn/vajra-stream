import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)

r = client.post("/api/v1/llm/chat", json={
    "messages": [{"role": "user", "content": "list populations"}],
    "provider": "auto",
    "debug_mode": True,
})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Tool calls: {len(data.get('tool_calls', []))}")
for tc in data.get("tool_calls", []):
    print(f"  {tc.get('tool_name')} -> {tc.get('status')}")
print(f"\nResponse:\n{data.get('response', '')[:500]}")
dbg = data.get("debug_info", {})
if dbg:
    print(f"\nDebug: text_parsed={dbg.get('text_parsed_tool_calls')}, tools_executed={dbg.get('tools_executed')}")
    raw = dbg.get("raw_tool_results", [])
    if raw:
        print(f"Raw results count: {len(raw)}")
        print(f"First result keys: {list(raw[0].keys()) if raw else 'none'}")
