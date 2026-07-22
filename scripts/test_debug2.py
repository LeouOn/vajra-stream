import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402

client = TestClient(app)

r = client.post(
    "/api/v1/llm/chat",
    json={
        "messages": [{"role": "user", "content": "list populations"}],
        "provider": "auto",
        "debug_mode": True,
    },
)
data = r.json()
print(f"Status: {r.status_code}")
print(f"Tool calls: {len(data.get('tool_calls', []))}")
for tc in data.get("tool_calls", []):
    print(f"  {tc.get('tool_name')} -> {tc.get('status')}")
print(f"\nResponse preview: {data.get('response', '')[:200]}")
dbg = data.get("debug_info", {})
if dbg:
    print(f"\nDebug keys: {list(dbg.keys())}")
    print(f"text_parsed_tool_calls: {dbg.get('text_parsed_tool_calls')}")
    print(f"tools_executed: {dbg.get('tools_executed')}")
    print(f"provider: {dbg.get('provider')}")
    print(f"model: {dbg.get('model')}")
    print(f"finish_reason: {dbg.get('finish_reason')}")
