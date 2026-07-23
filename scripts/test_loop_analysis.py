import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)

r = client.post("/api/v1/llm/chat", json={
    "messages": [{"role": "user", "content": "get statistics"}],
    "provider": "auto",
    "debug_mode": True,
})
data = r.json()

print(f"=== Tool loop analysis ===")
for tc in data.get("tool_calls", []):
    print(f"  {tc.get('tool_name')}({tc.get('arguments')}) -> {tc.get('status')}")

dbg = data.get("debug_info", {})
raw_responses = dbg.get("raw_llm_responses", [])
print(f"\n=== LLM turns ({len(raw_responses)}) ===")
for rr in raw_responses:
    preview = rr.get("content_preview", "")[:60]
    native_names = rr.get("native_tool_names", [])
    text_parsed = rr.get("text_parsed_tool_calls", [])
    print(f"  Turn {rr.get('turn')}: finish={rr.get('finish_reason')}")
    if native_names:
        print(f"    NATIVE tool calls: {native_names}")
    if text_parsed:
        print(f"    TEXT-parsed tool calls: {text_parsed}")
    print(f"    Preview: {preview}")

print(f"\n=== Raw tool results count ===")
raw = dbg.get("raw_tool_results", [])
print(f"  Total tools executed: {len(raw)}")
for r2 in raw:
    status = r2.get("status")
    name = r2.get("tool")
    result = r2.get("result")
    if isinstance(result, dict):
        print(f"  {name} -> {status}: keys={list(result.keys())[:8]}")
    else:
        print(f"  {name} -> {status}: result type={type(result).__name__}")
