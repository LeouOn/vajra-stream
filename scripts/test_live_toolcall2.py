"""Test with the exact model the user is using."""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)

MODEL = "nvidia/nemotron-nemotron-3-ultra-550b-a55b:free"

print(f"=== Test with model={MODEL} ===")
r = client.post("/api/v1/llm/chat", json={
    "messages": [{"role": "user", "content": "list populations"}],
    "provider": "auto",
    "model": MODEL,
})
data = r.json()
resp = data.get("response", "")
tcs = data.get("tool_calls", [])

print(f"Status: {r.status_code}")
print(f"Response (first 200): {resp[:200]}")
print(f"Tool calls: {len(tcs)}")
for tc in tcs:
    print(f"  {tc.get('tool_name')} -> {tc.get('status')}")

if not tcs:
    print("\nNo tool_calls returned. Checking if text parser finds them...")
    from backend.app.api.v1.endpoints.llm import _parse_text_tool_calls
    parsed = _parse_text_tool_calls(resp)
    print(f"Parsed from response text: {parsed}")
    if parsed:
        print("TEXT PARSER FOUND THEM but they weren't executed!")
        print("This means the text parser path in _run_openai_compatible_tool_loop isn't firing.")
        print("Likely cause: the model returned msg.tool_calls as an empty list, not None.")
    else:
        print("Text parser also found nothing. The response text has no tool-call JSON.")

print(f"\n=== Provider routing ===")
for key in ["DEEPSEEK_API_KEY", "OPENROUTER_API_KEY"]:
    val = os.getenv(key, "")
    print(f"  {key}: {'SET' if val else 'NOT SET'}")
