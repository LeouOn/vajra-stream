import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)

print("=== Test: POST /api/v1/llm/chat with 'list populations' ===")
r = client.post("/api/v1/llm/chat", json={
    "messages": [{"role": "user", "content": "list populations"}],
    "provider": "auto",
})
data = r.json()
resp_text = data.get("response", "")
print(f"Status: {r.status_code}")
print(f"Response (first 300 chars):")
print(resp_text[:300])
print(f"\nTool calls count: {len(data.get('tool_calls', []))}")
for tc in data.get("tool_calls", []):
    print(f"  {tc.get('tool_name')} -> {tc.get('status')}")
dbg = data.get("debug_info", {})
print(f"\nDebug info:")
print(f"  provider: {dbg.get('provider') or dbg.get('provider_selected')}")
print(f"  model: {dbg.get('model')}")

print("\n=== Test: Parse the actual response for tool calls ===")
from backend.app.api.v1.endpoints.llm import _parse_text_tool_calls
parsed = _parse_text_tool_calls(resp_text)
print(f"Parsed tool calls: {parsed}")

print("\n=== Provider env check ===")
for key in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"]:
    val = os.getenv(key, "")
    if val:
        print(f"  {key}: SET ({val[:8]}...)")
    else:
        print(f"  {key}: NOT SET")

print("\n=== Test: model='nvidia/nemotron-nemotron-3-ultra-550b-a55b:free' ===")
r2 = client.post("/api/v1/llm/chat", json={
    "messages": [{"role": "user", "content": "list populations"}],
    "provider": "auto",
    "model": "nvidia/nemotron-nemotron-3-ultra-550b-a55b:free",
})
data2 = r2.json()
resp2 = data2.get("response", "")
print(f"Status: {r2.status_code}")
print(f"Response (first 300 chars):")
print(resp2[:300])
print(f"\nTool calls count: {len(data2.get('tool_calls', []))}")
for tc in data2.get("tool_calls", []):
    print(f"  {tc.get('tool_name')} -> {tc.get('status')}")
dbg2 = data2.get("debug_info", {})
print(f"Debug provider: {dbg2.get('provider') or dbg2.get('provider_selected')}")
print(f"Debug model: {dbg2.get('model')}")

parsed2 = _parse_text_tool_calls(resp2)
print(f"Parsed from response: {parsed2}")
